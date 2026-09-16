"""Test detection helpers for conditional fixture loading.

This module provides helper functions to detect which type of tests are being run,
allowing expensive fixtures (embedding model, PDF ingestion) to skip for unit-only
test runs. This saves 60-150s of startup time.
"""

import os
import sys


def _is_postgresql_only_tests(request) -> bool:
    """Check if only postgresql_only tests are being collected.

    PostgreSQL-only tests (Story 7b-4) don't need Qdrant or embedding model.

    CI OPTIMIZATION (2026-01-17): The PostgreSQL shard in CI runs tests from
    forecasting/, model_selection/, external_data/, and insights/ directories.
    These tests don't need the 2GB embedding model, saving:
    - 60s model load time
    - 2GB RAM per worker
    - Enables 4x parallelization (workers: 4 vs workers: 1)

    Detection methods (in priority order):
    1. CI_SHARD=postgresql environment variable (CI shards)
    2. Directory path detection for PostgreSQL-focused directories
    3. @pytest.mark.postgresql_only marker (explicit marking)

    Args:
        request: pytest request fixture

    Returns:
        True if tests don't need the embedding model
    """
    # PRIORITY 1: CI shard environment variable (set by CI workflow)
    # This is the most reliable check for CI environments
    # Skip embedding for shards that don't need it: postgresql-db, postgresql-ml, mcp
    # FIX (2026-01-25): Use startswith for postgresql-* shards after shard split
    ci_shard = os.environ.get("CI_SHARD")
    if ci_shard and (ci_shard.startswith("postgresql") or ci_shard == "mcp"):
        print(
            f"\n⚡ CI SHARD DETECTED: CI_SHARD={ci_shard} - skipping embedding model",
            file=sys.stderr,
        )
        return True

    # PRIORITY 2: Directory-based detection for PostgreSQL-focused test directories
    # These directories contain tests that use PostgreSQL but NOT the embedding model
    postgresql_only_dirs = {"forecasting", "model_selection", "external_data", "insights"}

    if hasattr(request, "session") and hasattr(request.session, "items"):
        items = request.session.items
        if not items:
            return False

        # Check if ALL test paths are in PostgreSQL-only directories
        all_postgresql_only = True
        for item in items:
            path_str = str(item.fspath)
            # Check if path contains any of the postgresql-only directories
            if not any(
                f"/{d}/" in path_str or path_str.endswith(f"/{d}") for d in postgresql_only_dirs
            ):
                all_postgresql_only = False
                break

        if all_postgresql_only:
            print(
                f"\n⚡ DIRECTORY DETECTION: All {len(items)} tests in PostgreSQL-only directories",
                file=sys.stderr,
            )
            return True

    # PRIORITY 3: Marker-based detection (explicit @pytest.mark.postgresql_only)
    if hasattr(request, "session") and hasattr(request.session, "items"):
        for item in request.session.items:
            markers = [m.name for m in item.iter_markers()]
            # If any test doesn't have postgresql_only, we need full setup
            if "postgresql_only" not in markers:
                return False
        # All collected tests have postgresql_only marker
        return len(request.session.items) > 0
    return False


def _needs_collection_ingestion(request) -> bool:
    """Check if tests need Qdrant collection with ingested documents.

    This function separates the concern of collection ingestion from embedding
    model loading. Some CI shards (like MCP) need the Qdrant collection but
    can skip embedding model loading (using pre-computed embeddings or mocks).

    CI Shards behavior:
    - postgresql: No Qdrant needed (forecasting, model_selection tests)
    - mcp: Qdrant NEEDED but embedding model skipped
    - retrieval: Qdrant NEEDED with fresh embeddings

    FIX (2026-01-20): Previously, _is_postgresql_only_tests() was used for both
    embedding skip AND collection skip. This caused MCP shard tests to fail with
    404 errors because the collection was never created.

    Args:
        request: pytest request fixture

    Returns:
        True if tests need Qdrant collection with ingested documents
    """
    ci_shard = os.environ.get("CI_SHARD")

    # PostgreSQL shards (db, ml) don't need Qdrant at all
    # FIX (2026-01-25): Use startswith for postgresql-* shards after shard split
    if ci_shard and ci_shard.startswith("postgresql"):
        print(
            f"\n⚡ CI_SHARD={ci_shard} - no Qdrant collection needed",
            file=sys.stderr,
        )
        return False

    # MCP and retrieval shards NEED collection
    if ci_shard in ("mcp", "retrieval"):
        print(
            f"\n⚡ CI_SHARD={ci_shard} - Qdrant collection REQUIRED",
            file=sys.stderr,
        )
        return True

    # Default: use existing integration test detection
    return _has_integration_tests(request)


