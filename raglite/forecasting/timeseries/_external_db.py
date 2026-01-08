"""Database query helpers for external timeseries extraction.

Part of Story 8.1 refactoring to split timeseries_extract.py.
Extracted from external.py to reduce function length.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from raglite.shared.models import TimeSeriesPoint

if TYPE_CHECKING:
    from psycopg import Cursor


def query_external_data_points(
    cursor: Cursor,
    source_name: str,
    metric_name: str,
) -> list[tuple[Any, ...]]:
    """Query external_data_points table for time series data.

    Args:
        cursor: PostgreSQL cursor
        source_name: External data source name (e.g., "external_data_points")
        metric_name: Metric name within source (e.g., "ttf_gas")

    Returns:
        List of tuples (date, value, unit)
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
    result = cursor.fetchall()
    # Ensure we return list[tuple[Any, ...]], not Any
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    return result


def convert_db_rows_to_points(rows: list[tuple[Any, ...]]) -> list[TimeSeriesPoint]:
    """Convert database rows to TimeSeriesPoint objects.

    Args:
        rows: List of tuples (date, value, unit) from database

    Returns:
        List of TimeSeriesPoint objects
    """
    points = []
    for date_val, value, unit in rows:
        # Convert date to datetime for consistency
        dt = datetime.combine(date_val, datetime.min.time())
        points.append(TimeSeriesPoint(date=dt, value=float(value), label=unit))
    return points
