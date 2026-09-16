"""Unit tests for year-value data corruption filter (Story 6.24.1).

Tests cover:
- AC1: Filter values in range 2000-2099 from Capacity Utilization
- AC2: Filter values in range 2000-2099 from Thermal Energy
- AC3: Log filtered values for audit trail
"""

from unittest.mock import MagicMock, patch

import pytest

from raglite.forecasting.timeseries import extract_timeseries_from_sql


class TestYearValueFilter:
    """Tests for year-value data corruption filter (Story 6.24.1)."""

    @pytest.mark.asyncio
    async def test_year_value_filtered_in_sql_extraction(self) -> None:
        """AC1/AC2: Year values (2000-2099) are filtered during SQL extraction."""
        # Mock SQL connection with year values in data
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            # Normal values
            ("Jan-23", 2023, 85.5, 1, "2023-01 Performance Review", False),
            ("Feb-23", 2023, 87.2, 1, "2023-02 Performance Review", False),
            # Year values that should be filtered
            ("Mar-23", 2023, 2021.0, 1, "2021-12 Performance Review", False),  # Year!
            ("Apr-23", 2023, 2022.0, 1, "2022-12 Performance Review", False),  # Year!
            ("May-23", 2023, 2023.0, 1, "2023-01 Performance Review", False),  # Year!
            # More normal values
            ("Jun-23", 2023, 88.9, 1, "2023-06 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="Frequency Ratio", min_points=3)

            # Should only have 3 valid data points (year values filtered)
            assert len(result.points) == 3
            values = [p.value for p in result.points]
            assert 85.5 in values
            assert 87.2 in values
            assert 88.9 in values
            # Year values should NOT be present
            assert 2021.0 not in values
            assert 2022.0 not in values
            assert 2023.0 not in values

    @pytest.mark.asyncio
    async def test_year_value_filtered_in_percentage_metrics(self) -> None:
        """AC1: Year values filtered in percentage metric validation."""
        # Mock SQL connection with year values
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-23", 2023, 75.0, 1, "2023-01 Review", False),
            ("Feb-23", 2023, 2024.0, 1, "2024-02 Review", False),  # Year value!
            ("Mar-23", 2023, 80.0, 1, "2023-03 Review", False),
            ("Apr-23", 2023, 2021.0, 1, "2021-12 Review", False),  # Year value!
            ("May-23", 2023, 85.0, 1, "2023-05 Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="capacity_utilization", min_points=3)

            # Should only have 3 valid data points
            assert len(result.points) == 3
            values = [p.value for p in result.points]
            # Valid percentage values should be present
            assert 75.0 in values
            assert 80.0 in values
            assert 85.0 in values
            # Year values should be filtered
            assert 2024.0 not in values
            assert 2021.0 not in values

    @pytest.mark.asyncio
    async def test_year_boundary_values_filtered(self) -> None:
        """AC1/AC2: Boundary year values (2000, 2099) are filtered."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-23", 2023, 2000.0, 1, "2000-01 Review", False),  # Boundary year
            ("Feb-23", 2023, 2099.0, 1, "2099-12 Review", False),  # Boundary year
            ("Mar-23", 2023, 1999.0, 1, "2023-03 Review", False),  # NOT filtered (valid data)
            ("Apr-23", 2023, 2100.0, 1, "2023-04 Review", False),  # NOT filtered (valid data)
            ("May-23", 2023, 50.0, 1, "2023-05 Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="Thermal Energy", min_points=3)

            # Should have 3 valid data points (2000 and 2099 filtered)
            assert len(result.points) == 3
            values = [p.value for p in result.points]
            # Year boundary values should be filtered
            assert 2000.0 not in values
            assert 2099.0 not in values
            # Non-year values should be present
            assert 1999.0 in values  # Just outside year range
            assert 2100.0 in values  # Just outside year range
            assert 50.0 in values

    @pytest.mark.asyncio
    async def test_percentage_metric_year_value_logging(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC3: Filtered year values are logged for audit trail."""
        import logging

        caplog.set_level(logging.WARNING)

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-23", 2023, 75.0, 1, "2023-01 Review", False),
            ("Feb-23", 2023, 2024.0, 1, "2024-02 Review", False),  # Year value
            ("Mar-23", 2023, 80.0, 1, "2023-03 Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            await extract_timeseries_from_sql(metric="Frequency Ratio", min_points=2)

            # Check that year value filtering was logged
            # The year filter logs warnings during SQL extraction
            warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
            assert len(warning_records) > 0, "Expected year-value filter warning logs"

            # Check for year-related warning messages
            log_messages = [record.message for record in warning_records]
            has_year_warning = any(
                "year" in msg.lower() or "filtered year" in msg.lower() for msg in log_messages
            )
            assert has_year_warning, f"Expected year-value filter warning. Got: {log_messages}"
