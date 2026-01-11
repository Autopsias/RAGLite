"""SQL query builders for entity contamination checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from psycopg import Cursor


def build_contamination_count_queries(
    metric_condition: str,
    metric_params: Sequence[str],
    entity: str,
    canonical_entity: str,
    has_normalized: bool,
) -> tuple[str, list, str, list]:
    """Build SQL queries for exact and fuzzy match counts.

    Args:
        metric_condition: SQL condition for metric matching
        metric_params: Parameters for metric condition
        entity: Original entity name
        canonical_entity: Canonical entity name
        has_normalized: Whether entity_normalized column is available

    Returns:
        Tuple of (exact_query, exact_params, fuzzy_query, fuzzy_params)
    """
    if has_normalized:
        # Use entity_normalized for exact match (canonical form)
        exact_query = f"""  # nosec
            SELECT COUNT(*) FROM financial_tables
            WHERE ({metric_condition})
            AND entity_normalized = %s
        """
        exact_params = list(metric_params) + [canonical_entity or entity]
    else:
        # Fallback to entity column
        exact_query = f"""  # nosec
            SELECT COUNT(*) FROM financial_tables
            WHERE ({metric_condition})
            AND entity = %s
        """
        exact_params = list(metric_params) + [entity]

    # Count with fuzzy match (ILIKE on original entity column)
    fuzzy_query = f"""  # nosec
        SELECT COUNT(*) FROM financial_tables
        WHERE ({metric_condition})
        AND entity ILIKE %s
    """
    fuzzy_params = list(metric_params) + [f"%{entity}%"]

    return exact_query, exact_params, fuzzy_query, fuzzy_params


def build_contamination_sample_query(
    metric_condition: str,
    metric_params: Sequence[str],
    entity: str,
    canonical_entity: str,
    has_normalized: bool,
) -> tuple[str, list]:
    """Build SQL query to sample contaminated entities.

    Args:
        metric_condition: SQL condition for metric matching
        metric_params: Parameters for metric condition
        entity: Original entity name
        canonical_entity: Canonical entity name
        has_normalized: Whether entity_normalized column is available

    Returns:
        Tuple of (sample_query, sample_params)
    """
    if has_normalized:
        sample_query = f"""  # nosec
            SELECT DISTINCT entity FROM financial_tables
            WHERE ({metric_condition})
            AND entity ILIKE %s
            AND entity_normalized != %s
            LIMIT 5
        """
        sample_params = list(metric_params) + [f"%{entity}%", canonical_entity or entity]
    else:
        sample_query = f"""  # nosec
            SELECT DISTINCT entity FROM financial_tables
            WHERE ({metric_condition})
            AND entity ILIKE %s
            AND entity != %s
            LIMIT 5
        """
        sample_params = list(metric_params) + [f"%{entity}%", entity]

    return sample_query, sample_params


def execute_contamination_queries(
    cursor: Cursor,
    exact_query: str,
    exact_params: list,
    fuzzy_query: str,
    fuzzy_params: list,
    sample_query: str,
    sample_params: list,
) -> tuple[int, int, list[str]]:
    """Execute contamination check queries.

    Args:
        cursor: PostgreSQL cursor
        exact_query: SQL query for exact match count
        exact_params: Parameters for exact query
        fuzzy_query: SQL query for fuzzy match count
        fuzzy_params: Parameters for fuzzy query
        sample_query: SQL query for contaminated samples
        sample_params: Parameters for sample query

    Returns:
        Tuple of (exact_count, fuzzy_count, contaminated_entities)
    """
    # Execute exact count query
    cursor.execute(exact_query, exact_params)
    exact_count = cursor.fetchone()[0]

    # Execute fuzzy count query
    cursor.execute(fuzzy_query, fuzzy_params)
    fuzzy_count = cursor.fetchone()[0]

    # Execute sample query
    cursor.execute(sample_query, sample_params)
    contaminated_entities = [row[0] for row in cursor.fetchall()]

    return exact_count, fuzzy_count, contaminated_entities
