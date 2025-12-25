"""TEST-AC-5: Data Quality Metrics.

Tests for AC5 acceptance criteria from Story 7b.2:
- TEST-AC-5.1: Calculate data length (number of observations)
- TEST-AC-5.2: Calculate missing ratio (NaN / total)
- TEST-AC-5.3: Count outliers using IQR method
- TEST-AC-5.4: Return quality metrics in DataCharacteristics
- TEST-AC-5.5: Return missing_ratio=0 for complete data
"""

from __future__ import annotations

import pandas as pd


class TestDataQualityMetrics:
    """AC5: Data Quality Metrics tests."""

    def test_ac5_1_calculate_data_length(self, stationary_series: pd.Series) -> None:
        """TEST-AC-5.1: Calculate data length (number of observations).

        Given: The need to assess data suitability for modeling
        When: Analyzing data quality
        Then: data_length should be calculated
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert hasattr(result, "data_length")
        assert result.data_length == 60

    def test_ac5_2_calculate_missing_ratio(self, series_with_nans: pd.Series) -> None:
        """TEST-AC-5.2: Calculate missing ratio (NaN / total).

        Given: A time series with missing values
        When: Analyzing data quality
        Then: missing_ratio should be calculated correctly
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(series_with_nans, frequency="M")

        assert hasattr(result, "missing_ratio")
        # 5 NaNs out of 60 observations
        expected_ratio = 5 / 60
        assert abs(result.missing_ratio - expected_ratio) < 0.01

    def test_ac5_3_count_outliers_using_iqr(self, series_with_outliers: pd.Series) -> None:
        """TEST-AC-5.3: Count outliers using IQR method.

        Given: A time series with outliers
        When: Analyzing data quality
        Then: outlier_count should detect outliers using IQR
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(series_with_outliers, frequency="M")

        assert hasattr(result, "outlier_count")
        # Should detect at least the 3 obvious outliers
        assert result.outlier_count >= 3

    def test_ac5_4_return_quality_metrics(self, stationary_series: pd.Series) -> None:
        """TEST-AC-5.4: Return quality metrics in DataCharacteristics.

        Given: Any time series
        When: Analyzing data quality
        Then: DataCharacteristics should include all quality metrics
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert hasattr(result, "data_length")
        assert hasattr(result, "missing_ratio")
        assert hasattr(result, "outlier_count")

    def test_ac5_5_no_missing_values(self, stationary_series: pd.Series) -> None:
        """TEST-AC-5.5: Return missing_ratio=0 for complete data.

        Given: A time series without missing values
        When: Analyzing data quality
        Then: missing_ratio should be 0
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert result.missing_ratio == 0.0
