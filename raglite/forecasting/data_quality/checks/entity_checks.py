"""Entity-related data quality checks.

Checks for entity contamination (fuzzy vs exact match leakage) and coverage.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.forecasting.data_quality.config import (
    EntityMatchMode,
    VariableQualityConfig,
)
from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def _check_entity_column_has_normalized(cursor: Any) -> bool | int:
    """Check if entity_normalized column exists and has data.

    Args:
        cursor: PostgreSQL cursor

    Returns:
        True if entity_normalized has data, False otherwise
    """
    check_normalized_query = """
        SELECT COUNT(*) FROM financial_tables WHERE entity_normalized IS NOT NULL LIMIT 1
    """
    cursor.execute(check_normalized_query)
    result = cursor.fetchone()[0]
    return result > 0 if isinstance(result, int) else False


def _build_metric_condition(aliases: list[str]) -> tuple[str, list[str]]:
    """Build SQL condition and parameters for metric matching.

    Args:
        aliases: List of metric aliases to search for

    Returns:
        Tuple of (SQL condition string, parameter list)
    """
    metric_condition = " OR ".join(["metric ILIKE %s"] * len(aliases))
    metric_params = [f"%{alias}%" for alias in aliases]
    return metric_condition, metric_params


def _execute_exact_match_count(
    cursor: Any,
    metric_condition: str,
    metric_params: list[str],
    entity: str,
    canonical_entity: str | None,
    has_normalized: bool,
) -> int | Any:
    """Execute query to count exact entity matches.

    Args:
        cursor: PostgreSQL cursor
        metric_condition: SQL condition for metric matching
        metric_params: Parameters for metric condition
        entity: Original entity name
        canonical_entity: Normalized entity name
        has_normalized: Whether to use entity_normalized column

    Returns:
        Count of exact matches
    """
    if has_normalized:
        exact_query = f"""  # nosec
            SELECT COUNT(*) FROM financial_tables
            WHERE ({metric_condition})
            AND entity_normalized = %s
        """
        cursor.execute(exact_query, metric_params + [canonical_entity or entity])
    else:
        exact_query = f"""  # nosec
            SELECT COUNT(*) FROM financial_tables
            WHERE ({metric_condition})
            AND entity = %s
        """
        cursor.execute(exact_query, metric_params + [entity])
    return cursor.fetchone()[0]


def _execute_fuzzy_match_count(
    cursor: Any,
    metric_condition: str,
    metric_params: list[str],
    entity: str,
) -> int | Any:
    """Execute query to count fuzzy entity matches.

    Args:
        cursor: PostgreSQL cursor
        metric_condition: SQL condition for metric matching
        metric_params: Parameters for metric condition
        entity: Entity name for fuzzy matching

    Returns:
        Count of fuzzy matches
    """
    fuzzy_query = f"""  # nosec
        SELECT COUNT(*) FROM financial_tables
        WHERE ({metric_condition})
        AND entity ILIKE %s
    """
    cursor.execute(fuzzy_query, metric_params + [f"%{entity}%"])
    return cursor.fetchone()[0]


def _get_contaminated_entities_sample(
    cursor: Any,
    metric_condition: str,
    metric_params: list[str],
    entity: str,
    canonical_entity: str | None,
    has_normalized: bool,
) -> list[str]:
    """Get sample of contaminated entities (fuzzy match but not exact).

    Args:
        cursor: PostgreSQL cursor
        metric_condition: SQL condition for metric matching
        metric_params: Parameters for metric condition
        entity: Original entity name
        canonical_entity: Normalized entity name
        has_normalized: Whether to use entity_normalized column

    Returns:
        List of contaminated entity names
    """
    if has_normalized:
        sample_query = f"""  # nosec
            SELECT DISTINCT entity FROM financial_tables
            WHERE ({metric_condition})
            AND entity ILIKE %s
            AND entity_normalized != %s
            LIMIT 5
        """
        cursor.execute(sample_query, metric_params + [f"%{entity}%", canonical_entity or entity])
    else:
        sample_query = f"""  # nosec
            SELECT DISTINCT entity FROM financial_tables
            WHERE ({metric_condition})
            AND entity ILIKE %s
            AND entity != %s
            LIMIT 5
        """
        cursor.execute(sample_query, metric_params + [f"%{entity}%", entity])
    return [row[0] for row in cursor.fetchall()]


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
        metric_condition, metric_params = _build_metric_condition(aliases)

        # Story 6.28: Use entity_normalized column if available for exact matches
        # This avoids contamination by matching on normalized canonical entities
        from raglite.ingestion.entity_normalizer import normalize_entity

        canonical_entity = normalize_entity(entity)
        has_normalized_bool = _check_entity_column_has_normalized(cursor)

        exact_count = _execute_exact_match_count(
            cursor,
            metric_condition,
            metric_params,
            entity,
            canonical_entity,
            bool(has_normalized_bool),
        )
        fuzzy_count = _execute_fuzzy_match_count(cursor, metric_condition, metric_params, entity)
        contaminated_entities = _get_contaminated_entities_sample(
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
        aliases = config.db_metric_aliases or [variable]
        metric_condition = " OR ".join(["metric ILIKE %s"] * len(aliases))
        metric_params = [f"%{alias}%" for alias in aliases]

        # Story 6.28: Use entity_normalized column if available
        from raglite.ingestion.entity_normalizer import normalize_entity

        canonical_entity = normalize_entity(entity)

        # Check if entity_normalized column has data
        check_normalized_query = """
            SELECT COUNT(*) FROM financial_tables WHERE entity_normalized IS NOT NULL LIMIT 1
        """
        cursor.execute(check_normalized_query)
        has_normalized = cursor.fetchone()[0] > 0

        # Build entity condition based on match mode
        if has_normalized and config.entity.match_mode == EntityMatchMode.EXACT:
            # Use entity_normalized for exact match
            entity_condition = "entity_normalized = %s"
            entity_param = canonical_entity or entity
        elif config.entity.match_mode == EntityMatchMode.EXACT:
            entity_condition = "entity = %s"
            entity_param = entity
        else:  # ILIKE
            entity_condition = "entity ILIKE %s"
            entity_param = f"%{entity}%"

        query = f"""  # nosec
            SELECT COUNT(DISTINCT period) FROM financial_tables
            WHERE ({metric_condition})
            AND {entity_condition}
            AND period IS NOT NULL
        """
        cursor.execute(query, metric_params + [entity_param])
        period_count = cursor.fetchone()[0]

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
