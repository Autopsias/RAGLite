#!/usr/bin/env python3
"""
Validate ground truth page references using Qdrant retrieval.

This script validates the expected_page_number field in ground truth questions
by querying Qdrant with the question text and comparing the page numbers of
the top-ranking chunks to the expected values.

Strategy:
1. Embed each ground truth question using the same embedding model (Fin-E5)
2. Query Qdrant for top-5 chunks
3. Extract page numbers from chunk metadata
4. Compare to expected_page_number
5. Generate validation report with corrections

Usage:
    uv run python scripts/validate-pages-via-qdrant.py

Output:
    - Console report with validation results
    - Corrections needed (question ID, old page, new page)
    - Validation worksheet markdown file
"""

import sys
from collections import Counter
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from qdrant_client import QdrantClient  # noqa: E402

from raglite.shared.clients import get_embedding_model  # noqa: E402
from raglite.shared.config import settings  # noqa: E402
from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402


def validate_question(qa: dict, client: QdrantClient, embedding_model) -> dict:
    """
    Validate a single question by querying Qdrant and checking page numbers.

    Args:
        qa: Ground truth question dict
        client: Qdrant client
        embedding_model: SentenceTransformer model for embeddings

    Returns:
        dict with validation results
    """
    question_id = qa["id"]
    question_text = qa["question"]
    expected_page = qa["expected_page_number"]
    category = qa["category"]

    # Embed the question
    query_vector = embedding_model.encode([question_text])[0]

    # Query Qdrant for top-5 chunks
    search_results = client.search(
        collection_name="documents",
        query_vector=query_vector.tolist(),
        limit=5,
        with_payload=True,
    )

    # Extract page numbers from results
    pages_found = []
    for result in search_results:
        page_num = result.payload.get("page_number")
        if page_num:
            pages_found.append(page_num)

    # Determine most common page (mode)
    if pages_found:
        page_counter = Counter(pages_found)
        actual_page = page_counter.most_common(1)[0][0]
        confidence = page_counter[actual_page] / len(pages_found)
    else:
        actual_page = None
        confidence = 0.0

    # Check if correction needed
    needs_correction = actual_page is not None and actual_page != expected_page

    return {
        "question_id": question_id,
        "question": question_text,
        "category": category,
        "expected_page": expected_page,
        "actual_page": actual_page,
        "pages_found": pages_found,
        "confidence": confidence,
        "needs_correction": needs_correction,
        "status": "incorrect"
        if needs_correction
        else ("correct" if actual_page == expected_page else "missing"),
    }


