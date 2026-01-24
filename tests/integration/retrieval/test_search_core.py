"""Integration tests for core search functionality.

Tests search_documents and generate_query_embedding with real Qdrant and embedding model.

Performance Optimization:
- Lazy imports: Expensive modules (raglite.retrieval.*, raglite.shared.*) imported inside test functions
  to avoid 6+ second import overhead during test discovery (critical for test explorers)
"""

import time

import pytest

# Mark all tests in this module as integration tests that preserve collection state
# xdist_group ensures all embedding model tests run on the same worker (prevents 4x model load)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="embedding_model"),
]

# Lazy imports for expensive modules - DO NOT import raglite modules at module level!
# Test explorers (VS Code) run discovery multiple times causing 30+ second delays.
# Import inside test functions instead:
#   from raglite.retrieval.search import search_documents
#   from raglite.retrieval.attribution import generate_citations
#   from raglite.shared.clients import get_qdrant_client
#   from raglite.shared.config import settings


@pytest.mark.xdist_group(name="embedding_model")
@pytest.mark.preserve_collection  # Tests are read-only - skip expensive Qdrant cleanup
class TestSearchCore:
    """Core search integration tests with real Qdrant.

    Note: Tests in this class load the embedding model (3s overhead).
    The @pytest.mark.xdist_group ensures all tests run in the same worker
    to avoid multiple model loads during parallel execution.
    """

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_integration_end_to_end(self, session_ingested_collection) -> None:
        """Integration test: End-to-end search validation with real Qdrant.

        Validates:
        - Query embedding generation works with real model
        - Qdrant vector search returns results
        - Results have valid metadata
        - Search latency <5 seconds (p50 target)

        Requires:
        - Qdrant running (docker-compose up -d)
        - Collection exists with stored chunks (via session_ingested_collection fixture)
        """
        # Lazy imports to avoid test discovery overhead
        from raglite.retrieval.search import search_documents
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

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

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_metadata_preservation_integration(self, session_ingested_collection) -> None:
        """Integration test: Metadata preservation validation.

        Validates:
        - All results from real Qdrant have page_number populated
        - All results have source_document populated
        - All results have chunk_index populated
        - CRITICAL for Story 1.8 (source attribution)

        Requires:
        - Qdrant collection with stored chunks
        """
        # Lazy imports to avoid test discovery overhead
        from raglite.retrieval.search import search_documents
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

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

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_metadata_filtering_integration(self, session_ingested_collection) -> None:
        """Integration test: Metadata filtering with real Qdrant.

        Validates:
        - Filtering by source_document works with real Qdrant
        - Results only contain chunks from specified document

        Requires:
        - Qdrant collection with multiple documents
        """
        # Lazy imports to avoid test discovery overhead
        from raglite.retrieval.search import search_documents
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

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
