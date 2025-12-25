"""[P1] Rationale String Validation Tests.

Tests for model_rationale string generation:
- Rationale mentions key characteristics
- Cold-start rationale mentions short series
- Rationale is never empty
"""

from __future__ import annotations

import pandas as pd


class TestModelRationaleGeneration:
    """[P1] Tests for model_rationale string generation."""

    def test_p1_rationale_mentions_key_characteristics(
        self, mixed_characteristics_series: pd.Series
    ) -> None:
        """[P1] Rationale string mentions detected characteristics.

        Given: A series with trend + seasonality + volatility
        When: Generating rationale
        Then: Should mention trend, seasonality, or volatility
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(mixed_characteristics_series, frequency="M")

        rationale_lower = result.model_rationale.lower()
        # Should mention at least one characteristic
        mentions_trend = "trend" in rationale_lower
        mentions_seasonal = "season" in rationale_lower
        mentions_volatility = "volatil" in rationale_lower or "cv=" in rationale_lower

        assert mentions_trend or mentions_seasonal or mentions_volatility

    def test_p1_rationale_for_cold_start_mentions_short_series(
        self, short_series: pd.Series
    ) -> None:
        """[P1] Cold-start rationale mentions series length.

        Given: A short series (<12 points)
        When: Generating rationale
        Then: Should mention "short series" or point count
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(short_series, frequency="M")

        rationale_lower = result.model_rationale.lower()
        # Should mention short series or point count
        assert "short" in rationale_lower or "points" in rationale_lower

    def test_p2_rationale_not_empty_for_any_series(self, stationary_series: pd.Series) -> None:
        """[P2] Rationale is never empty string.

        Given: Any valid series
        When: Generating rationale
        Then: model_rationale should be non-empty
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        result = analyze_data_characteristics(stationary_series, frequency="M")

        assert len(result.model_rationale) > 0
        assert result.model_rationale != ""
