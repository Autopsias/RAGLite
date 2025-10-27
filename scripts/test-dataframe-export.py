#!/usr/bin/env python3
"""
Quick test of DataFrame export on small PDF (10 pages).

Fast iteration to validate multi-header table detection.
"""

from pathlib import Path

import pandas as pd
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import TableItem


def test_dataframe_export():
    """Test DataFrame export on small PDF."""
    pdf_path = Path("data/test-10-pages.pdf")

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        print("   Using full PDF instead...")
        pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    print("=" * 80)
    print("DATAFRAME EXPORT TEST")
    print("=" * 80)
    print(f"File: {pdf_path}")
    print("Testing: export_to_dataframe() method")
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

            try:
                # Export to DataFrame
                df = item.export_to_dataframe()

                print("✅ DataFrame export successful!")
                print(f"   Shape: {df.shape} (rows x columns)")
                print(f"   Columns: {len(df.columns)}")
                print()

                # Check for MultiIndex columns (multi-header indicator)
                if isinstance(df.columns, pd.MultiIndex):
                    multi_header_count += 1
                    num_levels = df.columns.nlevels

                    print("🎯 MULTI-HEADER TABLE DETECTED!")
                    print(f"   - Column levels: {num_levels}")
                    print()

                    # Show first few column names
                    print("   First 3 columns:")
                    for i, col in enumerate(df.columns[:3]):
                        if isinstance(col, tuple):
                            print(f"     [{i}] {col}")
                        else:
                            print(f"     [{i}] {repr(col)}")
                    print()

                else:
                    print("   Single-header table")
                    print(f"   Column names: {list(df.columns[:5])}...")
                    print()

                # Show DataFrame structure
                print("   DataFrame head (first 3 rows, 5 cols):")
                print("-" * 80)
                print(df.iloc[:3, :5].to_string())
                print()

                # Show data types
                print(f"   Data types: {df.dtypes.value_counts().to_dict()}")
                print()

            except Exception as e:
                print(f"❌ DataFrame export failed: {e}")
                import traceback

                traceback.print_exc()
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
        print("✅ SUCCESS - Multi-header detection works via MultiIndex!")
        print("   - DataFrame export preserves table structure")
        print("   - MultiIndex columns indicate multi-header tables")
        print("   - Ready to implement DataFrame-based parser")
    else:
        print("⚠️  No multi-header tables found in first 3 tables")
        print("   - May need to check more tables")
        print("   - Or tables may have single headers")


if __name__ == "__main__":
    test_dataframe_export()
