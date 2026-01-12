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
    - Patches get_mistral_client() function instead of Mistral class
    - This allows test-specific function-level patches to override the session mock
    - Returns realistic mock responses for SQL generation and metadata extraction
    - Session-scoped ensures patch persists across entire test session
    - autouse=True ensures protection even if tests don't explicitly request mock

    CRITICAL FIX (2025-12-26):
    Changed from patching Mistral class to patching get_mistral_client() function.
    This resolves mock interference where test-specific function patches conflicted
    with session-level class patches, causing 145 test failures.

    CRITICAL FIX (2026-01-10):
    Added patch for raglite.agentic.agents.synthesis_methods.get_mistral_client
    to prevent real Mistral API calls from synthesis tests (4 tests were failing
    with "Status 401 Unauthorized" because synthesis_methods imports get_mistral_client
    directly and wasn't patched).

    CRITICAL FIX (2026-01-12):
    Added patch for raglite.retrieval.search.enrichment.get_mistral_client
    to prevent real Mistral API calls from enrichment tests (7 tests were failing
    with "RuntimeError: Unit test attempted to call Mistral API!" because enrichment.py
    has a lazy import at line 143 that wasn't patched).

    Patching at function level allows tests to:
    1. Completely override with their own get_mistral_client patches
    2. Use test-specific mock responses
    3. Still maintain protection against real API calls
    """
    # Create a single shared mock client with both sync and async methods configured
    mock_client_instance = MagicMock()
    # Sync method for SQL generation (query classifier)
    mock_client_instance.chat.complete.side_effect = generate_mock_sql
    # Async method for metadata extraction (embedding generation)
    mock_client_instance.chat.complete_async = AsyncMock(side_effect=generate_mock_metadata)

    # Patch the get_mistral_client function to return our mock
    # This allows test-specific patches to override by patching the same function
    # CRITICAL: Patch ALL import locations where get_mistral_client is used
    # For lazy imports (inside functions), use create=True to avoid AttributeError
    #
    # COMPREHENSIVE FIX (2026-01-12):
    # The validate-mock-coverage.py script found 17+ modules importing get_mistral_client.
    # All must be patched to prevent real API calls during tests.
    with (
        # Core clients module (source of truth)
        patch("raglite.shared.clients.get_mistral_client") as mock_get_client,
        # Ingestion modules
        patch("raglite.ingestion.embedding_generation.get_mistral_client") as mock_emb,
        patch(
            "raglite.ingestion.embedding_generation.__init__.get_mistral_client",
            create=True,
        ) as mock_emb_init,
        patch(
            "raglite.ingestion.document_ingestion.pdf_processing.__init__.get_mistral_client",
            create=True,
        ) as mock_pdf_init,
        patch(
            "raglite.ingestion.document_ingestion.pdf_processing._legacy.get_mistral_client",
            create=True,
        ) as mock_pdf_legacy,
        patch(
            "raglite.ingestion.adaptive_table.unit_inference.llm_inference.get_mistral_client",
            create=True,
        ) as mock_llm_inference,
        patch(
            "raglite.ingestion.adaptive_table.unit_inference.async_batch._legacy.get_mistral_client",
            create=True,
        ) as mock_async_batch_legacy,
        # Agentic modules
        patch("raglite.agentic.agents.synthesis_methods.get_mistral_client") as mock_synth,
        patch(
            "raglite.agentic.agents.synthesis_agent.get_mistral_client", create=True
        ) as mock_synth_agent,
        # Retrieval modules
        patch(
            "raglite.retrieval.search.enrichment.get_mistral_client", create=True
        ) as mock_enrichment,
        # Forecasting modules
        patch(
            "raglite.forecasting.hybrid.__init__.get_mistral_client", create=True
        ) as mock_forecast_hybrid,
        patch(
            "raglite.forecasting.hybrid.ensemble.get_mistral_client", create=True
        ) as mock_forecast_ensemble,
        patch(
            "raglite.forecasting.timeseries.core.get_mistral_client", create=True
        ) as mock_ts_core,
        # Insights modules
        patch("raglite.insights.anomalies.get_mistral_client", create=True) as mock_anomalies,
        patch("raglite.insights.trends.get_mistral_client", create=True) as mock_trends,
        patch(
            "raglite.insights.recommendations.get_mistral_client", create=True
        ) as mock_recommendations,
        patch(
            "raglite.insights.recommendations.synthesis.get_mistral_client", create=True
        ) as mock_rec_synthesis,
        patch(
            "raglite.insights.proactive_modules.synthesis.get_mistral_client", create=True
        ) as mock_proactive_synth,
    ):
        # Assign mock client instance to ALL patches
        mock_get_client.return_value = mock_client_instance
        mock_emb.return_value = mock_client_instance
        mock_emb_init.return_value = mock_client_instance
        mock_pdf_init.return_value = mock_client_instance
        mock_pdf_legacy.return_value = mock_client_instance
        mock_llm_inference.return_value = mock_client_instance
        mock_async_batch_legacy.return_value = mock_client_instance
        mock_synth.return_value = mock_client_instance
        mock_synth_agent.return_value = mock_client_instance
        mock_enrichment.return_value = mock_client_instance
        mock_forecast_hybrid.return_value = mock_client_instance
        mock_forecast_ensemble.return_value = mock_client_instance
        mock_ts_core.return_value = mock_client_instance
        mock_anomalies.return_value = mock_client_instance
        mock_trends.return_value = mock_client_instance
        mock_recommendations.return_value = mock_client_instance
        mock_rec_synthesis.return_value = mock_client_instance
        mock_proactive_synth.return_value = mock_client_instance
        yield


@pytest.fixture
def mock_mistral_client() -> Generator[tuple[MagicMock, MagicMock], None, None]:
    """Mock Mistral API client for SQL generation and enrichment tests.

    Prevents real API calls in CI when MISTRAL_API_KEY is not set.
    Returns query-aware mock that generates SQL with WHERE clauses based on query content.

    CRITICAL FIX (2026-01-12):
    Patch raglite.shared.clients.get_mistral_client at function scope to override
    the session-level blocking fixture in tests/unit/conftest.py.

    This allows enrichment tests (Story 5.0.6) to call enrich_results_with_metadata()
    which has a lazy import: `from raglite.shared.clients import get_mistral_client`.

    Fixture returns (mock_client_instance, mock_class) tuple for flexibility.

    Usage:
        @pytest.mark.asyncio
        async def test_sql_generation(mock_mistral_client):
            mock_client, mock_class = mock_mistral_client
            # Mock automatically generates query-specific SQL
            sql = await generate_sql_query("What is revenue for Portugal?")
            # SQL will contain: WHERE entity ILIKE '%Portugal%' AND metric ILIKE '%Revenue%'
    """
    # CRITICAL: Must patch raglite.shared.clients.get_mistral_client to override
    # the session-level blocking fixture in tests/unit/conftest.py
    # Function-scoped patches take precedence over session-scoped patches
    with (
        patch("raglite.shared.clients.get_mistral_client") as mock_shared,
        patch(
            "raglite.retrieval.query_classifier.sql_generation.get_mistral_client"
        ) as mock_sql_gen,
        patch(
            "raglite.retrieval.query_classifier.metadata_filter.get_mistral_client"
        ) as mock_metadata,
    ):
        # Create mock client instance
        mock_client = MagicMock()

        # Configure mock to use query-aware SQL generation (imported from mistral_mock_helpers)
        mock_client.chat.complete.side_effect = generate_query_aware_sql

        # All patches return the same mock instance
        mock_shared.return_value = mock_client
        mock_sql_gen.return_value = mock_client
        mock_metadata.return_value = mock_client

        yield mock_client, mock_shared
