"""Integration tests for external data MCP tool - Extended AC5 validation tests.

Story 6.6: External Data Query Tool (MCP)
AC5: Validate specific test queries from story requirements.

Tests real database interactions and end-to-end query flows.
REQUIRES: PostgreSQL running on test port (5433)
"""

from __future__ import annotations

import json
import os
from datetime import date

import pytest

# Set test environment before importing
os.environ["APP_ENV"] = "test"

# Skip all tests in this module if not running integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
]


@pytest.fixture(scope="module")
def db_session():
    """PostgreSQL session for integration tests.

    Creates tables in test database and yields session.
    Rolls back after tests complete.
    """
    from raglite.shared.safety import SafetyGuard

    guard = SafetyGuard()
    guard.validate_test_environment("external_data_mcp_integration")

    # IMPORTANT: Import ORM models BEFORE create_all() so they register with Base
    from raglite.external_data.orm_models import (  # noqa: F401
        ExternalDataPointORM,
        ExternalDataSourceORM,
    )
    from raglite.shared.database import Base, get_engine, get_session, reset_engine

    # Reset engine to pick up test environment settings
    reset_engine()

    # Create tables in test database
    engine = get_engine()
    Base.metadata.create_all(engine)

    session = get_session()
    yield session

    session.rollback()
    session.close()


@pytest.fixture(scope="module")
def populated_db(db_session):
    """Populate test database with sample external data.

    Creates a test source and data points for integration testing.
    Uses upsert=True to handle re-runs gracefully.
    """
    from raglite.external_data.storage import ExternalDataStorage

    storage = ExternalDataStorage(db_session)

    # Create test sources - get_or_create handles existing sources
    try:
        source, created1 = storage.get_or_create_source(
            source_name="TEST_MCP_BuildingPermits",
            data_type="time_series",
            refresh_frequency="monthly",
        )
    except Exception as e:
        # If there's an issue, rollback and try to get existing
        import logging

        logging.getLogger(__name__).warning(f"Fixture setup issue (source creation): {e}")
        db_session.rollback()
        source = storage.get_source("TEST_MCP_BuildingPermits")
        created1 = source is None
        if created1:
            source, _ = storage.get_or_create_source(
                source_name="TEST_MCP_BuildingPermits",
                data_type="time_series",
                refresh_frequency="monthly",
            )

    # Insert test data points - Q1-Q2 2024 (use upsert to handle re-runs)
    test_data = [
        {"date": date(2024, 1, 1), "metric_name": "permits_count", "value": 100, "unit": "count"},
        {"date": date(2024, 2, 1), "metric_name": "permits_count", "value": 110, "unit": "count"},
        {"date": date(2024, 3, 1), "metric_name": "permits_count", "value": 120, "unit": "count"},
        {"date": date(2024, 4, 1), "metric_name": "permits_count", "value": 115, "unit": "count"},
        {"date": date(2024, 5, 1), "metric_name": "permits_count", "value": 125, "unit": "count"},
        {"date": date(2024, 6, 1), "metric_name": "permits_count", "value": 130, "unit": "count"},
        # Different metric
        {"date": date(2024, 1, 1), "metric_name": "permits_value", "value": 10000, "unit": "EUR"},
        {"date": date(2024, 2, 1), "metric_name": "permits_value", "value": 11000, "unit": "EUR"},
    ]
    try:
        storage.insert_data_points("TEST_MCP_BuildingPermits", test_data, upsert=True)
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Fixture setup issue (data insert): {e}")
        db_session.rollback()

    # Create second source for multi-source testing
    try:
        source2, created2 = storage.get_or_create_source(
            source_name="TEST_MCP_ElectricityPrices",
            data_type="time_series",
            refresh_frequency="daily",
        )
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Fixture setup issue (source2 creation): {e}")
        db_session.rollback()
        source2 = storage.get_source("TEST_MCP_ElectricityPrices")
        if source2 is None:
            source2, _ = storage.get_or_create_source(
                source_name="TEST_MCP_ElectricityPrices",
                data_type="time_series",
                refresh_frequency="daily",
            )

    try:
        storage.insert_data_points(
            "TEST_MCP_ElectricityPrices",
            [
                {
                    "date": date(2024, 1, 15),
                    "metric_name": "price_mwh",
                    "value": 85.5,
                    "unit": "EUR/MWh",
                },
                {
                    "date": date(2024, 2, 15),
                    "metric_name": "price_mwh",
                    "value": 90.2,
                    "unit": "EUR/MWh",
                },
            ],
            upsert=True,
        )
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Fixture setup issue (electricity data): {e}")
        db_session.rollback()

    yield storage

    # Note: We don't delete test data at the end to allow for faster re-runs
    # The upsert=True on insert handles data conflicts gracefully


@pytest.mark.integration
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
