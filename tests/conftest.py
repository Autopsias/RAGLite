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

import logging
import os
import time
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from raglite.shared.config import Settings
from raglite.shared.models import Chunk, DocumentMetadata

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure test environment variables for all tests.

    OPTIMIZATION: Sets TESTING=true to enable test-specific optimizations
    in client connections, reducing timeouts and preventing test hangs.

    This fixture runs once per test session and applies to all tests.
    """
    # Set test environment flag for connection timeout optimizations
    os.environ["TESTING"] = "true"
    logger.info("Test environment configured: TESTING=true (enables connection timeouts)")

    yield

    # Clean up environment variable after session
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
        logger.info("Test environment cleaned up: TESTING=false")


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

    Returns:
        Settings instance with test configuration
    """
    import os

    start_time = time.time()
    logger.info("Fixture 'session_test_settings' starting")

    # Set environment variables once for the entire session
    os.environ["QDRANT_HOST"] = "localhost"
    os.environ["QDRANT_PORT"] = "6333"
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

    Args:
        monkeypatch: pytest monkeypatch fixture

    Returns:
        Settings instance with test configuration
    """
    monkeypatch.setenv("QDRANT_HOST", "localhost")
    monkeypatch.setenv("QDRANT_PORT", "6333")
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
        metrics = []
        if "ebitda" in query_lower:
            metrics.append("metric ILIKE '%EBITDA%'")
        if "revenue" in query_lower or "turnover" in query_lower:
            metrics.append("metric ILIKE '%Revenue%'")
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
            where_conditions.append("fiscal_year = 2025")

        # Construct WHERE clause
        where_clause = ""
        if where_conditions:
            where_clause = "\nWHERE " + " AND ".join(where_conditions)

        # Generate SQL query
        sql = f"""SELECT entity, metric, value, unit, period, fiscal_year, page_number
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
    # This prevents race conditions on shared Qdrant database AND avoids reloading embedding model
    # Tests that already have @pytest.mark.xdist_group("embedding_model") keep it
    # Tests without any group get added to "embedding_model" to ensure all integration tests
    # run in the same worker (critical for session-scoped fixtures)
    enforce_markers = config.getoption("--enforce-isolation-markers", default=False)

    for item in items:
        if "integration" in str(item.fspath):
            # Check if test already has xdist_group marker
            existing_group = item.get_closest_marker("xdist_group")
            if not existing_group:
                # Add to embedding_model group to match existing integration test group
                item.add_marker(pytest.mark.xdist_group(name="embedding_model"))

            # Enforce test isolation markers (Phase 2 optimization)
            # Integration tests must have @pytest.mark.preserve_collection or
            # @pytest.mark.manages_collection_state to prevent expensive cleanup
            has_preserve = item.get_closest_marker("preserve_collection")
            has_manages = item.get_closest_marker("manages_collection_state")

            if not (has_preserve or has_manages):
                # Only error if enforcement is enabled
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