def _check_pytest_args_for_integration(request) -> bool | None:
    """Check pytest's invocation directory and collected args.

    Args:
        request: pytest request fixture

    Returns:
        True if integration tests detected, False if unit-only, None if inconclusive
    """
    if not hasattr(request, "config"):
        return None

    # Check the args passed to pytest (available in all processes)
    args = getattr(request.config, "args", [])
    for arg in args:
        # FIX (2025-12-21): Exclude UAT tests - they mock everything and don't need Qdrant
        if ("tests/unit" in str(arg) or "tests/uat" in str(arg)) and "integration" not in str(arg):
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

    return None


def _check_sys_argv_for_integration() -> bool | None:
    """Check command-line arguments (works in controller process).

    Returns:
        True if integration tests detected, False if unit-only, None if inconclusive
    """
    for arg in sys.argv:
        # Running only unit or UAT tests - skip integration fixtures
        # FIX (2025-12-21): UAT tests mock external services, don't need Qdrant
        if ("tests/unit" in arg or "tests/uat" in arg) and "integration" not in arg:
            return False
        # Explicitly running integration tests
        if "tests/integration" in arg:
            return True

    return None


def _check_session_items_for_integration(request) -> bool | None:
    """Check collected test items (single-process runs).

    FIX (2025-12-29): Use THRESHOLD-based detection instead of ANY integration test.
    Previously returned True if ANY integration test existed, triggering expensive
    fixtures (embedding model: 60-70s, PDF ingestion: 60-150s) for FULL suite runs.

    New logic: Only load integration fixtures if:
    - Integration tests are >30% of total tests, OR
    - Total tests are few (<50) and any are integration (likely targeted run)

    Args:
        request: pytest request fixture

    Returns:
        True if integration tests detected, False if unit-only, None if inconclusive
    """
    if not (hasattr(request, "session") and hasattr(request.session, "items")):
        return None

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
    return False


def _check_xdist_worker_for_integration(request) -> bool | None:
    """In xdist workers, check current node's file path.

    Args:
        request: pytest request fixture

    Returns:
        True if integration test detected, None otherwise
    """
    if hasattr(request, "node") and hasattr(request.node, "fspath"):
        return "integration" in str(request.node.fspath)
    return None


def _check_vs_code_discovery(request) -> bool | None:
    """Check for VS Code Test Explorer patterns.

    VS Code passes different arguments than CLI pytest.

    Args:
        request: pytest request fixture

    Returns:
        False if VS Code discovery detected, None otherwise
    """
    if not hasattr(request, "config"):
        return None

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

    return None


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
    result = _check_pytest_args_for_integration(request)
    if result is not None:
        return result

    # PRIORITY 2: Check command-line arguments (works in controller process)
    result = _check_sys_argv_for_integration()
    if result is not None:
        return result

    # PRIORITY 3: Fall back to session items if available (single-process runs)
    result = _check_session_items_for_integration(request)
    if result is not None:
        return result

    # PRIORITY 4: In xdist workers, check current node's file path
    result = _check_xdist_worker_for_integration(request)
    if result is not None:
        return result

    # PRIORITY 5: Check for VS Code Test Explorer patterns
    result = _check_vs_code_discovery(request)
    if result is not None:
        return result

    # PRIORITY 6: Safe default - DON'T assume integration tests (FIX: 2025-12-29)
    # Previously returned True, causing 60-70s fixture overhead on unit-only runs
    # VS Code Test Explorer often doesn't pass clear integration paths
    # Better to skip fixtures and let tests fail fast than load 2GB model unnecessarily
    return False
