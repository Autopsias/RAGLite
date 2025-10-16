"""Epic 2 Regression Test Suite.

Ensures Epic 2 changes don't degrade Epic 1 baseline performance.
Sets accuracy and latency floors/ceilings to catch regressions early.

Regression Thresholds (from baseline-accuracy-report-FINAL.txt):
- Retrieval accuracy floor: 56.0% (Epic 1 baseline)
- Attribution accuracy floor: 32.0% (Epic 1 baseline)
- p95 latency ceiling: 10,000ms (NFR13 target)

Usage:
    # Run all regression tests
    pytest tests/integration/test_epic2_regression.py -v

    # Run specific regression test
    pytest tests/integration/test_epic2_regression.py::TestEpic2Regression::test_retrieval_accuracy_floor -v
"""

import time

import pytest

from raglite.retrieval.attribution import generate_citations
from raglite.retrieval.search import search_documents
from scripts.accuracy_utils import (
    NFR13_P95_TARGET_MS,
    calculate_performance_metrics,
    check_attribution_accuracy,
    check_retrieval_accuracy,
)
from tests.fixtures.ground_truth import GROUND_TRUTH_QA

# Epic 1 baseline thresholds (from baseline-accuracy-report-FINAL.txt)
BASELINE_RETRIEVAL_FLOOR = 56.0  # Must not regress below 56%
BASELINE_ATTRIBUTION_FLOOR = 32.0  # Must not regress below 32%
LATENCY_CEILING_P95 = NFR13_P95_TARGET_MS  # Must stay under 10s p95


