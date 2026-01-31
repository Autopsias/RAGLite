"""Normalization utilities for time-series data."""

from __future__ import annotations

import statistics

from raglite.forecasting.timeseries.sql_extraction_config import (
    get_ebitda_metrics,
    get_unit_scaling_factor,
)
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

logger = get_logger(__name__)


def normalize_by_unit(
    points: list[TimeSeriesPoint],
    units: list[str | None],
    metric: str,
) -> list[TimeSeriesPoint]:
    """Apply unit-based scaling to normalize values to EUR millions.

    Phase 2 data quality: Uses explicit unit metadata from database rather than
    value-based heuristics. This is more reliable than median-based detection.

    Args:
        points: List of TimeSeriesPoint objects
        units: List of unit strings (parallel to points)
        metric: Metric name for logging

    Returns:
        Normalized points with consistent EUR millions units

    Note:
        When unit is None or unknown, no scaling is applied.
        The function logs statistics about scaling applied.
    """
    if not points:
        return points

    if len(points) != len(units):
        logger.warning(
            "Points/units length mismatch, falling back to value heuristics",
            extra={"points_len": len(points), "units_len": len(units), "metric": metric},
        )
        return points

    normalized = []
    scale_counts: dict[str, int] = {}

    for point, unit in zip(points, units, strict=False):
        if point.value is None:
            continue

        factor = get_unit_scaling_factor(unit)

        if factor != 1.0:
            scaled_value = point.value * factor
            unit_label = unit if unit else "unknown"
            scale_counts[unit_label] = scale_counts.get(unit_label, 0) + 1
            normalized.append(
                TimeSeriesPoint(
                    date=point.date,
                    value=scaled_value,
                    label=f"{point.label} ({unit}→M EUR)",
                )
            )
        else:
            normalized.append(point)

    if scale_counts:
        logger.info(
            "Applied unit-based normalization",
            extra={
                "metric": metric,
                "scaling_applied": scale_counts,
                "total_scaled": sum(scale_counts.values()),
                "total_points": len(points),
            },
        )

    return normalized


def normalize_ebitda_pre_ytd(points: list[TimeSeriesPoint], metric: str) -> list[TimeSeriesPoint]:
    """Normalize EBITDA mixed units BEFORE YTD conversion.

    Story 6.25.1: EBITDA has mixed units - kEUR vs EUR millions.
    Must normalize before YTD→monthly conversion to avoid garbage deltas.

    Phase 9 Data Quality Fix (2026-01-29): Use MAD-based outlier detection instead of
    fixed bounds. Fixed bounds (1000 M EUR max) failed to catch annual values (960 M EUR)
    mixed with monthly values (2-15 M EUR), causing 335x swing ratio rejection.

    MAD (Median Absolute Deviation) is robust to outliers and adapts to actual data scale:
    - Calculate median of values
    - Calculate MAD = median(|value - median|)
    - Filter values > median + 5*MAD (catches annual values in monthly data)

    Args:
        points: List of EBITDA points
        metric: Metric name for logging

    Returns:
        Normalized points with consistent EUR millions units
    """
    EBITDA_KEUR_THRESHOLD = 10000  # Values > 10000 are in kEUR
    EBITDA_LARGE_SCALING_WARNING = 10  # Log warning if scaling factor > 10x
    # Phase 9: MAD multiplier for outlier detection (5 = very conservative, ~99.9% of normal dist)
    MAD_OUTLIER_THRESHOLD = 5.0
    # Minimum MAD to prevent division by zero or near-zero MAD
    MIN_MAD = 1.0

    # Step 1: Normalize kEUR → EUR millions
    normalized_points = []
    keur_count = 0
    scaling_factors: list[float] = []

    for p in points:
        if p.value is None:
            continue
        if abs(p.value) > EBITDA_KEUR_THRESHOLD:
            normalized_val = p.value / 1000
            scaling_factor = abs(p.value / normalized_val) if normalized_val != 0 else 1
            scaling_factors.append(scaling_factor)
            keur_count += 1
            normalized_points.append(
                TimeSeriesPoint(date=p.date, value=normalized_val, label=f"{p.label} (kEUR→M EUR)")
            )
        else:
            normalized_points.append(p)

    # Forecast debug fix: Log if large scaling was needed
    if scaling_factors:
        max_scaling = max(scaling_factors)
        if max_scaling > EBITDA_LARGE_SCALING_WARNING:
            logger.warning(
                "EBITDA required large scaling factor - potential unit confusion",
                extra={
                    "metric": metric,
                    "max_scaling_factor": max_scaling,
                    "keur_converted": keur_count,
                    "total_points": len(points),
                },
            )

    # Step 2: Filter extreme outliers using MAD-based detection
    # This is more robust than fixed bounds and adapts to actual data scale
    values = [abs(p.value) for p in normalized_points if p.value is not None and p.value != 0]

    if len(values) < 3:
        # Not enough data for MAD calculation, return as-is
        return normalized_points

    median_val = statistics.median(values)
    # Calculate MAD: median of |value - median|
    absolute_deviations = [abs(v - median_val) for v in values]
    mad = statistics.median(absolute_deviations)
    # Ensure minimum MAD to prevent aggressive filtering
    mad = max(mad, MIN_MAD)

    # Upper bound = median + MAD_OUTLIER_THRESHOLD * MAD
    upper_bound = median_val + MAD_OUTLIER_THRESHOLD * mad

    filtered_points = []
    filtered_count = 0
    for p in normalized_points:
        if p.value is None:
            filtered_points.append(p)
            continue

        abs_val = abs(p.value)
        # Filter values exceeding MAD-based upper bound
        if abs_val > upper_bound:
            filtered_count += 1
            logger.debug(
                "Filtered EBITDA value exceeding MAD bound",
                extra={
                    "date": str(p.date),
                    "value": p.value,
                    "median": median_val,
                    "mad": mad,
                    "upper_bound": upper_bound,
                },
            )
        elif abs_val < 0.01:  # Filter near-zero values (likely data errors)
            filtered_count += 1
            logger.debug(
                "Filtered near-zero EBITDA value",
                extra={"date": str(p.date), "value": p.value},
            )
        else:
            filtered_points.append(p)

    if filtered_count > 0:
        logger.info(
            "EBITDA pre-YTD normalization filtered outliers (MAD-based)",
            extra={
                "metric": metric,
                "filtered_count": filtered_count,
                "remaining_points": len(filtered_points),
                "keur_converted": keur_count,
                "median": median_val,
                "mad": mad,
                "upper_bound": upper_bound,
            },
        )

    return filtered_points


