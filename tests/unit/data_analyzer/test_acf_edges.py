"""[P2-P3] ACF Computation Edge Cases.

Tests for ACF computation boundary conditions:
- ACF with series length equal to period
- ACF with series shorter than double period
"""

from __future__ import annotations

import pandas as pd


class TestACFEdgeCases:
    """[P2-P3] Tests for ACF computation boundary conditions."""

    def test_p2_acf_with_series_length_equal_to_period(self) -> None:
        """[P2] Series with exactly seasonal_period points (12 for M) computes ACF.

        Given: A monthly series with exactly 12 data points
        When: Computing ACF for seasonality
        Then: Should handle without error (nlags limited by series length)
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        dates = pd.date_range(start="2024-01-01", periods=12, freq="MS")
        values = [100, 105, 110, 108, 115, 120, 118, 125, 130, 128, 135, 140]
        series = pd.Series(values, index=dates)

        result = analyze_data_characteristics(series, frequency="M")

        # Should complete without error
        assert result is not None
        # Seasonal period might not be detected due to short length
        assert result.seasonal_strength >= 0

    def test_p3_acf_with_series_shorter_than_double_period(self, short_series: pd.Series) -> None:
        """[P3] Series with length < 2*period returns SeasonalityType.NONE.

        Given: A series with 6 points (< 24 for 2*M period)
        When: Detecting seasonality
        Then: Should return NONE due to insufficient lags
        """
        from raglite.forecasting.data_analyzer import (
            SeasonalityType,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(short_series, frequency="M")

        # Should detect insufficient lags
        assert result.seasonality_type == SeasonalityType.NONE
        assert result.seasonal_period is None