def main():
    """Main validation workflow."""
    print("=" * 80)
    print("GROUND TRUTH PAGE VALIDATION VIA QDRANT - Story 2.9")
    print("=" * 80)
    print()
    print(f"Validating {len(GROUND_TRUTH_QA)} ground truth questions...")
    print()

    # Initialize clients
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    # Check collection exists
    collections = client.get_collections().collections
    if not any(c.name == "documents" for c in collections):
        print("❌ Error: 'documents' collection not found in Qdrant")
        print("   Please run ingestion first: uv run python -m raglite.ingestion.pipeline")
        return

    # Get embedding model
    print("Loading embedding model...")
    embedding_model = get_embedding_model()
    print("✅ Model loaded")
    print()

    # Group questions by category
    by_category = {}
    for qa in GROUND_TRUTH_QA:
        category = qa["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(qa)

    # Validation results
    all_results = []

    # Validate each category
    for category, questions in sorted(by_category.items()):
        print(f"\n📋 Category: {category.upper()} ({len(questions)} questions)")
        print("-" * 80)

        for qa in questions:
            result = validate_question(qa, client, embedding_model)
            all_results.append(result)

            # Print result
            q_id = result["question_id"]
            expected = result["expected_page"]
            actual = result["actual_page"]
            status = result["status"]

            if status == "correct":
                print(f"  ✅ Q{q_id:2d}: Page {expected} CORRECT")
            elif status == "incorrect":
                print(
                    f"  ❌ Q{q_id:2d}: Page {expected} → {actual} NEEDS CORRECTION (confidence: {result['confidence']:.1%})"
                )
            else:
                print(f"  ⚠️  Q{q_id:2d}: Page {expected} UNCERTAIN (no clear match)")

    # Summary statistics
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()

    total = len(all_results)
    correct = sum(1 for r in all_results if r["status"] == "correct")
    incorrect = sum(1 for r in all_results if r["status"] == "incorrect")
    missing = sum(1 for r in all_results if r["status"] == "missing")

    print(f"Total questions: {total}")
    print(f"Correct page references: {correct} ({correct / total * 100:.1f}%)")
    print(f"Incorrect page references: {incorrect} ({incorrect / total * 100:.1f}%)")
    print(f"Uncertain/missing: {missing} ({missing / total * 100:.1f}%)")
    print()

    # Corrections needed
    corrections = [r for r in all_results if r["needs_correction"]]

    if corrections:
        print(f"\n📝 CORRECTIONS NEEDED: {len(corrections)} questions")
        print("-" * 80)

        # Group by category
        corrections_by_category = {}
        for corr in corrections:
            cat = corr["category"]
            if cat not in corrections_by_category:
                corrections_by_category[cat] = []
            corrections_by_category[cat].append(corr)

        for category, corrs in sorted(corrections_by_category.items()):
            print(f"\n{category.upper()}:")
            for c in corrs:
                print(f"  Q{c['question_id']:2d}: Page {c['expected_page']} → {c['actual_page']}")
    else:
        print("\n✅ All page references are correct!")

    # Create validation worksheet
    worksheet_path = project_root / "docs" / "validation" / "story-2.9-page-validation.md"
    worksheet_path.parent.mkdir(parents=True, exist_ok=True)

    with open(worksheet_path, "w") as f:
        f.write("# Story 2.9: Ground Truth Page Validation Results\n\n")
        f.write("**Validation Date:** 2025-10-25\n")
        f.write("**Validation Method:** Qdrant retrieval (top-5 chunks)\n")
        f.write(f"**Total Questions:** {total}\n\n")

        f.write("## Summary Statistics\n\n")
        f.write(f"- **Correct:** {correct} ({correct / total * 100:.1f}%)\n")
        f.write(f"- **Incorrect:** {incorrect} ({incorrect / total * 100:.1f}%)\n")
        f.write(f"- **Uncertain:** {missing} ({missing / total * 100:.1f}%)\n\n")

        f.write("## Validation Results by Category\n\n")

        for category, _ in sorted(by_category.items()):
            f.write(f"### {category.upper()}\n\n")
            f.write("| Q# | Current Page | Actual Page | Status | Confidence | Notes |\n")
            f.write("|----|--------------|-------------|--------|------------|-------|\n")

            category_results = [r for r in all_results if r["category"] == category]
            for result in category_results:
                q_id = result["question_id"]
                expected = result["expected_page"]
                actual = result["actual_page"] if result["actual_page"] else "?"
                status = result["status"]
                confidence = f"{result['confidence']:.0%}" if result["actual_page"] else "N/A"
                pages_str = ", ".join(str(p) for p in result["pages_found"][:3])
                notes = f"Top pages: {pages_str}" if result["pages_found"] else "No matches"

                f.write(f"| {q_id} | {expected} | {actual} | {status} | {confidence} | {notes} |\n")

            f.write("\n")

        f.write("## Corrections List\n\n")

        if corrections:
            f.write("Questions requiring page number corrections:\n\n")
            for corr in corrections:
                f.write(
                    f"- Q{corr['question_id']:2d}: {corr['expected_page']} → {corr['actual_page']} "
                )
                f.write(f"({corr['category']}, confidence: {corr['confidence']:.0%})\n")
        else:
            f.write("No corrections needed - all page references are correct!\n")

        f.write("\n---\n\n")
        f.write("**Next Steps:**\n")
        f.write("1. Review corrections list\n")
        f.write("2. Apply corrections to `tests/fixtures/ground_truth.py`\n")
        f.write("3. Proceed to Story 2.9 AC2 (Update Ground Truth File)\n")

    print(f"\n📄 Validation worksheet saved: {worksheet_path}")
    print()

    return all_results


if __name__ == "__main__":
    main()
