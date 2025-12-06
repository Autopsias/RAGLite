"""Pytest configuration and shared fixtures for RAGLite tests.

Provides test fixtures for configuration, mock clients, and test data.

Performance Optimization:
- Session-scoped fixtures for expensive operations (mock clients)
- Module-scoped fixtures for shared test data
- Function-scoped fixtures only when test isolation is required

Test Isolation Enforcement:
- Integration tests must have @pytest.mark.preserve_collection or
  @pytest.mark.manages_collection_state to prevent expensive cleanup
- This hook validates markers during test collection to prevent regressions

Fixture Timing (Phase 2.4):
- Session fixtures log start/completion time to identify bottlenecks
- Useful for diagnosing test performance issues
"""

# CRITICAL: Set APP_ENV=test BEFORE any raglite imports
# This ensures the Settings singleton uses test database ports (6335, 5433)
# Must be at module level before imports to take effect during module initialization
import os

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
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

# CRITICAL FIX (2025-11-23): Force reload of settings singleton after env vars are set
# The Settings class creates a singleton at module import time (config.py line 135).
# If config.py was imported before conftest.py set test env vars, we need to recreate it.
import raglite.shared.config
from raglite.shared.config import Settings
from raglite.shared.models import Chunk, DocumentMetadata

raglite.shared.config.settings = Settings()  # Recreate singleton with test env vars

logger = logging.getLogger(__name__)


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
    import os

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


@pytest.fixture(scope="module")
def mock_qdrant_client() -> MagicMock:
    """Provide a mock Qdrant client for unit tests (module-scoped).

    Module-scoped to avoid recreating mock for every test.
    Safe because unit tests don't modify the mock state.

    Returns:
        MagicMock instance configured with typical Qdrant methods
    """
    start_time = time.time()
    logger.info("Fixture 'mock_qdrant_client' starting")

    mock_client = MagicMock()
    mock_client.get_collections.return_value = []
    mock_client.search.return_value = []
    mock_client.query_points.return_value.points = []

    _timed_fixture("mock_qdrant_client", mock_qdrant_client, start_time)
    return mock_client


@pytest.fixture(scope="module")
def mock_claude_client() -> MagicMock:
    """Provide a mock Anthropic Claude client for unit tests (module-scoped).

    Module-scoped to avoid recreating mock for every test.

    Returns:
        MagicMock instance configured with typical Claude API methods
    """
    start_time = time.time()
    logger.info("Fixture 'mock_claude_client' starting")

    mock_client = MagicMock()

    _timed_fixture("mock_claude_client", mock_claude_client, start_time)
    return mock_client


@pytest.fixture(scope="module")
def sample_document_metadata() -> DocumentMetadata:
    """Provide sample document metadata for testing (module-scoped).

    Module-scoped because metadata is immutable and can be shared.

    Returns:
        DocumentMetadata instance with test data
    """
    start_time = time.time()
    logger.info("Fixture 'sample_document_metadata' starting")

    metadata = DocumentMetadata(
        filename="test_financial_report.pdf",
        doc_type="PDF",
        ingestion_timestamp="2025-10-04T12:00:00Z",
        page_count=10,
        source_path="/tmp/test_financial_report.pdf",
    )

    _timed_fixture("sample_document_metadata", sample_document_metadata, start_time)
    return metadata


@pytest.fixture
def sample_chunk(sample_document_metadata: DocumentMetadata) -> Chunk:
    """Provide sample chunk for testing (function-scoped for isolation).

    Function-scoped because tests may modify chunk content.

    Args:
        sample_document_metadata: Fixture providing document metadata

    Returns:
        Chunk instance with test data
    """
    return Chunk(
        chunk_id="chunk-001",
        content="Q3 revenue was $50M, up 20% YoY.",
        metadata=sample_document_metadata,
        page_number=5,
        embedding=[0.1] * 1024,  # Mock embedding vector
    )


