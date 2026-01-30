"""Unit tests for Story 4.4: Forecast Query Models and Parser.

Tests the ForecastQueryRequest/Response models and parse_forecast_query helper function.
"""

from datetime import datetime

import pytest

from raglite.shared.models import (
    ForecastPoint,
    ForecastQueryRequest,
    ForecastQueryResponse,
    ForecastResult,
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
        """Test that periods_ahead must be <= 18."""
        with pytest.raises(ValueError):
            ForecastQueryRequest(metric="revenue", periods_ahead=19)

    def test_valid_periods_range(self):
        """Test valid periods_ahead values within range (1-18)."""
        for periods in [1, 2, 4, 6, 8, 10, 12, 13, 15, 18]:
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
        assert 1 <= periods <= 12

    def test_periods_capped_at_18(self):
        """Test that periods are capped at maximum 18."""
        from raglite.main import parse_forecast_query

        _, periods = parse_forecast_query("Forecast revenue for next 20 quarters")
        assert periods == 18

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
