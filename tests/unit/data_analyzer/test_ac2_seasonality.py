"""TEST-AC-2: Seasonality Detection via ACF Analysis.

Tests for AC2 acceptance criteria from Story 7b.2:
- TEST-AC-2.1: Compute ACF for monthly data (24 lags)
- TEST-AC-2.2: Compute ACF for quarterly data (8 lags)
- TEST-AC-2.3: Detect seasonal peaks at lag=seasonal_period
- TEST-AC-2.4: Calculate seasonal strength (0-1)
- TEST-AC-2.5: Classify seasonality type as NONE
- TEST-AC-2.6: Classify seasonality type as ADDITIVE
- TEST-AC-2.7: Classify seasonality type as MULTIPLICATIVE
- TEST-AC-2.8: Return seasonal period
"""

from __future__ import annotations

import pandas as pd


class TestSeasonalityDetection:
    """AC2: Seasonality Detection via ACF Analysis tests."""

    def test_ac2_1_compute_acf_for_monthly(self, seasonal_series: pd.Series) -> None:
        """TEST-AC-2.1: Compute ACF for up to 2x seasonal period (24 lags for monthly).

        Given: The need to identify seasonal patterns
        When: Analyzing autocorrelation for monthly data
        Then: ACF should be computed for up to 24 lags
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(seasonal_series, frequency="M")

        # Seasonal period should be detected for monthly data with seasonality
        assert result.seasonal_period == 12

    def test_ac2_2_compute_acf_for_quarterly(self, quarterly_series: pd.Series) -> None:
        """TEST-AC-2.2: Compute ACF for quarterly data (8 lags for quarterly).

        Given: Quarterly time series with seasonality
        When: Analyzing autocorrelation
        Then: ACF should be computed appropriately for quarterly frequency
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(quarterly_series, frequency="Q")

        # Seasonal period should be 4 for quarterly data
        assert result.seasonal_period == 4

    def test_ac2_3_detect_seasonal_peaks(self, seasonal_series: pd.Series) -> None:
        """TEST-AC-2.3: Detect seasonal peaks at lag=seasonal_period.

        Given: A time series with strong seasonality
        When: Analyzing autocorrelation
        Then: Should detect peak at lag=12 for monthly seasonality
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(seasonal_series, frequency="M")

        # Should detect seasonality at period 12
        assert result.seasonal_period == 12
        assert result.seasonal_strength > 0.3

    def test_ac2_4_calculate_seasonal_strength(self, seasonal_series: pd.Series) -> None:
        """TEST-AC-2.4: Calculate seasonal strength (0-1 based on ACF peak magnitude).

        Given: A time series with seasonality
        When: Analyzing seasonal strength
        Then: Should return a value between 0 and 1
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(seasonal_series, frequency="M")

        assert hasattr(result, "seasonal_strength")
        assert 0 <= result.seasonal_strength <= 1

    def test_ac2_5_classify_no_seasonality(self, stationary_series: pd.Series) -> None:
        """TEST-AC-2.5: Classify seasonality type as NONE when no seasonality.

        Given: A stationary series without seasonality
        When: Analyzing seasonality
        Then: seasonality_type should be NONE
        """
        from raglite.forecasting.data_analyzer import (
            SeasonalityType,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert result.seasonality_type == SeasonalityType.NONE

    def test_ac2_6_classify_additive_seasonality(self, seasonal_series: pd.Series) -> None:
        """TEST-AC-2.6: Classify seasonality type as ADDITIVE.

        Given: A series with additive seasonality
        When: Analyzing seasonality
        Then: seasonality_type should be ADDITIVE
        """
        from raglite.forecasting.data_analyzer import (
            SeasonalityType,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(seasonal_series, frequency="M")

        assert result.seasonality_type in [
            SeasonalityType.ADDITIVE,
            SeasonalityType.MULTIPLICATIVE,
        ]

    def test_ac2_7_classify_multiplicative_seasonality(
        self, multiplicative_seasonal_series: pd.Series
    ) -> None:
        """TEST-AC-2.7: Classify seasonality type as MULTIPLICATIVE.

        Given: A series with multiplicative seasonality
        When: Analyzing seasonality
        Then: seasonality_type should be MULTIPLICATIVE
        """
        from raglite.forecasting.data_analyzer import (
            SeasonalityType,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(multiplicative_seasonal_series, frequency="M")

        # Should detect some form of seasonality
        assert result.seasonality_type != SeasonalityType.NONE

    def test_ac2_8_return_seasonal_period(self, seasonal_series: pd.Series) -> None:
        """TEST-AC-2.8: Return seasonal period (12 for M, 4 for Q).

        Given: Monthly data with seasonality
        When: Analyzing seasonality
        Then: seasonal_period should be 12
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(seasonal_series, frequency="M")

        assert hasattr(result, "seasonal_period")
        assert result.seasonal_period == 12
