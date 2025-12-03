"""Unit tests for metric discovery functionality.

Story 5.0.4 AC1: Tests for list_available_metrics() and MetricInfo model.

Note: Period column is VARCHAR, not datetime (Story 5.0.4 fix).
Mock data uses period strings like "Jan-23", "Dec-25".
"""

from unittest.mock import MagicMock, patch

import pytest

from raglite.forecasting.metrics import (
    MetricInfo,
    clear_metrics_cache,
    list_available_metrics,
)

# Test database marker (Story 4.0.7: three-mode database system)
pytestmark = pytest.mark.unit


class TestMetricInfo:
    """Test MetricInfo Pydantic model."""

    def test_metric_info_creation(self):
        """Test MetricInfo model can be created with valid data."""
        # Note: period column is VARCHAR, not datetime (Story 5.0.4 fix)
        metric = MetricInfo(
            name="revenue",
            data_point_count=12,
            min_period="Jan-23",
            max_period="Dec-25",
            can_forecast=True,
        )

        assert metric.name == "revenue"
        assert metric.data_point_count == 12
        assert metric.can_forecast is True

    def test_metric_info_optional_periods(self):
        """Test MetricInfo works with None periods (empty database case)."""
        metric = MetricInfo(
            name="capex", data_point_count=3, min_period=None, max_period=None, can_forecast=False
        )

        assert metric.name == "capex"
        assert metric.min_period is None
        assert metric.max_period is None
        assert metric.can_forecast is False

    def test_metric_info_insufficient_data_flag(self):
        """Test can_forecast flag correctly represents data availability."""
        # Sufficient data (8+ points)
        metric_ok = MetricInfo(
            name="ebitda",
            data_point_count=8,
            min_period="Jan-23",
            max_period="Jan-25",
            can_forecast=True,
        )

        # Insufficient data (<8 points)
        metric_low = MetricInfo(
            name="margins",
            data_point_count=3,
            min_period="Jan-25",
            max_period="Mar-25",
            can_forecast=False,
        )

        assert metric_ok.can_forecast is True
        assert metric_low.can_forecast is False


