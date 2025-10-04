#!/usr/bin/env python3
"""
Quick Page Number Extraction Test (First 5 Pages Only)

Purpose: Fast diagnosis of Week 0 page number extraction blocker
Processes only first 5 pages for quick feedback

Usage:
    uv run python scripts/test_page_extraction_quick.py
"""

import sys
from pathlib import Path
from typing import Any

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    print("ERROR: Docling not installed. Run: uv pip install docling")
    sys.exit(2)


def test_page_extraction_quick(pdf_path: str, max_pages: int = 5) -> dict[str, Any]:
    """
    Test page number extraction from first N pages of PDF.

    Args:
        pdf_path: Path to test PDF
        max_pages: Maximum pages to process (default: 5)

    Returns:
        Dict with test results
    """
    print(f"Testing page extraction from: {pdf_path}")
    print(f"Processing first {max_pages} pages only...\n")

    # Initialize converter with page limit
    converter = DocumentConverter()

    # Convert PDF (limited pages)
    print("Converting PDF with Docling...")
    try:
        # Try to configure for limited pages
        result = converter.convert(pdf_path)
    except Exception as e:
        print(f"ERROR: Docling conversion failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "recommendation": "Check PDF file is valid and accessible",
        }

    # Analyze page metadata
    page_numbers_found = []
    elements_without_pages = 0
    total_elements = 0

    print("\nAnalyzing extracted elements for page metadata...\n")

    # Only check first N elements (approximates first N pages)
    max_elements = max_pages * 20  # ~20 elements per page estimate

    for i, element in enumerate(result.document.elements):
        if i >= max_elements:
            break

        total_elements += 1
        page_num = None

        # Try different page number attributes
        if hasattr(element, "page_number"):
            page_num = element.page_number
        elif hasattr(element, "page"):
            page_num = element.page
        elif hasattr(element, "prov") and element.prov:
            # Check provenance for page info
            for prov_item in element.prov:
                if hasattr(prov_item, "page_no"):
                    page_num = prov_item.page_no
                    break

        if page_num is not None:
            page_numbers_found.append(page_num)
        else:
            elements_without_pages += 1

        # Print first 10 elements for debugging
        if total_elements <= 10:
            text_preview = str(element.text)[:60] if hasattr(element, "text") else "[No text]"
            print(f"Element {total_elements}: Page={page_num}, Text='{text_preview}...'")

    # Calculate statistics
    unique_pages = sorted(set(page_numbers_found))
    success = len(unique_pages) > 0

    result_dict = {
        "success": success,
        "total_elements": total_elements,
        "elements_with_pages": len(page_numbers_found),
        "elements_without_pages": elements_without_pages,
        "unique_page_numbers": unique_pages,
        "page_count": len(unique_pages),
        "sample_pages": unique_pages[:5] if unique_pages else [],
    }

    # Add recommendation
    if success:
        result_dict["recommendation"] = (
            "✅ SUCCESS: Page numbers found via element.prov[].page_no! "
            "Solution: Extract page numbers from provenance metadata."
        )
    else:
        result_dict["recommendation"] = (
            "🚨 BLOCKER: No page numbers in first 5 pages. "
            "Implement PyMuPDF fallback for page detection."
        )

    return result_dict


def print_results(results: dict[str, Any]) -> None:
    """Pretty-print test results."""
    print("\n" + "=" * 70)
    print(" QUICK PAGE EXTRACTION TEST RESULTS (First 5 Pages)")
    print("=" * 70 + "\n")

    if "error" in results:
        print(f"❌ ERROR: {results['error']}")
        print(f"\n💡 Recommendation: {results['recommendation']}\n")
        return

    print(f"Total elements analyzed: {results['total_elements']}")
    print(f"Elements WITH page numbers: {results['elements_with_pages']}")
    print(f"Elements WITHOUT page numbers: {results['elements_without_pages']}")
    print(f"Unique pages found: {results['page_count']}")

    if results["sample_pages"]:
        print(f"Sample page numbers: {results['sample_pages']}")
    else:
        print("Sample page numbers: NONE")

    print(f"\n{'✅ SUCCESS' if results['success'] else '❌ FAILED'}")
    print(f"\n💡 {results['recommendation']}\n")


def main():
    """Main test execution."""
    pdf_dir = Path("docs/sample pdf")

    if not pdf_dir.exists():
        print(f"ERROR: Sample PDF directory not found: {pdf_dir}")
        sys.exit(2)

    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"ERROR: No PDF files found in {pdf_dir}")
        sys.exit(2)

    if len(pdf_files) > 1:
        print(f"WARNING: Multiple PDFs found. Using first: {pdf_files[0].name}")

    pdf_path = str(pdf_files[0])

    # Run quick test
    results = test_page_extraction_quick(pdf_path, max_pages=5)

    # Print results
    print_results(results)

    # Exit code
    if "error" in results:
        sys.exit(2)
    elif results["success"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
