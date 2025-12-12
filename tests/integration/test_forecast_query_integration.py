"""Integration tests for Story 4.4: Forecast Query Tool (MCP).

Tests end-to-end flow from MCP tool through time-series extraction and forecasting.
Requires mocked Qdrant and Mistral API for reproducible testing.

Story 5.0.4 Advisory: Added dynamic metric forecasting integration tests.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.shared.models import ForecastQueryRequest, ForecastQueryResponse

# Import database test fixtures

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
                "raglite.main.extract_timeseries_from_sql",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_extract_sql,
            patch(
                "raglite.main.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
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
                "raglite.main.extract_timeseries_from_sql",
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

        # FIX: Updated to check for enhanced validation error format
        error_msg = str(exc_info.value)
        # Accept either the old "Insufficient historical data" format or new validation format
        assert "Insufficient historical data" in error_msg or "data points" in error_msg, (
            f"Expected insufficient data error, got: {error_msg}"
        )
        # Verify it mentions the metric and requirement
        assert "revenue" in error_msg.lower()
        assert "minimum" in error_msg or "8" in error_msg or "required" in error_msg


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
                "raglite.main.extract_timeseries_from_sql",
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
                "raglite.main.extract_timeseries_from_sql",
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

    @pytest.fixture(autouse=True)
    def setup_test_data(self, test_financial_data):
        """Ensure test financial data is loaded for all tests in this class."""
        pass

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
        # DATABASE FIX (2025-12-03): Updated regex to match new MetricValidationError format
        # Note: Will match either "has X data points" (MetricValidationError) or "No data found" (ExtractionError)
        with pytest.raises(
            ExtractionError,
            match="(has \\d+ data points|Insufficient data|No data found)",
        ):
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
            # FIX (2025-12-03): Updated min_points to match DEFAULT_MIN_FORECAST_POINTS = 6 (raglite/forecasting/timeseries_extract.py:36)
            mock_sql.assert_called_once()
            mock_sql.assert_called_with(metric="revenue", min_points=6)

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


# =============================================================================
# Story 5.0.4 Advisory: Dynamic Metric Forecasting Integration Tests
# =============================================================================


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
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

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
                "raglite.main.extract_timeseries_from_sql",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_sql,
            patch(
                "raglite.main.generate_forecast",
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
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

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
                "raglite.main.extract_timeseries_from_sql",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.main.generate_forecast",
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
        from raglite.forecasting.timeseries_extract import MetricValidationError
        from raglite.main import get_financial_forecast
        from raglite.retrieval.search import QueryError

        # Create MetricValidationError with available metrics
        validation_error = MetricValidationError(
            metric_name="unknown_metric",
            data_points_found=3,
            minimum_required=8,
            available_metrics=["revenue", "ebitda"],
        )

        with patch(
            "raglite.main.extract_timeseries_from_sql",
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
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
            ForecastResult,
            TimeSeriesData,
            TimeSeriesPoint,
        )

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
                "raglite.main.extract_timeseries_from_sql",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_sql,
            patch(
                "raglite.main.generate_forecast",
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
        from raglite.shared.config import settings

        # Verify default TTL is 300 seconds (5 minutes)
        assert hasattr(settings, "metrics_cache_ttl_seconds")
        assert settings.metrics_cache_ttl_seconds == 300

    def test_metrics_module_uses_settings_ttl(self):
        """Test that metrics module uses configurable TTL from settings."""
        from raglite.forecasting.metrics import _get_cache_ttl
        from raglite.shared.config import settings

        # Verify _get_cache_ttl returns the settings value
        assert _get_cache_ttl() == settings.metrics_cache_ttl_seconds

    @pytest.mark.asyncio
    async def test_cache_respects_custom_ttl(self):
        """Test that cache respects custom TTL setting."""
        from raglite.forecasting.metrics import (
            _get_cache_ttl,
            clear_metrics_cache,
            list_available_metrics,
        )

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
