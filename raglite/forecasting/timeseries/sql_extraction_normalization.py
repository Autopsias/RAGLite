"""SQL extraction data normalization and cleaning.

Part of Story 8.1 refactoring to split sql_extraction.py.
Handles YTD conversion, unit normalization, outlier filtering, and value transformations.
"""

from __future__ import annotations

from raglite.forecasting.timeseries.sql_extraction_config import (
    get_cost_metrics,
    get_ebitda_metrics,
    get_percentage_metrics,
)
from raglite.forecasting.timeseries.sql_extraction_normalization_utils import (
    apply_percentage_bounds,
    convert_cost_to_absolute,
    convert_ytd_to_monthly,
    deduplicate_points,
    normalize_ebitda_pre_ytd,
    normalize_units_and_filter_outliers,
)
from raglite.shared.models import TimeSeriesPoint


def normalize_timeseries_data(
    points: list[TimeSeriesPoint],
    metric: str,
    is_ytd_data: bool = False,
) -> list[TimeSeriesPoint]:
    """Apply all normalization steps to time-series data.

    Args:
        points: Raw time-series points
        metric: Metric name
        is_ytd_data: Whether data is in YTD cumulative format

    Returns:
        Normalized and cleaned time-series points
    """
    if not points:
        return points

    # Step 1: Deduplicate
    points = deduplicate_points(points, metric)

    # Step 2: EBITDA pre-YTD normalization
    if metric.lower() in get_ebitda_metrics() and is_ytd_data:
        points = normalize_ebitda_pre_ytd(points, metric)

    # Step 3: YTD → Monthly conversion
    if is_ytd_data and len(points) > 1:
        points = convert_ytd_to_monthly(points, metric)

    # Step 4: Unit normalization & outlier filtering (skip EBITDA - already done)
    points = normalize_units_and_filter_outliers(points, metric, skip_ebitda=True)

    # Step 5: Percentage bounds
    if metric.lower() in get_percentage_metrics():
        points = apply_percentage_bounds(points, metric)

    # Step 6: Cost absolute value conversion
    if metric.lower() in get_cost_metrics():
        points = convert_cost_to_absolute(points, metric)

    return points
