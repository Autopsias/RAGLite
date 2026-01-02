"""SQL extraction data normalization and cleaning.

Part of Story 8.1 refactoring to split sql_extraction.py.
Handles YTD conversion, unit normalization, outlier filtering, and value transformations.
"""

import statistics
from collections import defaultdict
from datetime import datetime

from raglite.forecasting.timeseries.sql_extraction_config import (
    get_cost_metrics,
    get_ebitda_metrics,
    get_percentage_metrics,
)
from raglite.forecasting.timeseries.sql_extraction_normalization_utils import (
    filter_year_end_only_points,
    interpolate_missing_months,
)
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

logger = get_logger(__name__)


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
        logger.warning(
            "Duplicate dates detected - aggregating by largest magnitude",
            extra={
                "metric": metric,
                "total_points": len(points),
                "unique_dates": len(date_to_points),
                "duplicates_removed": len(points) - len(date_to_points),
            },
        )

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

    logger.info(
        "Converting YTD cumulative to monthly deltas",
        extra={
            "metric": metric,
            "points_count": len(points),
            "ytd_values": [f"€{p.value:.1f}M" for p in points[:5]],
        },
    )

    monthly_points = []
    prev_ytd = 0.0
    prev_date = None

    for p in points:
        # Calculate monthly value (handle year boundaries)
        if prev_date is not None:
            if p.date.year != prev_date.year:
                logger.info(
                    f"Year boundary: {prev_date.strftime('%b-%y')} → {p.date.strftime('%b-%y')} - resetting baseline",
                    extra={
                        "prev_year": prev_date.year,
                        "curr_year": p.date.year,
                        "prev_ytd": prev_ytd,
                    },
                )
                prev_ytd = 0.0
                monthly_value = p.value
            else:
                monthly_value = p.value - prev_ytd
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

        logger.debug(
            f"YTD→Monthly: {period_label} YTD €{p.value:.1f}M → Monthly €{monthly_value:.1f}M",
            extra={"period": period_label, "ytd": p.value, "monthly": monthly_value},
        )

    logger.info(
        "YTD→Monthly conversion complete",
        extra={
            "metric": metric,
            "monthly_values": [f"€{p.value:.1f}M" for p in monthly_points[:5]],
        },
    )

    return monthly_points


def normalize_ebitda_pre_ytd(points: list[TimeSeriesPoint], metric: str) -> list[TimeSeriesPoint]:
    """Normalize EBITDA mixed units BEFORE YTD conversion.

    Story 6.25.1: EBITDA has mixed units - kEUR vs EUR millions.
    Must normalize before YTD→monthly conversion to avoid garbage deltas.

    Args:
        points: List of EBITDA points
        metric: Metric name for logging

    Returns:
        Normalized points with consistent EUR millions units
    """
    EBITDA_KEUR_THRESHOLD = 10000  # Values > 10000 are in kEUR
    EBITDA_MAX_REASONABLE = 500  # Max YTD EBITDA in EUR millions

    # Step 1: Normalize kEUR → EUR millions
    normalized_points = []
    keur_count = 0
    for p in points:
        if p.value is None:
            continue
        if abs(p.value) > EBITDA_KEUR_THRESHOLD:
            normalized_val = p.value / 1000
            keur_count += 1
            logger.info(
                f"Pre-YTD normalization (kEUR→M): {p.value:.0f} → {normalized_val:.2f}",
                extra={
                    "metric": metric,
                    "date": p.date.strftime("%Y-%m-%d"),
                    "original": p.value,
                    "normalized": normalized_val,
                },
            )
            normalized_points.append(
                TimeSeriesPoint(date=p.date, value=normalized_val, label=f"{p.label} (kEUR→M EUR)")
            )
        else:
            normalized_points.append(p)

    if keur_count > 0:
        logger.info(
            f"Pre-YTD normalization: {keur_count}/{len(points)} values converted from kEUR",
            extra={"metric": metric, "keur_count": keur_count, "total": len(points)},
        )

    # Step 2: Filter extreme outliers
    filtered_points = []
    filtered_count = 0
    for p in normalized_points:
        if p.value is not None and abs(p.value) > EBITDA_MAX_REASONABLE:
            logger.warning(
                f"Filtered extreme EBITDA outlier: {p.value:.1f}M EUR (max: {EBITDA_MAX_REASONABLE}M)",
                extra={"metric": metric, "date": p.date.strftime("%Y-%m-%d"), "value": p.value},
            )
            filtered_count += 1
        else:
            filtered_points.append(p)

    if filtered_count > 0:
        logger.info(
            f"Filtered {filtered_count} extreme outliers before YTD conversion",
            extra={"metric": metric, "filtered": filtered_count, "remaining": len(filtered_points)},
        )

    return filtered_points


