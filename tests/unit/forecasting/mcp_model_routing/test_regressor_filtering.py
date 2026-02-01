"""Unit tests for MCP Regressor Filtering (TEST-AC-7b.6.3.x).

Story 7b-6: MCP Integration with Model Selection
TDD Phase: RED - These tests are expected to FAIL until implementation complete.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestRegressorFiltering:
    """[P0] AC-7b.6.3: Use Selected Regressor Set."""

    @pytest.mark.asyncio
    async def test_ac_7b_6_3_1_filters_regressors_to_cached_set(
        self,
        sample_time_series_data,
        mock_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.3.1: Only cached regressors are passed to model."""
        import pandas as pd

        from raglite.forecasting.hybrid import generate_forecast

        # Provide more regressors than cached selection specifies
        all_regressors = {
            "gas_price": pd.Series([1.0, 2.0, 3.0]),
            "euribor": pd.Series([0.5, 0.6, 0.7]),
            "oil_price": pd.Series([50, 55, 60]),  # Not in cached selection
            "electricity": pd.Series([10, 11, 12]),  # Not in cached selection
        }

        with patch(
            "raglite.forecasting.hybrid.ensemble.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = mock_cached_model_selection

            with patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data"
            ) as mock_ensure_data:
                mock_ensure_data.return_value = sample_time_series_data

                # Mock _route_to_model at its definition location (used inside forecast_helpers)
                with patch(
                    "raglite.forecasting.hybrid.model_generators._route_to_model"
                ) as mock_route:
                    mock_route.return_value = MagicMock()

                    with patch(
                        "raglite.forecasting.hybrid.ensemble.explain_forecast"
                    ) as mock_explain:
                        mock_explain.return_value = "Test explanation"

                        await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            external_regressors=all_regressors,
                            use_model_selection=True,
                        )

                        # Check that only cached regressors were passed
                        assert mock_route.called, "_route_to_model should be called"
                        call_kwargs = mock_route.call_args[1]
                        filtered_regressors = call_kwargs.get("external_regressors")

                        # Should only contain gas_price and euribor
                        assert filtered_regressors is not None, (
                            "Filtered regressors should not be None"
                        )
                        assert set(filtered_regressors.keys()) == {"gas_price", "euribor"}

    @pytest.mark.asyncio
    async def test_ac_7b_6_3_2_no_regressors_when_use_regressors_false(
        self,
        sample_time_series_data,
    ) -> None:
        """TEST-AC-7b.6.3.2: No regressors passed when use_regressors=False in cache."""
        import pandas as pd

        from raglite.external_data.storage import CachedModelSelection
        from raglite.forecasting.hybrid import generate_forecast

        # Create cache entry with use_regressors=False
        # Use "arima" model (not "prophet") to test the _route_to_model path
        # Prophet has a special code path that doesn't use _route_to_model
        now = datetime.utcnow()
        cached_no_regressors = CachedModelSelection(
            variable_name="ebitda",
            best_model="arima",  # Use ARIMA to test _route_to_model path
            best_mape=6.0,
            best_mase=0.9,
            use_regressors=False,  # Explicitly disabled
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        all_regressors = {
            "gas_price": pd.Series([1.0, 2.0, 3.0]),
            "euribor": pd.Series([0.5, 0.6, 0.7]),
        }

        with patch(
            "raglite.forecasting.hybrid.ensemble.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = cached_no_regressors

            with patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data"
            ) as mock_ensure_data:
                mock_ensure_data.return_value = sample_time_series_data

                with patch(
                    "raglite.forecasting.hybrid.model_generators._route_to_model"
                ) as mock_route:
                    mock_route.return_value = MagicMock()

                    with patch(
                        "raglite.forecasting.hybrid.ensemble.explain_forecast"
                    ) as mock_explain:
                        mock_explain.return_value = "Test explanation"

                        await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            external_regressors=all_regressors,
                            use_model_selection=True,
                        )

                        # Check that no regressors were passed
                        assert mock_route.called, "_route_to_model should be called"
                        call_kwargs = mock_route.call_args[1]
                        filtered_regressors = call_kwargs.get("external_regressors")

                        assert filtered_regressors is None

    @pytest.mark.asyncio
    async def test_ac_7b_6_3_3_handles_missing_regressor_gracefully(
        self,
        sample_time_series_data,
        mock_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.3.3: Handles missing regressors gracefully."""
        import pandas as pd

        from raglite.forecasting.hybrid import generate_forecast

        # Only provide gas_price, euribor is missing
        partial_regressors = {
            "gas_price": pd.Series([1.0, 2.0, 3.0]),
            # "euribor" is missing but in cached regressor_list
        }

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
                    mock_route.return_value = MagicMock()

                    with patch(
                        "raglite.forecasting.hybrid.ensemble.explain_forecast"
                    ) as mock_explain:
                        mock_explain.return_value = "Test explanation"

                        # Should not raise - handles missing regressor gracefully
                        await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            external_regressors=partial_regressors,
                            use_model_selection=True,
                        )

                        # Only gas_price should be passed
                        assert mock_route.called, "_route_to_model should be called"
                        call_kwargs = mock_route.call_args[1]
                        filtered_regressors = call_kwargs.get("external_regressors")
                        assert filtered_regressors is not None, (
                            "Filtered regressors should not be None"
                        )
                        assert "gas_price" in filtered_regressors
                        assert "euribor" not in filtered_regressors
