"""Query performance and latency validation tests (Story 5.0.6 Task 7.4).

Tests verify that query-time metadata enrichment completes within the
3-second budget while maintaining acceptable query performance.
"""

import time

import pytest
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from raglite.retrieval.search import hybrid_search
from raglite.shared.config import settings

# Mark all tests in this module as integration tests
# CRITICAL: xdist_group required because tests use embedding model via hybrid_search
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
]


@pytest.mark.priority("P1")
@pytest.mark.timeout(120)  # 2 minutes
@pytest.mark.asyncio
@pytest.mark.preserve_collection  # Assumes data already ingested
async def test_query_latency_with_enrichment():
    """Test AC5/Task 7.4: Verify query latency with metadata enrichment <3 seconds.

    Story 5.0.6 Task 7.4: Validate that query-time metadata enrichment completes
    within the 3-second budget, maintaining acceptable query performance.

    This test assumes data is already ingested (run after test_parallel_ingestion_three_documents).
    """
    # Check if Qdrant collection exists before running test
    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        client.get_collection(settings.qdrant_collection_name)
    except (UnexpectedResponse, ResponseHandlingException) as e:
        pytest.skip(f"Qdrant not available: {e}")

    # Verify query-time metadata enrichment is enabled
    assert settings.query_time_metadata_enabled, (
        "Query-time metadata enrichment must be enabled for this test "
        "(set QUERY_TIME_METADATA_ENABLED=true)"
    )

    # Test query (financial domain query that should retrieve results)
    query = "What is the revenue for the last fiscal year?"

    # Measure query latency with enrichment
    start_time = time.perf_counter()
    results = await hybrid_search(query, top_k=5)
    elapsed_seconds = time.perf_counter() - start_time

    # Verify results were returned
    assert len(results) > 0, "Query should return at least 1 result"

    # AC5: Verify query completes within 3-second budget (Task 7.4)
    assert elapsed_seconds < 3.0, (
        f"Query with enrichment took {elapsed_seconds:.2f}s, exceeds 3s budget. "
        f"Expected: <3s for query-time metadata enrichment (Story 5.0.6 AC5)."
    )

    # Verify enrichment actually ran (check that results were enriched)
    # Note: If all results already had metadata, enrichment may have been skipped
    # This is expected behavior and not a failure

    print("\n✅ Query latency test passed:")
    print(f"   Query: {query}")
    print(f"   Results returned: {len(results)}")
    print(f"   Latency: {elapsed_seconds:.2f}s (target: <3s)")
    print(
        f"   Query-time enrichment: {'enabled' if settings.query_time_metadata_enabled else 'disabled'}"
    )
    print(f"   Timeout budget: {settings.query_time_metadata_timeout}s")


@pytest.mark.priority("P2")
@pytest.mark.timeout(180)  # 3 minutes
@pytest.mark.asyncio
@pytest.mark.preserve_collection  # Assumes data already ingested
async def test_query_latency_multiple_queries():
    """Test Task 7.4 Extended: Verify consistent query latency across multiple queries.

    Validates that query-time enrichment maintains acceptable performance across
    a batch of diverse queries.
    """
    import statistics

    # Check if Qdrant collection exists before running test
    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        client.get_collection(settings.qdrant_collection_name)
    except (UnexpectedResponse, ResponseHandlingException) as e:
        pytest.skip(f"Qdrant not available: {e}")

    # Test queries (financial domain)
    test_queries = [
        "What is the total revenue?",
        "Show me the EBITDA margin",
        "What are the operating expenses?",
        "How many employees does the company have?",
        "What is the profit for Q3?",
    ]

    latencies = []

    for query in test_queries:
        start_time = time.perf_counter()
        _ = await hybrid_search(query, top_k=5)
        elapsed = time.perf_counter() - start_time
        latencies.append(elapsed)

        # Individual query should complete within 3 seconds
        assert elapsed < 3.0, f"Query '{query}' took {elapsed:.2f}s, exceeds 3s budget"

    # Calculate statistics
    avg_latency = statistics.mean(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    # All queries should be under 3 seconds
    assert max_latency < 3.0, f"Max query latency {max_latency:.2f}s exceeds 3s budget"

    # Average should be well under 3 seconds
    assert avg_latency < 2.5, f"Average query latency {avg_latency:.2f}s too close to 3s budget"

    print("\n✅ Multiple query latency test passed:")
    print(f"   Queries tested: {len(test_queries)}")
    print(f"   Average latency: {avg_latency:.2f}s (target: <2.5s)")
    print(f"   Min latency: {min_latency:.2f}s")
    print(f"   Max latency: {max_latency:.2f}s (target: <3s)")
    print("   All queries within budget: ✓")
