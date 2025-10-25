#!/usr/bin/env python3
"""
Validate ground truth page references by directly reading split PDF files.

This script validates the expected_page_number field in ground truth questions
by extracting text from split PDF files and searching for keywords.

Strategy:
1. Read split PDF files (4 parts, 40 pages each)
2. For each question, search for keywords in PDF text
3. Identify pages where keywords appear
4. Compare to expected_page_number
5. Generate validation report with corrections

Usage:
    uv run python scripts/validate-pages-direct.py

Output:
    - Console report with validation results
    - Validation worksheet markdown file
"""

import re
import sys
from collections import Counter
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pypdf import PdfReader  # noqa: E402

from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402


def load_split_pdfs():
    """Load all split PDF files and extract text by page."""
    split_dir = project_root / "docs" / "sample pdf" / "split"

    pdf_parts = [
        (
            "part01",
            split_dir / "2025-08 Performance Review CONSO_v2_part01_pages001-040.pdf",
            range(1, 41),
        ),
        (
            "part02",
            split_dir / "2025-08 Performance Review CONSO_v2_part02_pages041-080.pdf",
            range(41, 81),
        ),
        (
            "part03",
            split_dir / "2025-08 Performance Review CONSO_v2_part03_pages081-120.pdf",
            range(81, 121),
        ),
        (
            "part04",
            split_dir / "2025-08 Performance Review CONSO_v2_part04_pages121-160.pdf",
            range(121, 161),
        ),
    ]

    pages_text = {}  # page_number -> text

    print("📖 Loading split PDF files...")

    for part_name, pdf_path, page_range in pdf_parts:
        if not pdf_path.exists():
            print(f"   ⚠️  Warning: {pdf_path.name} not found, skipping")
            continue

        print(
            f"   Loading {part_name} (pages {page_range.start}-{page_range.stop - 1})...", end=" "
        )
        reader = PdfReader(pdf_path)

        for i, page in enumerate(reader.pages):
            actual_page_num = page_range.start + i
            text = page.extract_text()
            pages_text[actual_page_num] = text

        print(f"✅ {len(reader.pages)} pages")

    print(f"\n✅ Loaded {len(pages_text)} total pages")
    return pages_text


def find_keywords_in_pages(keywords: list[str], pages_text: dict) -> list[int]:
    """
    Find pages where keywords appear.

    Args:
        keywords: List of keywords to search for
        pages_text: Dict of page_number -> text

    Returns:
        List of page numbers where keywords were found
    """
    matching_pages = []

    for page_num, text in pages_text.items():
        # Normalize text for searching
        text_lower = text.lower()

        # Check if any keywords appear on this page
        matches = 0
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Use word boundary search for better accuracy
            if re.search(r"\b" + re.escape(keyword_lower) + r"\b", text_lower):
                matches += 1

        # If multiple keywords found, this is likely the right page
        if matches >= 2 or (len(keywords) <= 2 and matches >= 1):
            matching_pages.append(page_num)

    return matching_pages


def validate_question(qa: dict, pages_text: dict) -> dict:
    """
    Validate a single question by searching for keywords in PDF pages.

    Args:
        qa: Ground truth question dict
        pages_text: Dict of page_number -> text

    Returns:
        dict with validation results
    """
    question_id = qa["id"]
    question_text = qa["question"]
    expected_page = qa["expected_page_number"]
    keywords = qa["expected_keywords"]
    category = qa["category"]

    # Find pages where keywords appear
    matching_pages = find_keywords_in_pages(keywords, pages_text)

    # Determine most likely page
    if matching_pages:
        # Use most common page if multiple matches
        page_counter = Counter(matching_pages)
        actual_page = page_counter.most_common(1)[0][0]
    else:
        actual_page = None

    # Check if correction needed
    needs_correction = actual_page is not None and actual_page != expected_page

    return {
        "question_id": question_id,
        "question": question_text,
        "category": category,
        "expected_page": expected_page,
        "actual_page": actual_page,
        "matching_pages": matching_pages,
        "needs_correction": needs_correction,
        "status": "incorrect"
        if needs_correction
        else ("correct" if actual_page == expected_page else "missing"),
        "keywords": keywords,
    }


