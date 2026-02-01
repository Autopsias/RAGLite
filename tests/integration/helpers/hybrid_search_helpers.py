"""Helper functions for hybrid search integration tests.

Extracted from test_hybrid_search_integration.py to reduce file size.
These functions support the hybrid search accuracy validation workflow.
"""

import time

import pytest

from tests.fixtures.ground_truth import GROUND_TRUTH_QA


async def validate_qdrant_collection():
    """Validate Qdrant collection has sufficient data for testing.

    Returns:
        Collection info if valid, skips test otherwise

    Raises:
        pytest.skip: If collection is empty or has insufficient data
    """
    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    qdrant = get_qdrant_client()
    collection_info = qdrant.get_collection(settings.qdrant_collection_name)

    if collection_info.points_count == 0:
        pytest.skip(
            "Qdrant collection is empty. Run 'python scripts/ingest-whole-pdf.py' "
            "to populate test data before running this test."
        )

    # Element-aware chunking produces ~900-1200 chunks for 160-page PDF
    MIN_REQUIRED_POINTS = 800

    if collection_info.points_count < MIN_REQUIRED_POINTS:
        pytest.skip(
            f"Qdrant collection has only {collection_info.points_count} points. "
            f"Expected ~900-1200 points for full 160-page PDF with element-aware chunking. "
            f"Run 'python scripts/ingest-whole-pdf.py' and wait for completion."
        )

    return collection_info


def print_test_header(collection_info):
    """Print test header with validation information.

    Args:
        collection_info: Qdrant collection info
    """
    print("\n" + "=" * 80)
    print("ELEMENT-AWARE CHUNKING VALIDATION (Story 2.2 AC3 - DECISION GATE)")
    print("=" * 80)
    print(f"Qdrant data validated: {collection_info.points_count} points available")
    print(f"Running {len(GROUND_TRUTH_QA)} queries with hybrid search + element chunking...")
    print("MANDATORY: ≥64% retrieval accuracy (32/50 queries)")
    print("STRETCH: ≥68% retrieval accuracy (34/50 queries)")
    print("BASELINE: 56% (28/50 queries with fixed chunking)")
    print("=" * 80 + "\n")


async def run_single_query(qa, idx, total):
    """Run hybrid search for a single query.

    Args:
        qa: Ground truth Q&A pair
        idx: Query index (for progress display)
        total: Total number of queries

    Returns:
        Tuple of (result dict, latency_ms)
    """
    from raglite.retrieval.attribution import generate_citations
    from raglite.retrieval.search import hybrid_search
    from scripts.accuracy_utils import check_attribution_accuracy, check_retrieval_accuracy

    print(f"  [{idx}/{total}] {qa['question'][:60]}...", end=" ")

    start_time = time.time()

    query_results = await hybrid_search(
        query=qa["question"], top_k=5, alpha=0.5, enable_hybrid=True
    )
    query_results = await generate_citations(query_results)

    latency_ms = (time.time() - start_time) * 1000

    retrieval_result = check_retrieval_accuracy(qa, query_results)
    attribution_result = check_attribution_accuracy(qa, query_results)

    result = {
        "query_id": qa["id"],
        "latency_ms": latency_ms,
        "retrieval": retrieval_result,
        "attribution": attribution_result,
    }

    status = "✓" if retrieval_result["pass_"] else "✗"
    print(f"{status} ({latency_ms:.0f}ms)")

    return result, latency_ms


async def run_all_queries():
    """Run hybrid search on all ground truth queries.

    Returns:
        Tuple of (results list, latencies list)
    """
    results = []
    latencies = []

    for i, qa in enumerate(GROUND_TRUTH_QA, start=1):
        result, latency = await run_single_query(qa, i, len(GROUND_TRUTH_QA))
        results.append(result)
        latencies.append(latency)

    return results, latencies


