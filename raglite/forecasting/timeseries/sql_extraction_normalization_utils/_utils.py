"""SQL extraction normalization utility functions.

Part of Story 8.1 refactoring to split sql_extraction.py.
Extracted from sql_extraction_normalization.py to meet file size limits.
"""

from collections import Counter
from datetime import datetime

from dateutil.relativedelta import relativedelta

from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

logger = get_logger(__name__)


def filter_year_end_only_points(
    points: list[TimeSeriesPoint], metric: str
) -> list[TimeSeriesPoint]:
    """Filter out year-end-only data points (Dec only years).

    Story 6.27: Years with only December data are unreliable.

    Args:
        points: List of points to filter
        metric: Metric name for logging

    Returns:
        Filtered list of points
    """
    year_month_counts = Counter(p.date.year for p in points)
    single_point_years = {yr for yr, cnt in year_month_counts.items() if cnt == 1}

    if single_point_years:
        dec_only_years = [
            yr
            for yr in single_point_years
            if any(p.date.year == yr and p.date.month == 12 for p in points)
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
