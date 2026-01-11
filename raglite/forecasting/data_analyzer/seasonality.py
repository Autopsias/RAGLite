"""Seasonality detection for time-series data.

This module provides functions for detecting seasonality via ACF peak analysis.
"""

from __future__ import annotations

import pandas as pd
from statsmodels.tsa.stattools import acf

from .models import SeasonalityResult, SeasonalityType


def detect_seasonality(series: pd.Series, frequency: str) -> SeasonalityResult:
    """Detect seasonality via ACF peak analysis.

    Args:
        series: Cleaned time series
        frequency: Time frequency ("M" or "Q")

    Returns:
        SeasonalityResult with type, period, and strength
    """
    seasonal_period = 12 if frequency == "M" else 4

    # Compute ACF
    nlags = min(len(series) - 1, seasonal_period * 2)
    if nlags < seasonal_period:
        return SeasonalityResult(
            seasonality_type=SeasonalityType.NONE,
            seasonal_period=None,
            seasonal_strength=0.0,
        )

    acf_values = acf(series, nlags=nlags, fft=True)

    # Check for peak at seasonal lag
    seasonal_acf = abs(acf_values[seasonal_period]) if len(acf_values) > seasonal_period else 0.0

    # Determine seasonality type based on coefficient of variation pattern
    # Multiplicative if variance scales with level
    if seasonal_acf > 0.3:
        # Simple heuristic: if high-value periods have proportionally higher variance
        mean_series = series.mean()
        if mean_series > 0:
            upper_half = series[series > mean_series]
            lower_half = series[series <= mean_series]
            if len(upper_half) > 2 and len(lower_half) > 2:
                cv_upper = upper_half.std() / upper_half.mean() if upper_half.mean() != 0 else 0
                cv_lower = lower_half.std() / lower_half.mean() if lower_half.mean() != 0 else 0
                seasonality_type = (
                    SeasonalityType.MULTIPLICATIVE
                    if cv_upper > cv_lower * 1.2
                    else SeasonalityType.ADDITIVE
                )
            else:
                seasonality_type = SeasonalityType.ADDITIVE
        else:
            seasonality_type = SeasonalityType.ADDITIVE
    else:
        seasonality_type = SeasonalityType.NONE

    return SeasonalityResult(
        seasonality_type=seasonality_type,
        seasonal_period=seasonal_period if seasonal_acf > 0.1 else None,
        seasonal_strength=seasonal_acf,
    )
