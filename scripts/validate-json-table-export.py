#!/usr/bin/env python3
"""
Validate Docling JSON Table Export for Multi-Header Detection.

Story 2.13 AC1: Verify that Docling's JSON export preserves table structure
metadata (row_type, cell hierarchy) needed for multi-header table parsing.

Based on: docs/sessions/2025-10-26-architect-session-docling-research-json-solution.md
"""

import asyncio
import json
from pathlib import Path

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import TableItem


async def validate_json_export(pdf_path: str, max_tables: int = 3):
    """Validate that Docling JSON export preserves table structure.

    Args:
        pdf_path: Path to financial PDF document
        max_tables: Maximum number of tables to inspect (default: 3)

    Returns:
        Validation results and sample JSON structures
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        print(f"❌ ERROR: PDF not found at {pdf_path}")
        return

    print("=" * 80)
    print("DOCLING JSON EXPORT VALIDATION")
    print("=" * 80)
    print(f"File: {pdf_path}")
    print("Testing: Multi-header table detection via row_type metadata")
    print()

    # Configure Docling (same settings as production)
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
    print("Converting document (this may take 5-10 minutes)...")
    result = converter.convert(str(pdf_path))
    print("✅ Conversion complete!")
    print()

    # Analyze tables
    table_count = 0
    multi_header_count = 0
    has_row_type_metadata = False

    for item, _ in result.document.iterate_items():
        if isinstance(item, TableItem):
            table_count += 1

            # Get table metadata
            page_number = item.prov[0].page_no if item.prov else 1
            caption = item.caption if hasattr(item, "caption") else "No caption"

            print("=" * 80)
            print(f"TABLE {table_count} - Page {page_number}")
            print("=" * 80)
            print(f"Caption: {caption}")
            print()

            # Export to JSON
            try:
                # Try JSON export
                table_data = item.export_to_dict()  # Docling uses export_to_dict()

                # Check structure
                if "rows" in table_data or "data" in table_data:
                    print("✅ JSON export successful")

                    # Detect row_type metadata
                    rows = table_data.get("rows", table_data.get("data", []))

                    if rows and isinstance(rows, list):
                        # Check if rows have type information
                        sample_row = rows[0] if rows else {}

                        # Check for various metadata patterns
                        has_row_type = "row_type" in sample_row or "type" in sample_row
                        has_cells = "cells" in sample_row or "data" in sample_row

                        if has_row_type:
                            has_row_type_metadata = True
                            print("✅ Row type metadata found")

                            # Count header rows
                            header_rows = [
                                r
                                for r in rows
                                if r.get("row_type") == "header" or r.get("type") == "header"
                            ]
                            data_rows = [
                                r
                                for r in rows
                                if r.get("row_type") == "data" or r.get("type") == "data"
                            ]

                            print(f"   - Header rows: {len(header_rows)}")
                            print(f"   - Data rows: {len(data_rows)}")

                            if len(header_rows) > 1:
                                multi_header_count += 1
                                print(
                                    f"   ⚠️  MULTI-HEADER TABLE DETECTED ({len(header_rows)} headers)"
                                )

                                # Show header structure
                                for i, header in enumerate(header_rows[:2]):  # First 2
                                    cells = header.get("cells", header.get("data", []))
                                    if isinstance(cells, list):
                                        cell_values = [
                                            str(c.get("value", c.get("text", "")))[:30]
                                            if isinstance(c, dict)
                                            else str(c)[:30]
                                            for c in cells[:5]
                                        ]  # First 5 cells
                                        print(f"   Header {i}: {cell_values}")

                        elif has_cells:
                            print("⚠️  JSON structure found but no row_type metadata")
                            print("   - Using cell-based structure")

                            # Still try to analyze
                            print(f"   - Total rows: {len(rows)}")

                        # Show raw JSON structure (first table only)
                        if table_count == 1:
                            print("\n📋 Sample JSON Structure (first 1000 chars):")
                            print("-" * 80)
                            json_str = json.dumps(table_data, indent=2)
                            print(json_str[:1000])
                            if len(json_str) > 1000:
                                print("... (truncated)")
                            print()

                    else:
                        print("⚠️  Unexpected JSON structure")
                        print(f"   Type: {type(rows)}")

                else:
                    print("❌ No row data found in JSON export")
                    print(f"   Available keys: {list(table_data.keys())}")

            except Exception as e:
                print(f"❌ JSON export failed: {e}")
                import traceback

                traceback.print_exc()

            print()

            # Limit to max_tables
            if table_count >= max_tables:
                print("=" * 80)
                print(f"(Showing first {max_tables} tables)")
                print("=" * 80)
                break

    # Summary
    print()
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total tables analyzed: {table_count}")
    print(f"Tables with row_type metadata: {'YES' if has_row_type_metadata else 'NO'}")
    print(f"Multi-header tables detected: {multi_header_count}")
    print()

    if has_row_type_metadata and multi_header_count > 0:
        print("✅ VALIDATION PASSED")
        print("   - JSON export preserves table structure metadata")
        print("   - Multi-header detection is possible")
        print("   - Ready to implement JSON-based parser")
    elif has_row_type_metadata:
        print("⚠️  PARTIAL VALIDATION")
        print("   - JSON export has metadata but no multi-headers found")
        print("   - May need to check more tables")
    else:
        print("❌ VALIDATION FAILED")
        print("   - JSON export does not have expected metadata")
        print("   - May need alternative parsing strategy")

    print()


if __name__ == "__main__":
    pdf_path = "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"
    asyncio.run(validate_json_export(pdf_path, max_tables=3))
