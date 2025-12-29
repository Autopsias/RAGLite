"""Integration tests for Story 7b-6: Model Selection Cache MCP Integration.

Tests the integration between model selection cache and MCP forecast tool,
including cache hits, cache misses, regressor filtering, and fallback behavior.

NOTE: These tests require Qdrant and PostgreSQL to be running.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from raglite.external_data.storage import CachedModelSelection
from raglite.forecasting import regressor_config as regressor_config_module
from raglite.forecasting import regressor_fetch as regressor_fetch_module
from raglite.mcp.tools import forecast as forecast_module
from raglite.shared.models import (
    ForecastPoint,
    ForecastQueryRequest,
    ForecastResult,
    TimeSeriesData,
    TimeSeriesPoint,
)

pytestmark = [
    pytest.mark.unit,  # All dependencies mocked - should be unit tests
]

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_historical_data():
    """Create sample time series data for testing."""
    points = [
        TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0),
        TimeSeriesPoint(date=datetime(2024, 2, 1), value=105.0),
        TimeSeriesPoint(date=datetime(2024, 3, 1), value=110.0),
        TimeSeriesPoint(date=datetime(2024, 4, 1), value=108.0),
        TimeSeriesPoint(date=datetime(2024, 5, 1), value=115.0),
        TimeSeriesPoint(date=datetime(2024, 6, 1), value=120.0),
        TimeSeriesPoint(date=datetime(2024, 7, 1), value=118.0),
        TimeSeriesPoint(date=datetime(2024, 8, 1), value=125.0),
    ]
    return TimeSeriesData(
        metric_name="test_metric",
        points=points,
        source_documents=["test_doc.pdf"],
    )


@pytest.fixture
def sample_forecast_result():
    """Create sample forecast result for mocking."""
    return ForecastResult(
        metric_name="test_metric",
        forecast=[
            ForecastPoint(
                date=datetime(2024, 10, 1),
                value=130.0,
                lower=120.0,
                upper=140.0,
                label="2024-Q4",
            ),
        ],
        basis="Test model",
        confidence_reasoning="High confidence",
    )


@pytest.fixture
def cached_selection_with_regressors():
    """Create cached model selection with regressors."""
    return CachedModelSelection(
        variable_name="revenue",
        best_model="catboost",
        best_mape=5.5,
        best_mase=0.85,
        use_regressors=True,
        regressor_list=["gdp_growth", "inflation"],
        candidate_results={},
        data_characteristics=None,
        selected_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )


@pytest.fixture
def cached_selection_without_regressors():
    """Create cached model selection without regressors."""
    return CachedModelSelection(
        variable_name="sales_volume",
        best_model="chronos",
        best_mape=12.5,
        best_mase=1.24,
        use_regressors=False,
        regressor_list=[],
        candidate_results={},
        data_characteristics=None,
        selected_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )


@pytest.fixture
def expired_cached_selection():
    """Create expired cached model selection."""
    return CachedModelSelection(
        variable_name="revenue",
        best_model="catboost",
        best_mape=5.5,
        best_mase=0.85,
        use_regressors=True,
        regressor_list=["gdp_growth"],
        candidate_results={},
        data_characteristics=None,
        selected_at=datetime.utcnow() - timedelta(days=10),
        expires_at=datetime.utcnow() - timedelta(days=3),  # Expired
    )


# =============================================================================
# Test CachedModelSelection
# =============================================================================


class TestCachedModelSelection:
    """Tests for CachedModelSelection dataclass."""

    def test_is_expired_returns_false_for_valid(self, cached_selection_with_regressors):
        """Non-expired selection returns is_expired=False."""
        assert not cached_selection_with_regressors.is_expired

    def test_is_expired_returns_true_for_expired(self, expired_cached_selection):
        """Expired selection returns is_expired=True."""
        assert expired_cached_selection.is_expired


# =============================================================================
# Test Model Selection Cache Integration
# =============================================================================


class TestModelSelectionCacheIntegration:
    """Tests for model selection cache integration in MCP tool."""

    @pytest.mark.asyncio
    async def test_cache_hit_uses_cached_model(
        self,
        sample_historical_data,
        sample_forecast_result,
        cached_selection_without_regressors,
    ):
        """When cache hit, should use cached model instead of default."""
        from raglite.main import get_financial_forecast

        with (
            patch.object(
                forecast_module,
                "get_cached_model_selection",
                new_callable=Mock,  # Sync function, use Mock not AsyncMock
            ) as mock_cache,
            patch.object(
                forecast_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                forecast_module,
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
            mock_cache.return_value = cached_selection_without_regressors
            mock_extract.return_value = sample_historical_data
            mock_route.return_value = sample_forecast_result

            request = ForecastQueryRequest(metric="sales_volume", periods_ahead=4)
            response = await get_financial_forecast.fn(request)

            # Verify cache was checked
            mock_cache.assert_called_once_with("sales_volume")

            # Verify _route_to_model was called with cached model
            mock_route.assert_called_once()
            call_kwargs = mock_route.call_args.kwargs
            assert call_kwargs["model_name"] == "chronos"

            # Verify response indicates cached model
            assert response.model_type == "chronos"

    @pytest.mark.asyncio
    async def test_cache_miss_falls_back_to_select_model_type(
        self,
        sample_historical_data,
        sample_forecast_result,
    ):
        """When cache miss, should fall back to select_model_type()."""
        from raglite.main import get_financial_forecast

        with (
            patch.object(
                forecast_module,
                "get_cached_model_selection",
                new_callable=Mock,  # Sync function
            ) as mock_cache,
            patch.object(
                forecast_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                regressor_config_module,
                "select_model_type",
            ) as mock_select,
            patch.object(
                forecast_module,
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
            mock_cache.return_value = None
            mock_extract.return_value = sample_historical_data
            mock_select.return_value = ("prophet", "Default selection")
            mock_forecast.return_value = sample_forecast_result

            request = ForecastQueryRequest(metric="unknown_metric", periods_ahead=4)
            await get_financial_forecast.fn(request)

            # Verify cache was checked
            mock_cache.assert_called_once()

            # Verify select_model_type was called as fallback
            mock_select.assert_called_once()

            # Verify generate_forecast (Prophet path) was called
            mock_forecast.assert_called_once()

    @pytest.mark.asyncio
    async def test_expired_cache_treated_as_miss(
        self,
        sample_historical_data,
        sample_forecast_result,
        expired_cached_selection,
    ):
        """Expired cache entries should trigger fallback."""
        from raglite.main import get_financial_forecast

        with (
            patch.object(
                forecast_module,
                "get_cached_model_selection",
                new_callable=Mock,  # Sync function
            ) as mock_cache,
            patch.object(
                forecast_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                regressor_config_module,
                "select_model_type",
            ) as mock_select,
            patch.object(
                forecast_module,
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
            # Setup mocks - cache returns expired entry
            mock_cache.return_value = expired_cached_selection
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
        sample_historical_data,
        sample_forecast_result,
        cached_selection_with_regressors,
    ):
        """Only regressors in cached.regressor_list should be passed."""
        from raglite.main import get_financial_forecast

        # Create mock regressor data
        mock_regressors = {
            "gdp_growth": pd.Series([1.0, 1.1, 1.2]),
            "inflation": pd.Series([2.0, 2.1, 2.2]),
            "euribor_3m": pd.Series([3.0, 3.1, 3.2]),  # Not in cached list
        }

        with (
            patch.object(
                forecast_module,
                "get_cached_model_selection",
                new_callable=Mock,  # Sync function
            ) as mock_cache,
            patch.object(
                forecast_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                forecast_module,
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
            mock_cache.return_value = cached_selection_with_regressors
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
        sample_historical_data,
        sample_forecast_result,
    ):
        """Cache lookup errors should not break forecasting."""
        from raglite.main import get_financial_forecast

        with (
            patch.object(
                forecast_module,
                "get_cached_model_selection",
                new_callable=Mock,  # Sync function
            ) as mock_cache,
            patch.object(
                forecast_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                regressor_config_module,
                "select_model_type",
            ) as mock_select,
            patch.object(
                forecast_module,
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
            # Setup mocks - cache throws exception
            mock_cache.side_effect = Exception("Database connection failed")
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
        sample_historical_data,
        sample_forecast_result,
    ):
        """Explicit model_type should bypass cache lookup."""
        from raglite.main import get_financial_forecast

        with (
            patch.object(
                forecast_module,
                "get_cached_model_selection",
                new_callable=Mock,  # Sync function
            ) as mock_cache,
            patch.object(
                forecast_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                forecast_module,
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
            mock_cache.assert_not_called()

            # Ensemble should be used as explicitly requested
            mock_ensemble.assert_called_once()


# =============================================================================
# Test Model Routers
# =============================================================================


class TestModelRouters:
    """Tests for model router implementations."""

    @pytest.mark.asyncio
    async def test_prophet_router_delegates_to_generate_forecast(
        self,
        sample_historical_data,
        sample_forecast_result,
    ):
        """Prophet router should delegate to generate_forecast."""
        from raglite.forecasting.hybrid import _generate_prophet_forecast

        with patch(
            "raglite.forecasting.hybrid.ensemble.generate_forecast",  # Patch where used in ensemble
            new_callable=AsyncMock,
        ) as mock_forecast:
            mock_forecast.return_value = sample_forecast_result

            await _generate_prophet_forecast(
                metric="test_metric",
                historical_data=sample_historical_data,
                periods_ahead=4,
                external_regressors=None,
            )

            # Verify generate_forecast was called with use_model_selection=False
            mock_forecast.assert_called_once()
            call_kwargs = mock_forecast.call_args.kwargs
            assert call_kwargs["use_model_selection"] is False

    @pytest.mark.asyncio
    async def test_chronos_router_delegates_to_cold_start(
        self,
        sample_historical_data,
        sample_forecast_result,
    ):
        """Chronos router should delegate to generate_chronos_cold_start_forecast."""
        from raglite.forecasting.hybrid import _generate_chronos_forecast

        with (
            patch(
                "raglite.forecasting.hybrid.model_generators.generate_chronos_cold_start_forecast",  # Patch where used in model_generators
                new_callable=AsyncMock,
            ) as mock_chronos
        ):
            mock_chronos.return_value = sample_forecast_result

            await _generate_chronos_forecast(
                metric="test_metric",
                historical_data=sample_historical_data,
                periods_ahead=4,
                external_regressors={"ignored": pd.Series([1, 2, 3])},  # Should be ignored
            )

            # Verify cold_start was called (regressors ignored for Chronos)
            mock_chronos.assert_called_once()
            call_kwargs = mock_chronos.call_args.kwargs
            assert "external_regressors" not in call_kwargs
