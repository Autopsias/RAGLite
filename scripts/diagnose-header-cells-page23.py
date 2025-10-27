#!/usr/bin/env python3
"""Diagnose header cell structure in page 23 tables to understand unit detection failure.

Page 23 shows 37.07% unit population with NO improvement from statistical framework.
This script analyzes the table structure to determine root cause.

Expected findings:
- Different table structure than pages 20-21
- Units may be in different column or row
- Header flagging patterns may differ
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption

print("=" * 80)
print("DIAGNOSING HEADER CELL STRUCTURE IN PAGE 23 TABLES")
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

# Step 2: Convert full PDF
print("Step 2: Converting full PDF...")
full_pdf = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
print(f"   Converting {full_pdf.name}...")
print("   (This will take ~14 minutes)")
print()

result = converter.convert(str(full_pdf))

print("   ✅ Converted")
print()

# Step 3: Find tables on page 23
print("Step 3: Analyzing page 23 tables...")
print()

page_23_tables = []
for item_idx, (item, level) in enumerate(result.document.iterate_items()):
    if hasattr(item, "prov") and item.prov and len(item.prov) > 0:
        page_num = item.prov[0].page_no
        if page_num == 23 and item.__class__.__name__ == "TableItem":
            page_23_tables.append((item_idx, item))

print(f"Found {len(page_23_tables)} tables on page 23")
print()

if not page_23_tables:
    print("❌ ERROR: No tables found on page 23")
    print()
    print("This suggests:")
    print("  1. Page 23 has no table structures")
    print("  2. Tables are not being detected by Docling")
    print("  3. Page numbering issue")
    sys.exit(1)

# Step 4: Analyze each table
for table_num, (item_idx, table) in enumerate(page_23_tables, 1):
    print("=" * 80)
    print(f"TABLE {table_num} (Item {item_idx})")
    print("=" * 80)
    print()

    # Check if table has cell data
    if not hasattr(table, "data") or not table.data:
        print("❌ ERROR: Table has no data attribute")
        continue

    if not hasattr(table.data, "table_cells") or not table.data.table_cells:
        print("❌ ERROR: Table has no table_cells")
        continue

    cells = table.data.table_cells
    print(f"Total cells in table: {len(cells)}")
    print()

    # Group cells by row
    from collections import defaultdict

    rows = defaultdict(list)
    for cell in cells:
        row_idx = cell.start_row_offset_idx
        rows[row_idx].append(cell)

    # Sort rows by index
    sorted_rows = sorted(rows.items())

    # Analyze header cells
    print("--- CELLS FLAGGED AS column_header=True ---")
    header_cells = [c for c in cells if c.column_header]
    print(f"Total header cells: {len(header_cells)}")
    print()

    if header_cells:
        # Group header cells by row
        header_rows = defaultdict(list)
        for cell in header_cells:
            header_rows[cell.start_row_offset_idx].append(cell)

        print("Header cells grouped by row:")
        for row_idx in sorted(header_rows.keys())[:5]:  # First 5 header rows
            cells_in_row = header_rows[row_idx]
            print(f"   Row {row_idx}: {len(cells_in_row)} cells")
            for i, cell in enumerate(cells_in_row[:3]):  # First 3 cells
                print(
                    f'      [{cell.start_row_offset_idx},{cell.start_col_offset_idx}]: "{cell.text}"'
                )
        print()

    # Analyze first few rows (expected header area)
    print("--- ALL CELLS IN ROWS 0, 1, 2 (Expected Header Rows) ---")
    print()

    # Define unit patterns
    unit_patterns = [
        "EUR",
        "Meur",
        "€",
        "$",
        "USD",
        "ton",
        "kton",
        "kt",
        "%",
        "GJ",
        "kWh",
        "m³",
        "MW",
        "m²",
        "kg",
        "g",
        "t",
        "l",
        "ml",
        "h",
        "min",
        "s",
        "kW",
        "GW",
        "MWh",
        "GWh",
        "million",
        "billion",
        "thousand",
        "M€",
        "k€",
        "bn",
        "mn",
        "ratio",
        "rate",
        "pts",
        "bps",
        "basis points",
        "percentage",
        "pct",
        "people",
        "FTE",
        "headcount",
        "units",
    ]

    for row_idx in range(min(3, len(sorted_rows))):
        if row_idx not in rows:
            continue

        cells_in_row = rows[row_idx]
        header_count = sum(1 for c in cells_in_row if c.column_header)

        print(f"Row {row_idx}: {len(cells_in_row)} cells")
        print(f"   Flagged as column_header: {header_count} / {len(cells_in_row)}")
        print("   Sample cells:")

        for i, cell in enumerate(cells_in_row[:5]):  # First 5 cells
            header_marker = "✅ HEADER" if cell.column_header else "❌ NOT HEADER"
            print(
                f"      Cell {i}: [{cell.start_row_offset_idx},{cell.start_col_offset_idx}] {header_marker}"
            )
            print(f'              Text: "{cell.text}"')

        print()

        # Check for unit patterns in this row
        cells_with_units = [
            c
            for c in cells_in_row
            if any(pattern.lower() in c.text.lower() for pattern in unit_patterns)
        ]
        if cells_with_units:
            print(f"   🔍 UNIT DETECTION IN ROW {row_idx}:")
            print(f"      Cells with unit patterns: {len(cells_with_units)} / {len(cells_in_row)}")
            print("      Sample cells with units:")
            for cell in cells_with_units[:5]:
                print(f'         "{cell.text}" (column {cell.start_col_offset_idx})')
            print()

    # Check column 1 specifically (where we expect units in transposed tables)
    print("--- COLUMN 1 ANALYSIS (Expected Unit Column in Transposed Tables) ---")
    print()

    col_1_cells = [c for c in cells if c.start_col_offset_idx == 1]
    if col_1_cells:
        print(f"Total cells in column 1: {len(col_1_cells)}")
        print("Sample cells (first 10):")
        for i, cell in enumerate(col_1_cells[:10]):
            has_unit = any(pattern.lower() in cell.text.lower() for pattern in unit_patterns)
            marker = "🔍 UNIT" if has_unit else ""
            print(
                f'   [{cell.start_row_offset_idx},{cell.start_col_offset_idx}]: "{cell.text}" {marker}'
            )
        print()

        # Count units in column 1
        col_1_with_units = [
            c
            for c in col_1_cells
            if any(pattern.lower() in c.text.lower() for pattern in unit_patterns)
        ]
        unit_percentage = 100.0 * len(col_1_with_units) / len(col_1_cells) if col_1_cells else 0.0
        print(
            f"Cells with unit patterns in column 1: {len(col_1_with_units)}/{len(col_1_cells)} = {unit_percentage:.2f}%"
        )
        print()
    else:
        print("❌ ERROR: No cells found in column 1")
        print()

    # Check if this is a transposed table
    print("--- TABLE LAYOUT ANALYSIS ---")
    print()

    # Count cells per row and column
    row_counts = defaultdict(int)
    col_counts = defaultdict(int)
    for cell in cells:
        row_counts[cell.start_row_offset_idx] += 1
        col_counts[cell.start_col_offset_idx] += 1

    avg_cells_per_row = sum(row_counts.values()) / len(row_counts) if row_counts else 0
    avg_cells_per_col = sum(col_counts.values()) / len(col_counts) if col_counts else 0

    print(f"Total rows: {len(row_counts)}")
    print(f"Total columns: {len(col_counts)}")
    print(f"Average cells per row: {avg_cells_per_row:.1f}")
    print(f"Average cells per column: {avg_cells_per_col:.1f}")
    print()

    # Determine if transposed
    if len(col_counts) > len(row_counts) * 1.5:
        print("📊 LIKELY TRANSPOSED: More columns than rows (data flows horizontally)")
    elif len(row_counts) > len(col_counts) * 1.5:
        print("📊 LIKELY NORMAL: More rows than columns (data flows vertically)")
    else:
        print("📊 UNCLEAR: Similar row/column counts")
    print()

    # Diagnosis summary
    print("--- DIAGNOSIS SUMMARY ---")
    print()

    if header_count > 0 and row_idx < 3:
        print(f"✅ GOOD NEWS: Row {row_idx} has {header_count} cells flagged as headers")
    else:
        print("⚠️  WARNING: First 3 rows have limited header flagging")

    if cells_with_units:
        print(f"✅ UNITS FOUND: {len(cells_with_units)} cells with unit patterns in first 3 rows")
    else:
        print("❌ NO UNITS: No unit patterns detected in first 3 rows")

    if col_1_with_units and unit_percentage >= 50.0:
        print(f"✅ COLUMN 1 HAS UNITS: {unit_percentage:.2f}% of column 1 cells contain units")
    elif col_1_with_units:
        print(
            f"⚠️  COLUMN 1 PARTIAL: {unit_percentage:.2f}% of column 1 cells contain units (below 50% threshold)"
        )
    else:
        print("❌ COLUMN 1 NO UNITS: Units not found in column 1")

    print()
    print("💡 RECOMMENDATIONS:")
    if len(col_counts) > len(row_counts) * 1.5 and col_1_with_units:
        print("  1. Page 23 appears to be transposed like pages 20-21")
        print("  2. Statistical framework should work - investigate why it doesn't")
        print("  3. Check if unit detection logic is being called for page 23")
    elif len(row_counts) > len(col_counts) * 1.5:
        print("  1. Page 23 is NORMAL table layout (NOT transposed)")
        print("  2. Statistical framework assumes transposed tables")
        print("  3. Need different detection strategy for normal tables")
    else:
        print("  1. Page 23 table structure is ambiguous")
        print("  2. Manual inspection of PDF required")
        print("  3. May need hybrid detection strategy")

    print()

print("=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)
print()
print("Next steps:")
print("  1. Based on findings above, determine table structure type")
print("  2. If transposed: Debug why statistical framework fails")
print("  3. If normal: Implement normal table unit detection")
print("  4. If ambiguous: Manual PDF inspection required")
