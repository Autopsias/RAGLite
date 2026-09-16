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


def _get_mistral_client_patch_targets() -> list[str]:
    """Get all module paths that need get_mistral_client patched.

    This helper consolidates the comprehensive list of modules that import
    get_mistral_client. All patches are required to prevent real Mistral API
    calls during testing (session fixture ingestion, integration tests, etc.).

    Returns:
        List of module paths to patch with mock_mistral_client
    """
    return [
        # Core clients module (source of truth)
        "raglite.shared.clients.get_mistral_client",
        # Ingestion modules
        "raglite.ingestion.embedding_generation.get_mistral_client",
        "raglite.ingestion.embedding_generation.__init__.get_mistral_client",
        "raglite.ingestion.document_ingestion.pdf_processing.__init__.get_mistral_client",
        "raglite.ingestion.document_ingestion.pdf_processing._legacy.get_mistral_client",
        "raglite.ingestion.adaptive_table.unit_inference.llm_inference.get_mistral_client",
        "raglite.ingestion.adaptive_table.unit_inference.async_batch._legacy.get_mistral_client",
        # Classification modules (Epic 9)
        "raglite.ingestion.classification.period_classifier.get_mistral_client",
        # Agentic modules
        "raglite.agentic.agents.synthesis_methods.get_mistral_client",
        "raglite.agentic.agents.synthesis_agent.get_mistral_client",
        # Retrieval modules
        "raglite.retrieval.search.enrichment.get_mistral_client",
        # Forecasting modules
        "raglite.forecasting.hybrid.__init__.get_mistral_client",
        "raglite.forecasting.hybrid.ensemble.get_mistral_client",
        "raglite.forecasting.timeseries.core.get_mistral_client",
        # Retrieval query classifier modules (SQL generation, metadata filtering)
        "raglite.retrieval.query_classifier.sql_generation.get_mistral_client",
        "raglite.retrieval.query_classifier.metadata_filter.get_mistral_client",
        # Insights modules
        "raglite.insights.anomalies.get_mistral_client",
        "raglite.insights.trends.get_mistral_client",
        "raglite.insights.recommendations.get_mistral_client",
        "raglite.insights.recommendations.synthesis.get_mistral_client",
        "raglite.insights.proactive_modules.synthesis.get_mistral_client",
    ]


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
    from contextlib import ExitStack

    # Create a single shared mock client with both sync and async methods configured
    mock_client_instance = MagicMock()
    # Sync method for SQL generation (query classifier)
    mock_client_instance.chat.complete.side_effect = generate_mock_sql
    # Async method for metadata extraction (embedding generation)
    mock_client_instance.chat.complete_async = AsyncMock(side_effect=generate_mock_metadata)

    # Get all module paths that need patching (consolidated helper function)
    patch_targets = _get_mistral_client_patch_targets()

    # Create patches for all targets using ExitStack
    with ExitStack() as stack:
        mock_patches = []
        for target in patch_targets:
            # Use create=True for lazy imports to avoid AttributeError
            needs_create = "__init__" in target or any(
                module in target
                for module in [
                    "synthesis_agent",
                    "enrichment",
                    "hybrid",
                    "ensemble",
                    "timeseries.core",
                    "anomalies",
                    "trends",
                    "recommendations",
                    "proactive_modules",
                    "llm_inference",  # Lazy import inside _call_mistral_api function
                    "_legacy",  # Lazy import in async_batch/_legacy.py
                    "period_classifier",  # Lazy import in classification module (Epic 9)
                ]
            )
            mock_patch = stack.enter_context(patch(target, create=needs_create))
            mock_patch.return_value = mock_client_instance
            mock_patches.append(mock_patch)

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
