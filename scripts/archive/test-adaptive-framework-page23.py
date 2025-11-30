#!/usr/bin/env python3
"""Test adaptive orientation-aware framework on full PDF page 23 (normal table).

This script validates that the Phase 2.7.4 adaptive framework successfully
handles normal table orientation and achieves >85% unit population accuracy.

Expected Results:
- Orientation detected: 'normal'
- Confidence: >0.70
- Unit population: >85% (vs 37.07% baseline from Phase 2.7.3)
- Improvement: ~+48 percentage points

Usage:
    python scripts/test-adaptive-framework-page23.py
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
    """Test adaptive framework on page 23 (normal table)."""

    # Configuration
    full_pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
    document_id = "2025-08 Performance Review CONSO_v2.pdf"
    target_page = 23

    if not full_pdf_path.exists():
        logger.error(f"Full PDF not found: {full_pdf_path}")
        sys.exit(1)

    logger.info("=" * 80)
    logger.info("PHASE 2.7.4 - ADAPTIVE FRAMEWORK TEST (NORMAL TABLE)")
    logger.info("=" * 80)
    logger.info(f"Input: {full_pdf_path}")
    logger.info(f"Target page: {target_page}")
    logger.info("Expected orientation: NORMAL")
    logger.info("Baseline accuracy: 37.07% (Phase 2.7.3)")
    logger.info("Target accuracy: >85%")
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
    logger.info("Converting full PDF with Docling...")
    result = converter.convert(str(full_pdf_path))

    # Extract tables from page 23 only
    logger.info(f"\nProcessing Page {target_page}...")
    all_rows = []

    # Find tables on target page
    page_tables = []
    for item, _ in result.document.iterate_items():
        if hasattr(item, "prov") and item.prov and len(item.prov) > 0:
            page_num = item.prov[0].page_no
            if page_num == target_page and item.__class__.__name__ == "TableItem":
                page_tables.append(item)

    logger.info(f"{'=' * 60}")
    logger.info(f"Page {target_page}")
    logger.info(f"{'=' * 60}")

    logger.info(f"Found {len(page_tables)} table(s) on page {target_page}")

    if page_tables:
        for table_idx, table_item in enumerate(page_tables):
            logger.info(f"\n--- Table {table_idx} on Page {target_page} ---")

            # Get table cells
            if not hasattr(table_item, "data") or not hasattr(table_item.data, "table_cells"):
                logger.warning(f"Table {table_idx} has no cells - skipping")
                continue

            table_cells = table_item.data.table_cells

            # Calculate dimensions
            num_rows = max(cell.end_row_offset_idx for cell in table_cells) if table_cells else 0
            num_cols = max(cell.end_col_offset_idx for cell in table_cells) if table_cells else 0

            logger.info(f"Table dimensions: {num_rows} rows × {num_cols} columns")
            logger.info(f"Aspect ratio: {num_rows / num_cols:.2f} (rows/cols)")

            # Extract using adaptive framework
            try:
                rows = _extract_transposed_entity_cols_metric_row_labels(
                    table_cells=table_cells,
                    num_rows=num_rows,
                    num_cols=num_cols,
                    metadata={},
                    document_id=document_id,
                    page_number=target_page,
                    table_index=table_idx,
                    table_item=table_item,
                    result=result,
                )

                all_rows.extend(rows)
                logger.info(f"Extracted {len(rows)} data rows")

            except Exception as e:
                logger.error(f"Error extracting table {table_idx}: {e}", exc_info=True)
    else:
        logger.error(f"No tables found on page {target_page}")
        sys.exit(1)

    # Analysis
    logger.info("\n" + "=" * 80)
    logger.info("RESULTS ANALYSIS")
    logger.info("=" * 80)

    total_rows = len(all_rows)
    rows_with_units = sum(1 for row in all_rows if row.get("unit") is not None)

    unit_population_pct = (rows_with_units / total_rows * 100) if total_rows > 0 else 0.0
    baseline_accuracy = 37.07
    improvement = unit_population_pct - baseline_accuracy

    logger.info(f"Total data rows extracted: {total_rows}")
    logger.info(f"Rows with units: {rows_with_units}")
    logger.info(f"Unit population: {unit_population_pct:.2f}%")
    logger.info(f"Baseline (Phase 2.7.3): {baseline_accuracy:.2f}%")
    logger.info(f"Improvement: {improvement:+.2f} percentage points")

    # Sample output
    if all_rows:
        logger.info("\nSample extracted rows (first 10):")
        for i, row in enumerate(all_rows[:10]):
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

    target_accuracy = 85.0
    success = unit_population_pct >= target_accuracy

    logger.info(f"Target: ≥{target_accuracy:.2f}% unit population")
    logger.info(f"Actual: {unit_population_pct:.2f}%")
    logger.info(f"Status: {'✅ PASS' if success else '❌ FAIL'}")

    if success:
        logger.info("\n🎉 SUCCESS: Adaptive framework handles normal tables!")
        logger.info(f"   Improvement: {improvement:+.2f} percentage points")
        logger.info("   Phase 2.7.4 solves normal table orientation challenge")
    else:
        logger.warning("\n⚠️  BELOW TARGET: Unit population not yet at target!")
        logger.warning(f"   Expected: ≥{target_accuracy:.2f}%")
        logger.warning(f"   Actual: {unit_population_pct:.2f}%")
        logger.warning(f"   Gap: {target_accuracy - unit_population_pct:.2f} percentage points")
        if improvement > 0:
            logger.info(f"   ✅ Still improved by {improvement:+.2f}pp from baseline")

    logger.info("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