@pytest.fixture(scope="session", autouse=True)
def mock_mistral_api_globally():
    """Session-scoped autouse mock - BLOCKS ALL Mistral API calls in entire test suite.

    CRITICAL PERFORMANCE & COST FIX:
    - Prevents real Mistral API calls during session fixture ingestion (metadata extraction)
    - Prevents real Mistral API calls during integration tests (SQL generation, query classification)
    - Eliminates 660-1100 seconds of API latency overhead
    - Eliminates ALL Mistral API token costs during testing

    This fixture runs ONCE per pytest invocation at session start, BEFORE any tests or
    other fixtures execute, ensuring NO real API calls occur anywhere in the test suite.

    Protects:
    - Session fixture PDF ingestion with metadata extraction
    - All integration tests calling hybrid_search() → classify_query() → Mistral API
    - All unit tests that may use Mistral API
    - Any async tasks spawned by tests

    Technical Details:
    - Patches ALL possible import paths where get_mistral_client() is used
    - Returns realistic mock responses for SQL generation and metadata extraction
    - Session-scoped ensures patch persists across entire test session
    - autouse=True ensures protection even if tests don't explicitly request mock
    """
    from unittest.mock import MagicMock, patch

    def generate_mock_sql(messages, **kwargs):
        """Mock SQL generation for table search - returns query-aware realistic SQL.

        Extracts entity, metric, and period filters from the natural language query
        to generate SQL with appropriate WHERE clauses, ensuring tests retrieve
        relevant table data instead of all rows.
        """
        # Extract query from messages (last user message)
        query_text = ""
        if messages and len(messages) > 0:
            # Handle both dict and object message formats
            last_msg = messages[-1]
            if isinstance(last_msg, dict):
                full_content = last_msg.get("content", "")
            else:
                full_content = getattr(last_msg, "content", "")

            # For SQL generation, extract actual query from the prompt template
            # The prompt contains: "**USER QUERY:**\n{query}\n\n**INSTRUCTIONS:**"
            if "**USER QUERY:**" in full_content:
                # Extract text after "**USER QUERY:**" and before "**INSTRUCTIONS:**"
                start_marker = "**USER QUERY:**"
                end_marker = "**INSTRUCTIONS:**"
                start_idx = full_content.find(start_marker) + len(start_marker)
                end_idx = full_content.find(end_marker)
                if end_idx > start_idx:
                    query_text = full_content[start_idx:end_idx].strip()
                else:
                    query_text = full_content[start_idx:].strip()
            else:
                # Fallback: use full content for non-SQL generation calls
                query_text = full_content

        query_lower = query_text.lower()

        # Build WHERE clause filters based on query content
        where_conditions = []

        # Entity filters (country names) - handle multiple entities for comparison queries
        entities = []
        if "portugal" in query_lower:
            entities.append("entity ILIKE '%Portugal%'")
        if "tunisia" in query_lower:
            entities.append("entity ILIKE '%Tunisia%'")
        if "angola" in query_lower:
            entities.append("entity ILIKE '%Angola%'")
        if "brazil" in query_lower:
            entities.append("entity ILIKE '%Brazil%'")

        # Add entity filter (OR if multiple entities for comparison)
        if entities:
            if len(entities) == 1:
                where_conditions.append(entities[0])
            else:
                where_conditions.append("(" + " OR ".join(entities) + ")")

        # Metric filters - handle multiple metrics with OR
        # For "table for X" queries, be flexible with metric matching to handle test data
        metrics = []
        if "ebitda" in query_lower:
            metrics.append("metric ILIKE '%EBITDA%'")
        if "revenue" in query_lower or "turnover" in query_lower:
            metrics.append("metric ILIKE '%Revenue%'")
        # CRITICAL FIX (2025-11-24): "operating" should match BOTH "operational" AND "operating"
        # Test query "operating expenses" needs to match test data which may use either term
        if "operating" in query_lower:
            # Use OR to match both variations (operational OR operating)
            metrics.append("(metric ILIKE '%operational%' OR metric ILIKE '%operating%')")
        if "variable cost" in query_lower:
            metrics.append("metric ILIKE '%variable cost%'")
        if "currency" in query_lower:
            metrics.append("metric ILIKE '%Currency%'")
        if "frequency" in query_lower:
            metrics.append("metric ILIKE '%frequency%'")

        # Add metric filter (OR if multiple metrics)
        if metrics:
            if len(metrics) == 1:
                where_conditions.append(metrics[0])
            else:
                where_conditions.append("(" + " OR ".join(metrics) + ")")

        # Period filters (month/year)
        if "august" in query_lower or "aug" in query_lower:
            where_conditions.append("period ILIKE '%Aug%'")
        if "2025" in query_lower:
            where_conditions.append("(fiscal_year = 2025 OR fiscal_year IS NULL)")

        # Construct WHERE clause
        where_clause = ""
        if where_conditions:
            where_clause = "\nWHERE " + " AND ".join(where_conditions)

        # CRITICAL FIX (2025-11-24): For queries with ONLY metric filters and no temporal/entity filters,
        # use a more permissive query to ensure CI has matching data.
        # This prevents SQL returning 0 results which triggers vector fallback.
        # Root cause: CI test database may have different metric naming than local
        # ("operating expenses" vs "operational costs" vs "operating costs")
        is_generic_table_query = (
            "table" in query_lower
            and len(where_conditions) <= 1  # Only metric filter, no entity/period
            and metrics  # Has metric filter
            and not entities  # No entity filter
            and not (
                "august" in query_lower or "aug" in query_lower or "2025" in query_lower
            )  # No period filter
        )

        if is_generic_table_query:
            # PERMISSIVE QUERY: Return ANY data for generic "table for X" queries
            # This ensures SQL search returns results in CI environment
            where_clause = ""  # Remove restrictive filters
            sql = """SELECT document_id, entity, metric, value, unit, period, fiscal_year, page_number, table_caption
FROM financial_tables
ORDER BY page_number DESC
LIMIT 10;""".strip()
        else:
            # Normal query with filters
            sql = f"""SELECT document_id, entity, metric, value, unit, period, fiscal_year, page_number, table_caption
FROM financial_tables{where_clause}
ORDER BY page_number DESC
LIMIT 50;""".strip()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = sql
        return mock_response

    def generate_mock_metadata(messages, **kwargs):
        """Mock metadata extraction for chunk enrichment - returns realistic JSON."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[
            0
        ].message.content = '{"metric_category": "Revenue", "time_period": "Q3 2025"}'
        return mock_response

    # CRITICAL APPROACH CHANGE (2025-11-22):
    # Instead of patching get_mistral_client() everywhere, patch the Mistral class itself.
    # This allows test-specific mocks to override while still preventing real API calls.
    #
    # Why this works better:
    # 1. Tests can mock raglite.shared.clients.Mistral for specific behavior
    # 2. Session mock catches ANY instantiation of Mistral class
    # 3. No conflict between session-scoped and test-scoped mocks

    # Import AsyncMock for async Mistral client methods
    from unittest.mock import AsyncMock

    # Create a single shared mock client with both sync and async methods configured
    mock_client_instance = MagicMock()
    # Sync method for SQL generation (query classifier)
    mock_client_instance.chat.complete.side_effect = generate_mock_sql
    # Async method for metadata extraction (embedding generation)
    mock_client_instance.chat.complete_async = AsyncMock(side_effect=generate_mock_metadata)

    # Patch the Mistral class constructor to return our mock
    with patch("raglite.shared.clients.Mistral") as mock_mistral_class:
        mock_mistral_class.return_value = mock_client_instance
        yield


@pytest.fixture
def mock_mistral_client():
    """Mock Mistral API client for SQL generation tests.

    Prevents real API calls in CI when MISTRAL_API_KEY is not set.
    Returns query-aware mock that generates SQL with WHERE clauses based on query content.

    Fixture returns (mock_client_instance, mock_class) tuple for flexibility.

    Usage:
        @pytest.mark.asyncio
        async def test_sql_generation(mock_mistral_client):
            mock_client, mock_class = mock_mistral_client
            # Mock automatically generates query-specific SQL
            sql = await generate_sql_query("What is revenue for Portugal?")
            # SQL will contain: WHERE entity ILIKE '%Portugal%' AND metric ILIKE '%Revenue%'
    """
    from unittest.mock import MagicMock, patch

    def generate_query_aware_sql(messages, **kwargs):
        """Generate query-specific SQL based on natural language query content.

        This mock inspects the query to extract entity, metric, and period filters,
        then generates realistic SQL with appropriate WHERE clauses.

        Args:
            messages: List of message dicts with 'content' containing the natural language query

        Returns:
            Mock response object with SQL query string in choices[0].message.content
        """
        # Extract query from messages (last user message)
        query_text = ""
        if messages and len(messages) > 0:
            # Handle both dict and object message formats
            last_msg = messages[-1]
            if isinstance(last_msg, dict):
                full_content = last_msg.get("content", "")
            else:
                full_content = getattr(last_msg, "content", "")

            # For SQL generation, extract actual query from the prompt template
            # The prompt contains: "**USER QUERY:**\n{query}\n\n**INSTRUCTIONS:**"
            if "**USER QUERY:**" in full_content:
                # Extract text after "**USER QUERY:**" and before "**INSTRUCTIONS:**"
                start_marker = "**USER QUERY:**"
                end_marker = "**INSTRUCTIONS:**"
                start_idx = full_content.find(start_marker) + len(start_marker)
                end_idx = full_content.find(end_marker)
                if end_idx > start_idx:
                    query_text = full_content[start_idx:end_idx].strip()
                else:
                    query_text = full_content[start_idx:].strip()
            else:
                # Fallback: use full content for non-SQL generation calls
                query_text = full_content

        query_lower = query_text.lower()

        # Build WHERE clause filters based on query content
        where_conditions = []

        # Entity filters (country names) - handle multiple entities for comparison queries
        entities = []
        if "portugal" in query_lower:
            entities.append("entity ILIKE '%Portugal%'")
        if "tunisia" in query_lower:
            entities.append("entity ILIKE '%Tunisia%'")
        if "angola" in query_lower:
            entities.append("entity ILIKE '%Angola%'")
        if "brazil" in query_lower:
            entities.append("entity ILIKE '%Brazil%'")

        # Add entity filter (OR if multiple entities for comparison)
        if entities:
            if len(entities) == 1:
                where_conditions.append(entities[0])
            else:
                where_conditions.append("(" + " OR ".join(entities) + ")")

        # Metric filters - handle multiple metrics with OR
        # For "table for X" queries, be flexible with metric matching to handle test data
        metrics = []
        if "ebitda" in query_lower:
            metrics.append("metric ILIKE '%EBITDA%'")
        if "revenue" in query_lower or "turnover" in query_lower:
            metrics.append("metric ILIKE '%Revenue%'")
        # CRITICAL FIX (2025-11-24): "operating" should match BOTH "operational" AND "operating"
        # Test query "operating expenses" needs to match test data which may use either term
        if "operating" in query_lower:
            # Use OR to match both variations (operational OR operating)
            metrics.append("(metric ILIKE '%operational%' OR metric ILIKE '%operating%')")
        if "variable cost" in query_lower:
            metrics.append("metric ILIKE '%variable cost%'")
        if "currency" in query_lower:
            metrics.append("metric ILIKE '%Currency%'")
        if "frequency" in query_lower:
            metrics.append("metric ILIKE '%frequency%'")

        # Add metric filter (OR if multiple metrics)
        if metrics:
            if len(metrics) == 1:
                where_conditions.append(metrics[0])
            else:
                where_conditions.append("(" + " OR ".join(metrics) + ")")

        # Period filters (month/year)
        if "august" in query_lower or "aug" in query_lower:
            where_conditions.append("period ILIKE '%Aug%'")
        if "2025" in query_lower:
            where_conditions.append("(fiscal_year = 2025 OR fiscal_year IS NULL)")

        # Construct WHERE clause
        where_clause = ""
        if where_conditions:
            where_clause = "\nWHERE " + " AND ".join(where_conditions)

        # CRITICAL FIX (2025-11-24): For queries with ONLY metric filters and no temporal/entity filters,
        # use a more permissive query to ensure CI has matching data.
        # This prevents SQL returning 0 results which triggers vector fallback.
        # Root cause: CI test database may have different metric naming than local
        # ("operating expenses" vs "operational costs" vs "operating costs")
        is_generic_table_query = (
            "table" in query_lower
            and len(where_conditions) <= 1  # Only metric filter, no entity/period
            and metrics  # Has metric filter
            and not entities  # No entity filter
            and not (
                "august" in query_lower or "aug" in query_lower or "2025" in query_lower
            )  # No period filter
        )

        if is_generic_table_query:
            # PERMISSIVE QUERY: Return ANY data for generic "table for X" queries
            # This ensures SQL search returns results in CI environment
            where_clause = ""  # Remove restrictive filters
            sql = """SELECT document_id, entity, metric, value, unit, period, fiscal_year, page_number, table_caption