def main():
    """Main validation workflow."""
    print("=" * 80)
    print("GROUND TRUTH PAGE VALIDATION - Story 2.9")
    print("=" * 80)
    print()
    print(f"Validating {len(GROUND_TRUTH_QA)} ground truth questions...")
    print()

    # Load split PDFs
    pages_text = load_split_pdfs()

    if not pages_text:
        print("\n❌ Error: Could not load any PDF pages")
        print("   Check that split PDFs exist in: docs/sample pdf/split/")
        return

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
            result = validate_question(qa, pages_text)
            all_results.append(result)

            # Print result
            q_id = result["question_id"]
            expected = result["expected_page"]
            actual = result["actual_page"]
            status = result["status"]

            if status == "correct":
                print(f"  ✅ Q{q_id:2d}: Page {expected} CORRECT")
            elif status == "incorrect":
                pages_list = ", ".join(str(p) for p in result["matching_pages"][:3])
                print(
                    f"  ❌ Q{q_id:2d}: Page {expected} → {actual} NEEDS CORRECTION (found on: {pages_list})"
                )
            else:
                print(f"  ⚠️  Q{q_id:2d}: Page {expected} UNCERTAIN (keywords not found clearly)")

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
        f.write("**Validation Method:** Direct PDF keyword search (split PDFs)\n")
        f.write(f"**Total Questions:** {total}\n\n")

        f.write("## Summary Statistics\n\n")
        f.write(f"- **Correct:** {correct} ({correct / total * 100:.1f}%)\n")
        f.write(f"- **Incorrect:** {incorrect} ({incorrect / total * 100:.1f}%)\n")
        f.write(f"- **Uncertain:** {missing} ({missing / total * 100:.1f}%)\n\n")

        f.write("## Validation Results by Category\n\n")

        for category, _ in sorted(by_category.items()):
            f.write(f"### {category.upper()}\n\n")
            f.write(
                "| Q# | Question (truncated) | Current Page | Actual Page | Status | Matching Pages |\n"
            )
            f.write(
                "|----|----------------------|--------------|-------------|--------|----------------|\n"
            )

            category_results = [r for r in all_results if r["category"] == category]
            for result in category_results:
                q_id = result["question_id"]
                q_text = (
                    result["question"][:50] + "..."
                    if len(result["question"]) > 50
                    else result["question"]
                )
                expected = result["expected_page"]
                actual = result["actual_page"] if result["actual_page"] else "?"
                status = result["status"]
                pages_str = ", ".join(str(p) for p in result["matching_pages"][:5])
                if not pages_str:
                    pages_str = "None found"

                f.write(f"| {q_id} | {q_text} | {expected} | {actual} | {status} | {pages_str} |\n")

            f.write("\n")

        f.write("## Corrections List\n\n")

        if corrections:
            f.write("Questions requiring page number corrections:\n\n")
            for corr in corrections:
                f.write(
                    f"- **Q{corr['question_id']:2d}**: {corr['expected_page']} → {corr['actual_page']} "
                )
                f.write(f"({corr['category']})\n")
                f.write(f"  - Question: {corr['question']}\n")
                f.write(f"  - Keywords: {', '.join(corr['keywords'])}\n")
                f.write(
                    f"  - Found on pages: {', '.join(str(p) for p in corr['matching_pages'])}\n\n"
                )
        else:
            f.write("No corrections needed - all page references are correct!\n")

        f.write("\n---\n\n")
        f.write("**Next Steps:**\n")
        f.write("1. Review corrections list\n")
        f.write("2. For uncertain cases, manually verify in split PDFs\n")
        f.write("3. Apply corrections to `tests/fixtures/ground_truth.py`\n")
        f.write("4. Proceed to Story 2.9 AC2 (Update Ground Truth File)\n")

    print(f"\n📄 Validation worksheet saved: {worksheet_path}")
    print()

    return all_results


if __name__ == "__main__":
    main()
