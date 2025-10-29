#!/usr/bin/env python3
"""Test adaptive table extraction on small 3-page PDF.

This script:
1. Converts the small test PDF (pages 4, 10, 20)
2. Extracts tables using adaptive extraction module
3. Analyzes the results to validate adaptive extraction logic
4. Expected runtime: ~30 seconds vs ~45 minutes for full PDF
"""

import sys
from pathlib import Path

# Add raglite to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter

from raglite.ingestion.adaptive_table_extraction import extract_table_data_adaptive
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def test_adaptive_extraction():
    """Test adaptive extraction on small PDF."""
    pdf_path = Path("docs/sample pdf/test-pages-4-10-20.pdf")

    if not pdf_path.exists():
        logger.error(f"Test PDF not found: {pdf_path}")
        logger.error("Run: python scripts/extract-test-pages.py first")
        return

    logger.info("=" * 80)
    logger.info("ADAPTIVE TABLE EXTRACTION TEST - Small PDF")
    logger.info("=" * 80)
    logger.info(f"PDF: {pdf_path}")
    logger.info(f"Size: {pdf_path.stat().st_size / 1024:.1f} KB")
    logger.info("Expected runtime: ~30 seconds")
    logger.info("")

    # Convert PDF
    logger.info("Step 1: Converting PDF with Docling...")
    converter = DocumentConverter(allowed_formats=[InputFormat.PDF])
    result = converter.convert(pdf_path)

    if not result.document:
        logger.error("PDF conversion failed!")
        return

    logger.info("✅ Conversion complete")
    logger.info("")

    # Extract tables with adaptive extraction
    logger.info("Step 2: Extracting tables with adaptive module...")

    all_table_rows = []
    table_count = 0

    for element, _level in result.document.iterate_items():
        from docling_core.types.doc import TableItem

        if isinstance(element, TableItem):
            table_count += 1

            # Get page number
            page_no = None
            if hasattr(element, "prov") and element.prov:
                for prov_item in element.prov:
                    if hasattr(prov_item, "page_no"):
                        page_no = prov_item.page_no
                        break

            logger.info(f"  Table {table_count} (Page {page_no}):")

            # Extract using adaptive module
            table_rows = extract_table_data_adaptive(
                table_item=element,
                result=result,
                table_index=table_count,
                document_id="test-doc",
                page_number=page_no or 0,
            )

            logger.info(f"    Rows extracted: {len(table_rows)}")

            if table_rows:
                # Show sample rows
                for row in table_rows[:3]:
                    logger.info(
                        f"      Entity: {row.get('entity', 'None')}, "
                        f"Metric: {row.get('metric', 'None')}, "
                        f"Period: {row.get('period', 'None')}"
                    )
                if len(table_rows) > 3:
                    logger.info(f"      ... and {len(table_rows) - 3} more rows")
            else:
                logger.warning("    ⚠️ No rows extracted (unknown layout?)")

            all_table_rows.extend(table_rows)

    logger.info("")
    logger.info("=" * 80)
    logger.info("RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total tables found: {table_count}")
    logger.info(f"Total rows extracted: {len(all_table_rows)}")

    if all_table_rows:
        # Analyze data quality
        entities = {row.get("entity") for row in all_table_rows if row.get("entity")}
        metrics = {row.get("metric") for row in all_table_rows if row.get("metric")}
        periods = {row.get("period") for row in all_table_rows if row.get("period")}

        logger.info("")
        logger.info("Data Quality Check:")
        logger.info(f"  Unique entities: {len(entities)}")
        logger.info(f"  Unique metrics: {len(metrics)}")
        logger.info(f"  Unique periods: {len(periods)}")

        logger.info("")
        logger.info("Sample entities:")
        for entity in list(entities)[:5]:
            logger.info(f"  - {entity}")

        logger.info("")
        logger.info("Sample metrics:")
        for metric in list(metrics)[:5]:
            logger.info(f"  - {metric}")

        logger.info("")
        logger.info("Sample periods:")
        for period in list(periods)[:5]:
            logger.info(f"  - {period}")

        # Check for data corruption (periods/years in wrong fields)
        corrupted_entities = [
            e
            for e in entities
            if e
            and any(year in str(e) for year in ["2020", "2021", "2022", "2023", "2024", "2025"])
        ]
        corrupted_metrics = [
            m
            for m in metrics
            if m
            and any(year in str(m) for year in ["2020", "2021", "2022", "2023", "2024", "2025"])
        ]

        logger.info("")
        if corrupted_entities or corrupted_metrics:
            logger.error("⚠️ POTENTIAL DATA CORRUPTION DETECTED:")
            if corrupted_entities:
                logger.error(f"  Years found in entities: {corrupted_entities[:5]}")
            if corrupted_metrics:
                logger.error(f"  Years found in metrics: {corrupted_metrics[:5]}")
        else:
            logger.info("✅ No obvious data corruption detected")
    else:
        logger.error("❌ NO DATA EXTRACTED - Adaptive extraction may have issues")

    logger.info("")
    logger.info("=" * 80)

    return all_table_rows


if __name__ == "__main__":
    import time

    start = time.time()

    rows = test_adaptive_extraction()

    elapsed = time.time() - start
    logger.info(f"Test completed in {elapsed:.1f} seconds")

    if rows:
        logger.info("✅ Test PASSED - Adaptive extraction working")
        sys.exit(0)
    else:
        logger.error("❌ Test FAILED - No data extracted")
        sys.exit(1)
