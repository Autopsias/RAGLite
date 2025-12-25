"""Root pytest configuration for RAGLite tests.

This is the root conftest.py that sets up the test environment and loads
fixture modules via pytest_plugins. The fixture modules are organized in
tests/fixtures/ for better maintainability and AI comprehension.

Fixture Modules Loaded:
- database_fixtures: Session-scoped database fixtures (Qdrant, PostgreSQL)
- mock_clients: Mock Qdrant, Claude, Mistral clients
- sample_data: Sample document metadata and chunks
- pytest_hooks: Custom pytest hooks (options, collection modification)
- performance_monitoring: Session timing and budget validation

Test Environment Configuration:
- APP_ENV=test: Uses test database ports (Qdrant 6335, PostgreSQL 5433)
- TESTING=true: Enables test-specific optimizations (connection timeouts)
- PostgreSQL: raglite_ci database on port 5433
- Qdrant: _test collection suffix on port 6335
- LIGHTWEIGHT_TESTS=true: Mock heavy ML dependencies for unit tests (CI mode)
"""

# CRITICAL: CI lightweight mode - mock heavy ML dependencies BEFORE any imports
# This prevents loading 10-15GB of ML libraries during test collection on CI runners with ~6GB RAM
import os
import sys
from unittest.mock import MagicMock

if os.environ.get("LIGHTWEIGHT_TESTS") == "true":
    # Mock heavy dependencies before they're imported
    # These dependencies are only needed for forecasting/insights (not core RAG)
    # CRITICAL: Must include ALL submodules that are directly imported
    heavy_deps = [
        # Prophet (~1-2GB)
        "prophet",
        "prophet.serialize",
        "prophet.diagnostics",
        # Chronos/PyTorch (~2-3GB combined)
        "chronos",
        "chronos_forecasting",
        "pytorch_forecasting",
        "pytorch_lightning",
        "torch",
        "torch.nn",
        "transformers",
        # Sentence Transformers (~2-3GB)
        "sentence_transformers",
        # Statsmodels (~500MB) - must include all imported submodules
        "statsmodels",
        "statsmodels.tsa",
        "statsmodels.tsa.stattools",
        "statsmodels.tsa.holtwinters",  # ExponentialSmoothing
        # PMDARIMA (~200MB)
        "pmdarima",
        "pmdarima.arima",
        # Boosting libraries (~500MB each)
        "catboost",
        "lightgbm",
        "xgboost",
    ]
    for dep in heavy_deps:
        if dep not in sys.modules:
            sys.modules[dep] = MagicMock()
    print(f"[LIGHTWEIGHT_TESTS] Mocked {len(heavy_deps)} heavy ML dependencies")

# CRITICAL: Set APP_ENV=test BEFORE any raglite imports
# This ensures the Settings singleton uses test database ports (6335, 5433)
# Must be at module level before imports to take effect during module initialization

os.environ["APP_ENV"] = "test"
os.environ["TESTING"] = "true"

# CRITICAL (2025-11-23): PostgreSQL settings NO LONGER auto-adjust in validator
# Must set PostgreSQL environment variables explicitly for test environment
# Qdrant settings STILL auto-adjust (port 6335, collection _test/_ci suffix)
# NOTE: PostgreSQL test container (port 5433) uses raglite_ci credentials, not raglite_test
os.environ["POSTGRES_PORT"] = "5433"
os.environ["POSTGRES_DB"] = "raglite_ci"
os.environ["POSTGRES_USER"] = "raglite_ci"
os.environ["POSTGRES_PASSWORD"] = "raglite_ci"

# CRITICAL FIX (2025-12-06): Set dummy MISTRAL_API_KEY for unit tests
# The get_mistral_client() function validates the API key BEFORE instantiation,
# which happens before the mock_mistral_api_globally fixture can patch the Mistral class.
# This dummy key prevents ValueError in unit tests while the autouse mock handles actual API calls.
os.environ.setdefault("MISTRAL_API_KEY", "test-mistral-api-key-for-ci")

import logging
import time

import pytest
from pytest import MonkeyPatch

# CRITICAL FIX (2025-11-23): Force reload of settings singleton after env vars are set
# The Settings class creates a singleton at module import time (config.py line 135).
# If config.py was imported before conftest.py set test env vars, we need to recreate it.
import raglite.shared.config
from raglite.shared.config import Settings

raglite.shared.config.settings = Settings()  # Recreate singleton with test env vars

logger = logging.getLogger(__name__)

