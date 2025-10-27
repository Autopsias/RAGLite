#!/usr/bin/env python3
"""Comprehensive table type analysis for adaptive framework design.

This script analyzes ALL tables in the chunk PDF to understand the different
table structures and design appropriate extraction strategies.

Goal: Build a robust detection system that adapts to ANY table type.

Usage:
    python scripts/analyze-table-types.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def analyze_table_structure(table_cells, num_rows, num_cols):
    """Analyze table structure and classify type."""

    # Get column 0 cells
    col_0_cells = [c for c in table_cells if c.start_col_offset_idx == 0 and not c.column_header]

    # Analyze column 0 content
    metric_patterns = [
        "EBITDA",
        "EBIT",
        "Revenue",
        "Sales",
        "Turnover",
        "Margin",
        "Profit",
        "Loss",
        "Cost",
        "Expense",
        "Income",
        "Debt",
        "Cash",
        "Asset",
        "Liability",
        "Equity",
        "Volume",
        "Production",
        "Capacity",
        "CAPEX",
        "OPEX",
        "Investment",
        "Price",
    ]

    entity_patterns = [
        "GROUP",
        "PORTUGAL",
        "ANGOLA",
        "Entity",
        "Company",
        "Country",
        "Region",
        "Division",
        "Segment",
        "Business",
        "Unit",
        "Branch",
        "Subsidiary",
    ]

    metric_count = 0
    entity_count = 0
    numeric_count = 0
    text_count = 0

    col_0_samples = []

    for cell in col_0_cells[:10]:  # First 10 cells as sample
        if not cell.text:
            continue

        cell_text = cell.text.strip()
        col_0_samples.append(cell_text)

        # Check patterns
        if any(p.upper() in cell_text.upper() for p in metric_patterns):
            metric_count += 1
        elif any(p.upper() in cell_text.upper() for p in entity_patterns):
            entity_count += 1

        # Check if numeric
        try:
            float(cell_text.replace(",", "").replace(" ", ""))
            numeric_count += 1
        except:
            text_count += 1

    total_samples = len(col_0_samples)

    # Get column 1 cells (potential units column)
    col_1_cells = [c for c in table_cells if c.start_col_offset_idx == 1 and not c.column_header]
    col_1_samples = [c.text.strip() for c in col_1_cells[:10] if c.text]

    # Get column headers
    headers = [c for c in table_cells if c.column_header]
    header_samples = [c.text.strip() for c in headers[:10] if c.text]

    # Get first 3 rows (check for unit rows)
    row_0 = [c.text.strip() for c in table_cells if c.start_row_offset_idx == 0 and c.text]
    row_1 = [c.text.strip() for c in table_cells if c.start_row_offset_idx == 1 and c.text]
    row_2 = [c.text.strip() for c in table_cells if c.start_row_offset_idx == 2 and c.text]

    return {
        "dimensions": f"{num_rows} rows × {num_cols} cols",
        "aspect_ratio": num_rows / num_cols if num_cols > 0 else 0,
        "col_0_samples": col_0_samples,
        "col_0_analysis": {
            "metric_count": metric_count,
            "entity_count": entity_count,
            "numeric_count": numeric_count,
            "text_count": text_count,
            "total": total_samples,
            "metric_ratio": metric_count / total_samples if total_samples > 0 else 0,
            "numeric_ratio": numeric_count / total_samples if total_samples > 0 else 0,
        },
        "col_1_samples": col_1_samples,
        "header_samples": header_samples,
        "row_0_samples": row_0[:5],
        "row_1_samples": row_1[:5],
        "row_2_samples": row_2[:5],
    }


def main():
    chunk_pdf_path = Path("docs/sample pdf/test-chunk-pages-18-23.pdf")

    if not chunk_pdf_path.exists():
        logger.error(f"Chunk PDF not found: {chunk_pdf_path}")
        sys.exit(1)

    logger.info("=" * 100)
    logger.info("COMPREHENSIVE TABLE TYPE ANALYSIS")
    logger.info("=" * 100)
    logger.info(f"Input: {chunk_pdf_path}")
    logger.info("")

    # Configure Docling
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

    logger.info("Converting PDF...")
    result = converter.convert(str(chunk_pdf_path))
    logger.info("✅ Converted")
    logger.info("")

    # Group tables by page
    tables_by_page = {}
    for item_idx, (item, level) in enumerate(result.document.iterate_items()):
        if hasattr(item, "prov") and item.prov and len(item.prov) > 0:
            page_num = item.prov[0].page_no
            if item.__class__.__name__ == "TableItem":
                if page_num not in tables_by_page:
                    tables_by_page[page_num] = []
                tables_by_page[page_num].append(item)

    # Analyze each table
    table_count = 0
    for page_num in sorted(tables_by_page.keys()):
        tables = tables_by_page[page_num]

        for table_idx, table_item in enumerate(tables):
            table_count += 1

            logger.info("=" * 100)
            logger.info(f"TABLE #{table_count} - Page {page_num}, Table {table_idx}")
            logger.info("=" * 100)

            if not hasattr(table_item, "data") or not hasattr(table_item.data, "table_cells"):
                logger.info("⚠️  No cells - skipping")
                logger.info("")
                continue

            table_cells = table_item.data.table_cells
            num_rows = max(cell.end_row_offset_idx for cell in table_cells) if table_cells else 0
            num_cols = max(cell.end_col_offset_idx for cell in table_cells) if table_cells else 0

            analysis = analyze_table_structure(table_cells, num_rows, num_cols)

            logger.info(
                f"📏 Dimensions: {analysis['dimensions']} (aspect ratio: {analysis['aspect_ratio']:.2f})"
            )
            logger.info("")

            logger.info("🔍 Column 0 Analysis:")
            col_0 = analysis["col_0_analysis"]
            logger.info(
                f"   Metric patterns: {col_0['metric_count']}/{col_0['total']} ({col_0['metric_ratio']:.1%})"
            )
            logger.info(
                f"   Numeric values: {col_0['numeric_count']}/{col_0['total']} ({col_0['numeric_ratio']:.1%})"
            )
            logger.info(f"   Text values: {col_0['text_count']}/{col_0['total']}")
            logger.info(f"   Entity patterns: {col_0['entity_count']}/{col_0['total']}")
            logger.info("")

            logger.info("📋 Column 0 Samples (first 5):")
            for i, sample in enumerate(analysis["col_0_samples"][:5], 1):
                logger.info(f"   [{i}] {sample}")
            logger.info("")

            logger.info("📋 Column 1 Samples (first 5):")
            for i, sample in enumerate(analysis["col_1_samples"][:5], 1):
                logger.info(f"   [{i}] {sample}")
            logger.info("")

            logger.info("📋 Column Headers (first 5):")
            for i, sample in enumerate(analysis["header_samples"][:5], 1):
                logger.info(f"   [{i}] {sample}")
            logger.info("")

            logger.info("📋 Row 0 (first 5 cells):")
            logger.info(f"   {', '.join(analysis['row_0_samples'])}")
            logger.info("")

            logger.info("📋 Row 1 (first 5 cells):")
            logger.info(f"   {', '.join(analysis['row_1_samples'])}")
            logger.info("")

            logger.info("📋 Row 2 (first 5 cells):")
            logger.info(f"   {', '.join(analysis['row_2_samples'])}")
            logger.info("")

            # Classification
            logger.info("🎯 PRELIMINARY CLASSIFICATION:")

            if col_0["metric_ratio"] > 0.5:
                logger.info("   ✅ TYPE A: Transposed Metric-Entity Table")
                logger.info("      → Metrics in Column 0, likely Units in Column 1")
            elif col_0["numeric_ratio"] > 0.7:
                logger.info("   ✅ TYPE B: Row-Indexed or Pure Data Table")
                logger.info("      → Numeric values in Column 0, investigate Columns 1+")
            else:
                logger.info("   ✅ TYPE C: Normal or Mixed Table")
                logger.info("      → Check row headers and dedicated unit rows")

            logger.info("")

    logger.info("=" * 100)
    logger.info(f"SUMMARY: Analyzed {table_count} tables across {len(tables_by_page)} pages")
    logger.info("=" * 100)


if __name__ == "__main__":
    main()
