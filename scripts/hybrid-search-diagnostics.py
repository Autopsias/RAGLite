#!/usr/bin/env python3
"""Hybrid Search Diagnostics - Analyze BM25 vs semantic score contributions.

Analyzes which retrieval method (BM25 or semantic) drives accuracy for each query
and generates fusion parameter (alpha) recommendations.

NOTE: This script requires Story 2.1 (Hybrid Search) to be implemented.
      Before Story 2.1, it will only analyze semantic search performance.

Usage:
    # Run diagnostics on full ground truth suite
    uv run python scripts/hybrid-search-diagnostics.py

    # Run diagnostics on subset of queries
    uv run python scripts/hybrid-search-diagnostics.py --subset 15

    # Save detailed results to JSON
    uv run python scripts/hybrid-search-diagnostics.py --output diagnostics.json

Exit codes:
    0 - Diagnostics completed successfully
    1 - Error encountered
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze BM25 vs semantic search contributions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--subset",
        type=int,
        metavar="N",
        help="Run diagnostics on N queries only",
    )
    parser.add_argument(
        "--output",
        type=str,
        metavar="FILE",
        help="Save detailed results to JSON file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-query details",
    )
    return parser.parse_args()


async def run_hybrid_search_diagnostic(query: str) -> dict[str, Any]:
    """Run hybrid search with score breakdown.

    NOTE: This function assumes Story 2.1 hybrid search is implemented.
          If not implemented, it will only return semantic scores.

    Args:
        query: Query string

    Returns:
        Dict with BM25 score, semantic score, and hybrid score
    """
    try:
        # Import hybrid search function (will fail before Story 2.1)
        from raglite.retrieval.search import hybrid_search  # noqa: F401

        # Run hybrid search with score breakdown
        # (This is the EXPECTED API after Story 2.1 implementation)
        results = await hybrid_search(query, top_k=5, return_scores=True)

        # Extract scores
        bm25_scores = [r.bm25_score for r in results if hasattr(r, "bm25_score")]
        semantic_scores = [r.semantic_score for r in results if hasattr(r, "semantic_score")]
        hybrid_scores = [r.score for r in results]

        return {
            "bm25_available": len(bm25_scores) > 0,
            "bm25_score": max(bm25_scores) if bm25_scores else 0.0,
            "semantic_score": max(semantic_scores) if semantic_scores else 0.0,
            "hybrid_score": max(hybrid_scores) if hybrid_scores else 0.0,
            "num_results": len(results),
        }

    except ImportError:
        # Story 2.1 not implemented yet, fall back to semantic-only
        from raglite.retrieval.search import search_documents

        results = await search_documents(query, top_k=5)
        semantic_scores = [r.score for r in results]

        return {
            "bm25_available": False,
            "bm25_score": 0.0,
            "semantic_score": max(semantic_scores) if semantic_scores else 0.0,
            "hybrid_score": 0.0,
            "num_results": len(results),
        }


async def analyze_query(qa: dict[str, Any], verbose: bool = False) -> dict[str, Any]:
    """Analyze a single query's BM25 vs semantic contributions.

    Args:
        qa: Ground truth question dict
        verbose: Print verbose output

    Returns:
        Dict with analysis results
    """
    query = qa["question"]

    if verbose:
        print(f"\n[Query {qa['id']}] {query}")

    # Run hybrid search diagnostic
    scores = await run_hybrid_search_diagnostic(query)

    # Determine dominant method
    if not scores["bm25_available"]:
        dominant = "semantic-only"
        dominance_ratio = 1.0
    elif scores["bm25_score"] > scores["semantic_score"] * 1.5:
        dominant = "bm25"
        dominance_ratio = scores["bm25_score"] / max(scores["semantic_score"], 0.01)
    elif scores["semantic_score"] > scores["bm25_score"] * 1.5:
        dominant = "semantic"
        dominance_ratio = scores["semantic_score"] / max(scores["bm25_score"], 0.01)
    else:
        dominant = "balanced"
        dominance_ratio = 1.0

    if verbose:
        if scores["bm25_available"]:
            print(
                f"  BM25: {scores['bm25_score']:.4f}, Semantic: {scores['semantic_score']:.4f}, "
                f"Hybrid: {scores['hybrid_score']:.4f}"
            )
            print(f"  Dominant: {dominant} (ratio: {dominance_ratio:.2f}x)")
        else:
            print(f"  Semantic-only: {scores['semantic_score']:.4f} (Story 2.1 not implemented)")

    return {
        "query_id": qa["id"],
        "question": query,
        "category": qa["category"],
        "bm25_score": scores["bm25_score"],
        "semantic_score": scores["semantic_score"],
        "hybrid_score": scores["hybrid_score"],
        "dominant": dominant,
        "dominance_ratio": dominance_ratio,
    }


def calculate_fusion_recommendation(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate recommended fusion alpha parameter.

    Args:
        results: List of query analysis results

    Returns:
        Dict with fusion recommendations
    """
    if not results or not results[0].get("bm25_score", 0.0) > 0:
        return {
            "recommended_alpha": 0.7,
            "reason": "Story 2.1 not implemented - using default alpha=0.7 (70% semantic)",
        }

    # Count dominant methods
    bm25_dominant = sum(1 for r in results if r["dominant"] == "bm25")
    semantic_dominant = sum(1 for r in results if r["dominant"] == "semantic")
    balanced = sum(1 for r in results if r["dominant"] == "balanced")

    # Calculate recommended alpha (higher alpha = more semantic weight)
    total = len(results)
    semantic_ratio = (semantic_dominant + balanced / 2) / total
    recommended_alpha = 0.5 + (semantic_ratio - 0.5) * 0.4  # Scale to 0.3-0.7 range

    # Clamp to reasonable range
    recommended_alpha = max(0.3, min(0.7, recommended_alpha))

    return {
        "recommended_alpha": recommended_alpha,
        "bm25_dominant_count": bm25_dominant,
        "semantic_dominant_count": semantic_dominant,
        "balanced_count": balanced,
        "reason": f"Based on {bm25_dominant} BM25-dominant, {semantic_dominant} semantic-dominant, {balanced} balanced queries",
    }


