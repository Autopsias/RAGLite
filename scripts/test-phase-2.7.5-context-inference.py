#!/usr/bin/env python3
"""
Test Phase 2.7.5: Context-Aware Unit Inference

Tests the LLM-based unit inference on chunk PDF to validate:
- Overall accuracy improvement from 74.22% → 90-95%
- Type B (entity-column junk) improvement from 0% → 85-90%
- Type C (normal metric) improvement from 77.62% → 90-95%
- Page 23 improvement from 37.07% → 85-90%

Expected impact: +16-21 percentage points
"""

import logging
import sys
from pathlib import Path

# Add raglite to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.document_converter import DocumentConverter

from raglite.ingestion.adaptive_table_extraction import extract_table_data_adaptive

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Test Phase 2.7.5 on chunk PDF."""
    # Use chunk PDF (pages 18-23 of original document)
    pdf_path = "docs/sample pdf/test-chunk-pages-18-23.pdf"

    if not Path(pdf_path).exists():
        logger.error(f"PDF not found: {pdf_path}")
        return

    logger.info("=" * 80)
    logger.info("PHASE 2.7.5: CONTEXT-AWARE UNIT INFERENCE TEST")
    logger.info("=" * 80)
    logger.info(f"Testing: {pdf_path}")
    logger.info("")

    # Convert PDF with Docling
    logger.info("Converting PDF with Docling...")
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    logger.info("Conversion complete")
    logger.info("")

    # Group tables by page
    tables_by_page = {}
    for item, _ in result.document.iterate_items():
        if hasattr(item, "prov") and item.prov and len(item.prov) > 0:
            page_num = item.prov[0].page_no
            if item.__class__.__name__ == "TableItem":
                if page_num not in tables_by_page:
                    tables_by_page[page_num] = []
                tables_by_page[page_num].append(item)

    # Extract all tables
    all_rows = []
    table_stats_by_page = {}

    for page_num in sorted(tables_by_page.keys()):
        page_rows = []
        tables = tables_by_page[page_num]

        for table_idx, table_item in enumerate(tables):
            table_rows = extract_table_data_adaptive(
                table_item=table_item,
                result=result,
                table_index=table_idx,
                document_id=pdf_path,
                page_number=page_num,
            )
            page_rows.extend(table_rows)

        # Calculate page stats
        total_rows = len(page_rows)
        rows_with_units = sum(1 for row in page_rows if row.get("unit") is not None)
        unit_population = (rows_with_units / total_rows * 100) if total_rows > 0 else 0

        # Count unit sources
        explicit_units = sum(1 for row in page_rows if row.get("unit_source") in [None, "explicit"])
        llm_inferred = sum(1 for row in page_rows if row.get("unit_source") == "llm_inference")
        cached_inferred = sum(
            1 for row in page_rows if row.get("unit_source") == "cached_inference"
        )

        table_stats_by_page[page_num] = {
            "total_rows": total_rows,
            "rows_with_units": rows_with_units,
            "unit_population": unit_population,
            "explicit_units": explicit_units,
            "llm_inferred": llm_inferred,
            "cached_inferred": cached_inferred,
        }

        all_rows.extend(page_rows)
        logger.info(
            f"Page {page_num}: {total_rows} rows, {rows_with_units} with units ({unit_population:.2f}%)"
        )
        logger.info(
            f"  Sources: {explicit_units} explicit, {llm_inferred} LLM, {cached_inferred} cached"
        )

    # Overall statistics
    logger.info("")
    logger.info("=" * 80)
    logger.info("OVERALL RESULTS")
    logger.info("=" * 80)

    total_rows = len(all_rows)
    total_with_units = sum(1 for row in all_rows if row.get("unit") is not None)
    overall_accuracy = (total_with_units / total_rows * 100) if total_rows > 0 else 0

    logger.info(f"Total rows extracted: {total_rows}")
    logger.info(f"Rows with units: {total_with_units}")
    logger.info(f"Unit population: {overall_accuracy:.2f}%")
    logger.info("")

    # Unit source breakdown
    explicit_count = sum(1 for row in all_rows if row.get("unit_source") in [None, "explicit"])
    llm_count = sum(1 for row in all_rows if row.get("unit_source") == "llm_inference")
    cached_count = sum(1 for row in all_rows if row.get("unit_source") == "cached_inference")

    logger.info("Unit Sources:")
    logger.info(
        f"  Explicit extraction: {explicit_count} ({explicit_count / total_rows * 100:.1f}%)"
    )
    logger.info(f"  LLM inference: {llm_count} ({llm_count / total_rows * 100:.1f}%)")
    logger.info(f"  Cached inference: {cached_count} ({cached_count / total_rows * 100:.1f}%)")
    logger.info("")

    # Compare with Phase 2.7.4 baseline
    baseline_accuracy = 74.22
    improvement = overall_accuracy - baseline_accuracy

    logger.info("=" * 80)
    logger.info("COMPARISON WITH BASELINE")
    logger.info("=" * 80)
    logger.info(f"Phase 2.7.4 Baseline: {baseline_accuracy:.2f}%")
    logger.info(f"Phase 2.7.5 Result: {overall_accuracy:.2f}%")
    logger.info(f"Improvement: {improvement:+.2f} percentage points")
    logger.info("")

    # Success criteria
    target_min = 90.0
    target_max = 95.0

    logger.info("=" * 80)
    logger.info("SUCCESS CRITERIA")
    logger.info("=" * 80)
    logger.info(f"Target: {target_min:.0f}%-{target_max:.0f}% unit population")
    logger.info(f"Actual: {overall_accuracy:.2f}%")

    if overall_accuracy >= target_min:
        logger.info(f"Status: ✅ PASS (≥{target_min:.0f}%)")
    else:
        gap = target_min - overall_accuracy
        logger.warning(f"Status: ❌ FAIL (gap: {gap:.2f}pp)")
        logger.warning("")
        logger.warning("⚠️  BELOW TARGET: Unit population not yet at target!")
        logger.warning(f"   Expected: ≥{target_min:.0f}%")
        logger.warning(f"   Actual: {overall_accuracy:.2f}%")
        logger.warning(f"   Gap: {gap:.2f} percentage points")

    logger.info("=" * 80)

    # Sample extracted rows with units
    logger.info("")
    logger.info("Sample extracted rows (first 10):")
    for i, row in enumerate(all_rows[:10], 1):
        unit_source = row.get("unit_source", "explicit")
        unit_str = f"{row.get('unit')} ({unit_source})" if row.get("unit") else "None"
        logger.info(f"  Row {i}:")
        logger.info(f"    Entity: {row.get('entity')}")
        logger.info(f"    Metric: {row.get('metric')}")
        logger.info(f"    Period: {row.get('period')}")
        logger.info(f"    Value: {row.get('value')}")
        logger.info(f"    Unit: {unit_str}")

    logger.info("")
    logger.info("Test complete!")


if __name__ == "__main__":
    main()
