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
from pathlib import Path

import pytest

from tests.fixtures.ground_truth import GROUND_TRUTH_QA, GroundTruthQuestion
from tests.integration.helpers.ground_truth_helpers import (
    AccuracyMetrics,
    QueryValidationResult,
    calculate_accuracy_metrics,
    execute_single_ground_truth_query,
    print_accuracy_summary,
    save_ground_truth_results,
)

# Mark all tests in this module as integration tests that preserve collection state
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


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
        query: GroundTruthQuestion = query_data  # type: ignore[assignment]
        result, elapsed_ms = await execute_single_ground_truth_query(idx, query)
        results.append(result)
        latencies.append(elapsed_ms)

    # Calculate accuracy metrics
    metrics = calculate_accuracy_metrics(results, latencies)

    # Print summary
    print_accuracy_summary(
        retrieval_accuracy=metrics.retrieval_accuracy,
        attribution_accuracy=metrics.attribution_accuracy,
        successful_queries=metrics.successful_queries,
        failed_queries=metrics.failed_queries,
        average_latency_ms=metrics.average_latency_ms,
        p50_latency_ms=metrics.p50_latency_ms,
        p95_latency_ms=metrics.p95_latency_ms,
        p99_latency_ms=metrics.p99_latency_ms,
    )

    # Save results to JSON for analysis (AC4 conditional failure analysis)
    save_ground_truth_results(
        metrics=metrics,
        retrieval_accuracy=metrics.retrieval_accuracy,
        attribution_accuracy=metrics.attribution_accuracy,
        failed_queries=metrics.failed_queries,
        average_latency_ms=metrics.average_latency_ms,
        p50_latency_ms=metrics.p50_latency_ms,
        p95_latency_ms=metrics.p95_latency_ms,
        p99_latency_ms=metrics.p99_latency_ms,
    )

    return metrics


@pytest.mark.priority("P0")
@pytest.mark.slow
@pytest.mark.skipif(
    not getattr(pytest, "run_slow", False),
    reason="Requires full 160-page PDF. Run with: pytest --run-slow",
)
@pytest.mark.timeout(600)  # 10 minutes - delegates to test_ac1 which runs 50 queries
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


@pytest.mark.priority("P0")
@pytest.mark.slow
@pytest.mark.skipif(
    not getattr(pytest, "run_slow", False),
    reason="Requires full 160-page PDF. Run with: pytest --run-slow",
)
@pytest.mark.timeout(600)  # 10 minutes - delegates to test_ac1 which runs 50 queries
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
