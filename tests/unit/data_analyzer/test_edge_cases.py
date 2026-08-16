"""Edge Case Tests for Data Characteristics Analyzer.

Additional edge case tests for robustness:
- Empty series handling
- Very short series (3 points)
- All NaN values
- Negative values
- Zero mean series
- Frequency auto-detection
- Complete field validation
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


class TestEdgeCases:
    """Additional edge case tests for robustness."""

    def test_edge_case_empty_series(self) -> None:
        """Test handling of empty series.

        Given: An empty pandas Series
        When: Calling analyze_data_characteristics
        Then: Should raise appropriate error
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        empty_series = pd.Series([], dtype=float)

        with pytest.raises(ValueError):
            analyze_data_characteristics(empty_series, frequency="M")

    def test_edge_case_three_points(self) -> None:
        """Test handling of series with exactly 3 points.

        Given: A series with only 3 data points
        When: Calling analyze_data_characteristics
        Then: Should raise ValueError (minimum 4 required)
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        dates = pd.date_range(start="2024-01-01", periods=3, freq="MS")
        short = pd.Series([100, 105, 110], index=dates)

        with pytest.raises(ValueError, match="[Ss]hort|[Mm]inimum"):
            analyze_data_characteristics(short, frequency="M")

    def test_edge_case_all_nans(self) -> None:
        """Test handling of series with all NaN values.

        Given: A series with all NaN values
        When: Calling analyze_data_characteristics
        Then: Should raise ValueError
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        dates = pd.date_range(start="2020-01-01", periods=30, freq="MS")
        all_nan = pd.Series([np.nan] * 30, index=dates)

        with pytest.raises(ValueError):
            analyze_data_characteristics(all_nan, frequency="M")

    def test_edge_case_negative_values(self) -> None:
        """Test handling of series with negative values.

        Given: A series with negative values
        When: Analyzing volatility
        Then: Should handle correctly (CV uses absolute mean)
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        np.random.seed(42)
        dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
        values = -100 + np.random.normal(0, 10, 60)
        negative_series = pd.Series(values, index=dates)

        result = analyze_data_characteristics(negative_series, frequency="M")

        # Should handle negative mean gracefully
        assert result is not None
        assert result.coefficient_of_variation >= 0

    def test_edge_case_zero_mean(self) -> None:
        """Test handling of series with zero mean.

        Given: A series centered around zero
        When: Analyzing volatility
        Then: Should handle CV calculation gracefully
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        np.random.seed(42)
        dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
        values = np.random.normal(0, 5, 60)  # Mean ~0
        zero_mean_series = pd.Series(values, index=dates)

        result = analyze_data_characteristics(zero_mean_series, frequency="M")

        # Should handle zero mean (CV may be inf or handled specially)
        assert result is not None

    def test_edge_case_frequency_detection(self) -> None:
        """Test auto-detection of frequency from series index.

        Given: A series with DatetimeIndex but no explicit frequency
        When: Calling analyze_data_characteristics without frequency
        Then: Should auto-detect frequency
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
        values = np.linspace(100, 200, 60)
        series = pd.Series(values, index=dates)

        # Should auto-detect monthly frequency
        result = analyze_data_characteristics(series)
        assert result is not None

    def test_datacharacteristics_has_all_fields(self, stationary_series: pd.Series) -> None:
        """Test that DataCharacteristics has all required fields.

        Given: A valid time series
        When: Analyzing characteristics
        Then: All required fields should be present
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        # Stationarity fields
        assert hasattr(result, "stationarity")
        assert hasattr(result, "adf_pvalue")
        assert hasattr(result, "kpss_pvalue")
        assert hasattr(result, "suggested_differencing")

        # Seasonality fields
        assert hasattr(result, "seasonality_type")
        assert hasattr(result, "seasonal_period")
        assert hasattr(result, "seasonal_strength")

        # Trend fields
        assert hasattr(result, "trend_slope")
        assert hasattr(result, "trend_significance")
        assert hasattr(result, "trend_direction")

        # Volatility fields
        assert hasattr(result, "coefficient_of_variation")
        assert hasattr(result, "volatility_level")

        # Data quality fields
        assert hasattr(result, "data_length")
        assert hasattr(result, "missing_ratio")
        assert hasattr(result, "outlier_count")

        # Recommendations
        assert hasattr(result, "recommended_models")
        assert hasattr(result, "model_rationale")
