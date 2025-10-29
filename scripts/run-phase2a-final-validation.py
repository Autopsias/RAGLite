"""Run final Phase 2A validation with all fixes applied.

Story 2.11 AC4: Comprehensive validation of all Phase 2A improvements:
  - Story 2.8: Table-aware chunking (8.6 → 1.2 chunks per table)
  - Story 2.9: Ground truth page references (valid metrics)
  - Story 2.10: Query routing fix (48% → 6% SQL)
  - Story 2.11: Hybrid search scoring + BM25 tuning

Decision Gate Criteria:
  - ≥70% accuracy → Epic 2 COMPLETE
  - 65-70% accuracy → Re-evaluate Phase 2B
  - <65% accuracy → Escalate to Phase 2B

Usage:
    python scripts/run-phase2a-final-validation.py
"""

import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Note: imports below are placed after sys.path.insert for local module discovery
from raglite.retrieval.multi_index_search import multi_index_search  # noqa: E402
from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402


async def run_phase2a_final_validation():
    """Run final Phase 2A validation with all fixes applied.

    Measures:
      1. Retrieval accuracy (% queries with correct page in top-5)
      2. Attribution accuracy (% correct source citations)
      3. Query latency (p50, p95)
      4. Decision gate evaluation
    """
    print("=" * 80)
    print("PHASE 2A FINAL VALIDATION")
    print("=" * 80)
    print(f"\nTesting {len(GROUND_TRUTH_QA)} ground truth queries with all fixes applied:")
    print("\nPhase 2A Fixes Implemented:")
    print("  ✅ Story 2.8: Table-aware chunking (8.6 → 1.2 chunks per table)")
    print("  ✅ Story 2.9: Ground truth page references (50 validated Q&A pairs)")
    print("  ✅ Story 2.10: Query routing fix (48% → 6% SQL routing)")
    print("  ✅ Story 2.11: Hybrid search RRF fusion + BM25 tuning")
    print("\n" + "=" * 80)

    correct_count = 0
    attribution_correct = 0
    latencies = []
    total_valid_queries = 0

    method_results = {
        "multi_index": {"correct": 0, "total": 0},
    }

    for qa in GROUND_TRUTH_QA:
        query = qa["question"]
        expected_page = qa.get("expected_page_number")
        expected_doc = qa.get("source_document", "")

        if not expected_page:
            print(f"⚠️  Skipping query (no expected page): {query[:80]}")
            continue

        total_valid_queries += 1

        # Measure latency
        start_time = time.time()
        try:
            results = await multi_index_search(query, top_k=5)
            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)

            # Check retrieval accuracy
            retrieved_pages = [r.page_number for r in results]
            method_results["multi_index"]["total"] += 1

            if expected_page in retrieved_pages:
                correct_count += 1
                method_results["multi_index"]["correct"] += 1

            # Check attribution accuracy (if source_document available)
            if expected_doc and results:
                # Get document_id from first result (SearchResult has document_id field)
                top_doc = (
                    results[0].document_id
                    if hasattr(results[0], "document_id")
                    else results[0].source_document
                    if hasattr(results[0], "source_document")
                    else ""
                )
                if top_doc == expected_doc or expected_doc in top_doc:
                    attribution_correct += 1

        except Exception as e:
            print(f"❌ Error on query '{query[:60]}...': {e}")
            latencies.append(0)  # Add 0 for failed queries
            method_results["multi_index"]["total"] += 1
            continue

    # Calculate metrics
    retrieval_accuracy = (
        (correct_count / total_valid_queries) * 100 if total_valid_queries > 0 else 0.0
    )
    attribution_accuracy = (
        (attribution_correct / total_valid_queries) * 100 if total_valid_queries > 0 else 0.0
    )

    # Filter out zero latencies (failed queries) for percentile calculation
    valid_latencies = [lat for lat in latencies if lat > 0]

    if valid_latencies:
        p50_latency = statistics.median(valid_latencies)
        # Calculate p95 manually if we have enough samples
        if len(valid_latencies) >= 20:
            sorted_latencies = sorted(valid_latencies)
            p95_index = int(len(sorted_latencies) * 0.95)
            p95_latency = sorted_latencies[p95_index]
        else:
            p95_latency = max(valid_latencies)  # Use max if too few samples
    else:
        p50_latency = 0
        p95_latency = 0

    # Print results
    print("\n" + "=" * 80)
    print("\nFINAL VALIDATION RESULTS:")
    print("=" * 80)
    print(
        f"\nRetrieval Accuracy: {retrieval_accuracy:.1f}% ({correct_count}/{total_valid_queries})"
    )
    print(
        f"Attribution Accuracy: {attribution_accuracy:.1f}% ({attribution_correct}/{total_valid_queries})"
    )
    print("\nQuery Latency:")
    print(f"  p50: {p50_latency:.0f}ms")
    print(f"  p95: {p95_latency:.0f}ms")

    # Decision gate checks
    print("\n" + "=" * 80)
    print("\nDECISION GATE EVALUATION:")
    print("=" * 80)

    checks = {
        "Retrieval accuracy ≥70%": retrieval_accuracy >= 70.0,
        "Attribution accuracy ≥95%": attribution_accuracy >= 95.0,
        "p95 latency <15000ms": p95_latency < 15000,
    }

    for check, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {check}")

    # Decision
    print("\n" + "=" * 80)
    print("\nPHASE 2A DECISION:")
    print("=" * 80)

    if retrieval_accuracy >= 70.0:
        decision = "epic_2_complete"
        print("\n🎉 EPIC 2 COMPLETE - Phase 2A SUCCESS")
        print(f"  → Achieved {retrieval_accuracy:.1f}% accuracy (target: ≥70%)")
        print("  → Proceed to Epic 3 (AI Intelligence & Orchestration)")
        print("\nPhase 2A Achievement:")
        print("  • Baseline accuracy: 56%")
        print(f"  • Final accuracy: {retrieval_accuracy:.1f}%")
        print(f"  • Improvement: {retrieval_accuracy - 56:.1f}pp")
    elif retrieval_accuracy >= 65.0:
        decision = "reevaluate_phase2b"
        print(f"\n⚠️  PHASE 2A PARTIAL SUCCESS - {retrieval_accuracy:.1f}% accuracy")
        print("  → Re-evaluate Phase 2B necessity with PM")
        print("  → Accuracy meets minimum threshold but below target")
        print("\nRecommendations:")
        print("  1. Review Phase 2A improvements effectiveness")
        print("  2. Consider additional tuning before Phase 2B")
        print("  3. Discuss with PM: Accept 65-70% or invest in Phase 2B?")
    else:
        decision = "escalate_phase2b"
        print(f"\n❌ PHASE 2A INSUFFICIENT - {retrieval_accuracy:.1f}% accuracy")
        print("  → Escalate to Phase 2B (Structured Multi-Index)")
        print("  → PM approval required for Phase 2B implementation")
        print("\nPhase 2B Requirements:")
        print("  • PostgreSQL + Qdrant + cross-encoder re-ranking")
        print("  • Timeline: +3-4 weeks")
        print("  • Expected accuracy: 70-80%")

    # Save results
    output_path = project_root / "docs" / "validation" / "phase2a-final-validation.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results_data = {
        "retrieval_accuracy": retrieval_accuracy,
        "attribution_accuracy": attribution_accuracy,
        "correct_count": correct_count,
        "total_queries": total_valid_queries,
        "latency_p50_ms": p50_latency,
        "latency_p95_ms": p95_latency,
        "decision": decision,
        "decision_checks": checks,
        "baseline_accuracy": 56.0,
        "accuracy_improvement_pp": retrieval_accuracy - 56.0,
        "phase2a_fixes": [
            "Story 2.8: Table-aware chunking",
            "Story 2.9: Ground truth page references",
            "Story 2.10: Query routing fix",
            "Story 2.11: Hybrid search RRF + BM25 tuning",
        ],
    }

    with open(output_path, "w") as f:
        json.dump(results_data, f, indent=2)

    print(f"\nResults saved to: {output_path}")
    print("\n" + "=" * 80)

    return decision, retrieval_accuracy


if __name__ == "__main__":
    print("\n")
    decision, accuracy = asyncio.run(run_phase2a_final_validation())
    print(f"\n✅ Phase 2A final accuracy: {accuracy:.1f}%")
    print(f"✅ Decision: {decision}")

    if decision == "epic_2_complete":
        print("\n🎊 Congratulations! Epic 2 requirements met.")
        print("   Next: Begin Epic 3 planning (AI Intelligence & Orchestration)")
    elif decision == "reevaluate_phase2b":
        print("\n   Next: Schedule PM meeting to discuss Phase 2B necessity")
    else:
        print("\n   Next: Prepare Phase 2B implementation plan for PM approval")

    print("\n")
