"""Caching operations for model selection.

Story 8.2: External Data Client Refactoring - Cache Module
Story 7b-4: Model Selection Cache
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy.exc import IntegrityError

from raglite.external_data.orm_models import ModelSelectionORM
from raglite.external_data.storage.constants import MODEL_SELECTION_TTL_DAYS
from raglite.shared.database import get_session
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from raglite.forecasting.model_selection import ModelSelectionResult

logger = get_logger(__name__)


@dataclass
class CachedModelSelection:
    """Cached model selection result for a variable.

    Story 7b-4 AC-7b.4.3: Dataclass for cached model selection results.
    """

    variable_name: str
    best_model: str
    best_mape: float
    best_mase: float | None  # M3: Can be None if not calculated
    use_regressors: bool
    regressor_list: list[str]
    candidate_results: dict
    data_characteristics: dict | None
    selected_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if cached entry has expired (AC-7b.4.5).

        Returns:
            True if current time is past expires_at, False otherwise
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        return now >= self.expires_at


def _sanitize_for_json(obj: Any) -> Any:
    """Sanitize a value for JSON serialization, handling Infinity, NaN, Enums, and numpy types.

    Args:
        obj: Any value that may not be JSON-serializable

    Returns:
        JSON-serializable version of the value
    """
    import math

    import numpy as np

    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        val = float(obj)
        if math.isinf(val) or math.isnan(val):
            return None
        return val
    elif isinstance(obj, float):
        if math.isinf(obj) or math.isnan(obj):
            return None
        return obj
    elif isinstance(obj, np.ndarray):
        return [_sanitize_for_json(v) for v in obj.tolist()]
    else:
        return obj


def _serialize_dataclass_with_enums(obj: Any) -> dict[str, Any]:
    """Serialize a dataclass to dict, converting Enums and numpy types to JSON-serializable values.

    Args:
        obj: A dataclass instance that may contain Enum fields or numpy types

    Returns:
        Dictionary with all values converted to JSON-serializable types
    """
    result = dataclasses.asdict(obj)
    sanitized = _sanitize_for_json(result)
    # _sanitize_for_json preserves dict structure when input is dict
    return dict(sanitized) if isinstance(sanitized, dict) else {"data": sanitized}


def _create_model_selection_orm(
    result: ModelSelectionResult,
    selected_at: datetime,
    expires_at: datetime,
    sanitized_candidate_results: dict,
    data_chars_dict: dict | None,
) -> ModelSelectionORM:
    """Create a ModelSelectionORM instance from result data.

    Args:
        result: ModelSelectionResult from select_best_model()
        selected_at: Timestamp when model was selected
        expires_at: Expiration timestamp
        sanitized_candidate_results: JSON-safe candidate results
        data_chars_dict: Serialized data characteristics

    Returns:
        ModelSelectionORM instance ready for database insertion
    """
    return ModelSelectionORM(
        variable_name=result.variable_name,
        best_model=result.best_model,
        best_mape=Decimal(str(result.best_mape)),
        best_mase=Decimal(str(result.best_mase)),
        use_regressors=result.best_with_regressors,
        regressor_list=result.best_regressor_set,
        candidate_results=sanitized_candidate_results,
        data_characteristics=data_chars_dict,
        selected_at=selected_at,
        expires_at=expires_at,
    )


def _update_existing_entry(
    existing: ModelSelectionORM,
    result: ModelSelectionResult,
    selected_at: datetime,
    expires_at: datetime,
    sanitized_candidate_results: dict,
    data_chars_dict: dict | None,
) -> None:
    """Update an existing ModelSelectionORM entry with new data.

    Args:
        existing: Existing ModelSelectionORM instance to update
        result: New ModelSelectionResult data
        selected_at: Timestamp when model was selected
        expires_at: Expiration timestamp
        sanitized_candidate_results: JSON-safe candidate results
        data_chars_dict: Serialized data characteristics
    """
    existing.best_model = result.best_model
    existing.best_mape = Decimal(str(result.best_mape))
    existing.best_mase = Decimal(str(result.best_mase))
    existing.use_regressors = result.best_with_regressors
    existing.regressor_list = result.best_regressor_set
    existing.candidate_results = sanitized_candidate_results
    existing.data_characteristics = data_chars_dict
    existing.selected_at = selected_at
    existing.expires_at = expires_at


def _handle_integrity_error_update(
    session: Any,
    result: ModelSelectionResult,
    selected_at: datetime,
    expires_at: datetime,
    sanitized_candidate_results: dict,
    data_chars_dict: dict | None,
) -> None:
    """Handle IntegrityError by updating existing entry or retrying insert.

    Args:
        session: SQLAlchemy session
        result: ModelSelectionResult from select_best_model()
        selected_at: Timestamp when model was selected
        expires_at: Expiration timestamp
        sanitized_candidate_results: JSON-safe candidate results
        data_chars_dict: Serialized data characteristics
    """
    session.rollback()

    # Re-fetch with lock to prevent concurrent modification
    existing = (
        session.query(ModelSelectionORM)
        .filter(ModelSelectionORM.variable_name == result.variable_name)
        .with_for_update()
        .first()
    )

    if existing:
        # Update using helper
        _update_existing_entry(
            existing,
            result,
            selected_at,
            expires_at,
            sanitized_candidate_results,
            data_chars_dict,
        )

        try:
            session.commit()
            logger.info(
                "Updated cached model selection",
                extra={
                    "variable_name": result.variable_name,
                    "best_model": result.best_model,
                    "best_mape": result.best_mape,
                },
            )
        except Exception as update_error:
            # Handle race condition where row was deleted between SELECT and UPDATE
            session.rollback()
            logger.warning(
                "Failed to update cached model selection (possible concurrent deletion)",
                extra={
                    "variable_name": result.variable_name,
                    "error": str(update_error),
                },
            )
            # Attempt insert again as a fallback using helper
            new_entry_retry = _create_model_selection_orm(
                result,
                selected_at,
                expires_at,
                sanitized_candidate_results,
                data_chars_dict,
            )
            session.add(new_entry_retry)
            session.commit()


def cache_model_selection(result: ModelSelectionResult) -> None:
    """Cache model selection result in PostgreSQL.

    Story 7b-4 AC-7b.4.2: Store model selection results with upsert semantics.

    Uses INSERT ... ON CONFLICT to update existing entries for the same variable.
    Sets expires_at to selected_at + 7 days (AC-7b.4.5).

    Args:
        result: ModelSelectionResult from select_best_model()
    """
    session = get_session()

    try:
        # Calculate expiry time (AC-7b.4.5: 7-day TTL)
        # Use naive datetime for PostgreSQL TIMESTAMP column
        selected_at = datetime.now(UTC).replace(tzinfo=None)
        expires_at = selected_at + timedelta(days=MODEL_SELECTION_TTL_DAYS)

        # Serialize DataCharacteristics if present (with Enum->string conversion)
        data_chars_dict = None
        if result.data_characteristics:
            data_chars_dict = _serialize_dataclass_with_enums(result.data_characteristics)

        # Sanitize candidate_results (may contain Infinity/NaN from failed models)
        sanitized_candidate_results = _sanitize_for_json(result.candidate_results)

        # Create new entry using helper
        new_entry = _create_model_selection_orm(
            result, selected_at, expires_at, sanitized_candidate_results, data_chars_dict
        )

        # Try insert first (optimistic approach for new entries)
        session.add(new_entry)

        try:
            session.commit()
            logger.info(
                "Cached model selection",
                extra={
                    "variable_name": result.variable_name,
                    "best_model": result.best_model,
                    "best_mape": result.best_mape,
                },
            )
        except IntegrityError:
            # Entry exists, update instead
            _handle_integrity_error_update(
                session,
                result,
                selected_at,
                expires_at,
                sanitized_candidate_results,
                data_chars_dict,
            )
    except Exception as e:
        session.rollback()
        logger.error(
            "Failed to cache model selection",
            extra={"variable_name": result.variable_name, "error": str(e)},
        )
        raise
    finally:
        session.close()


def get_cached_model_selection(variable_name: str) -> CachedModelSelection | None:
    """Retrieve cached model selection for a variable.

    Story 7b-4 AC-7b.4.3: Lookup cached model selection by variable name.
    Performance target: <100ms (indexed query on variable_name).

    Note: Returns expired entries with is_expired=True. Caller should check
    the is_expired property to determine if re-selection is needed.

    Args:
        variable_name: Name of the variable to look up (non-empty, max 100 chars)

    Returns:
        CachedModelSelection if found (may be expired), None if not found

    Raises:
        ValueError: If variable_name is empty or exceeds 100 characters
    """
    # M4: Input validation
    if not variable_name or not variable_name.strip():
        raise ValueError("variable_name cannot be empty")
    if len(variable_name) > 100:
        raise ValueError("variable_name cannot exceed 100 characters")
    session = get_session()

    try:
        record = (
            session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == variable_name)
            .first()
        )

        if not record:
            return None

        # Convert ORM to dataclass
        cached = CachedModelSelection(
            variable_name=record.variable_name,
            best_model=record.best_model,
            best_mape=float(record.best_mape),
            best_mase=float(record.best_mase)
            if record.best_mase is not None
            else None,  # M2: Preserve None
            use_regressors=record.use_regressors,
            regressor_list=record.regressor_list or [],
            candidate_results=record.candidate_results or {},
            data_characteristics=record.data_characteristics,
            selected_at=record.selected_at,
            expires_at=record.expires_at,
        )

        return cached

    finally:
        session.close()


def invalidate_model_selection(variable_name: str | None = None) -> int:
    """Invalidate (delete) cached model selection entries.

    Story 7b-4 AC-7b.4.4: Manual cache invalidation.

    Args:
        variable_name: Specific variable to invalidate, or None to invalidate all
                       (non-empty, max 100 chars if provided)

    Returns:
        Number of deleted records

    Raises:
        ValueError: If variable_name is empty or exceeds 100 characters
    """
    # M4: Input validation
    if variable_name is not None:
        if not variable_name.strip():
            raise ValueError("variable_name cannot be empty")
        if len(variable_name) > 100:
            raise ValueError("variable_name cannot exceed 100 characters")

    session = get_session()

    try:
        query = session.query(ModelSelectionORM)

        if variable_name:
            query = query.filter(ModelSelectionORM.variable_name == variable_name)

        count = query.delete()
        session.commit()

        logger.info(
            "Invalidated model selection cache",
            extra={"variable_name": variable_name or "all", "count": count},
        )

        return count

    except Exception as e:
        session.rollback()
        logger.error(
            "Failed to invalidate model selection cache",
            extra={"variable_name": variable_name, "error": str(e)},
        )
        raise
    finally:
        session.close()


def cleanup_expired_model_selections() -> int:
    """Delete expired model selection entries.

    Story 7b-4 AC-7b.4.5: Automatic cleanup of expired entries.
    Should be run periodically (e.g., daily cron job).

    Returns:
        Number of deleted records
    """
    session = get_session()

    try:
        # Use naive datetime for PostgreSQL TIMESTAMP column
        now = datetime.now(UTC).replace(tzinfo=None)

        count = session.query(ModelSelectionORM).filter(ModelSelectionORM.expires_at < now).delete()
        session.commit()

        logger.info("Cleaned up expired model selections", extra={"count": count})

        return count

    except Exception as e:
        session.rollback()
        logger.error(
            "Failed to cleanup expired model selections",
            extra={"error": str(e)},
        )
        raise
    finally:
        session.close()


def invalidate_all_model_selections() -> int:
    """Invalidate all cached model selection entries.

    Story 7b-4 AC-7b.4.4: Convenience alias for invalidating all entries.

    This is a convenience wrapper around invalidate_model_selection(None).

    Returns:
        Number of deleted records
    """
    return invalidate_model_selection(variable_name=None)