def print_diagnostics_summary(results: list[dict[str, Any]], fusion_rec: dict[str, Any]) -> None:
    """Print diagnostics summary.

    Args:
        results: List of query analysis results
        fusion_rec: Fusion recommendation dict
    """
    if not results:
        print("No results to analyze.")
        return

    total = len(results)
    bm25_available = results[0].get("bm25_score", 0.0) > 0

    print("=" * 70)
    print(f"Hybrid Search Diagnostics ({total} queries)")
    print("=" * 70)

    if not bm25_available:
        print("\n⚠️  Story 2.1 (Hybrid Search) not implemented yet")
        print("   This diagnostic will be fully functional after Story 2.1 completion")
        print("\nCurrent Status: Semantic-only search")
        semantic_avg = sum(r["semantic_score"] for r in results) / total
        print(f"  Average semantic score: {semantic_avg:.4f}")
        print("\n" + "=" * 70)
        return

    # Categorize queries
    bm25_dominant = [r for r in results if r["dominant"] == "bm25"]
    semantic_dominant = [r for r in results if r["dominant"] == "semantic"]
    balanced = [r for r in results if r["dominant"] == "balanced"]

    print(
        f"\nBM25 Dominant: {len(bm25_dominant)} queries ({len(bm25_dominant) / total * 100:.0f}%)"
    )
    if bm25_dominant:
        example = bm25_dominant[0]
        print(f'  Example: "{example["question"][:60]}..."')
        print(
            f"           (BM25: {example['bm25_score']:.4f}, Semantic: {example['semantic_score']:.4f})"
        )

    print(
        f"\nSemantic Dominant: {len(semantic_dominant)} queries ({len(semantic_dominant) / total * 100:.0f}%)"
    )
    if semantic_dominant:
        example = semantic_dominant[0]
        print(f'  Example: "{example["question"][:60]}..."')
        print(
            f"           (BM25: {example['bm25_score']:.4f}, Semantic: {example['semantic_score']:.4f})"
        )

    print(f"\nBalanced: {len(balanced)} queries ({len(balanced) / total * 100:.0f}%)")
    if balanced:
        example = balanced[0]
        print(f'  Example: "{example["question"][:60]}..."')
        print(
            f"           (BM25: {example['bm25_score']:.4f}, Semantic: {example['semantic_score']:.4f})"
        )

    print("\n" + "-" * 70)
    print("FUSION PARAMETER RECOMMENDATION")
    print("-" * 70)
    print(
        f"Recommended Alpha: {fusion_rec['recommended_alpha']:.2f} "
        f"({fusion_rec['recommended_alpha'] * 100:.0f}% semantic, {(1 - fusion_rec['recommended_alpha']) * 100:.0f}% BM25)"
    )
    print(f"Rationale: {fusion_rec['reason']}")
    print("=" * 70)


async def main() -> int:
    """Main function."""
    args = parse_args()

    # Load queries
    queries = GROUND_TRUTH_QA
    if args.subset and args.subset < len(queries):
        queries = queries[: args.subset]
        print(f"Running diagnostics on {args.subset} queries...\n")
    else:
        print(f"Running diagnostics on {len(queries)} queries...\n")

    # Analyze all queries
    results = []
    for qa in queries:
        result = await analyze_query(qa, verbose=args.verbose)
        results.append(result)

    # Calculate fusion recommendation
    fusion_rec = calculate_fusion_recommendation(results)

    # Print summary
    print()
    print_diagnostics_summary(results, fusion_rec)

    # Save to file if requested
    if args.output:
        output_data = {
            "results": results,
            "fusion_recommendation": fusion_rec,
            "total_queries": len(results),
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nDetailed results saved to: {args.output}")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
