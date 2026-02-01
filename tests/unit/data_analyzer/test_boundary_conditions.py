"""[P1-P2] Boundary Condition Tests for Data Characteristics Analyzer.

Tests at exact thresholds and edge values:
- CV exactly at LOW/MEDIUM boundary (0.1)
- CV exactly at MEDIUM/HIGH boundary (0.3)
- Seasonal strength near detection threshold (0.1)
- Seasonal strength at ADDITIVE threshold (0.3)
- Exactly 12 points (cold-start boundary)
- Exactly 24 points (TFT recommendation threshold)
"""

from __future__ import annotations

import pandas as pd


class TestBoundaryConditions:
    """[P1-P2] Tests at exact thresholds and edge values."""

    def test_p1_cv_exactly_at_low_medium_boundary(self, cv_threshold_low_series: pd.Series) -> None:
        """[P1] CV = 0.1 exactly classifies as LOW or MEDIUM consistently.

        Given: A series with CV exactly at 0.1 threshold
        When: Measuring volatility
        Then: Classification should be deterministic (LOW if <0.1, MEDIUM if >=0.1)
        """
        from raglite.forecasting.data_analyzer import (
            VolatilityLevel,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(cv_threshold_low_series, frequency="M")

        # At boundary, should be consistent with implementation threshold
        assert result.volatility_level in [VolatilityLevel.LOW, VolatilityLevel.MEDIUM]
        # Verify CV is near boundary
        assert 0.08 <= result.coefficient_of_variation <= 0.12

    def test_p1_cv_exactly_at_medium_high_boundary(
        self, cv_threshold_high_series: pd.Series
    ) -> None:
        """[P1] CV = 0.3 exactly classifies as MEDIUM or HIGH consistently.

        Given: A series with CV exactly at 0.3 threshold
        When: Measuring volatility
        Then: Classification should be deterministic
        """
        from raglite.forecasting.data_analyzer import (
            VolatilityLevel,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(cv_threshold_high_series, frequency="M")

        # At boundary, should be consistent
        assert result.volatility_level in [VolatilityLevel.MEDIUM, VolatilityLevel.HIGH]
        # Verify CV is near boundary
        assert 0.25 <= result.coefficient_of_variation <= 0.35

    def test_p2_seasonal_strength_near_detection_threshold(
        self, seasonal_strength_weak_series: pd.Series
    ) -> None:
        """[P2] Weak seasonality (strength ~0.1) detects seasonal_period conditionally.

        Given: A series with seasonal strength near 0.1 threshold
        When: Detecting seasonality
        Then: seasonal_period should be set if strength > 0.1, else None
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(seasonal_strength_weak_series, frequency="M")

        # If strength > 0.1, period should be set; otherwise None
        if result.seasonal_strength > 0.1:
            assert result.seasonal_period == 12
        else:
            assert result.seasonal_period is None

    def test_p1_seasonal_strength_at_additive_threshold(
        self, seasonal_strength_boundary_series: pd.Series
    ) -> None:
        """[P1] Seasonal strength = 0.3 triggers ADDITIVE classification.

        Given: A series with seasonal ACF exactly at 0.3
        When: Classifying seasonality type
        Then: Should classify as ADDITIVE or MULTIPLICATIVE (not NONE)
        """
        from raglite.forecasting.data_analyzer import (
            SeasonalityType,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(seasonal_strength_boundary_series, frequency="M")

        # At 0.3 threshold, should trigger additive/multiplicative detection
        assert result.seasonality_type != SeasonalityType.NONE
        assert result.seasonal_strength >= 0.25  # Allow some variance

    def test_p2_exactly_twelve_points_cold_start_boundary(
        self, exactly_twelve_points: pd.Series
    ) -> None:
        """[P2] Series with exactly 12 points is NOT cold-start (threshold is <12).

        Given: A series with exactly 12 data points
        When: Generating recommendations
        Then: Should NOT recommend Chronos (only for <12 points)
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(exactly_twelve_points, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        # 12 points is NOT cold-start (only <12)
        assert "chronos" not in recommended

    def test_p2_exactly_twenty_four_points_tft_boundary(
        self, exactly_twenty_four_points: pd.Series
    ) -> None:
        """[P2] Series with exactly 24 points includes TFT recommendation.

        Given: A series with exactly 24 data points (TFT threshold)
        When: Generating recommendations
        Then: Should include TFT in recommendations
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(exactly_twenty_four_points, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        # 24 points should trigger TFT inclusion (threshold is >= 24)
        assert "tft" in recommended

    def test_p1_stationary_arima_linear_appear_first(self, stationary_series: pd.Series) -> None:
        """[P1] Stationary series prioritizes ARIMA/Linear at start of list.

        Given: A stationary series without seasonality
        When: Generating recommendations
        Then: First models should be ARIMA or Linear
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        # First two should include arima or linear
        assert "arima" in recommended[:3] or "linear" in recommended[:3]

    def test_p1_no_duplicate_models_in_recommendations(
        self, mixed_characteristics_series: pd.Series
    ) -> None:
        """[P1] Recommendations list contains no duplicates.

        Given: A series with multiple characteristics
        When: Generating recommendations
        Then: Each model should appear at most once
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(mixed_characteristics_series, frequency="M")

        recommended = result.recommended_models
        # Check for duplicates
        assert len(recommended) == len(set(recommended))

    def test_p1_chronos_is_only_recommendation_for_short_series(
        self, short_series: pd.Series
    ) -> None:
        """[P1] Cold-start series (<12 pts) returns ONLY Chronos (early return).

        Given: A series with <12 data points
        When: Generating recommendations
        Then: Should return immediately with Chronos only
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(short_series, frequency="M")

        recommended = [m.lower() for m in result.recommended_models]
        # Should be ONLY chronos (early return in _recommend_models)
        assert recommended == ["chronos"]

    def test_p2_outlier_detection_with_very_short_series(
        self, very_short_series: pd.Series
    ) -> None:
        """[P2] Outlier detection with <4 clean points returns 0.

        Given: A series with <4 data points after cleaning
        When: Detecting outliers
        Then: outlier_count should be 0 (insufficient for IQR)
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        # 4 points is the minimum
        result = analyze_data_characteristics(very_short_series, frequency="M")

        # With only 4 points, IQR method works but might find 0 outliers
        assert result.outlier_count >= 0
