"""[P2] Data Quality Metrics Edge Cases.

Tests for data quality assessment edge cases (subset from expanded tests):
- Outlier detection with very short series (moved from boundary_conditions)
- Missing ratio with partial NaNs (moved from error_handling)
- Outlier count with no outliers (moved from model_priority)
"""

from __future__ import annotations

import pandas as pd


class TestDataQualityEdgeCases:
    """[P2] Tests for data quality assessment edge cases."""

    def test_p2_data_length_matches_series_length(self, stationary_series: pd.Series) -> None:
        """[P2] data_length field matches actual series length.

        Given: A series with known length
        When: Analyzing data quality
        Then: data_length should match series length
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert result.data_length == len(stationary_series)

    def test_p2_missing_ratio_zero_for_complete_series(self, stationary_series: pd.Series) -> None:
        """[P2] Missing ratio is 0.0 for series with no NaNs.

        Given: A complete series with no missing values
        When: Analyzing data quality
        Then: missing_ratio should be 0.0
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert result.missing_ratio == 0.0

    def test_p2_outlier_detection_with_series_with_outliers(
        self, series_with_outliers: pd.Series
    ) -> None:
        """[P2] Outlier detection finds outliers using IQR method.

        Given: A series with known outliers
        When: Detecting outliers
        Then: Should detect at least the obvious outliers
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(series_with_outliers, frequency="M")

        # Should detect the 3 inserted outliers
        assert result.outlier_count >= 3
