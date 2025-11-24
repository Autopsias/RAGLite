#!/usr/bin/env python3
"""Diagnose why 3rd header row isn't marked as column_header by Docling.

This script examines the actual cell structure of transposed tables to:
1. Identify all cells in rows 0, 1, 2 (the 3 header rows)
2. Check which cells have column_header=True
3. Determine if units appear in row 2 but aren't flagged as headers
4. Find workaround: manual detection of unit row
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import TableItem
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption

print("=" * 80)
print("DIAGNOSING HEADER CELL STRUCTURE IN TRANSPOSED TABLES")
print("=" * 80)
print()

# Step 1: Configure Docling
print("Step 1: Configuring Docling...")
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
print("   ✅ Configured")
print()

# Step 2: Convert chunk PDF
chunk_pdf = Path("docs/sample pdf/test-chunk-pages-18-23.pdf")
print(f"Step 2: Converting {chunk_pdf.name}...")
print("   (This will take ~27 seconds)")
print()

result = converter.convert(str(chunk_pdf))
print("   ✅ Converted")
print()

# Step 3: Find transposed tables on pages 3-4 (original 20-21)
print("Step 3: Analyzing transposed tables on pages 3-4 (original 20-21)...")
print()

target_pages = [3, 4]  # Chunk pages 3-4 = original pages 20-21

for page_num in target_pages:
    print(f"{'=' * 80}")
    print(f"PAGE {page_num} (original page {page_num + 17})")
    print(f"{'=' * 80}")
    print()

    # Find tables on this page
    tables = [
        item
        for item, _ in result.document.iterate_items()
        if isinstance(item, TableItem)
        and item.prov
        and len(item.prov) > 0
        and item.prov[0].page_no == page_num
    ]

    if not tables:
        print("   🚨 NO TABLES FOUND")
        print()
        continue

    # Examine first table (transposed table with entities as columns)
    table = tables[0]

    if not hasattr(table, "data") or not table.data:
        print("   🚨 Table has no data attribute")
        print()
        continue

    if not hasattr(table.data, "table_cells") or not table.data.table_cells:
        print("   🚨 Table has no table_cells")
        print()
        continue

    table_cells = table.data.table_cells
    print(f"Total cells in table: {len(table_cells)}")
    print()

    # Step 3a: Check cells flagged as column_header
    print("--- CELLS FLAGGED AS column_header=True ---")
    header_cells = [cell for cell in table_cells if cell.column_header]
    print(f"Total header cells: {len(header_cells)}")
    print()

    if header_cells:
        # Group by row
        from collections import defaultdict

        headers_by_row = defaultdict(list)
        for cell in header_cells:
            headers_by_row[cell.start_row_offset_idx].append(cell)

        print("Header cells grouped by row:")
        for row_idx in sorted(headers_by_row.keys()):
            cells_in_row = headers_by_row[row_idx]
            print(f"   Row {row_idx}: {len(cells_in_row)} cells")
            # Sample first 3 cells
            sample = cells_in_row[:3]
            for cell in sample:
                text = cell.text[:30] if cell.text else "(empty)"
                print(f'      [{row_idx},{cell.start_col_offset_idx}]: "{text}"')
    print()

    # Step 3b: Check ALL cells in rows 0, 1, 2 (expected header rows)
    print("--- ALL CELLS IN ROWS 0, 1, 2 (Expected Header Rows) ---")
    for row_idx in [0, 1, 2]:
        cells_in_row = [cell for cell in table_cells if cell.start_row_offset_idx == row_idx]

        print(f"\nRow {row_idx}: {len(cells_in_row)} cells")

        if not cells_in_row:
            print("   🚨 No cells found in this row!")
            continue

        # Check how many are flagged as column_header
        flagged_as_header = sum(1 for cell in cells_in_row if cell.column_header)
        print(f"   Flagged as column_header: {flagged_as_header} / {len(cells_in_row)}")

        # Sample first 5 cells
        print("   Sample cells:")
        for i, cell in enumerate(cells_in_row[:5]):
            text = cell.text[:40] if cell.text else "(empty)"
            header_flag = "✅ HEADER" if cell.column_header else "❌ NOT HEADER"
            print(f"      Cell {i}: [{row_idx},{cell.start_col_offset_idx}] {header_flag}")
            print(f'              Text: "{text}"')

        # Check if row 2 has unit patterns
        if row_idx == 2:
            unit_patterns = ["EUR", "ton", "Meur", "kt", "%", "GJ", "€", "USD", "kWh", "m3", "MW"]
            cells_with_units = [
                cell
                for cell in cells_in_row
                if cell.text and any(pattern in cell.text for pattern in unit_patterns)
            ]
            print("\n   🔍 UNIT DETECTION IN ROW 2:")
            print(f"      Cells with unit patterns: {len(cells_with_units)} / {len(cells_in_row)}")

            if cells_with_units:
                print("      Sample cells with units:")
                for cell in cells_with_units[:5]:
                    print(f'         "{cell.text}" (column {cell.start_col_offset_idx})')

    print()

    # Step 3c: Summary and Recommendation
    print("--- DIAGNOSIS SUMMARY ---")
    print()

    # Check if row 2 exists
    row_2_cells = [cell for cell in table_cells if cell.start_row_offset_idx == 2]
    if not row_2_cells:
        print("❌ PROBLEM: Row 2 doesn't exist in table structure")
        print("   → Table has fewer than 3 header rows")
        print()
    else:
        # Check if row 2 has units
        unit_patterns = ["EUR", "ton", "Meur", "kt", "%", "GJ", "€", "USD", "kWh", "m3", "MW"]
        cells_with_units = [
            cell
            for cell in row_2_cells
            if cell.text and any(pattern in cell.text for pattern in unit_patterns)
        ]

        if cells_with_units:
            print("✅ GOOD NEWS: Row 2 exists and contains unit patterns")
            print(f"   → {len(cells_with_units)} cells with units found")
            print()

            # Check if flagged as headers
            flagged_count = sum(1 for cell in cells_with_units if cell.column_header)
            if flagged_count == 0:
                print("🚨 ROOT CAUSE CONFIRMED: Row 2 cells NOT flagged as column_header")
                print("   → Docling's TableFormer doesn't recognize 3rd header row")
                print()
                print("💡 SOLUTION: Manually detect row 2 as unit row")
                print("   → Check if row 2 cells contain unit patterns")
                print("   → Don't rely on column_header flag for row 2")
                print()
                print("   Proposed logic:")
                print("   1. Get ALL cells (not just column_header=True)")
                print("   2. Group by start_row_offset_idx")
                print("   3. Check if row 2 has ≥50% cells with unit patterns")
                print("   4. If yes, treat row 2 as unit row")
            else:
                print(f"   → {flagged_count} / {len(cells_with_units)} flagged as column_header")
                print("   → Partial detection by Docling")
        else:
            print("❌ PROBLEM: Row 2 exists but no unit patterns found")
            print("   → Units might be in a different row")

    print()
    print()

print("=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)
print()
print("Next steps:")
print("  1. If row 2 has units but isn't flagged: Implement manual unit detection")
print("  2. If row 2 doesn't exist: Investigate table structure detection")
print("  3. If units are elsewhere: Update unit detection logic")
