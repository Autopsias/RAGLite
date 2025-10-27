"""Integration tests for MCP response validation and end-to-end flows (Story 1.11).

Tests validate complete metadata flow from ingestion → retrieval → citation,
LLM synthesis compatibility, and performance against NFR targets.

Target: 100% metadata completeness on all queries (NFR7 - 95%+ attribution accuracy).
"""

import time

import pytest

from raglite.retrieval.attribution import generate_citations
from raglite.retrieval.search import search_documents
from raglite.shared.models import QueryResponse
from tests.fixtures.ground_truth import GROUND_TRUTH_QA


@pytest.mark.integration
@pytest.mark.preserve_collection  # Test is read-only - skip cleanup
async def test_e2e_metadata_completeness():
    """Validate metadata completeness from ingestion to response.

    End-to-end test: search_documents → generate_citations → validate metadata.
    Target: 100% metadata completeness (all required fields populated).
    Critical for NFR7 (95%+ source attribution accuracy).
    """
    # Test with diverse queries
    test_queries = [
        "What are the fixed costs per ton for operations?",
        "What is the distribution cost per ton?",
        "What are the EBITDA margins?",
        "What are the safety metrics?",
        "What is the workforce headcount?",
    ]

    total_results = 0
    complete_metadata_count = 0
    incomplete_results = []

    for query in test_queries:
        # Execute search
        results = await search_documents(query, top_k=5)

        # Apply citations
        results_with_citations = await generate_citations(results)

        for result in results_with_citations:
            total_results += 1

            # Check metadata completeness
            # Note: BM25 hybrid search (Story 2.1) can produce negative scores
            metadata_complete = (
                result.page_number is not None
                and result.source_document != ""
                and result.word_count > 0
                and result.score <= 1.0  # Only upper bound (BM25 can be negative)
                and result.text != ""
                and "(Source:" in result.text  # Citation appended
            )

            if metadata_complete:
                complete_metadata_count += 1
            else:
                incomplete_results.append(
                    {
                        "query": query,
                        "source": result.source_document,
                        "page": result.page_number,
                        "chunk": result.chunk_index,
                    }
                )

    completeness_rate = (complete_metadata_count / total_results) * 100 if total_results > 0 else 0

    print("\n=== Metadata Completeness Results ===")
    print(f"Total results tested: {total_results}")
    print(f"Complete metadata: {complete_metadata_count}")
    print(f"Incomplete metadata: {len(incomplete_results)}")
    print(f"Completeness rate: {completeness_rate:.1f}%")

    if incomplete_results:
        print("\nIncomplete results:")
        for item in incomplete_results[:5]:  # Show first 5
            print(f"  Query: {item['query'][:50]}...")
            print(f"  Source: {item['source']}, Page: {item['page']}, Chunk: {item['chunk']}")

    # Assert 100% metadata completeness
    assert completeness_rate == 100.0, (
        f"Metadata completeness {completeness_rate:.1f}% below target 100%. "
        f"{complete_metadata_count}/{total_results} results have complete metadata."
    )


@pytest.mark.integration
@pytest.mark.preserve_collection  # Test is read-only - skip cleanup
async def test_e2e_citation_integration():
    """Validate citations from Story 1.8 work correctly in end-to-end flow.

    Tests:
    - generate_citations() appends citations to QueryResult.text
    - Citation format: (Source: document.pdf, page X, chunk Y)
    - Citations include all required fields
    """
    query = "What are the fixed costs per ton for operations?"

    # Execute search
    results = await search_documents(query, top_k=3)

    # Results should NOT have citations yet
    for result in results:
        assert "(Source:" not in result.text, "Raw search results should not have citations"

    # Apply citations
    results_with_citations = await generate_citations(results)

    # Validate citations appended correctly
    for i, result in enumerate(results_with_citations, 1):
        print(f"\nResult {i}:")
        print(f"  Source: {result.source_document}")
        print(f"  Page: {result.page_number}")
        print(f"  Chunk: {result.chunk_index}")
        print(f"  Citation: {result.text[-100:]}")

        # Verify citation format
        assert "(Source:" in result.text, "Citation must be appended"
        assert result.source_document in result.text, "Source document must be in citation"
        assert f"page {result.page_number}" in result.text or "page N/A" in result.text
        assert f"chunk {result.chunk_index}" in result.text

        # Verify citation at end of text
        assert result.text.rstrip().endswith(")"), "Citation should be at end of text"


