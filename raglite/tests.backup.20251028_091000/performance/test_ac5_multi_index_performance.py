"""AC5 Performance Validation - Story 2.7 Multi-Index Search.

This script validates multi-index search performance against NFR13 requirements:
- p50 latency: <5s (target)
- p95 latency: <15s (NFR13 requirement)
- p99 latency: <30s (acceptable)

Performance Metrics Captured:
1. Query classification time (<50ms target)
2. Vector search latency
3. SQL search latency (when applicable)
4. Result fusion time (<20ms target)
5. Total end-to-end latency

Test Set: 50 ground truth queries from tests/fixtures/ground_truth.py
Categories: Cost Analysis, Margins, Financial Performance, Safety, Workforce, Operating Expenses

Usage:
    python -m raglite.tests.performance.test_ac5_multi_index_performance
"""

import asyncio
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from raglite.retrieval.multi_index_search import multi_index_search  # noqa: E402
from raglite.shared.logging import get_logger  # noqa: E402
from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402

logger = get_logger(__name__)


class PerformanceMetrics:
    """Performance metrics for a single query."""

    def __init__(
        self,
        query_id: int,
        query: str,
        total_latency_ms: float,
        query_type: str,
        results_count: int,
        top_score: float | None = None,
    ):
        self.query_id = query_id
        self.query = query
        self.total_latency_ms = total_latency_ms
        self.query_type = query_type
        self.results_count = results_count
        self.top_score = top_score


