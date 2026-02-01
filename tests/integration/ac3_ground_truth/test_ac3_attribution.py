"""AC3: Attribution Accuracy Validation Test.

This module validates source attribution accuracy (NFR7 compliance).
"""

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
async def test_ac3_attribution_accuracy_validation():
    """AC3: Validate attribution accuracy ≥95% (NFR7 compliance).

    NOTE: This test require the full 160-page PDF (2025-08 Performance Review CONSO_v2.pdf).
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
