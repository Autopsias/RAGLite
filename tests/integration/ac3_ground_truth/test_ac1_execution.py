"""AC1: Full Ground Truth Execution Test.

This module executes all 50 ground truth queries to measure retrieval and attribution
accuracy for Epic 2 Phase 2A completion (Stories 2.3 + 2.4 implemented).
"""

import json
import time
from pathlib import Path

import pytest

from raglite.retrieval.search import hybrid_search
from tests.fixtures.ground_truth import GROUND_TRUTH_QA
from tests.integration.ac3_ground_truth.models import AccuracyMetrics, QueryValidationResult


@pytest.mark.priority("P0")
@pytest.mark.slow
@pytest.mark.skipif(
    not getattr(pytest, "run_slow", False),
    reason="Requires full 160-page PDF. Run with: pytest --run-slow",
)
@pytest.mark.timeout(600)  # 10 minutes - 50 queries × ~10 seconds each + overhead
@pytest.mark.asyncio
async def test_ac1_full_ground_truth_execution() -> AccuracyMetrics:
    """AC1: Execute all 50 ground truth queries and measure retrieval/attribution accuracy.

    NOTE: This test requires the full 160-page PDF (2025-08 Performance Review CONSO_v2.pdf).
    Run with: pytest --run-slow

    Test Structure:
        - 50 ground truth queries from tests/fixtures/ground_truth.py
        - Each query executed via hybrid_search (BM25 + semantic, alpha=0.7)
        - Measure: retrieval accuracy (correct chunk in top-5)
        - Measure: attribution accuracy (correct document + page)
        - Measure: query latency (for AC6 performance validation)

    Expected Results:
        - Retrieval accuracy: 70-75% (35-37.5 / 50 queries pass)
        - Attribution accuracy: ≥95% (NFR7 compliance)
        - Average latency: <5s (target for user experience)

    Returns:
        AccuracyMetrics object with detailed results for AC2/AC3 validation
    """
    print("\n" + "=" * 80)
    print("STORY 2.5 AC1: Full Ground Truth Execution (50 queries)")
    print("=" * 80)
    print(f"Total queries: {len(GROUND_TRUTH_QA)}")
    print("Expected retrieval accuracy: 70-75% (Story 2.3 + 2.4)")
    print("Expected attribution accuracy: ≥95% (NFR7)")
    print("=" * 80 + "\n")

    results: list[QueryValidationResult] = []
    latencies: list[float] = []

    for idx, query_data in enumerate(GROUND_TRUTH_QA, start=1):
        # Cast to GroundTruthQuestion for type safety
        query = query_data  # type: ignore[assignment]

        print(f"\n[{idx}/50] Query ID {query['id']}: {query['question'][:80]}...")

        # Execute hybrid search with timing
        start_time = time.time()
        try:
            search_results = await hybrid_search(
                query=query["question"],
                top_k=5,  # AC1 requirement: top-5 validation
                alpha=0.7,  # 70% semantic, 30% BM25 (Story 2.1 default)
                enable_hybrid=True,
            )
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
            # Record as failure with 0 results
            elapsed_ms = (time.time() - start_time) * 1000
            results.append(
                QueryValidationResult(
                    query_id=query["id"],
                    question=query["question"],
                    retrieval_success=False,
                    attribution_success=False,
                    top_5_chunks=[],
                    latency_ms=elapsed_ms,
                    top_score=0.0,
                    expected_page=query["expected_page_number"],
                    expected_document=query["source_document"],
                )
            )
            latencies.append(elapsed_ms)
            continue

        elapsed_ms = (time.time() - start_time) * 1000
        latencies.append(elapsed_ms)

        # Extract top-5 chunk metadata for validation
        top_5_chunks = [
            (
                result.source_document,
                result.page_number,
                result.chunk_index,
            )
            for result in search_results
        ]

        # Validate retrieval (correct chunk in top-5)
        # Note: We don't have chunk_id in GroundTruthQuestion, so we validate by page_number
        # This is acceptable for Story 2.5 because:
        # 1. Each page typically has 1-3 chunks (fixed 512-token chunking)
        # 2. If correct page is retrieved, retrieval is considered successful
        retrieval_success = any(
            result.page_number == query["expected_page_number"]
            and result.source_document == query["source_document"]
            for result in search_results
        )

        # Validate attribution (correct document + page in top-5)
        attribution_success = any(
            result.source_document == query["source_document"]
            and result.page_number == query["expected_page_number"]
            for result in search_results
        )

        # Determine top score
        top_score = search_results[0].score if search_results else 0.0

        # Store result
        result_obj = QueryValidationResult(
            query_id=query["id"],
            question=query["question"],
            retrieval_success=retrieval_success,
            attribution_success=attribution_success,
            top_5_chunks=top_5_chunks,
            latency_ms=elapsed_ms,
            top_score=top_score,
            expected_page=query["expected_page_number"],
            expected_document=query["source_document"],
        )
        results.append(result_obj)

        # Print result
        if retrieval_success:
            print(
                f"   ✅ PASS (page {query['expected_page_number']} found, score={top_score:.3f}, {elapsed_ms:.0f}ms)"
            )
        else:
            print(
                f"   ❌ FAIL (page {query['expected_page_number']} not in top-5, score={top_score:.3f}, {elapsed_ms:.0f}ms)"
            )
            print(f"      Retrieved pages: {[p for _, p, _ in top_5_chunks]}")

    # Calculate accuracy metrics
    retrieval_accuracy = (sum(r.retrieval_success for r in results) / len(results)) * 100
    attribution_accuracy = (sum(r.attribution_success for r in results) / len(results)) * 100
    successful_queries = sum(r.retrieval_success for r in results)
    failed_queries = [r for r in results if not r.retrieval_success]

    # Calculate latency distribution
    latencies_sorted = sorted(latencies)
    average_latency_ms = sum(latencies) / len(latencies)
    p50_latency_ms = latencies_sorted[int(len(latencies) * 0.50)]
    p95_latency_ms = latencies_sorted[int(len(latencies) * 0.95)]
    p99_latency_ms = latencies_sorted[int(len(latencies) * 0.99)]

    metrics = AccuracyMetrics(
        retrieval_accuracy=retrieval_accuracy,
        attribution_accuracy=attribution_accuracy,
        total_queries=len(results),
        successful_queries=successful_queries,
        failed_queries=failed_queries,
        average_latency_ms=average_latency_ms,
        p50_latency_ms=p50_latency_ms,
        p95_latency_ms=p95_latency_ms,
        p99_latency_ms=p99_latency_ms,
    )

    # Print summary
    print("\n" + "=" * 80)
    print("AC1 RESULTS SUMMARY")
    print("=" * 80)
    print(f"Retrieval Accuracy:    {retrieval_accuracy:.1f}% ({successful_queries}/50)")
    print(f"Attribution Accuracy:  {attribution_accuracy:.1f}%")
    print(f"Failed Queries:        {len(failed_queries)}/50")
    print(f"Average Latency:       {average_latency_ms:.0f}ms")
    print(f"p50 Latency:           {p50_latency_ms:.0f}ms")
    print(f"p95 Latency:           {p95_latency_ms:.0f}ms (NFR13 target: <15,000ms)")
    print(f"p99 Latency:           {p99_latency_ms:.0f}ms")
    print("=" * 80 + "\n")

    # Save results to JSON for analysis (AC4 conditional failure analysis)
    results_file = Path("docs/stories/AC1-ground-truth-results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)

    with results_file.open("w") as f:
        json.dump(
            {
                "story": "2.5",
                "acceptance_criteria": "AC1",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "metrics": {
                    "retrieval_accuracy": retrieval_accuracy,
                    "attribution_accuracy": attribution_accuracy,
                    "total_queries": metrics.total_queries,
                    "successful_queries": metrics.successful_queries,
                    "failed_queries_count": len(failed_queries),
                    "average_latency_ms": average_latency_ms,
                    "p50_latency_ms": p50_latency_ms,
                    "p95_latency_ms": p95_latency_ms,
                    "p99_latency_ms": p99_latency_ms,
                },
                "failed_queries": [
                    {
                        "query_id": r.query_id,
                        "question": r.question,
                        "expected_page": r.expected_page,
                        "expected_document": r.expected_document,
                        "retrieved_pages": [p for _, p, _ in r.top_5_chunks],
                        "top_score": r.top_score,
                        "latency_ms": r.latency_ms,
                    }
                    for r in failed_queries
                ],
            },
            f,
            indent=2,
        )

    print(f"Results saved to: {results_file}\n")

    return metrics
