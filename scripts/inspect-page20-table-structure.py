#!/usr/bin/env python3
"""Inspect table structure on page 20 to understand unit header layout.

This script examines the table_cells structure to determine:
1. How many header rows exist
2. Where units appear in the headers
3. How to identify unit header rows vs entity/period headers
"""

import asyncio
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter


async def inspect_page20_tables():
    """Inspect table structure on page 20."""

    # Setup Docling with table_cells extraction
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: pipeline_options,
        },
    )

    # Convert document (page 20 is in part01_pages001-040.pdf)
    pdf_path = Path(
        "docs/sample pdf/split/2025-08 Performance Review CONSO_v2_part01_pages001-040.pdf"
    )
    print(f"Converting {pdf_path}...")
    result = doc_converter.convert(pdf_path)

    # Find tables on page 20 (20th page in the original document = page 20 in this split)
    print("\n" + "=" * 80)
    print("TABLES ON PAGE 20")
    print("=" * 80)

    page_20_tables = []
    for item_idx, (item, _) in enumerate(result.document.iterate_items()):
        if item.prov and len(item.prov) > 0:
            page_num = item.prov[0].page_no
            if page_num == 20 and hasattr(item, "data") and item.data is not None:
                # This is a table on page 20
                page_20_tables.append((item_idx, item))
                print(f"\nTable {len(page_20_tables)} (Item {item_idx}):")
                print(f"  Caption: {item.caption if hasattr(item, 'caption') else 'N/A'}")

    # Inspect first table in detail
    if page_20_tables:
        table_idx, table_item = page_20_tables[0]

        print("\n" + "=" * 80)
        print("DETAILED INSPECTION: First Table on Page 20")
        print("=" * 80)

        if hasattr(table_item, "data") and table_item.data:
            table_data = table_item.data

            # Get table dimensions
            print("\nTable Dimensions:")
            print(
                f"  Grid shape: {table_data.grid.shape if hasattr(table_data.grid, 'shape') else 'N/A'}"
            )

            # Check if table_cells exists
            if hasattr(table_data, "table_cells") and table_data.table_cells:
                table_cells = table_data.table_cells
                print(f"  Number of cells: {len(table_cells)}")

                # Group cells by row
                cells_by_row = {}
                for cell in table_cells:
                    row_idx = cell.start_row_offset_idx
                    if row_idx not in cells_by_row:
                        cells_by_row[row_idx] = []
                    cells_by_row[row_idx].append(cell)

                print(f"  Number of rows: {len(cells_by_row)}")

                # Print first 5 rows in detail
                print("\n" + "-" * 80)
                print("FIRST 5 ROWS (showing structure):")
                print("-" * 80)

                for row_idx in sorted(cells_by_row.keys())[:5]:
                    cells = cells_by_row[row_idx]
                    print(f"\nRow {row_idx}:")
                    for cell in sorted(cells, key=lambda c: c.start_col_offset_idx):
                        col_span = f"{cell.start_col_offset_idx}-{cell.end_col_offset_idx}"
                        header_flag = " [HEADER]" if cell.column_header else ""
                        text = cell.text[:50] if cell.text else ""
                        print(f"  Col {col_span:6s}{header_flag:10s}: {text}")

                # Identify header rows
                print("\n" + "-" * 80)
                print("HEADER ROW ANALYSIS:")
                print("-" * 80)

                header_rows = sorted(
                    [
                        row_idx
                        for row_idx, cells in cells_by_row.items()
                        if any(cell.column_header for cell in cells)
                    ]
                )

                print(f"\nHeader rows: {header_rows}")

                for row_idx in header_rows:
                    cells = cells_by_row[row_idx]
                    header_cells = [c for c in cells if c.column_header]
                    print(f"\nRow {row_idx} - {len(header_cells)} header cells:")
                    for cell in sorted(header_cells, key=lambda c: c.start_col_offset_idx):
                        col_span = f"Cols {cell.start_col_offset_idx}-{cell.end_col_offset_idx}"
                        text = cell.text if cell.text else "(empty)"
                        print(f"  {col_span:15s}: '{text}'")

                # Check for potential unit patterns in headers
                print("\n" + "-" * 80)
                print("POTENTIAL UNIT HEADERS:")
                print("-" * 80)

                unit_patterns = ["EUR", "ton", "Meur", "kt", "%", "GJ", "€", "$"]

                for row_idx in header_rows:
                    cells = cells_by_row[row_idx]
                    header_cells = [c for c in cells if c.column_header]

                    for cell in header_cells:
                        if cell.text:
                            text = cell.text.strip()
                            if any(pattern in text for pattern in unit_patterns):
                                col_span = f"Row {row_idx}, Cols {cell.start_col_offset_idx}-{cell.end_col_offset_idx}"
                                print(f"  {col_span:25s}: '{text}' ← UNIT DETECTED")

            else:
                print("  ❌ No table_cells found in table data")
        else:
            print("  ❌ No table data available")
    else:
        print("\n❌ No tables found on page 20")


if __name__ == "__main__":
    asyncio.run(inspect_page20_tables())
