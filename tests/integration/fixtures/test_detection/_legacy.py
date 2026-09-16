"""Test detection helpers for conditional fixture loading.

Provides utilities to detect if integration tests are being run, allowing
expensive fixtures (embedding model, PDF ingestion) to skip for unit-only runs.
"""

from ._priority_checks import (
    check_command_line_args,
    check_pytest_config,
    check_session_items_ratio,
    check_vs_code_patterns,
    check_xdist_worker_node,
)


def is_postgresql_only_tests(request) -> bool:
    """Check if only postgresql_only tests are being collected.

    PostgreSQL-only tests (Story 7b-4) don't need Qdrant or embedding model.

    Args:
        request: pytest request fixture

    Returns:
        True if all tests have the postgresql_only marker
    """
    if hasattr(request, "session") and hasattr(request.session, "items"):
        for item in request.session.items:
            markers = [m.name for m in item.iter_markers()]
            # If any test doesn't have postgresql_only, we need full setup
            if "postgresql_only" not in markers:
                return False
        # All collected tests have postgresql_only marker
        return len(request.session.items) > 0
    return False


def has_integration_tests(request) -> bool:
    """Check if any integration tests are being collected.

    This allows expensive fixtures (embedding model, PDF ingestion) to skip
    when only unit tests are running, saving 60-70s+ startup time.

    PERFORMANCE FIX (2025-12-18): Without this check, autouse=True fixtures
    would load the 2GB Fin-E5 model even for unit tests.

    FIX (2025-12-20): Use multiple detection methods because pytest-xdist
    workers have different sys.argv than the controller. Workers are spawned
    as separate processes with gateway-specific arguments.

    Args:
        request: pytest request fixture

    Returns:
        True if any tests in tests/integration/ are being collected
    """
    # PRIORITY 1: Check pytest's invocation directory and collected args
    result = check_pytest_config(request)
    if result is not None:
        return result

    # PRIORITY 2: Check command-line arguments (works in controller process)
    result = check_command_line_args()
    if result is not None:
        return result

    # PRIORITY 3: Fall back to session items if available (single-process runs)
    result = check_session_items_ratio(request)
    if result is not None:
        return result

    # PRIORITY 4: In xdist workers, check current node's file path
    result = check_xdist_worker_node(request)
    if result is not None:
        return result

    # PRIORITY 5: Check for VS Code Test Explorer patterns
    result = check_vs_code_patterns(request)
    if result is not None:
        return result

    # PRIORITY 6: Safe default - DON'T assume integration tests (FIX: 2025-12-29)
    # Previously returned True, causing 60-70s fixture overhead on unit-only runs
    # VS Code Test Explorer often doesn't pass clear integration paths
    # Better to skip fixtures and let tests fail fast than load 2GB model unnecessarily
    return False