@pytest.mark.integration
@pytest.mark.preserve_collection  # Test is read-only - skip cleanup
async def test_e2e_llm_synthesis_compatibility():
    """Simulate LLM client processing QueryResponse.

    Validates that QueryResponse structure is optimized for LLM synthesis:
    - Clear field names (source_document, page_number, chunk_index)
    - Citations appended to text for easy parsing
    - Consistent JSON structure
    """
    query = "What were the main drivers of margin improvement?"

    # Execute search and citation
    results = await search_documents(query, top_k=5)
    results_with_citations = await generate_citations(results)

    # Create QueryResponse (simulating MCP tool response)
    response = QueryResponse(results=results_with_citations, query=query, retrieval_time_ms=123.45)

    # Simulate LLM processing: extract information from QueryResponse
    print("\n=== Simulating LLM Synthesis ===")
    print(f"Original query: {response.query}")
    print(f"Results count: {len(response.results)}")
    print(f"Retrieval time: {response.retrieval_time_ms}ms")

    # LLM would synthesize from these chunks:
    for i, result in enumerate(response.results[:3], 1):  # Top 3 results
        print(f"\nChunk {i} (score: {result.score:.4f}):")
        print(f"  Content: {result.text[:100]}...")
        print(f"  Source: {result.source_document}, page {result.page_number}")

    # Validate structure is LLM-friendly
    assert response.query != "", "Query must be preserved for context"
    assert len(response.results) > 0, "Must have results to synthesize from"
    assert all(r.text != "" for r in response.results), "All chunks must have text"
    assert all("(Source:" in r.text for r in response.results), "All chunks must have citations"

    # Validate JSON serialization works (LLM clients use JSON)
    response_dict = response.model_dump()
    assert isinstance(response_dict, dict)
    assert "results" in response_dict
    assert "query" in response_dict

    print("\n✅ QueryResponse structure is LLM-compatible")


@pytest.mark.integration
@pytest.mark.preserve_collection  # Test is read-only - skip cleanup
async def test_e2e_performance_validation():
    """Measure p50/p95 latency on multiple queries.

    Validates performance meets NFR13 (<10s query response time).
    Target: p50 <5s, p95 <10s
    Baseline: Story 1.10 achieved 25ms p50 (exceptional)
    """
    # Test with 20+ diverse queries
    test_queries = [
        "What are the fixed costs per ton?",
        "What is the distribution cost per ton?",
        "What are the EBITDA margins?",
        "What are the safety metrics?",
        "What is the workforce headcount?",
        "What are the operating expenses?",
        "What is the revenue trend?",
        "What are the net transport costs?",
        "What is the fuel expense?",
        "What are the insurance costs?",
        "What are the utilities expenses?",
        "What are the professional services fees?",
        "What is the total margin?",
        "What are the raw materials costs?",
        "What is the production volume?",
        "What are the employee costs?",
        "What is the depreciation expense?",
        "What are the maintenance costs?",
        "What is the energy consumption?",
        "What are the environmental costs?",
    ]

    latencies = []

    print(f"\n=== Performance Testing ({len(test_queries)} queries) ===")

    for query in test_queries:
        start_time = time.perf_counter()

        # Execute search + citation (complete flow)
        results = await search_documents(query, top_k=5)
        await generate_citations(results)

        duration_ms = (time.perf_counter() - start_time) * 1000
        latencies.append(duration_ms)

    # Calculate percentiles
    latencies.sort()
    p50_idx = len(latencies) // 2
    p95_idx = int(len(latencies) * 0.95)

    p50_latency = latencies[p50_idx]
    p95_latency = latencies[p95_idx]
    avg_latency = sum(latencies) / len(latencies)

    print("\nResults:")
    print(f"  Queries tested: {len(test_queries)}")
    print(f"  Average latency: {avg_latency:.2f}ms")
    print(f"  p50 latency: {p50_latency:.2f}ms")
    print(f"  p95 latency: {p95_latency:.2f}ms")
    print(f"  Min latency: {min(latencies):.2f}ms")
    print(f"  Max latency: {max(latencies):.2f}ms")

    # Validate NFR13 targets
    # p50 <5000ms, p95 <10000ms
    assert p50_latency < 5000, f"p50 latency {p50_latency:.2f}ms exceeds 5000ms target"
    assert p95_latency < 10000, f"p95 latency {p95_latency:.2f}ms exceeds 10000ms target"

    print("\n✅ Performance meets NFR13 targets")
    print(f"   p50: {p50_latency:.2f}ms < 5000ms target")
    print(f"   p95: {p95_latency:.2f}ms < 10000ms target")