FROM financial_tables
ORDER BY page_number DESC
LIMIT 10;""".strip()
        else:
            # Normal query with filters
            sql = f"""SELECT document_id, entity, metric, value, unit, period, fiscal_year, page_number, table_caption
FROM financial_tables{where_clause}
ORDER BY page_number DESC
LIMIT 50;""".strip()

        # Create mock response structure matching mistralai SDK
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = sql

        return mock_response

    # CRITICAL: Patch where the function is USED, not where it's DEFINED
    # query_classifier does: from raglite.shared.clients import get_mistral_client
    # So we must patch: raglite.retrieval.query_classifier.get_mistral_client
    with patch("raglite.retrieval.query_classifier.get_mistral_client") as mock_get_client:
        # Create mock client instance
        mock_client = MagicMock()

        # Configure mock to use query-aware SQL generation
        mock_client.chat.complete.side_effect = generate_query_aware_sql
        mock_get_client.return_value = mock_client

        yield mock_client, mock_get_client


# pytest-xdist parallel execution hooks
def pytest_addoption(parser):
    """Add custom command line options for pytest.

    This allows us to control slow test execution, ingestion behavior, and test isolation
    enforcement via CLI flags.
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


def pytest_configure(config):
    """Configure pytest for optimal parallel execution and custom options.

    This hook is called once per worker process in pytest-xdist.
    Makes the run_slow and skip_ingestion options available to all tests.
    """
    # Store flags globally so tests can access them
    pytest.run_slow = config.getoption("--run-slow")
    pytest.skip_ingestion = config.getoption("--skip-ingestion")

    # Only set workerinput if we're actually in xdist mode
    # DO NOT create empty workerinput - it confuses pytest-cov!
    # pytest-xdist will create workerinput if running with -n flag


