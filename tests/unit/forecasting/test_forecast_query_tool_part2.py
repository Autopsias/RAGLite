"""Unit tests for get_financial_forecast MCP tool - Part 2.

Tests error handling and edge cases.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from raglite.main import get_financial_forecast
from raglite.mcp.tools import forecast_helpers as forecast_helpers_module
from raglite.shared.models import (
    ForecastPoint,
    ForecastQueryRequest,
    ForecastResult,
    TimeSeriesData,
    TimeSeriesPoint,
)


@pytest.mark.timeout(300)
class TestForecastToolPart2:
    """Additional tests for forecast tool edge cases."""

    @pytest.mark.asyncio
    async def test_cash_flow_metric(self):
        """Test forecast for cash_flow metric."""
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
            metric_name="cash_flow",
            points=[TimeSeriesPoint(date=datetime(y, m, 1), value=50.0) for y, m in quarters],
            source_documents=["Cashflow.pdf"],
        )

        mock_forecast = ForecastResult(
            metric_name="cash_flow",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=55.0,
                    lower=50.0,
                    upper=60.0,
                    label="Q1 2025",
                ),
            ],
            basis="Test",
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
                "extract_timeseries",
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
            request = ForecastQueryRequest(query="Forecast cash flow for the next 4 quarters")
            response = await get_financial_forecast.fn(request)

        assert response.metric_name == "cash_flow"

    @pytest.mark.asyncio
    async def test_expenses_metric(self):
        """Test forecast for expenses metric."""
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
            metric_name="expenses",
            points=[TimeSeriesPoint(date=datetime(y, m, 1), value=30.0) for y, m in quarters],
            source_documents=["Expenses.pdf"],
        )

        mock_forecast = ForecastResult(
            metric_name="expenses",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=32.0,
                    lower=28.0,
                    upper=36.0,
                    label="Q1 2025",
                ),
            ],
            basis="Test",
            periods_ahead=2,
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
                "extract_timeseries",
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
            request = ForecastQueryRequest(query="Predict expenses for next 2 quarters")
            response = await get_financial_forecast.fn(request)

        assert response.metric_name == "expenses"

    @pytest.mark.asyncio
    async def test_response_includes_methodology(self):
        """Test that response includes methodology field (AC3)."""
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
            forecast=[],
            basis="Test",
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
                "extract_timeseries",
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
            request = ForecastQueryRequest(metric="revenue")
            response = await get_financial_forecast.fn(request)

        assert "Prophet" in response.methodology
        assert "Mistral" in response.methodology

    @pytest.mark.asyncio
    async def test_enhanced_basis_with_document_count(self):
        """Test that basis includes document count (AC3)."""
        quarters = [
            (2022, 1),
            (2022, 4),
            (2022, 7),
            (2022, 10),
            (2023, 1),
            (2023, 4),
            (2023, 7),
            (2023, 10),
            (2024, 1),
            (2024, 4),
        ]
        mock_ts_data = TimeSeriesData(
            metric_name="revenue",
            points=[TimeSeriesPoint(date=datetime(y, m, 1), value=100.0) for y, m in quarters],
            source_documents=["Q1.pdf", "Q2.pdf", "Q3.pdf"],
        )

        mock_forecast = ForecastResult(
            metric_name="revenue",
            forecast=[],
            basis="Original basis",
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
                "extract_timeseries",
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
            request = ForecastQueryRequest(metric="revenue")
            response = await get_financial_forecast.fn(request)

        assert "10 quarters" in response.basis
        assert "3 documents" in response.basis

    @pytest.mark.asyncio
    async def test_metric_case_insensitive(self):
        """Test that metric parameter is case insensitive."""
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
            forecast=[],
            basis="Test",
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
                "extract_timeseries",
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
            # Test uppercase metric
            request = ForecastQueryRequest(metric="REVENUE")
            response = await get_financial_forecast.fn(request)

        assert response.metric_name == "revenue"


# =============================================================================
# Story 5.0.1 Update: SUPPORTED_FORECAST_METRICS constant removed
# =============================================================================
# The TestSupportedMetrics class has been removed because Story 5.0.1 changed
# the validation model from a hardcoded whitelist to dynamic database lookup.
# Any metric in the financial_tables database is now valid - metrics are
# validated dynamically by checking if data exists in financial_tables.
#
# See raglite/main.py line 1478 for the implementation note.
