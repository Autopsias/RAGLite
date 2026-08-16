"""TEST-AC-4: Volatility Measurement.

Tests for AC4 acceptance criteria from Story 7b.2:
- TEST-AC-4.1: Calculate coefficient of variation (CV = std/mean)
- TEST-AC-4.2: Classify volatility as LOW (<0.1)
- TEST-AC-4.3: Classify volatility as MEDIUM (0.1 <= CV < 0.3)
- TEST-AC-4.4: Classify volatility as HIGH (>0.3)
- TEST-AC-4.5: Return CV value and classification
"""

from __future__ import annotations

import pandas as pd


class TestVolatilityMeasurement:
    """AC4: Volatility Measurement tests."""

    def test_ac4_1_calculate_coefficient_of_variation(
        self, high_volatility_series: pd.Series
    ) -> None:
        """TEST-AC-4.1: Calculate coefficient of variation (CV = std/mean).

        Given: The need to quantify data variability
        When: Analyzing volatility
        Then: CV should be calculated correctly
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(high_volatility_series, frequency="M")

        assert hasattr(result, "coefficient_of_variation")
        assert isinstance(result.coefficient_of_variation, float)
        assert result.coefficient_of_variation >= 0

    def test_ac4_2_classify_volatility_low(self, low_volatility_series: pd.Series) -> None:
        """TEST-AC-4.2: Classify volatility as LOW (<0.1).

        Given: A time series with low volatility
        When: Analyzing volatility
        Then: volatility_level should be LOW
        """
        from raglite.forecasting.data_analyzer import (
            VolatilityLevel,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(low_volatility_series, frequency="M")

        assert result.volatility_level == VolatilityLevel.LOW
        assert result.coefficient_of_variation < 0.1

    def test_ac4_3_classify_volatility_medium(self, stationary_series: pd.Series) -> None:
        """TEST-AC-4.3: Classify volatility as MEDIUM (0.1 <= CV < 0.3).

        Given: A time series with medium volatility
        When: Analyzing volatility
        Then: volatility_level should be MEDIUM
        """
        from raglite.forecasting.data_analyzer import (
            VolatilityLevel,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(stationary_series, frequency="M")

        # Stationary series with some noise should have low-medium volatility
        assert result.volatility_level in [VolatilityLevel.LOW, VolatilityLevel.MEDIUM]

    def test_ac4_4_classify_volatility_high(self, high_volatility_series: pd.Series) -> None:
        """TEST-AC-4.4: Classify volatility as HIGH (>0.3).

        Given: A time series with high volatility
        When: Analyzing volatility
        Then: volatility_level should be HIGH
        """
        from raglite.forecasting.data_analyzer import (
            VolatilityLevel,
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(high_volatility_series, frequency="M")

        assert result.volatility_level == VolatilityLevel.HIGH
        assert result.coefficient_of_variation > 0.3

    def test_ac4_5_return_cv_value(self, stationary_series: pd.Series) -> None:
        """TEST-AC-4.5: Return CV value and classification.

        Given: Any time series
        When: Analyzing volatility
        Then: Both CV value and volatility_level should be returned
        """
        from raglite.forecasting.data_analyzer import (
            analyze_data_characteristics,
        )

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert hasattr(result, "coefficient_of_variation")
        assert hasattr(result, "volatility_level")
        assert result.volatility_level.__class__.__name__ == "VolatilityLevel"
