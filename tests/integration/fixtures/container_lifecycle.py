"""Container lifecycle management for integration tests.

Strategic recommendation from test-strategy-analyst (2025-12-24):
Provides auto-restart capability for test containers to prevent infrastructure failures.

This module ensures test containers (PostgreSQL, Qdrant) are running before tests execute.
If containers are stopped, it attempts to restart them automatically.

Functions:
    ensure_container_running: Check and optionally restart a Docker container
    ensure_test_infrastructure: Session fixture to guarantee all test containers are up
    initialize_test_database_schema: Ensure database schema is complete after restart
"""

import logging
import os
import shutil
import socket
import subprocess
import time
from typing import Literal

import pytest

logger = logging.getLogger(__name__)

# Container names for test infrastructure
POSTGRES_TEST_CONTAINER = "raglite-postgresql-test"
QDRANT_TEST_CONTAINER = "raglite-qdrant-test"

# Test ports (Story 4.0.5 database separation)
POSTGRES_TEST_PORT = 5433
QDRANT_TEST_PORT = 6335


def _is_docker_available() -> bool:
    """Check if Docker CLI is available."""
    return shutil.which("docker") is not None


def _get_container_status(container_name: str) -> Literal["running", "exited", "not_found"]:
    """Get the status of a Docker container.

    Args:
        container_name: Name of the container to check

    Returns:
        "running" if container is up, "exited" if stopped, "not_found" if doesn't exist
    """
    if not _is_docker_available():
        return "not_found"

    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            status = result.stdout.strip()
            if status == "running":
                return "running"
            return "exited"
        return "not_found"
    except (subprocess.TimeoutExpired, Exception):
        return "not_found"


def _start_container(container_name: str) -> bool:
    """Attempt to start a stopped Docker container.

    Args:
        container_name: Name of the container to start

    Returns:
        True if container started successfully, False otherwise
    """
    if not _is_docker_available():
        return False

    try:
        logger.info(f"Attempting to start container: {container_name}")
        result = subprocess.run(
            ["docker", "start", container_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info(f"Container {container_name} started successfully")
            return True
        logger.warning(f"Failed to start container {container_name}: {result.stderr}")
        return False
    except (subprocess.TimeoutExpired, Exception) as e:
        logger.warning(f"Error starting container {container_name}: {e}")
        return False


def _wait_for_port(host: str, port: int, timeout: int = 30) -> bool:
    """Wait for a port to become available.

    Args:
        host: Host to connect to
        port: Port number to check
        timeout: Maximum seconds to wait

    Returns:
        True if port is available within timeout, False otherwise
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def ensure_container_running(
    container_name: str,
    port: int,
    service_name: str,
    auto_restart: bool = True,
) -> tuple[bool, str]:
    """Ensure a test container is running, with optional auto-restart.

    Strategic recommendation: Instead of just checking and skipping, this function
    attempts to restart stopped containers to reduce test infrastructure failures.

    Args:
        container_name: Docker container name
        port: Expected port for health check
        service_name: Human-readable service name for logging
        auto_restart: Whether to attempt restart if container is stopped

    Returns:
        Tuple of (is_available, status_message)
    """
    # First check if port is already available (fast path)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        if sock.connect_ex(("localhost", port)) == 0:
            sock.close()
            return True, f"{service_name} is available on port {port}"
        sock.close()
    except Exception:
        pass

    # Port not available - check container status
    status = _get_container_status(container_name)

    if status == "running":
        # Container running but port not responding - wait a bit
        if _wait_for_port("localhost", port, timeout=10):
            return True, f"{service_name} became available after waiting"
        return False, f"{service_name} container running but port {port} not responding"

    if status == "exited" and auto_restart:
        # Container stopped - try to restart
        if _start_container(container_name):
            # Wait for port to become available
            if _wait_for_port("localhost", port, timeout=30):
                return True, f"{service_name} restarted successfully"
            return False, f"{service_name} restarted but port {port} not responding"
        return False, f"Failed to restart {service_name} container"

    if status == "not_found":
        return False, f"{service_name} container {container_name} not found"

    return False, f"{service_name} container is stopped (auto_restart={auto_restart})"


def initialize_test_database_schema() -> None:
    """Initialize database schema after container restart.

    This ensures all ORM tables exist after a PostgreSQL container restart.
    The container may have ephemeral storage that loses tables on restart.
    """
    try:
        # Import here to avoid circular imports
        from sqlalchemy import create_engine

        from raglite.external_data.orm_models import Base as ORMBase

        # Build connection URL for test database
        db_url = f"postgresql://raglite_ci:raglite_ci@localhost:{POSTGRES_TEST_PORT}/raglite_ci"
        engine = create_engine(db_url)

        # Create all tables
        ORMBase.metadata.create_all(engine)
        logger.info("Test database schema initialized (ORM tables created)")

    except Exception as e:
        logger.warning(f"Could not initialize test database schema: {e}")


@pytest.fixture(scope="session", autouse=False)
def ensure_test_infrastructure():
    """Session fixture to ensure test containers are running.

    Strategic recommendation from test-strategy-analyst:
    This fixture should be used by integration tests to guarantee infrastructure
    is available. It attempts auto-restart before skipping tests.

    Usage:
        @pytest.mark.usefixtures("ensure_test_infrastructure")
        class TestSomething:
            ...

    Or add to conftest.py for automatic application:
        pytestmark = [pytest.mark.usefixtures("ensure_test_infrastructure")]
    """
    # Skip if running unit tests only
    if os.environ.get("UNIT_TESTS_ONLY"):
        yield
        return

    issues = []
    services_restarted = []

    # Check PostgreSQL
    pg_available, pg_message = ensure_container_running(
        POSTGRES_TEST_CONTAINER,
        POSTGRES_TEST_PORT,
        "PostgreSQL",
        auto_restart=True,
    )
    if not pg_available:
        issues.append(pg_message)
    elif "restarted" in pg_message:
        services_restarted.append("PostgreSQL")

    # Check Qdrant
    qd_available, qd_message = ensure_container_running(
        QDRANT_TEST_CONTAINER,
        QDRANT_TEST_PORT,
        "Qdrant",
        auto_restart=True,
    )
    if not qd_available:
        issues.append(qd_message)
    elif "restarted" in qd_message:
        services_restarted.append("Qdrant")

    # If PostgreSQL was restarted, initialize schema
    if "PostgreSQL" in services_restarted:
        logger.info("PostgreSQL was restarted - initializing schema...")
        initialize_test_database_schema()

    # Report status
    if services_restarted:
        logger.info(f"Auto-restarted services: {', '.join(services_restarted)}")

    if issues:
        skip_message = f"Test infrastructure unavailable: {'; '.join(issues)}"
        logger.warning(skip_message)
        pytest.skip(skip_message, allow_module_level=True)

    yield

    # No cleanup needed - containers persist for next test run


# Convenience function for manual checks
def check_test_infrastructure() -> dict:
    """Check status of all test infrastructure components.

    Returns:
        Dictionary with status of each component
    """
    return {
        "postgresql": {
            "container": POSTGRES_TEST_CONTAINER,
            "port": POSTGRES_TEST_PORT,
            "status": _get_container_status(POSTGRES_TEST_CONTAINER),
            "port_open": _wait_for_port("localhost", POSTGRES_TEST_PORT, timeout=2),
        },
        "qdrant": {
            "container": QDRANT_TEST_CONTAINER,
            "port": QDRANT_TEST_PORT,
            "status": _get_container_status(QDRANT_TEST_CONTAINER),
            "port_open": _wait_for_port("localhost", QDRANT_TEST_PORT, timeout=2),
        },
    }
