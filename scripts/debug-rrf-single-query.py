"""Debug RRF implementation with a single ground truth query.

Traces end-to-end execution to identify why retrieval accuracy is 0%.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from raglite.retrieval.search import hybrid_search
from tests.fixtures.ground_truth import GROUND_TRUTH_QA


async def debug_single_query():
    """Debug a single query to trace RRF execution."""

    # Use first query from ground truth
    qa = GROUND_TRUTH_QA[0]
    query = qa["question"]
    expected_page = qa["expected_page_number"]

    print("=" * 80)
    print("RRF DEBUG - SINGLE QUERY")
    print("=" * 80)
    print(f"\nQuery: {query}")
    print(f"Expected page: {expected_page}")
    print(f"Source: {qa['source_document']}")
    print("\n" + "=" * 80)

    # Run hybrid search with alpha=0.7 (default)
    print("\nRunning hybrid_search() with alpha=0.7...")
    results = await hybrid_search(query, top_k=5, alpha=0.7, auto_classify=False)

    print(f"\nReturned {len(results)} results")
    print("\n" + "=" * 80)
    print("RETRIEVED PAGES:")
    print("=" * 80)

    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"  Page: {result.page_number}")
        print(f"  Score: {result.score:.6f}")
        print(f"  Source: {result.source_document}")
        print(f"  Chunk index: {result.chunk_index}")
        print(f"  Text preview: {result.chunk_text[:100]}...")

    # Check if expected page in results
    retrieved_pages = [r.page_number for r in results]

    print("\n" + "=" * 80)
    print("ACCURACY CHECK:")
    print("=" * 80)
    print(f"\nExpected page: {expected_page}")
    print(f"Retrieved pages: {retrieved_pages}")

    if expected_page in retrieved_pages:
        rank = retrieved_pages.index(expected_page) + 1
        print(f"\n✅ SUCCESS: Expected page found at rank {rank}")
    else:
        print(f"\n❌ FAILURE: Expected page {expected_page} NOT in top-5 results")
        print("   This explains the 0% accuracy!")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_single_query())
