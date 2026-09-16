"""AC2: Decision Gate Validation Test.

This module contains the critical decision gate for Epic 2 Phase 2A completion.
Validates that retrieval accuracy meets the ≥70% threshold.
"""

import json
import time

import pytest

from tests.integration.ac3_ground_truth.test_ac1_execution import (
    test_ac1_full_ground_truth_execution,
)


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
    from pathlib import Path

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
