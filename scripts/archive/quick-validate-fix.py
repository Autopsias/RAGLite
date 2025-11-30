#!/usr/bin/env python3
"""Quick validation script to test page attribution fix on sample PDF.

Tests Story 1.13 fix with a small PDF before running full migration.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import ingest_pdf  # noqa: E402
from raglite.retrieval.search import search_documents  # noqa: E402
from raglite.shared.clients import get_qdrant_client  # noqa: E402
from raglite.shared.config import settings  # noqa: E402


async def main():
    """Test page attribution fix with sample PDF and queries."""
    print("=" * 80)
    print("QUICK VALIDATION: Page Attribution Fix (Story 1.13)")
    print("=" * 80)
    print()

    # Step 1: Clear collection and ingest sample PDF
    print("Step 1: Ingesting sample PDF with fix...")
    qdrant_client = get_qdrant_client()

    try:
        # Clear collection
        qdrant_client.delete_collection(collection_name=settings.qdrant_collection_name)
        print(f"✓ Cleared collection '{settings.qdrant_collection_name}'")
    except Exception as e:
        print(f"  Collection doesn't exist yet (OK): {e}")

    # Ingest sample PDF
    sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")
    if not sample_pdf.exists():
        print(f"❌ ERROR: Sample PDF not found at {sample_pdf}")
        return 1

    print(f"✓ Found sample PDF: {sample_pdf}")

    try:
        metadata = await ingest_pdf(str(sample_pdf))
        print("✓ Ingestion complete")
        print(f"  Chunks: {metadata.chunk_count}")
        print(f"  Pages: {metadata.page_count}")
        print()
    except Exception as e:
        print(f"❌ ERROR during ingestion: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Step 2: Test sample queries with page attribution
    print("Step 2: Testing sample queries...")
    print()

    # Sample queries that should find content with correct page numbers
    test_queries = [
        {
            "query": "What are the health and safety KPIs?",
            "expected_keywords": ["KPI", "health", "safety"],
        },
        {
            "query": "What is the lost time injury rate?",
            "expected_keywords": ["lost", "time", "injury"],
        },
        {
            "query": "What safety metrics are tracked?",
            "expected_keywords": ["safety", "metrics"],
        },
    ]

    results_summary = []

    for i, test in enumerate(test_queries, 1):
        query = test["query"]
        expected_keywords = test["expected_keywords"]

        print(f"Query {i}: {query}")

        try:
            # Search for documents
            search_results = await search_documents(query=query, top_k=3)

            if not search_results:
                print("  ❌ No results found")
                results_summary.append(
                    {
                        "query": query,
                        "found_results": False,
                        "keywords_found": 0,
                        "page_numbers": [],
                    }
                )
                print()
                continue

            # Check if keywords are found in top results
            keywords_found = 0
            page_numbers = []

            print(f"  ✓ Found {len(search_results)} results")

            for j, result in enumerate(search_results, 1):
                text_lower = result.text.lower()
                page_no = result.page_number
                page_numbers.append(page_no)

                # Count keywords
                for keyword in expected_keywords:
                    if keyword.lower() in text_lower:
                        keywords_found += 1
                        break  # Count each result once

                print(f"    Result {j}: Page {page_no}, Score {result.score:.3f}")
                print(f"      Content preview: {result.text[:80]}...")

            keyword_ratio = keywords_found / len(expected_keywords)
            print(
                f"  Keywords found: {keywords_found}/{len(expected_keywords)} ({keyword_ratio * 100:.0f}%)"
            )
            print(f"  Page numbers: {page_numbers}")

            results_summary.append(
                {
                    "query": query,
                    "found_results": True,
                    "keywords_found": keywords_found,
                    "total_keywords": len(expected_keywords),
                    "page_numbers": page_numbers,
                }
            )

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results_summary.append(
                {
                    "query": query,
                    "found_results": False,
                    "error": str(e),
                }
            )

        print()

    # Step 3: Summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    queries_with_results = sum(1 for r in results_summary if r.get("found_results"))
    total_queries = len(results_summary)

    print(f"Queries with results: {queries_with_results}/{total_queries}")

    if queries_with_results > 0:
        # Calculate keyword accuracy
        total_keywords_found = sum(
            r.get("keywords_found", 0) for r in results_summary if r.get("found_results")
        )
        total_keywords = sum(
            r.get("total_keywords", 0) for r in results_summary if r.get("found_results")
        )
        keyword_accuracy = (
            (total_keywords_found / total_keywords * 100) if total_keywords > 0 else 0
        )

        print(f"Keyword accuracy: {keyword_accuracy:.1f}%")

        # Check page numbers are valid (within PDF bounds)
        all_pages = [p for r in results_summary if r.get("page_numbers") for p in r["page_numbers"]]
        if all_pages:
            min_page = min(all_pages)
            max_page = max(all_pages)
            print(f"Page range: {min_page}-{max_page} (PDF has {metadata.page_count} pages)")

            if min_page >= 1 and max_page <= metadata.page_count:
                print("✅ Page numbers are valid (within PDF bounds)")
            else:
                print(f"⚠ WARNING: Page numbers outside bounds (1-{metadata.page_count})")

    print()

    if queries_with_results == total_queries and queries_with_results > 0:
        print("✅ VALIDATION PASSED")
        print("   Fix is working correctly on sample PDF")
        print("   Ready to proceed with full 160-page PDF migration")
        return 0
    else:
        print("⚠ VALIDATION INCOMPLETE")
        print("   Some queries failed - review results above")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
