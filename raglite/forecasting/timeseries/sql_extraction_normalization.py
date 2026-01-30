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
    filter_bimodal_cost_to_dominant_sign,
    normalize_by_unit,
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

    # Step 2: Filter bimodal cost distributions EARLY (before outlier removal)
    # Phase 4 Quality Fix (2026-01-29): Moved from Step 6 to preserve true distribution
    # percentages (63% negative / 36% positive) before statistical filtering changes them
    if metric.lower() in get_cost_metrics():
        points = filter_bimodal_cost_to_dominant_sign(points, metric)

    # Step 3: EBITDA outlier normalization
    # Phase 9 Fix (2026-01-29): Run MAD filtering for non-YTD EBITDA data
    # Root cause: EBITDA config has prefer_ytd=False, but with monthly data the
    # 335x swing ratio (annual 960M vs monthly 2-15M) caused data rejection
    # For YTD data: Skip MAD filtering - YTD→monthly conversion handles outliers
    # For non-YTD data: Apply MAD filtering to catch annual values mixed with monthly
    if metric.lower() in get_ebitda_metrics() and not is_ytd_data:
        points = normalize_ebitda_pre_ytd(points, metric)

    # Step 4: YTD → Monthly conversion (was Step 3)
    if is_ytd_data and len(points) > 1:
        points = convert_ytd_to_monthly(points, metric)

    # Step 5: Unit normalization & outlier filtering (was Step 4, skip EBITDA - already done)
    points = normalize_units_and_filter_outliers(points, metric, skip_ebitda=True)

    # Step 6: Percentage bounds (was Step 5)
    if metric.lower() in get_percentage_metrics():
        points = apply_percentage_bounds(points, metric)

    # Step 7: Cost absolute value conversion (unchanged)
    if metric.lower() in get_cost_metrics():
        points = convert_cost_to_absolute(points, metric)

    return points


def normalize_timeseries_with_units(
    points: list[TimeSeriesPoint],
    units: list[str | None],
    metric: str,
    is_ytd_data: bool = False,
) -> list[TimeSeriesPoint]:
    """Apply all normalization steps with explicit unit-based scaling.

    Phase 2 data quality: Uses unit metadata from database for normalization
    instead of value-based heuristics where possible.

    Args:
        points: Raw time-series points
        units: List of unit strings (parallel to points)
        metric: Metric name
        is_ytd_data: Whether data is in YTD cumulative format

    Returns:
        Normalized and cleaned time-series points
    """
    if not points:
        return points

    # Step 0: Apply unit-based normalization FIRST (before any other processing)
    # This is the key Phase 2 improvement - explicit units trump heuristics
    if units and len(units) == len(points):
        points = normalize_by_unit(points, units, metric)
        # After unit normalization, units list is no longer parallel
        # Reset for downstream processing
        units = [None] * len(points)

    # Step 1: Deduplicate
    points = deduplicate_points(points, metric)

    # Step 2: Filter bimodal cost distributions EARLY (before outlier removal)
    # Phase 4 Quality Fix (2026-01-29): Moved from Step 6 to preserve true distribution
    # percentages (63% negative / 36% positive) before statistical filtering changes them
    if metric.lower() in get_cost_metrics():
        points = filter_bimodal_cost_to_dominant_sign(points, metric)

    # Step 3: EBITDA MAD-based outlier filtering (non-YTD data only)
    # Phase 9 Fix (2026-01-29): Apply MAD filtering for non-YTD EBITDA data
    # Root cause: 335x swing ratio (annual 960M EUR vs monthly 2-15M EUR) caused rejection
    # For YTD data: Skip MAD filtering - YTD→monthly conversion handles outliers
    # For non-YTD data: Apply MAD filtering to catch annual values mixed with monthly
    if metric.lower() in get_ebitda_metrics() and not is_ytd_data:
        points = normalize_ebitda_pre_ytd(points, metric)

    # Step 4: YTD → Monthly conversion
    if is_ytd_data and len(points) > 1:
        points = convert_ytd_to_monthly(points, metric)

    # Step 5: Skip value-based unit normalization (already done with explicit units)
    # Only apply statistical outlier filtering (was Step 4)
    if len(points) >= 6 and metric.lower() not in get_ebitda_metrics():
        from raglite.forecasting.timeseries.sql_extraction_normalization_utils._normalization import (
            _filter_statistical_outliers,
        )

        points = _filter_statistical_outliers(points, metric)

    # Step 6: Percentage bounds (was Step 5)
    if metric.lower() in get_percentage_metrics():
        points = apply_percentage_bounds(points, metric)

    # Step 7: Cost absolute value conversion (unchanged)
    if metric.lower() in get_cost_metrics():
        points = convert_cost_to_absolute(points, metric)

    return points
