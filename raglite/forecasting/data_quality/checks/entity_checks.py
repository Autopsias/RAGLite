"""Entity-related data quality checks.

Checks for entity contamination (fuzzy vs exact match leakage) and coverage.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.forecasting.data_quality.checks.entity_checks_helpers import (
    build_coverage_entity_condition,
    build_metric_condition,
    check_entity_column_has_normalized,
    execute_coverage_count_query,
    execute_exact_match_count,
    execute_fuzzy_match_count,
    get_contaminated_entities_sample,
)
from raglite.forecasting.data_quality.config import (
    EntityMatchMode,
    VariableQualityConfig,
)
from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def _evaluate_contamination_result(
    variable: str,
    entity: str,
    fuzzy_count: int,
    exact_count: int,
    contaminated_entities: list[str],
) -> CheckResult:
    """Evaluate contamination check results and return appropriate status.

    Args:
        variable: Variable name
        entity: Entity name
        fuzzy_count: Count of fuzzy matches
        exact_count: Count of exact matches
        contaminated_entities: List of contaminated entity samples

    Returns:
        CheckResult with appropriate status based on contamination level
    """
    if fuzzy_count == 0 and exact_count == 0:
        return CheckResult(
            check_name="entity_contamination",
            status=CheckStatus.WARN,
            message=f"No data found for entity '{entity}'",
            variable=variable,
            actual_value=0,
            severity=2,
        )

    ratio = fuzzy_count / max(exact_count, 1)

    # Story 6.28: Use tolerance-based thresholds for contamination detection
    # - ratio <= 1.1 (10% tolerance): PASS - essentially no leakage
    # - ratio <= 1.5 (50% tolerance): WARN - minor leakage
    # - ratio > 1.5: FAIL - significant leakage
    if ratio <= 1.1:
        return CheckResult(
            check_name="entity_contamination",
            status=CheckStatus.PASS,
            message=f"Minimal contamination: fuzzy={fuzzy_count}, exact={exact_count} ({ratio:.1f}x)",
            variable=variable,
            actual_value=exact_count,
        )

    if ratio <= 1.5:
        return CheckResult(
            check_name="entity_contamination",
            status=CheckStatus.WARN,
            message=f"Minor leakage: fuzzy={fuzzy_count}, exact={exact_count} ({ratio:.1f}x)",
            variable=variable,
            actual_value=fuzzy_count,
            threshold=exact_count,
            severity=2,
        )

    # Significant contamination detected
    severity = 5 if ratio > 5 else (4 if ratio > 2 else 3)

    return CheckResult(
        check_name="entity_contamination",
        status=CheckStatus.FAIL,
        message=f"Leakage detected: fuzzy={fuzzy_count}, exact={exact_count} ({ratio:.1f}x)",
        variable=variable,
        severity=severity,
        actual_value=fuzzy_count,
        threshold=exact_count,
        sample_rows=[{"entity": e} for e in contaminated_entities],
    )


async def check_entity_contamination(
    variable: str,
    config: VariableQualityConfig,
    data: pd.DataFrame | None = None,
) -> CheckResult:
    """Check for entity contamination in SQL queries.

    Detects leakage where ILIKE patterns match unintended rows.
    E.g., '%Group%' matching 'Portugal Group Madeira' instead of just 'GROUP'.

    Story 6.27: This check detects the 11x leakage issue where ILIKE '%Group%'
    matched 198 rows vs 18 for exact 'GROUP' match.

    Args:
        variable: Variable name
        config: Variable quality configuration
        data: Optional pre-fetched data (unused, queries DB directly)

    Returns:
        CheckResult with contamination status
    """
    if not config.entity.contamination_check:
        return CheckResult(
            check_name="entity_contamination",
            status=CheckStatus.SKIP,
            message="Entity contamination check not configured",
            variable=variable,
        )

    if config.entity.required_entity is None:
        return CheckResult(
            check_name="entity_contamination",
            status=CheckStatus.SKIP,
            message="No entity filter configured",
            variable=variable,
        )

    entity = config.entity.required_entity

    # Query DB to compare exact vs fuzzy match counts
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # Get metric aliases to search for
        aliases = config.db_metric_aliases or [variable]
        metric_condition, metric_params = build_metric_condition(aliases)

        # Story 6.28: Use entity_normalized column if available for exact matches
        # This avoids contamination by matching on normalized canonical entities
        from raglite.ingestion.entity_normalizer import normalize_entity

        canonical_entity = normalize_entity(entity)
        has_normalized_bool = check_entity_column_has_normalized(cursor)

        exact_count = execute_exact_match_count(
            cursor,
            metric_condition,
            metric_params,
            entity,
            canonical_entity,
            bool(has_normalized_bool),
        )
        fuzzy_count = execute_fuzzy_match_count(cursor, metric_condition, metric_params, entity)
        contaminated_entities = get_contaminated_entities_sample(
            cursor,
            metric_condition,
            metric_params,
            entity,
            canonical_entity,
            bool(has_normalized_bool),
        )

    except Exception as e:
        logger.error(
            "Entity contamination check failed",
            extra={"variable": variable, "error": str(e)},
        )
        return CheckResult(
            check_name="entity_contamination",
            status=CheckStatus.FAIL,
            message=f"Query error: {e}",
            variable=variable,
            severity=3,
        )
    finally:
        cursor.close()

    return _evaluate_contamination_result(
        variable, entity, fuzzy_count, exact_count, contaminated_entities
    )


def _build_coverage_metric_condition(
    variable: str, config: VariableQualityConfig
) -> tuple[str, list[str]]:
    """Build SQL condition and parameters for metric matching in coverage check.

    Args:
        variable: Variable name
        config: Variable quality configuration

    Returns:
        Tuple of (SQL condition string, parameter list)
    """
    aliases = config.db_metric_aliases or [variable]
    metric_condition = " OR ".join(["metric ILIKE %s"] * len(aliases))
    metric_params = [f"%{alias}%" for alias in aliases]
    return metric_condition, metric_params


def _check_entity_normalized_available(cursor: Any) -> bool:
    """Check if entity_normalized column exists and has data.

    Args:
        cursor: PostgreSQL cursor

    Returns:
        True if entity_normalized has data, False otherwise
    """
    result = check_entity_column_has_normalized(cursor)
    return bool(result) if isinstance(result, int) else result


def _evaluate_coverage_result(
    variable: str,
    entity: str,
    period_count: int,
    min_required: int,
) -> CheckResult:
    """Evaluate coverage check results and return appropriate status.

    Args:
        variable: Variable name
        entity: Entity name
        period_count: Number of periods found
        min_required: Minimum required periods

    Returns:
        CheckResult with appropriate status based on coverage level
    """
    if period_count >= min_required:
        return CheckResult(
            check_name="entity_coverage",
            status=CheckStatus.PASS,
            message=f"Entity '{entity}' has {period_count} periods (>= {min_required})",
            variable=variable,
            actual_value=period_count,
            threshold=min_required,
        )

    if period_count > 0:
        return CheckResult(
            check_name="entity_coverage",
            status=CheckStatus.WARN,
            message=f"Low coverage: {period_count} periods (need {min_required})",
            variable=variable,
            actual_value=period_count,
            threshold=min_required,
            severity=2,
        )

    return CheckResult(
        check_name="entity_coverage",
        status=CheckStatus.FAIL,
        message=f"No data for entity '{entity}'",
        variable=variable,
        actual_value=0,
        threshold=min_required,
        severity=4,
    )


async def check_entity_coverage(
    variable: str,
    config: VariableQualityConfig,
    data: pd.DataFrame | None = None,
) -> CheckResult:
    """Check if required entity has sufficient data.

    Verifies that the entity filter returns at least min_data_points rows.

    Args:
        variable: Variable name
        config: Variable quality configuration
        data: Optional pre-fetched data

    Returns:
        CheckResult with coverage status
    """
    if config.entity.match_mode == EntityMatchMode.ANY:
        return CheckResult(
            check_name="entity_coverage",
            status=CheckStatus.SKIP,
            message="No entity filter required",
            variable=variable,
        )

    entity = config.entity.required_entity
    if entity is None:
        return CheckResult(
            check_name="entity_coverage",
            status=CheckStatus.SKIP,
            message="No entity configured",
            variable=variable,
        )

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # Build metric condition
        metric_condition, metric_params = _build_coverage_metric_condition(variable, config)

        # Story 6.28: Use entity_normalized column if available
        from raglite.ingestion.entity_normalizer import normalize_entity

        canonical_entity = normalize_entity(entity) or entity
        has_normalized = _check_entity_normalized_available(cursor)

        # Build entity condition based on match mode
        entity_condition, entity_param = build_coverage_entity_condition(
            entity, canonical_entity, has_normalized, config.entity.match_mode
        )

        # Execute query
        period_count = execute_coverage_count_query(
            cursor, metric_condition, metric_params, entity_condition, entity_param
        )

    except Exception as e:
        logger.error(
            "Entity coverage check failed",
            extra={"variable": variable, "error": str(e)},
        )
        return CheckResult(
            check_name="entity_coverage",
            status=CheckStatus.FAIL,
            message=f"Query error: {e}",
            variable=variable,
            severity=3,
        )
    finally:
        cursor.close()

    min_required = config.min_data_points
    return _evaluate_coverage_result(variable, entity, period_count, min_required)
