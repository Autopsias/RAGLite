"""Integration tests for external data MCP tool.

Story 6.6: External Data Query Tool (MCP)
AC7: Integration Tests

Tests real database interactions and end-to-end query flows.
REQUIRES: PostgreSQL running on test port (5433)
"""

from __future__ import annotations

import os
from datetime import date

import pytest

# Set test environment before importing
os.environ["APP_ENV"] = "test"

# Import shared fixtures from parent conftest
from tests.conftest import db_session

# Skip all tests in this module if not running integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.integration,
    pytest.mark.preserve_collection,
]


@pytest.fixture(scope="module")
def mcp_db_session():
    """PostgreSQL session for MCP integration tests.

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
def populated_db(mcp_db_session):
    """Populate test database with sample external data.

    Creates a test source and data points for integration testing.
    Uses upsert=True to handle re-runs gracefully.
    """
    from raglite.external_data.storage import ExternalDataStorage

    storage = ExternalDataStorage(mcp_db_session)

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
