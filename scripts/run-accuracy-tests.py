#!/usr/bin/env python3
"""Accuracy test runner for RAGLite Phase 1 validation.

Runs ground truth queries against RAGLite system and calculates:
- Retrieval accuracy (% of queries returning correct information)
- Source attribution accuracy (% of citations with correct page numbers)
- Performance metrics (p50, p95 response times)

Usage:
    # Run all queries
    uv run python scripts/run-accuracy-tests.py

    # Run subset for daily checks
    uv run python scripts/run-accuracy-tests.py --subset 15

    # Run specific category
    uv run python scripts/run-accuracy-tests.py --category cost_analysis

    # Save results to file
    uv run python scripts/run-accuracy-tests.py --output results.json --verbose

Exit codes:
    0 - All tests pass (≥90% retrieval accuracy, ≥95% attribution accuracy)
    1 - Tests fail (accuracy below targets) or errors encountered
"""

import argparse
import asyncio
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from accuracy_utils import (  # noqa: E402
    NFR6_RETRIEVAL_TARGET,
    NFR7_ATTRIBUTION_TARGET,
    calculate_performance_metrics,
    check_attribution_accuracy,
    check_nfr_compliance,
    check_retrieval_accuracy,
)

from raglite.retrieval.attribution import generate_citations  # noqa: E402
from raglite.retrieval.search import search_documents  # noqa: E402
from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run RAGLite accuracy validation tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--subset",
        type=int,
        metavar="N",
        help="Run only N randomly selected queries (for daily spot checks)",
    )
    parser.add_argument(
        "--category",
        type=str,
        metavar="CAT",
        choices=[
            "cost_analysis",
            "margins",
            "financial_performance",
            "safety_metrics",
            "workforce",
            "operating_expenses",
        ],
        help="Run only queries from specific category",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output for each query",
    )
    parser.add_argument(
        "--output",
        type=str,
        metavar="FILE",
        help="Save results to JSON file",
    )
    return parser.parse_args()


def filter_queries(queries: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    """Filter queries based on command-line arguments."""
    filtered = queries

    # Filter by category if specified
    if args.category:
        filtered = [q for q in filtered if q["category"] == args.category]
        print(f"Filtered to {len(filtered)} queries in category '{args.category}'")

    # Select random subset if specified
    if args.subset and args.subset < len(filtered):
        filtered = random.sample(filtered, args.subset)
        print(f"Selected random subset of {args.subset} queries")

    return filtered


# Accuracy checking functions imported from accuracy_utils


async def run_single_query(qa: dict[str, Any], verbose: bool = False) -> dict[str, Any]:
    """Run a single ground truth query and collect metrics.

    Args:
        qa: Ground truth question dict
        verbose: Print detailed output

    Returns:
        Dict with query results and metrics
    """
    query_id = qa["id"]
    question = qa["question"]

    if verbose:
        print(f"\n[Query {query_id}] {question}")

    # Measure query latency
    start_time = time.perf_counter()
    try:
        # Call search_documents directly (returns list[QueryResult])
        query_results = await search_documents(query=question, top_k=5)

        # Generate citations (modifies text field in-place)
        query_results = await generate_citations(query_results)

        # Create QueryResponse-like object
        class SimpleResponse:
            def __init__(self, results):
                self.results = results

        response = SimpleResponse(query_results)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Check retrieval accuracy
        retrieval_result = check_retrieval_accuracy(qa, response.results)

        # Check attribution accuracy
        attribution_result = check_attribution_accuracy(qa, response.results)

        if verbose:
            print(f"  Latency: {latency_ms:.2f}ms")
            print(
                f"  Retrieval: {'✓ PASS' if retrieval_result['pass_'] else '✗ FAIL'} - {retrieval_result['reason']}"
            )
            print(
                f"  Attribution: {'✓ PASS' if attribution_result['pass_'] else '✗ FAIL'} - {attribution_result['reason']}"
            )
            print(f"  Results: {len(response.results)} chunks returned")

        return {
            "query_id": query_id,
            "question": question,
            "category": qa["category"],
            "difficulty": qa["difficulty"],
            "latency_ms": latency_ms,
            "retrieval": retrieval_result,
            "attribution": attribution_result,
            "num_results": len(response.results),
            "top_score": response.results[0].score if response.results else 0.0,
            "error": None,
        }

    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        error_msg = f"{type(e).__name__}: {str(e)}"

        if verbose:
            print(f"  ✗ ERROR: {error_msg}")

        return {
            "query_id": query_id,
            "question": question,
            "category": qa["category"],
            "difficulty": qa["difficulty"],
            "latency_ms": latency_ms,
            "retrieval": {"pass": False, "reason": error_msg},
            "attribution": {"pass": False, "reason": error_msg},
            "num_results": 0,
            "top_score": 0.0,
            "error": error_msg,
        }


# Performance metrics calculation imported from accuracy_utils


async def main() -> int:
    """Main test runner function."""
    args = parse_args()

    print("=" * 60)
    print("RAGLite Accuracy Validation Test Suite")
    print("=" * 60)

    # Load and filter queries
    queries = filter_queries(GROUND_TRUTH_QA, args)
    print(f"\nRunning {len(queries)} queries...\n")

    # Run all queries
    results = []
    for qa in queries:
        result = await run_single_query(qa, verbose=args.verbose)
        results.append(result)

    # Calculate metrics
    metrics = calculate_performance_metrics(results)

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Queries:         {metrics['total_queries']}")
    print(
        f"Retrieval Accuracy:    {metrics['retrieval_accuracy']:.1f}% ({metrics['retrieval_pass']}/{metrics['total_queries']} pass)"
    )
    print(
        f"Attribution Accuracy:  {metrics['attribution_accuracy']:.1f}% ({metrics['attribution_pass']}/{metrics['total_queries']} pass)"
    )
    print(f"p50 Latency:           {metrics['p50_latency_ms']:.2f}ms")
    print(f"p95 Latency:           {metrics['p95_latency_ms']:.2f}ms")
    print(f"Errors:                {metrics['errors']}")

    # Check NFR targets (imported constants)
    print("\n" + "-" * 60)
    print("NFR VALIDATION")
    print("-" * 60)
    nfr_status = check_nfr_compliance(metrics)
    print(f"NFR6 (≥90% retrieval):      {'✓ PASS' if nfr_status['nfr6_retrieval'] else '✗ FAIL'}")
    print(f"NFR7 (≥95% attribution):    {'✓ PASS' if nfr_status['nfr7_attribution'] else '✗ FAIL'}")
    print(f"NFR13 (p50 <5s):            {'✓ PASS' if nfr_status['nfr13_p50'] else '✗ FAIL'}")
    print(f"NFR13 (p95 <15s):           {'✓ PASS' if nfr_status['nfr13_p95'] else '✗ FAIL'}")

    # Save results to file if requested
    if args.output:
        output_data = {
            "metrics": metrics,
            "results": results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {args.output}")

    # Determine exit code
    all_pass = (
        metrics["retrieval_accuracy"] >= NFR6_RETRIEVAL_TARGET
        and metrics["attribution_accuracy"] >= NFR7_ATTRIBUTION_TARGET
        and metrics["errors"] == 0
    )

    if all_pass:
        print("\n✓ ALL TESTS PASS")
        return 0
    else:
        print("\n✗ TESTS FAIL")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
