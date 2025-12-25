"""Pytest hooks for test collection and execution customization.

This module contains pytest hooks for:
- Custom command line options (--run-slow, --skip-ingestion, --enforce-isolation-markers)
- Test collection modification (grouping, marker enforcement, priority sorting)
- xdist worker configuration

These hooks are loaded by pytest via pytest_plugins in the root conftest.py.
"""

import logging

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item

logger = logging.getLogger(__name__)


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

    Args:
        config: pytest configuration object
    """
    # Store flags globally so tests can access them
    pytest.run_slow = config.getoption("--run-slow")  # type: ignore[attr-defined]
    pytest.skip_ingestion = config.getoption("--skip-ingestion")  # type: ignore[attr-defined]

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

    # Add xdist_group marker to all integration tests
    # Do this in a separate loop to avoid collection modification issues
    for item in integration_items:
        # Force embedding_model group (single worker for all integration tests)
        # This will override any existing xdist_group marker automatically
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