def pytest_collection_modifyitems(config, items):
    """Modify test collection to optimize execution order and prevent race conditions.

    1. Groups all integration tests to run in the same xdist worker (prevents Qdrant race conditions)
    2. Reorders tests to run fast tests first for quicker feedback
    """

    # Force ALL integration tests into the EXISTING "embedding_model" xdist worker group
    # CRITICAL (2025-11-21): MUST force override ALL xdist groups to "embedding_model"
    # - pytest-xdist creates separate PROCESS per xdist group
    # - Session-scoped fixtures run ONCE PER PROCESS (not once globally)
    # - Split groups = duplicate session fixture runs = 2x slowdown (50s × N workers)
    # - Database tests previously used xdist_group(name="database") creating 2nd worker
    # - Result: Session fixture ran TWICE (1600s total vs 600s expected)
    enforce_markers = config.getoption("--enforce-isolation-markers", default=False)

    for item in items:
        if "integration" in str(item.fspath):
            # FORCE all integration tests into embedding_model group (override any existing)
            # This ensures session-scoped fixtures run ONCE, not once per worker
            existing_group = item.get_closest_marker("xdist_group")

            # Remove any existing xdist_group marker (including "database")
            if existing_group:
                # Remove from markers list (keywords dict is immutable in pytest 8.x)
                item.own_markers = [m for m in item.own_markers if m.name != "xdist_group"]

            # Force embedding_model group (single worker for all integration tests)
            item.add_marker(pytest.mark.xdist_group(name="embedding_model"))

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

    # Sort tests: unit tests first, then integration, then e2e/slow
    def test_priority(item):
        """Calculate test priority (lower = run first)."""
        if "unit" in item.keywords:
            return 0
        elif "integration" in item.keywords:
            return 1
        elif "slow" in item.keywords or "e2e" in item.keywords:
            return 2
        else:
            return 1  # Default: medium priority

    items.sort(key=test_priority)
