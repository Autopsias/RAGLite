"""Pytest hooks for test collection and execution customization.

This module contains pytest hooks for:
- Custom command line options (--run-slow, --skip-ingestion, --enforce-isolation-markers)
- Test collection modification (grouping, marker enforcement, priority sorting)
- xdist worker configuration
- Docker/Colima auto-startup (ensures infrastructure is available before tests)

These hooks are loaded by pytest via pytest_plugins in the root conftest.py.
"""

import logging
import os
import shutil
import subprocess

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item

logger = logging.getLogger(__name__)


def _ensure_docker_running() -> bool:
    """Ensure Docker daemon is running, starting Colima if needed.

    This function is called early in pytest_configure to ensure Docker is available
    before any tests or fixtures that need containers are executed.

    Strategic recommendation (2026-01-11): Prevents recurring test failures due to
    Colima/Docker not running after system reboot, sleep, or crash.

    Returns:
        True if Docker is now available, False if startup failed
    """
    # Skip in CI - containers are managed by CI workflow
    if os.environ.get("CI") == "true":
        logger.debug("Skipping Docker startup check in CI (managed by workflow)")
        return True

    # Check if Docker is already available (fast path)
    docker_path = shutil.which("docker")
    if not docker_path:
        logger.warning("Docker CLI not found - skipping Docker check")
        return False

    # Pass DOCKER_HOST to docker info command (for CI Colima profiles)
    env = os.environ.copy()

    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        if result.returncode == 0:
            logger.debug("Docker daemon is already running")
            return True
    except (subprocess.TimeoutExpired, Exception):
        pass

    # Docker not available - try to start via ensure-docker-running.sh
    logger.info("Docker daemon not running - attempting auto-start...")

    # Find the script relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    script_path = os.path.join(project_root, "scripts", "ensure-docker-running.sh")

    if os.path.exists(script_path):
        try:
            logger.info(f"Running {script_path}...")
            result = subprocess.run(
                ["bash", script_path],
                capture_output=True,
                text=True,
                timeout=120,  # Colima startup can take up to 60s
                env=os.environ.copy(),  # Pass DOCKER_HOST for CI profiles
            )
            if result.returncode == 0:
                logger.info("Docker daemon started successfully via ensure-docker-running.sh")
                return True
            else:
                logger.warning(f"ensure-docker-running.sh failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.warning("ensure-docker-running.sh timed out after 120s")
        except Exception as e:
            logger.warning(f"Error running ensure-docker-running.sh: {e}")
    else:
        # Fallback: Try direct Colima start if script not found
        colima_path = shutil.which("colima")
        if colima_path:
            try:
                logger.info("Attempting to start Colima directly...")
                result = subprocess.run(
                    ["colima", "start"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    logger.info("Colima started successfully")
                    return True
            except Exception as e:
                logger.warning(f"Failed to start Colima: {e}")

    logger.warning(
        "Could not start Docker/Colima. Integration tests may fail. "
        "Run 'colima start' or './scripts/ensure-docker-running.sh' manually."
    )
    return False


def pytest_addoption(parser: Parser) -> None:
    """Add custom command line options for pytest.

    This allows us to control slow test execution, ingestion behavior, and test isolation
    enforcement via CLI flags.

    Args:
        parser: pytest argument parser
    """
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests (data-dependent tests requiring full 160-page PDF)",
    )
    parser.addoption(
        "--skip-ingestion",
        action="store_true",
        default=False,
        help="Skip session fixture ingestion and use existing Qdrant/PostgreSQL data (saves ~25 min)",
    )
    parser.addoption(
        "--enforce-isolation-markers",
        action="store_true",
        default=False,
        help="Enforce @pytest.mark.preserve_collection or @pytest.mark.manages_collection_state "
        "on all integration tests (prevents expensive cleanup regressions)",
    )


def pytest_configure(config: Config) -> None:
    """Configure pytest for optimal parallel execution and custom options.

    This hook is called once per worker process in pytest-xdist.
    Makes the run_slow and skip_ingestion options available to all tests.

    Strategic update (2026-01-11): Now also ensures Docker/Colima is running
    before test collection begins. This prevents the recurring issue where
    Colima stops between sessions and integration tests fail.

    Args:
        config: pytest configuration object
    """
    # Store flags globally so tests can access them
    pytest.run_slow = config.getoption("--run-slow")  # type: ignore[attr-defined]
    pytest.skip_ingestion = config.getoption("--skip-ingestion")  # type: ignore[attr-defined]

    # Ensure Docker is running (only on main worker, not xdist workers)
    # Check for xdist worker - if workerinput exists, we're a worker
    if not hasattr(config, "workerinput"):
        # We're the main process (or running without xdist)
        # Check if unit tests only - skip Docker check for pure unit tests
        # This is determined by looking at the test paths
        args = config.args or []
        is_unit_only = all("tests/unit" in str(arg) for arg in args) if args else False

        if not is_unit_only:
            # Not unit-only, so we may need Docker for integration tests
            _ensure_docker_running()

    # Only set workerinput if we're actually in xdist mode
    # DO NOT create empty workerinput - it confuses pytest-cov!
    # pytest-xdist will create workerinput if running with -n flag


def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:
    """Modify test collection to optimize execution order and prevent race conditions.

    1. Groups all integration tests to run in the same xdist worker (prevents Qdrant race conditions)
    2. Reorders tests to run fast tests first for quicker feedback

    CRITICAL FIX (2025-12-18): Fixed pytest internal errors by avoiding direct keyword/marker manipulation.
    Use a safer approach that doesn't modify pytest internal data structures directly.

    Args:
        config: pytest configuration object
        items: list of collected test items
    """

    # Force ALL integration tests into the EXISTING "embedding_model" xdist worker group
    # CRITICAL (2025-11-21): MUST force override ALL xdist groups to "embedding_model"
    # - pytest-xdist creates separate PROCESS per xdist group
    # - Session-scoped fixtures run ONCE PER PROCESS (not once globally)
    # - Split groups = duplicate session fixture runs = 2x slowdown (50s × N workers)
    # - Database tests previously used xdist_group(name="database") creating 2nd worker
    # - Result: Session fixture ran TWICE (1600s total vs 600s expected)
    enforce_markers = config.getoption("--enforce-isolation-markers", default=False)

    # Create new lists for processed items to avoid modifying during iteration
    integration_items = []
    other_items = []

    for item in items:
        if "integration" in str(item.fspath):
            integration_items.append(item)
        else:
            other_items.append(item)

    # Process integration tests separately
    for item in integration_items:
        # PERFORMANCE FIX (2025-12-06): Apply default preserve_collection marker
        # Integration tests that don't explicitly have a marker get preserve_collection
        # by default, eliminating unnecessary cleanup checks (42+ seconds overhead).
        #
        # Tests that modify data should explicitly use @pytest.mark.manages_collection_state
        # to override this default.
        has_preserve = item.get_closest_marker("preserve_collection")
        has_manages = item.get_closest_marker("manages_collection_state")

        if not (has_preserve or has_manages):
            # DEFAULT: Apply preserve_collection marker for read-only tests
            # This prevents expensive cleanup after each test (100ms × 425 tests = 42s)
            item.add_marker(pytest.mark.preserve_collection)

            # In strict CI mode, still require explicit markers
            if enforce_markers:
                raise ValueError(
                    f"{item.nodeid}: Integration test missing isolation marker. "
                    "Add @pytest.mark.preserve_collection (read-only) or "
                    "@pytest.mark.manages_collection_state (modifies data)."
                )

    # Add xdist_group marker ONLY to integration tests that don't already have one
    # Do this in a separate loop to avoid collection modification issues
    for item in integration_items:
        # Check if item already has an xdist_group marker (from pytestmark)
        existing_xdist_marker = item.get_closest_marker("xdist_group")

        if not existing_xdist_marker:
            # Force embedding_model group (single worker for all integration tests)
            # Only add if not already present to avoid pytest-xdist scheduler conflicts
            item.add_marker(pytest.mark.xdist_group(name="embedding_model"))

    # Sort tests: unit tests first, then integration, then e2e/slow
    def test_priority(item: Item) -> int:
        """Calculate test priority (lower = run first).

        Args:
            item: pytest test item

        Returns:
            Priority value (lower = run first)
        """
        if "unit" in item.keywords:
            return 0
        elif "integration" in item.keywords:
            return 1
        elif "slow" in item.keywords or "e2e" in item.keywords:
            return 2
        else:
            return 1  # Default: medium priority

    # Sort the original items list (not our separated lists)
    items.sort(key=test_priority)
