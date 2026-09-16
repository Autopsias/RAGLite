"""[P2] Rolling Volatility Edge Cases.

Tests for rolling volatility calculation edge cases:
- Series shorter than window has rolling_volatility=None
- Series with sufficient data has rolling_volatility calculated
- Rolling volatility matches manual calculation
"""

from __future__ import annotations

import pandas as pd


class TestRollingVolatilityEdgeCases:
    """[P2] Tests for rolling volatility calculation edge cases."""

    def test_p2_rolling_volatility_with_short_series(self, short_window_series: pd.Series) -> None:
        """[P2] Series shorter than window (default=12) has rolling_volatility=None.

        Given: A series with 8 data points (less than default window=12)
        When: Measuring volatility
        Then: rolling_volatility should be None
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(short_window_series, frequency="M")

        # Should have CV calculated but not rolling volatility
        assert result.coefficient_of_variation > 0
        assert result.rolling_volatility is None

    def test_p2_rolling_volatility_with_sufficient_data(self, stationary_series: pd.Series) -> None:
        """[P2] Series with >= 12 points has rolling_volatility calculated.

        Given: A series with 60 data points
        When: Measuring volatility
        Then: rolling_volatility should be a positive float
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        # Should calculate rolling volatility
        assert result.rolling_volatility is not None
        assert isinstance(result.rolling_volatility, float)
        assert result.rolling_volatility > 0

    def test_p3_rolling_volatility_custom_window(self, stationary_series: pd.Series) -> None:
        """[P3] Verify rolling volatility uses mean of rolling window.

        Given: A known series
        When: Calculating rolling volatility
        Then: Result should match manual calculation
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        # Manual calculation for comparison
        rolling_std = stationary_series.rolling(window=12).std()
        expected_rolling_vol = rolling_std.mean()

        # Should be close to manual calculation
        assert result.rolling_volatility is not None
        assert abs(result.rolling_volatility - expected_rolling_vol) < 0.01
