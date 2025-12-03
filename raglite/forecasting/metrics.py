"""Metric discovery and availability checking for forecasting.

Story 5.0.4: Dynamic Metric Forecasting Support.
Provides list_available_metrics() to discover all financial metrics
in the database and determine which have sufficient data for forecasting.
"""

from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, Field

from raglite.forecasting.hybrid import MIN_DATA_POINTS
from raglite.shared.clients import get_postgresql_connection
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class MetricsCache(TypedDict):
    """Type definition for metrics cache."""

    last_fetch: datetime
    metrics: list["MetricInfo"]


# In-memory cache for metric list (configurable TTL via settings)
_metrics_cache: MetricsCache | None = None


def _get_cache_ttl() -> int:
    """Get cache TTL from settings (Story 5.0.4 Advisory: configurable TTL)."""
    return settings.metrics_cache_ttl_seconds


class MetricInfo(BaseModel):
    """Information about an available metric for forecasting.

    Story 5.0.4 AC1: Metric discovery model.

    Attributes:
        name: Metric name as stored in DB (e.g., "revenue", "ebitda")
        data_point_count: Number of data points available
        min_period: Earliest period string (e.g., "Aug-24", "2024-Q1")
        max_period: Latest period string (e.g., "Dec-25", "2025-Q4")
        can_forecast: True if >= MIN_DATA_POINTS (8) data points available

    Note:
        The financial_tables.period column stores VARCHAR period descriptions,
        not datetime values. Examples: "Aug-24", "YTD B Aug-25", "Total YTD Aug".
    """

    name: str = Field(..., description="Metric name as stored in DB")
    data_point_count: int = Field(..., description="Number of data points available")
    min_period: str | None = Field(None, description="Earliest period string")
    max_period: str | None = Field(None, description="Latest period string")
    can_forecast: bool = Field(..., description="True if >= 8 data points")


async def list_available_metrics(
    min_points: int = MIN_DATA_POINTS,
    use_cache: bool = True,
) -> list[MetricInfo]:
    """List all metrics available for forecasting.

    Story 5.0.4 AC1: Query financial_tables for unique metrics
    with data point counts.

    Args:
        min_points: Minimum points to set can_forecast=True (default 8)
        use_cache: Use cached results if available (default True)

    Returns:
        List of MetricInfo objects sorted by data_point_count desc

    Raises:
        ConnectionError: If PostgreSQL connection fails
        RuntimeError: If SQL query fails

    Example:
        >>> metrics = await list_available_metrics()
        >>> forecas table_metrics = [m for m in metrics if m.can_forecast]
        >>> print(f"Found {len(forecastable_metrics)} forecastable metrics")
    """
    global _metrics_cache

    # Check cache first (AC1.2: configurable TTL via settings)
    if use_cache and _metrics_cache is not None:
        cache_age = datetime.now() - _metrics_cache["last_fetch"]
        if cache_age.total_seconds() < _get_cache_ttl():
            logger.info(
                "Returning cached metrics list",
                extra={
                    "cache_age_seconds": cache_age.total_seconds(),
                    "metric_count": len(_metrics_cache["metrics"]),
                },
            )
            return _metrics_cache["metrics"]

    logger.info("Fetching available metrics from database", extra={"min_points": min_points})

    # Query PostgreSQL for unique metrics with counts
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # AC1: SQL query for unique metrics with data point counts and date ranges
        query = """
            SELECT
                metric,
                COUNT(*) as data_point_count,
                MIN(period) as min_date,
                MAX(period) as max_date
            FROM financial_tables
            WHERE metric IS NOT NULL
            GROUP BY metric
            ORDER BY data_point_count DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        # Build MetricInfo objects
        metrics = []
        for row in rows:
            metric_name, count, min_period, max_period = row
            can_forecast = count >= min_points

            metrics.append(
                MetricInfo(
                    name=metric_name,
                    data_point_count=count,
                    min_period=min_period,
                    max_period=max_period,
                    can_forecast=can_forecast,
                )
            )

        logger.info(
            "Metrics discovery complete",
            extra={
                "total_metrics": len(metrics),
                "forecastable_metrics": sum(1 for m in metrics if m.can_forecast),
                "min_points_threshold": min_points,
            },
        )

        # Update cache (AC1.2: configurable TTL via settings.metrics_cache_ttl_seconds)
        _metrics_cache = {"last_fetch": datetime.now(), "metrics": metrics}

        return metrics

    except Exception as e:
        logger.error(
            "Failed to fetch metrics from database",
            extra={"error": str(e), "query": query},
            exc_info=True,
        )
        raise RuntimeError(f"Metric discovery query failed: {e}") from e

    finally:
        cursor.close()


def clear_metrics_cache() -> None:
    """Clear the in-memory metrics cache.

    Useful for testing or when database has been updated with new metrics.

    Story 5.0.4 AC1.2: Cache management.
    """
    global _metrics_cache
    _metrics_cache = None
    logger.info("Metrics cache cleared")
