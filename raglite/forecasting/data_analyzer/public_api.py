"""Public API for data characteristics analyzer.

This module provides the main analysis function that orchestrates
all time-series analysis components.
"""

from __future__ import annotations

import pandas as pd

from .cleaning import clean_series
from .models import DataCharacteristics
from .quality import assess_data_quality
from .recommendations import recommend_models
from .seasonality import detect_seasonality
from .stationarity import test_stationarity
from .trend import detect_trend
from .volatility import measure_volatility


def analyze_data_characteristics(
    series: pd.Series,
    frequency: str = "M",
) -> DataCharacteristics:
    """Analyze time-series for model selection.

    Args:
        series: Time series data (pandas Series with DatetimeIndex)
        frequency: Time frequency ("M" for monthly, "Q" for quarterly)

    Returns:
        DataCharacteristics with all metrics and model recommendations

    Raises:
        ValueError: If series is too short (<4 observations) or all NaN
    """
    # 1. Clean data
    clean_series_data = clean_series(series)

    # 2. Test stationarity (ADF + KPSS)
    stationarity_result = test_stationarity(clean_series_data)

    # 3. Detect seasonality
    seasonality_result = detect_seasonality(clean_series_data, frequency)

    # 4. Detect trend
    trend_result = detect_trend(clean_series_data)

    # 5. Measure volatility
    volatility_result = measure_volatility(clean_series_data)

    # 6. Assess data quality
    quality_result = assess_data_quality(series)  # Original with NaNs

    # 7. Generate recommendations
    recommended_models, rationale = recommend_models(
        stationarity_result,
        seasonality_result,
        trend_result,
        volatility_result,
        quality_result,
    )

    return DataCharacteristics(
        stationarity=stationarity_result.stationarity,
        adf_pvalue=stationarity_result.adf_pvalue,
        kpss_pvalue=stationarity_result.kpss_pvalue,
        suggested_differencing=stationarity_result.suggested_differencing,
        seasonality_type=seasonality_result.seasonality_type,
        seasonal_period=seasonality_result.seasonal_period,
        seasonal_strength=seasonality_result.seasonal_strength,
        trend_slope=trend_result.slope,
        trend_significance=trend_result.significance,
        trend_direction=trend_result.direction,
        coefficient_of_variation=volatility_result.cv,
        volatility_level=volatility_result.level,
        rolling_volatility=volatility_result.rolling_volatility,
        data_length=quality_result.data_length,
        missing_ratio=quality_result.missing_ratio,
        outlier_count=quality_result.outlier_count,
        recommended_models=recommended_models,
        model_rationale=rationale,
    )
