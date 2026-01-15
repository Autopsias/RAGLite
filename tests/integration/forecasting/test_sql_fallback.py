"""Integration tests for SQL-first extraction with fallback logic.

Split from test_forecast_workflows.py to maintain file size <500 LOC (Story 8-4b).

Tests SQL-first extraction pattern where MCP tool attempts SQL extraction
before falling back to hybrid search (Story 5.0.1 AC3).
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from raglite.shared.models import ForecastQueryRequest

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestSQLFirstExtractionFallback:
    """Integration tests for SQL-first extraction with fallback (Story 5.0.1 AC3)."""

    @pytest.mark.asyncio
    async def test_mcp_tool_uses_sql_first_then_fallback(self):
        """Test that MCP tool tries SQL first, then falls back to hybrid search."""
        from raglite.forecasting.timeseries import ExtractionError
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
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
                "raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type",
                new_callable=AsyncMock,
                side_effect=ExtractionError("SQL extraction failed - no data"),
            ) as mock_sql,
            patch(
                "raglite.mcp.tools.forecast_helpers.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_hybrid,
            patch(
                "raglite.mcp.tools.forecast_helpers.generate_forecast",
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
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
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
                "raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ) as mock_sql,
            patch(
                "raglite.mcp.tools.forecast_helpers.extract_timeseries", new_callable=AsyncMock
            ) as mock_hybrid,
            patch(
                "raglite.mcp.tools.forecast_helpers.generate_forecast",
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
        from raglite.forecasting.timeseries import ExtractionError
        from raglite.main import get_financial_forecast
        from raglite.shared.models import (
            ForecastPoint,
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
                    "raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type",
                    new_callable=AsyncMock,
                    side_effect=error,
                ),
                patch(
                    "raglite.mcp.tools.forecast_helpers.extract_timeseries",
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

                # Verify response is valid for all error scenarios
                assert response.metric_name == "revenue"
                assert len(response.forecast) > 0
