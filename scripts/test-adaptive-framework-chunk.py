#!/usr/bin/env python3
"""Test adaptive orientation-aware framework on chunk PDF (pages 20-21).

This script validates that the Phase 2.7.4 adaptive framework maintains
the 96.77% unit population accuracy achieved on transposed tables.

Expected Results:
- Orientation detected: 'transposed'
- Confidence: >0.80
- Unit population: ≥96.77% (maintain Phase 2.7.3 performance)
- No regression from statistical framework

Usage:
    python scripts/test-adaptive-framework-chunk.py
"""

import sys
from pathlib import Path

# Add raglite to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from raglite.ingestion.adaptive_table_extraction import (
    _extract_transposed_entity_cols_metric_row_labels,
)

# Configure logging to see diagnostic output
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Test adaptive framework on chunk PDF (transposed tables)."""

    # Configuration
    chunk_pdf_path = Path("docs/sample pdf/test-chunk-pages-18-23.pdf")
    document_id = "test-chunk-pages-18-23.pdf"

    if not chunk_pdf_path.exists():
        logger.error(f"Chunk PDF not found: {chunk_pdf_path}")
        sys.exit(1)

    logger.info("=" * 80)
    logger.info("PHASE 2.7.4 - ADAPTIVE FRAMEWORK TEST (TRANSPOSED TABLES)")
    logger.info("=" * 80)
    logger.info(f"Input: {chunk_pdf_path}")
    logger.info("Expected orientation: TRANSPOSED")
    logger.info("Target accuracy: ≥96.77% (maintain Phase 2.7.3)")
    logger.info("=" * 80)

    # Configure Docling with pypdfium2 backend
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options, backend=PyPdfiumDocumentBackend
            )
        }
    )

    # Convert document
    logger.info("Converting chunk PDF with Docling...")
    result = converter.convert(str(chunk_pdf_path))

    # Extract tables
    logger.info("Extracting tables with adaptive framework...")
    all_rows = []

    # Group tables by page
    tables_by_page = {}
    for item, _ in result.document.iterate_items():
        if hasattr(item, "prov") and item.prov and len(item.prov) > 0:
            page_num = item.prov[0].page_no
            if item.__class__.__name__ == "TableItem":
                if page_num not in tables_by_page:
                    tables_by_page[page_num] = []
                tables_by_page[page_num].append(item)

    # Process each page
    for page_num in sorted(tables_by_page.keys()):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing Page {page_num}")
        logger.info(f"{'=' * 60}")

        tables = tables_by_page[page_num]
        logger.info(f"Found {len(tables)} table(s) on page {page_num}")

        for table_idx, table_item in enumerate(tables):
            logger.info(f"\n--- Table {table_idx} on Page {page_num} ---")

            # Get table cells
            if not hasattr(table_item, "data") or not hasattr(table_item.data, "table_cells"):
                logger.warning(f"Table {table_idx} has no cells - skipping")
                continue

            table_cells = table_item.data.table_cells

            # Calculate dimensions
            num_rows = max(cell.end_row_offset_idx for cell in table_cells) if table_cells else 0
            num_cols = max(cell.end_col_offset_idx for cell in table_cells) if table_cells else 0

            logger.info(f"Table dimensions: {num_rows} rows × {num_cols} columns")

            # Extract using adaptive framework
            try:
                rows = _extract_transposed_entity_cols_metric_row_labels(
                    table_cells=table_cells,
                    num_rows=num_rows,
                    num_cols=num_cols,
                    metadata={},
                    document_id=document_id,
                    page_number=page_num,
                    table_index=table_idx,
                    table_item=table_item,
                    result=result,
                )

                all_rows.extend(rows)
                logger.info(f"Extracted {len(rows)} data rows")

            except Exception as e:
                logger.error(f"Error extracting table {table_idx}: {e}", exc_info=True)

    # Analysis
    logger.info("\n" + "=" * 80)
    logger.info("RESULTS ANALYSIS")
    logger.info("=" * 80)

    total_rows = len(all_rows)
    rows_with_units = sum(1 for row in all_rows if row.get("unit") is not None)

    unit_population_pct = (rows_with_units / total_rows * 100) if total_rows > 0 else 0.0

    logger.info(f"Total data rows extracted: {total_rows}")
    logger.info(f"Rows with units: {rows_with_units}")
    logger.info(f"Unit population: {unit_population_pct:.2f}%")

    # Sample output
    if all_rows:
        logger.info("\nSample extracted rows (first 5):")
        for i, row in enumerate(all_rows[:5]):
            logger.info(f"  Row {i + 1}:")
            logger.info(f"    Entity: {row.get('entity')}")
            logger.info(f"    Metric: {row.get('metric')}")
            logger.info(f"    Period: {row.get('period')}")
            logger.info(f"    Value: {row.get('value')}")
            logger.info(f"    Unit: {row.get('unit')} {'✅' if row.get('unit') else '❌'}")

    # Success criteria
    logger.info("\n" + "=" * 80)
    logger.info("SUCCESS CRITERIA")
    logger.info("=" * 80)

    target_accuracy = 96.77
    success = unit_population_pct >= target_accuracy

    logger.info(f"Target: ≥{target_accuracy:.2f}% unit population")
    logger.info(f"Actual: {unit_population_pct:.2f}%")
    logger.info(f"Status: {'✅ PASS' if success else '❌ FAIL'}")

    if success:
        logger.info("\n🎉 SUCCESS: Adaptive framework maintains transposed table accuracy!")
        logger.info("   No regression from Phase 2.7.3 statistical framework")
    else:
        logger.warning("\n⚠️  REGRESSION: Unit population dropped below target!")
        logger.warning(f"   Expected: ≥{target_accuracy:.2f}%")
        logger.warning(f"   Actual: {unit_population_pct:.2f}%")
        logger.warning(f"   Delta: {unit_population_pct - target_accuracy:.2f} percentage points")

    logger.info("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
