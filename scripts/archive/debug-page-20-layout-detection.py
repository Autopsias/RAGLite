#!/usr/bin/env python3
"""
Diagnostic script to check what layout is detected for page 20 tables.

This helps identify why Variable Cost data is not being extracted correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.document_converter import DocumentConverter
from docling_core.types.doc import TableItem

from raglite.ingestion.adaptive_table_extraction import detect_table_layout


def main():
    pdf_path = "docs/sample pdf/sections/section-01_pages-1-20.pdf"

    if not Path(pdf_path).exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)

    print("=" * 80)
    print("LAYOUT DETECTION DIAGNOSTIC - PAGE 20 TABLES")
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

    # Focus on page 20
    page_20_tables = [t for t in all_tables if t["page"] == 20]

    if not page_20_tables:
        print("❌ NO TABLES ON PAGE 20")
        return

    print(f"✅ Found {len(page_20_tables)} table(s) on page 20")
    print()

    # Analyze each table
    for table in page_20_tables:
        item = table["item"]
        page = table["page"]
        idx = table["index"]

        print("=" * 80)
        print(f"TABLE {idx} (Page {page})")
        print("=" * 80)
        print()

        # Get table cells - Docling structure
        if not hasattr(item, "data") or not hasattr(item.data, "table_cells"):
            print("⚠️  No table cells found (checking item.data.table_cells)")

            # Try alternative access patterns
            if hasattr(item, "export_to_dataframe"):
                try:
                    df = item.export_to_dataframe()
                    print(f"   DataFrame shape: {df.shape}")
                    print(f"   Columns: {list(df.columns)[:5]}")
                except Exception as e:
                    print(f"   DataFrame export failed: {e}")

            print()
            print("   Skipping layout detection (no table_cells)")
            print()
            continue

        table_cells = item.data.table_cells

        num_rows = max((cell.end_row_offset_idx for cell in table_cells), default=0)
        num_cols = max((cell.end_col_offset_idx for cell in table_cells), default=0)

        print(f"Table dimensions: {num_rows} rows x {num_cols} cols")
        print()

        # Detect layout
        print("Detecting layout...")
        try:
            layout, metadata = detect_table_layout(table_cells, num_rows, num_cols)

            print(f"✅ Detected layout: {layout}")
            print("   Expected layout: TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS")
            print()

            if str(layout) != "TableLayout.TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS":
                print("❌ LAYOUT MISMATCH!")
                print()
            else:
                print("✅ CORRECT LAYOUT DETECTED")
                print()

            print("Metadata:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
            print()

        except Exception as e:
            print(f"❌ Layout detection failed: {e}")
            print()
            import traceback

            traceback.print_exc()

        # Analyze table structure
        print("Table structure analysis:")
        print()

        # Get column headers
        column_headers = [cell for cell in table_cells if cell.column_header]
        print(f"Column headers: {len(column_headers)}")
        for cell in column_headers[:5]:
            print(
                f"  Row {cell.start_row_offset_idx}, Col {cell.start_col_offset_idx}: {cell.text[:50]}"
            )
        print()

        # Get first column cells (should be metrics)
        first_col_cells = [
            cell
            for cell in table_cells
            if cell.start_col_offset_idx == 0 and not cell.column_header
        ]
        print(f"First column cells: {len(first_col_cells)}")
        for cell in first_col_cells[:10]:
            print(f"  Row {cell.start_row_offset_idx}: {cell.text[:50]}")
        print()

        # Check for metric keywords
        metric_keywords = [
            "variable",
            "cost",
            "thermal",
            "electricity",
            "personnel",
            "ebitda",
            "revenue",
            "sales",
            "margin",
            "fixed",
        ]

        metric_count = sum(
            1
            for cell in first_col_cells
            if cell.text and any(kw in cell.text.lower() for kw in metric_keywords)
        )

        print(f"Metric keyword matches in first column: {metric_count}/{len(first_col_cells)}")
        print(
            f"Ratio: {metric_count / len(first_col_cells) * 100:.1f}%" if first_col_cells else "N/A"
        )
        print()

        # Show markdown preview
        md = item.export_to_markdown()
        lines = md.split("\n")
        print("Markdown preview (first 15 lines):")
        for line in lines[:15]:
            print(f"  {line[:100]}")
        print()


if __name__ == "__main__":
    main()
