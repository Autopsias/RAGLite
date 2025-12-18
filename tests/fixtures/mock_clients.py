"""Mock client fixtures for unit tests.

This module provides mock fixtures for Qdrant, Claude, and Mistral clients,
preventing real API calls during testing.

Fixtures:
    mock_qdrant_client: Module-scoped mock Qdrant client
    mock_claude_client: Module-scoped mock Anthropic Claude client
    mock_mistral_api_globally: Session-scoped autouse mock blocking ALL Mistral API calls
    mock_mistral_client: Function-scoped mock Mistral client for specific tests
"""

import logging
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.fixtures.mistral_mock_helpers import (
    generate_mock_metadata,
    generate_mock_sql,
    generate_query_aware_sql,
)

logger = logging.getLogger(__name__)


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


@pytest.fixture(scope="session", autouse=True)
def mock_mistral_api_globally() -> Generator[None, None, None]:
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
    # CRITICAL APPROACH CHANGE (2025-11-22):
    # Instead of patching get_mistral_client() everywhere, patch the Mistral class itself.
    # This allows test-specific mocks to override while still preventing real API calls.
    #
    # Why this works better:
    # 1. Tests can mock raglite.shared.clients.Mistral for specific behavior
    # 2. Session mock catches ANY instantiation of Mistral class
    # 3. No conflict between session-scoped and test-scoped mocks

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
def mock_mistral_client() -> Generator[tuple[MagicMock, MagicMock], None, None]:
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
    # CRITICAL: Patch where the function is USED, not where it's DEFINED
    # query_classifier does: from raglite.shared.clients import get_mistral_client
    # So we must patch: raglite.retrieval.query_classifier.get_mistral_client
    with patch("raglite.retrieval.query_classifier.get_mistral_client") as mock_get_client:
        # Create mock client instance
        mock_client = MagicMock()

        # Configure mock to use query-aware SQL generation (imported from mistral_mock_helpers)
        mock_client.chat.complete.side_effect = generate_query_aware_sql
        mock_get_client.return_value = mock_client

        yield mock_client, mock_get_client
