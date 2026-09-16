"""PostgreSQL database schema fixture.

Ensures test database schema exists before integration tests run.
"""

import pytest

from .service_checking import check_and_skip_if_unavailable


@pytest.fixture(scope="session", autouse=True)
def ensure_test_database_schema(request):
    """Ensure PostgreSQL schema exists before tests (Story 4.0.5)."""
    if request.config.option.collectonly:
        yield
        return

    # PERFORMANCE FIX: Skip for unit-only test runs
    from .test_detection import has_integration_tests

    if not has_integration_tests(request):
        yield
        return

    import logging

    logger = logging.getLogger(__name__)
    check_and_skip_if_unavailable()
    logger.info("🔧 Ensuring test database schema exists...")

    try:
        from raglite.shared.clients import get_postgresql_connection

        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'financial_chunks');"
        )
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            logger.warning("⚠️  Test database schema not found - initializing")
            import subprocess

            result = subprocess.run(
                ["uv", "run", "python", "scripts/init-test-postgresql.py"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                pytest.fail(f"Failed to initialize test database schema:\n{result.stderr}")
            logger.info("✅ Test database schema initialized")
        else:
            logger.info("✅ Test database schema already exists")
        cursor.close()
    except Exception as e:
        pytest.fail(f"Failed to verify/initialize test database schema: {e}")
    yield
