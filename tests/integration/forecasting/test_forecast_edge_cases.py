"""Integration tests for forecast edge cases - split from test_forecast_query_integration.py.

Tests dynamic metric forecasting and metrics cache configuration.
Story 5.0.4 Advisory: Added dynamic metric forecasting integration tests.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.forecasting.metrics import (
    _get_cache_ttl,
    clear_metrics_cache,
    list_available_metrics,
)
from raglite.forecasting.timeseries import MetricValidationError
from raglite.main import get_financial_forecast
from raglite.retrieval.search import QueryError
from raglite.shared.config import settings
from raglite.shared.models import (
    ForecastPoint,
    ForecastQueryRequest,
    ForecastResult,
    TimeSeriesData,
    TimeSeriesPoint,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    # REMOVED: xdist_group(name="database_writes") - tests use mocks, no real DB writes
]


class TestDynamicMetricForecasting:
    """Integration tests for dynamic metric forecasting (Story 5.0.4 Advisory).

    These tests verify the full pipeline for any metric:
    1. MCP tool receives request with arbitrary metric name
    2. SQL extraction retrieves data for the metric
    3. MetricValidationError returned if insufficient data
    4. Forecast generated for metrics with 8+ data points
    """

    @pytest.mark.asyncio
    async def test_dynamic_metric_capex_forecast(self):
        """Test forecasting for arbitrary metric 'capex' (not hardcoded)."""
        # Create mock time-series data for 'capex' metric
        mock_ts_data = TimeSeriesData(
            metric_name="capex",
            points=[
                TimeSeriesPoint(date=datetime(2024, m, 1), value=50.0 + m * 2)
                for m in range(1, 10)  # 9 data points
            ],
            interval="monthly",
            source_documents=[],
        )

        mock_forecast = ForecastResult(
            metric_name="capex",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=72.0,
                    lower=65.0,
                    upper=79.0,
                    label="Jan 2025",
                ),
            ],
            confidence_reasoning="Capital expenditure shows steady growth.",
            basis="Prophet model trained on 9 months of CAPEX data",
            periods_ahead=1,
        )

        with (
            patch(
                "raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_sql,
            patch(
                "raglite.mcp.tools.forecast_helpers.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ),
        ):
            # Request forecast for arbitrary metric "capex"
            request = ForecastQueryRequest(metric="capex", periods_ahead=1)
            response = await get_financial_forecast.fn(request)

            # Verify SQL extraction was called with "capex"
            mock_sql.assert_called_once()
            assert mock_sql.call_args.kwargs["metric"] == "capex"

            # Verify response
            assert response.metric_name == "capex"
            assert len(response.forecast) == 1
            assert response.forecast[0].label == "Jan 2025"

    @pytest.mark.asyncio
    async def test_dynamic_metric_margins_forecast(self):
        """Test forecasting for arbitrary metric 'margins'."""
        mock_ts_data = TimeSeriesData(
            metric_name="margins",
            points=[
                TimeSeriesPoint(date=datetime(2024, m, 1), value=15.0 + m * 0.5)
                for m in range(1, 10)
            ],
            interval="monthly",
            source_documents=[],
        )

        mock_forecast = ForecastResult(
            metric_name="margins",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=20.5,
                    lower=18.0,
                    upper=23.0,
                    label="Jan 2025",
                ),
            ],
            basis="Prophet model trained on margin data",
            periods_ahead=1,
        )

        with (
            patch(
                "raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.mcp.tools.forecast_helpers.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ),
        ):
            request = ForecastQueryRequest(metric="margins", periods_ahead=1)
            response = await get_financial_forecast.fn(request)

            assert response.metric_name == "margins"
            assert len(response.forecast) == 1

    @pytest.mark.asyncio
    async def test_metric_validation_error_with_suggestions(self):
        """Test that MetricValidationError provides available metric suggestions."""
        # Create MetricValidationError with available metrics
        validation_error = MetricValidationError(
            metric_name="unknown_metric",
            data_points_found=3,
            minimum_required=8,
            available_metrics=["revenue", "ebitda"],
        )

        with patch(
            "raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type",
            new_callable=AsyncMock,
            side_effect=validation_error,
        ):
            request = ForecastQueryRequest(metric="unknown_metric", periods_ahead=1)

            with pytest.raises(QueryError) as exc_info:
                await get_financial_forecast.fn(request)

            # Verify error message includes suggestions
            error_msg = str(exc_info.value)
            assert "unknown_metric" in error_msg
            assert "revenue" in error_msg or "ebitda" in error_msg

    @pytest.mark.asyncio
    async def test_ebitda_forecast_without_entity_parameter(self):
        """Test that EBITDA forecasting works without entity disambiguation (AC5)."""
        # EBITDA uses consolidated GROUP values automatically
        mock_ts_data = TimeSeriesData(
            metric_name="ebitda",
            points=[
                TimeSeriesPoint(date=datetime(2024, m, 1), value=155.0 + m * 5)
                for m in range(1, 10)
            ],
            interval="monthly",
            source_documents=[],
        )

        mock_forecast = ForecastResult(
            metric_name="ebitda",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=210.0,
                    lower=190.0,
                    upper=230.0,
                    label="Jan 2025",
                ),
            ],
            confidence_reasoning="EBITDA shows consistent growth pattern.",
            basis="Prophet model using consolidated GROUP values",
            periods_ahead=1,
        )

        with (
            patch(
                "raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_sql,
            patch(
                "raglite.mcp.tools.forecast_helpers.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ),
        ):
            # Request EBITDA forecast - no entity parameter needed
            request = ForecastQueryRequest(metric="ebitda", periods_ahead=1)
            response = await get_financial_forecast.fn(request)

            # Verify SQL extraction was called with just "ebitda"
            mock_sql.assert_called_once()
            call_kwargs = mock_sql.call_args.kwargs
            assert call_kwargs["metric"] == "ebitda"
            # No "entity" parameter should be in the call
            assert "entity" not in call_kwargs

            # Verify response
            assert response.metric_name == "ebitda"
            assert len(response.forecast) == 1


class TestMetricsCacheConfiguration:
    """Integration tests for configurable metrics cache TTL (Story 5.0.4 Advisory)."""

    def test_cache_ttl_configurable_via_settings(self):
        """Test that metrics cache TTL is configurable via settings."""
        # Verify default TTL is 300 seconds (5 minutes)
        assert hasattr(settings, "metrics_cache_ttl_seconds")
        assert settings.metrics_cache_ttl_seconds == 300

    def test_metrics_module_uses_settings_ttl(self):
        """Test that metrics module uses configurable TTL from settings."""
        # Verify _get_cache_ttl returns the settings value
        assert _get_cache_ttl() == settings.metrics_cache_ttl_seconds

    @pytest.mark.asyncio
    async def test_cache_respects_custom_ttl(self):
        """Test that cache respects custom TTL setting."""
        # Clear any existing cache
        clear_metrics_cache()

        # Mock PostgreSQL connection at the metrics module level
        # Note: period column is VARCHAR, not datetime (Story 5.0.4 fix)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("revenue", 12, "Jan-24", "Dec-24"),
            ("ebitda", 10, "Jan-24", "Oct-24"),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.forecasting.metrics.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # First call - should fetch from DB
            result1 = await list_available_metrics()
            assert len(result1) == 2
            assert mock_cursor.execute.call_count == 1

            # Second call within TTL - should use cache
            result2 = await list_available_metrics()
            assert len(result2) == 2
            assert mock_cursor.execute.call_count == 1  # No additional DB call

            # Verify cache TTL comes from settings
            assert _get_cache_ttl() == 300

        # Cleanup: clear cache for other tests
        clear_metrics_cache()
