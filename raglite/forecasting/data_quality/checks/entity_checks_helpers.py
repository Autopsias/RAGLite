"""Helper functions for entity-related data quality checks.

This module contains reusable SQL query builders and database utilities
for contamination and coverage checks.
"""

from __future__ import annotations

from typing import Any

from raglite.forecasting.data_quality.config import EntityMatchMode


def check_entity_column_has_normalized(cursor: Any) -> bool | int:
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


def build_metric_condition(aliases: list[str]) -> tuple[str, list[str]]:
    """Build SQL condition and parameters for metric matching.

    Args:
        aliases: List of metric aliases to search for

    Returns:
        Tuple of (SQL condition string, parameter list)
    """
    metric_condition = " OR ".join(["metric ILIKE %s"] * len(aliases))
    metric_params = [f"%{alias}%" for alias in aliases]
    return metric_condition, metric_params


def execute_exact_match_count(
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


def execute_fuzzy_match_count(
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


def get_contaminated_entities_sample(
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


def build_coverage_entity_condition(
    entity: str,
    canonical_entity: str,
    has_normalized: bool,
    match_mode: EntityMatchMode,
) -> tuple[str, str]:
    """Build SQL condition and parameter for entity matching in coverage check.

    Args:
        entity: Original entity name
        canonical_entity: Normalized entity name
        has_normalized: Whether entity_normalized column has data
        match_mode: Entity match mode (EXACT, ILIKE, ANY)

    Returns:
        Tuple of (SQL condition string, entity parameter)
    """
    if has_normalized and match_mode == EntityMatchMode.EXACT:
        # Use entity_normalized for exact match
        entity_condition = "entity_normalized = %s"
        entity_param = canonical_entity or entity
    elif match_mode == EntityMatchMode.EXACT:
        entity_condition = "entity = %s"
        entity_param = entity
    else:  # ILIKE
        entity_condition = "entity ILIKE %s"
        entity_param = f"%{entity}%"

    return entity_condition, entity_param


def execute_coverage_count_query(
    cursor: Any,
    metric_condition: str,
    metric_params: list[str],
    entity_condition: str,
    entity_param: str,
) -> int:
    """Execute query to count distinct periods for entity coverage.

    Args:
        cursor: PostgreSQL cursor
        metric_condition: SQL condition for metric matching
        metric_params: Parameters for metric condition
        entity_condition: SQL condition for entity matching
        entity_param: Parameter for entity condition

    Returns:
        Count of distinct periods
    """
    query = f"""  # nosec
        SELECT COUNT(DISTINCT period) FROM financial_tables
        WHERE ({metric_condition})
        AND {entity_condition}
        AND period IS NOT NULL
    """
    cursor.execute(query, metric_params + [entity_param])
    result = cursor.fetchone()[0]
    return int(result) if isinstance(result, int) else 0
