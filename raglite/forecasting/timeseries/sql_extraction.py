"""Timeseries extraction - SQL-based extraction.

Part of Story 8.1 refactoring to split timeseries_extract.py.

This module is now a facade that re-exports functionality from:
- sql_extraction_execution: SQL query execution and configuration
- sql_extraction_response: Response handling, validation, finalization
"""

from raglite.forecasting.timeseries.metadata import (
    ExtractionError,
    MetricValidationError,
)
from raglite.forecasting.timeseries.sql_extraction_config import (
    prefer_group_level,  # Re-export for backward compatibility
)
from raglite.forecasting.timeseries.sql_extraction_execution import (
    build_entity_filter_clause,
    configure_extraction,
    execute_sql_with_fallback,
)
from raglite.forecasting.timeseries.sql_extraction_parsing import (
    parse_sql_rows_with_units,
)
from raglite.forecasting.timeseries.sql_extraction_response import (
    finalize_timeseries,
    handle_extraction_failure,
    suggest_available_metrics,
    validate_minimum_points,
)
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData

# Re-export for backward compatibility
__all__ = ["extract_timeseries_from_sql", "prefer_group_level"]

logger = get_logger(__name__)


def _handle_transaction_error(metric: str, error: Exception) -> None:
    """Handle PostgreSQL transaction abort errors by resetting connection."""
    error_msg = str(error).lower()
    if "transaction" in error_msg and "aborted" in error_msg:
        logger.warning(
            "PostgreSQL transaction aborted - resetting connection", extra={"metric": metric}
        )
        from raglite.shared.clients import reset_postgresql_connection

        reset_postgresql_connection()


async def extract_timeseries_from_sql(
    metric: str = "revenue",
    min_points: int = 6,
    aggregation: str = "sum",
    entity: str | None = None,
) -> TimeSeriesData:
    """Extract time-series data from PostgreSQL financial_tables.

    Args:
        metric: Metric name to extract (e.g., "revenue", "expenses", "ebitda")
        min_points: Minimum number of data points required (default: 6)
        aggregation: "sum" (default) or "max" - aggregation method for multiple values per period
        entity: Optional entity filter (e.g., "portugal", "tunisia", "brazil")

    Returns:
        TimeSeriesData with metric_name, chronologically sorted points, interval

    Raises:
        ExtractionError: If insufficient data (<min_points) or SQL query fails
    """
    metric_search, aggregation, ENTITY_FILTERS = configure_extraction(metric, aggregation, entity)

    logger.info(
        "Extracting time-series from SQL",
        extra={"metric": metric, "metric_search": metric_search, "min_points": min_points},
    )

    try:
        entity_filter, prefer_ytd = build_entity_filter_clause(metric_search, ENTITY_FILTERS)
        rows = await execute_sql_with_fallback(
            metric, metric_search, entity_filter, prefer_ytd, aggregation
        )

        if not rows:
            logger.warning("No SQL data found for metric", extra={"metric": metric})
            await suggest_available_metrics(metric, min_points)

        # Phase 2 data quality: Use unit-aware parsing
        parsed = parse_sql_rows_with_units(rows, metric)
        points = parsed.points
        units = parsed.units
        source_documents = parsed.source_documents
        is_ytd_data = parsed.is_ytd_data

        if not points:
            raise ExtractionError(
                f"No valid data points could be parsed from SQL for metric '{metric}'"
            )

        await validate_minimum_points(points, metric, min_points)
        return finalize_timeseries(points, metric, is_ytd_data, source_documents, units)

    except (MetricValidationError, ExtractionError) as e:
        return await handle_extraction_failure(e, metric, min_points)

    except Exception as e:
        _handle_transaction_error(metric, e)
        logger.error(
            "SQL extraction failed", extra={"metric": metric, "error": str(e)}, exc_info=True
        )
        raise ExtractionError(f"SQL query failed: {e}") from e