# Load fixture modules via pytest_plugins
# NOTE: Order matters for hooks - pytest_hooks must load BEFORE other plugins
# NOTE: pytest_plugins MUST be defined at root conftest only (pytest deprecation)
pytest_plugins = [
    # Root fixtures (for all tests)
    "tests.fixtures.pytest_hooks",  # Load hooks first (pytest_addoption, etc.)
    "tests.fixtures.performance_monitoring",  # Session timing hooks
    "tests.fixtures.database_fixtures",  # Database fixtures
    "tests.fixtures.mistral_mock_helpers",  # Mistral mock helper functions (must be before mock_clients)
    "tests.fixtures.mock_clients",  # Mock clients (includes autouse Mistral mock)
    "tests.fixtures.sample_data",  # Sample metadata and chunks
    # Integration fixtures (moved from tests/integration/conftest.py per pytest deprecation)
    "tests.integration.fixtures.session_state",
    "tests.integration.fixtures.service_checking",
    "tests.integration.fixtures.container_lifecycle",  # Auto-restart for test containers (2025-12-24)
    "tests.integration.fixtures.session_fixtures",
    "tests.integration.fixtures.test_isolation",
    "tests.integration.fixtures.module_fixtures",
    "tests.integration.fixtures.helper_fixtures",
]


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure test environment variables for all tests.

    NOTE (2025-11-19): Environment variables are now set at module level (lines 25-35)
    BEFORE any imports to ensure the Settings singleton uses test database ports.
    This fixture now only logs the configuration and handles cleanup.

    CRITICAL (2025-11-23): PostgreSQL settings NO LONGER auto-adjust in validator.
    PostgreSQL env vars (POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD)
    must be set EXPLICITLY at module level.

    CRITICAL FIX (2025-11-23): Settings singleton is forcibly reloaded after env vars
    are set (line 50) to ensure test database configuration takes effect even if
    config.py was imported before conftest.py ran.

    CRITICAL FIX (2025-11-27 - Story 4.0.7): Added SafetyGuard validation to catch
    any test attempting to run on production infrastructure. This is a defense-in-depth
    measure after the 2025-11-27 incident where VS Code test runner deleted production data.

    Test databases run on separate ports:
    - Qdrant: localhost:6335 (auto-adjusted by Settings validator)
    - PostgreSQL: localhost:5433 with raglite_ci credentials (set explicitly)

    OPTIMIZATION: TESTING=true enables test-specific optimizations
    in client connections, reducing timeouts and preventing test hangs.
    """
    # Environment already set at module level - just log it
    logger.info(
        "Test environment confirmed: APP_ENV=test (uses Qdrant:6335, PostgreSQL:5433 raglite_ci)"
    )
    logger.info("Test environment confirmed: TESTING=true (enables connection timeouts)")
    logger.info("Test PostgreSQL settings: POSTGRES_PORT=5433, POSTGRES_DB=raglite_ci")

    # DEFENSE-IN-DEPTH (Story 4.0.7): Validate test environment via SafetyGuard
    # This is a redundant check - integration/conftest.py also validates.
    # Belt-and-suspenders approach to prevent production data loss.
    from raglite.shared.safety import SafetyGuard

    guard = SafetyGuard()
    try:
        # Note: This will log a warning if on production ports but won't fail
        # because unit tests don't do database operations. Integration tests
        # have their own stricter check that WILL fail.
        if guard.is_production:
            logger.warning(
                "SafetyGuard detected PRODUCTION environment in test session! "
                "This should not happen - APP_ENV should be 'test'. "
                f"Current: app_env={guard._app_env}, qdrant_port={guard._qdrant_port}"
            )
    except Exception as e:
        logger.error(f"SafetyGuard check failed: {e}")

    yield

    # Clean up environment variables after session
    if "APP_ENV" in os.environ:
        del os.environ["APP_ENV"]
        logger.info("Test environment cleaned up: APP_ENV removed")
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
        logger.info("Test environment cleaned up: TESTING=false")
    # Clean up PostgreSQL env vars
    for key in ["POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture(scope="session", autouse=True)
def disable_joblib_parallel_processing():
    """Disable parallel processing in joblib to prevent resource leaks.

    CRITICAL FIX (2025-12-24): Prevents SIGKILL during pytest shutdown.

    Issue: Integration tests use forecasting models (statsmodels, pmdarima) which
    use joblib for parallel processing. Joblib creates multiprocessing semaphores
    and shared memory that aren't properly cleaned up during pytest shutdown,
    causing Python's multiprocessing resource_tracker to issue warnings and
    trigger SIGKILL.

    Fix Strategy (Two-Part):
    1. CI Workflow: Kills orphaned resource_tracker processes BEFORE pytest starts
       (see .github/workflows/ci.yml "Pre-test memory cleanup" step)
    2. This Fixture: Configures joblib to use threading instead of multiprocessing
       to prevent NEW resource leaks during current test run

    Resource leak warnings before fix:
    - UserWarning: resource_tracker: There appear to be 1 leaked semaphore objects
    - UserWarning: resource_tracker: There appear to be 6 leaked semlock objects
    - UserWarning: resource_tracker: There appear to be 2 leaked folder objects

    Impact: Tests run successfully (159 passed) but pytest process was killed
    with SIGKILL during cleanup phase.

    References:
    - https://github.com/joblib/joblib/issues/945
    - https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
    """
    # Configure environment variable to disable joblib parallel processing
    # This affects statsmodels, scikit-learn, and pmdarima which use joblib internally
    os.environ["JOBLIB_START_METHOD"] = "threading"  # Use threading instead of multiprocessing
    os.environ["LOKY_MAX_CPU_COUNT"] = "1"  # Limit loky (joblib backend) to single CPU

    logger.info("Joblib parallel processing disabled: using threading backend")
    logger.info("This prevents multiprocessing resource leaks during test cleanup")

    yield

    # Cleanup: restore to defaults
    if "JOBLIB_START_METHOD" in os.environ:
        del os.environ["JOBLIB_START_METHOD"]
    if "LOKY_MAX_CPU_COUNT" in os.environ:
        del os.environ["LOKY_MAX_CPU_COUNT"]

    # Force garbage collection to cleanup any remaining resources
    import gc

    gc.collect()
    logger.info("Joblib configuration cleaned up")


def _timed_fixture(fixture_name: str, func, start_time: float) -> None:
    """Log fixture execution time (Phase 2.4 instrumentation).

    Args:
        fixture_name: Name of the fixture for logging
        func: Fixture function (for documentation)
        start_time: Start time from time.time()
    """
    elapsed = time.time() - start_time
    logger.info(
        f"Fixture '{fixture_name}' completed",
        extra={"elapsed_seconds": f"{elapsed:.2f}", "fixture": fixture_name},
    )


@pytest.fixture(scope="session")
def session_test_settings() -> Settings:
    """Provide test settings at session scope for performance.

    Session-scoped to avoid recreating settings for every test.
    Use this for read-only settings access.

    NOTE (2025-11-23): PostgreSQL settings NO LONGER auto-adjust in validator.
    PostgreSQL env vars (POSTGRES_PORT, POSTGRES_DB, etc) are set at module level (lines 31-34).
    Qdrant settings STILL auto-adjust via Settings.adjust_for_environment() (port 6335).

    Returns:
        Settings instance with test configuration
    """
    start_time = time.time()
    logger.info("Fixture 'session_test_settings' starting")

    # Set environment variables once for the entire session
    # NOTE: QDRANT_PORT is NOT set here - it's automatically determined by APP_ENV=test
    # via Settings.adjust_for_environment() (auto-adjusts to 6335)
    # PostgreSQL settings (POSTGRES_PORT, POSTGRES_DB, etc) are set at module level
    os.environ["QDRANT_HOST"] = "localhost"
    os.environ["ANTHROPIC_API_KEY"] = "test-api-key-12345"
    os.environ["EMBEDDING_MODEL"] = "intfloat/e5-large-v2"
    os.environ["EMBEDDING_DIMENSION"] = "1024"
    settings = Settings()

    _timed_fixture("session_test_settings", session_test_settings, start_time)
    return settings


@pytest.fixture
def test_settings(monkeypatch: MonkeyPatch) -> Settings:
    """Provide test settings with safe defaults (function-scoped for isolation).

    Overrides environment variables to prevent tests from using production values.
    Use this when tests need to modify settings.

    NOTE (2025-11-23): PostgreSQL settings NO LONGER auto-adjust in validator.
    PostgreSQL env vars (POSTGRES_PORT, POSTGRES_DB, etc) are set at module level (lines 31-34).
    Qdrant settings STILL auto-adjust via Settings.adjust_for_environment() (port 6335).

    Args:
        monkeypatch: pytest monkeypatch fixture

    Returns:
        Settings instance with test configuration
    """
    # NOTE: QDRANT_PORT is NOT set here - it's automatically determined by APP_ENV=test
    # via Settings.adjust_for_environment() (auto-adjusts to 6335)
    # PostgreSQL settings (POSTGRES_PORT, POSTGRES_DB, etc) are set at module level
    monkeypatch.setenv("QDRANT_HOST", "localhost")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("EMBEDDING_MODEL", "intfloat/e5-large-v2")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "1024")
    return Settings()
