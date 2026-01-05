"""Model recommendation engine for time-series forecasting.

This module provides functions for generating model recommendations
based on data characteristics.
"""

from __future__ import annotations

from .models import (
    DataQualityResult,
    SeasonalityResult,
    Stationarity,
    StationarityResult,
    TrendDirection,
    TrendResult,
    VolatilityLevel,
    VolatilityResult,
)


def recommend_models(
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
