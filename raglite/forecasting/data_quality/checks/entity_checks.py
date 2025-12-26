"""Entity-related data quality checks.

Checks for entity contamination (fuzzy vs exact match leakage) and coverage.
"""

from __future__ import annotations

import pandas as pd

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.forecasting.data_quality.config import (
    EntityMatchMode,
    VariableQualityConfig,
)
from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


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
        metric_condition = " OR ".join(["metric ILIKE %s"] * len(aliases))
        metric_params = [f"%{alias}%" for alias in aliases]

        # Story 6.28: Use entity_normalized column if available for exact matches
        # This avoids contamination by matching on normalized canonical entities
        from raglite.ingestion.entity_normalizer import normalize_entity

        canonical_entity = normalize_entity(entity)

        # Count with exact match on entity_normalized (if available) or entity
        # First check if entity_normalized column exists and has data
        check_normalized_query = """
            SELECT COUNT(*) FROM financial_tables WHERE entity_normalized IS NOT NULL LIMIT 1
        """
        cursor.execute(check_normalized_query)
        has_normalized = cursor.fetchone()[0] > 0

        if has_normalized:
            # Use entity_normalized for exact match (canonical form)
            exact_query = f"""  # nosec
                SELECT COUNT(*) FROM financial_tables
                WHERE ({metric_condition})
                AND entity_normalized = %s
            """
            cursor.execute(exact_query, metric_params + [canonical_entity or entity])
            exact_count = cursor.fetchone()[0]
        else:
            # Fallback to entity column
            exact_query = f"""  # nosec
                SELECT COUNT(*) FROM financial_tables
                WHERE ({metric_condition})
                AND entity = %s
            """
            cursor.execute(exact_query, metric_params + [entity])
            exact_count = cursor.fetchone()[0]

        # Count with fuzzy match (ILIKE on original entity column)
        fuzzy_query = f"""  # nosec
            SELECT COUNT(*) FROM financial_tables
            WHERE ({metric_condition})
            AND entity ILIKE %s
        """
        cursor.execute(fuzzy_query, metric_params + [f"%{entity}%"])
        fuzzy_count = cursor.fetchone()[0]

        # Get sample of contaminated entities (those that match fuzzy but not exact)
        if has_normalized:
            sample_query = f"""  # nosec
                SELECT DISTINCT entity FROM financial_tables
                WHERE ({metric_condition})
                AND entity ILIKE %s
                AND entity_normalized != %s
                LIMIT 5
            """
            cursor.execute(
                sample_query, metric_params + [f"%{entity}%", canonical_entity or entity]
            )
        else:
            sample_query = f"""  # nosec
                SELECT DISTINCT entity FROM financial_tables
                WHERE ({metric_condition})
                AND entity ILIKE %s
                AND entity != %s
                LIMIT 5
            """
            cursor.execute(sample_query, metric_params + [f"%{entity}%", entity])
        contaminated_entities = [row[0] for row in cursor.fetchall()]

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

    # Evaluate contamination
    if fuzzy_count == 0 and exact_count == 0:
        return CheckResult(
            check_name="entity_contamination",
            status=CheckStatus.WARN,
            message=f"No data found for entity '{entity}'",
            variable=variable,
            actual_value=0,
            severity=2,
        )

    # Calculate contamination ratio
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
