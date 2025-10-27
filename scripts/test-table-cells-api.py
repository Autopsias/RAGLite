#!/usr/bin/env python3
"""
Test direct TableItem.data.table_cells API access for multi-header detection.

This approach accesses the raw table structure with cell-level metadata including:
- column_header: bool - Is this cell a column header?
- row_header: bool - Is this cell a row header?
- start_row_offset_idx, end_row_offset_idx - Cell row position
- start_col_offset_idx, end_col_offset_idx - Cell column position
- text: str - Cell content
"""

from pathlib import Path

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import TableItem


def test_table_cells_api():
    """Test direct table_cells API access."""
    pdf_path = Path("data/test-10-pages.pdf")

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        print("   Using full PDF instead...")
        pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    print("=" * 80)
    print("TABLE CELLS API TEST")
    print("=" * 80)
    print(f"File: {pdf_path}")
    print("Testing: table.data.table_cells direct access")
    print()

    # Configure Docling
    pipeline_options = PdfPipelineOptions()
    pipeline_options.accelerator_options = AcceleratorOptions(num_threads=8, device="cpu")
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=PyPdfiumDocumentBackend,
            )
        }
    )

    # Convert PDF
    print("Converting document...")
    result = converter.convert(str(pdf_path))
    print("✅ Conversion complete!")
    print()

    # Analyze first 3 tables
    table_count = 0
    multi_header_count = 0

    for item, _ in result.document.iterate_items():
        if isinstance(item, TableItem):
            table_count += 1

            page_number = item.prov[0].page_no if item.prov else 1

            print("=" * 80)
            print(f"TABLE {table_count} - Page {page_number}")
            print("=" * 80)

            # Access table_cells directly
            table_cells = item.data.table_cells
            num_rows = item.data.num_rows
            num_cols = item.data.num_cols

            print(f"Table dimensions: {num_rows} rows x {num_cols} cols")
            print(f"Total cells: {len(table_cells)}")
            print()

            # Analyze header structure
            column_headers = [cell for cell in table_cells if cell.column_header]
            row_headers = [cell for cell in table_cells if cell.row_header]

            print(f"Column header cells: {len(column_headers)}")
            print(f"Row header cells: {len(row_headers)}")
            print()

            # Detect multi-header tables
            if len(column_headers) > 0:
                # Check if column headers span multiple rows
                header_rows = set(cell.start_row_offset_idx for cell in column_headers)
                num_header_rows = len(header_rows)

                print(f"🎯 Column header rows: {sorted(header_rows)}")
                print(f"   Number of header row levels: {num_header_rows}")
                print()

                if num_header_rows > 1:
                    multi_header_count += 1
                    print("✅ MULTI-HEADER TABLE DETECTED!")
                    print(f"   - {num_header_rows} levels of column headers")
                    print()

                    # Show structure of first few headers
                    print("   First 5 column headers:")
                    for i, cell in enumerate(column_headers[:5]):
                        print(
                            f"     [{i}] Row {cell.start_row_offset_idx}, "
                            f"Col {cell.start_col_offset_idx}: "
                            f'"{cell.text}"'
                        )
                    print()

            # Show sample cells (first row of data)
            print("   First data row (non-header cells):")
            data_cells = [
                cell
                for cell in table_cells
                if not cell.column_header
                and not cell.row_header
                and cell.start_row_offset_idx
                == min(
                    c.start_row_offset_idx
                    for c in table_cells
                    if not c.column_header and not c.row_header
                )
            ]
            for i, cell in enumerate(data_cells[:5]):
                print(
                    f"     [{i}] Row {cell.start_row_offset_idx}, "
                    f"Col {cell.start_col_offset_idx}: "
                    f'"{cell.text}"'
                )
            print()

            # Limit to 3 tables
            if table_count >= 3:
                print("=" * 80)
                print("(Showing first 3 tables)")
                print("=" * 80)
                break

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tables: {table_count}")
    print(f"Multi-header tables: {multi_header_count}")
    print()

    if multi_header_count > 0:
        print("✅ SUCCESS - Multi-header detection works via table_cells API!")
        print("   - column_header flag identifies header cells")
        print("   - start_row_offset_idx shows header row levels")
        print("   - Direct access to cell text and position")
        print("   - Ready to implement table_cells-based parser")
    else:
        print("⚠️  No multi-header tables found in first 3 tables")
        print("   - May need to check more tables")
        print("   - Or tables may have single headers")


if __name__ == "__main__":
    test_table_cells_api()
