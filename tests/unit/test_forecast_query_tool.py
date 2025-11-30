"""Unit tests for Story 4.4: Forecast Query Tool (MCP).

Tests the get_financial_forecast MCP tool, ForecastQueryRequest/Response models,
and parse_forecast_query helper function.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from raglite.shared.models import (
    ForecastPoint,
    ForecastQueryRequest,
    ForecastQueryResponse,
    ForecastResult,
    TimeSeriesData,
    TimeSeriesPoint,
)

# =============================================================================
# Test ForecastQueryRequest Model (AC1)
# =============================================================================


class TestForecastQueryRequest:
    """Tests for the ForecastQueryRequest model."""

    def test_structured_query_all_params(self):
        """Test creating request with all structured parameters."""
        request = ForecastQueryRequest(
            metric="revenue",
            periods_ahead=4,
            query=None,
        )

        assert request.metric == "revenue"
        assert request.periods_ahead == 4
        assert request.query is None

    def test_structured_query_defaults(self):
        """Test default values for optional parameters."""
        request = ForecastQueryRequest(metric="cash_flow")

        assert request.metric == "cash_flow"
        assert request.periods_ahead == 4  # Default
        assert request.query is None  # Default

    def test_natural_language_query_only(self):
        """Test creating request with only NL query parameter."""
        request = ForecastQueryRequest(query="What's the revenue forecast for next quarter?")

        assert request.metric is None
        assert request.periods_ahead == 4  # Default
        assert request.query == "What's the revenue forecast for next quarter?"

    def test_combined_query_and_metric(self):
        """Test request with both metric and query (metric takes precedence)."""
        request = ForecastQueryRequest(
            metric="expenses",
            query="Forecast revenue for next quarter",  # Conflicting query
        )

        assert request.metric == "expenses"  # Explicit metric wins
        assert request.query == "Forecast revenue for next quarter"

    def test_periods_validation_minimum(self):
        """Test that periods_ahead must be >= 1."""
        with pytest.raises(ValueError):
            ForecastQueryRequest(metric="revenue", periods_ahead=0)

    def test_periods_validation_maximum(self):
        """Test that periods_ahead must be <= 8."""
        with pytest.raises(ValueError):
            ForecastQueryRequest(metric="revenue", periods_ahead=9)

    def test_valid_periods_range(self):
        """Test valid periods_ahead values within range."""
        for periods in [1, 2, 4, 6, 8]:
            request = ForecastQueryRequest(metric="revenue", periods_ahead=periods)
            assert request.periods_ahead == periods

    def test_all_supported_metrics(self):
        """Test creating requests with all supported metrics."""
        for metric in ["revenue", "cash_flow", "expenses"]:
            request = ForecastQueryRequest(metric=metric)
            assert request.metric == metric


# =============================================================================
# Test ForecastQueryResponse Model (AC2, AC3)
# =============================================================================


class TestForecastQueryResponse:
    """Tests for the ForecastQueryResponse model."""

    def test_response_with_all_fields(self):
        """Test creating response with all fields populated."""
        forecast_points = [
            ForecastPoint(
                date=datetime(2025, 1, 1),
                value=100.0,
                lower=95.0,
                upper=105.0,
                label="Q1 2025",
            ),
            ForecastPoint(
                date=datetime(2025, 4, 1),
                value=110.0,
                lower=100.0,
                upper=120.0,
                label="Q2 2025",
            ),
        ]

        response = ForecastQueryResponse(
            metric_name="revenue",
            forecast=forecast_points,
            basis="Prophet model trained on 12 quarters of historical data",
            confidence_reasoning="Wide intervals due to market volatility.",
            methodology="Prophet + Mistral Large hybrid forecasting",
            accuracy_estimate="±15% (NFR10 target)",
            source_documents=["Q1_2024.pdf", "Q2_2024.pdf"],
            periods_ahead=2,
        )

        assert response.metric_name == "revenue"
        assert len(response.forecast) == 2
        assert response.forecast[0].value == 100.0
        assert response.forecast[0].lower == 95.0
        assert response.forecast[0].upper == 105.0
        assert "Prophet" in response.basis
        assert "volatility" in response.confidence_reasoning
        assert response.methodology == "Prophet + Mistral Large hybrid forecasting"
        assert len(response.source_documents) == 2
        assert response.periods_ahead == 2

    def test_response_defaults(self):
        """Test default values for optional fields."""
        response = ForecastQueryResponse(
            metric_name="cash_flow",
            basis="Test basis",
            periods_ahead=4,
        )

        assert response.forecast == []
        assert response.confidence_reasoning == ""
        assert response.methodology == "Prophet + Mistral Large hybrid forecasting"
        assert response.accuracy_estimate == "±15% (NFR10 target)"
        assert response.source_documents == []

    def test_forecast_points_confidence_intervals(self):
        """Test that forecast points have valid confidence intervals (AC2)."""
        response = ForecastQueryResponse(
            metric_name="expenses",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=50.0,
                    lower=45.0,
                    upper=55.0,
                    label="Q1 2025",
                ),
            ],
            basis="Test basis",
            periods_ahead=1,
        )

        point = response.forecast[0]
        # lower <= value <= upper
        assert point.lower <= point.value <= point.upper

    def test_from_forecast_result_factory(self):
        """Test the from_forecast_result factory method."""
        historical = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=90.0, label="Q1 2024"),
            TimeSeriesPoint(date=datetime(2024, 4, 1), value=95.0, label="Q2 2024"),
        ]
        forecast_points = [
            ForecastPoint(
                date=datetime(2025, 1, 1),
                value=100.0,
                lower=95.0,
                upper=105.0,
                label="Q1 2025",
            ),
        ]

        forecast_result = ForecastResult(
            metric_name="revenue",
            historical_data=historical,
            forecast=forecast_points,
            confidence_reasoning="Model shows stable growth pattern.",
            basis="Prophet model trained on 8 quarters",
            accuracy_estimate="±15%",
            periods_ahead=4,
        )

        response = ForecastQueryResponse.from_forecast_result(
            forecast_result,
            source_documents=["Q1_2024.pdf", "Q2_2024.pdf"],
        )

        assert response.metric_name == "revenue"
        assert len(response.forecast) == 1
        assert response.basis == "Prophet model trained on 8 quarters"
        assert response.confidence_reasoning == "Model shows stable growth pattern."
        assert response.source_documents == ["Q1_2024.pdf", "Q2_2024.pdf"]
        assert response.periods_ahead == 4

    def test_from_forecast_result_no_sources(self):
        """Test factory method with no source documents."""
        forecast_result = ForecastResult(
            metric_name="expenses",
            historical_data=[],
            forecast=[],
            basis="Test",
            periods_ahead=1,
        )

        response = ForecastQueryResponse.from_forecast_result(forecast_result)

        assert response.source_documents == []


# =============================================================================
# Test parse_forecast_query (AC4)
# =============================================================================


class TestParseForecastQuery:
    """Tests for the parse_forecast_query helper function."""

    def test_revenue_metric_extraction(self):
        """Test extracting revenue metric from various queries."""
        from raglite.main import parse_forecast_query

        queries = [
            "What's the revenue forecast?",
            "Forecast sales for next quarter",
            "What will income look like?",
        ]

        for query in queries:
            metric, _ = parse_forecast_query(query)
            assert metric == "revenue", f"Failed for query: {query}"

    def test_cash_flow_metric_extraction(self):
        """Test extracting cash_flow metric from various queries."""
        from raglite.main import parse_forecast_query

        queries = [
            "Forecast cash flow",
            "What's the cashflow projection?",
            "cash flow for next year",
        ]

        for query in queries:
            metric, _ = parse_forecast_query(query)
            assert metric == "cash_flow", f"Failed for query: {query}"

    def test_expenses_metric_extraction(self):
        """Test extracting expenses metric from various queries."""
        from raglite.main import parse_forecast_query

        queries = [
            "What will expenses be?",
            "Forecast cost for next quarter",
            "Predict spending trends",
        ]

        for query in queries:
            metric, _ = parse_forecast_query(query)
            assert metric == "expenses", f"Failed for query: {query}"

    def test_next_quarter_period(self):
        """Test parsing 'next quarter' as 1 period."""
        from raglite.main import parse_forecast_query

        _, periods = parse_forecast_query("Revenue forecast for next quarter")
        assert periods == 1

    def test_next_n_quarters_period(self):
        """Test parsing 'next N quarters' pattern."""
        from raglite.main import parse_forecast_query

        test_cases = [
            ("Forecast revenue for the next 2 quarters", 2),
            ("Revenue forecast next 4 quarters", 4),
            ("Cash flow for the next 6 quarters", 6),
        ]

        for query, expected_periods in test_cases:
            _, periods = parse_forecast_query(query)
            assert periods == expected_periods, f"Failed for query: {query}"

    def test_for_n_quarters_period(self):
        """Test parsing 'for N quarters' pattern."""
        from raglite.main import parse_forecast_query

        _, periods = parse_forecast_query("Forecast expenses for 3 quarters")
        assert periods == 3

    def test_specific_quarter_reference(self):
        """Test parsing specific quarter references like 'Q1 2026'."""
        from raglite.main import parse_forecast_query

        # This test is time-dependent, but we can verify it returns a value
        _, periods = parse_forecast_query("Predict revenue for Q1 2026")
        assert periods is not None
        assert 1 <= periods <= 8

    def test_periods_capped_at_8(self):
        """Test that periods are capped at maximum 8."""
        from raglite.main import parse_forecast_query

        _, periods = parse_forecast_query("Forecast revenue for next 20 quarters")
        assert periods == 8

    def test_no_metric_found(self):
        """Test when no metric can be extracted."""
        from raglite.main import parse_forecast_query

        metric, _ = parse_forecast_query("What's the weather forecast?")
        assert metric is None

    def test_no_period_found(self):
        """Test when no period can be extracted."""
        from raglite.main import parse_forecast_query

        _, periods = parse_forecast_query("What's the revenue forecast?")
        assert periods is None

    def test_full_query_parsing(self):
        """Test complete query parsing with metric and period."""
        from raglite.main import parse_forecast_query

        metric, periods = parse_forecast_query("What's the revenue forecast for next quarter?")
        assert metric == "revenue"
        assert periods == 1

    def test_case_insensitivity(self):
        """Test that parsing is case insensitive."""
        from raglite.main import parse_forecast_query

        metric, _ = parse_forecast_query("REVENUE FORECAST FOR NEXT QUARTER")
        assert metric == "revenue"


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

        assert response.metric_name == "revenue"
        assert len(response.forecast) == 1
        assert response.forecast[0].value == 150.0
        assert response.forecast[0].lower == 140.0
        assert response.forecast[0].upper == 160.0
        assert "Prophet model trained on 8 quarters" in response.basis
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

        # NL parsing should extract "revenue" and periods=1
        assert response.metric_name == "revenue"
        assert response.periods_ahead == 1

    @pytest.mark.asyncio
    async def test_invalid_metric_error(self):
        """Test error handling for metric with no data."""
        from raglite.forecasting.timeseries_extract import ExtractionError
        from raglite.main import get_financial_forecast
        from raglite.retrieval.search import QueryError

        # Mock SQL extraction to fail (no data for this metric)
        with (
            patch(
                "raglite.main.extract_timeseries_from_sql",
                new_callable=AsyncMock,
                side_effect=ExtractionError(
                    "No data found in financial_tables for metric 'invalid_metric'"
                ),
            ),
            patch(
                "raglite.main.extract_timeseries",  # Fallback also fails
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
            patch(
                "raglite.main.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.main.generate_forecast",
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
        from raglite.forecasting.timeseries_extract import ExtractionError
        from raglite.main import get_financial_forecast
        from raglite.retrieval.search import QueryError

        with patch(
            "raglite.main.extract_timeseries",
            new_callable=AsyncMock,
            side_effect=ExtractionError("No documents found"),
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

        with patch(
            "raglite.main.extract_timeseries",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Unexpected crash"),
        ):
            request = ForecastQueryRequest(metric="revenue")

            with pytest.raises(QueryError) as exc_info:
                await get_financial_forecast.fn(request)

        assert "Forecast generation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cash_flow_metric(self):
        """Test forecast for cash_flow metric."""
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
            request = ForecastQueryRequest(query="Forecast cash flow for the next 4 quarters")
            response = await get_financial_forecast.fn(request)

        assert response.metric_name == "cash_flow"

    @pytest.mark.asyncio
    async def test_expenses_metric(self):
        """Test forecast for expenses metric."""
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
            request = ForecastQueryRequest(query="Predict expenses for next 2 quarters")
            response = await get_financial_forecast.fn(request)

        assert response.metric_name == "expenses"

    @pytest.mark.asyncio
    async def test_response_includes_methodology(self):
        """Test that response includes methodology field (AC3)."""
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
            forecast=[],
            basis="Test",
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
            request = ForecastQueryRequest(metric="revenue")
            response = await get_financial_forecast.fn(request)

        assert "Prophet" in response.methodology
        assert "Mistral" in response.methodology

    @pytest.mark.asyncio
    async def test_enhanced_basis_with_document_count(self):
        """Test that basis includes document count (AC3)."""
        from raglite.main import get_financial_forecast

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

        assert "10 quarters" in response.basis
        assert "3 documents" in response.basis

    @pytest.mark.asyncio
    async def test_metric_case_insensitive(self):
        """Test that metric parameter is case insensitive."""
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
            forecast=[],
            basis="Test",
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
