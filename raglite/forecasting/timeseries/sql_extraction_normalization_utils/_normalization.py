"""Normalization utilities for time-series data."""

from __future__ import annotations

import statistics

from raglite.forecasting.timeseries.sql_extraction_config import (
    get_ebitda_metrics,
)
from raglite.shared.models import TimeSeriesPoint


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
            normalized_points.append(
                TimeSeriesPoint(date=p.date, value=normalized_val, label=f"{p.label} (kEUR→M EUR)")
            )
        else:
            normalized_points.append(p)

    # Step 2: Filter extreme outliers
    filtered_points = []
    filtered_count = 0
    for p in normalized_points:
        if p.value is not None and abs(p.value) > EBITDA_MAX_REASONABLE:
            filtered_count += 1
        else:
            filtered_points.append(p)

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
