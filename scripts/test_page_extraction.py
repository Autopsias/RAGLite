#!/usr/bin/env python3
"""
Page Number Extraction Test Script

Purpose: Diagnose Week 0 page number extraction blocker (NFR7 critical issue)

Tests whether Docling extracts page numbers from PDF documents.
If page numbers are missing, provides recommendations for fix.

Usage:
    poetry run python scripts/test_page_extraction.py

Exit Codes:
    0 - Page numbers successfully extracted
    1 - Page numbers missing (blocker confirmed)
    2 - Script error (Docling not installed, PDF not found, etc.)
"""

import sys
from pathlib import Path
from typing import Any

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    print("ERROR: Docling not installed. Run: poetry install")
    sys.exit(2)


def test_page_extraction(pdf_path: str) -> dict[str, Any]:
    """
    Test page number extraction from PDF using Docling.

    Args:
        pdf_path: Absolute path to test PDF

    Returns:
        Dictionary with test results:
        - success: bool (page numbers found)
        - page_count: int (total pages extracted)
        - sample_pages: List[int] (first 5 page numbers found)
        - elements_without_pages: int (elements missing page numbers)
        - recommendation: str (fix guidance)
    """
    print(f"Testing page extraction from: {pdf_path}\n")

    # Initialize Docling converter
    converter = DocumentConverter()

    # Convert PDF
    print("Converting PDF with Docling...")
    try:
        result = converter.convert(pdf_path)
    except Exception as e:
        print(f"ERROR: Docling conversion failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "recommendation": "Check PDF file is valid and accessible",
        }

    # Analyze page metadata in extracted elements
    page_numbers_found = []
    elements_without_pages = 0
    total_elements = 0

    print("\nAnalyzing extracted elements for page metadata...\n")

    for element in result.document.elements:
        total_elements += 1

        # Check various page number attributes
        page_num = None

        # Try different attribute names
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

    result = {
        "success": success,
        "total_elements": total_elements,
        "elements_with_pages": len(page_numbers_found),
        "elements_without_pages": elements_without_pages,
        "unique_page_numbers": unique_pages,
        "page_count": len(unique_pages),
        "sample_pages": unique_pages[:5] if unique_pages else [],
    }

    # Add recommendation based on results
    if success:
        result["recommendation"] = (
            "✅ SUCCESS: Page numbers found! Verify chunking logic preserves metadata in Story 1.4."
        )
    else:
        result["recommendation"] = (
            "🚨 BLOCKER: No page numbers extracted. "
            "Options: (1) Check Docling API for page parameter, "
            "(2) Implement PyMuPDF fallback for page detection."
        )

    return result


def print_results(results: dict[str, Any]) -> None:
    """Pretty-print test results."""
    print("\n" + "=" * 70)
    print(" PAGE EXTRACTION TEST RESULTS")
    print("=" * 70 + "\n")

    if "error" in results:
        print(f"❌ ERROR: {results['error']}")
        print(f"\n💡 Recommendation: {results['recommendation']}\n")
        return

    print(f"Total elements extracted: {results['total_elements']}")
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
    # Locate Week 0 test PDF
    pdf_dir = Path("/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/sample pdf")

    if not pdf_dir.exists():
        print(f"ERROR: Sample PDF directory not found: {pdf_dir}")
        print("Expected location from Week 0 spike.")
        sys.exit(2)

    # Find PDF file (assumes single PDF in directory)
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"ERROR: No PDF files found in {pdf_dir}")
        sys.exit(2)

    if len(pdf_files) > 1:
        print(f"WARNING: Multiple PDFs found. Using first: {pdf_files[0].name}")

    pdf_path = str(pdf_files[0])

    # Run test
    results = test_page_extraction(pdf_path)

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
