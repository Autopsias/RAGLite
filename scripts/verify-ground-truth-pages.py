#!/usr/bin/env python3
"""Verify and recalibrate ground truth page numbers.

This script helps identify the correct page numbers for ground truth Q&A pairs
by querying Qdrant and comparing with expected pages.

Usage:
    python scripts/verify-ground-truth-pages.py
"""

import asyncio
import json
from pathlib import Path

from raglite.retrieval.search import hybrid_search
from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings
from tests.fixtures.ground_truth import GROUND_TRUTH_QA


async def verify_ground_truth_pages():
    """Verify ground truth page numbers against Qdrant data."""

    print("=" * 80)
    print("GROUND TRUTH PAGE NUMBER VERIFICATION")
    print("=" * 80)
    print()

    qdrant = get_qdrant_client()

    # Results storage
    verification_results = []
    page_offset_samples = []

    for i, question_data in enumerate(GROUND_TRUTH_QA[:10], 1):  # Start with first 10
        question = question_data["question"]
        expected_page = question_data["expected_page_number"]
        keywords = question_data["expected_keywords"]

        print(f"[{i}/10] Verifying Question ID {question_data['id']}")
        print(f"Question: {question[:80]}...")
        print(f"Expected page: {expected_page}")
        print()

        # Perform hybrid search
        results = await hybrid_search(query=question, top_k=5, alpha=0.7)

        if not results:
            print("   ⚠️  No results found")
            verification_results.append(
                {
                    "question_id": question_data["id"],
                    "expected_page": expected_page,
                    "found_pages": [],
                    "status": "no_results",
                    "recommendation": "Investigate query or data",
                }
            )
            print()
            continue

        # Get top-5 pages
        found_pages = [r.page_number for r in results]
        top_score = results[0].score

        print(f"   Retrieved pages (top-5): {found_pages}")
        print(f"   Top score: {top_score:.3f}")

        # Check if expected page is in top-5
        if expected_page in found_pages:
            rank = found_pages.index(expected_page) + 1
            print(f"   ✅ PASS - Expected page {expected_page} found at rank {rank}")
            status = "pass"
            recommendation = "No change needed"
        else:
            print(f"   ❌ FAIL - Expected page {expected_page} NOT in top-5")

            # Check what's on the expected page
            expected_page_result = qdrant.scroll(
                collection_name=settings.qdrant_collection_name,
                scroll_filter={"must": [{"key": "page_number", "match": {"value": expected_page}}]},
                limit=1,
                with_payload=True,
                with_vectors=False,
            )

            if expected_page_result[0]:
                expected_page_text = expected_page_result[0][0].payload.get("text", "")

                # Check if keywords are in expected page
                keywords_found = sum(
                    1 for kw in keywords if kw.lower() in expected_page_text.lower()
                )
                keywords_ratio = keywords_found / len(keywords) if keywords else 0

                print(f"   Expected page content preview: {expected_page_text[:100]}...")
                print(
                    f"   Keywords on expected page: {keywords_found}/{len(keywords)} ({keywords_ratio:.0%})"
                )

                if keywords_ratio < 0.3:
                    print("   🔍 LIKELY WRONG PAGE - Few keywords found")
                    status = "wrong_page"
                    recommendation = f"Consider page {found_pages[0]} instead"

                    # Calculate potential offset
                    if found_pages:
                        offset = found_pages[0] - expected_page
                        page_offset_samples.append(offset)
                        print(f"   Potential offset: {offset} pages")
                else:
                    print("   ⚠️  AMBIGUOUS - Keywords present but not in top-5")
                    status = "ambiguous"
                    recommendation = "Manual review needed"
            else:
                print(f"   ⚠️  Expected page {expected_page} not found in Qdrant")
                status = "missing_page"
                recommendation = "Verify PDF extraction"

        verification_results.append(
            {
                "question_id": question_data["id"],
                "question": question[:100],
                "expected_page": expected_page,
                "found_pages": found_pages,
                "top_score": float(top_score),
                "status": status,
                "recommendation": recommendation,
            }
        )

        print()

    # Summary statistics
    print("=" * 80)
    print("VERIFICATION SUMMARY (First 10 Questions)")
    print("=" * 80)

    status_counts = {}
    for result in verification_results:
        status = result["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"✅ Passed (expected page in top-5): {status_counts.get('pass', 0)}/10")
    print(f"❌ Wrong page (few keywords on expected page): {status_counts.get('wrong_page', 0)}/10")
    print(f"⚠️  Ambiguous (needs manual review): {status_counts.get('ambiguous', 0)}/10")
    print(f"⚠️  No results: {status_counts.get('no_results', 0)}/10")
    print()

    # Page offset analysis
    if page_offset_samples:
        avg_offset = sum(page_offset_samples) / len(page_offset_samples)
        print(f"Average page offset: {avg_offset:.1f} pages")
        print(f"Offset samples: {page_offset_samples}")
        print()
        print("💡 Recommendation:")
        if abs(avg_offset) > 2:
            print(f"   Systematic offset detected (~{avg_offset:.0f} pages)")
            print(f"   Consider applying offset: Docling page = PDF page + {avg_offset:.0f}")
        else:
            print("   No clear systematic offset - manual review recommended")

    # Export results
    output_file = Path("docs/stories/ground-truth-verification-results.json")
    with open(output_file, "w") as f:
        json.dump(
            {
                "summary": {
                    "total_verified": len(verification_results),
                    "passed": status_counts.get("pass", 0),
                    "wrong_page": status_counts.get("wrong_page", 0),
                    "ambiguous": status_counts.get("ambiguous", 0),
                    "no_results": status_counts.get("no_results", 0),
                    "average_offset": round(avg_offset, 1) if page_offset_samples else None,
                },
                "results": verification_results,
            },
            f,
            indent=2,
        )

    print()
    print(f"📄 Detailed results exported to: {output_file}")
    print()
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Review docs/stories/ground-truth-verification-results.json")
    print("2. Manually inspect PDF for questions marked as 'wrong_page'")
    print("3. Update tests/fixtures/ground_truth.py with correct page numbers")
    print("4. Rerun: bash scripts/run-ac2-decision-gate.sh")
    print()


if __name__ == "__main__":
    asyncio.run(verify_ground_truth_pages())
