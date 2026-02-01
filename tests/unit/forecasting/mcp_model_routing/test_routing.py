"""Unit tests for MCP Model Routing (TEST-AC-7b.6.2.x).

Story 7b-6: MCP Integration with Model Selection
TDD Phase: RED - These tests are expected to FAIL until implementation complete.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestModelRouting:
    """[P0] AC-7b.6.2: Route to Correct Model."""

    def test_ac_7b_6_2_1_route_to_model_function_exists(self) -> None:
        """TEST-AC-7b.6.2.1: _route_to_model function exists."""
        from raglite.forecasting.hybrid import _route_to_model

        assert callable(_route_to_model)

    def test_ac_7b_6_2_2_route_to_model_supports_all_models(self) -> None:
        """TEST-AC-7b.6.2.2: _route_to_model supports all 9 model types."""
        # This test verifies the model_routers dict contains all expected models
        import inspect

        from raglite.forecasting.hybrid import _route_to_model

        # Get the source code of _route_to_model to verify it supports all models
        source = inspect.getsource(_route_to_model)

        expected_models = [
            "arima",
            "ets",
            "prophet",
            "xgboost",
            "lightgbm",
            "catboost",
            "chronos",
            "tft",
            "linear",
        ]

        for model in expected_models:
            assert f'"{model}"' in source or f"'{model}'" in source, (
                f"Model {model} should be supported in _route_to_model"
            )

    @pytest.mark.asyncio
    async def test_ac_7b_6_2_3_route_to_arima(self, sample_time_series_data) -> None:
        """TEST-AC-7b.6.2.3: _route_to_model routes arima to _generate_arima_forecast."""
        from raglite.forecasting.hybrid import _route_to_model

        with patch(
            "raglite.forecasting.hybrid.model_generators._generate_arima_forecast"
        ) as mock_arima:
            mock_arima.return_value = MagicMock()

            await _route_to_model(
                model_name="arima",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )

            mock_arima.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_7b_6_2_4_route_to_ets(self, sample_time_series_data) -> None:
        """TEST-AC-7b.6.2.4: _route_to_model routes ets to _generate_ets_forecast."""
        from raglite.forecasting.hybrid import _route_to_model

        with patch(
            "raglite.forecasting.hybrid.model_generators._generate_ets_forecast"
        ) as mock_ets:
            mock_ets.return_value = MagicMock()

            await _route_to_model(
                model_name="ets",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )

            mock_ets.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_7b_6_2_5_route_to_prophet(self, sample_time_series_data) -> None:
        """TEST-AC-7b.6.2.5: _route_to_model routes prophet to _generate_prophet_forecast."""
        from raglite.forecasting.hybrid import _route_to_model

        with patch(
            "raglite.forecasting.hybrid.model_generators._generate_prophet_forecast"
        ) as mock_prophet:
            mock_prophet.return_value = MagicMock()

            await _route_to_model(
                model_name="prophet",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )

            mock_prophet.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_7b_6_2_6_route_to_xgboost(self, sample_time_series_data) -> None:
        """TEST-AC-7b.6.2.6: _route_to_model routes xgboost to _generate_xgboost_forecast."""
        from raglite.forecasting.hybrid import _route_to_model

        with patch(
            "raglite.forecasting.hybrid.model_generators._generate_xgboost_forecast"
        ) as mock_xgboost:
            mock_xgboost.return_value = MagicMock()

            await _route_to_model(
                model_name="xgboost",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )

            mock_xgboost.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_7b_6_2_7_route_unknown_model_raises_error(
        self, sample_time_series_data
    ) -> None:
        """TEST-AC-7b.6.2.7: _route_to_model raises ValueError for unknown model."""
        from raglite.forecasting.hybrid import _route_to_model

        with pytest.raises(ValueError, match="Unknown model"):
            await _route_to_model(
                model_name="unknown_model",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )
