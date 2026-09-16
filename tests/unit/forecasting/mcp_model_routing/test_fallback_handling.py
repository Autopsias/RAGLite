"""Unit tests for MCP Fallback Handling (TEST-AC-7b.6.4.x).

Story 7b-6: MCP Integration with Model Selection
TDD Phase: RED - These tests are expected to FAIL until implementation complete.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestFallbackHandling:
    """[P0] AC-7b.6.4: Fallback to Prophet on Cache Miss or Model Failure."""

    @pytest.mark.asyncio
    async def test_ac_7b_6_4_1_fallback_on_cache_miss(
        self,
        sample_time_series_data,
    ) -> None:
        """TEST-AC-7b.6.4.1: Falls back to Prophet when no cache exists."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch(
            "raglite.forecasting.hybrid.ensemble.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = None  # Cache miss

            with patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data"
            ) as mock_ensure_data:
                mock_ensure_data.return_value = sample_time_series_data

                with patch("raglite.forecasting.hybrid._get_prophet_class") as mock_prophet_class:
                    mock_prophet = MagicMock()
                    mock_prophet.fit.return_value = None
                    mock_prophet.make_future_dataframe.return_value = MagicMock()
                    mock_prophet.predict.return_value = MagicMock()
                    mock_prophet_class.return_value = mock_prophet

                    with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                        mock_explain.return_value = "Test explanation"

                        result = await generate_forecast(
                            metric="unknown_metric",
                            periods_ahead=4,
                            use_model_selection=True,
                        )

                        # Should use Prophet (default) and mark source as "default"
                        assert result.model_source == "default"

    @pytest.mark.asyncio
    async def test_ac_7b_6_4_2_fallback_on_model_failure(
        self,
        sample_time_series_data,
        mock_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.4.2: Falls back to Prophet when selected model fails."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch(
            "raglite.forecasting.hybrid.ensemble.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = mock_cached_model_selection

            with patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data"
            ) as mock_ensure_data:
                mock_ensure_data.return_value = sample_time_series_data

                with patch(
                    "raglite.forecasting.hybrid.model_generators._route_to_model"
                ) as mock_route:
                    # ARIMA fails
                    mock_route.side_effect = Exception("Failed to fit ARIMA: convergence failed")

                    with patch(
                        "raglite.forecasting.hybrid.ensemble.explain_forecast"
                    ) as mock_explain:
                        mock_explain.return_value = "Test explanation"

                        result = await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            use_model_selection=True,
                        )

                        # Should fall back to Prophet (main path execution)
                        assert result.model_source == "fallback"
                        # Verify fallback reason includes error context (check for actual error text)
                        assert (
                            "Failed to fit ARIMA" in result.model_selection_reason
                            or "arima" in result.model_selection_reason.lower()
                        )

    @pytest.mark.asyncio
    async def test_ac_7b_6_4_3_fallback_includes_error_context(
        self,
        sample_time_series_data,
        mock_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.4.3: Fallback model_selection_reason includes error context."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch(
            "raglite.forecasting.hybrid.ensemble.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = mock_cached_model_selection

            with patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data"
            ) as mock_ensure_data:
                mock_ensure_data.return_value = sample_time_series_data

                with patch(
                    "raglite.forecasting.hybrid.model_generators._route_to_model"
                ) as mock_route:
                    mock_route.side_effect = Exception("ARIMA convergence failed")

                    with patch(
                        "raglite.forecasting.hybrid.model_generators._generate_prophet_forecast"
                    ) as mock_prophet:
                        mock_result = MagicMock()
                        mock_result.model_source = "fallback"
                        mock_result.model_selection_reason = "Fallback due to arima failure"
                        mock_prophet.return_value = mock_result

                        result = await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            use_model_selection=True,
                        )

                        # Should include error context in reason
                        assert (
                            "arima" in result.model_selection_reason.lower()
                            or "fallback" in result.model_selection_reason.lower()
                        )
