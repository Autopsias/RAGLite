"""TEST-AC-3: Trend Detection via Linear Regression.

Tests for AC3 acceptance criteria from Story 7b.2:
- TEST-AC-3.1: Fit OLS regression: y = a + b*t
- TEST-AC-3.2: Calculate trend slope (b coefficient)
- TEST-AC-3.3: Calculate trend significance (p-value of slope)
- TEST-AC-3.4: Classify trend as significant if p-value < 0.05
- TEST-AC-3.5: Return direction UP for positive significant trend
- TEST-AC-3.6: Return direction DOWN for negative significant trend
- TEST-AC-3.7: Return direction FLAT for non-significant trend
"""

from __future__ import annotations

import pandas as pd


class TestTrendDetection:
    """AC3: Trend Detection via Linear Regression tests."""

    def test_ac3_1_fit_ols_regression(self, trending_series: pd.Series) -> None:
        """TEST-AC-3.1: Fit OLS regression: y = a + b*t.

        Given: The need to identify significant trends
        When: Fitting linear regression to time-series
        Then: OLS regression should be fitted
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(trending_series, frequency="M")

        # Should have trend-related attributes
        assert hasattr(result, "trend_slope")
        assert hasattr(result, "trend_significance")
        assert hasattr(result, "trend_direction")

    def test_ac3_2_calculate_trend_slope(self, trending_series: pd.Series) -> None:
        """TEST-AC-3.2: Calculate trend slope (b coefficient).

        Given: A time series with an upward trend
        When: Fitting linear regression
        Then: Slope should be positive
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(trending_series, frequency="M")

        assert result.trend_slope > 0

    def test_ac3_3_calculate_trend_significance(self, trending_series: pd.Series) -> None:
        """TEST-AC-3.3: Calculate trend significance (p-value of slope).

        Given: A time series with a significant trend
        When: Fitting linear regression
        Then: Significance (p-value) should be < 0.05
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(trending_series, frequency="M")

        assert hasattr(result, "trend_significance")
        assert result.trend_significance < 0.05

    def test_ac3_4_classify_significant_trend(self, trending_series: pd.Series) -> None:
        """TEST-AC-3.4: Classify trend as significant if p-value < 0.05.

        Given: A time series with significant upward trend
        When: Analyzing trend
        Then: Trend should be classified as significant (direction UP)
        """
        from raglite.forecasting.data_analyzer import (
            TrendDirection,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(trending_series, frequency="M")

        assert result.trend_direction == TrendDirection.UP
        assert result.trend_significance < 0.05

    def test_ac3_5_return_direction_up(self, trending_series: pd.Series) -> None:
        """TEST-AC-3.5: Return direction UP for positive significant trend.

        Given: A time series with upward trend
        When: Analyzing trend direction
        Then: Direction should be UP
        """
        from raglite.forecasting.data_analyzer import (
            TrendDirection,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(trending_series, frequency="M")

        assert result.trend_direction == TrendDirection.UP

    def test_ac3_6_return_direction_down(self, downward_trending_series: pd.Series) -> None:
        """TEST-AC-3.6: Return direction DOWN for negative significant trend.

        Given: A time series with downward trend
        When: Analyzing trend direction
        Then: Direction should be DOWN
        """
        from raglite.forecasting.data_analyzer import (
            TrendDirection,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(downward_trending_series, frequency="M")

        assert result.trend_direction == TrendDirection.DOWN

    def test_ac3_7_return_direction_flat(self, stationary_series: pd.Series) -> None:
        """TEST-AC-3.7: Return direction FLAT for non-significant trend.

        Given: A stationary time series without trend
        When: Analyzing trend direction
        Then: Direction should be FLAT (or trend non-significant)
        """
        from raglite.forecasting.data_analyzer import (
            TrendDirection,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(stationary_series, frequency="M")

        # For stationary data, expect FLAT direction or non-significant trend
        assert result.trend_direction == TrendDirection.FLAT or result.trend_significance >= 0.05
