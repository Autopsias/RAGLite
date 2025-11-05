#!/usr/bin/env python3
"""
Diagnostic script to check what tables Docling detects on pages 20-21.

This helps identify why table extraction returns 0 rows.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.document_converter import DocumentConverter
from docling_core.types.doc import TableItem


def main():
    pdf_path = "tests/fixtures/sample_financial_report.pdf"

    if not Path(pdf_path).exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)

    print("=" * 80)
    print("DOCLING TABLE DETECTION DIAGNOSTIC - PAGES 20-21")
    print("=" * 80)
    print()
    print(f"PDF: {pdf_path}")
    print()

    # Convert PDF
    print("Converting PDF with Docling...")
    converter = DocumentConverter()
    result = converter.convert(pdf_path)

    print("✅ Conversion complete")
    print(f"   Total pages: {len(result.pages)}")
    print()

    # Find all tables
    all_tables = []
    for idx, (item, _) in enumerate(result.document.iterate_items()):
        if isinstance(item, TableItem):
            page_no = item.prov[0].page_no if item.prov else None
            all_tables.append(
                {"index": len(all_tables), "doc_index": idx, "page": page_no, "item": item}
            )

    print(f"Tables found: {len(all_tables)}")
    print()

    # Show all table pages
    print("Table distribution by page:")
    page_counts = {}
    for table in all_tables:
        page = table["page"]
        page_counts[page] = page_counts.get(page, 0) + 1

    for page in sorted(page_counts.keys()):
        print(f"  Page {page}: {page_counts[page]} table(s)")
    print()

    # Focus on pages 20-21
    print("=" * 80)
    print("PAGES 20-21 ANALYSIS")
    print("=" * 80)
    print()

    pages_20_21_tables = [t for t in all_tables if t["page"] in [20, 21]]

    if not pages_20_21_tables:
        print("❌ NO TABLES DETECTED ON PAGES 20-21!")
        print()
        print("This explains why extraction returns 0 rows.")
        print()
        print("Possible reasons:")
        print("1. Pages 20-21 don't have tables in this PDF")
        print("2. Page numbering mismatch (PDF pages vs document pages)")
        print("3. Docling failed to detect tables on these pages")
        print()
        print("Checking nearby pages for tables...")

        nearby_tables = [t for t in all_tables if t["page"] and 15 <= t["page"] <= 25]
        print("\nTables on pages 15-25:")
        for table in nearby_tables:
            print(f"  Page {table['page']}: Table {table['index']}")

        return

    print(f"✅ Found {len(pages_20_21_tables)} table(s) on pages 20-21")
    print()

    # Analyze each table
    for table in pages_20_21_tables:
        item = table["item"]
        page = table["page"]
        idx = table["index"]

        print(f"Table {idx} (Page {page}):")
        print("-" * 40)

        # Get markdown
        md = item.export_to_markdown()
        lines = md.split("\n")

        print(f"  Markdown lines: {len(lines)}")
        print("  First 10 lines:")
        for line in lines[:10]:
            print(f"    {line[:80]}")

        # Check if it looks like a transposed table
        print()
        print("  Structure analysis:")

        # Heuristic: if first column has metric-like words, it's likely transposed
        metric_keywords = [
            "variable",
            "cost",
            "thermal",
            "electricity",
            "personnel",
            "ebitda",
            "revenue",
            "margin",
        ]

        first_col_values = []
        for line in lines[2:]:  # Skip header rows
            if "|" in line:
                cols = [c.strip() for c in line.split("|")]
                if len(cols) > 1:
                    first_col_values.append(cols[1].lower())

        metric_matches = sum(
            1 for val in first_col_values if any(kw in val for kw in metric_keywords)
        )

        if metric_matches > 0:
            print(f"    ⚠️  LIKELY TRANSPOSED: {metric_matches} metric-like values in first column")
            print(f"    First column samples: {first_col_values[:5]}")
        else:
            print("    Standard table structure")

        print()

    print("=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
