#!/usr/bin/env python3
"""Test Docling table extraction on page 46 sample.

This script tests whether Docling extracts table cell data correctly.
Expected to find: "23.2", "50.6%", "20.3", "29.4" on page 46.
"""

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption


def test_default_extraction():
    """Test with default DocumentConverter (current approach)."""
    print("\n" + "=" * 80)
    print("TEST 1: DEFAULT DocumentConverter (current approach)")
    print("=" * 80)

    converter = DocumentConverter()

    pdf_path = "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"
    result = converter.convert(pdf_path)

    # Export to markdown
    markdown_text = result.document.export_to_markdown()

    # Search for known table values from page 46
    test_values = ["23.2", "50.6%", "20.3", "29.4", "EUR/ton"]

    print("\nSearching for table cell values from page 46...")
    for value in test_values:
        if value in markdown_text:
            print(f"  ✓ Found: '{value}'")
        else:
            print(f"  ✗ Missing: '{value}'")

    # Count table occurrences
    table_count = markdown_text.count("```")
    print(f"\nMarkdown code blocks (potential tables): {table_count // 2}")

    # Show sample of page 46 area (search for "Portugal")
    if "Portugal" in markdown_text:
        idx = markdown_text.find("Portugal")
        sample = markdown_text[max(0, idx - 200) : idx + 500]
        print("\nSample text around 'Portugal':")
        print("-" * 80)
        print(sample)
        print("-" * 80)


def test_configured_extraction():
    """Test with explicit table extraction configuration."""
    print("\n" + "=" * 80)
    print("TEST 2: CONFIGURED DocumentConverter (with table extraction)")
    print("=" * 80)

    # Configure with explicit table extraction options
    pipeline_options = PdfPipelineOptions(do_table_structure=True)
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    pdf_path = "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"
    result = converter.convert(pdf_path)

    # Export to markdown
    markdown_text = result.document.export_to_markdown()

    # Search for known table values from page 46
    test_values = ["23.2", "50.6%", "20.3", "29.4", "EUR/ton"]

    print("\nSearching for table cell values from page 46...")
    for value in test_values:
        if value in markdown_text:
            print(f"  ✓ Found: '{value}'")
        else:
            print(f"  ✗ Missing: '{value}'")

    # Count table occurrences
    table_count = markdown_text.count("```")
    print(f"\nMarkdown code blocks (potential tables): {table_count // 2}")

    # Show sample of page 46 area
    if "Portugal" in markdown_text:
        idx = markdown_text.find("Portugal")
        sample = markdown_text[max(0, idx - 200) : idx + 500]
        print("\nSample text around 'Portugal':")
        print("-" * 80)
        print(sample)
        print("-" * 80)


def inspect_docling_items():
    """Inspect individual Docling items to see table data."""
    print("\n" + "=" * 80)
    print("TEST 3: INSPECT Docling Items (debug table item types)")
    print("=" * 80)

    pipeline_options = PdfPipelineOptions(do_table_structure=True)
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    pdf_path = "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"
    result = converter.convert(pdf_path)

    # Iterate through items and look for tables on page 46
    print("\nLooking for items on page 46...")
    page_46_items = []

    for item, _level in result.document.iterate_items():
        if hasattr(item, "prov") and item.prov:
            page_no = item.prov[0].page_no if item.prov else None
            if page_no == 46:
                item_type = type(item).__name__
                page_46_items.append((item_type, item))

                # Print table items
                if "Table" in item_type:
                    print(f"\n  Found {item_type} on page 46!")
                    if hasattr(item, "text"):
                        preview = item.text[:200] if len(item.text) > 200 else item.text
                        print(f"    Preview: {preview}")

                    # Check for table grid/data
                    if hasattr(item, "data"):
                        print(f"    Has 'data' attribute: {item.data}")
                    if hasattr(item, "grid"):
                        print("    Has 'grid' attribute")

    print(f"\nTotal items on page 46: {len(page_46_items)}")

    # Count by type
    from collections import Counter

    type_counts = Counter(item_type for item_type, _ in page_46_items)
    print("\nItem types on page 46:")
    for item_type, count in type_counts.items():
        print(f"  {item_type}: {count}")


if __name__ == "__main__":
    print("Testing Docling table extraction on page 46...")
    print("Expected values: 23.2, 50.6%, 20.3, 29.4 (financial metrics)")

    try:
        test_default_extraction()
    except Exception as e:
        print(f"\n❌ Test 1 failed: {e}")

    try:
        test_configured_extraction()
    except Exception as e:
        print(f"\n❌ Test 2 failed: {e}")

    try:
        inspect_docling_items()
    except Exception as e:
        print(f"\n❌ Test 3 failed: {e}")

    print("\n" + "=" * 80)
    print("Test complete!")
    print("=" * 80)
