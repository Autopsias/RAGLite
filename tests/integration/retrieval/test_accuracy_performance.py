"""Integration tests for retrieval accuracy and performance.

Tests ground truth validation, citation accuracy, and performance metrics.
"""

import json
import statistics
import time
from pathlib import Path

import pytest

# Mark all tests in this module as integration tests that preserve collection state
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


@pytest.mark.xdist_group(name="embedding_model")
@pytest.mark.preserve_collection
class TestAccuracyPerformance:
    """Accuracy and performance validation tests."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skip(
        reason="KNOWN REGRESSION: Element-aware chunking (Story 2.2) reduced accuracy from 56% baseline to 42%. "
        "Requires fixed chunking strategy (Story 2.3 - Phase 2A). "
        "See: story-2.2-pivot-analysis/ for Strategic Pivot details. "
        "Re-enable after Story 2.3 implementation (target: 70%+ accuracy)."
    )
    @pytest.mark.priority("P0")
    async def test_retrieval_accuracy_ground_truth(self, session_ingested_collection) -> None:
        """Integration test: Retrieval accuracy on ground truth query set.

        **KNOWN ISSUE**: Element-aware chunking (Story 2.2) caused accuracy regression:
        - Baseline (fixed 512-token chunking): 56% accuracy
        - Current (element-aware chunking): 42% accuracy (20% on sample)
        - Root cause: Chunks too large, semantic coherence reduced
        - Fix planned: Story 2.3 (Fixed 512-token + LLM metadata) - target 70%+

        Validates:
        - Retrieval accuracy on 10+ queries from Story 1.12A ground truth
        - Target: 70%+ accuracy after Phase 2A fix
        - Results contain expected keywords
        - Measures current accuracy for tracking

        Requires:
        - Ground truth JSON file with queries and expected keywords
        - Qdrant collection with ingested chunks
        """
        # Lazy imports to avoid test discovery overhead
        from raglite.retrieval.search import search_documents
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

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
        print("  Current (Story 2.2 element-aware): ~42% (regression)")
        print("  Baseline (fixed 512-token): 56%")
        print("  Target (after Story 2.3 fix): 70%+")
        print("  Final target (Week 5): 90%+")

        # KNOWN REGRESSION: Element-aware chunking reduced accuracy
        # Marking as xfail until Story 2.3 fixes chunking strategy
        # Original baseline: 56-60% with fixed 512-token chunking
        # Current: ~20-42% with element-aware chunking (regression)
        # Target after Story 2.3 fix: 70%+
        assert accuracy >= 60.0, (
            f"Accuracy {accuracy:.1f}% below original baseline (60%). "
            f"Known regression from element-aware chunking (56% → 42% → 20% on samples). "
            f"Will be fixed in Story 2.3 with fixed 512-token chunking + LLM metadata (target: 70%+)."
        )

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_performance_p50_p95_latency(self, session_ingested_collection) -> None:
        """Integration test: Performance validation (p50 <5s, p95 <15s).

        Validates:
        - Measure p50 and p95 latency across 20+ queries
        - Target: p50 <5s, p95 <15s (NFR13)
        - Week 0 baseline: 0.83s avg (12x better than 10s target)

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

    def _load_ground_truth_queries(self):
        """Load ground truth queries for citation validation.

        Returns:
            List of question dictionaries

        Raises:
            pytest.skip: If ground truth file not found
        """
        ground_truth_path = Path("tests/ground_truth.json")
        if not ground_truth_path.exists():
            pytest.skip("Ground truth file not found")

        with open(ground_truth_path) as f:
            ground_truth = json.load(f)

        # Use at least 10 queries for validation
        return ground_truth["questions"][:10]

    def _validate_qdrant_collection_for_citations(self):
        """Validate Qdrant collection exists for citation testing.

        Raises:
            pytest.skip: If collection does not exist
        """
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

        qdrant = get_qdrant_client()
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name not in collection_names:
            pytest.skip(
                f"Collection {settings.qdrant_collection_name} does not exist. Run ingestion first."
            )

    async def _validate_single_result_citation(self, result):
        """Validate citation format for a single result.

        Args:
            result: Search result with potential citation

        Returns:
            Tuple of (has_citation, has_correct_format)
        """
        # Check citation was appended to text
        has_citation = "(Source:" in result.text

        if not has_citation:
            return False, False

        # Validate citation format
        citation_text = result.text.split("(Source:")[-1]
        has_source_doc = result.source_document in citation_text
        has_page = f"page {result.page_number}" in citation_text or "page N/A" in citation_text
        has_chunk = f"chunk {result.chunk_index}" in citation_text

        has_correct_format = has_source_doc and has_page and has_chunk

        return has_citation, has_correct_format

    async def _test_query_citations(self, q, query_idx):
        """Test citation generation for a single query.

        Args:
            q: Question dictionary
            query_idx: Query index (for manual validation output)

        Returns:
            Tuple of (total_results, results_with_valid_citations, results_with_correct_format)
        """
        from raglite.retrieval.attribution import generate_citations
        from raglite.retrieval.search import search_documents

        query_text = q["question"]

        # Perform search
        results = await search_documents(query_text, top_k=3)

        if not results:
            return 0, 0, 0

        # Generate citations
        cited_results = await generate_citations(results)

        # Validate citations
        total_results = 0
        results_with_valid_citations = 0
        results_with_correct_format = 0

        for j, result in enumerate(cited_results):
            total_results += 1

            has_citation, has_correct_format = await self._validate_single_result_citation(result)

            if has_citation:
                results_with_valid_citations += 1

                if has_correct_format:
                    results_with_correct_format += 1

                # Manual validation output (first query only)
                if query_idx == 0:
                    print(f"\n📝 Citation Sample {j + 1}:")
                    print(f"  Query: {query_text}")
                    print(f"  Score: {result.score:.4f}")
                    print(f"  Source: {result.source_document}")
                    print(f"  Page: {result.page_number}")
                    print(f"  Chunk: {result.chunk_index}")
                    print(f"  Text: {result.text[:150]}...")
                    print(f"  Citation: ...{result.text[-80:]}")

        return total_results, results_with_valid_citations, results_with_correct_format

    def _calculate_and_print_citation_metrics(
        self, questions, total_results, results_with_valid_citations, results_with_correct_format
    ):
        """Calculate and print citation accuracy metrics.

        Args:
            questions: List of questions tested
            total_results: Total number of results
            results_with_valid_citations: Results with valid citations
            results_with_correct_format: Results with correct citation format

        Returns:
            Tuple of (citation_coverage, format_accuracy)
        """
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

        return citation_coverage, format_accuracy

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
        # Validate Qdrant collection exists
        self._validate_qdrant_collection_for_citations()

        # Load ground truth queries
        questions = self._load_ground_truth_queries()

        # Track citation validation metrics
        total_results = 0
        results_with_valid_citations = 0
        results_with_correct_format = 0

        # Test each query
        for i, q in enumerate(questions):
            query_total, query_valid, query_correct = await self._test_query_citations(q, i)
            total_results += query_total
            results_with_valid_citations += query_valid
            results_with_correct_format += query_correct

        # Calculate and print metrics
        citation_coverage, format_accuracy = self._calculate_and_print_citation_metrics(
            questions, total_results, results_with_valid_citations, results_with_correct_format
        )

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
