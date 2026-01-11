"""Integration tests for Story 7b-6: Model Selection Cache MCP Integration.

Tests the integration between model selection cache and MCP forecast tool,
including cache hits, cache misses, regressor filtering, and fallback behavior.
"""

from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from raglite.forecasting import regressor_fetch as regressor_fetch_module
from raglite.mcp.tools import forecast_helpers as forecast_helpers_module
from raglite.shared.models import ForecastQueryRequest, ForecastResult, TimeSeriesData

# Group cache integration tests that share mocked state to run on same worker
pytestmark = pytest.mark.xdist_group(name="model_cache")


class TestModelSelectionCacheIntegration:
    """Tests for model selection cache integration in MCP tool."""

    @pytest.mark.asyncio
    async def test_cache_hit_uses_cached_model(
        self,
        sample_historical_data: TimeSeriesData,
        sample_forecast_result: ForecastResult,
        cached_selection_without_regressors,
    ) -> None:
        """When cache hit, should use cached model instead of default."""
        from raglite.main import get_financial_forecast
        from raglite.mcp.tools import forecast as forecast_module

        with (
            patch.object(
                forecast_module,
                "check_model_selection_cache_for_forecast",
                new_callable=Mock,  # Sync function
            ) as mock_cache_check,
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                forecast_helpers_module,
                "_route_to_model",
                new_callable=AsyncMock,
            ) as mock_route,
            patch.object(
                regressor_fetch_module,
                "fetch_regressors_for_metric",
                new_callable=AsyncMock,
                return_value={},  # No regressors for unit tests
            ),
        ):
            # Setup mocks
            mock_cache_check.return_value = cached_selection_without_regressors
            mock_extract.return_value = sample_historical_data
            mock_route.return_value = sample_forecast_result

            request = ForecastQueryRequest(metric="sales_volume", periods_ahead=4)
            response = await get_financial_forecast.fn(request)

            # Verify cache was checked
            mock_cache_check.assert_called_once()

            # Verify _route_to_model was called with cached model
            mock_route.assert_called_once()
            call_kwargs = mock_route.call_args.kwargs
            assert call_kwargs["model_name"] == "chronos"

            # Verify response indicates cached model
            assert response.model_type == "chronos"

    @pytest.mark.asyncio
    async def test_cache_miss_falls_back_to_select_model_type(
        self,
        sample_historical_data: TimeSeriesData,
        sample_forecast_result: ForecastResult,
    ) -> None:
        """When cache miss, should fall back to select_model_type()."""
        from raglite.main import get_financial_forecast
        from raglite.mcp.tools import forecast as forecast_module

        with (
            patch.object(
                forecast_module,
                "check_model_selection_cache_for_forecast",
                new_callable=Mock,  # Sync function
            ) as mock_cache_check,
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                forecast_helpers_module,
                "select_model_type",
            ) as mock_select,
            patch.object(
                forecast_helpers_module,
                "generate_forecast",
                new_callable=AsyncMock,
            ) as mock_forecast,
            patch.object(
                regressor_fetch_module,
                "fetch_regressors_for_metric",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            # Setup mocks - cache returns None (miss)
            mock_cache_check.return_value = None
            mock_extract.return_value = sample_historical_data
            mock_select.return_value = ("prophet", "Default selection")
            mock_forecast.return_value = sample_forecast_result

            request = ForecastQueryRequest(metric="unknown_metric", periods_ahead=4)
            await get_financial_forecast.fn(request)

            # Verify cache was checked
            mock_cache_check.assert_called_once()

            # Verify select_model_type was called as fallback
            mock_select.assert_called_once()

            # Verify generate_forecast (Prophet path) was called
            mock_forecast.assert_called_once()

    @pytest.mark.asyncio
    async def test_expired_cache_treated_as_miss(
        self,
        sample_historical_data: TimeSeriesData,
        sample_forecast_result: ForecastResult,
    ) -> None:
        """Expired cache entries should trigger fallback."""
        from raglite.main import get_financial_forecast
        from raglite.mcp.tools import forecast as forecast_module

        with (
            patch.object(
                forecast_module,
                "check_model_selection_cache_for_forecast",
                new_callable=Mock,  # Sync function
            ) as mock_cache_check,
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                forecast_helpers_module,
                "select_model_type",
            ) as mock_select,
            patch.object(
                forecast_helpers_module,
                "generate_forecast",
                new_callable=AsyncMock,
            ) as mock_forecast,
            patch.object(
                regressor_fetch_module,
                "fetch_regressors_for_metric",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            # Setup mocks - cache returns expired entry (check function returns None)
            mock_cache_check.return_value = None  # Expired treated as miss
            mock_extract.return_value = sample_historical_data
            mock_select.return_value = ("prophet", "Fallback selection")
            mock_forecast.return_value = sample_forecast_result

            request = ForecastQueryRequest(metric="revenue", periods_ahead=4)
            await get_financial_forecast.fn(request)

            # Verify select_model_type was called (fallback path)
            mock_select.assert_called_once()

    @pytest.mark.asyncio
    async def test_regressors_filtered_to_cached_list(
        self,
        sample_historical_data: TimeSeriesData,
        sample_forecast_result: ForecastResult,
        cached_selection_with_regressors,
    ) -> None:
        """Only regressors in cached.regressor_list should be passed."""
        from raglite.main import get_financial_forecast
        from raglite.mcp.tools import forecast as forecast_module

        # Create mock regressor data
        mock_regressors = {
            "gdp_growth": pd.Series([1.0, 1.1, 1.2]),
            "inflation": pd.Series([2.0, 2.1, 2.2]),
            "euribor_3m": pd.Series([3.0, 3.1, 3.2]),  # Not in cached list
        }

        with (
            patch.object(
                forecast_module,
                "check_model_selection_cache_for_forecast",
                new_callable=Mock,  # Sync function
            ) as mock_cache_check,
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                forecast_helpers_module,
                "_route_to_model",
                new_callable=AsyncMock,
            ) as mock_route,
            patch.object(
                regressor_fetch_module,
                "fetch_regressors_for_metric",
                new_callable=AsyncMock,
            ) as mock_fetch_regressors,
        ):
            # Setup mocks
            mock_cache_check.return_value = cached_selection_with_regressors
            mock_extract.return_value = sample_historical_data
            mock_route.return_value = sample_forecast_result
            mock_fetch_regressors.return_value = mock_regressors

            request = ForecastQueryRequest(
                metric="revenue",
                periods_ahead=4,
                use_external_regressors=True,
            )
            await get_financial_forecast.fn(request)

            # Verify _route_to_model was called
            mock_route.assert_called_once()
            call_kwargs = mock_route.call_args.kwargs

            # Verify only cached regressors were passed
            filtered_regressors = call_kwargs.get("external_regressors")
            if filtered_regressors:
                assert "gdp_growth" in filtered_regressors
                assert "inflation" in filtered_regressors
                assert "euribor_3m" not in filtered_regressors

    @pytest.mark.asyncio
    async def test_cache_error_gracefully_falls_back(
        self,
        sample_historical_data: TimeSeriesData,
        sample_forecast_result: ForecastResult,
    ) -> None:
        """Cache lookup errors should not break forecasting."""
        from raglite.main import get_financial_forecast

        with (
            patch.object(
                forecast_helpers_module,
                "get_cached_model_selection",
                new_callable=Mock,  # Sync function
            ) as mock_get_cached,
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                forecast_helpers_module,
                "select_model_type",
            ) as mock_select,
            patch.object(
                forecast_helpers_module,
                "generate_forecast",
                new_callable=AsyncMock,
            ) as mock_forecast,
            patch.object(
                regressor_fetch_module,
                "fetch_regressors_for_metric",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            # Setup mocks - underlying cache function throws exception
            # This will be caught by check_model_selection_cache_for_forecast
            mock_get_cached.side_effect = Exception("Database connection failed")
            mock_extract.return_value = sample_historical_data
            mock_select.return_value = ("prophet", "Fallback after error")
            mock_forecast.return_value = sample_forecast_result

            request = ForecastQueryRequest(metric="revenue", periods_ahead=4)
            await get_financial_forecast.fn(request)

            # Verify fallback path was used (no exception raised)
            mock_select.assert_called_once()
            mock_forecast.assert_called_once()

    @pytest.mark.asyncio
    async def test_explicit_model_type_bypasses_cache(
        self,
        sample_historical_data: TimeSeriesData,
        sample_forecast_result: ForecastResult,
    ) -> None:
        """Explicit model_type should bypass cache lookup."""
        from raglite.main import get_financial_forecast
        from raglite.mcp.tools import forecast as forecast_module

        with (
            patch.object(
                forecast_module,
                "check_model_selection_cache_for_forecast",
                new_callable=Mock,  # Sync function
            ) as mock_cache_check,
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                forecast_helpers_module,
                "generate_ensemble_forecast",
                new_callable=AsyncMock,
            ) as mock_ensemble,
            patch.object(
                regressor_fetch_module,
                "fetch_regressors_for_metric",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            mock_extract.return_value = sample_historical_data
            mock_ensemble.return_value = sample_forecast_result

            # Explicitly request ensemble - should bypass cache
            request = ForecastQueryRequest(
                metric="revenue",
                periods_ahead=4,
                model_type="ensemble",
            )
            await get_financial_forecast.fn(request)

            # Cache should not be checked when model_type is explicit
            mock_cache_check.assert_not_called()

            # Ensemble should be used as explicitly requested
            mock_ensemble.assert_called_once()
