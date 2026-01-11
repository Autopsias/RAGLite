"""Data quality assessment for time-series data.

This module provides functions for assessing data quality metrics.
"""

from __future__ import annotations

import pandas as pd

from .models import DataQualityResult


def assess_data_quality(series: pd.Series) -> DataQualityResult:
    """Assess data quality metrics.

    Args:
        series: Original time series (may contain NaN)

    Returns:
        DataQualityResult with length, missing ratio, and outlier count
    """
    data_length = len(series)
    missing_count = series.isna().sum()
    missing_ratio = missing_count / data_length if data_length > 0 else 0.0

    # Outlier detection using IQR
    clean_series = series.dropna()
    if len(clean_series) >= 4:
        q1 = clean_series.quantile(0.25)
        q3 = clean_series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outlier_count = ((clean_series < lower_bound) | (clean_series > upper_bound)).sum()
    else:
        outlier_count = 0

    return DataQualityResult(
        data_length=data_length,
        missing_ratio=missing_ratio,
        outlier_count=outlier_count,
    )
