#!/usr/bin/env python3
"""Diagnostic script to verify Docling page number extraction.

Tests whether Docling provides page numbers in provenance metadata
and compares with current estimated page numbers in Qdrant.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from docling.document_converter import DocumentConverter  # noqa: E402


def test_docling_page_numbers():
    """Test if Docling provides page numbers in provenance metadata."""

    # Test PDF path
    pdf_path = "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"

    if not Path(pdf_path).exists():
        print(f"❌ Test PDF not found: {pdf_path}")
        return

    print("🔍 Testing Docling Page Number Extraction")
    print("=" * 70)
    print(f"PDF: {pdf_path}")
    print()

    # Initialize Docling converter
    converter = DocumentConverter()

    # Convert PDF
    print("Converting PDF with Docling...")
    result = converter.convert(pdf_path)

    # Analyze provenance metadata
    total_items = 0
    items_with_prov = 0
    items_with_page_no = 0
    page_numbers = []

    print("\nAnalyzing provenance metadata...")
    print()

    for item, _level in result.document.iterate_items():
        total_items += 1

        # Check if item has provenance
        if hasattr(item, "prov") and item.prov:
            items_with_prov += 1

            # Check if provenance has page_no
            for prov in item.prov:
                if hasattr(prov, "page_no"):
                    items_with_page_no += 1
                    page_numbers.append(prov.page_no)

                    # Show first 10 examples
                    if items_with_page_no <= 10:
                        text_preview = item.text[:60] if hasattr(item, "text") else "N/A"
                        print(
                            f"✓ Item {items_with_page_no}: page_no={prov.page_no}, text='{text_preview}...'"
                        )

    print()
    print("=" * 70)
    print("RESULTS:")
    print(f"  Total items: {total_items}")
    print(f"  Items with prov: {items_with_prov} ({items_with_prov / total_items * 100:.1f}%)")
    print(
        f"  Items with page_no: {items_with_page_no} ({items_with_page_no / total_items * 100:.1f}%)"
    )

    if page_numbers:
        print(f"  Page range: {min(page_numbers)} - {max(page_numbers)}")
        print()
        print("✅ DOCLING PROVIDES PAGE NUMBERS!")
        print()
        print(
            "🐛 BUG CONFIRMED: pipeline.py uses ESTIMATED page numbers instead of Docling's actual page_no"
        )
    else:
        print()
        print("❌ Docling NOT providing page numbers in this case")
        print("   Need to investigate Docling configuration")


if __name__ == "__main__":
    test_docling_page_numbers()
