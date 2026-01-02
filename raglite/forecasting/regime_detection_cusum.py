"""CUSUM-based mean shift detection for regime changes.

Story 6.8 AC6: CUSUM algorithm for detecting mean shifts in time-series.
Story 7.5: Extracted from regime_detection.py for modularity.
"""

from __future__ import annotations

import pandas as pd

from raglite.forecasting.regime_detection_models import (
    DEFAULT_CUSUM_THRESHOLD,
    MIN_REGIME_DATA_POINTS,
)


def _calculate_cusum(
    series: pd.Series,
    target_mean: float | None = None,
) -> tuple[pd.Series, pd.Series]:
    """Calculate CUSUM statistics for change point detection.

    CUSUM (Cumulative Sum) control chart detects shifts in the mean.
    Returns both upper and lower CUSUM series.

    Args:
        series: Time-series values
        target_mean: Target mean (default: series mean)

    Returns:
        Tuple of (upper_cusum, lower_cusum) Series
    """
    if target_mean is None:
        target_mean = series.mean()

    # Standardize using series std
    std = series.std()
    if std == 0:
        std = 1.0  # Avoid division by zero

    # Calculate standardized deviations
    z = (series - target_mean) / std

    # CUSUM: cumulative sum of deviations
    # Upper CUSUM detects upward shifts
    # Lower CUSUM detects downward shifts
    cusum_upper = z.cumsum()
    cusum_lower = -z.cumsum()

    return cusum_upper, cusum_lower


def detect_mean_shifts(
    series: pd.Series,
    threshold: float = DEFAULT_CUSUM_THRESHOLD,
    min_segment_size: int = 6,
) -> list[tuple[pd.Timestamp, float, str]]:
    """Detect mean shifts using CUSUM algorithm.

    Story 6.8 AC6: Mean shift detection for regime changes.

    Args:
        series: Time-series with DatetimeIndex
        threshold: CUSUM threshold for detecting change (default: 4.0)
        min_segment_size: Minimum observations between change points

    Returns:
        List of (date, significance, direction) tuples for detected shifts
    """
    if len(series) < MIN_REGIME_DATA_POINTS:
        return []

    cusum_upper, cusum_lower = _calculate_cusum(series)
    change_points: list[tuple[pd.Timestamp, float, str]] = []

    # Find points where CUSUM exceeds threshold
    # Then reset CUSUM to detect additional changes
    remaining_series = series.copy()

    while len(remaining_series) >= min_segment_size * 2:
        cusum_upper, cusum_lower = _calculate_cusum(remaining_series)

        # Find maximum absolute CUSUM
        max_upper_idx = cusum_upper.abs().idxmax()
        max_lower_idx = cusum_lower.abs().idxmax()
        max_upper = abs(cusum_upper.loc[max_upper_idx])
        max_lower = abs(cusum_lower.loc[max_lower_idx])

        # Determine which CUSUM is larger
        if max_upper >= max_lower and max_upper > threshold:
            change_idx = max_upper_idx
            direction = "increase"
            significance = min(1.0, max_upper / (threshold * 2))
        elif max_lower > threshold:
            change_idx = max_lower_idx
            direction = "decrease"
            significance = min(1.0, max_lower / (threshold * 2))
        else:
            # No more significant changes
            break

        # Get position in remaining series
        pos = remaining_series.index.get_loc(change_idx)

        # Only accept if it divides series into reasonable segments
        if pos >= min_segment_size and len(remaining_series) - pos >= min_segment_size:
            change_points.append(
                (
                    pd.Timestamp(change_idx),
                    significance,
                    direction,
                )
            )

            # Reset: analyze only the portion after the change point
            remaining_series = remaining_series.iloc[pos:]
        else:
            break

    return change_points
