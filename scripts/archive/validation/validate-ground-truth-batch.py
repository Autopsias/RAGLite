#!/usr/bin/env python3
"""
Efficient ground truth validation script.
Searches PDFs for keywords and reports correct page numbers.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402

try:
    from pypdf import PdfReader
except ImportError:
    print("ERROR: pypdf not installed. Run: uv pip install pypdf")
    sys.exit(1)


def get_pdf_path(page_num: int) -> Path:
    """Get the correct split PDF file for a page number."""
    base = project_root / "docs" / "sample pdf" / "split"
    if 1 <= page_num <= 40:
        return base / "2025-08 Performance Review CONSO_v2_part01_pages001-040.pdf"
    elif 41 <= page_num <= 80:
        return base / "2025-08 Performance Review CONSO_v2_part02_pages041-080.pdf"
    elif 81 <= page_num <= 120:
        return base / "2025-08 Performance Review CONSO_v2_part03_pages081-120.pdf"
    elif 121 <= page_num <= 160:
        return base / "2025-08 Performance Review CONSO_v2_part04_pages121-160.pdf"
    raise ValueError(f"Page {page_num} out of range (1-160)")


def search_pdf_for_keywords(
    pdf_path: Path, keywords: list[str], start_page: int, end_page: int
) -> list[tuple[int, str, list[str]]]:
    """
    Search a PDF for keywords within a page range.
    Returns list of (page_num, page_text_snippet, found_keywords).
    """
    matches = []
    reader = PdfReader(str(pdf_path))

    # Determine PDF-relative page indices
    if "part01" in pdf_path.name:
        offset = 0
    elif "part02" in pdf_path.name:
        offset = 40
    elif "part03" in pdf_path.name:
        offset = 80
    elif "part04" in pdf_path.name:
        offset = 120
    else:
        offset = 0

    for i in range(len(reader.pages)):
        abs_page_num = i + offset + 1
        if abs_page_num < start_page or abs_page_num > end_page:
            continue

        page = reader.pages[i]
        text = page.extract_text().lower()

        found = [kw for kw in keywords if kw.lower() in text]
        if len(found) >= 2:  # At least 2 keywords match
            snippet = text[:200].replace("\n", " ")
            matches.append((abs_page_num, snippet, found))

    return matches


def validate_question(qa: dict) -> dict:
    """Validate a single question by searching for keywords."""
    q_id = qa["id"]
    expected_page = qa["expected_page_number"]
    keywords = qa["expected_keywords"]

    print(f"  Q{q_id}: ", end="", flush=True)

    # Get the PDF file that contains this page
    pdf_path = get_pdf_path(expected_page)

    # Search a window around the expected page (±10 pages)
    search_start = max(1, expected_page - 10)
    search_end = min(160, expected_page + 10)

    matches = search_pdf_for_keywords(pdf_path, keywords, search_start, search_end)

    # Check if expected page is in matches
    expected_match = [m for m in matches if m[0] == expected_page]

    result = {
        "question_id": q_id,
        "question": qa["question"],
        "expected_page": expected_page,
        "keywords": keywords,
        "matches": matches,
        "valid": len(expected_match) > 0,
        "needs_correction": len(expected_match) == 0,
    }

    if result["valid"]:
        print(f"✓ (page {expected_page})")
    else:
        if matches:
            pages_found = [m[0] for m in matches]
            print(f"✗ (found on pages {pages_found}, not {expected_page})")
        else:
            print("✗ (keywords not found in ±10 page window)")

    return result


def main():
    """Validate Operating Expenses questions (Q43-Q50)."""
    print("=" * 80)
    print("GROUND TRUTH VALIDATION - Operating Expenses (Q43-Q50)")
    print("=" * 80)
    print()

    # Filter to Operating Expenses questions
    cost_questions = [qa for qa in GROUND_TRUTH_QA if qa["category"] == "operating_expenses"]

    print(f"Validating {len(cost_questions)} Operating Expenses questions...")
    print()

    results = []
    for qa in cost_questions:
        result = validate_question(qa)
        results.append(result)

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    valid = sum(1 for r in results if r["valid"])
    needs_correction = sum(1 for r in results if r["needs_correction"])

    print(f"Valid: {valid}/{len(results)}")
    print(f"Needs correction: {needs_correction}/{len(results)}")
    print()

    # Detailed corrections
    if needs_correction > 0:
        print("CORRECTIONS NEEDED:")
        print()
        for r in results:
            if r["needs_correction"]:
                print(f"Q{r['question_id']}: {r['question']}")
                print(f"  Expected page: {r['expected_page']}")
                if r["matches"]:
                    for page, snippet, found_kw in r["matches"]:
                        print(f"  Found on page {page}: {found_kw}")
                        print(f"    Snippet: {snippet}")
                else:
                    print("  NOT FOUND in ±10 page window")
                print()

    return results


if __name__ == "__main__":
    results = main()