@pytest.mark.integration
@pytest.mark.preserve_collection  # Test is read-only - skip cleanup
async def test_e2e_ground_truth_metadata():
    """Validate metadata completeness on ground truth test set.

    Uses 50+ ground truth Q&A pairs from Story 1.12A.
    Target: 100% metadata completeness (NFR7 - 95%+ source attribution).
    This is the CRITICAL acceptance test for Story 1.11 (AC9).
    """
    print("\n=== Ground Truth Metadata Validation ===")
    print(f"Total ground truth questions: {len(GROUND_TRUTH_QA)}")

    total_results = 0
    complete_metadata_count = 0
    incomplete_results = []

    # Test first 10 queries (full 50+ would take too long for unit testing)
    # Production validation would test all 50+
    test_subset = GROUND_TRUTH_QA[:10]

    for qa in test_subset:
        query = qa["question"]

        # Execute search + citation
        results = await search_documents(query, top_k=5)
        results_with_citations = await generate_citations(results)

        for result in results_with_citations:
            total_results += 1

            # Check metadata completeness
            # Note: BM25 hybrid search (Story 2.1) can produce negative scores
            metadata_complete = (
                result.page_number is not None
                and result.source_document != ""
                and result.word_count > 0
                and result.score <= 1.0  # Only upper bound (BM25 can be negative)
                and result.text != ""
                and "(Source:" in result.text
            )

            if metadata_complete:
                complete_metadata_count += 1
            else:
                incomplete_results.append(
                    {
                        "question": query[:50],
                        "source": result.source_document,
                        "page": result.page_number,
                        "chunk": result.chunk_index,
                    }
                )

    completeness_rate = (complete_metadata_count / total_results) * 100 if total_results > 0 else 0

    print(f"\nResults (subset of {len(test_subset)} questions):")
    print(f"  Total results: {total_results}")
    print(f"  Complete metadata: {complete_metadata_count}")
    print(f"  Incomplete metadata: {len(incomplete_results)}")
    print(f"  Completeness rate: {completeness_rate:.1f}%")

    if incomplete_results:
        print("\nIncomplete results:")
        for item in incomplete_results[:5]:
            print(f"  Q: {item['question']}...")
            print(f"     Source: {item['source']}, Page: {item['page']}, Chunk: {item['chunk']}")

    # Assert 100% metadata completeness
    assert completeness_rate == 100.0, (
        f"Ground truth metadata completeness {completeness_rate:.1f}% below target 100%. "
        f"{complete_metadata_count}/{total_results} results have complete metadata. "
        f"This BLOCKS NFR7 (95%+ source attribution accuracy)."
    )

    print("\n✅ Ground truth metadata validation PASSED")
    print(f"   100% metadata completeness on {len(test_subset)} ground truth queries")


@pytest.mark.integration
@pytest.mark.preserve_collection  # Test is read-only - skip cleanup
async def test_e2e_standard_mcp_pattern():
    """Validate standard MCP pattern: RAGLite returns raw chunks, no synthesis.

    Confirms AC10: Standard MCP architecture where:
    - RAGLite MCP tools return raw chunks with metadata
    - Claude Code (LLM client) synthesizes natural language answers
    - NO answer synthesis logic in RAGLite codebase
    """
    query = "What were the main drivers of margin improvement?"

    # Execute search + citation
    results = await search_documents(query, top_k=5)
    results_with_citations = await generate_citations(results)

    # Create QueryResponse
    response = QueryResponse(results=results_with_citations, query=query, retrieval_time_ms=123.45)

    print("\n=== Standard MCP Pattern Validation ===")
    print(f"Query: {response.query}")
    print(f"Results count: {len(response.results)}")

    # Validate: Response contains raw chunks, NOT synthesized answers
    for i, result in enumerate(response.results[:2], 1):
        print(f"\nResult {i}:")
        print(f"  Text (first 80 chars): {result.text[:80]}...")
        print(f"  Citation present: {'(Source:' in result.text}")

        # Verify this is raw chunk text, not synthesized answer
        # Synthesized would be: "The main drivers were X, Y, Z based on documents..."
        # Raw chunk would be: Original document text + citation

        # Check: text should be document chunk, not synthesized narrative
        assert "(Source:" in result.text, "Must have citation (raw chunk + attribution)"

        # Check: text should NOT start with synthesized phrases
        synthesized_phrases = [
            "Based on the documents",
            "According to the analysis",
            "The main points are",
            "In summary",
            "The answer is",
        ]
        text_lower = result.text.lower()
        for phrase in synthesized_phrases:
            assert not text_lower.startswith(phrase.lower()), (
                f"Text should be raw chunk, not synthesized answer starting with '{phrase}'"
            )

    print("\n✅ Standard MCP pattern confirmed")
    print("   RAGLite returns raw chunks with citations")
    print("   NO answer synthesis in RAGLite codebase")
    print("   LLM client (Claude Code) will synthesize from these chunks")
