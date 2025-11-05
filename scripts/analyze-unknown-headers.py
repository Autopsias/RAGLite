#!/usr/bin/env python3
"""Analyze UNKNOWN headers to improve classification patterns.

Goal: Understand what headers are being classified as UNKNOWN (87.3%)
and expand regex patterns to recognize them.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from docling_core.types.doc import TableItem

from raglite.ingestion.adaptive_table_extraction import HeaderType, classify_header
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def main():
    """Analyze UNKNOWN headers on 20-page test PDF."""
    pdf_path = Path("docs/sample pdf/test-pages-1-20.pdf")

    logger.info("=" * 80)
    logger.info("UNKNOWN HEADER ANALYSIS (20-page test)")
    logger.info("=" * 80)
    logger.info(f"PDF: {pdf_path}")
    logger.info("")

    # Convert PDF
    logger.info("Converting PDF...")
    converter = DocumentConverter(allowed_formats=[InputFormat.PDF])
    result = converter.convert(pdf_path)

    if not result.document:
        logger.error("PDF conversion failed!")
        return

    logger.info("✅ Conversion complete")
    logger.info("")

    # Collect all headers
    all_col_headers = []
    all_row_headers = []
    unknown_col_headers = []
    unknown_row_headers = []

    table_count = 0
    for element, _ in result.document.iterate_items():
        if isinstance(element, TableItem):
            table_count += 1
            table_cells = element.data.table_cells

            col_headers = [cell for cell in table_cells if cell.column_header]
            row_headers = [cell for cell in table_cells if cell.row_header]

            for cell in col_headers:
                if cell.text:
                    header_text = cell.text.strip()
                    all_col_headers.append(header_text)
                    h_type = classify_header(header_text)
                    if h_type == HeaderType.UNKNOWN:
                        unknown_col_headers.append(header_text)

            for cell in row_headers:
                if cell.text:
                    header_text = cell.text.strip()
                    all_row_headers.append(header_text)
                    h_type = classify_header(header_text)
                    if h_type == HeaderType.UNKNOWN:
                        unknown_row_headers.append(header_text)

    # Statistics
    logger.info("STATISTICS")
    logger.info("=" * 80)
    logger.info(f"Total tables: {table_count}")
    logger.info(f"Total column headers: {len(all_col_headers)}")
    logger.info(f"Total row headers: {len(all_row_headers)}")
    logger.info("")
    logger.info(
        f"UNKNOWN column headers: {len(unknown_col_headers)}/{len(all_col_headers)} ({len(unknown_col_headers) / len(all_col_headers) * 100:.1f}%)"
    )
    logger.info(
        f"UNKNOWN row headers: {len(unknown_row_headers)}/{len(all_row_headers)} ({len(unknown_row_headers) / len(all_row_headers) * 100:.1f}%)"
    )
    logger.info("")

    # Classification breakdown
    logger.info("COLUMN HEADER CLASSIFICATION BREAKDOWN")
    logger.info("=" * 80)
    col_types = Counter()
    for header in all_col_headers:
        h_type = classify_header(header)
        col_types[h_type.value] += 1

    for htype, count in col_types.most_common():
        pct = count / len(all_col_headers) * 100 if all_col_headers else 0
        logger.info(f"  {htype}: {count}/{len(all_col_headers)} ({pct:.1f}%)")

    logger.info("")
    logger.info("ROW HEADER CLASSIFICATION BREAKDOWN")
    logger.info("=" * 80)
    row_types = Counter()
    for header in all_row_headers:
        h_type = classify_header(header)
        row_types[h_type.value] += 1

    for htype, count in row_types.most_common():
        pct = count / len(all_row_headers) * 100 if all_row_headers else 0
        logger.info(f"  {htype}: {count}/{len(all_row_headers)} ({pct:.1f}%)")

    # Sample UNKNOWN headers
    logger.info("")
    logger.info("=" * 80)
    logger.info("SAMPLE UNKNOWN COLUMN HEADERS (first 50)")
    logger.info("=" * 80)
    for i, header in enumerate(unknown_col_headers[:50], 1):
        logger.info(f"{i:3d}. {header}")

    logger.info("")
    logger.info("=" * 80)
    logger.info("SAMPLE UNKNOWN ROW HEADERS (first 50)")
    logger.info("=" * 80)
    for i, header in enumerate(unknown_row_headers[:50], 1):
        logger.info(f"{i:3d}. {header}")

    # Identify patterns in UNKNOWN headers
    logger.info("")
    logger.info("=" * 80)
    logger.info("PATTERN ANALYSIS (What should these be?)")
    logger.info("=" * 80)

    # Common words in UNKNOWN column headers
    col_words = Counter()
    for header in unknown_col_headers:
        words = header.lower().split()
        for word in words:
            # Skip very short words
            if len(word) >= 3:
                col_words[word] += 1

    logger.info("")
    logger.info("Most common words in UNKNOWN column headers:")
    for word, count in col_words.most_common(30):
        logger.info(f"  {word}: {count}")

    # Common words in UNKNOWN row headers
    row_words = Counter()
    for header in unknown_row_headers:
        words = header.lower().split()
        for word in words:
            # Skip very short words
            if len(word) >= 3:
                row_words[word] += 1

    logger.info("")
    logger.info("Most common words in UNKNOWN row headers:")
    for word, count in row_words.most_common(30):
        logger.info(f"  {word}: {count}")

    # Manual categorization suggestions
    logger.info("")
    logger.info("=" * 80)
    logger.info("SUGGESTED PATTERNS TO ADD")
    logger.info("=" * 80)

    logger.info("")
    logger.info("Based on manual review, these look like METRICS:")
    metrics_candidates = [
        h
        for h in unknown_col_headers[:20]
        if any(
            kw in h.lower()
            for kw in [
                "volume",
                "price",
                "cost",
                "sales",
                "ebitda",
                "revenue",
                "margin",
                "ratio",
                "debt",
                "capex",
                "opex",
                "production",
                "capacity",
                "efficiency",
                "net",
            ]
        )
    ]
    for h in metrics_candidates[:10]:
        logger.info(f"  - {h}")

    logger.info("")
    logger.info("Based on manual review, these look like ENTITIES:")
    entity_candidates = [
        h
        for h in unknown_col_headers[:20]
        if any(
            kw in h.lower()
            for kw in [
                "portugal",
                "spain",
                "brazil",
                "angola",
                "tunisia",
                "lebanon",
                "france",
                "italy",
                "cement",
                "aggregates",
                "ready",
                "mix",
                "group",
                "conso",
                "division",
            ]
        )
    ]
    for h in entity_candidates[:10]:
        logger.info(f"  - {h}")

    logger.info("")
    logger.info("Based on manual review, these look like TEMPORAL:")
    temporal_candidates = [
        h
        for h in unknown_col_headers[:20]
        if any(
            kw in h.lower()
            for kw in [
                "jan",
                "feb",
                "mar",
                "apr",
                "may",
                "jun",
                "jul",
                "aug",
                "sep",
                "oct",
                "nov",
                "dec",
                "q1",
                "q2",
                "q3",
                "q4",
                "ytd",
                "mtd",
                "budget",
                "forecast",
                "actual",
                "2023",
                "2024",
                "2025",
            ]
        )
    ]
    for h in temporal_candidates[:10]:
        logger.info(f"  - {h}")

    logger.info("")
    logger.info("=" * 80)
    logger.info("RECOMMENDATIONS")
    logger.info("=" * 80)
    logger.info("")
    logger.info("1. Add these patterns to classify_header() function:")
    logger.info("")

    # Generate pattern suggestions based on most common words
    metric_words = [
        w
        for w, c in col_words.most_common(50)
        if w
        in [
            "volume",
            "volumes",
            "price",
            "prices",
            "cost",
            "costs",
            "sales",
            "ebitda",
            "revenue",
            "margin",
            "margins",
            "ratio",
            "debt",
            "capex",
            "opex",
            "production",
            "capacity",
            "efficiency",
            "net",
            "gross",
            "operating",
            "investment",
            "cash",
            "flow",
        ]
    ]

    if metric_words:
        logger.info("   METRIC patterns to add:")
        logger.info(f"     r'\\b({'|'.join(metric_words[:20])})\\b'")

    entity_words = [
        w
        for w, c in col_words.most_common(50)
        if w
        in [
            "portugal",
            "spain",
            "brazil",
            "angola",
            "tunisia",
            "lebanon",
            "france",
            "italy",
            "cement",
            "aggregates",
            "ready",
            "mix",
            "clinker",
            "group",
            "conso",
            "division",
            "segment",
            "region",
            "country",
        ]
    ]

    if entity_words:
        logger.info("")
        logger.info("   ENTITY patterns to add:")
        logger.info(f"     r'\\b({'|'.join(entity_words[:20])})\\b'")

    logger.info("")
    logger.info("2. Consider using fuzzy matching for country/company names")
    logger.info("3. Consider LLM-assisted classification for remaining UNKNOWN headers")
    logger.info("")
    logger.info("✅ Analysis complete. Review samples above to improve classification.")


if __name__ == "__main__":
    main()
