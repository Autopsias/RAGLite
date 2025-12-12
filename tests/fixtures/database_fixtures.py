"""Database test fixtures for integration testing.

Provides fixtures to populate the test database with proper time-series data
for forecasting and extraction tests.
"""

from pathlib import Path

import pytest

from raglite.shared.clients import get_postgresql_connection
from raglite.shared.safety import SafetyGuard


@pytest.fixture(scope="session")
def test_financial_data():
    """Populate test database with proper financial time-series data.

    This fixture loads test data that matches the expected format for
    revenue/turnover, EBITDA, expenses, and cash flow forecasting tests.

    The data is loaded once per session and cleaned up after all tests.

    Yields:
        None: Fixture provides side-effect of populating database
    """
    from raglite.shared.logging import get_logger

    logger = get_logger(__name__)

    # Verify we're using TEST environment
    guard = SafetyGuard()
    guard.validate_test_environment("test_financial_data fixture")

    # Path to test data SQL file
    sql_file = Path(__file__).parent / "test_financial_data.sql"

    if not sql_file.exists():
        raise FileNotFoundError(f"Test data file not found: {sql_file}")

    # Load test data into PostgreSQL
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # Read and execute SQL
        with open(sql_file) as f:
            sql_content = f.read()

        logger.info("Loading test financial data into database", extra={"sql_file": str(sql_file)})

        # Remove SQL comments and split into statements
        # Remove line comments starting with --
        lines = [line for line in sql_content.split("\n") if not line.strip().startswith("--")]
        # Remove block comments (/* ... */) and split by semicolon
        cleaned_sql = "\n".join(lines)
        statements = [stmt.strip() for stmt in cleaned_sql.split(";") if stmt.strip()]

        for statement in statements:
            if statement and not statement.startswith("#"):
                cursor.execute(statement)
        conn.commit()

        # Verify data was loaded
        cursor.execute(
            "SELECT COUNT(*) FROM financial_tables WHERE metric LIKE 'test_%' OR metric IN ('turnover', 'EBITDA IFRS')"
        )
        test_rows = cursor.fetchone()[0]

        logger.info("Test financial data loaded successfully", extra={"test_rows": test_rows})

        yield

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass  # Ignore rollback errors

        logger.error("Failed to load test financial data", extra={"error": str(e)}, exc_info=True)
        raise
    finally:
        # Clean up test data after session
        try:
            cursor.execute("DELETE FROM financial_tables WHERE metric LIKE 'test_%'")
            conn.commit()
            logger.info("Test financial data cleaned up")
        except Exception as cleanup_error:
            logger.warning("Failed to clean up test data", extra={"error": str(cleanup_error)})
        finally:
            cursor.close()


@pytest.fixture(scope="function")
def ensure_test_data_exists():
    """Ensure test financial data exists for individual tests.

    This is a safety check for tests that rely on the test data
    being present. It's a lighter-weight alternative to the
    test_financial_data fixture when the data should already
    be loaded.

    Raises:
        pytest.skip.Exception: If test data is not found
    """
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # Check for test data
        cursor.execute(
            "SELECT COUNT(*) FROM financial_tables WHERE metric LIKE 'test_%' OR metric IN ('turnover', 'EBITDA IFRS')"
        )
        test_rows = cursor.fetchone()[0]

        if test_rows == 0:
            pytest.skip("Test financial data not loaded - use test_financial_data fixture")

        yield test_rows

    finally:
        cursor.close()
