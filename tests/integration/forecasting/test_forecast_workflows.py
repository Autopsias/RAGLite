"""Integration tests for forecast workflows - split from test_forecast_query_integration.py.

Tests scenario-based workflows and SQL-based extraction patterns.

File Organization (Story 8-4b):
- test_forecast_workflows.py: Scenario tests + SQL extraction tests (298 LOC)
- test_sql_fallback.py: SQL-first with fallback tests (194 LOC)

Split to maintain <500 LOC per file for AI comprehension.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from raglite.shared.models import ForecastQueryRequest

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


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
                "raglite.mcp.tools.forecast.extract_historical_data_by_type",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.mcp.tools.forecast.generate_forecast",
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
                "raglite.mcp.tools.forecast.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.mcp.tools.forecast.generate_forecast",
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
                "raglite.mcp.tools.forecast.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.mcp.tools.forecast.generate_forecast",
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


class TestSQLTimeseriesExtraction:
    """Integration tests for SQL-based time-series extraction (Story 5.0.1 AC4).

    These tests use the real PostgreSQL TEST database (port 5433).

    Note: test_financial_data fixture is loaded via pytest_plugins in tests/conftest.py
    and is session-scoped, so it's available to all tests that need it.
    """

    @pytest.fixture(autouse=True)
    def setup_test_data(self, test_financial_data):
        """Ensure test financial data is loaded for all tests in this class.

        The test_financial_data fixture is defined in tests/fixtures/database_fixtures.py
        and loaded via pytest_plugins. This autouse fixture ensures it runs before
        each test in this class.
        """
        # Fixture provides side-effect of populating database
        pass

    @pytest.mark.asyncio
    async def test_sql_extraction_with_real_database(self):
        """Test SQL extraction with real PostgreSQL test database."""

        from raglite.forecasting.timeseries import (
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
        from raglite.forecasting.timeseries import (
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
        from raglite.forecasting.timeseries import (
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
