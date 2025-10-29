#!/usr/bin/env python3
"""Test adaptive extraction on pages 1-20 and analyze patterns."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from docling_core.types.doc import TableItem

from raglite.ingestion.adaptive_table_extraction import (
    classify_header,
    detect_table_layout,
    extract_table_data_adaptive,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def analyze_table_pattern(table_item: TableItem, result, page_no: int, table_idx: int):
    """Analyze a single table's pattern."""
    table_cells = table_item.data.table_cells
    num_rows = table_item.data.num_rows
    num_cols = table_item.data.num_cols

    # Detect layout
    layout, metadata = detect_table_layout(table_cells, num_rows, num_cols)

    # Get column headers
    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]

    # Count header rows
    col_header_rows = {cell.start_row_offset_idx for cell in column_headers}

    # Classify sample headers
    col_samples = []
    row_samples = []

    for cell in column_headers[:5]:
        h_type = classify_header(cell.text)
        col_samples.append((cell.text[:30], h_type.value))

    for cell in row_headers[:5]:
        h_type = classify_header(cell.text)
        row_samples.append((cell.text[:30], h_type.value))

    return {
        "page": page_no,
        "table": table_idx,
        "layout": layout.value,
        "dimensions": f"{num_rows}x{num_cols}",
        "header_rows": len(col_header_rows),
        "col_samples": col_samples,
        "row_samples": row_samples,
        "metadata": metadata,
    }


def main():
    """Test adaptive extraction on pages 1-20."""
    pdf_path = Path("docs/sample pdf/test-pages-1-20.pdf")

    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        logger.error("Run: python scripts/extract-pages-1-20.py first")
        return

    logger.info("=" * 80)
    logger.info("ADAPTIVE EXTRACTION TEST - Pages 1-20")
    logger.info("=" * 80)
    logger.info(f"PDF: {pdf_path}")
    logger.info(f"Size: {pdf_path.stat().st_size / 1024:.1f} KB")
    logger.info("")

    # Convert PDF
    logger.info("Converting PDF with Docling...")
    converter = DocumentConverter(allowed_formats=[InputFormat.PDF])
    result = converter.convert(pdf_path)

    if not result.document:
        logger.error("PDF conversion failed!")
        return

    logger.info("✅ Conversion complete")
    logger.info("")

    # Extract and analyze all tables
    logger.info("Analyzing table patterns...")
    logger.info("")

    table_analyses = []
    extraction_results = []

    table_count = 0
    for element, _ in result.document.iterate_items():
        if isinstance(element, TableItem):
            # Get page number
            page_no = None
            if hasattr(element, "prov") and element.prov:
                for prov_item in element.prov:
                    if hasattr(prov_item, "page_no"):
                        page_no = prov_item.page_no
                        break

            if page_no is None:
                continue

            table_count += 1

            # Analyze pattern
            analysis = analyze_table_pattern(element, result, page_no, table_count)
            table_analyses.append(analysis)

            # Try extraction
            rows = extract_table_data_adaptive(
                table_item=element,
                result=result,
                table_index=table_count,
                document_id="test-pages-1-20",
                page_number=page_no,
            )

            extraction_results.append(
                {
                    "page": page_no,
                    "table": table_count,
                    "layout": analysis["layout"],
                    "rows_extracted": len(rows),
                    "success": len(rows) > 0,
                }
            )

            # Log result
            status = "✅" if len(rows) > 0 else "⚠️"
            logger.info(
                f"{status} Page {page_no}, Table {table_count}: {analysis['layout']} ({analysis['dimensions']}) → {len(rows)} rows"
            )

    # Summary statistics
    logger.info("")
    logger.info("=" * 80)
    logger.info("PATTERN ANALYSIS")
    logger.info("=" * 80)

    # Count layouts
    layout_counts = Counter(a["layout"] for a in table_analyses)
    logger.info("\nTable Layouts Detected:")
    for layout, count in layout_counts.most_common():
        logger.info(f"  {layout}: {count} tables")

    # Success rate by layout
    logger.info("\nExtraction Success by Layout:")
    for layout in layout_counts.keys():
        layout_tables = [r for r in extraction_results if r["layout"] == layout]
        successful = [r for r in layout_tables if r["success"]]
        success_rate = (len(successful) / len(layout_tables) * 100) if layout_tables else 0
        logger.info(f"  {layout}: {len(successful)}/{len(layout_tables)} ({success_rate:.1f}%)")

    # Show failed patterns in detail
    logger.info("\n" + "=" * 80)
    logger.info("FAILED PATTERNS (Need Implementation)")
    logger.info("=" * 80)

    failed = [
        a for a, r in zip(table_analyses, extraction_results, strict=False) if not r["success"]
    ]

    if failed:
        for analysis in failed:
            logger.info(f"\nPage {analysis['page']}, Table {analysis['table']}:")
            logger.info(f"  Layout: {analysis['layout']}")
            logger.info(f"  Dimensions: {analysis['dimensions']}")
            logger.info(f"  Header rows: {analysis['header_rows']}")
            logger.info(f"  Column samples: {analysis['col_samples'][:3]}")
            logger.info(f"  Row samples: {analysis['row_samples'][:3]}")
    else:
        logger.info("✅ All patterns extracted successfully!")

    # Overall stats
    total_tables = len(extraction_results)
    successful_tables = len([r for r in extraction_results if r["success"]])
    success_rate = (successful_tables / total_tables * 100) if total_tables else 0

    logger.info("")
    logger.info("=" * 80)
    logger.info("OVERALL RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total tables: {total_tables}")
    logger.info(f"Successfully extracted: {successful_tables} ({success_rate:.1f}%)")
    logger.info(f"Failed (need implementation): {total_tables - successful_tables}")

    return extraction_results, table_analyses


if __name__ == "__main__":
    import time

    start = time.time()

    results, analyses = main()

    elapsed = time.time() - start
    logger.info(f"\nCompleted in {elapsed:.1f} seconds")
