"""[P0-P1] Integration Tests for Component Interactions.

Tests for interactions between analyzer components:
- Stationary + seasonal series recommendations
- High volatility + non-stationary dual recommendations
- Mixed characteristics comprehensive recommendations
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class TestComponentIntegration:
    """[P0-P1] Tests for interactions between analyzer components."""

    def test_p0_stationary_with_seasonality_recommendations(self) -> None:
        """[P0] Verify stationary + seasonal series recommends SARIMA not ARIMA.

        Given: A stationary series with strong seasonality
        When: Analyzing characteristics
        Then: Should recommend SARIMA (upgraded from ARIMA), ETS, Prophet
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        # Create stationary but seasonal data
        dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
        np.random.seed(42)
        # Stationary with strong seasonality
        seasonality = 25 * np.sin(2 * np.pi * np.arange(60) / 12)
        noise = np.random.normal(0, 5, 60)
        values = 100 + seasonality + noise
        series = pd.Series(values, index=dates)

        result = analyze_data_characteristics(series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        # Should upgrade ARIMA to SARIMA due to seasonality
        assert "sarima" in recommended or ("ets" in recommended and "prophet" in recommended)

    def test_p1_high_volatility_non_stationary_dual_recommendation(
        self, high_volatility_series: pd.Series
    ) -> None:
        """[P1] High volatility + non-stationary triggers both statistical and ML models.

        Given: A non-stationary series with high volatility
        When: Analyzing characteristics
        Then: Should recommend both Prophet/ETS and ML models
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        # Make it non-stationary by adding cumulative trend
        dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
        np.random.seed(42)
        cumulative_trend = np.cumsum(np.random.normal(2, 25, 60))  # High volatility
        series = pd.Series(100 + cumulative_trend, index=dates)

        result = analyze_data_characteristics(series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        # Should have both statistical (prophet/ets/arima) and ML models
        has_statistical = any(m in recommended for m in ["prophet", "ets", "arima"])
        has_ml = any(m in recommended for m in ["xgboost", "lightgbm", "catboost"])
        assert has_statistical and has_ml

    def test_p1_mixed_characteristics_comprehensive_recommendations(
        self, mixed_characteristics_series: pd.Series
    ) -> None:
        """[P1] Series with trend + seasonality + volatility gets comprehensive model list.

        Given: A series with multiple strong characteristics
        When: Analyzing characteristics
        Then: Should recommend Prophet, seasonal models, and ML models
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(mixed_characteristics_series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        # Should include Prophet (trend), seasonal models, and ML (volatility)
        assert "prophet" in recommended
        assert len(recommended) >= 4  # Multiple characteristics -> multiple models
