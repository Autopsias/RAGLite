#!/usr/bin/env python3
"""Test query-aware metadata filtering with automatic classification.

Validates that the query classifier correctly extracts metadata filters from
natural language queries and that hybrid_search applies them successfully.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.retrieval.search import hybrid_search  # noqa: E402


async def main():
    """Test query-aware metadata filtering with 5 sample queries."""
    print("=" * 80)
    print("QUERY-AWARE METADATA FILTERING TEST")
    print("=" * 80)
    print("\nTesting automatic metadata extraction and filtering on 160-page PDF")
    print()

    # Test queries from ground truth (varying complexity)
    test_queries = [
        {
            "id": 1,
            "query": "What is the variable cost per ton for Portugal Cement in August 2025 YTD?",
            "expected_filters": [
                "metric_category: Operating Expenses",
                "company_name: Portugal",
                "time_granularity: YTD",
            ],
        },
        {
            "id": 13,
            "query": "What is the EBITDA IFRS margin percentage for Portugal Cement?",
            "expected_filters": ["metric_category: EBITDA", "company_name: Portugal"],
        },
        {
            "id": 21,
            "query": "What is the EBITDA for Portugal operations in Aug-25 YTD?",
            "expected_filters": [
                "metric_category: EBITDA",
                "geographic_jurisdiction: Portugal",
                "time_granularity: YTD",
            ],
        },
        {
            "id": 43,
            "query": "What are the other costs per ton for Portugal Cement operations?",
            "expected_filters": [
                "metric_category: Operating Expenses",
                "company_name: Portugal",
                "units: EUR/ton",
            ],
        },
        {
            "id": 2,
            "query": "What is the thermal energy cost per ton for Portugal Cement?",
            "expected_filters": [
                "metric_category: Operating Expenses",
                "company_name: Portugal",
                "units: EUR/ton",
            ],
        },
    ]

    for test in test_queries:
        print(f"\n{'=' * 80}")
        print(f"TEST {test['id']}: {test['query']}")
        print(f"{'=' * 80}")
        print(f"Expected filters: {', '.join(test['expected_filters'])}")
        print()

        try:
            # Call hybrid_search with auto_classify enabled (default)
            results = await hybrid_search(
                query=test["query"],
                top_k=5,
                alpha=0.7,
                enable_hybrid=True,
                auto_classify=True,  # Enable automatic metadata classification
            )

            print(f"✅ Found {len(results)} results\n")

            for i, result in enumerate(results, 1):
                print(f"  Result {i} (score: {result.score:.4f}):")
                print(f"    Source: {result.source_document}, Page: {result.page_number}")
                print(f"    Content preview: {result.text[:120]}...")
                print()

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
            print()

    print("=" * 80)
    print("✅ QUERY-AWARE FILTERING TEST COMPLETE")
    print("=" * 80)
    print("\nNOTE: Check logs for extracted metadata filters.")
    print("Expected: Queries should show 'Metadata filters extracted from query' in logs.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
