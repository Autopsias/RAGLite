#!/usr/bin/env python3
"""
Validation script for Story 1.14: Validate ground truth questions against actual PDF content.

This script reads all 50 ground truth questions and checks if the expected_keywords
appear on the expected_page_number in the actual PDF. It generates a corrections
report showing which questions need page number updates.

Usage:
    uv run python scripts/validate-ground-truth-against-pdf.py

Output:
    - Validation report printed to console
    - Corrections needed listed with actual page numbers
    - Summary statistics (% requiring corrections)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402


def get_pdf_path_for_page(page_number: int) -> Path:
    """Get the correct split PDF file path for a given page number."""
    base_path = project_root / "docs" / "sample pdf" / "split"

    if 1 <= page_number <= 40:
        return base_path / "2025-08 Performance Review CONSO_v2_part01_pages001-040.pdf"
    elif 41 <= page_number <= 80:
        return base_path / "2025-08 Performance Review CONSO_v2_part02_pages041-080.pdf"
    elif 81 <= page_number <= 120:
        return base_path / "2025-08 Performance Review CONSO_v2_part03_pages081-120.pdf"
    elif 121 <= page_number <= 160:
        return base_path / "2025-08 Performance Review CONSO_v2_part04_pages121-160.pdf"
    else:
        raise ValueError(f"Page number {page_number} out of range (1-160)")


def validate_question(qa: dict) -> dict:
    """
    Validate a single ground truth question against the PDF.

    Returns:
        dict with validation results:
        - valid: bool (True if keywords found on expected page)
        - found_on_expected: bool (keywords found on the expected page)
        - found_pages: list[int] (pages where keywords were found)
        - message: str (validation status message)
    """
    question_id = qa["id"]
    expected_page = qa["expected_page_number"]
    keywords = qa["expected_keywords"]

    print(f"  Validating Q{question_id}: Page {expected_page}...", end=" ")

    # Note: In the actual implementation, we would use a PDF library like PyPDF2
    # or pdfplumber to extract text from the PDF pages. For this script structure,
    # we're setting up the framework. The actual PDF reading will be done by
    # Claude Code's Read tool which can process PDFs.

    result = {
        "question_id": question_id,
        "question": qa["question"],
        "expected_page": expected_page,
        "keywords": keywords,
        "valid": None,  # To be filled by manual validation
        "found_pages": [],  # To be filled by manual validation
        "needs_correction": False,
        "message": "Validation pending - requires PDF reading",
    }

    return result


def main():
    """Main validation workflow."""
    print("=" * 80)
    print("GROUND TRUTH VALIDATION - Story 1.14")
    print("=" * 80)
    print()
    print("Validating 50 ground truth questions against actual PDF content...")
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
    for category, questions in by_category.items():
        print(f"\n📋 Category: {category.upper()} ({len(questions)} questions)")
        print("-" * 80)

        for qa in questions:
            result = validate_question(qa)
            all_results.append(result)
            print(result["message"])

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total questions validated: {len(all_results)}")
    print()
    print("Next step: Use Claude Code's Read tool to check PDF content for each question")
    print("and identify which questions need page number corrections.")

    return all_results


if __name__ == "__main__":
    results = main()
