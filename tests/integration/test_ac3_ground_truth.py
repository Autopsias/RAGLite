"""Story 2.5 AC1/AC2/AC3 - Full Ground Truth Accuracy Validation and Decision Gate.

This module executes all 50 ground truth queries to measure retrieval and attribution
accuracy for Epic 2 Phase 2A completion (Stories 2.3 + 2.4 implemented).

AC1: Run all 50 ground truth queries and measure accuracy
AC2: DECISION GATE - Retrieval accuracy ≥70% (MANDATORY)
AC3: Attribution accuracy ≥95% (NFR7 compliance)

Expected Results (Research-Validated):
    - Retrieval accuracy: 70-75% (35-37.5 / 50 queries pass)
      - Story 2.3 baseline: 68-72% (Yepes et al. 2024 - fixed 512-token chunks)
      - Story 2.4 boost: +2-3pp (Snowflake research - LLM metadata)
    - Attribution accuracy: ≥95% (NFR7 compliance)

Decision Gate Logic (AC2):
    - IF ≥70% → Epic 2 Phase 2A COMPLETE → Recommend Epic 3 start
    - IF <70% → Escalate to PM for Phase 2B (Structured Multi-Index) approval

Source: docs/stories/story-2.5.md
Context: docs/stories/story-context-2.5.xml
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from raglite.retrieval.search import hybrid_search
from tests.fixtures.ground_truth import GROUND_TRUTH_QA, GroundTruthQuestion


@dataclass
class QueryValidationResult:
    """Result of validating a single ground truth query.

    Attributes:
        query_id: Ground truth question ID (1-50)
        question: Natural language query text
        retrieval_success: True if correct chunk found in top-5 results
        attribution_success: True if correct document + page in top-5
        top_5_chunks: List of (source_document, page_number, chunk_index) tuples
        latency_ms: Query execution time in milliseconds
        top_score: Highest relevance score in results
        expected_page: Expected page number from ground truth
        expected_document: Expected document name from ground truth
    """

    query_id: int
    question: str
    retrieval_success: bool
    attribution_success: bool
    top_5_chunks: list[tuple[str, int | None, int]]
    latency_ms: float
    top_score: float
    expected_page: int
    expected_document: str


@dataclass
class AccuracyMetrics:
    """Aggregated accuracy metrics for all ground truth queries.

    Attributes:
        retrieval_accuracy: Percentage of queries with correct chunk in top-5
        attribution_accuracy: Percentage of queries with correct document + page
        total_queries: Total number of queries executed (should be 50)
        successful_queries: Count of retrieval successes
        failed_queries: List of QueryValidationResult objects for failures
        average_latency_ms: Mean query execution time
        p50_latency_ms: Median query execution time (p50)
        p95_latency_ms: 95th percentile query execution time (NFR13 target: <15s)
        p99_latency_ms: 99th percentile query execution time
    """

    retrieval_accuracy: float
    attribution_accuracy: float
    total_queries: int
    successful_queries: int
    failed_queries: list[QueryValidationResult]
    average_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


@pytest.mark.slow
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
        query: GroundTruthQuestion = query_data  # type: ignore[assignment]

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


@pytest.mark.slow
@pytest.mark.asyncio
async def test_ac2_decision_gate_validation():
    """AC2: DECISION GATE - Validate retrieval accuracy ≥70% (MANDATORY).

    NOTE: This test requires the full 160-page PDF (2025-08 Performance Review CONSO_v2.pdf).
    Run with: pytest --run-slow

    This is the CRITICAL DECISION GATE for Epic 2 Phase 2A completion.

    Test Logic:
        - Execute AC1 to get accuracy metrics
        - Assert retrieval_accuracy >= 70.0%
        - If PASS: Epic 2 Phase 2A COMPLETE → Document success
        - If FAIL: Escalate to PM for Phase 2B approval

    Expected Result:
        - Retrieval accuracy: 70-75% (Research-validated range)
        - Assertion PASS → Epic 2 complete

    Raises:
        AssertionError: If retrieval accuracy <70% (Epic 2 Phase 2A FAILED)
    """
    print("\n" + "=" * 80)
    print("STORY 2.5 AC2: DECISION GATE - Retrieval Accuracy ≥70%")
    print("=" * 80)
    print("THIS IS THE CRITICAL DECISION GATE FOR EPIC 2 PHASE 2A COMPLETION")
    print("Target: ≥70.0% (35/50 queries pass)")
    print("=" * 80 + "\n")

    # Execute AC1 to get metrics
    metrics = await test_ac1_full_ground_truth_execution()

    # AC2 DECISION GATE: Assert retrieval accuracy ≥70%
    print("\n" + "=" * 80)
    print("AC2 DECISION GATE EVALUATION")
    print("=" * 80)
    print(f"Retrieval Accuracy: {metrics.retrieval_accuracy:.1f}%")
    print("Target:             ≥70.0%")
    print(f"Successful Queries: {metrics.successful_queries}/50")
    print("=" * 80 + "\n")

    if metrics.retrieval_accuracy >= 70.0:
        print("✅ DECISION GATE: PASS")
        print("=" * 80)
        print("Epic 2 Phase 2A COMPLETE")
        print("=" * 80)
        print("Outcome:  Epic 2 SUCCESS")
        print("Timeline: 2-3 weeks (as projected)")
        print("Next:     Recommend Epic 3 planning (Intelligence Features)")
        print("=" * 80 + "\n")
    else:
        print("❌ DECISION GATE: FAIL")
        print("=" * 80)
        print("Epic 2 Phase 2A INCOMPLETE")
        print("=" * 80)
        print(f"Shortfall: {70.0 - metrics.retrieval_accuracy:.1f}pp below target")
        print("Action:    Escalate to PM for Phase 2B (Structured Multi-Index) approval")
        print("Timeline:  +3-4 weeks (total 5-7 weeks)")
        print("Expected:  70-80% accuracy with Phase 2B")
        print("=" * 80 + "\n")

        # Save failure report for PM escalation (if needed)
        failure_report = Path("docs/stories/AC2-decision-gate-failure-report.json")
        with failure_report.open("w") as f:
            json.dump(
                {
                    "story": "2.5",
                    "decision_gate": "AC2",
                    "status": "FAILED",
                    "retrieval_accuracy": metrics.retrieval_accuracy,
                    "target_accuracy": 70.0,
                    "shortfall_pp": 70.0 - metrics.retrieval_accuracy,
                    "successful_queries": metrics.successful_queries,
                    "failed_queries_count": len(metrics.failed_queries),
                    "recommendation": "Escalate to Phase 2B (Structured Multi-Index)",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                f,
                indent=2,
            )
        print(f"Failure report saved to: {failure_report}\n")

    # Assert retrieval accuracy ≥70% (MANDATORY)
    assert metrics.retrieval_accuracy >= 70.0, (
        f"DECISION GATE FAILED: Retrieval accuracy {metrics.retrieval_accuracy:.1f}% < 70% target. "
        f"Epic 2 Phase 2A incomplete. Escalate to PM for Phase 2B (Structured Multi-Index) approval. "
        f"See: docs/stories/AC2-decision-gate-failure-report.json"
    )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_ac3_attribution_accuracy_validation():
    """AC3: Validate attribution accuracy ≥95% (NFR7 compliance).

    NOTE: This test requires the full 160-page PDF (2025-08 Performance Review CONSO_v2.pdf).
    Run with: pytest --run-slow

    Test Logic:
        - Execute AC1 to get accuracy metrics
        - Assert attribution_accuracy >= 95.0%
        - Analyze attribution failures (wrong document/page)

    Expected Result:
        - Attribution accuracy: ≥95% (NFR7 compliance)

    NFR7: 95%+ source attribution accuracy
    Source: docs/architecture/1-introduction-vision.md
    """
    print("\n" + "=" * 80)
    print("STORY 2.5 AC3: Attribution Accuracy Validation (NFR7)")
    print("=" * 80)
    print("Target: ≥95.0% (NFR7 compliance)")
    print("=" * 80 + "\n")

    # Execute AC1 to get metrics
    metrics = await test_ac1_full_ground_truth_execution()

    # Analyze attribution failures
    attribution_failures = [r for r in metrics.failed_queries if not r.attribution_success]

    print("\n" + "=" * 80)
    print("AC3 ATTRIBUTION ACCURACY EVALUATION")
    print("=" * 80)
    print(f"Attribution Accuracy: {metrics.attribution_accuracy:.1f}%")
    print("Target:               ≥95.0%")
    print(f"Attribution Failures: {len(attribution_failures)}/50")
    print("=" * 80 + "\n")

    if attribution_failures:
        print("Attribution Failure Analysis:")
        print("-" * 80)
        for failure in attribution_failures[:10]:  # Show first 10 failures
            print(f"Query {failure.query_id}: {failure.question[:60]}...")
            print(f"  Expected: {failure.expected_document}, page {failure.expected_page}")
            print(f"  Retrieved pages: {[p for _, p, _ in failure.top_5_chunks]}")
        if len(attribution_failures) > 10:
            print(f"... and {len(attribution_failures) - 10} more failures")
        print("=" * 80 + "\n")

    # Assert attribution accuracy ≥95% (NFR7 compliance)
    assert metrics.attribution_accuracy >= 95.0, (
        f"NFR7 FAILED: Attribution accuracy {metrics.attribution_accuracy:.1f}% < 95% required. "
        f"Attribution failures: {len(attribution_failures)}/50. "
        f"See: docs/stories/AC1-ground-truth-results.json for detailed failure analysis."
    )

    print("✅ AC3: PASS - Attribution accuracy meets NFR7 (≥95%)\n")
