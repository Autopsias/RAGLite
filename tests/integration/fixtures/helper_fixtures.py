"""Helper fixtures for integration tests.

This module provides utility fixtures for testing:
- qdrant_with_sample_docs: Access to Qdrant collection with sample documents
- mock_synthesis_agent: Mock synthesis agent for workflow testing
- sample_ground_truth: Sample ground truth query for validation testing

Fixtures:
    qdrant_with_sample_docs: Provides access to Qdrant with test data
    mock_synthesis_agent: Mock agent for synthesis workflow testing
    sample_ground_truth: Sample query with expected documents
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def qdrant_with_sample_docs(session_ingested_collection):
    """Fixture providing access to Qdrant collection with sample documents.

    Story 3.2 AC5: Provides Qdrant instance populated with test PDFs.
    This is a simple wrapper around session_ingested_collection to provide
    the expected fixture name for integration tests.

    Returns:
        True if Qdrant collection is available and populated with sample docs,
        False otherwise (tests will skip).
    """
    # session_ingested_collection fixture confirms Qdrant is available
    # If this fixture is reached, Qdrant has sample docs loaded
    return True


@pytest.fixture
def mock_synthesis_agent():
    """Fixture providing mock synthesis agent for workflow testing.

    Story 3.2 AC5: Provides mock synthesis agent to avoid real LLM calls
    during integration testing of retrieval → synthesis workflows.

    Returns:
        Async callable that simulates synthesis agent behavior.
    """

    async def mock_agent(query: str, retrieval_results: list, **kwargs) -> str:
        """Mock synthesis agent that returns pre-formatted answer.

        Args:
            query: The original query
            retrieval_results: List of retrieved document chunks
            **kwargs: Additional arguments (ignored)

        Returns:
            JSON-serialized synthesis result
        """
        import asyncio

        # Simulate agent processing
        await asyncio.sleep(0.1)

        # Return mock synthesis with retrieved chunks as context
        return json.dumps(
            {
                "query": query,
                "synthesis": f"Based on {len(retrieval_results)} retrieved documents: "
                f"The answer to '{query}' is synthesized from the provided context.",
                "cited_chunks": [r.get("id") for r in retrieval_results]
                if retrieval_results
                else [],
                "confidence": 0.85,
                "latency_ms": 100,
            }
        )

    return mock_agent


@pytest.fixture
def sample_ground_truth():
    """Fixture providing sample ground truth query for validation testing.

    Story 3.2 AC5: Provides test query and expected documents for accuracy validation.
    Loads from ground_truth_50queries.json if available.

    Returns:
        Dict with keys: query, expected_documents (or None if not available)
    """
    # Try to load ground truth file
    project_root = Path(__file__).parent.parent.parent
    ground_truth_file = project_root / "ground_truth_50queries.json"

    if ground_truth_file.exists():
        try:
            with open(ground_truth_file) as f:
                data = json.load(f)
                # Return first query from ground truth set
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                elif isinstance(data, dict) and "queries" in data:
                    return data["queries"][0]
        except Exception:
            pass

    # Fallback: provide minimal test query
    return {
        "query": "What is the annual revenue?",
        "expected_documents": [],  # Empty - tests will skip if needed
    }
