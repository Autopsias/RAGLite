"""Integration test fixtures for E2E and regression testing.

PRODUCTION-PROVEN PATTERN: Session-scoped fixture with read-only data sharing.

This module implements pytest best practices from production codebases (Django, FastAPI, pandas, Mozilla):
- Session scope ingests PDFs once (75-85 seconds)
- All read-only tests share the ingested collection (zero setup per test)
- Tests that need fresh data use @pytest.mark.manages_collection_state
- Reduces test suite from 40+ min to ~90 seconds

References:
- Django: Uses session-scoped database with transaction rollback per test
- FastAPI: Session-scoped DB schema, function-scoped transactions
- Mozilla Firefox: Session-scoped browser, JS state reset per test (80% speedup)
- pandas: Module-scoped DataFrame factories for grouped tests

IMPORTANT: Integration tests use shared Qdrant collection (read-only mode).
Tests that modify data are marked with @pytest.mark.manages_collection_state.
"""

import os
import sys

import pytest

# Debug: Track module load
print("DEBUG: conftest.py loading...", file=sys.stderr)

# CRITICAL FIX (2025-11-23): Set test environment variables BEFORE any raglite imports
# This ensures the Settings singleton uses test database settings when it's created.
# Root cause: tests/conftest.py sets env vars, but tests/integration/conftest.py is loaded
# BEFORE parent conftest completes, so Settings singleton was created with production defaults.
# Solution: Set env vars in BOTH conftest files to ensure they're available at import time.
if "APP_ENV" not in os.environ:
    os.environ["APP_ENV"] = "test"
if "TESTING" not in os.environ:
    os.environ["TESTING"] = "true"
if "POSTGRES_PORT" not in os.environ:
    os.environ["POSTGRES_PORT"] = "5433"
if "POSTGRES_DB" not in os.environ:
    os.environ["POSTGRES_DB"] = "raglite_ci"
if "POSTGRES_USER" not in os.environ:
    os.environ["POSTGRES_USER"] = "raglite_ci"
if "POSTGRES_PASSWORD" not in os.environ:
    os.environ["POSTGRES_PASSWORD"] = "raglite_ci"

print("DEBUG: Test environment variables set before raglite imports", file=sys.stderr)

# CRITICAL: Import raglite.shared.config to force Settings singleton reload
# This ensures Settings uses the test environment variables set above
import raglite.shared.config  # noqa: E402
from raglite.shared.config import Settings  # noqa: E402

raglite.shared.config.settings = Settings()  # Recreate singleton with test env vars

# ============================================================================
# PERFORMANCE FIX (2025-12-06): Default all integration tests to preserve_collection
# ============================================================================
# This applies @pytest.mark.preserve_collection to ALL tests in this directory,
# telling ensure_qdrant_test_isolation to SKIP post-test cleanup checks.
#
# WHY: Without this marker, each of the ~509 integration tests triggers a
# qdrant.count() call after execution to check if data was modified.
# With 425 unmarked tests × ~100ms = 42+ seconds of pure overhead!
#
# OVERRIDE: Tests that actually modify collection state should explicitly use:
#   @pytest.mark.manages_collection_state
# This marker has higher precedence and tells the fixture to skip cleanup
# because the test intentionally manages its own state.
#
# Result: 509 tests now skip unnecessary cleanup checks by default.
# ============================================================================
pytestmark = pytest.mark.preserve_collection

# ============================================================================
# FIXTURE MODULE LOADING
# ============================================================================
# NOTE: pytest_plugins has been moved to tests/conftest.py (root)
# per pytest deprecation warning. Defining pytest_plugins in non-top-level
# conftest files is no longer supported.
#
# Integration fixture modules are now loaded from the root conftest:
# - tests.integration.fixtures.session_state
# - tests.integration.fixtures.service_checking
# - tests.integration.fixtures.session_fixtures
# - tests.integration.fixtures.test_isolation
# - tests.integration.fixtures.module_fixtures
# - tests.integration.fixtures.helper_fixtures
#
# Session state is managed via tests.integration.fixtures.session_state module
# which is imported by dependent fixture modules.
# ============================================================================
