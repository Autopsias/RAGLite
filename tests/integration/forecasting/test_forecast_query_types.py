"""Integration tests for forecast query types - split from test_forecast_query_integration.py.

Tests end-to-end flow from MCP tool through time-series extraction and forecasting.
Requires mocked Qdrant and Mistral API for reproducible testing.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from raglite.forecasting.hybrid import InsufficientDataError
from raglite.forecasting.timeseries import ExtractionError
from raglite.main import get_financial_forecast, parse_forecast_query
from raglite.retrieval.search import QueryError
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


class TestForecastQueryIntegration:
    """Integration tests for the get_financial_forecast MCP tool.

    These tests verify the full pipeline:
    1. MCP tool receives request
    2. NL query parsing extracts parameters
    3. Time-series data extracted from documents
    4. Prophet generates forecast
    5. Mistral provides confidence reasoning
    6. Response returned with all fields populated
    """

    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocked_dependencies(
        self, mock_revenue_ts_data, mock_revenue_forecast
    ):
        """Test complete forecast pipeline with mocked external dependencies."""
        with (
            patch(
                "raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type",
                new_callable=AsyncMock,
                return_value=mock_revenue_ts_data,
            ) as mock_extract_sql,
            patch(
                "raglite.mcp.tools.forecast_helpers.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_revenue_forecast,
            ) as mock_generate,
        ):
            # Test natural language query
            request = ForecastQueryRequest(query="What's the revenue forecast for next 2 quarters?")
            response = await get_financial_forecast.fn(request)

        # Verify SQL extraction was called with correct parameters
        mock_extract_sql.assert_called_once()
        extract_call_kwargs = mock_extract_sql.call_args.kwargs
        assert extract_call_kwargs["metric"] == "revenue"

        # Verify forecast generation was called
        mock_generate.assert_called_once()
        generate_call_kwargs = mock_generate.call_args.kwargs
        assert generate_call_kwargs["metric"] == "revenue"
        assert generate_call_kwargs["periods_ahead"] == 2

        # Verify response structure (AC2, AC3)
        assert response.__class__.__name__ == "ForecastQueryResponse"
        assert response.metric_name == "revenue"
        assert len(response.forecast) == 2
        assert response.forecast[0].label == "Q3 2024"
        assert response.forecast[1].label == "Q4 2024"
        assert response.methodology == "Prophet + Mistral Large hybrid forecasting"
        assert len(response.source_documents) == 3

        # Verify confidence intervals present (AC2)
        for point in response.forecast:
            assert point.lower < point.value < point.upper

    @pytest.mark.asyncio
    async def test_nl_query_parsing_integration(self):
        """Test that NL queries are correctly parsed and routed (AC4)."""
        # Test various NL query patterns
        test_cases = [
            ("What's the revenue forecast for next quarter?", "revenue", 1),
            ("Forecast sales for the next 4 quarters", "revenue", 4),
            ("Predict cash flow for next 2 quarters", "cash_flow", 2),
            ("What will expenses be for the next 6 quarters?", "expenses", 6),
            ("Show me cost projections for next quarter", "expenses", 1),
        ]

        for query, expected_metric, expected_periods in test_cases:
            metric, periods = parse_forecast_query(query)
            assert metric == expected_metric, f"Failed for query: {query}"
            assert periods == expected_periods, f"Failed for query: {query}"

    @pytest.mark.asyncio
    async def test_error_propagation_from_timeseries(self):
        """Test that errors from time-series extraction propagate correctly (AC5).

        Note: extract_historical_data_by_type is called first; if it raises ExtractionError,
        extract_timeseries is called as fallback. We patch both to ensure error propagation.
        """
        with (
            patch(
                "raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type",
                new_callable=AsyncMock,
                side_effect=ExtractionError("SQL extraction failed"),
            ),
            patch(
                "raglite.mcp.tools.forecast_helpers.extract_timeseries",
                new_callable=AsyncMock,
                side_effect=ExtractionError("No revenue data found in documents"),
            ),
        ):
            request = ForecastQueryRequest(metric="revenue")

            with pytest.raises(QueryError) as exc_info:
                await get_financial_forecast.fn(request)

        # FIX: Updated to accept new MetricValidationError format or old generic format
        error_msg = str(exc_info.value)
        assert (
            "Could not extract revenue time-series data" in error_msg
            or "data points" in error_msg
            or "minimum" in error_msg
        )

    @pytest.mark.asyncio
    async def test_error_propagation_from_forecast(self):
        """Test that errors from forecast generation propagate correctly (AC5)."""
        # Create mock data with insufficient points
        mock_ts_data = TimeSeriesData(
            metric_name="revenue",
            points=[
                TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0),
                TimeSeriesPoint(date=datetime(2024, 4, 1), value=105.0),
            ],
            source_documents=["Report.pdf"],
        )

        with (
            patch(
                "raglite.mcp.tools.forecast_helpers.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.mcp.tools.forecast_helpers.generate_forecast",
                new_callable=AsyncMock,
                side_effect=InsufficientDataError("Need at least 8 data points, got 2"),
            ),
        ):
            request = ForecastQueryRequest(metric="revenue")

            with pytest.raises(QueryError) as exc_info:
                await get_financial_forecast.fn(request)

        # FIX: Updated to check for enhanced validation error format
        error_msg = str(exc_info.value)
        assert "Insufficient historical data" in error_msg or "data points" in error_msg, (
            f"Expected data point validation error, got: {error_msg}"
        )
        # Verify it mentions the minimum requirement
        assert "minimum" in error_msg or "8" in error_msg or "required" in error_msg

    @pytest.mark.asyncio
    async def test_structured_query_bypasses_nl_parsing(self):
        """Test that structured queries bypass NL parsing (AC1)."""
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
            source_documents=["Report.pdf"],
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
            periods_ahead=1,
        )

        with (
            patch(
                "raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_extract,
            patch(
                "raglite.mcp.tools.forecast_helpers.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ) as mock_generate,
        ):
            # Use structured parameters (not NL query)
            request = ForecastQueryRequest(metric="cash_flow", periods_ahead=1)
            response = await get_financial_forecast.fn(request)

        # Verify cash_flow was used (not parsed from NL)
        assert mock_extract.call_args.kwargs["metric"] == "cash_flow"
        assert mock_generate.call_args.kwargs["periods_ahead"] == 1
        assert response.metric_name == "cash_flow"


class TestForecastResponseFormat:
    """Tests to verify response format meets MCP requirements."""

    @pytest.mark.asyncio
    async def test_response_serializable_to_json(self):
        """Test that response can be serialized to JSON for MCP transport."""
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
                    lower=100.0,
                    upper=120.0,
                    label="Q1 2025",
                ),
            ],
            basis="Test",
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
            request = ForecastQueryRequest(metric="revenue")
            response = await get_financial_forecast.fn(request)

        # Verify JSON serialization works
        json_output = response.model_dump_json()
        assert len(json_output) > 0

        # Verify key fields present in JSON
        assert '"metric_name"' in json_output
        assert '"forecast"' in json_output
        assert '"confidence_reasoning"' in json_output
        assert '"methodology"' in json_output

    @pytest.mark.asyncio
    async def test_response_includes_all_required_fields(self):
        """Test that response includes all fields specified in AC2/AC3."""
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
            source_documents=["Report1.pdf", "Report2.pdf"],
        )

        mock_forecast = ForecastResult(
            metric_name="revenue",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=110.0,
                    lower=100.0,
                    upper=120.0,
                    label="Q1 2025",
                ),
            ],
            confidence_reasoning="Test confidence reasoning",
            basis="Test basis",
            accuracy_estimate="±15%",
            periods_ahead=4,
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
            request = ForecastQueryRequest(metric="revenue", periods_ahead=4)
            response = await get_financial_forecast.fn(request)

        # AC2: Verify forecast points with confidence intervals
        assert len(response.forecast) > 0
        for point in response.forecast:
            assert point.date is not None
            assert point.value is not None
            assert point.lower is not None
            assert point.upper is not None
            assert point.label is not None

        # AC3: Verify confidence reasoning and methodology
        assert len(response.confidence_reasoning) > 0
        assert "Prophet" in response.methodology
        assert "Mistral" in response.methodology

        # Verify other required fields
        assert response.metric_name == "revenue"
        assert response.periods_ahead == 4
        assert len(response.source_documents) == 2
