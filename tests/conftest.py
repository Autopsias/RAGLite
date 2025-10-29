"""Pytest configuration and shared fixtures for RAGLite tests.

Provides test fixtures for configuration, mock clients, and test data.

Performance Optimization:
- Session-scoped fixtures for expensive operations (mock clients)
- Module-scoped fixtures for shared test data
- Function-scoped fixtures only when test isolation is required
"""

from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from raglite.shared.config import Settings
from raglite.shared.models import Chunk, DocumentMetadata


@pytest.fixture(scope="session")
def session_test_settings() -> Settings:
    """Provide test settings at session scope for performance.

    Session-scoped to avoid recreating settings for every test.
    Use this for read-only settings access.

    Returns:
        Settings instance with test configuration
    """
    import os

    # Set environment variables once for the entire session
    os.environ["QDRANT_HOST"] = "localhost"
    os.environ["QDRANT_PORT"] = "6333"
    os.environ["ANTHROPIC_API_KEY"] = "test-api-key-12345"
    os.environ["EMBEDDING_MODEL"] = "intfloat/e5-large-v2"
    os.environ["EMBEDDING_DIMENSION"] = "1024"
    return Settings()


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
    mock_client = MagicMock()
    mock_client.get_collections.return_value = []
    mock_client.search.return_value = []
    mock_client.query_points.return_value.points = []
    return mock_client


@pytest.fixture(scope="module")
def mock_claude_client() -> MagicMock:
    """Provide a mock Anthropic Claude client for unit tests (module-scoped).

    Module-scoped to avoid recreating mock for every test.

    Returns:
        MagicMock instance configured with typical Claude API methods
    """
    mock_client = MagicMock()
    return mock_client


@pytest.fixture(scope="module")
def sample_document_metadata() -> DocumentMetadata:
    """Provide sample document metadata for testing (module-scoped).

    Module-scoped because metadata is immutable and can be shared.

    Returns:
        DocumentMetadata instance with test data
    """
    return DocumentMetadata(
        filename="test_financial_report.pdf",
        doc_type="PDF",
        ingestion_timestamp="2025-10-04T12:00:00Z",
        page_count=10,
        source_path="/tmp/test_financial_report.pdf",
    )


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
    Fixture returns (mock_client_instance, mock_class) tuple for flexibility.

    Usage:
        @pytest.mark.asyncio
        async def test_sql_generation(mock_mistral_client):
            mock_client, mock_class = mock_mistral_client
            # Configure mock response
            mock_client.chat.complete.return_value.choices[0].message.content = "SELECT ..."
            # Now call function under test
            sql = await generate_sql_query(query)
    """
    from unittest.mock import MagicMock, patch

    with patch("raglite.retrieval.query_classifier.Mistral") as mock_class:
        # Create mock client instance
        mock_client = MagicMock()

        # Mock the response structure matching mistralai SDK
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()

        # Default SQL response (valid SELECT query for financial_tables)
        mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
ORDER BY page_number DESC
LIMIT 50;
        """.strip()

        # Configure mock to return this response
        mock_client.chat.complete.return_value = mock_response
        mock_class.return_value = mock_client

        yield mock_client, mock_class


# pytest-xdist parallel execution hooks
def pytest_addoption(parser):
    """Add custom command line options for pytest.

    This allows us to control slow test execution via CLI flags.
    """
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests (data-dependent tests requiring full 160-page PDF)",
    )


def pytest_configure(config):
    """Configure pytest for optimal parallel execution and custom options.

    This hook is called once per worker process in pytest-xdist.
    Makes the run_slow option available to all tests via pytest.run_slow.
    """
    # Store run_slow flag globally so tests can access it via pytest.run_slow
    pytest.run_slow = config.getoption("--run-slow")

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
    for item in items:
        if "integration" in str(item.fspath):
            # Check if test already has xdist_group marker
            existing_group = item.get_closest_marker("xdist_group")
            if not existing_group:
                # Add to embedding_model group to match existing integration test group
                item.add_marker(pytest.mark.xdist_group(name="embedding_model"))

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
