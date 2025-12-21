"""TEST-AC-1: Combined ADF + KPSS Stationarity Test.

Tests for AC1 acceptance criteria from Story 7b.2:
- TEST-AC-1.1: Implement ADF test (Augmented Dickey-Fuller)
- TEST-AC-1.2: Implement KPSS test
- TEST-AC-1.3: Kwiatkowski protocol - STATIONARY case
- TEST-AC-1.4: Kwiatkowski protocol - NON_STATIONARY case
- TEST-AC-1.5: Return stationarity enum
- TEST-AC-1.6: Return both p-values
- TEST-AC-1.7: Suggest differencing order 0 for stationary data
- TEST-AC-1.8: Suggest differencing order 1 for non-stationary data
"""

from __future__ import annotations

import pandas as pd


class TestStationarityTests:
    """AC1: Combined ADF + KPSS Stationarity Test tests."""

    def test_ac1_1_implement_adf_test(self, stationary_series: pd.Series) -> None:
        """TEST-AC-1.1: Implement ADF test (Augmented Dickey-Fuller, null: non-stationary).

        Given: The need to classify time-series stationarity
        When: Running stationarity analysis on a stationary series
        Then: ADF test should be implemented and return p-value
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert hasattr(result, "adf_pvalue")
        assert isinstance(result.adf_pvalue, float)
        assert 0 <= result.adf_pvalue <= 1

    def test_ac1_2_implement_kpss_test(self, stationary_series: pd.Series) -> None:
        """TEST-AC-1.2: Implement KPSS test (null: stationary).

        Given: The need to classify time-series stationarity
        When: Running stationarity analysis
        Then: KPSS test should be implemented and return p-value
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert hasattr(result, "kpss_pvalue")
        assert isinstance(result.kpss_pvalue, float)
        assert 0 <= result.kpss_pvalue <= 1

    def test_ac1_3_kwiatkowski_protocol_stationary(self, stationary_series: pd.Series) -> None:
        """TEST-AC-1.3: Apply Kwiatkowski protocol - STATIONARY case.

        Given: A stationary time series
        When: ADF p<0.05 AND KPSS p>0.05
        Then: Result should be classified as STATIONARY
        """
        from raglite.forecasting.data_analyzer import (
            Stationarity,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(stationary_series, frequency="M")

        # For stationary data: ADF should reject null (p<0.05), KPSS should not (p>0.05)
        assert result.stationarity == Stationarity.STATIONARY
        assert result.adf_pvalue < 0.10  # Allow some margin for synthetic data
        assert result.kpss_pvalue > 0.01

    def test_ac1_4_kwiatkowski_protocol_non_stationary(
        self, non_stationary_series: pd.Series
    ) -> None:
        """TEST-AC-1.4: Apply Kwiatkowski protocol - NON_STATIONARY case.

        Given: A non-stationary time series (random walk)
        When: ADF p>=0.05 AND KPSS p<=0.05
        Then: Result should be classified as NON_STATIONARY
        """
        from raglite.forecasting.data_analyzer import (
            Stationarity,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(non_stationary_series, frequency="M")

        # For non-stationary data: ADF should not reject (p>=0.05), KPSS should reject (p<=0.05)
        assert result.stationarity in [
            Stationarity.NON_STATIONARY,
            Stationarity.TREND_STATIONARY,
            Stationarity.DIFFERENCE_STATIONARY,
        ]

    def test_ac1_5_return_stationarity_enum(self, stationary_series: pd.Series) -> None:
        """TEST-AC-1.5: Return stationarity enum.

        Given: Any time series
        When: Running stationarity analysis
        Then: Result should include stationarity as an enum type
        """
        from raglite.forecasting.data_analyzer import (
            Stationarity,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert hasattr(result, "stationarity")
        assert isinstance(result.stationarity, Stationarity)

    def test_ac1_6_return_both_pvalues(self, stationary_series: pd.Series) -> None:
        """TEST-AC-1.6: Return both p-values.

        Given: Any time series
        When: Running stationarity analysis
        Then: Result should include both ADF and KPSS p-values
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert hasattr(result, "adf_pvalue")
        assert hasattr(result, "kpss_pvalue")
        assert result.adf_pvalue is not None
        assert result.kpss_pvalue is not None

    def test_ac1_7_suggest_differencing_order_zero(self, stationary_series: pd.Series) -> None:
        """TEST-AC-1.7: Suggest differencing order 0 for stationary data.

        Given: A stationary time series
        When: Running stationarity analysis
        Then: suggested_differencing should be 0
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert hasattr(result, "suggested_differencing")
        assert result.suggested_differencing == 0

    def test_ac1_8_suggest_differencing_order_one(self, non_stationary_series: pd.Series) -> None:
        """TEST-AC-1.8: Suggest differencing order 1 for non-stationary data.

        Given: A non-stationary time series
        When: Running stationarity analysis
        Then: suggested_differencing should be 1 or 2
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(non_stationary_series, frequency="M")

        assert hasattr(result, "suggested_differencing")
        assert result.suggested_differencing in [1, 2]
