"""Unit tests for Story 4.4: Forecast Query MCP Tool.

Tests the get_financial_forecast MCP tool integration.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from raglite.mcp.tools import forecast_helpers as forecast_helpers_module
from raglite.shared.models import (
    ForecastPoint,
    ForecastQueryRequest,
    ForecastResult,
    TimeSeriesData,
    TimeSeriesPoint,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def mock_regressor_fetch():
    """Auto-mock regressor fetch to prevent real API calls in unit tests."""
    with patch(
        "raglite.forecasting.regressor_fetch.fetch_regressors_for_metric",
        new_callable=AsyncMock,
        return_value={},  # No external API calls in unit tests
    ):
        yield


# =============================================================================
# Test get_financial_forecast MCP Tool (AC1-AC5)
# =============================================================================


class TestGetFinancialForecast:
    """Tests for the get_financial_forecast MCP tool."""

    @pytest.mark.asyncio
    async def test_structured_query_success(self):
        """Test successful forecast with structured parameters."""
        from raglite.main import get_financial_forecast

        # Mock time-series data - 8 quarters across 2 years
        quarters = [
            (2023, 1),
            (2023, 4),
            (2023, 7),
            (2023, 10),
            (2024, 1),
            (2024, 4),
            (2024, 7),
            (2024, 10),
        ]
        mock_ts_data = TimeSeriesData(
            metric_name="revenue",
            points=[
                TimeSeriesPoint(date=datetime(y, m, 1), value=100.0 + i * 5)
                for i, (y, m) in enumerate(quarters)
            ],
            source_documents=["Q1_2023.pdf", "Q2_2023.pdf"],
        )

        # Mock forecast result
        mock_forecast = ForecastResult(
            metric_name="revenue",
            historical_data=mock_ts_data.points,
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=150.0,
                    lower=140.0,
                    upper=160.0,
                    label="Q1 2025",
                ),
            ],
            confidence_reasoning="Test reasoning",
            basis="Prophet model trained on 8 quarters",
            periods_ahead=4,
        )

        with (
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch.object(
                forecast_helpers_module,
                "generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ),
        ):
            request = ForecastQueryRequest(metric="revenue", periods_ahead=4)
            response = await get_financial_forecast.fn(request)

        assert response.metric_name == "revenue"
        assert len(response.forecast) == 1
        assert response.forecast[0].value == 150.0
        assert response.forecast[0].lower == 140.0
        assert response.forecast[0].upper == 160.0
        # Story 6.11: Basis format updated to include model type and regressor info
        assert "8 quarters" in response.basis
        assert len(response.source_documents) == 2

    @pytest.mark.asyncio
    async def test_natural_language_query_success(self):
        """Test successful forecast with natural language query (AC4)."""
        from raglite.main import get_financial_forecast

        quarters = [
            (2023, 1),
            (2023, 4),
            (2023, 7),
            (2023, 10),
            (2024, 1),
            (2024, 4),
            (2024, 7),
            (2024, 10),
        ]
        mock_ts_data = TimeSeriesData(
            metric_name="revenue",
            points=[TimeSeriesPoint(date=datetime(y, m, 1), value=100.0) for y, m in quarters],
            source_documents=["Report.pdf"],
        )

        mock_forecast = ForecastResult(
            metric_name="revenue",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=110.0,
                    lower=105.0,
                    upper=115.0,
                    label="Q1 2025",
                ),
            ],
            basis="Test",
            periods_ahead=1,
        )

        with (
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch.object(
                forecast_helpers_module,
                "generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ),
        ):
            request = ForecastQueryRequest(query="What's the revenue forecast for next quarter?")
            response = await get_financial_forecast.fn(request)

        # NL parsing should extract "revenue" and periods=1
        assert response.metric_name == "revenue"
        assert response.periods_ahead == 1

    @pytest.mark.asyncio
    async def test_invalid_metric_error(self):
        """Test error handling for metric with no data."""
        from raglite.forecasting.timeseries import ExtractionError
        from raglite.main import get_financial_forecast
        from raglite.retrieval.search import QueryError

        # Mock SQL extraction to fail (no data for this metric)
        with (
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
                side_effect=ExtractionError(
                    "No data found in financial_tables for metric 'invalid_metric'"
                ),
            ),
            patch.object(
                forecast_helpers_module,
                "extract_timeseries",  # Fallback also fails
                new_callable=AsyncMock,
                side_effect=ExtractionError("No documents found"),
            ),
        ):
            request = ForecastQueryRequest(metric="invalid_metric")

            with pytest.raises(QueryError) as exc_info:
                await get_financial_forecast.fn(request)

        assert "Could not extract" in str(exc_info.value)
        assert "invalid_metric" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_metric_error(self):
        """Test error when no metric can be determined."""
        from raglite.main import get_financial_forecast
        from raglite.retrieval.search import QueryError

        request = ForecastQueryRequest(query="What's the weather like?")

        with pytest.raises(QueryError) as exc_info:
            await get_financial_forecast.fn(request)

        assert "Could not determine metric" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_insufficient_data_error(self):
        """Test error handling for InsufficientDataError (AC5)."""
        from raglite.forecasting.hybrid import InsufficientDataError
        from raglite.main import get_financial_forecast
        from raglite.retrieval.search import QueryError

        mock_ts_data = TimeSeriesData(
            metric_name="revenue",
            points=[TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0)],
            source_documents=["Report.pdf"],
        )

        with (
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch.object(
                forecast_helpers_module,
                "generate_forecast",
                new_callable=AsyncMock,
                side_effect=InsufficientDataError("Need at least 8 data points"),
            ),
        ):
            request = ForecastQueryRequest(metric="revenue")

            with pytest.raises(QueryError) as exc_info:
                await get_financial_forecast.fn(request)

        assert "Insufficient historical data" in str(exc_info.value)
        assert "8 data points" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extraction_error(self):
        """Test error handling for ExtractionError."""
        from raglite.forecasting.timeseries import ExtractionError
        from raglite.main import get_financial_forecast
        from raglite.retrieval.search import QueryError

        with (
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
                side_effect=ExtractionError("No data found in financial_tables"),
            ),
            patch.object(
                forecast_helpers_module,
                "extract_timeseries",
                new_callable=AsyncMock,
                side_effect=ExtractionError("No documents found"),
            ),
        ):
            request = ForecastQueryRequest(metric="revenue")

            with pytest.raises(QueryError) as exc_info:
                await get_financial_forecast.fn(request)

        assert "Could not extract" in str(exc_info.value)
        assert "revenue" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self):
        """Test graceful handling of unexpected errors."""
        from raglite.main import get_financial_forecast
        from raglite.retrieval.search import QueryError

        with (
            patch.object(
                forecast_helpers_module,
                "extract_historical_data_by_type",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Unexpected crash"),
            ),
            patch.object(
                forecast_helpers_module,
                "extract_timeseries",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Fallback also crashed"),
            ),
        ):
            request = ForecastQueryRequest(metric="revenue")

            with pytest.raises(QueryError) as exc_info:
                await get_financial_forecast.fn(request)

        assert "Forecast generation failed" in str(exc_info.value)
