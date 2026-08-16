"""Internal metric regressor fetching.

EBITDA forecast fix (2026-02-03): Internal metrics like revenue have high
correlation with profit metrics. This module provides functions to fetch
historical values of internal metrics to use as regressors.

This is part of the regressor_fetch module split to maintain file size limits.
"""

from __future__ import annotations

import pandas as pd

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# EBITDA forecast fix: Internal metrics that can serve as regressors for profit metrics
# Revenue has high correlation with EBITDA (EBITDA ≈ f(Revenue, Costs))
# Construction industry: Revenue correlates with construction market and licenses
INTERNAL_REGRESSOR_MAPPINGS = {
    "ebitda": ["revenue", "turnover", "sales_volume"],
    "ebitda ifrs": ["revenue", "turnover", "sales_volume"],
    "net_income": ["revenue", "ebitda", "turnover"],
    "operating_profit": ["revenue", "ebitda"],
    "gross_profit": ["revenue", "sales_volume"],
}


async def fetch_internal_metric_as_regressor(
    internal_metric: str,
    target_metric: str,
    entity: str | None = None,
) -> pd.Series | None:
    """Fetch an internal metric from database to use as a regressor.

    EBITDA forecast fix (2026-02-03): Internal metrics like revenue have high
    correlation with profit metrics. This function fetches historical values
    of an internal metric to use as a regressor.

    Args:
        internal_metric: Name of internal metric to fetch (e.g., "revenue")
        target_metric: Target metric being forecast (to avoid self-reference)
        entity: Optional entity filter (e.g., "GROUP", "Portugal")

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    # Avoid self-reference
    if internal_metric.lower() == target_metric.lower():
        logger.debug(f"Skipping self-reference: {internal_metric} == {target_metric}")
        return None

    try:
        from raglite.forecasting.timeseries.sql_extraction import extract_timeseries_from_sql

        # Extract internal metric data from database
        timeseries = await extract_timeseries_from_sql(
            metric=internal_metric,
            min_points=6,
            aggregation="sum",
            entity=entity,
        )

        if not timeseries.points:
            logger.warning(
                f"No data for internal regressor {internal_metric}",
                extra={"metric": internal_metric, "target": target_metric},
            )
            return None

        # Convert to pandas Series with datetime index
        dates = [p.date for p in timeseries.points]
        values = [p.value for p in timeseries.points]
        series = pd.Series(values, index=pd.DatetimeIndex(dates), name=internal_metric)

        logger.info(
            f"Fetched internal regressor {internal_metric}",
            extra={
                "regressor": internal_metric,
                "target": target_metric,
                "points": len(series),
                "date_range": f"{series.index.min()} to {series.index.max()}",
            },
        )

        return series

    except Exception as e:
        logger.warning(
            f"Failed to fetch internal regressor {internal_metric}: {e}",
            extra={"metric": internal_metric, "target": target_metric, "error": str(e)},
        )
        return None


async def fetch_internal_regressors_for_metric(
    metric: str,
    entity: str | None = None,
) -> dict[str, pd.Series]:
    """Fetch internal metrics as regressors for a target metric.

    EBITDA forecast fix (2026-02-03): For profit metrics, internal metrics like
    revenue often have high correlation and can improve forecast accuracy.

    Args:
        metric: Target metric (e.g., "ebitda", "net_income")
        entity: Optional entity filter

    Returns:
        Dict of internal regressor name -> pandas Series
    """
    metric_lower = metric.lower().strip()

    # Get configured internal regressors for this metric
    internal_regressors = INTERNAL_REGRESSOR_MAPPINGS.get(metric_lower, [])

    if not internal_regressors:
        logger.debug(f"No internal regressors configured for {metric}")
        return {}

    logger.info(
        f"Fetching internal regressors for {metric}",
        extra={
            "target_metric": metric,
            "internal_regressors": internal_regressors,
            "entity": entity,
        },
    )

    # Fetch all internal regressors
    results: dict[str, pd.Series] = {}
    for internal_metric in internal_regressors:
        series = await fetch_internal_metric_as_regressor(
            internal_metric=internal_metric,
            target_metric=metric,
            entity=entity,
        )
        if series is not None and len(series) > 0:
            results[f"internal_{internal_metric}"] = series  # Prefix to distinguish

    logger.info(
        "Internal regressor fetch complete",
        extra={
            "target_metric": metric,
            "requested": len(internal_regressors),
            "successful": len(results),
            "regressors": list(results.keys()),
        },
    )

    return results
