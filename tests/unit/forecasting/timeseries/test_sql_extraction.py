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
from raglite.forecasting.timeseries.metadata import UnitMixingError


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
            assert result.__class__.__name__ == "TimeSeriesData"
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


@pytest.mark.asyncio
class TestEntityColumnFallback:
    """Test Phase 3 entity column fallback for inverted data (Story 8.x fix)."""

    async def test_entity_column_fallback_for_inverted_data(self) -> None:
        """Test that extraction falls back to entity column when metric is NULL.

        This handles the inverted data pattern where:
        - metric = NULL or 'None'
        - entity = 'EBITDA IFRS' (should be in metric column)

        The fallback searches entity column when metric column search fails.
        """
        mock_cursor = MagicMock()
        # Simulate inverted data scenario:
        # Phase 1 (exact match on metric): 0 rows
        # Phase 2 (wildcard on metric): 0 rows
        # Phase 3 (entity column fallback): finds data
        mock_cursor.fetchall.side_effect = [
            [],  # Phase 1: exact match on metric column fails
            [],  # Phase 2: wildcard match on metric column fails
            [  # Phase 3: entity column match succeeds
                ("Aug-25", 2025, 128.83, 1, "Performance Review", True),
                ("Sep-25", 2025, 135.0, 1, "Performance Review", True),
                ("Oct-25", 2025, 140.5, 1, "Performance Review", True),
                ("Nov-25", 2025, 145.2, 1, "Performance Review", True),
                ("Dec-25", 2025, 150.0, 1, "Performance Review", True),
                ("Jan-26", 2026, 155.3, 1, "Performance Review", True),
                ("Feb-26", 2026, 160.8, 1, "Performance Review", True),
                ("Mar-26", 2026, 165.4, 1, "Performance Review", True),
            ],
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Patch the rejection threshold high to avoid unit mixing validation
        # (this test is about fallback logic, not data quality validation)
        with (
            patch("raglite.shared.clients.get_postgresql_connection") as mock_pg,
            patch(
                "raglite.forecasting.timeseries.sql_extraction_response.UNIT_MIXING_REJECTION_THRESHOLD",
                1000.0,
            ),
        ):
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="ebitda", min_points=8)

            # Verify result
            assert result.__class__.__name__ == "TimeSeriesData"
            assert result.metric_name == "ebitda"
            assert len(result.points) == 8

            # Verify 3 phases were attempted (3 execute calls)
            assert mock_cursor.execute.call_count == 3

            # Verify Phase 3 query searched entity column
            phase3_query = mock_cursor.execute.call_args_list[2][0][0]
            assert "entity" in phase3_query.lower()
            assert "metric IS NULL OR metric = 'None'" in phase3_query

    async def test_entity_fallback_not_triggered_when_metric_found(self) -> None:
        """Test that entity fallback is NOT triggered when metric column has data."""
        mock_cursor = MagicMock()
        # Phase 1 (exact match) succeeds - no need for Phase 2 or 3
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

            # Should only have 1 execute call (Phase 1 succeeded)
            assert mock_cursor.execute.call_count == 1
            assert len(result.points) == 8

    async def test_entity_fallback_disables_entity_filter(self) -> None:
        """Test that Phase 3 disables entity filter since entity contains metric name."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [],  # Phase 1 fails
            [],  # Phase 2 fails
            [  # Phase 3 succeeds
                ("Aug-25", 2025, 128.83, 1, "Performance Review", True),
                ("Sep-25", 2025, 135.0, 1, "Performance Review", True),
                ("Oct-25", 2025, 140.5, 1, "Performance Review", True),
                ("Nov-25", 2025, 145.2, 1, "Performance Review", True),
                ("Dec-25", 2025, 150.0, 1, "Performance Review", True),
                ("Jan-26", 2026, 155.3, 1, "Performance Review", True),
                ("Feb-26", 2026, 160.8, 1, "Performance Review", True),
                ("Mar-26", 2026, 165.4, 1, "Performance Review", True),
            ],
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Patch the rejection threshold high to avoid unit mixing validation
        # (this test is about entity filter logic, not data quality validation)
        with (
            patch("raglite.shared.clients.get_postgresql_connection") as mock_pg,
            patch(
                "raglite.forecasting.timeseries.sql_extraction_response.UNIT_MIXING_REJECTION_THRESHOLD",
                1000.0,
            ),
        ):
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="ebitda", min_points=8)

            # Verify Phase 3 query does NOT have GROUP entity filter
            # (because entity column contains the metric name in inverted data)
            phase3_query = mock_cursor.execute.call_args_list[2][0][0]

            # Phase 3 should NOT have "AND UPPER(entity) = 'GROUP'" filter
            # The entity filter is disabled for Phase 3
            # Check that the query pattern uses LOWER(entity) LIKE (the metric search)
            assert "LOWER(entity) LIKE" in phase3_query

            # Result should still be valid
            assert len(result.points) == 8


class TestPeriodMatchClause:
    """Test _get_period_match_clause SQL generation for YTD and monthly formats."""

    def test_ytd_mode_accepts_both_formats(self) -> None:
        """Test that prefer_ytd=True matches BOTH YTD and monthly formats.

        Fix for: December 2025 data stored as 'Dec-25' (monthly format) was not
        being extracted because query only accepted 'YTD Dec-25' format.
        """
        from raglite.forecasting.timeseries.sql_extraction_query import (
            _get_period_match_clause,
        )

        period_match, period_extract, is_ytd_flag = _get_period_match_clause(prefer_ytd=True)

        # Should match YTD format
        assert "YTD\\s+[A-Z][a-z]{2}-[0-9]{2}" in period_match

        # Should ALSO match plain monthly format (the fix)
        assert "^[A-Z][a-z]{2}-[0-9]{2}$" in period_match
        assert " OR " in period_match  # Both patterns joined with OR

        # Should exclude budget periods
        assert "B" in period_match

        # Period extraction should work for both formats
        assert "REGEXP_MATCH" in period_extract
        assert "[A-Z][a-z]{2}-[0-9]{2}" in period_extract

        # is_ytd should be dynamic (CASE expression)
        assert "CASE" in is_ytd_flag
        assert "WHEN period ~ '^YTD'" in is_ytd_flag
        assert "TRUE" in is_ytd_flag
        assert "ELSE FALSE" in is_ytd_flag

    def test_monthly_mode_only_matches_monthly_format(self) -> None:
        """Test that prefer_ytd=False only matches plain monthly format."""
        from raglite.forecasting.timeseries.sql_extraction_query import (
            _get_period_match_clause,
        )

        period_match, period_extract, is_ytd_flag = _get_period_match_clause(prefer_ytd=False)

        # Should match only monthly format
        assert "^[A-Z][a-z]{2}-[0-9]{2}$" in period_match

        # Should NOT match YTD format
        assert "YTD" not in period_match
        assert "OR" not in period_match

        # Period extraction is direct (no regex needed)
        assert period_extract == "period"

        # is_ytd is always FALSE for monthly mode
        assert is_ytd_flag == "FALSE"

    def test_ytd_mode_dynamic_is_ytd_flag_sql_syntax(self) -> None:
        """Test that the dynamic is_ytd flag generates valid SQL CASE syntax."""
        from raglite.forecasting.timeseries.sql_extraction_query import (
            _get_period_match_clause,
        )

        _, _, is_ytd_flag = _get_period_match_clause(prefer_ytd=True)

        # Verify complete CASE expression structure
        expected = "CASE WHEN period ~ '^YTD' THEN TRUE ELSE FALSE END"
        assert is_ytd_flag == expected


@pytest.mark.asyncio
class TestMonthlyFormatFallback:
    """Test that monthly format data is extracted when YTD data is not available."""

    async def test_mixed_ytd_and_monthly_data_extraction(self) -> None:
        """Test extraction of both YTD and monthly format periods.

        Simulates the real scenario where:
        - Jan-Sep 2025: Available as 'YTD Sep-25' (YTD format)
        - Oct-Dec 2025: Available as 'Oct-25', 'Dec-25' (monthly format)

        Note: Missing Nov-25 is interpolated by the normalization layer.
        """
        mock_cursor = MagicMock()
        # Simulate mixed YTD and monthly data
        # Note: is_ytd_data column (index 5) now reflects actual format
        mock_cursor.fetchall.return_value = [
            ("Jan-25", 2025, 100.0, 1, "2025-01 Performance Review", True),  # YTD
            ("Feb-25", 2025, 105.0, 1, "2025-02 Performance Review", True),  # YTD
            ("Mar-25", 2025, 110.0, 1, "2025-03 Performance Review", True),  # YTD
            ("Apr-25", 2025, 115.0, 1, "2025-04 Performance Review", True),  # YTD
            ("May-25", 2025, 120.0, 1, "2025-05 Performance Review", True),  # YTD
            ("Jun-25", 2025, 125.0, 1, "2025-06 Performance Review", True),  # YTD
            ("Jul-25", 2025, 130.0, 1, "2025-07 Performance Review", True),  # YTD
            ("Aug-25", 2025, 135.0, 1, "2025-08 Performance Review", True),  # YTD
            ("Sep-25", 2025, 140.0, 1, "2025-09 Performance Review", True),  # YTD
            ("Oct-25", 2025, 172.28, 1, "2025-10 Performance Review", False),  # Monthly
            ("Dec-25", 2025, 203.16, 1, "2025-12 Performance Review", False),  # Monthly
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="ebitda", min_points=8)

            # Should have 12 data points (9 YTD + 2 monthly + 1 interpolated Nov)
            # The normalization layer interpolates missing months
            assert len(result.points) == 12

            # Verify October and December 2025 are included (the fix)
            months = [p.date.month for p in result.points]
            assert 10 in months, "October 2025 monthly data should be extracted"
            assert 11 in months, "November 2025 should be interpolated"
            assert 12 in months, "December 2025 monthly data should be extracted"

    async def test_december_2025_data_now_extracted(self) -> None:
        """Test the specific bug fix: December 2025 data is now extracted.

        Root cause: December 2025 Performance Review stores EBITDA as 'Dec-25'
        (monthly format), but the query only accepted 'YTD Dec-25' format.

        Note: Oct-Nov 2025 are missing in this test data, so they get interpolated.
        """
        mock_cursor = MagicMock()
        # Simulate the exact scenario from production
        mock_cursor.fetchall.return_value = [
            ("Jan-25", 2025, 100.0, 1, "Jan 2025 Performance Review", True),
            ("Feb-25", 2025, 105.0, 1, "Feb 2025 Performance Review", True),
            ("Mar-25", 2025, 110.0, 1, "Mar 2025 Performance Review", True),
            ("Apr-25", 2025, 115.0, 1, "Apr 2025 Performance Review", True),
            ("May-25", 2025, 120.0, 1, "May 2025 Performance Review", True),
            ("Jun-25", 2025, 125.0, 1, "Jun 2025 Performance Review", True),
            ("Jul-25", 2025, 130.0, 1, "Jul 2025 Performance Review", True),
            ("Aug-25", 2025, 135.0, 1, "Aug 2025 Performance Review", True),
            ("Sep-25", 2025, 140.0, 1, "Sep 2025 Performance Review", True),
            # This is the critical data point - December 2025 in monthly format
            ("Dec-25", 2025, 203.16, 1, "December 2025 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="ebitda", min_points=8)

            # Should have 12 data points (10 from SQL + 2 interpolated for Oct/Nov)
            # The normalization layer interpolates missing months
            assert len(result.points) == 12

            # Verify the last point is December 2025 (the critical fix)
            last_point = result.points[-1]
            assert last_point.date.month == 12
            assert last_point.date.year == 2025

            # Verify December 2025 data was extracted (the key assertion)
            months = [p.date.month for p in result.points]
            assert 12 in months, "December 2025 monthly format data should be extracted"


@pytest.mark.asyncio
class TestUnitMixingValidation:
    """Test Phase 5 unit mixing validation (UnitMixingError).

    Phase 5 enhancement: Data with swing >50x is rejected to prevent
    forecasting with data that has severe unit mixing (e.g., kEUR vs M EUR).
    Phase 3 Quality Fix (2026-01-29): Threshold increased from 20x to 50x
    to accommodate legitimate EBITDA volatility in cyclical industries.
    """

    async def test_unit_mixing_error_raised_for_extreme_swing(self) -> None:
        """Test that UnitMixingError is raised when value swing exceeds 50x.

        Phase 5 change: validate_unit_consistency() now rejects data with
        swing >50x (non-EBITDA) instead of just warning, preventing forecasts
        with severely mixed units.
        """
        from datetime import datetime

        from raglite.forecasting.timeseries.sql_extraction_response import (
            validate_unit_consistency,
        )
        from raglite.shared.models import TimeSeriesPoint

        # Create data with extreme swing (60x) - should be rejected
        # Threshold is 50x for non-EBITDA metrics
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=10.0),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=15.0),
            TimeSeriesPoint(date=datetime(2024, 3, 1), value=600.0),  # 60x the min
        ]

        # Should raise UnitMixingError
        with pytest.raises(UnitMixingError) as exc_info:
            validate_unit_consistency(points, "test_metric")

        assert exc_info.value.swing_ratio == pytest.approx(60.0)
        assert exc_info.value.metric == "test_metric"
        assert "fix_ebitda_scale_v2.py" in str(exc_info.value)

    async def test_unit_mixing_warning_for_moderate_swing(self) -> None:
        """Test that warning is returned (not error) for moderate swing 10x-50x."""
        from datetime import datetime

        from raglite.forecasting.timeseries.sql_extraction_response import (
            validate_unit_consistency,
        )
        from raglite.shared.models import TimeSeriesPoint

        # Create data with moderate swing (15x) - should warn but not reject
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=10.0),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=15.0),
            TimeSeriesPoint(date=datetime(2024, 3, 1), value=150.0),  # 15x the min
        ]

        # Should return warnings but not raise error
        issues = validate_unit_consistency(points, "test_metric")

        assert len(issues) == 1
        assert "Unit mixing suspected" in issues[0]
        assert "15.0x" in issues[0]

    async def test_unit_mixing_no_warning_for_normal_swing(self) -> None:
        """Test that no warning for normal swing <10x."""
        from datetime import datetime

        from raglite.forecasting.timeseries.sql_extraction_response import (
            validate_unit_consistency,
        )
        from raglite.shared.models import TimeSeriesPoint

        # Create data with normal swing (5x) - no warning
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=150.0),
            TimeSeriesPoint(date=datetime(2024, 3, 1), value=500.0),  # 5x the min
        ]

        # Should return empty issues
        issues = validate_unit_consistency(points, "test_metric")
        assert len(issues) == 0

    async def test_unit_mixing_can_be_disabled(self) -> None:
        """Test that rejection can be disabled with reject_on_severe=False."""
        from datetime import datetime

        from raglite.forecasting.timeseries.sql_extraction_response import (
            validate_unit_consistency,
        )
        from raglite.shared.models import TimeSeriesPoint

        # Create data with extreme swing (30x)
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=10.0),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=15.0),
            TimeSeriesPoint(date=datetime(2024, 3, 1), value=300.0),  # 30x the min
        ]

        # With reject_on_severe=False, should warn but not raise
        issues = validate_unit_consistency(points, "test_metric", reject_on_severe=False)

        assert len(issues) == 1
        assert "Unit mixing suspected" in issues[0]
