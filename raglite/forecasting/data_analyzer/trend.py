"""Trend detection for time-series data.

This module provides functions for detecting trend via linear regression.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .models import TrendDirection, TrendResult


def detect_trend(series: pd.Series) -> TrendResult:
    """Detect trend via linear regression.

    Args:
        series: Cleaned time series

    Returns:
        TrendResult with slope, significance, and direction
    """
    # Create time index
    t = np.arange(len(series))

    # OLS regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(t, series.values)

    # Determine direction
    if p_value < 0.05:
        direction = TrendDirection.UP if slope > 0 else TrendDirection.DOWN
    else:
        direction = TrendDirection.FLAT

    return TrendResult(slope=slope, significance=p_value, direction=direction)
