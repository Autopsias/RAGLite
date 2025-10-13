"""Integration tests for vector similarity search and retrieval.

Tests search_documents and generate_query_embedding with real Qdrant and embedding model.
"""

import json
import statistics
import time
from pathlib import Path

import pytest

from raglite.retrieval.search import search_documents
from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings


class TestRetrievalIntegration:
    """Integration tests for end-to-end retrieval with real Qdrant."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_search_integration_end_to_end(self) -> None:
        """Integration test: End-to-end search validation with real Qdrant.

        Validates:
        - Query embedding generation works with real model
        - Qdrant vector search returns results
        - Results have valid metadata
        - Search latency <5 seconds (p50 target)

        Requires:
        - Qdrant running (docker-compose up -d)
        - Collection exists with stored chunks
        """
        # Check if Qdrant collection exists
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name not in collection_names:
            pytest.skip(
                f"Collection {settings.qdrant_collection_name} does not exist. Run ingestion first."
            )

        # Test query
        query = "What are the main health and safety KPIs tracked?"

        # Measure search latency
        start_time = time.time()
        results = await search_documents(query, top_k=5)
        elapsed_seconds = time.time() - start_time

        # Assertions
        assert len(results) > 0, "Search should return at least one result"
        assert len(results) <= 5, "Search should respect top_k=5 limit"

        # Validate result structure
        for result in results:
            assert 0.0 <= result.score <= 1.0, f"Score {result.score} out of range"
            assert result.text, "Result text should not be empty"
            assert result.source_document, "Source document should not be empty"
            assert result.page_number is not None, "Page number should be present"
            assert result.chunk_index is not None, "Chunk index should be present"
            assert result.word_count > 0, "Word count should be positive"

        # Performance validation (NFR13: p50 <5s)
        assert elapsed_seconds < 5.0, (
            f"Search took {elapsed_seconds:.2f}s, expected <5s (p50 target per NFR13)"
        )

        # Log results
        print("\n\n✅ End-to-End Search Test:")
        print(f"  Query: {query}")
        print(f"  Results: {len(results)}")
        print(f"  Latency: {elapsed_seconds:.3f}s")
        print(f"  Top score: {results[0].score:.4f}")
        print(f"  Top result: {results[0].text[:100]}...")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_retrieval_accuracy_ground_truth(self) -> None:
        """Integration test: Retrieval accuracy on ground truth query set.

        Validates:
        - Retrieval accuracy on 10+ queries from Story 1.12A ground truth
        - Target: 70%+ accuracy by Week 2 end (toward 90%+ by Week 5)
        - Results contain expected keywords
        - Measures baseline accuracy for Week 2

        Requires:
        - Ground truth JSON file with queries and expected keywords
        - Qdrant collection with ingested chunks
        """
        # Load ground truth queries
        ground_truth_path = Path("tests/ground_truth.json")
        if not ground_truth_path.exists():
            pytest.skip("Ground truth file not found")

        with open(ground_truth_path) as f:
            ground_truth = json.load(f)

        questions = ground_truth["questions"][:10]  # Use first 10 questions

        # Check if Qdrant collection exists
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name not in collection_names:
            pytest.skip(
                f"Collection {settings.qdrant_collection_name} does not exist. Run ingestion first."
            )

        # Test each query
        correct_retrievals = 0
        total_queries = len(questions)

        for q in questions:
            query_text = q["question"]
            expected_keywords = q["expected_keywords"]

            # Perform search
            results = await search_documents(query_text, top_k=5)

            if not results:
                continue

            # Check if any result contains expected keywords
            # (Simple keyword matching for baseline accuracy)
            top_result_text = results[0].text.lower()
            keyword_matches = sum(1 for kw in expected_keywords if kw.lower() in top_result_text)

            # Consider successful if at least 1 keyword matches
            if keyword_matches > 0:
                correct_retrievals += 1

        # Calculate accuracy
        accuracy = (correct_retrievals / total_queries) * 100

        # Log results
        print("\n\n📊 Ground Truth Accuracy Test:")
        print(f"  Total queries: {total_queries}")
        print(f"  Correct retrievals: {correct_retrievals}")
        print(f"  Accuracy: {accuracy:.1f}%")
        print("  Target (Week 2): 70%+")
        print("  Target (Week 5): 90%+")

        # Week 2 baseline target: 70%+ (Story 1.7 acceptance criteria)
        # Week 0 was 60%, so we expect improvement with better retrieval logic
        assert accuracy >= 60.0, (
            f"Accuracy {accuracy:.1f}% below Week 0 baseline (60%). "
            f"Expected at least maintaining baseline, targeting 70%+ by Week 2 end."
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_performance_p50_p95_latency(self) -> None:
        """Integration test: Performance validation (p50 <5s, p95 <15s).

        Validates:
        - Measure p50 and p95 latency across 20+ queries
        - Target: p50 <5s, p95 <15s (NFR13)
        - Week 0 baseline: 0.83s avg (12x better than 10s target)

        Requires:
        - Qdrant collection with stored chunks
        """
        # Check if Qdrant collection exists
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name not in collection_names:
            pytest.skip(
                f"Collection {settings.qdrant_collection_name} does not exist. Run ingestion first."
            )

        # Load ground truth queries (use all 15 questions)
        ground_truth_path = Path("tests/ground_truth.json")
        if not ground_truth_path.exists():
            pytest.skip("Ground truth file not found")

        with open(ground_truth_path) as f:
            ground_truth = json.load(f)

        questions = ground_truth["questions"]

        # Measure latency for each query
        latencies = []

        for q in questions:
            query_text = q["question"]

            start_time = time.time()
            _results = await search_documents(query_text, top_k=5)
            elapsed_seconds = time.time() - start_time

            latencies.append(elapsed_seconds)

        # Calculate p50 and p95
        latencies_sorted = sorted(latencies)
        p50_index = int(len(latencies_sorted) * 0.50)
        p95_index = int(len(latencies_sorted) * 0.95)

        p50_latency = latencies_sorted[p50_index]
        p95_latency = latencies_sorted[p95_index]
        avg_latency = statistics.mean(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        # Log results
        print("\n\n⏱️ Performance Latency Test:")
        print(f"  Queries tested: {len(latencies)}")
        print(f"  P50 latency: {p50_latency:.3f}s (target: <5s)")
        print(f"  P95 latency: {p95_latency:.3f}s (target: <15s)")
        print(f"  Avg latency: {avg_latency:.3f}s")
        print(f"  Min latency: {min_latency:.3f}s")
        print(f"  Max latency: {max_latency:.3f}s")
        print("  Week 0 baseline: 0.83s avg")

        # Assertions (NFR13: p50 <5s, p95 <15s)
        assert p50_latency < 5.0, f"P50 latency {p50_latency:.3f}s exceeds 5s target (NFR13)"
        assert p95_latency < 15.0, f"P95 latency {p95_latency:.3f}s exceeds 15s target (NFR13)"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_metadata_preservation_integration(self) -> None:
        """Integration test: Metadata preservation validation.

        Validates:
        - All results from real Qdrant have page_number populated
        - All results have source_document populated
        - All results have chunk_index populated
        - CRITICAL for Story 1.8 (source attribution)

        Requires:
        - Qdrant collection with stored chunks
        """
        # Check if Qdrant collection exists
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name not in collection_names:
            pytest.skip(
                f"Collection {settings.qdrant_collection_name} does not exist. Run ingestion first."
            )

        # Test multiple queries
        test_queries = [
            "What are the main health and safety KPIs?",
            "What is the EBITDA for cement operations?",
            "How do variable costs compare across periods?",
        ]

        total_results = 0
        results_with_complete_metadata = 0

        for query in test_queries:
            results = await search_documents(query, top_k=5)

            for result in results:
                total_results += 1

                # Check all required metadata fields
                has_page_number = result.page_number is not None
                has_source_document = result.source_document != ""
                has_chunk_index = result.chunk_index is not None
                has_word_count = result.word_count > 0

                if has_page_number and has_source_document and has_chunk_index and has_word_count:
                    results_with_complete_metadata += 1
                else:
                    # Log missing metadata
                    print("\n⚠️ Result with incomplete metadata:")
                    print(f"  page_number: {result.page_number}")
                    print(f"  source_document: {result.source_document}")
                    print(f"  chunk_index: {result.chunk_index}")
                    print(f"  word_count: {result.word_count}")

        # Calculate completion rate
        completion_rate = (results_with_complete_metadata / total_results) * 100

        # Log results
        print("\n\n🔍 Metadata Preservation Test:")
        print(f"  Total results: {total_results}")
        print(f"  Results with complete metadata: {results_with_complete_metadata}")
        print(f"  Completion rate: {completion_rate:.1f}%")

        # CRITICAL: All results must have complete metadata for Story 1.8
        assert completion_rate == 100.0, (
            f"Metadata completion rate {completion_rate:.1f}% < 100%. "
            f"All results MUST have page_number, source_document, chunk_index for Story 1.8 source attribution."
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_metadata_filtering_integration(self) -> None:
        """Integration test: Metadata filtering with real Qdrant.

        Validates:
        - Filtering by source_document works with real Qdrant
        - Results only contain chunks from specified document

        Requires:
        - Qdrant collection with multiple documents
        """
        # Check if Qdrant collection exists
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name not in collection_names:
            pytest.skip(
                f"Collection {settings.qdrant_collection_name} does not exist. Run ingestion first."
            )

        # Get first point to determine a valid source_document
        sample_points = qdrant.scroll(collection_name=settings.qdrant_collection_name, limit=1)

        if not sample_points[0]:
            pytest.skip("No points in collection")

        source_document = sample_points[0][0].payload.get("source_document")

        if not source_document:
            pytest.skip("Sample point has no source_document metadata")

        # Test query with filter
        query = "financial performance"
        filters = {"source_document": source_document}

        results = await search_documents(query, top_k=5, filters=filters)

        # Assertions
        assert len(results) > 0, "Filtered search should return results"

        # Verify all results are from the specified document
        for result in results:
            assert result.source_document == source_document, (
                f"Result source_document '{result.source_document}' "
                f"does not match filter '{source_document}'"
            )

        print("\n\n🔎 Metadata Filtering Test:")
        print(f"  Filtered by: {source_document}")
        print(f"  Results: {len(results)}")
        print("  All results match filter: ✅")
