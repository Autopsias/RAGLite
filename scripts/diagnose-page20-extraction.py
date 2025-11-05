#!/usr/bin/env python3
"""Diagnose why page 20 tables aren't being extracted.

This script uses the CORRECT Docling API to check:
1. Are tables detected on pages 19-22?
2. Do detected tables have table_cells data?
3. What's different about page 20 vs pages 19 and 22?
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption

print("=" * 80)
print("DIAGNOSING PAGE 20 TABLE EXTRACTION ISSUE")
print("=" * 80)
print()

# Step 1: Configure Docling with same settings as pipeline.py
print("Step 1: Configuring Docling with production settings...")
pipeline_options = PdfPipelineOptions()
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pipeline_options, backend=PyPdfiumDocumentBackend
        )
    }
)
print("   ✅ Docling configured")
print()

# Step 2: Convert PDF
pdf_path = "docs/sample pdf/test-pages-19-22.pdf"
print(f"Step 2: Converting PDF: {pdf_path}")
print("   This will take ~25 seconds...")
print()

result = converter.convert(pdf_path)
print("   ✅ PDF converted")
print()

# Step 3: Analyze pages 19-22
print("Step 3: Analyzing table detection on pages 19-22...")
print()

target_pages = [19, 20, 21, 22]

for page_num in target_pages:
    print(f"--- PAGE {page_num} ---")

    # Get all items on this page
    page_items = [
        item
        for item, level in result.document.iterate_items()
        if item.prov and len(item.prov) > 0 and item.prov[0].page_no == page_num
    ]

    print(f"Total items on page: {len(page_items)}")

    # Count tables
    tables = [item for item in page_items if item.__class__.__name__ == "TableItem"]

    print(f"Tables detected: {len(tables)}")

    if len(tables) == 0:
        print("   🚨 NO TABLES DETECTED - This is the problem!")
        print()
        continue

    # Check each table
    for i, table in enumerate(tables):
        print(f"\n   Table {i + 1}:")

        # Check if table has data
        has_data = hasattr(table, "data") and table.data is not None
        print(f"      has_data: {has_data}")

        if not has_data:
            print("      🚨 No data attribute - can't extract!")
            continue

        # Check if table has table_cells
        has_table_cells = (
            hasattr(table.data, "table_cells")
            and table.data.table_cells is not None
            and len(table.data.table_cells) > 0
        )
        print(f"      has_table_cells: {has_table_cells}")

        if not has_table_cells:
            print("      🚨 No table_cells - adaptive extraction will skip!")
            print("      (adaptive_table_extraction.py requires table_cells)")
            continue

        # If we have table_cells, show details
        cell_count = len(table.data.table_cells)
        print(f"      table_cells count: {cell_count}")

        # Try to identify table structure
        if hasattr(table.data, "num_rows") and hasattr(table.data, "num_cols"):
            print(f"      dimensions: {table.data.num_rows} rows x {table.data.num_cols} cols")

        # Sample first few cells
        sample_cells = table.data.table_cells[: min(5, cell_count)]
        print("      Sample cells:")
        for cell in sample_cells:
            cell_text = cell.text[:50] if cell.text else "(empty)"
            print(
                f"         [{cell.start_row_offset_idx},{cell.start_col_offset_idx}]: {cell_text}"
            )

        print("      ✅ This table SHOULD be extracted")

    print()

# Step 4: Summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()

pages_with_tables = sum(
    1
    for page in target_pages
    if any(
        item.__class__.__name__ == "TableItem"
        for item, level in result.document.iterate_items()
        if item.prov and len(item.prov) > 0 and item.prov[0].page_no == page
    )
)

print(f"Pages with detected tables: {pages_with_tables} / {len(target_pages)}")
print()

if pages_with_tables == len(target_pages):
    print("✅ ALL pages have detected tables")
    print()
    print("Root cause: Tables detected but extraction logic failing")
    print("Next step: Debug adaptive_table_extraction.py with added logging")
else:
    missing_pages = [
        page
        for page in target_pages
        if not any(
            item.__class__.__name__ == "TableItem"
            for item, level in result.document.iterate_items()
            if item.prov and len(item.prov) > 0 and item.prov[0].page_no == page
        )
    ]
    print(f"🚨 TABLES NOT DETECTED on pages: {missing_pages}")
    print()
    print("Root cause: Docling table detection failure")
    print("Next steps:")
    print("   1. Check if these pages have different table formats")
    print("   2. Try alternative Docling settings")
    print("   3. Consider fallback extraction from markdown")

print()
print("=" * 80)
