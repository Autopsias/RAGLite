#!/usr/bin/env python3
"""Epic 2 Final Validation - Stories 2.11 + 2.14 + 2.15 Integrated.

Validates that ALL three stories work together with normalized ground truth:
- Story 2.11: Hybrid search score normalization + BM25 tuning
- Story 2.14: SQL backend + fuzzy matching + multi-entity
- Story 2.15: Ground truth normalization + period mapping

Target: ≥70% accuracy on normalized ground truth

Usage:
    python scripts/validate-epic-2-final.py

Output:
    docs/validation/epic-2-final-validation.json
"""

import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

from raglite.retrieval.multi_index_search import multi_index_search
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a single validation query."""

    query_id: int
    question: str
    category: str
    expected_keywords: list[str]
    retrieved_keywords: list[str]
    passed: bool
    latency_ms: float
    error: str | None = None


async def validate_query(query_obj: dict) -> ValidationResult:
    """Validate a single ground truth query against the integrated system.

    Args:
        query_obj: Ground truth query object

    Returns:
        ValidationResult with pass/fail and latency
    """
    query_id = query_obj.get("id")
    question = query_obj.get("question")
    category = query_obj.get("category", "unknown")
    expected_keywords = query_obj.get("expected_keywords", [])

    logger.debug(f"Validating query {query_id}: {question[:60]}...")

    try:
        # Measure latency
        start_time = time.time()

        # Story 2.11 + 2.14 + 2.15: Multi-index search with hybrid scoring + SQL + period normalization
        results = await multi_index_search(question, top_k=5)

        latency_ms = (time.time() - start_time) * 1000

        # Extract retrieved text for keyword matching
        # SearchResult from multi_index_search has .text attribute
        retrieved_texts = []
        for result in results:
            if hasattr(result, "text"):
                retrieved_texts.append(result.text.lower())
            elif hasattr(result, "chunk") and hasattr(result.chunk, "content"):
                retrieved_texts.append(result.chunk.content.lower())
            elif hasattr(result, "content"):
                retrieved_texts.append(result.content.lower())
            else:
                logger.warning(f"Unknown result structure: {type(result)}")

        retrieved_text = " ".join(retrieved_texts)

        # Check if any expected keywords found
        retrieved_keywords = []
        for keyword in expected_keywords:
            if keyword.lower() in retrieved_text:
                retrieved_keywords.append(keyword)

        # Pass if at least one keyword found
        passed = len(retrieved_keywords) > 0

        return ValidationResult(
            query_id=query_id,
            question=question,
            category=category,
            expected_keywords=expected_keywords,
            retrieved_keywords=retrieved_keywords,
            passed=passed,
            latency_ms=latency_ms,
        )

    except Exception as e:
        logger.error(f"Query {query_id} failed: {e}", exc_info=True)
        return ValidationResult(
            query_id=query_id,
            question=question,
            category=category,
            expected_keywords=expected_keywords,
            retrieved_keywords=[],
            passed=False,
            latency_ms=0.0,
            error=str(e),
        )


async def validate_epic_2_final() -> tuple[str, float]:
    """Final Epic 2 validation with all improvements active.

    Returns:
        Tuple of (decision, accuracy_percentage)
    """
    print("=" * 80)
    print("EPIC 2 FINAL VALIDATION - All Stories Combined")
    print("=" * 80)
    print()
    print("Stories Under Test:")
    print("  ✅ Story 2.11: Hybrid Search Score Normalization")
    print("  ✅ Story 2.14: SQL Backend + Fuzzy Matching + Multi-Entity")
    print("  ✅ Story 2.15: Ground Truth Normalization + Period Mapping")
    print()

    # Load normalized ground truth (AC1 output)
    ground_truth_path = Path("tests/ground_truth_normalized.json")
    if not ground_truth_path.exists():
        raise FileNotFoundError(f"Normalized ground truth not found: {ground_truth_path}")

    with open(ground_truth_path) as f:
        ground_truth_data = json.load(f)

    queries = ground_truth_data.get("questions", [])
    total_queries = len(queries)

    print(f"Ground Truth: {total_queries} normalized queries")
    print()

    # Validate each query
    results: list[ValidationResult] = []

    for query_obj in queries:
        result = await validate_query(query_obj)
        results.append(result)

        status = "✅ PASS" if result.passed else "❌ FAIL"
        keywords_found = (
            f"{len(result.retrieved_keywords)}/{len(result.expected_keywords)} keywords"
        )

        print(
            f"{status} Query {result.query_id}: {result.question[:60]}... | {keywords_found} | latency={result.latency_ms:.0f}ms"
        )

    # Calculate metrics
    passed_count = sum(1 for r in results if r.passed)
    accuracy = (passed_count / total_queries) * 100 if total_queries > 0 else 0.0

    latencies = [r.latency_ms for r in results if r.latency_ms > 0]
    p50_latency = statistics.median(latencies) if latencies else 0.0
    p95_latency = (
        statistics.quantiles(latencies, n=20)[18]
        if len(latencies) >= 20
        else (max(latencies) if latencies else 0.0)
    )

    # Category breakdown
    category_stats = {}
    for result in results:
        if result.category not in category_stats:
            category_stats[result.category] = {"passed": 0, "total": 0}

        category_stats[result.category]["total"] += 1
        if result.passed:
            category_stats[result.category]["passed"] += 1

    # Print results
    print()
    print("=" * 80)
    print()
    print("FINAL VALIDATION RESULTS:")
    print()
    print(f"Overall Accuracy: {accuracy:.1f}% ({passed_count}/{total_queries})")
    print()
    print("Latency:")
    print(f"  p50: {p50_latency:.0f}ms")
    print(f"  p95: {p95_latency:.0f}ms")

    # Category breakdown
    print()
    print("=" * 80)
    print()
    print("ACCURACY BY CATEGORY:")
    for category, stats in sorted(category_stats.items()):
        cat_accuracy = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0.0
        print(f"  {category:30s}: {cat_accuracy:5.1f}% ({stats['passed']}/{stats['total']})")

    # Decision gate evaluation
    print()
    print("=" * 80)
    print()
    print("DECISION GATE EVALUATION:")

    checks = {
        "Retrieval accuracy ≥70%": accuracy >= 70.0,
        "p95 latency <15000ms": p95_latency < 15000,
    }

    for check, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {check}")

    # Final decision
    print()
    print("=" * 80)
    print()
    print("EPIC 2 COMPLETION DECISION:")
    print()

    if accuracy >= 70.0:
        decision = "EPIC_2_COMPLETE"
        print("  🎉 EPIC 2 COMPLETE - TARGET ACHIEVED")
        print(f"  → Achieved {accuracy:.1f}% accuracy (target: ≥70%)")
        print("  → Proceed to Epic 3 (AI Intelligence & Orchestration)")
    elif accuracy >= 60.0:
        decision = "PARTIAL_SUCCESS"
        print(f"  ⚠️ PARTIAL SUCCESS - {accuracy:.1f}% accuracy")
        print("  → Close to target but short of 70%")
        print("  → PM Decision: Accept 60-69% OR invest in Phase 2B")
    else:
        decision = "ESCALATE_PHASE_2B"
        print(f"  ❌ INSUFFICIENT - {accuracy:.1f}% accuracy")
        print("  → Escalate to Phase 2B (Cross-Encoder Re-Ranking)")
        print("  → Expected: +3-5pp improvement → 75-80% total")

    # Save results
    output_dir = Path("docs/validation")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "epic-2-final-validation.json"

    results_data = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "stories_tested": ["2.11", "2.14", "2.15"],
            "ground_truth_file": str(ground_truth_path),
            "total_queries": total_queries,
        },
        "metrics": {
            "overall_accuracy": accuracy,
            "passed_count": passed_count,
            "failed_count": total_queries - passed_count,
            "latency_p50_ms": p50_latency,
            "latency_p95_ms": p95_latency,
        },
        "category_breakdown": {
            category: {
                "accuracy": (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0.0,
                "passed": stats["passed"],
                "total": stats["total"],
            }
            for category, stats in category_stats.items()
        },
        "decision_gate": {
            "decision": decision,
            "checks": checks,
        },
        "individual_results": [
            {
                "query_id": r.query_id,
                "question": r.question,
                "category": r.category,
                "passed": r.passed,
                "expected_keywords": r.expected_keywords,
                "retrieved_keywords": r.retrieved_keywords,
                "latency_ms": r.latency_ms,
                "error": r.error,
            }
            for r in results
        ],
    }

    with open(output_path, "w") as f:
        json.dump(results_data, f, indent=2)

    print()
    print("-" * 80)
    print(f"✅ Results saved: {output_path}")
    print()

    return decision, accuracy


async def main():
    """Main validation execution."""
    try:
        decision, accuracy = await validate_epic_2_final()
        print(f"✅ Epic 2 Final Accuracy: {accuracy:.1f}%")
        print(f"✅ Decision: {decision}")
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        print(f"\n❌ Validation failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
