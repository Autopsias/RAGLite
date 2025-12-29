"""Integration tests for vector similarity search and retrieval - Extended tests.

Tests metadata preservation, filtering, and citation accuracy with real Qdrant.

Performance Optimization:
- Lazy imports: Expensive modules (raglite.retrieval.*, raglite.shared.*) imported inside test functions
  to avoid 6+ second import overhead during test discovery (critical for test explorers)
"""

import json
from pathlib import Path

import pytest

# Mark all tests in this module as integration tests that preserve collection state
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]

# Lazy imports for expensive modules - DO NOT import raglite modules at module level!
# Test explorers (VS Code) run discovery multiple times causing 30+ second delays.
# Import inside test functions instead:
#   from raglite.retrieval.search import search_documents
#   from raglite.retrieval.attribution import generate_citations
#   from raglite.shared.clients import get_qdrant_client
#   from raglite.shared.config import settings


@pytest.mark.xdist_group(name="embedding_model")
@pytest.mark.preserve_collection  # Tests are read-only - skip expensive Qdrant cleanup
class TestRetrievalExtended:
    """Integration tests for metadata preservation and citation accuracy.

    Note: Tests in this class load the embedding model (3s overhead).
    The @pytest.mark.xdist_group ensures all tests run in the same worker
    to avoid multiple model loads during parallel execution.
    """

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

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_citation_accuracy_integration(self, session_ingested_collection) -> None:
        """Integration test: Citation accuracy validation (Story 1.8).

        Validates:
        - Citations generated for all retrieved chunks
        - Citation format matches spec: "(Source: doc.pdf, page 12, chunk 5)"
        - Citations point to correct document locations
        - Manual validation on 10+ queries from ground truth set
        - Source attribution accuracy 95%+ (NFR7)

        Requires:
        - Ground truth JSON file with queries
        - Qdrant collection with ingested chunks
        - Week 0 test PDF with known page numbers

        Manual Validation:
        - Review output to verify citations point to correct pages
        - Check that citations enable users to find original text
        """
        # Lazy imports to avoid test discovery overhead
        from raglite.retrieval.attribution import generate_citations
        from raglite.retrieval.search import search_documents
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

        # Load ground truth queries
        ground_truth_path = Path("tests/ground_truth.json")
        if not ground_truth_path.exists():
            pytest.skip("Ground truth file not found")

        with open(ground_truth_path) as f:
            ground_truth = json.load(f)

        # Use at least 10 queries for validation
        questions = ground_truth["questions"][:10]

        # Check if Qdrant collection exists
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name not in collection_names:
            pytest.skip(
                f"Collection {settings.qdrant_collection_name} does not exist. Run ingestion first."
            )

        # Track citation validation metrics
        total_results = 0
        results_with_valid_citations = 0
        results_with_correct_format = 0

        # Test each query
        for i, q in enumerate(questions):
            query_text = q["question"]

            # Perform search
            results = await search_documents(query_text, top_k=3)

            if not results:
                continue

            # Generate citations
            cited_results = await generate_citations(results)

            # Validate citations
            for j, result in enumerate(cited_results):
                total_results += 1

                # Check citation was appended to text
                has_citation = "(Source:" in result.text

                if has_citation:
                    results_with_valid_citations += 1

                    # Validate citation format
                    citation_text = result.text.split("(Source:")[-1]
                    has_source_doc = result.source_document in citation_text
                    has_page = (
                        f"page {result.page_number}" in citation_text or "page N/A" in citation_text
                    )
                    has_chunk = f"chunk {result.chunk_index}" in citation_text

                    if has_source_doc and has_page and has_chunk:
                        results_with_correct_format += 1

                    # Manual validation output (first query only)
                    if i == 0:
                        print(f"\n📝 Citation Sample {j + 1}:")
                        print(f"  Query: {query_text}")
                        print(f"  Score: {result.score:.4f}")
                        print(f"  Source: {result.source_document}")
                        print(f"  Page: {result.page_number}")
                        print(f"  Chunk: {result.chunk_index}")
                        print(f"  Text: {result.text[:150]}...")
                        print(f"  Citation: ...{result.text[-80:]}")

        # Calculate metrics
        citation_coverage = (
            (results_with_valid_citations / total_results) * 100 if total_results > 0 else 0
        )
        format_accuracy = (
            (results_with_correct_format / total_results) * 100 if total_results > 0 else 0
        )

        # Log results
        print("\n\n📊 Citation Accuracy Test (Story 1.8):")
        print(f"  Queries tested: {len(questions)}")
        print(f"  Total results: {total_results}")
        print(f"  Results with citations: {results_with_valid_citations}")
        print(f"  Citation coverage: {citation_coverage:.1f}%")
        print(f"  Results with correct format: {results_with_correct_format}")
        print(f"  Format accuracy: {format_accuracy:.1f}%")
        print("  Target (NFR7): 95%+ source attribution accuracy")
        print("  Target (NFR11): 100% citation coverage")

        # Assertions (NFR7: 95%+ attribution accuracy, NFR11: 100% coverage)
        assert citation_coverage == 100.0, (
            f"Citation coverage {citation_coverage:.1f}% < 100%. "
            f"All results MUST have citations (NFR11)."
        )

        assert format_accuracy >= 95.0, (
            f"Citation format accuracy {format_accuracy:.1f}% < 95%. "
            f"Citations must correctly reference source document, page, and chunk (NFR7)."
        )

        print("\n✅ Citation accuracy test PASSED!")
        print(
            "   Manual validation recommended: Review citations point to correct pages in source PDFs."
        )
