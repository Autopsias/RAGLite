"""Test detection helpers for conditional fixture loading.

This module provides helper functions to detect which type of tests are being run,
allowing expensive fixtures (embedding model, PDF ingestion) to skip for unit-only
test runs. This saves 60-150s of startup time.
"""

import sys


def _is_postgresql_only_tests(request) -> bool:
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


def _has_integration_tests(request) -> bool:
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
    # This works in both controller and xdist worker processes
    if hasattr(request, "config"):
        # Check the args passed to pytest (available in all processes)
        args = getattr(request.config, "args", [])
        for arg in args:
            # FIX (2025-12-21): Exclude UAT tests - they mock everything and don't need Qdrant
            if ("tests/unit" in str(arg) or "tests/uat" in str(arg)) and "integration" not in str(
                arg
            ):
                return False
            if "tests/integration" in str(arg):
                return True

        # Check inipath for test root detection
        inipath = getattr(request.config, "inipath", None)
        if inipath:
            str(inipath.parent) if hasattr(inipath, "parent") else str(inipath)
            # Check known_args_namespace for file args
            known_args = getattr(request.config, "known_args_namespace", None)
            if known_args and hasattr(known_args, "file_or_dir"):
                for path in known_args.file_or_dir or []:
                    # FIX (2025-12-21): Exclude UAT tests - they mock everything
                    if (
                        "tests/unit" in str(path) or "tests/uat" in str(path)
                    ) and "integration" not in str(path):
                        return False
                    if "tests/integration" in str(path):
                        return True

    # PRIORITY 2: Check command-line arguments (works in controller process)
    for arg in sys.argv:
        # Running only unit or UAT tests - skip integration fixtures
        # FIX (2025-12-21): UAT tests mock external services, don't need Qdrant
        if ("tests/unit" in arg or "tests/uat" in arg) and "integration" not in arg:
            return False
        # Explicitly running integration tests
        if "tests/integration" in arg:
            return True

    # PRIORITY 3: Fall back to session items if available (single-process runs)
    # FIX (2025-12-29): Use THRESHOLD-based detection instead of ANY integration test
    # Previously returned True if ANY integration test existed, triggering expensive
    # fixtures (embedding model: 60-70s, PDF ingestion: 60-150s) for FULL suite runs.
    # This caused 1465s runtime when VS Code Test Explorer ran all tests.
    #
    # New logic: Only load integration fixtures if:
    # - Integration tests are >30% of total tests, OR
    # - Total tests are few (<50) and any are integration (likely targeted run)
    if hasattr(request, "session") and hasattr(request.session, "items"):
        total_tests = len(request.session.items)
        integration_count = sum(
            1 for item in request.session.items if "integration" in str(item.fspath)
        )

        if total_tests == 0:
            return False

        # If running a small targeted set, any integration test triggers fixtures
        if total_tests < 50 and integration_count > 0:
            return True

        # For large test runs (full suite), only load fixtures if primarily integration
        integration_ratio = integration_count / total_tests
        if integration_ratio > 0.30:  # >30% integration tests
            return True

        # Full suite with mostly unit tests - skip expensive fixtures
        # Unit tests will pass, integration tests will skip with clear message
        return False

    # PRIORITY 4: In xdist workers, check current node's file path
    if hasattr(request, "node") and hasattr(request.node, "fspath"):
        return "integration" in str(request.node.fspath)

    # PRIORITY 5: Check for VS Code Test Explorer patterns
    # VS Code passes different arguments than CLI pytest
    if hasattr(request, "config"):
        # VS Code Test Explorer uses --rootdir and specific test paths
        invocation_dir = getattr(request.config, "invocation_dir", None)
        if invocation_dir:
            # If invocation is from project root without explicit path, VS Code is discovering
            pass  # Fall through to default

        # Check if we're in pytest discovery mode (VS Code Test Explorer)
        # During discovery, we don't want to load heavy fixtures
        workerinput = getattr(request.config, "workerinput", None)
        if workerinput is None:
            # Not in xdist worker - check if this looks like VS Code discovery
            # VS Code often runs with just "tests" as the path
            args = getattr(request.config, "args", [])
            if args and len(args) == 1 and args[0] == "tests":
                # Generic "tests" directory - could be VS Code, default to safe (no fixtures)
                return False

    # PRIORITY 6: Safe default - DON'T assume integration tests (FIX: 2025-12-29)
    # Previously returned True, causing 60-70s fixture overhead on unit-only runs
    # VS Code Test Explorer often doesn't pass clear integration paths
    # Better to skip fixtures and let tests fail fast than load 2GB model unnecessarily
    return False
