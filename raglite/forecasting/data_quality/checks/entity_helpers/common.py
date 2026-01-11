"""Common helper functions for entity checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from raglite.ingestion.entity_normalizer import normalize_entity

if TYPE_CHECKING:
    from psycopg import Cursor


def check_entity_normalization_available(cursor: Cursor) -> bool:
    """Check if entity_normalized column has data.

    Args:
        cursor: PostgreSQL cursor

    Returns:
        True if entity_normalized column has data
    """
    check_normalized_query = """
        SELECT COUNT(*) FROM financial_tables WHERE entity_normalized IS NOT NULL LIMIT 1
    """
    cursor.execute(check_normalized_query)
    result = cursor.fetchone()[0]
    # Ensure we return bool, not Any
    assert isinstance(result, int), f"Expected int, got {type(result)}"
    return result > 0


def get_canonical_entity(entity: str) -> str:
    """Get canonical entity name using normalizer.

    Args:
        entity: Raw entity name

    Returns:
        Canonical entity name or original if normalization fails
    """
    canonical = normalize_entity(entity)
    return canonical or entity


def build_metric_condition(aliases: list[str]) -> tuple[str, list[str]]:
    """Build SQL condition and params for metric matching.

    Args:
        aliases: List of metric aliases

    Returns:
        Tuple of (SQL condition string, parameter list)
    """
    metric_condition = " OR ".join(["metric ILIKE %s"] * len(aliases))
    metric_params = [f"%{alias}%" for alias in aliases]
    return metric_condition, metric_params
