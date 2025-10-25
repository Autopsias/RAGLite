#!/usr/bin/env python3
"""Test metadata-aware search with 15-field rich schema.

Tests various metadata filter combinations on 10-page PDF collection.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.retrieval.search import search_documents  # noqa: E402


async def main():
    """Test metadata-aware search with various filter combinations."""
    print("=" * 80)
    print("METADATA-AWARE SEARCH TEST - 15 RICH FIELDS")
    print("=" * 80)
    print("\nTesting on 10-page PDF collection with rich metadata extraction")
    print()

    # Test cases with different metadata filter combinations
    test_cases = [
        {
            "name": "Baseline (No Filters)",
            "query": "What is the total revenue?",
            "filters": None,
        },
        {
            "name": "Filter by metric_category (Revenue)",
            "query": "What is the total revenue?",
            "filters": {"metric_category": "Revenue"},
        },
        {
            "name": "Filter by section_type (Table)",
            "query": "Show me financial tables",
            "filters": {"section_type": "Table"},
        },
        {
            "name": "Filter by time_granularity (YTD)",
            "query": "Year-to-date performance",
            "filters": {"time_granularity": "YTD"},
        },
        {
            "name": "Combined: metric_category + section_type",
            "query": "Show revenue tables",
            "filters": {"metric_category": "Revenue", "section_type": "Table"},
        },
        {
            "name": "Combined: metric_category + time_granularity",
            "query": "YTD EBITDA performance",
            "filters": {"metric_category": "EBITDA", "time_granularity": "YTD"},
        },
        {
            "name": "Filter by document_type (Operational Report)",
            "query": "Operational metrics",
            "filters": {"document_type": "Operational Report"},
        },
        {
            "name": "Filter by company_name (Secil)",
            "query": "Secil performance",
            "filters": {"company_name": "Secil"},
        },
        {
            "name": "Combined: company_name + metric_category",
            "query": "Secil Group revenue",
            "filters": {"company_name": "Secil Group", "metric_category": "Revenue"},
        },
        {
            "name": "Filter by units (EUR)",
            "query": "Financial data in euros",
            "filters": {"units": "EUR"},
        },
    ]

    results_summary = []

    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {idx}: {test_case['name']}")
        print(f"{'=' * 80}")
        print(f"Query: {test_case['query']}")
        print(f"Filters: {test_case['filters']}")
        print()

        try:
            results = await search_documents(
                query=test_case["query"],
                top_k=3,  # Limit to top 3 for readability
                filters=test_case["filters"],
            )

            print(f"✅ Found {len(results)} results\n")

            for i, result in enumerate(results, 1):
                print(f"  Result {i} (score: {result.score:.4f}):")
                print(f"    Source: {result.source_document}, Page: {result.page_number}")
                print(f"    Content preview: {result.text[:150]}...")
                print()

            results_summary.append(
                {
                    "test": test_case["name"],
                    "filters": test_case["filters"],
                    "count": len(results),
                    "top_score": results[0].score if results else 0.0,
                }
            )

        except Exception as e:
            print(f"❌ ERROR: {e}")
            results_summary.append(
                {
                    "test": test_case["name"],
                    "filters": test_case["filters"],
                    "count": 0,
                    "top_score": 0.0,
                    "error": str(e),
                }
            )

    # Summary table
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Test':<50} {'Filters':>10} {'Count':>8} {'Top Score':>12}")
    print("-" * 80)

    for summary in results_summary:
        test_name = summary["test"][:48]
        filter_count = len(summary["filters"]) if summary["filters"] else 0
        result_count = summary["count"]
        top_score = summary["top_score"]

        if "error" in summary:
            print(f"{test_name:<50} {filter_count:>10} {'ERROR':>8} {'N/A':>12}")
        else:
            print(f"{test_name:<50} {filter_count:>10} {result_count:>8} {top_score:>12.4f}")

    print("\n" + "=" * 80)
    print("✅ METADATA-AWARE SEARCH TEST COMPLETE")
    print("=" * 80)
    print("\nNOTE: Filters reduce result count by excluding non-matching chunks.")
    print("This is expected behavior - filtering trades recall for precision.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
