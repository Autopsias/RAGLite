"""Integration tests for Story 4.4: Forecast Query Tool (MCP).

Tests end-to-end flow from MCP tool through time-series extraction and forecasting.
Requires mocked Qdrant and Mistral API for reproducible testing.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from raglite.shared.models import (
    ForecastQueryRequest,
    ForecastQueryResponse,
)

# Mark all tests as preserve_collection - these are read-only tests
# that don't modify the Qdrant collection (performance optimization)
pytestmark = pytest.mark.preserve_collection

# =============================================================================
# Integration Tests for get_financial_forecast MCP Tool
# =============================================================================


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
    async def test_full_pipeline_with_mocked_dependencies(self):
        """Test complete forecast pipeline with mocked external dependencies."""
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

        # Create realistic time-series data (8+ quarters)
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
            points=[
                TimeSeriesPoint(
                    date=datetime(y, m, 1),
                    value=100.0 + i * 5,
                    label=f"Q{(m - 1) // 3 + 1} {y}",
                )
                for i, (y, m) in enumerate(quarters)
            ],
            interval="quarterly",
            source_documents=["Q1_2024.pdf", "Q2_2024.pdf", "Annual_2023.pdf"],
        )

        # Create realistic forecast result
        mock_forecast = ForecastResult(
            metric_name="revenue",
            historical_data=mock_ts_data.points,
            forecast=[
                ForecastPoint(
                    date=datetime(2024, 7, 1),
                    value=155.0,
                    lower=140.0,
                    upper=170.0,
                    label="Q3 2024",
                ),
                ForecastPoint(
                    date=datetime(2024, 10, 1),
                    value=162.0,
                    lower=145.0,
                    upper=179.0,
                    label="Q4 2024",
                ),
            ],
            confidence_reasoning="Revenue shows consistent 5% quarterly growth with narrow confidence intervals.",
            basis="Prophet model trained on 10 quarters of historical data",
            accuracy_estimate="±15% (NFR10 target)",
            periods_ahead=2,
        )

        with (
            patch(
                "raglite.main.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_extract,
            patch(
                "raglite.main.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ) as mock_generate,
        ):
            # Test natural language query
            request = ForecastQueryRequest(query="What's the revenue forecast for next 2 quarters?")
            response = await get_financial_forecast.fn(request)

        # Verify extraction was called with correct parameters
        mock_extract.assert_called_once()
        extract_call_kwargs = mock_extract.call_args.kwargs
        assert extract_call_kwargs["metric"] == "revenue"

        # Verify forecast generation was called
        mock_generate.assert_called_once()
        generate_call_kwargs = mock_generate.call_args.kwargs
        assert generate_call_kwargs["metric"] == "revenue"
        assert generate_call_kwargs["periods_ahead"] == 2

        # Verify response structure (AC2, AC3)
        assert isinstance(response, ForecastQueryResponse)
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
        from raglite.main import parse_forecast_query

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
        """Test that errors from time-series extraction propagate correctly (AC5)."""
        from raglite.forecasting.timeseries_extract import ExtractionError
        from raglite.main import get_financial_forecast
        from raglite.retrieval.search import QueryError

        with patch(
            "raglite.main.extract_timeseries",
            new_callable=AsyncMock,
            side_effect=ExtractionError("No revenue data found in documents"),
        ):
            request = ForecastQueryRequest(metric="revenue")

            with pytest.raises(QueryError) as exc_info:
                await get_financial_forecast.fn(request)

        assert "Could not extract revenue time-series data" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_propagation_from_forecast(self):
        """Test that errors from forecast generation propagate correctly (AC5)."""
        from raglite.forecasting.hybrid import InsufficientDataError
        from raglite.main import get_financial_forecast
        from raglite.retrieval.search import QueryError
        from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

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
                "raglite.main.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.main.generate_forecast",
                new_callable=AsyncMock,
                side_effect=InsufficientDataError("Need at least 8 data points, got 2"),
            ),
        ):
            request = ForecastQueryRequest(metric="revenue")

            with pytest.raises(QueryError) as exc_info:
                await get_financial_forecast.fn(request)

        assert "Insufficient historical data" in str(exc_info.value)
        assert "8 data points" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_structured_query_bypasses_nl_parsing(self):
        """Test that structured queries bypass NL parsing (AC1)."""
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

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
                "raglite.main.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_extract,
            patch(
                "raglite.main.generate_forecast",
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


# =============================================================================
# End-to-End Scenario Tests
# =============================================================================


class TestForecastQueryScenarios:
    """Scenario-based integration tests for common user workflows."""

    @pytest.mark.asyncio
    async def test_scenario_user_asks_about_revenue(self):
        """User scenario: 'What's the revenue forecast for next quarter?'"""
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

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
                TimeSeriesPoint(date=datetime(y, m, 1), value=100.0 + i * 3)
                for i, (y, m) in enumerate(quarters)
            ],
            source_documents=["Financial_Report.pdf"],
        )

        mock_forecast = ForecastResult(
            metric_name="revenue",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=125.0,
                    lower=118.0,
                    upper=132.0,
                    label="Q1 2025",
                ),
            ],
            confidence_reasoning="Revenue shows steady growth trend.",
            basis="Prophet model trained on 8 quarters",
            periods_ahead=1,
        )

        with (
            patch(
                "raglite.main.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.main.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ),
        ):
            request = ForecastQueryRequest(query="What's the revenue forecast for next quarter?")
            response = await get_financial_forecast.fn(request)

        # Verify user gets actionable response
        assert response.metric_name == "revenue"
        assert len(response.forecast) == 1
        assert response.forecast[0].label == "Q1 2025"
        assert "125" in str(response.forecast[0].value)
        assert len(response.confidence_reasoning) > 0

    @pytest.mark.asyncio
    async def test_scenario_user_asks_about_expenses_trend(self):
        """User scenario: 'Show me expense projections for the next 4 quarters'"""
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

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
            points=[
                TimeSeriesPoint(date=datetime(y, m, 1), value=40.0 + i * 2)
                for i, (y, m) in enumerate(quarters)
            ],
            source_documents=["Cost_Analysis.pdf", "Budget_2024.pdf"],
        )

        mock_forecast = ForecastResult(
            metric_name="expenses",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, i * 3 + 1, 1),
                    value=60.0 + i * 2,
                    lower=55.0 + i * 2,
                    upper=65.0 + i * 2,
                    label=f"Q{i + 1} 2025",
                )
                for i in range(4)
            ],
            confidence_reasoning="Expenses trending upward with moderate volatility.",
            basis="Prophet model trained on 8 quarters",
            periods_ahead=4,
        )

        with (
            patch(
                "raglite.main.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.main.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ),
        ):
            request = ForecastQueryRequest(
                query="Show me expense projections for the next 4 quarters"
            )
            response = await get_financial_forecast.fn(request)

        # Verify user gets 4-quarter projection
        assert response.metric_name == "expenses"
        assert len(response.forecast) == 4
        assert response.periods_ahead == 4
        assert response.forecast[0].label == "Q1 2025"
        assert response.forecast[3].label == "Q4 2025"

    @pytest.mark.asyncio
    async def test_scenario_insufficient_data_graceful_error(self):
        """User scenario: Request forecast but insufficient historical data"""
        from raglite.forecasting.hybrid import InsufficientDataError
        from raglite.main import get_financial_forecast
        from raglite.retrieval.search import QueryError
        from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

        # Only 4 data points (insufficient)
        mock_ts_data = TimeSeriesData(
            metric_name="revenue",
            points=[
                TimeSeriesPoint(date=datetime(2024, i * 3 + 1, 1), value=100.0) for i in range(4)
            ],
            source_documents=["Report.pdf"],
        )

        with (
            patch(
                "raglite.main.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.main.generate_forecast",
                new_callable=AsyncMock,
                side_effect=InsufficientDataError(
                    "Insufficient data. Minimum 8 data points required."
                ),
            ),
        ):
            request = ForecastQueryRequest(query="What's the revenue forecast?")

            with pytest.raises(QueryError) as exc_info:
                await get_financial_forecast.fn(request)

        # Verify user-friendly error message
        error_msg = str(exc_info.value)
        assert "Insufficient historical data" in error_msg
        assert "8 data points" in error_msg
        assert "revenue" in error_msg


# =============================================================================
# Response Format Validation Tests
# =============================================================================


class TestForecastResponseFormat:
    """Tests to verify response format meets MCP requirements."""

    @pytest.mark.asyncio
    async def test_response_serializable_to_json(self):
        """Test that response can be serialized to JSON for MCP transport."""
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

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
                "raglite.main.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.main.generate_forecast",
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
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

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
                "raglite.main.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.main.generate_forecast",
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


# =============================================================================
# Story 5.0.1: SQL-Based Time-Series Extraction Integration Tests
# =============================================================================


class TestSQLTimeseriesExtraction:
    """Integration tests for SQL-based time-series extraction (Story 5.0.1 AC4).

    These tests use the real PostgreSQL TEST database (port 5433).
    """

    @pytest.mark.asyncio
    async def test_sql_extraction_with_real_database(self):
        """Test SQL extraction with real PostgreSQL test database."""

        from raglite.forecasting.timeseries_extract import (
            ExtractionError,
            extract_timeseries_from_sql,
        )
        from raglite.shared.safety import SafetyGuard

        # Verify we're using TEST environment
        guard = SafetyGuard()
        guard.validate_test_environment("test_sql_extraction_with_real_database")

        # Try to extract revenue data from test database
        # Note: This requires test database to have data populated
        try:
            result = await extract_timeseries_from_sql(metric="revenue", min_points=8)

            # Verify result structure
            assert result.metric_name == "revenue"
            assert len(result.points) >= 8  # Should have at least 8 data points
            assert result.interval == "monthly"
            assert all(hasattr(point, "date") for point in result.points)
            assert all(hasattr(point, "value") for point in result.points)

            # Verify chronological sorting
            dates = [point.date for point in result.points]
            assert dates == sorted(dates), "Points should be sorted chronologically"

        except ExtractionError as e:
            # If test database has no data, this is expected
            pytest.skip(f"Test database has no revenue data: {e}")

    @pytest.mark.asyncio
    async def test_sql_extraction_no_data_raises_error(self):
        """Test that SQL extraction raises ExtractionError when no data found."""
        from raglite.forecasting.timeseries_extract import (
            ExtractionError,
            extract_timeseries_from_sql,
        )
        from raglite.shared.safety import SafetyGuard

        # Verify we're using TEST environment
        guard = SafetyGuard()
        guard.validate_test_environment("test_sql_extraction_no_data_raises_error")

        # Try to extract data for non-existent metric
        with pytest.raises(ExtractionError, match="No data found"):
            await extract_timeseries_from_sql(metric="nonexistent_metric_xyz_12345", min_points=8)

    @pytest.mark.asyncio
    async def test_sql_extraction_insufficient_data_raises_error(self):
        """Test that SQL extraction raises ExtractionError with <min_points data."""
        from raglite.forecasting.timeseries_extract import (
            ExtractionError,
            extract_timeseries_from_sql,
        )
        from raglite.shared.safety import SafetyGuard

        # Verify we're using TEST environment
        guard = SafetyGuard()
        guard.validate_test_environment("test_sql_extraction_insufficient_data_raises_error")

        # Try with unrealistically high min_points to trigger error
        # Note: Will match either "Insufficient data" or "No data found"
        with pytest.raises(ExtractionError, match="(Insufficient data|No data found)"):
            await extract_timeseries_from_sql(metric="revenue", min_points=1000000)


class TestSQLFirstExtractionFallback:
    """Integration tests for SQL-first extraction with fallback (Story 5.0.1 AC3)."""

    @pytest.mark.asyncio
    async def test_mcp_tool_uses_sql_first_then_fallback(self):
        """Test that MCP tool tries SQL first, then falls back to hybrid search."""
        from unittest.mock import AsyncMock, patch

        from raglite.forecasting.timeseries_extract import ExtractionError
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastQueryRequest,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

        # Mock SQL extraction to fail
        # Mock hybrid search extraction to succeed
        mock_ts_data = TimeSeriesData(
            metric_name="revenue",
            points=[
                TimeSeriesPoint(date=datetime(2024, m, 1), value=100.0 + m * 10)
                for m in range(1, 10)
            ],
            source_documents=["Report.pdf"],
        )

        mock_forecast = ForecastResult(
            metric_name="revenue",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=190.0,
                    lower=170.0,
                    upper=210.0,
                    label="Jan 2025",
                ),
            ],
            basis="Hybrid search fallback",
            periods_ahead=1,
        )

        with (
            patch(
                "raglite.main.extract_timeseries_from_sql",
                new_callable=AsyncMock,
                side_effect=ExtractionError("SQL extraction failed - no data"),
            ) as mock_sql,
            patch(
                "raglite.main.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_hybrid,
            patch(
                "raglite.main.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ),
        ):
            request = ForecastQueryRequest(metric="revenue")
            response = await get_financial_forecast.fn(request)

            # Verify SQL extraction was attempted first
            mock_sql.assert_called_once()
            mock_sql.assert_called_with(metric="revenue", min_points=8)

            # Verify fallback to hybrid search was triggered
            mock_hybrid.assert_called_once()

            # Verify response is valid
            assert response.metric_name == "revenue"
            assert len(response.forecast) > 0

    @pytest.mark.asyncio
    async def test_mcp_tool_uses_sql_successfully(self):
        """Test that MCP tool uses SQL extraction when it succeeds."""
        from unittest.mock import AsyncMock, patch

        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastQueryRequest,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

        # Mock SQL extraction to succeed
        mock_ts_data = TimeSeriesData(
            metric_name="revenue",
            points=[
                TimeSeriesPoint(date=datetime(2024, m, 1), value=100.0 + m * 10, label=f"Month {m}")
                for m in range(1, 10)
            ],
            source_documents=[],  # SQL has no source documents
        )

        mock_forecast = ForecastResult(
            metric_name="revenue",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=190.0,
                    lower=170.0,
                    upper=210.0,
                    label="Jan 2025",
                ),
            ],
            basis="SQL extraction",
            periods_ahead=1,
        )

        with (
            patch(
                "raglite.main.extract_timeseries_from_sql",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_sql,
            patch("raglite.main.extract_timeseries", new_callable=AsyncMock) as mock_hybrid,
            patch(
                "raglite.main.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ),
        ):
            request = ForecastQueryRequest(metric="revenue")
            response = await get_financial_forecast.fn(request)

            # Verify SQL extraction was attempted and succeeded
            mock_sql.assert_called_once()

            # Verify hybrid search was NOT called (SQL succeeded)
            mock_hybrid.assert_not_called()

            # Verify response is valid
            assert response.metric_name == "revenue"
            assert len(response.forecast) > 0

    @pytest.mark.asyncio
    async def test_fallback_behavior_with_various_sql_errors(self):
        """Test fallback behavior with different SQL error types."""
        from unittest.mock import AsyncMock, patch

        from raglite.forecasting.timeseries_extract import ExtractionError
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastQueryRequest,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

        error_scenarios = [
            ExtractionError("No data found in financial_tables for metric 'revenue'"),
            ExtractionError("Insufficient data: found 5 points, need 8 minimum"),
            ExtractionError("SQL query failed: connection timeout"),
        ]

        mock_ts_data = TimeSeriesData(
            metric_name="revenue",
            points=[
                TimeSeriesPoint(date=datetime(2024, m, 1), value=100.0 + m * 10)
                for m in range(1, 10)
            ],
            source_documents=["Report.pdf"],
        )

        mock_forecast = ForecastResult(
            metric_name="revenue",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=190.0,
                    lower=170.0,
                    upper=210.0,
                    label="Jan 2025",
                ),
            ],
            basis="Hybrid search fallback",
            periods_ahead=1,
        )

        for error in error_scenarios:
            with (
                patch(
                    "raglite.main.extract_timeseries_from_sql",
                    new_callable=AsyncMock,
                    side_effect=error,
                ),
                patch(
                    "raglite.main.extract_timeseries",
                    new_callable=AsyncMock,
                    return_value=mock_ts_data,
                ),
                patch(
                    "raglite.main.generate_forecast",
                    new_callable=AsyncMock,
                    return_value=mock_forecast,
                ),
            ):
                request = ForecastQueryRequest(metric="revenue")
                response = await get_financial_forecast.fn(request)

                # Verify response is valid for all error scenarios
                assert response.metric_name == "revenue"
                assert len(response.forecast) > 0
