"""Postprocessing utilities for time-series data."""

from __future__ import annotations

from raglite.shared.models import TimeSeriesPoint


def apply_percentage_bounds(points: list[TimeSeriesPoint], metric: str) -> list[TimeSeriesPoint]:
    """Apply 0-100 bounds to percentage metrics.

    Story 6.24.1: Filter year values and clamp percentages.

    Args:
        points: List of percentage metric points
        metric: Metric name for logging

    Returns:
        Bounded points
    """
    filtered_points = []
    year_filtered_count = 0

    for p in points:
        if p.value is None:
            continue
        # Filter year values (2000-2099)
        if 2000 <= p.value <= 2099:
            year_filtered_count += 1
            continue

        # Clamp to 0-100
        clamped_value = min(max(p.value, 0), 100)
        filtered_points.append(TimeSeriesPoint(date=p.date, value=clamped_value, label=p.label))

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
