#!/usr/bin/env python3
"""
Debug script to see actual markdown output from Docling table extraction.

This will help diagnose why financial_tables has corrupted data.
"""

import asyncio
from pathlib import Path

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import TableItem


async def main():
    """Debug Docling markdown output."""
    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return

    print("=" * 80)
    print("DEBUGGING DOCLING MARKDOWN OUTPUT")
    print("=" * 80)
    print(f"File: {pdf_path}")
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

    # Convert document
    print("Converting document (this may take 5-10 minutes)...")
    result = converter.convert(str(pdf_path))
    print("Conversion complete!")
    print()

    # Find first 3 tables
    table_count = 0
    for item, _ in result.document.iterate_items():
        if isinstance(item, TableItem):
            table_count += 1

            # Get table metadata
            page_number = item.prov[0].page_no if item.prov else 1

            # Export to markdown
            table_markdown = item.export_to_markdown(doc=result.document)

            print("=" * 80)
            print(f"TABLE {table_count} (Page {page_number})")
            print("=" * 80)
            print("RAW MARKDOWN:")
            print("-" * 80)
            print(table_markdown)
            print()

            # Parse markdown rows
            lines = [line.strip() for line in table_markdown.split("\n") if "|" in line]

            if len(lines) >= 3:
                print("PARSED STRUCTURE:")
                print("-" * 80)

                # Header
                header_line = lines[0]
                header_cells = [cell.strip() for cell in header_line.strip().strip("|").split("|")]
                print(f"Header ({len(header_cells)} columns):")
                for i, cell in enumerate(header_cells):
                    print(f"  [{i}] {repr(cell)}")
                print()

                # First 3 data rows
                print("First 3 Data Rows:")
                for row_idx, data_line in enumerate(lines[2:5]):  # Skip separator at lines[1]
                    cells = [cell.strip() for cell in data_line.strip().strip("|").split("|")]
                    print(f"  Row {row_idx} ({len(cells)} cells):")
                    for i, cell in enumerate(cells):
                        print(f"    [{i}] {repr(cell)}")
                print()

            else:
                print(f"WARNING: Malformed table - only {len(lines)} lines")
                print()

            # Only show first 3 tables
            if table_count >= 3:
                print("=" * 80)
                print(f"(Showing first 3 tables of {table_count} found)")
                print("=" * 80)
                break


if __name__ == "__main__":
    asyncio.run(main())
