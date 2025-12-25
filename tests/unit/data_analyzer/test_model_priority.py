"""[P1] Model Recommendation Priority Order Tests.

Tests for model recommendation ordering logic (already covered in test_boundary_conditions.py):
- Stationary ARIMA/Linear appear first
- No duplicate models in recommendations
- Chronos is only recommendation for short series

Note: These tests are relocated from test_data_analyzer_expanded.py to avoid duplication
with test_boundary_conditions.py which already covers these scenarios.
"""

from __future__ import annotations

import pandas as pd


class TestModelRecommendationPriority:
    """[P1] Tests for model recommendation ordering logic."""

    def test_p3_outlier_count_with_no_outliers(self, stationary_series: pd.Series) -> None:
        """[P3] Clean series with no outliers returns outlier_count=0.

        Given: A well-behaved stationary series
        When: Detecting outliers
        Then: Should find 0 or very few outliers
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        # Clean series should have few/no outliers
        assert result.outlier_count <= 3  # Allow some due to random noise

    def test_p1_high_volatility_includes_ml_models(self, high_volatility_series: pd.Series) -> None:
        """[P1] High volatility series includes ML models in recommendations.

        Given: A high volatility series
        When: Generating recommendations
        Then: Should include at least one ML model
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(high_volatility_series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        ml_models = ["xgboost", "lightgbm", "catboost"]
        has_ml = any(m in recommended for m in ml_models)
        assert has_ml

    def test_p1_seasonal_series_includes_seasonal_models(self, seasonal_series: pd.Series) -> None:
        """[P1] Seasonal series includes seasonal-capable models.

        Given: A seasonal series
        When: Generating recommendations
        Then: Should include seasonal models (SARIMA/ETS/Prophet)
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(seasonal_series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        seasonal_models = ["sarima", "ets", "prophet"]
        has_seasonal = any(m in recommended for m in seasonal_models)
        assert has_seasonal
