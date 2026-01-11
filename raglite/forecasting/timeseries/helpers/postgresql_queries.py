"""PostgreSQL query helpers for external data extraction (Story 8.1).

This module contains database query logic for extracting external
time series data from PostgreSQL.
"""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg2.extensions import cursor as PsycopgCursor


def query_external_data_points(
    cursor: "PsycopgCursor",
    source_name: str,
    metric_name: str,
) -> list[tuple[datetime, float, str]]:
    """Query external data points from PostgreSQL.

    Args:
        cursor: PostgreSQL cursor
        source_name: External data source name (e.g., "external_data_points")
        metric_name: Metric name within source (e.g., "ttf_gas")

    Returns:
        List of tuples (date, value, unit)

    Example:
        >>> cursor = conn.cursor()
        >>> rows = query_external_data_points(cursor, "external_data_points", "ttf_gas")
        >>> print(f"{len(rows)} data points")
    """
    query = """
        SELECT edp.date, edp.value, edp.unit
        FROM external_data_points edp
        JOIN external_data_sources eds ON edp.source_id = eds.id
        WHERE eds.source_name = %s
          AND edp.metric_name = %s
          AND edp.deleted_at IS NULL
        ORDER BY edp.date ASC
    """

    cursor.execute(query, (source_name, metric_name))
    results: list[tuple[datetime, float, str]] = cursor.fetchall()
    return results


def rows_to_timeseries_points(
    rows: list[tuple[datetime, float, str]],
) -> list[tuple[datetime, float, str]]:
    """Convert database rows to list of tuples for processing.

    Args:
        rows: List of database tuples (date, value, unit)

    Returns:
        List of tuples in same format (pass-through for now)

    Example:
        >>> points = rows_to_timeseries_points(db_rows)
        >>> for date, value, unit in points:
        ...     print(f"{date}: {value} {unit}")
    """
    return rows