def normalize_units_and_filter_outliers(
    points: list[TimeSeriesPoint], metric: str, skip_ebitda: bool = False
) -> list[TimeSeriesPoint]:
    """Normalize unit inconsistencies and filter extreme outliers.

    Story 6.23: Handles mixed units (kEUR vs EUR) and data corruption.

    Args:
        points: List of points to normalize
        metric: Metric name for logging
        skip_ebitda: If True, skip EBITDA (handled separately pre-YTD)

    Returns:
        Normalized and filtered points
    """
    if not points or len(points) < 6:
        return points

    if skip_ebitda and metric.lower() in get_ebitda_metrics():
        return points

    values = [abs(p.value) for p in points if p.value is not None]
    if not values:
        return points

    median_value = statistics.median(values)

    # Step 1: Normalize unit inconsistencies (kEUR → EUR)
    normalized_points = []
    for p in points:
        if p.value is None:
            continue

        abs_val = abs(p.value)
        ratio = abs_val / median_value if median_value > 0 else 0

        if ratio > 5.0:
            # Likely kEUR → EUR conversion needed
            normalized_value = p.value / 1000
            logger.info(
                f"Normalized kEUR to EUR: {p.value:.0f} → {normalized_value:.2f} ({ratio:.1f}x median)",
                extra={
                    "metric": metric,
                    "date": p.date.strftime("%Y-%m-%d"),
                    "original": p.value,
                    "normalized": normalized_value,
                    "ratio": ratio,
                },
            )
            normalized_points.append(
                TimeSeriesPoint(
                    date=p.date,
                    value=normalized_value,
                    label=f"{p.label} (normalized kEUR→EUR)",
                )
            )
        else:
            normalized_points.append(p)

    # Step 2: Filter extreme outliers after normalization
    normalized_values = [abs(p.value) for p in normalized_points if p.value is not None]
    if normalized_values and len(normalized_values) >= 6:
        new_median = statistics.median(normalized_values)
        new_std = statistics.stdev(normalized_values) if len(normalized_values) > 1 else 0

        filtered_points = []
        outlier_count = 0
        for p in normalized_points:
            if p.value is None:
                continue

            abs_val = abs(p.value)
            deviation = abs(abs_val - new_median)

            if deviation <= 2.5 * new_std or new_std == 0:
                filtered_points.append(p)
            else:
                outlier_count += 1
                logger.warning(
                    f"Filtered extreme outlier: {p.value:.2f} (deviation: {deviation:.2f}, threshold: {2.5 * new_std:.2f})",
                    extra={
                        "metric": metric,
                        "date": p.date.strftime("%Y-%m-%d"),
                        "value": p.value,
                        "median": new_median,
                        "std": new_std,
                    },
                )

        if outlier_count > 0:
            logger.info(
                f"Removed {outlier_count} extreme outliers",
                extra={
                    "metric": metric,
                    "outliers_removed": outlier_count,
                    "points_remaining": len(filtered_points),
                },
            )
            return filtered_points

    return normalized_points


def apply_percentage_bounds(points: list[TimeSeriesPoint], metric: str) -> list[TimeSeriesPoint]:
    """Apply 0-100 bounds to percentage metrics.

    Story 6.24.1: Filter year values and clamp percentages.

    Args:
        points: List of percentage metric points
        metric: Metric name for logging

    Returns:
        Bounded points
    """
    original_points = points
    filtered_points = []
    year_filtered_count = 0

    for p in points:
        if p.value is None:
            continue
        # Filter year values (2000-2099)
        if 2000 <= p.value <= 2099:
            logger.warning(
                f"Rejected year value {p.value} for percentage metric",
                extra={
                    "metric": metric,
                    "value": p.value,
                    "date": p.date.isoformat() if p.date else None,
                },
            )
            year_filtered_count += 1
            continue

        # Clamp to 0-100
        clamped_value = min(max(p.value, 0), 100)
        filtered_points.append(TimeSeriesPoint(date=p.date, value=clamped_value, label=p.label))

    if year_filtered_count > 0:
        logger.warning(
            f"Filtered {year_filtered_count} year-like values from percentage metric",
            extra={
                "metric": metric,
                "year_filtered": year_filtered_count,
                "points_remaining": len(filtered_points),
            },
        )

    # Log clamping stats
    clamped_count = sum(
        1
        for orig, new in zip(original_points, filtered_points, strict=False)
        if orig.value != new.value
    )
    if clamped_count > 0:
        logger.warning(
            f"Clamped {clamped_count} percentage values to 0-100 range",
            extra={
                "metric": metric,
                "clamped_count": clamped_count,
                "total_points": len(filtered_points),
            },
        )

    return filtered_points


def convert_cost_to_absolute(points: list[TimeSeriesPoint], metric: str) -> list[TimeSeriesPoint]:
    """Convert negative cost values to absolute values.

    Story 6.23: Cost metrics are recorded as negative in financial statements.

    Args:
        points: List of cost metric points
        metric: Metric name for logging

    Returns:
        Points with absolute values
    """
    original_points = points
    points = [
        TimeSeriesPoint(
            date=p.date,
            value=abs(p.value) if p.value is not None else None,
            label=p.label,
        )
        for p in points
        if p.value is not None
    ]

    negative_count = sum(1 for p in original_points if p.value is not None and p.value < 0)
    if negative_count > 0:
        avg_before = sum(p.value for p in original_points if p.value is not None) / len(
            original_points
        )
        avg_after = sum(p.value for p in points if p.value is not None) / len(points)
        logger.info(
            f"Converted {negative_count} negative cost values to absolute values",
            extra={
                "metric": metric,
                "negative_values": negative_count,
                "total_points": len(points),
                "avg_before": avg_before,
                "avg_after": avg_after,
            },
        )

    return points


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
