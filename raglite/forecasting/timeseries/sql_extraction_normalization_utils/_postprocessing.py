"""Postprocessing utilities for time-series data."""

from __future__ import annotations

from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

logger = get_logger(__name__)


def filter_bimodal_cost_to_dominant_sign(
    points: list[TimeSeriesPoint], metric: str
) -> list[TimeSeriesPoint]:
    """Filter bimodal cost distributions to dominant sign.

    Phase 3 Quality Fix (2026-01-29): Variable Cost has bimodal distribution
    (63% negative, 36% positive) due to mixing cost values (negative) with
    income/credit values (positive) in the same series.

    This function detects bimodal distributions and filters to the dominant
    sign to ensure consistent cost data for forecasting.

    Args:
        points: List of cost metric points
        metric: Metric name for logging

    Returns:
        Points filtered to dominant sign (if bimodal), or original points
    """
    if not points:
        return points

    values = [p.value for p in points if p.value is not None]
    if len(values) < 6:
        return points

    negative_vals = [v for v in values if v < 0]
    positive_vals = [v for v in values if v > 0]

    # Only filter if we have both signs present
    if not negative_vals or not positive_vals:
        return points

    neg_pct = len(negative_vals) / len(values)
    pos_pct = len(positive_vals) / len(values)

    # Consider bimodal if minority sign represents >20% of data
    MIN_BIMODAL_THRESHOLD = 0.20
    is_bimodal = min(neg_pct, pos_pct) > MIN_BIMODAL_THRESHOLD

    if not is_bimodal:
        return points

    # Filter to dominant sign (the one with >50% of values)
    if neg_pct > pos_pct:
        # Dominant negative (true costs) - filter to negative only
        filtered_points = [p for p in points if p.value is not None and p.value < 0]
        dominant_sign = "negative"
    else:
        # Dominant positive - keep positive only
        filtered_points = [p for p in points if p.value is not None and p.value > 0]
        dominant_sign = "positive"

    logger.info(
        "Filtered bimodal cost distribution to dominant sign",
        extra={
            "metric": metric,
            "original_count": len(points),
            "filtered_count": len(filtered_points),
            "negative_pct": f"{neg_pct:.1%}",
            "positive_pct": f"{pos_pct:.1%}",
            "dominant_sign": dominant_sign,
        },
    )

    return filtered_points


def apply_percentage_bounds(points: list[TimeSeriesPoint], metric: str) -> list[TimeSeriesPoint]:
    """Apply 0-105 bounds to percentage metrics with outlier filtering.

    Story 6.24.1: Filter year values and clamp percentages.
    Phase 4 Quality Fix (2026-01-29): Enhanced filtering for year-like contamination.

    Root cause: Capacity utilization showed +20.40 bias, suggesting year values (2020-2025)
    were contaminating percentage data. Values like "2025" were being treated as 2025%
    utilization, which only got clamped to 100% instead of filtered.

    Strategy:
    1. Filter values >105% (catches year contamination that exceeds percentage range)
    2. Filter explicit year range 2000-2099 (catches year values in valid percentage range)
    3. Filter negative values (percentages should be non-negative)
    4. Clamp remaining values to 0-100 (for edge cases like 101-105%)

    Args:
        points: List of percentage metric points
        metric: Metric name for logging

    Returns:
        Bounded points with outliers filtered
    """
    filtered_points = []
    outlier_filtered_count = 0
    year_filtered_count = 0

    for p in points:
        if p.value is None:
            continue

        # Phase 4: Filter values >105% (catches year-like contamination like 2025%)
        # Real percentage metrics should never exceed ~105% (allowing slight measurement error)
        if p.value > 105:
            outlier_filtered_count += 1
            continue

        # Filter year values (2000-2099) - catches years that happen to be in 0-105 range
        # Note: This is redundant for 2000-2099 given >105 filter, but kept for clarity
        if 2000 <= p.value <= 2099:
            year_filtered_count += 1
            continue

        # Filter negative values (percentages should be non-negative)
        if p.value < 0:
            outlier_filtered_count += 1
            continue

        # Clamp to 0-100 (for edge cases 100-105% like slight over-capacity)
        clamped_value = min(p.value, 100)
        filtered_points.append(TimeSeriesPoint(date=p.date, value=clamped_value, label=p.label))

    # Log if significant filtering occurred
    total_filtered = outlier_filtered_count + year_filtered_count
    if total_filtered > 0:
        logger.info(
            "Filtered percentage outliers",
            extra={
                "metric": metric,
                "original_count": len(points),
                "filtered_count": len(filtered_points),
                "outliers_removed": outlier_filtered_count,
                "years_removed": year_filtered_count,
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
    negative_count = sum(1 for p in points if p.value is not None and p.value < 0)
    if negative_count > 0:
        # Log conversion info if needed
        pass

    points = [
        TimeSeriesPoint(
            date=p.date,
            value=abs(p.value) if p.value is not None else None,
            label=p.label,
        )
        for p in points
        if p.value is not None
    ]

    return points
