"""Trend break detection for regime changes.

Story 6.8 AC6: Trend break detection using rolling slope analysis.
Story 7.5: Extracted from regime_detection.py for modularity.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from raglite.forecasting.regime_detection_models import DEFAULT_WINDOW_SIZE


def detect_trend_breaks(
    series: pd.Series,
    window_size: int = DEFAULT_WINDOW_SIZE,
    slope_change_threshold: float = 1.5,  # Increased from 0.5 for less noise sensitivity
) -> list[tuple[pd.Timestamp, float, str]]:
    """Detect trend direction changes using rolling slope.

    Story 6.8 AC6: Trend break detection for regime changes.

    Args:
        series: Time-series with DatetimeIndex
        window_size: Rolling window size (default: 6)
        slope_change_threshold: Threshold for slope change ratio (default: 0.5)

    Returns:
        List of (date, significance, direction_change) tuples
    """
    if len(series) < window_size * 3:
        return []

    # Calculate rolling slope
    slopes: list[float] = []
    dates: list[pd.Timestamp] = []

    for i in range(window_size, len(series) + 1):
        window = series.iloc[i - window_size : i]
        x = np.arange(len(window))
        y = window.values.astype(float)

        # Linear regression for slope
        if len(x) > 1:
            slope, _ = np.polyfit(x, y, 1)
            slopes.append(slope)
            dates.append(pd.Timestamp(series.index[i - 1]))

    if len(slopes) < 3:
        return []

    # Normalize slopes
    slope_series = pd.Series(slopes, index=pd.DatetimeIndex(dates))
    slope_std = slope_series.std()
    if slope_std == 0:
        return []

    # Detect sign changes or large magnitude changes
    change_points: list[tuple[pd.Timestamp, float, str]] = []

    for i in range(1, len(slopes)):
        prev_slope = slopes[i - 1]
        curr_slope = slopes[i]

        # Sign change (trend reversal)
        if prev_slope * curr_slope < 0:
            significance = abs(curr_slope - prev_slope) / slope_std
            direction = "reversal_up" if curr_slope > prev_slope else "reversal_down"
            if significance > slope_change_threshold:
                change_points.append((dates[i], min(1.0, significance / 3), direction))

        # Large magnitude change (acceleration/deceleration)
        elif abs(curr_slope) > 0 and abs(prev_slope) > 0:
            ratio = abs(curr_slope / prev_slope)
            if ratio > 2 or ratio < 0.5:  # Doubling or halving of slope
                significance = abs(np.log(ratio)) / 2
                direction = "acceleration" if ratio > 1 else "deceleration"
                if significance > slope_change_threshold:
                    change_points.append((dates[i], min(1.0, significance), direction))

    return change_points
