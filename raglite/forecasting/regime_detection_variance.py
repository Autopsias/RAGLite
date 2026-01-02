"""Variance shift detection for regime changes.

Story 6.8 AC6: Variance shift detection using rolling variance analysis.
Story 7.5: Extracted from regime_detection.py for modularity.
"""

from __future__ import annotations

import pandas as pd

from raglite.forecasting.regime_detection_models import DEFAULT_WINDOW_SIZE


def detect_variance_shifts(
    series: pd.Series,
    window_size: int = DEFAULT_WINDOW_SIZE,
    variance_ratio_threshold: float = 3.0,  # Increased from 2.0 for less noise sensitivity
) -> list[tuple[pd.Timestamp, float]]:
    """Detect variance (volatility) shifts using rolling variance.

    Story 6.8 AC6: Variance shift detection for regime changes.

    Args:
        series: Time-series with DatetimeIndex
        window_size: Rolling window size (default: 6)
        variance_ratio_threshold: Threshold for variance change (default: 2.0)

    Returns:
        List of (date, variance_ratio) tuples for detected shifts
    """
    if len(series) < window_size * 3:
        return []

    # Calculate rolling variance
    rolling_var = series.rolling(window=window_size, min_periods=window_size // 2).var()

    # Detect significant variance changes
    change_points: list[tuple[pd.Timestamp, float]] = []

    for i in range(window_size, len(rolling_var) - window_size):
        pre_var = rolling_var.iloc[i - window_size : i].mean()
        post_var = rolling_var.iloc[i : i + window_size].mean()

        if pre_var > 0 and post_var > 0:
            ratio = max(post_var / pre_var, pre_var / post_var)
            if ratio >= variance_ratio_threshold:
                change_points.append((pd.Timestamp(series.index[i]), ratio))

    # Remove duplicates (keep highest ratio within window)
    if change_points:
        filtered: list[tuple[pd.Timestamp, float]] = []
        sorted_points = sorted(change_points, key=lambda x: x[1], reverse=True)
        used_dates: set[pd.Timestamp] = set()

        for date, ratio in sorted_points:
            # Check if too close to existing point
            too_close = False
            for used_date in used_dates:
                if abs((date - used_date).days) < window_size * 30:  # ~months
                    too_close = True
                    break

            if not too_close:
                filtered.append((date, ratio))
                used_dates.add(date)

        return filtered

    return []
