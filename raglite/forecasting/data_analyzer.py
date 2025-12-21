"""Data Characteristics Analyzer for Time-Series Model Selection.

This module analyzes time-series data to extract characteristics needed for
intelligent model selection. It performs statistical tests on stationarity,
seasonality, trend, and volatility to recommend appropriate forecasting models.

Exports:
    - Stationarity: Enum for stationarity classification
    - SeasonalityType: Enum for seasonality type classification
    - VolatilityLevel: Enum for volatility level classification
    - TrendDirection: Enum for trend direction classification
    - DataCharacteristics: Dataclass containing all analysis results
    - analyze_data_characteristics: Main analysis function
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import acf, adfuller, kpss

# -----------------------------------------------------------------------------
# Enums for Classification
# -----------------------------------------------------------------------------


class Stationarity(Enum):
    """Stationarity classification based on ADF + KPSS tests."""

    STATIONARY = "stationary"  # ADF rejects, KPSS fails to reject
    TREND_STATIONARY = "trend_stationary"  # Both reject or conflicting
    DIFFERENCE_STATIONARY = "difference_stationary"  # Needs differencing
    NON_STATIONARY = "non_stationary"  # ADF fails to reject, KPSS rejects


class SeasonalityType(Enum):
    """Seasonality classification."""

    NONE = "none"
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"


class VolatilityLevel(Enum):
    """Volatility classification."""

    LOW = "low"  # CV < 0.1
    MEDIUM = "medium"  # 0.1 <= CV < 0.3
    HIGH = "high"  # CV >= 0.3


class TrendDirection(Enum):
    """Trend direction classification."""

    UP = "up"
    DOWN = "down"
    FLAT = "flat"


# -----------------------------------------------------------------------------
# Data Classes
# -----------------------------------------------------------------------------


@dataclass
class DataCharacteristics:
    """Complete data characteristics for model selection."""

    # Stationarity
    stationarity: Stationarity
    adf_pvalue: float
    kpss_pvalue: float
    suggested_differencing: int

    # Seasonality
    seasonality_type: SeasonalityType
    seasonal_period: int | None
    seasonal_strength: float  # 0-1

    # Trend
    trend_slope: float
    trend_significance: float
    trend_direction: TrendDirection

    # Volatility
    coefficient_of_variation: float
    volatility_level: VolatilityLevel
    rolling_volatility: float | None

    # Data quality
    data_length: int
    missing_ratio: float
    outlier_count: int

    # Recommendations
    recommended_models: list[str]
    model_rationale: str


@dataclass
class StationarityResult:
    """Stationarity test results."""

    stationarity: Stationarity
    adf_pvalue: float
    kpss_pvalue: float
    suggested_differencing: int


@dataclass
class SeasonalityResult:
    """Seasonality detection results."""

    seasonality_type: SeasonalityType
    seasonal_period: int | None
    seasonal_strength: float


@dataclass
class TrendResult:
    """Trend detection results."""

    slope: float
    significance: float
    direction: TrendDirection


@dataclass
class VolatilityResult:
    """Volatility measurement results."""

    cv: float
    level: VolatilityLevel
    rolling_volatility: float | None = None


@dataclass
class DataQualityResult:
    """Data quality assessment results."""

    data_length: int
    missing_ratio: float
    outlier_count: int


# -----------------------------------------------------------------------------
# Main Analysis Function
# -----------------------------------------------------------------------------


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
    clean_series = _clean_series(series)

    # 2. Test stationarity (ADF + KPSS)
    stationarity_result = _test_stationarity(clean_series)

    # 3. Detect seasonality
    seasonality_result = _detect_seasonality(clean_series, frequency)

    # 4. Detect trend
    trend_result = _detect_trend(clean_series)

    # 5. Measure volatility
    volatility_result = _measure_volatility(clean_series)

    # 6. Assess data quality
    quality_result = _assess_data_quality(series)  # Original with NaNs

    # 7. Generate recommendations
    recommended_models, rationale = _recommend_models(
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


# -----------------------------------------------------------------------------
# Helper Functions - Stationarity
# -----------------------------------------------------------------------------


def _test_stationarity(series: pd.Series) -> StationarityResult:
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


# -----------------------------------------------------------------------------
# Helper Functions - Seasonality
# -----------------------------------------------------------------------------


def _detect_seasonality(series: pd.Series, frequency: str) -> SeasonalityResult:
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


# -----------------------------------------------------------------------------
# Helper Functions - Trend
# -----------------------------------------------------------------------------


def _detect_trend(series: pd.Series) -> TrendResult:
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


# -----------------------------------------------------------------------------
# Helper Functions - Volatility
# -----------------------------------------------------------------------------


def _measure_volatility(series: pd.Series, window: int = 12) -> VolatilityResult:
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


# -----------------------------------------------------------------------------
# Helper Functions - Data Quality
# -----------------------------------------------------------------------------


def _assess_data_quality(series: pd.Series) -> DataQualityResult:
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


# -----------------------------------------------------------------------------
# Helper Functions - Model Recommendations
# -----------------------------------------------------------------------------


def _recommend_models(
    stationarity: StationarityResult,
    seasonality: SeasonalityResult,
    trend: TrendResult,
    volatility: VolatilityResult,
    quality: DataQualityResult,
) -> tuple[list[str], str]:
    """Generate model recommendations based on data characteristics.

    Args:
        stationarity: Stationarity test results
        seasonality: Seasonality detection results
        trend: Trend detection results
        volatility: Volatility measurement results
        quality: Data quality assessment results

    Returns:
        Tuple of (recommended_models, rationale)
    """
    candidates = []
    rationale_parts = []

    # Cold-start: prefer Chronos-2 for short series
    if quality.data_length < 12:
        candidates.append("chronos")
        rationale_parts.append(
            f"Short series ({quality.data_length} points) - Chronos-2 for zero-shot"
        )
        return candidates, "; ".join(rationale_parts)

    # Stationarity-based recommendations
    if stationarity.stationarity == Stationarity.STATIONARY:
        candidates.extend(["arima", "linear"])
        rationale_parts.append("Stationary data - ARIMA/Linear preferred")
    elif stationarity.stationarity == Stationarity.NON_STATIONARY:
        candidates.extend(["prophet", "ets", "arima"])
        rationale_parts.append("Non-stationary - Prophet/ETS/ARIMA with differencing")
    elif stationarity.stationarity == Stationarity.TREND_STATIONARY:
        candidates.extend(["prophet", "arima"])
        rationale_parts.append("Trend-stationary - Prophet/ARIMA with detrending")
    elif stationarity.stationarity == Stationarity.DIFFERENCE_STATIONARY:
        candidates.extend(["arima", "ets"])
        rationale_parts.append("Difference-stationary - ARIMA/ETS preferred")

    # Seasonality-based recommendations
    if seasonality.seasonal_strength > 0.3:
        if "arima" in candidates:
            candidates[candidates.index("arima")] = "sarima"  # Upgrade to SARIMA
        if "ets" not in candidates:
            candidates.append("ets")
        if "prophet" not in candidates:
            candidates.append("prophet")
        rationale_parts.append(
            f"Strong seasonality ({seasonality.seasonal_strength:.2f}) - SARIMA/ETS/Prophet"
        )

    # Volatility-based recommendations
    if volatility.level == VolatilityLevel.HIGH:
        candidates.extend(["xgboost", "lightgbm", "catboost"])
        rationale_parts.append(f"High volatility (CV={volatility.cv:.2f}) - ML models")

    # Trend-based recommendations
    if trend.direction != TrendDirection.FLAT and trend.significance < 0.05:
        if "prophet" not in candidates:
            candidates.append("prophet")
        rationale_parts.append("Significant trend - Prophet for changepoints")

    # Always include TFT for complex patterns (lower priority)
    if quality.data_length >= 24:
        candidates.append("tft")

    # Deduplicate while preserving order
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)

    rationale = "; ".join(rationale_parts) if rationale_parts else "Default model selection"

    return unique_candidates, rationale


# -----------------------------------------------------------------------------
# Helper Functions - Data Cleaning
# -----------------------------------------------------------------------------


def _clean_series(series: pd.Series) -> pd.Series:
    """Clean series by handling NaN values.

    Args:
        series: Original time series

    Returns:
        Cleaned time series without NaN values

    Raises:
        ValueError: If series is too short or constant
    """
    # Drop NaN values for analysis
    clean = series.dropna()

    if len(clean) < 4:
        raise ValueError(f"Series too short after cleaning: {len(clean)} observations (minimum: 4)")

    if clean.std() == 0:
        raise ValueError("Constant series cannot be analyzed for time-series properties")

    return clean