def print_accuracy_results(metrics, latency_ceiling_p95):
    """Print accuracy and performance results.

    Args:
        metrics: Performance metrics dict
        latency_ceiling_p95: p95 latency ceiling threshold
    """
    print("\n" + "=" * 80)
    print("HYBRID SEARCH ACCURACY RESULTS")
    print("=" * 80)
    print(f"  Retrieval Accuracy:   {metrics['retrieval_accuracy']:.1f}% (target: ≥70%)")
    print(f"  Attribution Accuracy: {metrics['attribution_accuracy']:.1f}% (target: ≥45%)")
    print(f"  p50 Latency:          {metrics['p50_latency_ms']:.0f}ms")
    print(
        f"  p95 Latency:          {metrics['p95_latency_ms']:.0f}ms (limit: {latency_ceiling_p95}ms)"
    )
    print("=" * 80)

    baseline_retrieval = 56.0
    baseline_attribution = 32.0
    retrieval_improvement = metrics["retrieval_accuracy"] - baseline_retrieval
    attribution_improvement = metrics["attribution_accuracy"] - baseline_attribution

    print("\nIMPROVEMENT OVER EPIC 1 BASELINE:")
    print(f"  Retrieval:   {retrieval_improvement:+.1f}pp (baseline: {baseline_retrieval}%)")
    print(f"  Attribution: {attribution_improvement:+.1f}pp (baseline: {baseline_attribution}%)")
    print("=" * 80 + "\n")


def validate_retrieval_accuracy(metrics):
    """Validate retrieval accuracy against Story 2.2 AC3 targets.

    Args:
        metrics: Performance metrics dict

    Raises:
        AssertionError: If mandatory target not met
    """
    STORY_2_2_MANDATORY_TARGET = 64.0  # 32/50 queries
    STORY_2_2_STRETCH_TARGET = 68.0  # 34/50 queries

    assert metrics["retrieval_accuracy"] >= STORY_2_2_MANDATORY_TARGET, (
        f"STORY 2.2 AC3 FAILED: Retrieval accuracy {metrics['retrieval_accuracy']:.1f}% "
        f"is below {STORY_2_2_MANDATORY_TARGET}% mandatory target. "
        f"Expected ≥{STORY_2_2_MANDATORY_TARGET}% for element-aware chunking + hybrid search. "
        f"Baseline was 56%. Element-aware chunking must achieve ≥{STORY_2_2_MANDATORY_TARGET}% to pass AC3.\n"
        f"DECISION GATE: <64% = ESCALATE TO PM (Story 2.2 BLOCKED)"
    )

    if metrics["retrieval_accuracy"] >= STORY_2_2_STRETCH_TARGET:
        print(
            f"\n✓ STRETCH GOAL ACHIEVED: {metrics['retrieval_accuracy']:.1f}% ≥ {STORY_2_2_STRETCH_TARGET}% "
            f"(high confidence in element-aware chunking approach)"
        )
    elif metrics["retrieval_accuracy"] >= STORY_2_2_MANDATORY_TARGET:
        print(
            f"\n⚠ MANDATORY TARGET MET: {metrics['retrieval_accuracy']:.1f}% in range "
            f"[{STORY_2_2_MANDATORY_TARGET}%, {STORY_2_2_STRETCH_TARGET}%) "
            f"(proceed with caution flag)"
        )
    else:
        print(
            f"\n❌ MANDATORY TARGET MISSED: {metrics['retrieval_accuracy']:.1f}% < "
            f"{STORY_2_2_MANDATORY_TARGET}% (ESCALATE TO PM)"
        )


def validate_attribution_accuracy(metrics, hybrid_attribution_target):
    """Validate and report attribution accuracy.

    Args:
        metrics: Performance metrics dict
        hybrid_attribution_target: Target attribution accuracy threshold
    """
    if metrics["attribution_accuracy"] >= hybrid_attribution_target:
        print(f"✓ Attribution accuracy {metrics['attribution_accuracy']:.1f}% meets target (≥45%)")
    else:
        print(
            f"⚠ Attribution accuracy {metrics['attribution_accuracy']:.1f}% below target "
            f"(≥45%), but story can still pass if retrieval ≥70%"
        )


def validate_latency(metrics, latency_ceiling_p95):
    """Validate NFR13 latency compliance.

    Args:
        metrics: Performance metrics dict
        latency_ceiling_p95: p95 latency ceiling threshold

    Raises:
        AssertionError: If p95 latency exceeds limit
    """
    assert metrics["p95_latency_ms"] < latency_ceiling_p95, (
        f"NFR13 VIOLATION: p95 latency {metrics['p95_latency_ms']:.0f}ms "
        f"exceeds {latency_ceiling_p95}ms limit"
    )


async def collect_all_query_results():
    """Run all ground truth queries and collect results.

    Returns:
        Tuple of (results list, latencies list, metrics dict, collection_info)
    """
    from scripts.accuracy_utils import calculate_performance_metrics

    # Validate Qdrant collection
    collection_info = await validate_qdrant_collection()

    # Print test header
    print_test_header(collection_info)

    # Run all queries
    results, latencies = await run_all_queries()

    # Calculate metrics
    metrics = calculate_performance_metrics(results)

    return results, latencies, metrics, collection_info
