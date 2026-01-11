"""Extraction routing for forecast data by variable type.

Story 7b-6 AC-7b.6.3: Unified extraction for all variable types.
This module routes data extraction based on the variable configuration
(internal/external_db/external_api).
"""

from raglite.forecasting.model_selection_job_config import VARIABLE_CONFIG
from raglite.forecasting.timeseries import (
    ExtractionError,
    extract_external_regressor_timeseries,
    extract_external_timeseries,
    extract_timeseries_from_sql,
)
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData

logger = get_logger(__name__)


def resolve_variable_alias(metric: str) -> str:
    """Resolve variable alias to normalized name for cache/config lookup.

    Epic 7 Fix: Ensures MCP queries using DB aliases (e.g., "Turnover+VAT")
    are normalized to cache keys (e.g., "revenue") for model selection lookup.

    Args:
        metric: Raw metric name (may be an alias like "Turnover+VAT")

    Returns:
        Normalized variable name for cache/config lookup (e.g., "revenue")

    Examples:
        >>> resolve_variable_alias("Turnover+VAT")
        "revenue"
        >>> resolve_variable_alias("EBITDA")
        "ebitda"
        >>> resolve_variable_alias("revenue")
        "revenue"
    """
    metric_lower = metric.lower()

    # Direct match in VARIABLE_CONFIG?
    if metric_lower in VARIABLE_CONFIG:
        return metric_lower

    # Search aliases for reverse lookup
    for var_name, config in VARIABLE_CONFIG.items():
        aliases = config.get("aliases", [])
        for alias in aliases:
            if alias.lower() == metric_lower:
                logger.debug(
                    "Resolved variable alias",
                    extra={"original": metric, "normalized": var_name},
                )
                return var_name

    # No match - return lowercased original
    return metric_lower


async def extract_historical_data_by_type(
    metric: str,
    min_points: int = 6,
) -> TimeSeriesData | None:
    """Route extraction based on variable type (internal/external_db/external_api).

    This function matches the routing logic in model_selection_job.fetch_historical_data()
    to ensure MCP forecasts can access the same data sources as model selection.

    Args:
        metric: Metric name to extract
        min_points: Minimum data points required

    Returns:
        TimeSeriesData if extraction succeeds, None otherwise

    Raises:
        ExtractionError: If extraction fails for known variable types
    """
    config = VARIABLE_CONFIG.get(metric.lower())

    if config is None:
        # Unknown metric - try SQL first (existing behavior)
        logger.info(
            "Unknown metric, using SQL extraction",
            extra={"metric": metric, "var_type": "unknown"},
        )
        return await extract_timeseries_from_sql(metric=metric, min_points=min_points)

    var_type = config.get("type", "internal")
    metric_name = config.get("metric_name", metric)

    logger.info(
        "Routing extraction by variable type",
        extra={"metric": metric, "var_type": var_type, "metric_name": metric_name},
    )

    if var_type == "internal":
        # Internal SECIL metrics from PostgreSQL financial_tables
        return await extract_timeseries_from_sql(metric=metric_name, min_points=min_points)

    elif var_type == "external_db":
        # External database metrics from PostgreSQL external_data_points
        ts_data = await extract_external_timeseries(metric=metric_name, min_points=min_points)
        if ts_data is None:
            raise ExtractionError(f"No external_db data found for {metric_name}")
        return ts_data

    elif var_type == "external_api":
        # External API metrics (ECB, Eurostat, REN, etc.)
        ts_data = await extract_external_regressor_timeseries(
            metric=metric_name, min_points=min_points
        )
        if ts_data is None:
            raise ExtractionError(f"No external_api data found for {metric_name}")
        return ts_data

    else:
        # Unknown type - fallback to SQL
        logger.warning(
            "Unknown variable type, falling back to SQL",
            extra={"metric": metric, "var_type": var_type},
        )
        return await extract_timeseries_from_sql(metric=metric, min_points=min_points)
