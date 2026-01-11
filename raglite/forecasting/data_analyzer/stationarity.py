"""Stationarity analysis for time-series data.

This module provides functions for testing stationarity using the
Kwiatkowski protocol (ADF + KPSS tests).
"""

from __future__ import annotations

import warnings

import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss

from .models import Stationarity, StationarityResult


def test_stationarity(series: pd.Series) -> StationarityResult:
    """Test stationarity using ADF + KPSS (Kwiatkowski protocol).

    Args:
        series: Cleaned time series

    Returns:
        StationarityResult with classification and p-values
    """
    # ADF test (null: non-stationary)
    adf_result = adfuller(series, autolag="AIC")
    adf_pvalue = adf_result[1]

    # KPSS test (null: stationary)
    # Suppress known interpolation warnings from statsmodels
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=Warning)
        try:
            kpss_result = kpss(series, regression="c", nlags="auto")
            kpss_pvalue = kpss_result[1]
        except Exception:
            kpss_pvalue = 0.5  # Inconclusive fallback

    # Kwiatkowski protocol interpretation
    if adf_pvalue < 0.05 and kpss_pvalue > 0.05:
        stationarity = Stationarity.STATIONARY
        differencing = 0
    elif adf_pvalue >= 0.05 and kpss_pvalue <= 0.05:
        stationarity = Stationarity.NON_STATIONARY
        differencing = 1

        # Check if d=2 is needed: test first-differenced series
        if len(series) > 10:  # Need enough data for second differencing test
            try:
                first_diff = series.diff().dropna()
                if len(first_diff) >= 4:
                    adf_diff = adfuller(first_diff, autolag="AIC")
                    # If first difference is still non-stationary, suggest d=2
                    if adf_diff[1] >= 0.05:
                        differencing = 2
            except Exception:
                # If testing fails, stick with d=1
                pass
    elif adf_pvalue < 0.05 and kpss_pvalue <= 0.05:
        stationarity = Stationarity.TREND_STATIONARY
        differencing = 1
    else:
        stationarity = Stationarity.DIFFERENCE_STATIONARY
        differencing = 1

    return StationarityResult(
        stationarity=stationarity,
        adf_pvalue=adf_pvalue,
        kpss_pvalue=kpss_pvalue,
        suggested_differencing=differencing,
    )
