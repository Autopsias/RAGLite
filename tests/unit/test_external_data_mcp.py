"""Unit tests for external data MCP tool.

Story 6.6: External Data Query Tool (MCP)
AC6: Unit Tests (80%+ coverage)

Tests date range parsing, visualization hints, and query logic.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import Mock

import pytest


class TestDateRangeParsing:
    """Test date range parsing logic."""

    def test_parse_iso_format(self) -> None:
        """Test ISO date range parsing."""
        from raglite.mcp.tools.external_data import _parse_date_range

        start, end = _parse_date_range("2024-01-01:2024-12-31")
        assert start == date(2024, 1, 1)
        assert end == date(2024, 12, 31)

    def test_parse_iso_format_with_spaces(self) -> None:
        """Test ISO date range parsing with spaces around dates."""
        from raglite.mcp.tools.external_data import _parse_date_range

        start, end = _parse_date_range("2024-01-01 : 2024-12-31")
        assert start == date(2024, 1, 1)
        assert end == date(2024, 12, 31)

    def test_parse_last_30_days(self) -> None:
        """Test last_30_days shortcut."""
        from raglite.mcp.tools.external_data import _parse_date_range

        start, end = _parse_date_range("last_30_days")
        assert end == date.today()
        assert start == date.today() - timedelta(days=30)

    def test_parse_last_90_days(self) -> None:
        """Test last_90_days shortcut."""
        from raglite.mcp.tools.external_data import _parse_date_range

        start, end = _parse_date_range("last_90_days")
        assert end == date.today()
        assert start == date.today() - timedelta(days=90)

    def test_parse_last_year(self) -> None:
        """Test last_year shortcut."""
        from raglite.mcp.tools.external_data import _parse_date_range

        start, end = _parse_date_range("last_year")
        assert end == date.today()
        assert start == date.today() - timedelta(days=365)

    def test_parse_last_quarter(self) -> None:
        """Test last_quarter shortcut (90 days)."""
        from raglite.mcp.tools.external_data import _parse_date_range

        start, end = _parse_date_range("last_quarter")
        assert end == date.today()
        assert start == date.today() - timedelta(days=90)

    def test_parse_ytd(self) -> None:
        """Test year-to-date shortcut."""
        from raglite.mcp.tools.external_data import _parse_date_range

        start, end = _parse_date_range("ytd")
        assert start == date(date.today().year, 1, 1)
        assert end == date.today()

    def test_parse_shortcuts_case_insensitive(self) -> None:
        """Test shortcuts are case insensitive."""
        from raglite.mcp.tools.external_data import _parse_date_range

        start1, end1 = _parse_date_range("LAST_30_DAYS")
        start2, end2 = _parse_date_range("Last_30_Days")
        start3, end3 = _parse_date_range("last_30_days")

        assert start1 == start2 == start3
        assert end1 == end2 == end3

    def test_parse_invalid_format(self) -> None:
        """Test invalid format raises ValueError."""
        from raglite.mcp.tools.external_data import _parse_date_range

        with pytest.raises(ValueError, match="Invalid date_range"):
            _parse_date_range("invalid")

    def test_parse_invalid_shortcut(self) -> None:
        """Test unknown shortcut raises ValueError."""
        from raglite.mcp.tools.external_data import _parse_date_range

        with pytest.raises(ValueError, match="Invalid date_range"):
            _parse_date_range("last_week")

    def test_parse_invalid_iso_date(self) -> None:
        """Test invalid ISO date raises ValueError."""
        from raglite.mcp.tools.external_data import _parse_date_range

        with pytest.raises(ValueError, match="Invalid date format"):
            _parse_date_range("2024-13-01:2024-12-31")  # Invalid month

    def test_parse_invalid_iso_format_wrong_parts(self) -> None:
        """Test malformed ISO format raises ValueError."""
        from raglite.mcp.tools.external_data import _parse_date_range

        with pytest.raises(ValueError, match="Invalid date range format"):
            _parse_date_range("2024-01-01:2024-06-30:2024-12-31")  # Too many parts


class TestVisualizationHints:
    """Test visualization hint generation."""

    def test_empty_data(self) -> None:
        """Test hint for empty dataset."""
        from raglite.mcp.tools.external_data import _get_visualization_hint

        hint = _get_visualization_hint(0, "time_series")
        assert "No data" in hint

    def test_single_value(self) -> None:
        """Test hint for single data point."""
        from raglite.mcp.tools.external_data import _get_visualization_hint

        hint = _get_visualization_hint(1, "time_series")
        assert "card" in hint.lower() or "gauge" in hint.lower()

    def test_small_dataset(self) -> None:
        """Test hint for small dataset (<=12 records)."""
        from raglite.mcp.tools.external_data import _get_visualization_hint

        hint = _get_visualization_hint(10, "index")
        assert "bar" in hint.lower()

    def test_exactly_12_records(self) -> None:
        """Test hint for exactly 12 records (bar chart boundary)."""
        from raglite.mcp.tools.external_data import _get_visualization_hint

        hint = _get_visualization_hint(12, "index")
        assert "bar" in hint.lower()

    def test_time_series_large_dataset(self) -> None:
        """Test hint for time series data with many records."""
        from raglite.mcp.tools.external_data import _get_visualization_hint

        hint = _get_visualization_hint(100, "time_series")
        assert "line" in hint.lower()

    def test_large_non_timeseries(self) -> None:
        """Test hint for large non-time-series dataset."""
        from raglite.mcp.tools.external_data import _get_visualization_hint

        hint = _get_visualization_hint(50, "index")
        assert "line" in hint.lower() or "area" in hint.lower()


class TestQueryHelpers:
    """Test query helper functions."""

    @pytest.fixture
    def mock_storage(self) -> Mock:
        """Create mock ExternalDataStorage."""
        storage = Mock()
        storage.get_source.return_value = Mock(
            source_name="INE_BuildingPermits",
            refresh_frequency="monthly",
            last_refresh_at=datetime(2024, 6, 15, 10, 30),
            data_type="time_series",
        )
        storage.query_data_range.return_value = []
        storage.list_sources.return_value = []
        return storage

    def test_query_single_source_not_found(self, mock_storage: Mock) -> None:
        """Test error when source not found."""
        from raglite.mcp.tools.external_data import _query_single_source

        mock_storage.get_source.return_value = None

        with pytest.raises(ValueError, match="Source 'Unknown' not found"):
            _query_single_source(
                mock_storage,
                "Unknown",
                date(2024, 1, 1),
                date(2024, 12, 31),
                None,
            )

    def test_query_single_source_empty_results(self, mock_storage: Mock) -> None:
        """Test empty results handling."""
        from raglite.mcp.tools.external_data import _query_single_source

        mock_storage.query_data_range.return_value = []

        results = _query_single_source(
            mock_storage,
            "INE_BuildingPermits",
            date(2024, 1, 1),
            date(2024, 12, 31),
            None,
        )

        assert len(results) == 1
        assert results[0].record_count == 0
        assert results[0].data_points == []

    def test_query_single_source_with_data(self, mock_storage: Mock) -> None:
        """Test query with actual data points."""
        from raglite.mcp.tools.external_data import _query_single_source

        mock_data_point = Mock()
        mock_data_point.date = date(2024, 1, 1)
        mock_data_point.metric_name = "permits"
        mock_data_point.value = 1234.5
        mock_data_point.unit = "count"

        mock_storage.query_data_range.return_value = [mock_data_point]

        results = _query_single_source(
            mock_storage,
            "INE_BuildingPermits",
            date(2024, 1, 1),
            date(2024, 12, 31),
            None,
        )

        assert len(results) == 1
        assert results[0].record_count == 1
        assert len(results[0].data_points) == 1
        assert results[0].data_points[0].value == 1234.5

    def test_query_all_sources_empty(self, mock_storage: Mock) -> None:
        """Test querying all sources when none exist."""
        from raglite.mcp.tools.external_data import _query_all_sources

        mock_storage.list_sources.return_value = []

        results = _query_all_sources(
            mock_storage,
            date(2024, 1, 1),
            date(2024, 12, 31),
            None,
        )

        assert results == []

    def test_query_all_sources_aggregates_results(self, mock_storage: Mock) -> None:
        """Test querying all sources aggregates results."""
        from raglite.mcp.tools.external_data import _query_all_sources

        source1 = Mock(
            source_name="Source1",
            refresh_frequency="daily",
            last_refresh_at=None,
            data_type="time_series",
        )
        source2 = Mock(
            source_name="Source2",
            refresh_frequency="weekly",
            last_refresh_at=None,
            data_type="index",
        )

        mock_storage.list_sources.return_value = [source1, source2]
        mock_storage.get_source.side_effect = lambda name: source1 if name == "Source1" else source2
        mock_storage.query_data_range.return_value = []

        results = _query_all_sources(
            mock_storage,
            date(2024, 1, 1),
            date(2024, 12, 31),
            None,
        )

        assert len(results) == 2
        assert results[0].source_name == "Source1"
        assert results[1].source_name == "Source2"


class TestResponseFormatting:
    """Test response formatting logic."""

    def test_format_empty_results(self) -> None:
        """Test formatting with no results."""
        import json

        from raglite.mcp.tools.external_data import _format_response

        response = _format_response([], "NonExistent")
        data = json.loads(response)

        assert "No data found" in data.get("message", "")
        assert "available_sources" in data

    def test_format_single_source_response(self) -> None:
        """Test formatting single source response."""
        import json

        from raglite.mcp.models import ExternalDataPoint, ExternalDataQueryResponse
        from raglite.mcp.tools.external_data import _format_response

        result = ExternalDataQueryResponse(
            source_name="INE_BuildingPermits",
            data_frequency="monthly",
            last_refresh=datetime(2024, 6, 15, 10, 30),
            data_points=[
                ExternalDataPoint(
                    date=date(2024, 1, 1),
                    metric_name="permits",
                    value=100.0,
                    unit="count",
                )
            ],
            visualization_hint="Line chart recommended",
            record_count=1,
        )

        response = _format_response([result], "INE_BuildingPermits")
        data = json.loads(response)

        assert data["source"] == "INE_BuildingPermits"
        assert data["frequency"] == "monthly"
        assert data["record_count"] == 1
        assert len(data["data"]) == 1
        assert data["data"][0]["metric"] == "permits"

    def test_format_multi_source_response(self) -> None:
        """Test formatting multi-source response (for 'all' query)."""
        import json

        from raglite.mcp.models import ExternalDataPoint, ExternalDataQueryResponse
        from raglite.mcp.tools.external_data import _format_response

        results = [
            ExternalDataQueryResponse(
                source_name="Source1",
                data_frequency="daily",
                last_refresh=None,
                data_points=[
                    ExternalDataPoint(
                        date=date(2024, 1, 1),
                        metric_name="metric1",
                        value=10.0,
                        unit=None,
                    )
                ],
                visualization_hint="Line chart",
                record_count=1,
            ),
            ExternalDataQueryResponse(
                source_name="Source2",
                data_frequency="weekly",
                last_refresh=None,
                data_points=[],
                visualization_hint="No data",
                record_count=0,
            ),
        ]

        response = _format_response(results, "all")
        data = json.loads(response)

        assert data["query"] == "multi-source"
        assert data["sources_queried"] == 2
        assert data["total_records"] == 1
        assert len(data["results"]) == 2

    def test_format_truncates_large_multi_source(self) -> None:
        """Test that multi-source responses truncate data per source."""
        import json

        from raglite.mcp.models import ExternalDataPoint, ExternalDataQueryResponse
        from raglite.mcp.tools.external_data import _format_response

        # Create result with 15 data points
        data_points = [
            ExternalDataPoint(
                date=date(2024, 1, i + 1),
                metric_name="metric",
                value=float(i),
                unit=None,
            )
            for i in range(15)
        ]

        result = ExternalDataQueryResponse(
            source_name="Source1",
            data_frequency="daily",
            last_refresh=None,
            data_points=data_points,
            visualization_hint="Line chart",
            record_count=15,
        )

        # Need two results to trigger multi-source response
        response = _format_response([result, result], "all")
        data = json.loads(response)

        # Multi-source limits to 10 per source
        assert len(data["results"][0]["data"]) == 10
        assert data["results"][0]["truncated"] is True


class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_external_data_query_request_required_fields(self) -> None:
        """Test ExternalDataQueryRequest requires source and date_range."""
        from raglite.mcp.models import ExternalDataQueryRequest

        # Valid request
        request = ExternalDataQueryRequest(
            source="INE_BuildingPermits",
            date_range="last_30_days",
        )
        assert request.source == "INE_BuildingPermits"
        assert request.metric is None  # Optional field

    def test_external_data_query_request_with_metric(self) -> None:
        """Test ExternalDataQueryRequest with optional metric."""
        from raglite.mcp.models import ExternalDataQueryRequest

        request = ExternalDataQueryRequest(
            source="INE_BuildingPermits",
            date_range="2024-01-01:2024-12-31",
            metric="permits_count",
        )
        assert request.metric == "permits_count"

    def test_external_data_point_model(self) -> None:
        """Test ExternalDataPoint model."""
        from raglite.mcp.models import ExternalDataPoint

        point = ExternalDataPoint(
            date=date(2024, 1, 1),
            metric_name="permits",
            value=1234.5,
            unit="count",
        )
        assert point.date == date(2024, 1, 1)
        assert point.value == 1234.5

    def test_external_data_query_response_model(self) -> None:
        """Test ExternalDataQueryResponse model."""
        from raglite.mcp.models import ExternalDataQueryResponse

        response = ExternalDataQueryResponse(
            source_name="INE_BuildingPermits",
            data_frequency="monthly",
            last_refresh=datetime(2024, 6, 15),
            data_points=[],
            visualization_hint="No data",
            record_count=0,
        )
        assert response.source_name == "INE_BuildingPermits"
        assert response.record_count == 0
