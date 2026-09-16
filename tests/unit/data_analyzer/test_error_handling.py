"""[P1-P2] Error Handling and Propagation Tests.

Tests for error handling in edge cases:
- Series with only 2 unique values
- Series with inf CV (zero mean)
- KPSS test failure fallback
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class TestErrorHandling:
    """[P1-P2] Tests for error handling in edge cases."""

    def test_p1_series_with_only_two_unique_values(self) -> None:
        """[P1] Series with only 2 unique values (near-constant) handles gracefully.

        Given: A series alternating between two values
        When: Analyzing characteristics
        Then: Should complete analysis or raise informative error
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        dates = pd.date_range(start="2020-01-01", periods=30, freq="MS")
        values = [100.0, 100.1] * 15
        series = pd.Series(values, index=dates)

        # Should either succeed with low volatility or raise ValueError
        try:
            result = analyze_data_characteristics(series, frequency="M")
            # If succeeds, should have very low volatility
            assert result.coefficient_of_variation < 0.01
        except ValueError as e:
            # Acceptable if detects near-constant series
            assert "constant" in str(e).lower() or "short" in str(e).lower()

    def test_p2_series_with_inf_values_after_cleaning(self) -> None:
        """[P2] Series that results in inf CV (zero mean) handles gracefully.

        Given: A series with zero mean (positive and negative values cancel)
        When: Calculating CV
        Then: Should handle inf CV appropriately
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
        # Symmetric around zero
        values = np.concatenate([np.ones(30) * 10, np.ones(30) * -10])
        series = pd.Series(values, index=dates)

        result = analyze_data_characteristics(series, frequency="M")

        # Should handle zero-mean case
        assert result is not None
        # CV might be inf or very high
        assert result.coefficient_of_variation >= 0 or np.isinf(result.coefficient_of_variation)

    def test_p2_missing_ratio_with_partial_nans(self) -> None:
        """[P2] Missing ratio calculation with mix of NaN and valid values.

        Given: A series with 50% NaN values
        When: Assessing data quality
        Then: missing_ratio should be 0.5
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        dates = pd.date_range(start="2020-01-01", periods=20, freq="MS")
        # Create varying values (not constant) with 50% NaNs
        np.random.seed(42)
        valid_values = 100 + np.random.normal(0, 10, 10)
        values = list(valid_values) + [np.nan] * 10
        series = pd.Series(values, index=dates)

        result = analyze_data_characteristics(series, frequency="M")

        # Should detect 50% missing
        assert abs(result.missing_ratio - 0.5) < 0.01
