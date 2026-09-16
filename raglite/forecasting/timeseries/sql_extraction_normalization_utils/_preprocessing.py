"""Preprocessing utilities for time-series data."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from raglite.shared.models import TimeSeriesPoint  # noqa: E402

from ._utils import filter_year_end_only_points, interpolate_missing_months  # noqa: E402


def deduplicate_points(points: list[TimeSeriesPoint], metric: str) -> list[TimeSeriesPoint]:
    """Deduplicate time-series points by date.

    Multi-year documents create duplicate dates when same period extracted multiple times.
    Aggregate by taking the value with largest absolute magnitude (most authoritative).

    Args:
        points: List of time-series points that may contain duplicates
        metric: Metric name for logging

    Returns:
        Deduplicated list of points
    """
    date_to_points: dict[datetime, list[TimeSeriesPoint]] = defaultdict(list)
    for p in points:
        date_to_points[p.date].append(p)

    if len(date_to_points) < len(points):
        # Duplicates detected - aggregate them
        # Log warning if needed

        deduplicated = []
        for date_val in sorted(date_to_points.keys()):
            date_points = date_to_points[date_val]
            # Take point with largest absolute value
            best_point = max(date_points, key=lambda p: abs(p.value) if p.value is not None else 0)
            deduplicated.append(best_point)

        return deduplicated

    return points


def convert_ytd_to_monthly(points: list[TimeSeriesPoint], metric: str) -> list[TimeSeriesPoint]:
    """Convert YTD cumulative values to monthly deltas.

    YTD values accumulate: Feb=23M, Mar=39M, Apr=51M
    Prophet needs periodic values: Feb=23M, Mar=16M (39-23), Apr=12M (51-39)

    Story 6.27: Filters out year-end-only data points (Dec only years).

    Fix 2026-02-03: When first YTD of a year is not January, distribute the
    cumulative value evenly across Jan-to-current months instead of assigning
    the full cumulative to the single month. This prevents inflated values like
    50.71M for Apr-25 (YTD) being treated as a single monthly value.

    Args:
        points: List of YTD cumulative points
        metric: Metric name for logging

    Returns:
        List of monthly delta points
    """
    if len(points) <= 1:
        return points

    # Filter year-end only data points
    points = filter_year_end_only_points(points, metric)

    # Log conversion info if needed

    monthly_points = []
    prev_ytd = 0.0
    prev_date = None

    for p in points:
        # Calculate monthly value (handle year boundaries)
        if prev_date is not None:
            if p.date.year != prev_date.year:
                # Year boundary crossed - reset YTD accumulator
                prev_ytd = 0.0
                # Fix 2026-02-03: If this is not January, distribute YTD across months
                if p.date.month > 1:
                    # First YTD of year is not January - distribute evenly
                    months_in_ytd = p.date.month
                    monthly_value = p.value / months_in_ytd
                    # Create synthetic points for Jan through (month-1)

                    for m in range(1, p.date.month):
                        synth_date = p.date.replace(month=m, day=1)
                        monthly_points.append(
                            TimeSeriesPoint(
                                date=synth_date,
                                value=monthly_value,
                                label=f"{synth_date.strftime('%b-%y')} Monthly (distributed from YTD)",
                            )
                        )
                else:
                    monthly_value = p.value
            else:
                monthly_value = p.value - prev_ytd
        else:
            # First point ever - check if it's not January
            if p.date.month > 1:
                # First YTD is not January - distribute evenly
                months_in_ytd = p.date.month
                monthly_value = p.value / months_in_ytd
                # Create synthetic points for Jan through (month-1)
                for m in range(1, p.date.month):
                    synth_date = p.date.replace(month=m, day=1)
                    monthly_points.append(
                        TimeSeriesPoint(
                            date=synth_date,
                            value=monthly_value,
                            label=f"{synth_date.strftime('%b-%y')} Monthly (distributed from YTD)",
                        )
                    )
            else:
                monthly_value = p.value

        # Interpolate missing months if needed
        if prev_date is not None:
            interpolated = interpolate_missing_months(prev_date, p.date, monthly_value)
            if interpolated:
                monthly_points.extend(interpolated)
                # Use per-month average from interpolation
                monthly_value = interpolated[0].value

        prev_ytd = p.value
        prev_date = p.date

        # Add current point with updated label
        period_label = p.label.split(" (")[0] if p.label and " (" in p.label else (p.label or "")
        monthly_points.append(
            TimeSeriesPoint(
                date=p.date,
                value=monthly_value,
                label=f"{period_label} Monthly (converted from YTD)",
            )
        )

    return monthly_points
