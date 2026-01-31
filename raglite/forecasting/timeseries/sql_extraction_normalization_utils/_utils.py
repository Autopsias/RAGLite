"""SQL extraction normalization utility functions.

Part of Story 8.1 refactoring to split sql_extraction.py.
Extracted from sql_extraction_normalization.py to meet file size limits.
"""

from collections import defaultdict
from datetime import datetime

from dateutil.relativedelta import relativedelta

from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

logger = get_logger(__name__)


def filter_year_end_only_points(
    points: list[TimeSeriesPoint], metric: str
) -> list[TimeSeriesPoint]:
    """Filter out year-end-only data points (years with only December data).

    Story 6.27: Years with only December data are unreliable.

    BUG FIX (2026-01-27): Previously counted points per year, which would
    incorrectly filter December when it was the only remaining point after
    YTD-to-monthly conversion, even if other months existed in raw data.
    Now properly detects years where December is the SOLE month in the dataset.

    Args:
        points: List of points to filter
        metric: Metric name for logging

    Returns:
        Filtered list of points
    """
    # Build month sets per year to properly identify year-end-only data
    year_to_months: dict[int, set[int]] = defaultdict(set)
    for p in points:
        year_to_months[p.date.year].add(p.date.month)

    # Identify the most recent year (preserve even if December-only)
    max_year = max(year_to_months.keys()) if year_to_months else None

    # Identify years where December is the ONLY month (unreliable year-end data)
    # EXCEPTION: Preserve most recent year - that data is valuable for forecasting
    dec_only_years = [
        yr
        for yr, months in year_to_months.items()
        if months == {12} and yr != max_year  # Preserve most recent year
    ]

    if dec_only_years:
        original_count = len(points)
        points = [p for p in points if p.date.year not in dec_only_years]
        logger.warning(
            f"Filtered {original_count - len(points)} year-end only points",
            extra={
                "metric": metric,
                "excluded_years": dec_only_years,
                "remaining_points": len(points),
            },
        )
    return points


def interpolate_missing_months(
    prev_date: datetime,
    curr_date: datetime,
    monthly_value: float,
) -> list[TimeSeriesPoint]:
    """Interpolate points for missing months within same year.

    Args:
        prev_date: Previous point date
        curr_date: Current point date
        monthly_value: Combined delta for gap period

    Returns:
        List of interpolated TimeSeriesPoint objects
    """
    months_gap = (curr_date.year - prev_date.year) * 12 + (curr_date.month - prev_date.month)

    # Only interpolate within same year and if gap > 1
    if months_gap > 1 and curr_date.year == prev_date.year:
        monthly_avg = monthly_value / months_gap
        logger.info(
            f"Detected {months_gap - 1} missing month(s), interpolating",
            extra={
                "gap_start": prev_date.strftime("%b-%y"),
                "gap_end": curr_date.strftime("%b-%y"),
                "combined_delta": monthly_value,
                "per_month_avg": monthly_avg,
            },
        )
        # Create synthetic points for missing months
        interpolated = []
        for gap_month_offset in range(1, months_gap):
            gap_date = prev_date + relativedelta(months=gap_month_offset)
            gap_label = gap_date.strftime("%b-%y")
            interpolated.append(
                TimeSeriesPoint(
                    date=gap_date,
                    value=monthly_avg,
                    label=f"{gap_label} Monthly (interpolated)",
                )
            )
        return interpolated
    return []
