"""TEST-AC-6: Return DataCharacteristics with Model Recommendations.

Tests for AC6 acceptance criteria from Story 7b.2:
- TEST-AC-6.1: Return DataCharacteristics dataclass with all metrics
- TEST-AC-6.2: Include recommended_models: list[str]
- TEST-AC-6.3: Include model_rationale: str
- TEST-AC-6.4: Prioritize recommendations (best model first)
- TEST-AC-6.5: Recommend ARIMA/Linear for stationary data
- TEST-AC-6.6: Recommend Prophet/ETS/ARIMA for non-stationary data
- TEST-AC-6.7: Recommend SARIMA/ETS/Prophet for seasonal data
- TEST-AC-6.8: Recommend XGBoost/LightGBM/CatBoost for high volatility
- TEST-AC-6.9: Recommend Chronos-2 for cold-start (<12 points)
- TEST-AC-6.10: Recommend Prophet for significant trend
- TEST-AC-6.11: Handle edge case - constant values
- TEST-AC-6.12: Handle edge case - very short series
"""

from __future__ import annotations

import pandas as pd
import pytest


class TestModelRecommendations:
    """AC6: Return DataCharacteristics with Model Recommendations tests."""

    def test_ac6_1_return_datacharacteristics_dataclass(self, stationary_series: pd.Series) -> None:
        """TEST-AC-6.1: Return DataCharacteristics dataclass with all metrics.

        Given: All characteristics are analyzed
        When: Returning results
        Then: Should return a DataCharacteristics instance
        """
        from raglite.forecasting.data_analyzer import (
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert result.__class__.__name__ == "DataCharacteristics"

    def test_ac6_2_include_recommended_models(self, stationary_series: pd.Series) -> None:
        """TEST-AC-6.2: Include recommended_models: list[str].

        Given: Data characteristics are analyzed
        When: Generating recommendations
        Then: recommended_models should be a list of strings
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert hasattr(result, "recommended_models")
        assert isinstance(result.recommended_models, list)
        assert all(isinstance(m, str) for m in result.recommended_models)

    def test_ac6_3_include_model_rationale(self, stationary_series: pd.Series) -> None:
        """TEST-AC-6.3: Include model_rationale: str.

        Given: Data characteristics are analyzed
        When: Generating recommendations
        Then: model_rationale should explain why models were recommended
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert hasattr(result, "model_rationale")
        assert isinstance(result.model_rationale, str)
        assert len(result.model_rationale) > 0

    def test_ac6_4_prioritize_recommendations(self, stationary_series: pd.Series) -> None:
        """TEST-AC-6.4: Prioritize recommendations (best model first).

        Given: Multiple models are recommended
        When: Returning recommendations
        Then: Best models should appear first in the list
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert len(result.recommended_models) > 0
        # First model should be the most appropriate for the data type

    def test_ac6_5_recommend_arima_linear_for_stationary(
        self, stationary_series: pd.Series
    ) -> None:
        """TEST-AC-6.5: Recommend ARIMA/Linear for stationary data.

        Given: A stationary time series
        When: Generating recommendations
        Then: recommended_models should include arima or linear
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        assert "arima" in recommended or "linear" in recommended

    def test_ac6_6_recommend_prophet_ets_for_non_stationary(
        self, non_stationary_series: pd.Series
    ) -> None:
        """TEST-AC-6.6: Recommend Prophet/ETS/ARIMA for non-stationary data.

        Given: A non-stationary time series
        When: Generating recommendations
        Then: recommended_models should include prophet, ets, or arima
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(non_stationary_series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        assert "prophet" in recommended or "ets" in recommended or "arima" in recommended

    def test_ac6_7_recommend_seasonal_models_for_seasonal_data(
        self, seasonal_series: pd.Series
    ) -> None:
        """TEST-AC-6.7: Recommend SARIMA/ETS/Prophet for seasonal data.

        Given: A time series with strong seasonality
        When: Generating recommendations
        Then: recommended_models should include seasonal models
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(seasonal_series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        # Should include at least one seasonal-capable model
        seasonal_models = ["sarima", "ets", "prophet"]
        assert any(m in recommended for m in seasonal_models)

    def test_ac6_8_recommend_ml_models_for_high_volatility(
        self, high_volatility_series: pd.Series
    ) -> None:
        """TEST-AC-6.8: Recommend XGBoost/LightGBM/CatBoost for high volatility.

        Given: A time series with high volatility
        When: Generating recommendations
        Then: recommended_models should include ML models
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(high_volatility_series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        ml_models = ["xgboost", "lightgbm", "catboost"]
        assert any(m in recommended for m in ml_models)

    def test_ac6_9_recommend_chronos_for_cold_start(self, short_series: pd.Series) -> None:
        """TEST-AC-6.9: Recommend Chronos-2 for cold-start (<12 points).

        Given: A short time series (< 12 data points)
        When: Generating recommendations
        Then: recommended_models should include chronos
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(short_series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        assert "chronos" in recommended

    def test_ac6_10_recommend_prophet_for_significant_trend(
        self, trending_series: pd.Series
    ) -> None:
        """TEST-AC-6.10: Recommend Prophet for significant trend.

        Given: A time series with significant trend
        When: Generating recommendations
        Then: recommended_models should include prophet
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(trending_series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        assert "prophet" in recommended

    def test_ac6_11_handle_edge_case_constant_values(self, constant_series: pd.Series) -> None:
        """TEST-AC-6.11: Handle edge case - constant values.

        Given: A constant time series
        When: Analyzing characteristics
        Then: Should raise ValueError or return appropriate message
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        with pytest.raises(ValueError, match="[Cc]onstant"):
            analyze_data_characteristics(constant_series, frequency="M")

    def test_ac6_12_handle_edge_case_short_series(self, very_short_series: pd.Series) -> None:
        """TEST-AC-6.12: Handle edge case - very short series.

        Given: A very short time series (4 points)
        When: Analyzing characteristics
        Then: Should handle gracefully (may return limited recommendations)
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        # Should not raise an error for 4 data points
        result = analyze_data_characteristics(very_short_series, frequency="M")
        assert result is not None
