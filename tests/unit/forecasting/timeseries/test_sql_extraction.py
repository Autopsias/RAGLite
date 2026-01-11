"""Unit tests for SQL-based time-series extraction (Story 5.0.1).

Tests cover:
- AC2: SQL-based extraction with ≥8 data points
- AC3: Insufficient data validation with available metrics
- AC5: EBITDA consolidated GROUP extraction
"""

from unittest.mock import MagicMock, patch

import pytest

from raglite.forecasting.timeseries import (
    ExtractionError,
    MetricValidationError,
    extract_timeseries_from_sql,
)
from raglite.shared.models import TimeSeriesData


@pytest.mark.asyncio
class TestExtractTimeseriesFromSQL:
    """Test SQL-based time-series extraction - Story 5.0.1 AC2."""

    async def test_successful_extraction_sufficient_data(self) -> None:
        """Test successful extraction with ≥8 data points."""
        # Mock SQL connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.5, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.2, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.8, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.3, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.5, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.2, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.8, 1, "2024-08 Performance Review", False),
            ("Sep-24", 2024, 140.3, 1, "2024-09 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="revenue", min_points=8)

            # Verify result
            assert isinstance(result, TimeSeriesData)
            assert result.metric_name == "revenue"
            assert len(result.points) == 9  # All 9 data points returned
            assert result.interval == "monthly"

            # Verify points are sorted chronologically
            assert result.points[0].date.month == 1  # Jan
            assert result.points[-1].date.month == 9  # Sep

            # Verify SQL query was executed with synonym-mapped metric
            mock_cursor.execute.assert_called_once()
            # "revenue" gets mapped to "turnover" via synonym mapping
            assert "turnover" in mock_cursor.execute.call_args[0][1]

    async def test_insufficient_data_raises_error(self) -> None:
        """Test that <min_points data raises ExtractionError (fallback when metrics can't be fetched)."""
        # Mock SQL connection with only 5 data points
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.5, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.2, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.8, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.3, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Mock list_available_metrics to fail, ensuring fallback to ExtractionError
            with patch("raglite.forecasting.metrics.list_available_metrics") as mock_list:
                mock_list.side_effect = Exception("Metrics fetch failed")

                # When list_available_metrics fails, falls back to ExtractionError
                with pytest.raises(ExtractionError, match="Insufficient data.*found 5.*need 6"):
                    await extract_timeseries_from_sql(metric="revenue", min_points=6)

    async def test_no_data_found_raises_error(self) -> None:
        """Test that no SQL data raises ExtractionError."""
        # Mock SQL connection with no results
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            with pytest.raises(ExtractionError, match="No data found in financial_tables"):
                await extract_timeseries_from_sql(metric="revenue", min_points=8)

    async def test_invalid_data_points_skipped(self) -> None:
        """Test that invalid data points are skipped with warnings."""
        # Mock SQL connection with mix of valid and invalid data
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.5, 1, "2024-01 Performance Review", False),
            (
                "InvalidFormat",
                2024,
                105.2,
                1,
                "2024-02 Performance Review",
                False,
            ),  # Invalid period format
            (
                "Mar-24",
                2024,
                "not_a_number",
                1,
                "2024-03 Performance Review",
                False,
            ),  # Invalid value
            ("Apr-24", 2024, 115.3, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.5, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.2, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.8, 1, "2024-08 Performance Review", False),
            ("Sep-24", 2024, 140.3, 1, "2024-09 Performance Review", False),
            ("Oct-24", 2024, 145.0, 1, "2024-10 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="revenue", min_points=8)

            # Should have 8 valid points (2 invalid skipped)
            assert len(result.points) == 8

    async def test_sql_query_error_handling(self) -> None:
        """Test that SQL query errors are caught and re-raised as ExtractionError."""
        # Mock SQL connection that raises an error
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("Database connection error")

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            with pytest.raises(ExtractionError, match="SQL query failed"):
                await extract_timeseries_from_sql(metric="revenue", min_points=8)

    async def test_metric_pattern_matching(self) -> None:
        """Test that metric uses LIKE pattern for flexible matching."""
        # Mock SQL connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.5, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.2, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.8, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.3, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.5, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.2, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.8, 1, "2024-08 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="revenue", min_points=8)

            # Should match via synonym mapping (revenue → turnover)
            assert len(result.points) == 8

            # Verify synonym mapping was applied (revenue → turnover)
            assert "turnover" in mock_cursor.execute.call_args[0][1]

    async def test_chronological_sorting(self) -> None:
        """Test that results are sorted chronologically by fiscal_year and period."""
        # Mock SQL connection with unsorted data
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jun-24", 2024, 125.5, 1, "2024-06 Performance Review", False),
            ("Jan-24", 2024, 100.5, 1, "2024-01 Performance Review", False),
            ("Dec-24", 2024, 150.0, 1, "2024-12 Performance Review", False),
            ("Mar-24", 2024, 110.8, 1, "2024-03 Performance Review", False),
            ("Sep-24", 2024, 140.3, 1, "2024-09 Performance Review", False),
            ("Apr-24", 2024, 115.3, 1, "2024-04 Performance Review", False),
            ("Feb-24", 2024, 105.2, 1, "2024-02 Performance Review", False),
            ("Aug-24", 2024, 135.8, 1, "2024-08 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="revenue", min_points=8)

            # Verify points are sorted chronologically
            dates = [p.date for p in result.points]
            assert dates == sorted(dates)

            # Verify first and last months
            assert result.points[0].date.month == 1  # Jan
            assert result.points[-1].date.month == 12  # Dec

    # Story 5.0.4 AC2: Tests for dynamic metric support
    async def test_arbitrary_metric_names_accepted(self) -> None:
        """Test that arbitrary metric names like 'capex', 'margins' are accepted (AC2)."""
        # Mock SQL connection for a custom metric "capex"
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 50.0, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 52.0, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 48.5, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 51.2, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 53.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 49.8, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 54.5, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 52.3, 1, "2024-08 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Should accept any metric name
            result = await extract_timeseries_from_sql(metric="capex", min_points=8)

            # Verify result
            assert result.metric_name == "capex"
            assert len(result.points) == 8
            # Verify metric name was used in query
            call_args = mock_cursor.execute.call_args[0]
            assert "capex" in call_args[1]

    async def test_metric_name_case_insensitivity(self) -> None:
        """Test that metric names are case insensitive: 'REVENUE' and 'revenue' return same data (AC2)."""
        # Test uppercase
        mock_cursor_upper = MagicMock()
        mock_cursor_upper.fetchall.return_value = [
            ("Jan-24", 2024, 100.0, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.0, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.0, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.0, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.0, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.0, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.0, 1, "2024-08 Performance Review", False),
        ]

        mock_conn_upper = MagicMock()
        mock_conn_upper.cursor.return_value = mock_cursor_upper

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn_upper

            result_upper = await extract_timeseries_from_sql(metric="REVENUE", min_points=8)
            assert result_upper.metric_name == "REVENUE"
            assert len(result_upper.points) == 8

            # Verify synonym mapping was used (REVENUE → revenue → turnover)
            call_args = mock_cursor_upper.execute.call_args[0]
            assert "turnover" in call_args[1]

        # Test lowercase (separate mock to avoid state issues)
        mock_cursor_lower = MagicMock()
        mock_cursor_lower.fetchall.return_value = [
            ("Jan-24", 2024, 100.0, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.0, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.0, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.0, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.0, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.0, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.0, 1, "2024-08 Performance Review", False),
        ]

        mock_conn_lower = MagicMock()
        mock_conn_lower.cursor.return_value = mock_cursor_lower

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn_lower

            result_lower = await extract_timeseries_from_sql(metric="revenue", min_points=8)
            assert result_lower.metric_name == "revenue"
            assert len(result_lower.points) == 8

            # Verify synonym mapping was used (revenue → turnover)
            call_args = mock_cursor_lower.execute.call_args[0]
            assert "turnover" in call_args[1]

    async def test_metric_synonym_resolution(self) -> None:
        """Test that metric synonyms are resolved correctly (AC2)."""
        # Mock SQL connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.0, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.0, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.0, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.0, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.0, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.0, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.0, 1, "2024-08 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Test "revenue" → "turnover" synonym
            _result = await extract_timeseries_from_sql(metric="revenue", min_points=8)

            # Verify SQL query uses "turnover" (synonym)
            call_args = mock_cursor.execute.call_args[0]
            assert "turnover" in call_args[1]  # Parameter should be "turnover"

            # Test "ebitda" → "EBITDA IFRS" synonym (Story 6.26: Restored)
            mock_cursor.reset_mock()
            _result_ebitda = await extract_timeseries_from_sql(metric="ebitda", min_points=8)

            call_args = mock_cursor.execute.call_args[0]
            # EBITDA synonym mapping - "ebitda" maps to "EBITDA IFRS" for consolidated YTD data
            assert (
                "EBITDA IFRS" in call_args[1]
            )  # Parameter should be "EBITDA IFRS" (synonym mapping applied)

    # Story 5.0.4 AC5: Test EBITDA consolidated GROUP extraction
    async def test_ebitda_uses_consolidated_group_values(self) -> None:
        """Test that EBITDA extraction uses consolidated GROUP values automatically (AC5)."""
        # Mock SQL connection with GROUP entity filtering
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (
                "Jan-24",
                2024,
                155.5,
                3,
                "2024-01 Performance Review",
                False,
            ),  # Consolidated GROUP sum
            ("Feb-24", 2024, 160.2, 3, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 165.8, 3, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 170.3, 3, "2024-04 Performance Review", False),
            ("May-24", 2024, 175.0, 3, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 180.5, 3, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 185.2, 3, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 190.8, 3, "2024-08 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Extract EBITDA (should use consolidated GROUP filtering)
            result = await extract_timeseries_from_sql(metric="ebitda", min_points=8)

            # Verify result
            assert result.metric_name == "ebitda"
            assert len(result.points) == 8

            # Verify SQL query includes GROUP entity filter
            call_args = mock_cursor.execute.call_args[0]
            query = call_args[0]
            # Query should filter to GROUP entity
            assert "GROUP" in query or "group" in query or "consolidated" in query

    # Story 5.0.4 AC3: Tests for insufficient data validation
    async def test_insufficient_data_raises_metric_validation_error(self) -> None:
        """Test that <min_points data raises MetricValidationError with available metrics (AC3)."""

        # Mock SQL connection with only 3 data points
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.0, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.0, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.0, 1, "2024-03 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Mock list_available_metrics to return alternative metrics
            with patch("raglite.forecasting.metrics.list_available_metrics") as mock_list:
                from raglite.forecasting.metrics import MetricInfo

                # Note: period column is VARCHAR, not datetime (Story 5.0.4 fix)
                mock_list.return_value = [
                    MetricInfo(
                        name="revenue",
                        data_point_count=12,
                        min_period="Jan-23",
                        max_period="Dec-24",
                        can_forecast=True,
                    ),
                    MetricInfo(
                        name="ebitda",
                        data_point_count=10,
                        min_period="Jan-23",
                        max_period="Oct-24",
                        can_forecast=True,
                    ),
                ]

                # Should raise MetricValidationError
                with pytest.raises(MetricValidationError) as exc_info:
                    await extract_timeseries_from_sql(metric="margins", min_points=8)

                # Verify error details
                error = exc_info.value
                assert error.metric_name == "margins"
                assert error.data_points_found == 3
                assert error.minimum_required == 8
                assert "revenue" in error.available_metrics
                assert "ebitda" in error.available_metrics
                assert "margins" in str(error)  # Error message mentions the metric

    async def test_unknown_metric_suggests_available_metrics(self) -> None:
        """Test that unknown metric raises ExtractionError with available metrics suggestion (AC3)."""
        # Mock SQL connection with no results
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # No data found

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Mock list_available_metrics
            with patch("raglite.forecasting.metrics.list_available_metrics") as mock_list:
                from raglite.forecasting.metrics import MetricInfo

                # Note: period column is VARCHAR, not datetime (Story 5.0.4 fix)
                mock_list.return_value = [
                    MetricInfo(
                        name="revenue",
                        data_point_count=12,
                        min_period="Jan-23",
                        max_period="Dec-24",
                        can_forecast=True,
                    ),
                    MetricInfo(
                        name="ebitda",
                        data_point_count=10,
                        min_period="Jan-23",
                        max_period="Oct-24",
                        can_forecast=True,
                    ),
                ]

                # Should raise ExtractionError with available metrics
                with pytest.raises(ExtractionError):
                    await extract_timeseries_from_sql(metric="unknown_metric", min_points=8)
