#!/usr/bin/env python3
"""
Comprehensive table structure analyzer for adaptive extraction.

Analyzes table structures across diverse pages to understand:
1. Header row structures (multi-header vs single-header)
2. Header content classification (TEMPORAL, ENTITY, METRIC)
3. Table layout patterns (rows vs columns for each dimension)
4. Data cell patterns

Pages analyzed: 4, 10, 20, 50, 100 (diverse sample)
"""

import asyncio
import re
from enum import Enum
from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.document_converter import ConversionResult, DocumentConverter
from docling_core.types.doc import TableItem


class HeaderType(Enum):
    """Classification of header content."""

    TEMPORAL = "temporal"  # Dates, periods, quarters, years
    ENTITY = "entity"  # Companies, divisions, countries
    METRIC = "metric"  # Financial metrics, KPIs
    MIXED = "mixed"  # Contains multiple types
    UNKNOWN = "unknown"  # Cannot classify


class TableStructure:
    """Detected table structure pattern."""

    def __init__(self):
        self.header_rows: int = 0
        self.header_cols: int = 0
        self.has_row_headers: bool = False
        self.has_col_headers: bool = False
        self.col_header_types: list[HeaderType] = []
        self.row_header_types: list[HeaderType] = []
        self.layout_pattern: str = ""  # e.g., "ENTITY_COLS_METRIC_ROWS_PERIOD_HEADERS"


def classify_header_cell(text: str) -> HeaderType:
    """Classify header cell content using pattern matching.

    Args:
        text: Cell text content

    Returns:
        HeaderType classification
    """
    if not text or not text.strip():
        return HeaderType.UNKNOWN

    text_lower = text.lower().strip()

    # TEMPORAL patterns (dates, periods, quarters, years)
    temporal_patterns = [
        r"\b(20\d{2}|19\d{2})\b",  # Years: 2024, 2023
        r"\b(Q[1-4]|H[1-2])\b",  # Quarters, half-years
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-\s]?\d{2,4}\b",
        r"\bYTD\b",
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
        r"\b\d{4}-\d{2}-\d{2}\b",  # ISO dates
        r"\b\d{2}/\d{2}/\d{4}\b",  # US dates
        r"\bbudget\b",
        r"\bforecast\b",
        r"\bactual\b",
        r"\bvar\.",  # Variance (temporal comparison)
        r"% (ly|py)",  # % Last Year, % Previous Year
    ]

    # ENTITY patterns (companies, divisions, countries, departments)
    entity_patterns = [
        r"\b(portugal|angola|tunisia|lebanon|brazil|spain|france|italy)\b",
        r"\b(cement|ready-mix|aggregates|concrete)\b",
        r"\b(cimpor|secil|intercement|group)\b",
        r"\b(operations|division|segment|region)\b",
        r"\bcorporate\b",
        r"\bconsolidated\b",
        r"\btotal\b",
    ]

    # METRIC patterns (financial metrics, KPIs, costs)
    metric_patterns = [
        r"\b(ebitda|revenue|turnover|sales)\b",
        r"\b(cost|expense|opex|capex)\b",
        r"\b(margin|ratio|percentage)\b",
        r"\b(variable|fixed|total)\b",
        r"\b(production|volume|capacity)\b",
        r"\b(thermal energy|electrical energy|fuel)\b",
        r"\b(frequency|severity|accident)\b",
        r"\b(employee|headcount|fte)\b",
        r"\b(price|unit)\b",
        r"\b(depreciation|amortization)\b",
        r"\beur/ton\b",
        r"\bgj/ton\b",
        r"\bmwh\b",
    ]

    # Count matches
    temporal_count = sum(1 for p in temporal_patterns if re.search(p, text_lower))
    entity_count = sum(1 for p in entity_patterns if re.search(p, text_lower))
    metric_count = sum(1 for p in metric_patterns if re.search(p, text_lower))

    # Classify based on strongest signal
    matches = {
        HeaderType.TEMPORAL: temporal_count,
        HeaderType.ENTITY: entity_count,
        HeaderType.METRIC: metric_count,
    }

    max_count = max(matches.values())

    if max_count == 0:
        return HeaderType.UNKNOWN

    # Check for mixed (multiple types match)
    matching_types = [t for t, c in matches.items() if c == max_count]
    if len(matching_types) > 1:
        return HeaderType.MIXED

    return matching_types[0]


