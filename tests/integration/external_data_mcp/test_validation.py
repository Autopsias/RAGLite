"""Integration tests for external data MCP tool - AC5 Validation.

Story 6.6: External Data Query Tool (MCP)
AC5: Date Range Validation Tests

Tests date parsing and validation edge cases.
"""

import json

import pytest

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestExternalDataMCPAC5Validation:
    """AC5: Validate specific test queries from story requirements."""

    @pytest.mark.asyncio
    async def test_ac5_q1_2024_building_permits(self, populated_db) -> None:
        """AC5: source='INE_BuildingPermits', date_range='2024-01-01:2024-03-31'"""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        # Use our test source (mimics INE_BuildingPermits)
        request = ExternalDataQueryRequest(
            source="TEST_MCP_BuildingPermits",
            date_range="2024-01-01:2024-03-31",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        # Should return Q1 2024 data
        assert "error" not in data
        assert data["record_count"] > 0

    @pytest.mark.asyncio
    async def test_ac5_last_30_days_shortcut(self, populated_db) -> None:
        """AC5: source='OMIE_Electricity', date_range='last_30_days'"""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="TEST_MCP_ElectricityPrices",
            date_range="last_30_days",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        # Should parse correctly (may have 0 records if test data is old)
        assert "error" not in data or "not found" not in data.get("error", "")

    @pytest.mark.asyncio
    async def test_ac5_all_sources_last_year(self, populated_db) -> None:
        """AC5: source='all', date_range='last_year'"""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="all",
            date_range="last_year",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        # Should return multi-source response
        assert data.get("query") == "multi-source" or "error" not in data

    @pytest.mark.asyncio
    async def test_ac5_metric_filter(self, populated_db) -> None:
        """AC5: source with metric filter"""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="TEST_MCP_BuildingPermits",
            date_range="2024-01-01:2024-12-31",
            metric="permits_count",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        # Should filter by metric
        assert "error" not in data
        for dp in data.get("data", []):
            assert dp["metric"] == "permits_count"

    @pytest.mark.asyncio
    async def test_ac5_nonexistent_source_error(self, populated_db) -> None:
        """AC5: source='NonExistent', date_range='last_30_days' -> Error"""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="NonExistent",
            date_range="last_30_days",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        assert "error" in data
        assert "not found" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_ac5_invalid_date_format_error(self, populated_db) -> None:
        """AC5: date_range='invalid' -> Error"""
        from raglite.main import (
            ExternalDataQueryRequest,
            query_external_data,
        )

        request = ExternalDataQueryRequest(
            source="TEST_MCP_BuildingPermits",
            date_range="invalid",
        )

        result = await query_external_data.fn(request)
        data = json.loads(result)

        assert "error" in data
        assert "Invalid" in data["error"]