def _normalize_keur_to_eur(
    points: list[TimeSeriesPoint], metric: str, median_value: float
) -> list[TimeSeriesPoint]:
    """Normalize kEUR values to EUR.

    Converts values that are >5x the median (likely kEUR → EUR conversion needed).

    Args:
        points: List of points to normalize
        metric: Metric name for logging
        median_value: Median of absolute values for ratio calculation

    Returns:
        Points with normalized units
    """
    normalized_points = []
    for p in points:
        if p.value is None:
            continue

        abs_val = abs(p.value)
        ratio = abs_val / median_value if median_value > 0 else 0

        if ratio > 5.0:
            # Likely kEUR → EUR conversion needed
            normalized_value = p.value / 1000
            normalized_points.append(
                TimeSeriesPoint(
                    date=p.date,
                    value=normalized_value,
                    label=f"{p.label} (normalized kEUR→EUR)",
                )
            )
        else:
            normalized_points.append(p)

    return normalized_points


def _filter_statistical_outliers(
    points: list[TimeSeriesPoint], metric: str
) -> list[TimeSeriesPoint]:
    """Filter extreme outliers using statistical deviation.

    Removes values with deviation >2.5 standard deviations from median.

    Args:
        points: List of points to filter
        metric: Metric name for logging

    Returns:
        Filtered points without outliers
    """
    normalized_values = [abs(p.value) for p in points if p.value is not None]
    if not normalized_values or len(normalized_values) < 6:
        return points

    new_median = statistics.median(normalized_values)
    new_std = statistics.stdev(normalized_values) if len(normalized_values) > 1 else 0

    filtered_points = []
    outlier_count = 0
    for p in points:
        if p.value is None:
            continue

        abs_val = abs(p.value)
        deviation = abs(abs_val - new_median)

        if deviation <= 2.5 * new_std or new_std == 0:
            filtered_points.append(p)
        else:
            outlier_count += 1

    if outlier_count > 0:
        return filtered_points

    return points


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
    normalized_points = _normalize_keur_to_eur(points, metric, median_value)

    # Step 2: Filter extreme outliers after normalization
    filtered_points = _filter_statistical_outliers(normalized_points, metric)

    return filtered_points
