"""SQL query builders and executors for entity coverage checks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from raglite.forecasting.data_quality.config import EntityMatchMode

if TYPE_CHECKING:
    from collections.abc import Sequence

    from psycopg import Cursor


def build_coverage_query(
    metric_condition: str,
    metric_params: Sequence[str],
    entity: str,
    canonical_entity: str,
    has_normalized: bool,
    match_mode: EntityMatchMode,
) -> tuple[str, list[Any]]:
    """Build SQL query for entity coverage check.

    Args:
        metric_condition: SQL condition for metric matching
        metric_params: Parameters for metric condition
        entity: Original entity name
        canonical_entity: Canonical entity name
        has_normalized: Whether entity_normalized column is available
        match_mode: Entity match mode (EXACT, ILIKE, ANY)

    Returns:
        Tuple of (query_string, query_params)
    """
    # Build entity condition based on match mode
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

    query = f"""  # nosec
        SELECT COUNT(DISTINCT period) FROM financial_tables
        WHERE ({metric_condition})
        AND {entity_condition}
        AND period IS NOT NULL
    """
    query_params = list(metric_params) + [entity_param]

    return query, query_params


def execute_coverage_query(
    cursor: Cursor,
    query: str,
    query_params: list[Any],
) -> int:
    """Execute coverage check query.

    Args:
        cursor: PostgreSQL cursor
        query: SQL query string
        query_params: Query parameters

    Returns:
        Period count
    """
    cursor.execute(query, query_params)
    result = cursor.fetchone()[0]
    # Ensure we return an int, not Any
    assert isinstance(result, int), f"Expected int, got {type(result)}"
    return result
