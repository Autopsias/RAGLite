"""Debug hybrid search scoring bug.

Story 2.11 AC1: Diagnostic script to compare scores across search methods
and identify where score normalization is occurring.

Expected Bug: Hybrid and multi-index search return score=1.0 for all results,
while semantic search returns realistic scores (0.8-0.9 range).

Usage:
    python scripts/debug-hybrid-search-scoring.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from raglite.retrieval.multi_index_search import multi_index_search
from raglite.retrieval.search import hybrid_search, search_documents


async def debug_hybrid_search_scoring():
    """Debug hybrid search scoring bug.

    Compares scores across search methods to identify normalization bug.
    """
    test_query = "What is the EBITDA margin for Portugal Cement in August 2025?"

    print("=" * 80)
    print("HYBRID SEARCH SCORING BUG DIAGNOSTIC")
    print("=" * 80)
    print(f"\nTest Query: {test_query}")
    print("\n" + "=" * 80)

    # 1. Semantic search (baseline - should have realistic scores)
    print("\n1. SEMANTIC SEARCH (search_documents):")
    print("   Expected: Realistic scores in 0.7-0.9 range with variance")
    try:
        semantic_results = await search_documents(test_query, top_k=5)
        if semantic_results:
            for i, result in enumerate(semantic_results, 1):
                print(
                    f"  {i}. score={result.score:.4f} | page={result.page_number} | {result.text[:80]}..."
                )
        else:
            print("  No results returned")
    except Exception as e:
        print(f"  ERROR: {e}")

    # 2. Hybrid search (BUG - expected to have all scores 1.0)
    print("\n2. HYBRID SEARCH (hybrid_search):")
    print("   Expected Bug: All scores = 1.0 (normalization bug)")
    try:
        hybrid_results = await hybrid_search(test_query, top_k=5, auto_classify=False)
        if hybrid_results:
            for i, result in enumerate(hybrid_results, 1):
                print(
                    f"  {i}. score={result.score:.4f} | page={result.page_number} | {result.text[:80]}..."
                )
        else:
            print("  No results returned")
    except Exception as e:
        print(f"  ERROR: {e}")

    # 3. Multi-index search (BUG - expected to have all scores 1.0)
    print("\n3. MULTI-INDEX SEARCH (multi_index_search):")
    print("   Expected Bug: All scores = 1.0 (normalization bug)")
    try:
        multi_results = await multi_index_search(test_query, top_k=5)
        if multi_results:
            for i, result in enumerate(multi_results, 1):
                # SearchResult has different attribute names than QueryResult
                score = result.score
                page = result.page_number
                text = result.text[:80] if hasattr(result, "text") else str(result)[:80]
                print(f"  {i}. score={score:.4f} | page={page} | {text}...")
        else:
            print("  No results returned")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Analysis
    print("\n" + "=" * 80)
    print("\nANALYSIS:")
    print("=" * 80)

    # Calculate score statistics
    if semantic_results:
        semantic_scores = [r.score for r in semantic_results]
        print("\nSemantic Search Scores:")
        print(f"  Min: {min(semantic_scores):.4f}")
        print(f"  Max: {max(semantic_scores):.4f}")
        print(f"  Mean: {sum(semantic_scores) / len(semantic_scores):.4f}")
        # Calculate standard deviation
        mean = sum(semantic_scores) / len(semantic_scores)
        variance = sum((x - mean) ** 2 for x in semantic_scores) / len(semantic_scores)
        std = variance**0.5
        print(f"  Std Dev: {std:.4f}")

    if hybrid_results:
        hybrid_scores = [r.score for r in hybrid_results]
        print("\nHybrid Search Scores:")
        print(f"  Min: {min(hybrid_scores):.4f}")
        print(f"  Max: {max(hybrid_scores):.4f}")
        print(f"  Mean: {sum(hybrid_scores) / len(hybrid_scores):.4f}")
        mean = sum(hybrid_scores) / len(hybrid_scores)
        variance = sum((x - mean) ** 2 for x in hybrid_scores) / len(hybrid_scores)
        std = variance**0.5
        print(f"  Std Dev: {std:.4f}")

    if multi_results:
        multi_scores = [r.score for r in multi_results]
        print("\nMulti-Index Search Scores:")
        print(f"  Min: {min(multi_scores):.4f}")
        print(f"  Max: {max(multi_scores):.4f}")
        print(f"  Mean: {sum(multi_scores) / len(multi_scores):.4f}")
        mean = sum(multi_scores) / len(multi_scores)
        variance = sum((x - mean) ** 2 for x in multi_scores) / len(multi_scores)
        std = variance**0.5
        print(f"  Std Dev: {std:.4f}")

    # Bug detection
    print("\n" + "=" * 80)
    print("\nBUG DETECTION:")
    print("=" * 80)

    bugs_found = []

    # Check for score normalization bug (all scores = 1.0)
    if hybrid_results and all(abs(s - 1.0) < 0.0001 for s in hybrid_scores):
        print("\n⚠️  BUG CONFIRMED: All hybrid search scores are 1.0")
        print("   → Score normalization occurring in hybrid_search() or fuse_search_results()")
        bugs_found.append("hybrid_search")

    if multi_results and all(abs(s - 1.0) < 0.0001 for s in multi_scores):
        print("⚠️  BUG CONFIRMED: All multi-index search scores are 1.0")
        print("   → Score normalization occurring in multi_index_search() or merge_results()")
        bugs_found.append("multi_index_search")

    # Check for low variance (scores too similar)
    if hybrid_results:
        hybrid_scores = [r.score for r in hybrid_results]
        mean = sum(hybrid_scores) / len(hybrid_scores)
        variance = sum((x - mean) ** 2 for x in hybrid_scores) / len(hybrid_scores)
        std = variance**0.5
        if std < 0.05:
            print(f"\n⚠️  WARNING: Hybrid search has very low score variance (std={std:.4f})")
            print("   → Scores may be artificially normalized or not properly fused")

    # Check ranking differences
    if semantic_results and hybrid_results:
        semantic_pages = [r.page_number for r in semantic_results[:3]]
        hybrid_pages = [r.page_number for r in hybrid_results[:3]]

        if semantic_pages != hybrid_pages:
            print("\n⚠️  RANKING DIFFERENCE DETECTED:")
            print(f"   Semantic top-3 pages: {semantic_pages}")
            print(f"   Hybrid top-3 pages: {hybrid_pages}")
            print(
                "   → BM25 fusion may be changing ranking, but scores hidden by normalization bug"
            )

    # Summary
    print("\n" + "=" * 80)
    print("\nSUMMARY:")
    print("=" * 80)

    if bugs_found:
        print(f"\n✗ Bugs found in: {', '.join(bugs_found)}")
        print("\nNext Steps:")
        print("  1. Investigate score normalization in identified functions")
        print("  2. Remove score normalization (preserve raw fusion scores)")
        print("  3. Re-run this diagnostic to verify fix")
    else:
        print("\n✓ No obvious scoring bugs detected")
        print("\nNote: If scores look realistic but ranking is poor, investigate:")
        print("  - BM25 fusion weights (alpha parameter)")
        print("  - Metadata boosting logic")
        print("  - Query classification accuracy")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_hybrid_search_scoring())
