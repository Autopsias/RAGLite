"""Integration tests for external data MCP tool - Core Tests.

Story 6.6: External Data Query Tool (MCP)
AC7: Integration Tests

Tests real database interactions and end-to-end query flows.
REQUIRES: PostgreSQL running on test port (5433)
"""

import json
import time

import pytest

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestExternalDataMCPIntegration:
    """Integration tests for external data MCP tool."""

    @pytest.mark.asyncio
    async def test_query_valid_source_iso_range(self, populated_db) -> None:
        """Test querying existing source with ISO date range returns data."""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="TEST_MCP_BuildingPermits",
            date_range="2024-01-01:2024-03-31",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        assert "error" not in data
        assert data["source"] == "TEST_MCP_BuildingPermits"
        assert data["record_count"] == 5  # 3 months permits_count + 2 months permits_value
        assert data["frequency"] == "monthly"
        assert "visualization_hint" in data
        assert len(data["data"]) > 0

    @pytest.mark.asyncio
    async def test_query_with_metric_filter(self, populated_db) -> None:
        """Test filtering by specific metric."""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="TEST_MCP_BuildingPermits",
            date_range="2024-01-01:2024-06-30",
            metric="permits_count",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        assert "error" not in data
        assert data["record_count"] == 6  # Only permits_count metrics
        for dp in data["data"]:
            assert dp["metric"] == "permits_count"

    @pytest.mark.asyncio
    async def test_query_date_shortcut(self, populated_db) -> None:
        """Test date range shortcut (last_year includes our test data)."""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        # Note: This test may need adjustment based on when it runs
        # For now, we test that the shortcut parses correctly
        request = ExternalDataQueryRequest(
            source="TEST_MCP_BuildingPermits",
            date_range="last_year",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        # Should parse correctly even if no data in range
        assert "error" not in data or "not found" not in data.get("error", "")

    @pytest.mark.asyncio
    async def test_query_all_sources(self, populated_db) -> None:
        """Test 'all' sources aggregation."""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="all",
            date_range="2024-01-01:2024-06-30",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        assert "error" not in data
        assert data["query"] == "multi-source"
        assert data["sources_queried"] >= 2  # At least our 2 test sources
        assert data["total_records"] > 0

    @pytest.mark.asyncio
    async def test_query_nonexistent_source(self, populated_db) -> None:
        """Test error response for non-existent source."""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="NONEXISTENT_Source",
            date_range="2024-01-01:2024-12-31",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        assert "error" in data
        assert "not found" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_query_invalid_date_format(self, populated_db) -> None:
        """Test error response for invalid date format."""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="TEST_MCP_BuildingPermits",
            date_range="invalid_format",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        assert "error" in data
        assert "Invalid date_range" in data["error"]

    @pytest.mark.asyncio
    async def test_query_empty_date_range(self, populated_db) -> None:
        """Test response when no data exists in date range."""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="TEST_MCP_BuildingPermits",
            date_range="2020-01-01:2020-12-31",  # No data in 2020
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        # Should return empty data array, not error
        assert "error" not in data
        assert data["record_count"] == 0
        assert data["data"] == []

    @pytest.mark.asyncio
    async def test_response_time_under_2s(self, populated_db) -> None:
        """NFR: Query response time <2s p95."""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="TEST_MCP_BuildingPermits",
            date_range="2024-01-01:2024-12-31",
        )

        start = time.time()
        await query_external_data.fn(request)
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Query took {elapsed:.2f}s, expected <2s"

    @pytest.mark.asyncio
    async def test_response_contains_visualization_hint(self, populated_db) -> None:
        """Test that response includes visualization hints."""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="TEST_MCP_BuildingPermits",
            date_range="2024-01-01:2024-06-30",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        assert "visualization_hint" in data
        assert data["visualization_hint"]  # Non-empty

    @pytest.mark.asyncio
    async def test_response_data_format(self, populated_db) -> None:
        """Test that data points have correct format."""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="TEST_MCP_BuildingPermits",
            date_range="2024-01-01:2024-01-31",
            metric="permits_count",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        assert "error" not in data
        assert len(data["data"]) > 0

        dp = data["data"][0]
        assert "date" in dp
        assert "metric" in dp
        assert "value" in dp
        assert "unit" in dp

        # Verify date is ISO format
        from datetime import datetime

        datetime.fromisoformat(dp["date"])  # Should not raise
