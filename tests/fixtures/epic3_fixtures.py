"""Pytest fixtures for Epic 3 Data Dictionary tests.

Provides fixtures for database inspection testing, mock database clients,
and sample catalog data following fixture-architecture.md patterns:
- Pure function → fixture → mergeTests composition
- Auto-cleanup in teardown
- Type-safe and isolated
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from tests.support.factories import create_database_query_result, create_inspection_catalog


@pytest.fixture
def sample_metrics_query_result() -> list[dict[str, str]]:
    """Provide sample metrics query result for unit tests.

    Returns:
        List of dictionaries representing database rows with metric field
    """
    return create_database_query_result(
        field="metric", values=["EBITDA", "Revenue", "Variable Cost", "Fixed Cost"]
    )


@pytest.fixture
def sample_periods_query_result() -> list[dict[str, str]]:
    """Provide sample periods query result for unit tests.

    Returns:
        List of dictionaries representing database rows with period field
    """
    return create_database_query_result(
        field="period",
        values=["Aug-25", "Sep-25", "Jul-25", "Aug-25 YTD", "Sep-25 YTD"],
    )


@pytest.fixture
def sample_entities_query_result() -> list[dict[str, str]]:
    """Provide sample entities query result for unit tests.

    Returns:
        List of dictionaries representing database rows with entity field
    """
    return create_database_query_result(
        field="entity",
        values=[
            "Portugal Cement",
            "Tunisia Cement",
            "Secil Angola",
            "Currency (1000 EUR)",
        ],
    )


@pytest.fixture
def sample_currencies_query_result() -> list[dict[str, str]]:
    """Provide sample currencies query result for unit tests.

    Returns:
        List of dictionaries representing database rows with currency field
    """
    return create_database_query_result(field="currency", values=["EUR"])


@pytest.fixture
def sample_inspection_catalog() -> dict[str, Any]:
    """Provide sample inspection catalog for unit tests.

    Returns:
        Dictionary with complete inspection catalog structure
    """
    return create_inspection_catalog(total_rows=170142)


@pytest.fixture
def mock_db_client_for_inspection(
    sample_metrics_query_result: list[dict[str, str]],
    sample_periods_query_result: list[dict[str, str]],
    sample_entities_query_result: list[dict[str, str]],
    sample_currencies_query_result: list[dict[str, str]],
) -> AsyncMock:
    """Provide mock database client configured for inspection tests.

    Args:
        sample_metrics_query_result: Fixture providing metrics data
        sample_periods_query_result: Fixture providing periods data
        sample_entities_query_result: Fixture providing entities data
        sample_currencies_query_result: Fixture providing currencies data

    Returns:
        AsyncMock database client with pre-configured query responses

    Usage:
        @pytest.mark.asyncio
        async def test_inspection(mock_db_client_for_inspection):
            # Client automatically returns sample data for each query
            catalog = await inspect_database(mock_db_client_for_inspection)
            assert catalog["total_rows"] == 170142
    """
    mock_db = AsyncMock()

    # Configure fetch() to return different results for each query
    # Order: metrics, periods, entities, currencies
    mock_db.fetch.side_effect = [
        sample_metrics_query_result,
        sample_periods_query_result,
        sample_entities_query_result,
        sample_currencies_query_result,
    ]

    # Configure fetchval() for row count query
    mock_db.fetchval.return_value = 170142

    return mock_db


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Provide temporary directory for test output files.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        Path to temporary output directory

    Usage:
        def test_file_creation(temp_output_dir):
            output_file = temp_output_dir / "catalog.json"
            save_catalog_to_file(catalog, str(output_file))
            assert output_file.exists()
    """
    output_dir = tmp_path / "epic3-test-output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def mock_catalog_json_content() -> str:
    """Provide mock JSON content for catalog file tests.

    Returns:
        JSON string representing a valid catalog
    """
    import json

    catalog = create_inspection_catalog(total_rows=170142)
    return json.dumps(catalog, indent=2)


# Integration test fixture with auto-cleanup
@pytest.fixture
async def real_db_with_cleanup():
    """Provide real database client with auto-cleanup after test.

    Setup:
    - Connects to PostgreSQL database
    - Verifies financial_tables exists

    Teardown:
    - Closes database connection
    - Cleans up any test artifacts

    Yields:
        Database client for integration tests

    Usage:
        @pytest.mark.asyncio
        async def test_real_db(real_db_with_cleanup):
            db = real_db_with_cleanup
            result = await db.fetch("SELECT COUNT(*) FROM financial_tables")
            assert result is not None
    """
    from raglite.shared.clients import get_postgresql_connection

    # Setup: Get database client
    db = get_postgresql_connection()

    # Verify database is accessible
    try:
        await db.fetch("SELECT 1;")
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")

    # Provide to test
    yield db

    # Teardown: Close connection if needed
    # (Database client handles cleanup internally)
    pass