class TestListAvailableMetrics:
    """Test list_available_metrics() function."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear metrics cache before each test."""
        clear_metrics_cache()
        yield
        clear_metrics_cache()

    @pytest.mark.asyncio
    async def test_list_metrics_returns_sorted_list(self):
        """Test metrics returned sorted by data_point_count desc (AC1)."""
        # Mock PostgreSQL connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("revenue", 12, "Jan-23", "Dec-25"),
            ("expenses", 10, "Jan-23", "Oct-25"),
            ("ebitda", 8, "Jan-23", "Aug-25"),
            ("capex", 3, "Jan-25", "Mar-25"),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.forecasting.metrics.get_postgresql_connection", return_value=mock_conn):
            metrics = await list_available_metrics(use_cache=False)

        # Verify sorted by data_point_count desc
        assert len(metrics) == 4
        assert metrics[0].name == "revenue"
        assert metrics[0].data_point_count == 12
        assert metrics[1].name == "expenses"
        assert metrics[1].data_point_count == 10
        assert metrics[2].name == "ebitda"
        assert metrics[2].data_point_count == 8
        assert metrics[3].name == "capex"
        assert metrics[3].data_point_count == 3

    @pytest.mark.asyncio
    async def test_list_metrics_can_forecast_flag(self):
        """Test can_forecast flag set correctly based on min_points (AC1)."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("revenue", 12, "Jan-23", "Dec-25"),
            ("ebitda", 8, "Jan-23", "Aug-25"),  # exactly 8
            ("capex", 7, "Jan-23", "Jul-25"),  # just below
            ("margins", 3, "Jan-25", "Mar-25"),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.forecasting.metrics.get_postgresql_connection", return_value=mock_conn):
            metrics = await list_available_metrics(min_points=8, use_cache=False)

        # Verify can_forecast flag
        assert metrics[0].can_forecast is True  # 12 >= 8
        assert metrics[1].can_forecast is True  # 8 >= 8 (boundary)
        assert metrics[2].can_forecast is False  # 7 < 8
        assert metrics[3].can_forecast is False  # 3 < 8

    @pytest.mark.asyncio
    async def test_list_metrics_empty_database(self):
        """Test empty database returns empty list gracefully (AC1.3)."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # Empty database

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.forecasting.metrics.get_postgresql_connection", return_value=mock_conn):
            metrics = await list_available_metrics(use_cache=False)

        assert metrics == []
        assert len(metrics) == 0

    @pytest.mark.asyncio
    async def test_list_metrics_caching_behavior(self):
        """Test metric list caching (5-minute TTL) (AC1.2)."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("revenue", 12, "Jan-23", "Dec-25"),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.forecasting.metrics.get_postgresql_connection", return_value=mock_conn):
            # First call - hits database
            metrics1 = await list_available_metrics(use_cache=True)
            assert len(metrics1) == 1

            # Second call - should use cache (no DB query)
            mock_cursor.fetchall.return_value = []  # Change DB response
            metrics2 = await list_available_metrics(use_cache=True)

            # Should still return cached result (not empty)
            assert len(metrics2) == 1
            assert metrics2[0].name == "revenue"

    @pytest.mark.asyncio
    async def test_list_metrics_cache_bypass(self):
        """Test cache can be bypassed with use_cache=False (AC1.2)."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("revenue", 12, "Jan-23", "Dec-25"),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.forecasting.metrics.get_postgresql_connection", return_value=mock_conn):
            # First call
            metrics1 = await list_available_metrics(use_cache=True)
            assert len(metrics1) == 1

            # Change DB response
            mock_cursor.fetchall.return_value = [
                ("ebitda", 10, "Jan-23", "Oct-25"),
            ]

            # Second call with cache bypass
            metrics2 = await list_available_metrics(use_cache=False)

            # Should fetch fresh data
            assert len(metrics2) == 1
            assert metrics2[0].name == "ebitda"  # New data, not cached "revenue"

    @pytest.mark.asyncio
    async def test_clear_metrics_cache(self):
        """Test cache clearing functionality (AC1.2)."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("revenue", 12, "Jan-23", "Dec-25"),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.forecasting.metrics.get_postgresql_connection", return_value=mock_conn):
            # Populate cache
            metrics1 = await list_available_metrics(use_cache=True)
            assert len(metrics1) == 1

            # Clear cache
            clear_metrics_cache()

            # Change DB response
            mock_cursor.fetchall.return_value = [
                ("expenses", 8, "Jan-23", "Aug-25"),
            ]

            # Next call should hit database (not cache)
            metrics2 = await list_available_metrics(use_cache=True)
            assert len(metrics2) == 1
            assert metrics2[0].name == "expenses"  # Fresh data

    @pytest.mark.asyncio
    async def test_list_metrics_sql_error_handling(self):
        """Test SQL query failure raises RuntimeError (AC1)."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database connection lost")

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.forecasting.metrics.get_postgresql_connection", return_value=mock_conn):
            with pytest.raises(RuntimeError, match="Metric discovery query failed"):
                await list_available_metrics(use_cache=False)

    @pytest.mark.asyncio
    async def test_list_metrics_custom_min_points(self):
        """Test custom min_points threshold (AC1)."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("revenue", 12, "Jan-23", "Dec-25"),
            ("ebitda", 6, "Jan-23", "Jun-25"),
            ("capex", 4, "Jan-25", "Apr-25"),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.forecasting.metrics.get_postgresql_connection", return_value=mock_conn):
            # Use lower threshold for testing
            metrics = await list_available_metrics(min_points=5, use_cache=False)

        # Verify can_forecast with custom threshold
        assert metrics[0].can_forecast is True  # 12 >= 5
        assert metrics[1].can_forecast is True  # 6 >= 5
        assert metrics[2].can_forecast is False  # 4 < 5
