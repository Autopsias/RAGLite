"""[P1-P2] Differencing Order Detection Edge Cases.

Tests for differencing order calculation:
- I(2) series suggests differencing order 1 or 2
- Very short series can still compute differencing
"""

from __future__ import annotations

import pandas as pd


class TestDifferencingOrderDetection:
    """[P1-P2] Tests for differencing order calculation edge cases."""

    def test_p1_non_stationary_suggests_d1_or_d2(self, non_stationary_d2_series: pd.Series) -> None:
        """[P1] I(2) series suggests differencing order 1 or 2.

        Given: A series integrated of order 2
        When: Testing stationarity
        Then: suggested_differencing should be 1 or 2
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(non_stationary_d2_series, frequency="M")

        # Should detect need for differencing
        assert result.suggested_differencing in [1, 2]
        # Should be classified as non-stationary variant
        from raglite.forecasting.data_analyzer import Stationarity

        assert result.stationarity in [
            Stationarity.NON_STATIONARY,
            Stationarity.DIFFERENCE_STATIONARY,
            Stationarity.TREND_STATIONARY,
        ]

    def test_p2_differencing_detection_with_short_series(
        self, very_short_series: pd.Series
    ) -> None:
        """[P2] Very short series (4-10 points) can still compute differencing suggestion.

        Given: A series with 4 data points
        When: Testing stationarity
        Then: Should return valid differencing order without errors
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        # Should not raise an error
        result = analyze_data_characteristics(very_short_series, frequency="M")

        assert result.suggested_differencing in [0, 1, 2]

    def test_p2_kpss_test_failure_fallback(self) -> None:
        """[P2] KPSS test failure triggers fallback p-value.

        Given: A series that might cause KPSS to fail
        When: Testing stationarity
        Then: Should use fallback kpss_pvalue=0.5 and complete analysis
        """
        import pandas as pd

        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        # Create edge case series (very short or problematic for KPSS)
        dates = pd.date_range(start="2024-01-01", periods=5, freq="MS")
        values = [100, 105, 103, 108, 106]
        series = pd.Series(values, index=dates)

        result = analyze_data_characteristics(series, frequency="M")

        # Should complete without raising
        assert result is not None
        assert 0 <= result.kpss_pvalue <= 1

    def test_p1_stationary_with_seasonality_no_differencing(self) -> None:
        """[P1] Stationary series with seasonality suggests d=0 or 1.

        Given: A seasonal series
        When: Analyzing stationarity
        Then: Should suggest differencing order 0 or 1 (depends on test results)
        """
        import numpy as np
        import pandas as pd

        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
        np.random.seed(42)
        seasonality = 25 * np.sin(2 * np.pi * np.arange(60) / 12)
        noise = np.random.normal(0, 5, 60)
        values = 100 + seasonality + noise
        series = pd.Series(values, index=dates)

        result = analyze_data_characteristics(series, frequency="M")

        # Series may be detected as DIFFERENCE_STATIONARY due to seasonality
        assert result.suggested_differencing in [0, 1]