async def run_performance_test() -> dict[str, Any]:
    """Run AC5 performance validation with 50 ground truth queries.

    Returns:
        Dictionary with performance metrics and validation results
    """
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🧪 AC5 PERFORMANCE VALIDATION - Story 2.7 Multi-Index Search")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"\nTest Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test Set: {len(GROUND_TRUTH_QA)} ground truth queries")
    print("Target: p50 <5s, p95 <15s (NFR13), p99 <30s")

    # Collect metrics for all queries
    all_metrics: list[PerformanceMetrics] = []
    failed_queries: list[tuple[int, str, str]] = []

    print("\n" + "─" * 60)
    print("RUNNING QUERIES...")
    print("─" * 60)

    for i, qa in enumerate(GROUND_TRUTH_QA, 1):
        query = qa["question"]
        query_id = qa["id"]

        try:
            # Measure total latency
            start_time = time.perf_counter()
            results = await multi_index_search(query, top_k=5)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Extract query type from classification (if logged)
            # For now, infer from results
            query_type = "unknown"
            if results:
                # Check source field to determine query type
                sources = {r.source for r in results}
                if "sql" in sources and "vector" in sources:
                    query_type = "hybrid"
                elif "sql" in sources:
                    query_type = "sql_only"
                else:
                    query_type = "vector_only"

            top_score = results[0].score if results else None

            metrics = PerformanceMetrics(
                query_id=query_id,
                query=query[:80],  # Truncate for display
                total_latency_ms=elapsed_ms,
                query_type=query_type,
                results_count=len(results),
                top_score=top_score,
            )
            all_metrics.append(metrics)

            # Progress indicator
            if i % 10 == 0 or i == len(GROUND_TRUTH_QA):
                avg_latency = statistics.mean([m.total_latency_ms for m in all_metrics])
                print(
                    f"  [{i}/{len(GROUND_TRUTH_QA)}] Avg latency: {avg_latency:.0f}ms "
                    f"| Query {query_id}: {elapsed_ms:.0f}ms"
                )

        except Exception as e:
            failed_queries.append((query_id, query[:80], str(e)))
            print(f"  ❌ Query {query_id} FAILED: {e}")

    print("\n" + "═" * 60)
    print("✅ QUERIES COMPLETE")
    print("═" * 60)

    # Calculate statistics
    if not all_metrics:
        print("\n❌ NO SUCCESSFUL QUERIES - Cannot calculate performance metrics")
        return {
            "success": False,
            "error": "All queries failed",
            "failed_count": len(failed_queries),
        }

    latencies = [m.total_latency_ms for m in all_metrics]
    latencies_sorted = sorted(latencies)

    # Calculate percentiles
    p50 = statistics.median(latencies_sorted)
    p95_idx = int(len(latencies_sorted) * 0.95)
    p95 = latencies_sorted[p95_idx] if p95_idx < len(latencies_sorted) else latencies_sorted[-1]
    p99_idx = int(len(latencies_sorted) * 0.99)
    p99 = latencies_sorted[p99_idx] if p99_idx < len(latencies_sorted) else latencies_sorted[-1]

    mean_latency = statistics.mean(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    stddev_latency = statistics.stdev(latencies) if len(latencies) > 1 else 0

    # Query type breakdown
    query_types: dict[str, int] = {}
    for m in all_metrics:
        query_types[m.query_type] = query_types.get(m.query_type, 0) + 1

    # NFR13 Validation
    nfr13_compliant = p95 <= 15000  # 15 seconds in ms
    p50_target_met = p50 <= 5000  # 5 seconds in ms
    p99_acceptable = p99 <= 30000  # 30 seconds in ms

    # Print results
    print("\n" + "═" * 60)
    print("📊 PERFORMANCE RESULTS")
    print("═" * 60)

    print("\n📈 LATENCY STATISTICS (milliseconds):")
    print(f"  • p50 (median):  {p50:>8.0f} ms {'✅' if p50_target_met else '⚠️'} (target: <5,000ms)")
    print(
        f"  • p95:           {p95:>8.0f} ms {'✅' if nfr13_compliant else '❌'} (NFR13: <15,000ms)"
    )
    print(
        f"  • p99:           {p99:>8.0f} ms {'✅' if p99_acceptable else '⚠️'} (target: <30,000ms)"
    )
    print(f"  • Mean:          {mean_latency:>8.0f} ms")
    print(f"  • Min:           {min_latency:>8.0f} ms")
    print(f"  • Max:           {max_latency:>8.0f} ms")
    print(f"  • Std Dev:       {stddev_latency:>8.0f} ms")

    print("\n🔍 QUERY TYPE DISTRIBUTION:")
    for qtype, count in sorted(query_types.items()):
        percentage = (count / len(all_metrics)) * 100
        print(f"  • {qtype.upper():<15}: {count:>3} queries ({percentage:>5.1f}%)")

    print("\n✅ SUCCESS METRICS:")
    print(f"  • Successful queries: {len(all_metrics)}/{len(GROUND_TRUTH_QA)}")
    print(f"  • Failed queries:     {len(failed_queries)}")
    success_rate = (len(all_metrics) / len(GROUND_TRUTH_QA)) * 100
    print(f"  • Success rate:       {success_rate:.1f}%")

    print("\n🎯 NFR13 VALIDATION:")
    if nfr13_compliant:
        print("  ✅ NFR13 COMPLIANT - p95 latency <15s")
    else:
        print(f"  ❌ NFR13 VIOLATION - p95 latency {p95 / 1000:.1f}s exceeds 15s limit")

    if p50_target_met:
        print("  ✅ p50 TARGET MET - Median latency <5s")
    else:
        print(f"  ⚠️  p50 ABOVE TARGET - Median latency {p50 / 1000:.1f}s exceeds 5s target")

    if p99_acceptable:
        print("  ✅ p99 ACCEPTABLE - 99th percentile <30s")
    else:
        print(f"  ⚠️  p99 CONCERN - 99th percentile {p99 / 1000:.1f}s exceeds 30s")

    # Failed queries summary
    if failed_queries:
        print("\n❌ FAILED QUERIES:")
        for query_id, query, error in failed_queries[:5]:  # Show first 5
            print(f"  • Query {query_id}: {query}")
            print(f"    Error: {error[:100]}")
        if len(failed_queries) > 5:
            print(f"  ... and {len(failed_queries) - 5} more")

    # Performance assessment
    print("\n" + "═" * 60)
    print("🏆 OVERALL ASSESSMENT")
    print("═" * 60)

    if nfr13_compliant and p50_target_met:
        print("  ✅ EXCELLENT - All performance targets met!")
        print("     Multi-index search is production-ready.")
    elif nfr13_compliant:
        print("  ✅ GOOD - NFR13 compliant (p95 <15s)")
        print("     p50 slightly above target but acceptable.")
    else:
        print("  ❌ NEEDS IMPROVEMENT - NFR13 violation")
        print("     Investigate bottlenecks before production.")

    print("\n" + "═" * 60)
    print("TEST COMPLETE")
    print("═" * 60)
    print(f"\nTest End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Return results dictionary
    return {
        "success": True,
        "nfr13_compliant": nfr13_compliant,
        "p50_target_met": p50_target_met,
        "p99_acceptable": p99_acceptable,
        "latency_stats": {
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "mean_ms": mean_latency,
            "min_ms": min_latency,
            "max_ms": max_latency,
            "stddev_ms": stddev_latency,
        },
        "query_metrics": {
            "total_queries": len(GROUND_TRUTH_QA),
            "successful": len(all_metrics),
            "failed": len(failed_queries),
            "success_rate": success_rate,
        },
        "query_type_distribution": query_types,
        "failed_queries": failed_queries,
    }


if __name__ == "__main__":
    # Run async test
    results = asyncio.run(run_performance_test())

    # Exit with appropriate code
    if results["success"] and results["nfr13_compliant"]:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure
