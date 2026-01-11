"""Volatility measurement for time-series data.

This module provides functions for measuring volatility using coefficient
of variation and rolling volatility.
"""

from __future__ import annotations

import pandas as pd

from .models import VolatilityLevel, VolatilityResult


def measure_volatility(series: pd.Series, window: int = 12) -> VolatilityResult:
    """Measure volatility using coefficient of variation and rolling volatility.

    Args:
        series: Cleaned time series
        window: Window size for rolling volatility (default: 12 months)

    Returns:
        VolatilityResult with CV, level classification, and rolling volatility
    """
    mean_val = series.mean()
    std_val = series.std()

    # Handle zero/near-zero mean
    if abs(mean_val) < 1e-10:
        cv = float("inf") if std_val > 0 else 0.0
    else:
        cv = abs(std_val / mean_val)

    # Classify volatility
    if cv < 0.1:
        level = VolatilityLevel.LOW
    elif cv < 0.3:
        level = VolatilityLevel.MEDIUM
    else:
        level = VolatilityLevel.HIGH

    # Calculate rolling volatility (standard deviation over windows)
    rolling_vol = None
    if len(series) >= window:
        rolling_std = series.rolling(window=window).std()
        # Use mean of rolling volatility for overall measure
        rolling_vol = rolling_std.mean()

    return VolatilityResult(cv=cv, level=level, rolling_volatility=rolling_vol)
