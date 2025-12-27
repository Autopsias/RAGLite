"""Model weight and registry storage operations.

Story 8.2 Task 3.7: Extract model weight and registry methods from storage.py

Provides operations for:
- Saving/updating model weights for ensemble forecasting
- Retrieving model weights for specific metrics
- Deleting model weights
- Model registry checkpoint management (Story 6.14)

Related to:
- Story 6.12: Model Weight Storage Methods
- Story 6.14: Model Registry Operations
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from raglite.external_data.orm_models import ModelWeightORM
from raglite.shared.database import utc_now
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from raglite.external_data.models import ModelRegistry

logger = get_logger(__name__)

# Story 6.12 AC4: Weight caps (5% min, 50% max)
MIN_WEIGHT = 0.05
MAX_WEIGHT = 0.50


def save_model_weight(
    session: Session,
    metric_name: str,
    model_name: str,
    weight: float,
    backtest_rmse: float | None = None,
    backtest_mape: float | None = None,
    has_regressors: bool = True,
    data_points: int | None = None,
) -> ModelWeightORM:
    """Save or update a model weight entry.

    Story 6.12 AC2: Store model weights from backtest results.
    Story 6.12 AC4: Weight caps enforced (5% min, 50% max).

    Uses upsert semantics: updates existing entry or creates new one.

    Args:
        session: SQLAlchemy database session
        metric_name: Target metric (e.g., "cement_demand")
        model_name: Model identifier (e.g., "prophet", "xgboost", "catboost")
        weight: Normalized weight (0.0-1.0)
        backtest_rmse: RMSE from backtest validation (optional)
        backtest_mape: MAPE from backtest validation (optional)
        has_regressors: Whether external regressors were available
        data_points: Number of data points used in backtest

    Returns:
        Created or updated ModelWeightORM instance

    Raises:
        ValueError: If weight is outside valid range after capping
    """
    # Apply caps and warn if adjustment was needed
    original_weight = weight
    weight = max(MIN_WEIGHT, min(MAX_WEIGHT, weight))

    if original_weight != weight:
        logger.warning(
            "Weight capped to valid range",
            extra={
                "metric": metric_name,
                "model": model_name,
                "original_weight": original_weight,
                "capped_weight": weight,
            },
        )

    # Check for existing entry
    existing: ModelWeightORM | None = (
        session.query(ModelWeightORM)
        .filter(
            ModelWeightORM.metric_name == metric_name,
            ModelWeightORM.model_name == model_name,
        )
        .first()
    )

    if existing:
        # Update existing entry
        existing.weight = Decimal(str(weight))
        existing.backtest_rmse = Decimal(str(backtest_rmse)) if backtest_rmse is not None else None
        existing.backtest_mape = Decimal(str(backtest_mape)) if backtest_mape is not None else None
        existing.has_regressors = has_regressors
        existing.data_points = data_points
        existing.calculated_at = utc_now()
        session.commit()
        session.refresh(existing)
        logger.info(
            "Updated model weight",
            extra={"metric": metric_name, "model": model_name, "weight": weight},
        )
        return existing
    else:
        # Create new entry
        new_weight = ModelWeightORM(
            metric_name=metric_name,
            model_name=model_name,
            weight=Decimal(str(weight)),
            backtest_rmse=Decimal(str(backtest_rmse)) if backtest_rmse is not None else None,
            backtest_mape=Decimal(str(backtest_mape)) if backtest_mape is not None else None,
            has_regressors=has_regressors,
            data_points=data_points,
            calculated_at=utc_now(),
        )
        session.add(new_weight)
        session.commit()
        session.refresh(new_weight)
        logger.info(
            "Created model weight",
            extra={"metric": metric_name, "model": model_name, "weight": weight},
        )
        return new_weight


def get_model_weights(
    session: Session,
    metric_name: str | None = None,
) -> list[ModelWeightORM]:
    """Get model weights, optionally filtered by metric.

    Story 6.12 AC2: Query model weights for ensemble configuration.

    Args:
        session: SQLAlchemy database session
        metric_name: Filter by metric (None = all metrics)

    Returns:
        List of ModelWeightORM entries
    """
    query = session.query(ModelWeightORM)

    if metric_name:
        query = query.filter(ModelWeightORM.metric_name == metric_name)

    query = query.order_by(ModelWeightORM.metric_name, ModelWeightORM.model_name)
    result: list[ModelWeightORM] = list(query.all())
    return result


def get_weights_for_metric(
    session: Session,
    metric_name: str,
) -> dict[str, float]:
    """Get model weights as a dict for a specific metric.

    Story 6.12 AC4: Retrieve weights for ensemble forecast.

    Args:
        session: SQLAlchemy database session
        metric_name: Target metric name

    Returns:
        Dict mapping model_name -> weight (float)
    """
    weights = get_model_weights(session, metric_name)
    return {w.model_name: float(w.weight) for w in weights}


def delete_model_weights(
    session: Session,
    metric_name: str | None = None,
) -> int:
    """Delete model weights, optionally filtered by metric.

    Args:
        session: SQLAlchemy database session
        metric_name: Metric to delete weights for (None = all weights)

    Returns:
        Number of deleted records
    """
    query = session.query(ModelWeightORM)

    if metric_name:
        query = query.filter(ModelWeightORM.metric_name == metric_name)

    count: int = query.delete()
    session.commit()

    logger.info(
        "Deleted model weights",
        extra={"metric": metric_name or "all", "count": count},
    )
    return count


# ===========================================================================
# Story 6.14: Model Registry Operations
# ===========================================================================


def save_model_checkpoint(
    session: Session,
    model_type: str,
    model_version: str,
    checkpoint_path: str,
    metrics_json: dict[str, float | str | int] | None = None,
    set_active: bool = True,
) -> ModelRegistry:
    """Save trained model checkpoint to registry.

    Story 6.14 AC2: Save checkpoint and update registry.

    Args:
        session: SQLAlchemy database session
        model_type: Model type (e.g., "tft")
        model_version: Version string (e.g., "2024-12-10")
        checkpoint_path: Path to checkpoint file
        metrics_json: Training/validation metrics
        set_active: Mark as active checkpoint for this model type

    Returns:
        ModelRegistry entry
    """
    from raglite.external_data.models import ModelRegistry
    from raglite.external_data.orm_models import ModelRegistryORM

    # Deactivate other checkpoints for this model_type if setting active
    if set_active:
        session.query(ModelRegistryORM).filter(ModelRegistryORM.model_type == model_type).update(
            {"is_active": False}
        )

    # Create new checkpoint entry
    checkpoint_orm = ModelRegistryORM(
        model_type=model_type,
        model_version=model_version,
        checkpoint_path=checkpoint_path,
        metrics_json=metrics_json,
        is_active=set_active,
    )

    session.add(checkpoint_orm)
    session.commit()
    session.refresh(checkpoint_orm)

    logger.info(
        "Saved model checkpoint to registry",
        extra={
            "model_type": model_type,
            "version": model_version,
            "active": set_active,
        },
    )

    return ModelRegistry(
        id=checkpoint_orm.id,
        model_type=checkpoint_orm.model_type,
        model_version=checkpoint_orm.model_version,
        checkpoint_path=checkpoint_orm.checkpoint_path,
        metrics_json=checkpoint_orm.metrics_json,
        trained_at=checkpoint_orm.trained_at,
        is_active=checkpoint_orm.is_active,
    )


def get_active_model(session: Session, model_type: str) -> ModelRegistry | None:
    """Get active checkpoint for model type.

    Story 6.14 AC2: Retrieve active checkpoint for inference.

    Args:
        session: SQLAlchemy database session
        model_type: Model type (e.g., "tft")

    Returns:
        Active ModelRegistry entry or None
    """
    from raglite.external_data.models import ModelRegistry
    from raglite.external_data.orm_models import ModelRegistryORM

    checkpoint_orm = (
        session.query(ModelRegistryORM)
        .filter(
            ModelRegistryORM.model_type == model_type,
            ModelRegistryORM.is_active == True,  # noqa: E712
        )
        .first()
    )

    if not checkpoint_orm:
        return None

    return ModelRegistry(
        id=checkpoint_orm.id,
        model_type=checkpoint_orm.model_type,
        model_version=checkpoint_orm.model_version,
        checkpoint_path=checkpoint_orm.checkpoint_path,
        metrics_json=checkpoint_orm.metrics_json,
        trained_at=checkpoint_orm.trained_at,
        is_active=checkpoint_orm.is_active,
    )


def get_model_history(
    session: Session,
    model_type: str,
    limit: int = 10,
) -> list[ModelRegistry]:
    """Get checkpoint history for model type.

    Story 6.14 AC2: Retrieve checkpoint history for fallback.

    Args:
        session: SQLAlchemy database session
        model_type: Model type (e.g., "tft")
        limit: Maximum number of checkpoints to return

    Returns:
        List of ModelRegistry entries (newest first)
    """
    from raglite.external_data.models import ModelRegistry
    from raglite.external_data.orm_models import ModelRegistryORM

    checkpoints_orm = (
        session.query(ModelRegistryORM)
        .filter(ModelRegistryORM.model_type == model_type)
        .order_by(ModelRegistryORM.trained_at.desc())
        .limit(limit)
        .all()
    )

    return [
        ModelRegistry(
            id=c.id,
            model_type=c.model_type,
            model_version=c.model_version,
            checkpoint_path=c.checkpoint_path,
            metrics_json=c.metrics_json,
            trained_at=c.trained_at,
            is_active=c.is_active,
        )
        for c in checkpoints_orm
    ]