async def analyze_page_tables(pdf_path: Path, page_number: int) -> list[dict[str, Any]]:
    """Analyze all tables on a specific page.

    Args:
        pdf_path: Path to PDF file
        page_number: Page number to analyze (1-indexed)

    Returns:
        List of table analysis results
    """
    print(f"\n{'=' * 80}")
    print(f"ANALYZING PAGE {page_number}")
    print(f"{'=' * 80}\n")

    # Convert page
    converter = DocumentConverter(allowed_formats=[InputFormat.PDF])
    result: ConversionResult = converter.convert(pdf_path)

    if not result.document:
        print(f"❌ Conversion failed for page {page_number}")
        return []

    # Find tables on this page
    tables = []
    for element, _level in result.document.iterate_items():
        if isinstance(element, TableItem):
            # Check if table is on target page
            if hasattr(element, "prov") and element.prov:
                for prov_item in element.prov:
                    if hasattr(prov_item, "page_no") and prov_item.page_no == page_number:
                        tables.append(element)
                        break

    print(f"Found {len(tables)} tables on page {page_number}")

    analyses = []

    for table_idx, table in enumerate(tables, 1):
        print(f"\n--- Table {table_idx} ---")

        # Get table cells
        table_cells = table.data.table_cells
        num_rows = table.data.num_rows
        num_cols = table.data.num_cols

        print(f"Dimensions: {num_rows} rows × {num_cols} cols")

        # Separate headers
        column_headers = [cell for cell in table_cells if cell.column_header]
        row_headers = [cell for cell in table_cells if cell.row_header]
        data_cells = [
            cell for cell in table_cells if not cell.column_header and not cell.row_header
        ]

        print(f"Column headers: {len(column_headers)}")
        print(f"Row headers: {len(row_headers)}")
        print(f"Data cells: {len(data_cells)}")

        # Analyze column header structure
        col_header_rows = {cell.start_row_offset_idx for cell in column_headers}
        is_multi_header = len(col_header_rows) > 1

        print(f"Multi-header: {is_multi_header}")
        if col_header_rows:
            print(f"Header rows: {sorted(col_header_rows)}")

        # Classify column headers by row level
        col_header_by_row: dict[int, list] = {}
        for cell in column_headers:
            row_idx = cell.start_row_offset_idx
            if row_idx not in col_header_by_row:
                col_header_by_row[row_idx] = []
            col_header_by_row[row_idx].append(cell)

        print("\nColumn Header Classification:")
        for row_idx in sorted(col_header_by_row.keys()):
            cells = col_header_by_row[row_idx]
            classifications = {}
            for cell in cells[:10]:  # Sample first 10
                header_type = classify_header_cell(cell.text)
                classifications[header_type] = classifications.get(header_type, 0) + 1

            print(f"  Row {row_idx}: {dict(classifications)}")

            # Show samples
            for cell in cells[:5]:
                h_type = classify_header_cell(cell.text)
                print(f"    - '{cell.text}' → {h_type.value}")

        # Classify row headers
        if row_headers:
            print("\nRow Header Classification:")
            classifications = {}
            for cell in row_headers[:20]:  # Sample first 20
                header_type = classify_header_cell(cell.text)
                classifications[header_type] = classifications.get(header_type, 0) + 1

            print(f"  Counts: {dict(classifications)}")

            # Show samples
            for cell in row_headers[:5]:
                h_type = classify_header_cell(cell.text)
                print(f"    - '{cell.text}' → {h_type.value}")

        # Sample data cells
        print("\nSample Data Cells:")
        for cell in data_cells[:5]:
            print(
                f"  Row {cell.start_row_offset_idx}, Col {cell.start_col_offset_idx}: '{cell.text}'"
            )

        # Build analysis result
        analysis = {
            "page": page_number,
            "table_index": table_idx,
            "num_rows": num_rows,
            "num_cols": num_cols,
            "is_multi_header": is_multi_header,
            "header_rows": sorted(col_header_rows),
            "col_header_classifications": {},
            "row_header_classifications": {},
        }

        # Store classifications
        for row_idx in col_header_by_row.keys():
            cells = col_header_by_row[row_idx]
            classifications = {}
            for cell in cells:
                h_type = classify_header_cell(cell.text)
                classifications[h_type.value] = classifications.get(h_type.value, 0) + 1
            analysis["col_header_classifications"][row_idx] = classifications

        if row_headers:
            classifications = {}
            for cell in row_headers:
                h_type = classify_header_cell(cell.text)
                classifications[h_type.value] = classifications.get(h_type.value, 0) + 1
            analysis["row_header_classifications"] = classifications

        analyses.append(analysis)

    return analyses


async def main():
    """Analyze table structures across diverse pages."""
    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return

    # Pages to analyze (diverse sample)
    pages = [4, 10, 20, 50, 100]

    all_analyses = []

    for page_num in pages:
        analyses = await analyze_page_tables(pdf_path, page_num)
        all_analyses.extend(analyses)

    # Summary
    print(f"\n\n{'=' * 80}")
    print("SUMMARY OF ANALYSIS")
    print(f"{'=' * 80}\n")

    print(f"Total tables analyzed: {len(all_analyses)}")

    # Pattern summary
    multi_header_count = sum(1 for a in all_analyses if a["is_multi_header"])
    single_header_count = len(all_analyses) - multi_header_count

    print("\nTable Types:")
    print(f"  Multi-header: {multi_header_count}")
    print(f"  Single-header: {single_header_count}")

    # Most common patterns
    print("\nColumn Header Patterns:")
    for analysis in all_analyses:
        page = analysis["page"]
        table_idx = analysis["table_index"]
        is_multi = analysis["is_multi_header"]

        print(f"\n  Page {page}, Table {table_idx} ({'multi' if is_multi else 'single'}-header):")
        for row_idx, classifications in analysis["col_header_classifications"].items():
            dominant = (
                max(classifications.items(), key=lambda x: x[1])
                if classifications
                else ("unknown", 0)
            )
            print(f"    Row {row_idx}: {dominant[0]} ({dominant[1]} cells)")

    print("\nRow Header Patterns:")
    for analysis in all_analyses:
        if analysis["row_header_classifications"]:
            page = analysis["page"]
            table_idx = analysis["table_index"]
            classifications = analysis["row_header_classifications"]

            dominant = (
                max(classifications.items(), key=lambda x: x[1])
                if classifications
                else ("unknown", 0)
            )
            print(f"  Page {page}, Table {table_idx}: {dominant[0]} ({dominant[1]} cells)")


if __name__ == "__main__":
    asyncio.run(main())
