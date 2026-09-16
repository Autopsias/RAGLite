"""Helper utilities for ground truth accuracy validation.

This module contains dataclasses, helper functions, and output utilities
extracted from test_ac3_ground_truth.py to reduce file size.
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path

from raglite.retrieval.search import hybrid_search
from tests.fixtures.ground_truth import GroundTruthQuestion


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


async def execute_single_ground_truth_query(
    idx: int,
    query: GroundTruthQuestion,
) -> tuple[QueryValidationResult, float]:
    """Execute a single ground truth query and return validation result with latency.

    Args:
        idx: Query index (1-50)
        query: Ground truth question dict

    Returns:
        Tuple of (validation result, elapsed time in ms)
    """
    print(f"\n[{idx}/50] Query ID {query['id']}: {query['question'][:80]}...")

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
        elapsed_ms = (time.time() - start_time) * 1000
        result = QueryValidationResult(
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
        return result, elapsed_ms

    elapsed_ms = (time.time() - start_time) * 1000

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

    return result_obj, elapsed_ms


def calculate_accuracy_metrics(
    results: list[QueryValidationResult],
    latencies: list[float],
) -> AccuracyMetrics:
    """Calculate accuracy metrics from query results.

    Args:
        results: List of query validation results
        latencies: List of query execution times in ms

    Returns:
        AccuracyMetrics with aggregated statistics
    """
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

    return AccuracyMetrics(
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


def print_accuracy_summary(
    retrieval_accuracy: float,
    attribution_accuracy: float,
    successful_queries: int,
    failed_queries: list[QueryValidationResult],
    average_latency_ms: float,
    p50_latency_ms: float,
    p95_latency_ms: float,
    p99_latency_ms: float,
) -> None:
    """Print accuracy metrics summary.

    Args:
        retrieval_accuracy: Percentage of successful retrievals
        attribution_accuracy: Percentage of successful attributions
        successful_queries: Count of successful queries
        failed_queries: List of failed query results
        average_latency_ms: Mean query execution time
        p50_latency_ms: Median query execution time
        p95_latency_ms: 95th percentile execution time
        p99_latency_ms: 99th percentile execution time
    """
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


def save_ground_truth_results(
    metrics: AccuracyMetrics,
    retrieval_accuracy: float,
    attribution_accuracy: float,
    failed_queries: list[QueryValidationResult],
    average_latency_ms: float,
    p50_latency_ms: float,
    p95_latency_ms: float,
    p99_latency_ms: float,
) -> None:
    """Save ground truth test results to JSON file.

    Args:
        metrics: AccuracyMetrics object
        retrieval_accuracy: Retrieval accuracy percentage
        attribution_accuracy: Attribution accuracy percentage
        failed_queries: List of failed query results
        average_latency_ms: Mean query execution time
        p50_latency_ms: Median query execution time
        p95_latency_ms: 95th percentile execution time
        p99_latency_ms: 99th percentile execution time
    """
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