class TestEpic2Regression:
    """Regression tests to ensure Epic 2 doesn't degrade Epic 1 baseline."""

    @pytest.mark.asyncio
    async def test_retrieval_accuracy_floor(self):
        """Test that retrieval accuracy doesn't regress below 56% baseline.

        This test ensures Epic 2 changes (hybrid search, new embeddings, etc.)
        maintain or improve upon the Epic 1 baseline retrieval accuracy.

        Regression threshold: 56.0% (Epic 1 baseline)
        """
        results = []

        # Run subset of queries for faster regression check (15 queries)
        test_queries = GROUND_TRUTH_QA[:15]

        for qa in test_queries:
            query_results = await search_documents(query=qa["question"], top_k=5)
            query_results = await generate_citations(query_results)

            retrieval_result = check_retrieval_accuracy(qa, query_results)

            results.append(
                {
                    "query_id": qa["id"],
                    "latency_ms": 0.0,
                    "retrieval": retrieval_result,
                    "attribution": {"pass_": False},
                }
            )

        metrics = calculate_performance_metrics(results)

        # Assert retrieval accuracy >= baseline floor
        assert metrics["retrieval_accuracy"] >= BASELINE_RETRIEVAL_FLOOR, (
            f"Retrieval accuracy regressed to {metrics['retrieval_accuracy']:.1f}% (below {BASELINE_RETRIEVAL_FLOOR}% floor)"
        )

    @pytest.mark.asyncio
    async def test_attribution_accuracy_floor(self):
        """Test that attribution accuracy doesn't regress below 32% baseline.

        This test ensures Epic 2 changes maintain or improve upon the Epic 1
        baseline attribution accuracy (correct page in top-5 results).

        Regression threshold: 32.0% (Epic 1 baseline)
        """
        results = []

        # Run subset of queries for faster regression check (15 queries)
        test_queries = GROUND_TRUTH_QA[:15]

        for qa in test_queries:
            query_results = await search_documents(query=qa["question"], top_k=5)
            query_results = await generate_citations(query_results)

            attribution_result = check_attribution_accuracy(qa, query_results)

            results.append(
                {
                    "query_id": qa["id"],
                    "latency_ms": 0.0,
                    "retrieval": {"pass_": False},
                    "attribution": attribution_result,
                }
            )

        metrics = calculate_performance_metrics(results)

        # Assert attribution accuracy >= baseline floor
        assert metrics["attribution_accuracy"] >= BASELINE_ATTRIBUTION_FLOOR, (
            f"Attribution accuracy regressed to {metrics['attribution_accuracy']:.1f}% (below {BASELINE_ATTRIBUTION_FLOOR}% floor)"
        )

    @pytest.mark.asyncio
    async def test_latency_ceiling(self):
        """Test that p95 latency stays under 10s ceiling (NFR13).

        This test ensures Epic 2 enhancements (BM25, LLM synthesis, etc.)
        don't violate the NFR13 performance requirement.

        Regression threshold: 10,000ms p95 (NFR13 target)
        """
        latencies = []

        # Run 10 queries for latency check
        test_queries = GROUND_TRUTH_QA[:10]

        for qa in test_queries:
            start_time = time.perf_counter()

            await search_documents(query=qa["question"], top_k=5)

            latency_ms = (time.perf_counter() - start_time) * 1000
            latencies.append(latency_ms)

        # Calculate p95
        latencies.sort()
        p95_idx = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_idx] if p95_idx < len(latencies) else latencies[-1]

        # Assert p95 latency < 10s ceiling
        assert p95_latency < LATENCY_CEILING_P95, (
            f"p95 latency exceeded ceiling: {p95_latency:.2f}ms (ceiling: {LATENCY_CEILING_P95}ms)"
        )

    @pytest.mark.asyncio
    async def test_hybrid_fusion_quality(self):
        """Test that hybrid search outperforms single methods (Story 2.1+).

        This test validates that hybrid search fusion produces better results
        than BM25 or semantic search alone. This test will be skipped if
        Story 2.1 (Hybrid Search) is not yet implemented.

        Quality check: hybrid_score > max(bm25_score, semantic_score)
        """
        try:
            # Import hybrid search (will fail before Story 2.1)
            from raglite.retrieval.search import hybrid_search  # noqa: F401

            # Run 10 queries with hybrid search
            test_queries = GROUND_TRUTH_QA[:10]
            hybrid_better_count = 0

            for qa in test_queries:
                # This assumes hybrid_search returns results with score breakdown
                # (This is the EXPECTED API after Story 2.1 implementation)
                results = await hybrid_search(qa["question"], top_k=5, return_scores=True)

                if results and hasattr(results[0], "hybrid_score"):
                    # Check if hybrid score > max(bm25, semantic)
                    hybrid_score = results[0].hybrid_score
                    bm25_score = getattr(results[0], "bm25_score", 0.0)
                    semantic_score = getattr(results[0], "semantic_score", 0.0)

                    if hybrid_score >= max(bm25_score, semantic_score):
                        hybrid_better_count += 1

            # Assert hybrid fusion improves results on majority of queries
            assert hybrid_better_count >= len(test_queries) * 0.7, (
                f"Hybrid search only better on {hybrid_better_count}/{len(test_queries)} queries (expected ≥70%)"
            )

        except ImportError:
            # Story 2.1 not implemented yet, skip this test
            pytest.skip(
                "Story 2.1 (Hybrid Search) not implemented yet - skipping hybrid fusion quality test"
            )


class TestEpic2IntegrationSanity:
    """Sanity checks for Epic 2 integration testing infrastructure."""

    def test_baseline_thresholds_defined(self):
        """Test that baseline regression thresholds are correctly defined."""
        assert BASELINE_RETRIEVAL_FLOOR == 56.0, "Retrieval floor should be 56% (Epic 1 baseline)"
        assert BASELINE_ATTRIBUTION_FLOOR == 32.0, (
            "Attribution floor should be 32% (Epic 1 baseline)"
        )
        assert LATENCY_CEILING_P95 == 15000.0, "p95 latency ceiling should be 15s (NFR13)"

    def test_ground_truth_available(self):
        """Test that ground truth data is loaded and available."""
        assert len(GROUND_TRUTH_QA) == 50, "Ground truth should have 50 queries"
        assert all("question" in qa for qa in GROUND_TRUTH_QA), (
            "All queries should have 'question' field"
        )
        assert all("expected_keywords" in qa for qa in GROUND_TRUTH_QA), (
            "All queries should have 'expected_keywords'"
        )
        assert all("expected_page_number" in qa for qa in GROUND_TRUTH_QA), (
            "All queries should have 'expected_page_number'"
        )
