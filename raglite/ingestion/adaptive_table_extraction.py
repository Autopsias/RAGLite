"""
Adaptive table extraction module for diverse financial table structures.

This module provides robust, pattern-adaptive table extraction that can handle:
1. Multi-header tables (Entity-Metric-Period combinations)
2. Standard pivot tables (various layouts)
3. Mixed header types
4. Single-header tables

Strategy:
- Classify header cells as TEMPORAL, ENTITY, or METRIC using pattern matching
- Detect table layout based on header classifications
- Adaptively map cells to (entity, metric, period) tuples
- Gracefully handle ambiguous or unknown structures
"""

import logging
import re
from enum import Enum
from typing import Any

from docling.document_converter import ConversionResult
from docling_core.types.doc import TableItem

logger = logging.getLogger(__name__)


class HeaderType(Enum):
    """Classification of header content."""

    TEMPORAL = "temporal"  # Dates, periods, quarters, years
    ENTITY = "entity"  # Companies, divisions, countries
    METRIC = "metric"  # Financial metrics, KPIs
    UNKNOWN = "unknown"  # Cannot classify


class TableLayout(Enum):
    """Detected table layout pattern."""

    # Multi-header: Row 0=Metrics, Row 1=Entities, Rows=Periods
    MULTI_HEADER_METRIC_ENTITY = "multi_header_metric_entity"

    # Multi-header generic: 2+ header rows + metric rows (relaxed detection)
    MULTI_HEADER_GENERIC = "multi_header_generic"

    # Standard pivots
    TEMPORAL_COLS_METRIC_ROWS = "temporal_cols_metric_rows"  # Cols=Periods, Rows=Metrics
    ENTITY_COLS_METRIC_ROWS = "entity_cols_metric_rows"  # Cols=Entities, Rows=Metrics
    METRIC_COLS_ENTITY_ROWS = "metric_cols_entity_rows"  # Cols=Metrics, Rows=Entities

    # Phase 2.7: Transposed table - metrics as row labels (first column), entities as column headers
    TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS = "transposed_entity_cols_metric_row_labels"

    # Fallback
    UNKNOWN = "unknown"


def classify_header(text: str) -> HeaderType:
    """Classify header cell content using pattern matching.

    Uses comprehensive pattern matching for financial document headers.
    Temporal indicators take precedence (strongest signal for layout detection).

    Args:
        text: Cell text content

    Returns:
        HeaderType classification
    """
    if not text or not text.strip():
        return HeaderType.UNKNOWN

    text_lower = text.lower().strip()

    # TEMPORAL patterns (highest priority - strongest layout signal)
    temporal_patterns = [
        # Years
        r"\b(20\d{2}|19\d{2})\b",
        # Quarters, halves, periods
        r"\b(Q[1-4]|H[1-2])\b",
        # English months (with optional year suffix)
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-\s]?\d{2,4}\b",
        # Portuguese months (CRITICAL - document is in Portuguese!)
        r"\b(fev|abr|mai|ago|set|out|dez)\b",
        # Full month names
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
        # Financial periods (case-insensitive via text_lower)
        r"\bytd\b",  # Year-to-date (CRITICAL!)
        r"\bmtd\b",  # Month-to-date
        r"\bqtd\b",  # Quarter-to-date
        r"\bly\b",  # Last year (CRITICAL!)
        r"\bpy\b",  # Previous year
        # Comparison keywords
        r"\bbudget\b",
        r"\bforecast\b",
        r"\bactual\b",
        r"\breal\b",  # Portuguese for "actual"
        r"\bvar\.?\b",  # Variance
        r"\bvs\.?\b",  # Versus (CRITICAL!)
        # Percentage comparisons (CRITICAL - no space after %!)
        r"%\s*(ly|py|b)\b",  # %LY, %PY, %B
        r"%\s*real\b",  # %Real
        # Generic temporal terms
        r"\bmonth\b",
        r"\byear\b",
        r"\bperiod\b",
        r"\blast\s+\d+\s+(months|years)\b",
    ]

    # ENTITY patterns (countries, divisions, business units)
    entity_patterns = [
        # Common European countries (universal pattern)
        r"\b(portugal|spain|france|italy|germany|uk|belgium|netherlands|poland|greece)\b",
        # Common non-European countries (universal pattern)
        r"\b(usa|canada|brazil|mexico|argentina|chile)\b",
        r"\b(china|japan|india|singapore|australia)\b",
        r"\b(tunisia|morocco|egypt|algeria|lebanon|angola|kenya|nigeria)\b",
        # Industry-specific terms (keep cement/aggregates but add more universal terms)
        r"\b(cement|concrete|clinker|aggregates|ready-mix|ready\s*mix)\b",
        # Generic company/division terms (CRITICAL - universal!)
        r"\b(group|total|consolidated|conso)\b",
        r"\b(division|segment|region|regional)\b",
        r"\b(operations|corporate|holding)\b",
        r"\b(subsidiary|affiliate|joint\s*venture)\b",
        # Generic entity descriptors (universal)
        r"\b(north|south|east|west|central)\b",
        r"\b(domestic|international|overseas)\b",
        r"\b(others|other|misc|miscellaneous)\b",
    ]

    # METRIC patterns (financial/operational metrics)
    metric_patterns = [
        # Core financial metrics (universal)
        r"\b(ebitda|ebit|revenue|turnover|sales|margin)\b",
        r"\b(cost|expense|opex|capex)\b",
        r"\b(profit|loss|income|earnings)\b",
        # Cash and debt (CRITICAL - universal!)
        r"\b(cash|debt|equity)\b",
        r"\b(receivables|payables|inventory)\b",
        r"\b(assets|liabilities)\b",
        # Financial modifiers (CRITICAL - universal!)
        r"\b(net|gross|total|operating)\b",
        # Capital metrics (CRITICAL - universal!)
        r"\b(capital|invested|working|employed)\b",
        # Performance metrics (CRITICAL - universal!)
        r"\b(profitability|performance|efficiency)\b",
        r"\b(operational|financial|commercial)\b",
        r"\b(results|indicators|metrics)\b",
        # Production and operations (universal)
        r"\b(production|volume|capacity|output)\b",
        r"\b(variable|fixed)\b",
        # Pricing (universal)
        r"\b(price|unit|average)\b",
        # Energy and utilities (may vary by industry, but universal terms)
        r"\b(thermal|electrical|fuel|energy)\b",
        # HR metrics (universal)
        r"\b(employee|headcount|fte|workforce)\b",
        # Safety metrics (universal)
        r"\b(frequency|severity|accident|safety)\b",
        # Accounting (universal)
        r"\b(depreciation|amortization|provision)\b",
        # Ratios and units (universal - add more common units)
        r"\bratio\b",
        r"\beur/ton\b",
        r"\b\$/ton\b",
        r"\bgbp/ton\b",
        r"\bgj/ton\b",
        r"\bmwh\b",
        r"\bkwh\b",
        # Exchange rates (CRITICAL - universal!)
        r"\beur/[a-z]{3}\b",  # EUR/USD, EUR/BRL, EUR/AKZ, etc.
        r"\busd/[a-z]{3}\b",  # USD/EUR, etc.
        r"\bgbp/[a-z]{3}\b",  # GBP/USD, etc.
        r"\bexchange\b",
        r"\bcurrency\b",
    ]

    # Count pattern matches
    temporal_score = sum(1 for p in temporal_patterns if re.search(p, text_lower))
    entity_score = sum(1 for p in entity_patterns if re.search(p, text_lower))
    metric_score = sum(1 for p in metric_patterns if re.search(p, text_lower))

    # Classify based on strongest signal (temporal has priority)
    if temporal_score > 0:
        return HeaderType.TEMPORAL
    elif metric_score > entity_score:
        return HeaderType.METRIC
    elif entity_score > 0:
        return HeaderType.ENTITY
    else:
        return HeaderType.UNKNOWN


def detect_table_layout(
    table_cells: list, num_rows: int, num_cols: int
) -> tuple[TableLayout, dict[str, Any]]:
    """Detect table layout pattern from header classifications.

    Analyzes header cells to determine table structure and return layout metadata.

    Args:
        table_cells: List of table cells from Docling
        num_rows: Number of rows
        num_cols: Number of columns

    Returns:
        Tuple of (TableLayout, metadata_dict)
        metadata_dict contains:
            - col_header_types: {row_idx: [HeaderType, ...]}
            - row_header_types: [HeaderType, ...]
            - entity_location: 'rows' | 'cols' | 'multi_header_row1'
            - metric_location: 'rows' | 'cols' | 'multi_header_row0'
            - period_location: 'rows' | 'cols' | 'row_headers'
    """
    # Separate header types
    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]

    # Classify column headers by row level
    col_header_by_row: dict[int, list] = {}
    for cell in column_headers:
        row_idx = cell.start_row_offset_idx
        if row_idx not in col_header_by_row:
            col_header_by_row[row_idx] = []
        col_header_by_row[row_idx].append(cell)

    # Classify each row of column headers
    col_header_types: dict[int, dict[HeaderType, int]] = {}
    for row_idx, cells in col_header_by_row.items():
        type_counts = {}
        for cell in cells:
            h_type = classify_header(cell.text)
            type_counts[h_type] = type_counts.get(h_type, 0) + 1
        col_header_types[row_idx] = type_counts

    # Classify row headers
    row_header_type_counts = {}
    for cell in row_headers:
        h_type = classify_header(cell.text)
        row_header_type_counts[h_type] = row_header_type_counts.get(h_type, 0) + 1

    # Detect layout pattern
    is_multi_header = len(col_header_by_row) > 1

    metadata = {
        "col_header_types": col_header_types,
        "row_header_types": row_header_type_counts,
        "is_multi_header": is_multi_header,
    }

    # Pattern 1: Multi-header with Metric (Row 0) + Entity (Row 1) - STRICT
    if is_multi_header and len(col_header_by_row) >= 2:
        row_levels = sorted(col_header_by_row.keys())
        row0_types = col_header_types.get(row_levels[0], {})
        row1_types = col_header_types.get(row_levels[1], {})

        row0_dominant = (
            max(row0_types.items(), key=lambda x: x[1])[0] if row0_types else HeaderType.UNKNOWN
        )
        row1_dominant = (
            max(row1_types.items(), key=lambda x: x[1])[0] if row1_types else HeaderType.UNKNOWN
        )

        if row0_dominant == HeaderType.METRIC and row1_dominant == HeaderType.ENTITY:
            metadata.update(
                {
                    "entity_location": "multi_header_row1",
                    "metric_location": "multi_header_row0",
                    "period_location": "row_headers",
                }
            )
            return TableLayout.MULTI_HEADER_METRIC_ENTITY, metadata

    # Pattern 1b: Phase 2.7 - TRANSPOSED table detection (PRIORITY: Check before relaxed multi-header)
    # CRITICAL: This must run BEFORE Pattern 1c (relaxed multi-header) to prevent being overridden
    # Check if first column (col_idx=0) contains metric names (NOT marked as row_header)
    # This handles the "Cost per ton" table pattern where metrics are row labels
    first_col_cells = [
        cell for cell in table_cells if cell.start_col_offset_idx == 0 and not cell.column_header
    ]
    if first_col_cells and len(first_col_cells) >= 3:  # At least 3 data rows
        # Classify first column cells
        first_col_types = {}
        for cell in first_col_cells:
            if cell.text and cell.text.strip():
                h_type = classify_header(cell.text)
                first_col_types[h_type] = first_col_types.get(h_type, 0) + 1

        # Check if first column is predominantly metrics
        metric_count = first_col_types.get(HeaderType.METRIC, 0)
        total_count = sum(first_col_types.values())
        is_first_col_metrics = (metric_count / total_count) > 0.5 if total_count > 0 else False

        # Check if column headers are entities or temporal
        col_header_entity_count = sum(
            count
            for htype, count in col_header_types.get(0, {}).items()
            if htype == HeaderType.ENTITY
        )
        col_header_temporal_count = sum(
            count
            for htype, count in col_header_types.get(0, {}).items()
            if htype == HeaderType.TEMPORAL
        )

        # Pattern match: First column = metrics + column headers = entities/temporal
        if is_first_col_metrics and (col_header_entity_count > 0 or col_header_temporal_count > 0):
            metadata.update(
                {
                    "entity_location": "cols",  # Entities in column headers
                    "metric_location": "first_column",  # Metrics in first column (row labels)
                    "period_location": "multi_header" if is_multi_header else "cols",
                    "transposed_pattern": True,
                    "first_col_metric_ratio": metric_count / total_count if total_count > 0 else 0,
                }
            )
            return TableLayout.TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS, metadata

    # Pattern 1c: Multi-header RELAXED - Accept mixed column headers if rows are metrics
    # Key insight: Financial tables often have 2+ header rows + metric row headers
    # Don't require exact type matches - structure matters more than content types
    # MOVED AFTER transposed detection to prevent overriding transposed tables
    if is_multi_header and len(col_header_by_row) >= 2:
        # Check if row headers are predominantly metrics
        row_metric_count = row_header_type_counts.get(HeaderType.METRIC, 0)
        row_total = sum(row_header_type_counts.values())
        row_is_metrics = (row_metric_count / row_total) > 0.5 if row_total > 0 else False

        if row_is_metrics:
            # Accept as multi-header variant even with mixed column types
            metadata.update(
                {
                    "entity_location": "multi_header_mixed",  # Will try to extract from headers
                    "metric_location": "multi_header_mixed",  # Will try to extract from headers
                    "period_location": "row_headers",
                    "relaxed_detection": True,
                    "confidence": "medium",
                }
            )
            return TableLayout.MULTI_HEADER_GENERIC, metadata

    # Pattern 2: Single column header row
    if not is_multi_header and col_header_by_row:
        row0_types = col_header_types.get(0, {})
        row0_dominant = (
            max(row0_types.items(), key=lambda x: x[1])[0] if row0_types else HeaderType.UNKNOWN
        )

        row_dominant = (
            max(row_header_type_counts.items(), key=lambda x: x[1])[0]
            if row_header_type_counts
            else HeaderType.UNKNOWN
        )

        # TEMPORAL columns + METRIC rows
        if row0_dominant == HeaderType.TEMPORAL and row_dominant == HeaderType.METRIC:
            metadata.update(
                {
                    "entity_location": "unknown",  # May need inference
                    "metric_location": "rows",
                    "period_location": "cols",
                }
            )
            return TableLayout.TEMPORAL_COLS_METRIC_ROWS, metadata

        # ENTITY columns + METRIC rows
        if row0_dominant == HeaderType.ENTITY and row_dominant == HeaderType.METRIC:
            metadata.update(
                {
                    "entity_location": "cols",
                    "metric_location": "rows",
                    "period_location": "unknown",  # May need inference
                }
            )
            return TableLayout.ENTITY_COLS_METRIC_ROWS, metadata

        # METRIC columns + ENTITY rows
        if row0_dominant == HeaderType.METRIC and row_dominant == HeaderType.ENTITY:
            metadata.update(
                {
                    "entity_location": "rows",
                    "metric_location": "cols",
                    "period_location": "unknown",
                }
            )
            return TableLayout.METRIC_COLS_ENTITY_ROWS, metadata

    # Fallback: Unknown layout
    metadata.update(
        {
            "entity_location": "unknown",
            "metric_location": "unknown",
            "period_location": "unknown",
        }
    )
    return TableLayout.UNKNOWN, metadata


def extract_table_data_adaptive(
    table_item: TableItem,
    result: ConversionResult,
    table_index: int,
    document_id: str,
    page_number: int,
) -> list[dict[str, Any]]:
    """Extract table data using adaptive pattern detection.

    This is the main entry point for adaptive extraction.

    Args:
        table_item: Docling TableItem
        result: Docling ConversionResult
        table_index: Table number on page
        document_id: Document filename
        page_number: Page number

    Returns:
        List of structured row dictionaries ready for PostgreSQL insertion
    """
    table_cells = table_item.data.table_cells
    num_rows = table_item.data.num_rows
    num_cols = table_item.data.num_cols

    # Detect layout
    layout, metadata = detect_table_layout(table_cells, num_rows, num_cols)

    # Extract based on detected layout
    if layout == TableLayout.MULTI_HEADER_METRIC_ENTITY:
        rows = _extract_multi_header_metric_entity(
            table_cells,
            num_rows,
            num_cols,
            metadata,
            document_id,
            page_number,
            table_index,
            table_item,
            result,
        )
    elif layout == TableLayout.MULTI_HEADER_GENERIC:
        # Reuse multi-header extraction logic for relaxed pattern
        rows = _extract_multi_header_metric_entity(
            table_cells,
            num_rows,
            num_cols,
            metadata,
            document_id,
            page_number,
            table_index,
            table_item,
            result,
        )
    elif layout == TableLayout.TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS:
        # Phase 2.7: Transposed table extraction
        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells,
            num_rows,
            num_cols,
            metadata,
            document_id,
            page_number,
            table_index,
            table_item,
            result,
        )
    elif layout == TableLayout.TEMPORAL_COLS_METRIC_ROWS:
        rows = _extract_temporal_cols_metric_rows(
            table_cells,
            num_rows,
            num_cols,
            metadata,
            document_id,
            page_number,
            table_index,
            table_item,
            result,
        )
    elif layout == TableLayout.ENTITY_COLS_METRIC_ROWS:
        rows = _extract_entity_cols_metric_rows(
            table_cells,
            num_rows,
            num_cols,
            metadata,
            document_id,
            page_number,
            table_index,
            table_item,
            result,
        )
    else:
        # Fallback: Try to extract what we can
        rows = _extract_fallback(
            table_cells,
            num_rows,
            num_cols,
            metadata,
            document_id,
            page_number,
            table_index,
            table_item,
            result,
        )

    # Phase 2.7.5: Apply context-aware unit inference for rows with null units
    rows = _apply_context_aware_unit_inference(rows, table_item, result)

    return rows


def _extract_multi_header_metric_entity(
    table_cells: list,
    num_rows: int,
    num_cols: int,
    metadata: dict,
    document_id: str,
    page_number: int,
    table_index: int,
    table_item: TableItem,
    result: ConversionResult,
) -> list[dict[str, Any]]:
    """Extract multi-header table: Row 0=Metrics, Row 1=Entities, Row headers=Periods."""
    # This is the EXISTING working logic for page 4
    rows: list[dict[str, Any]] = []

    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]
    data_cells = [cell for cell in table_cells if not cell.column_header and not cell.row_header]

    # Build column mapping: col_idx → (metric, entity)
    headers_by_row: dict[int, list] = {}
    for cell in column_headers:
        row_idx = cell.start_row_offset_idx
        if row_idx not in headers_by_row:
            headers_by_row[row_idx] = []
        headers_by_row[row_idx].append(cell)

    row_levels = sorted(headers_by_row.keys())

    if len(row_levels) < 2:
        return rows  # Cannot extract multi-header with < 2 header rows

    metric_row = row_levels[0]
    entity_row = row_levels[1]

    # Build metric mapping (may span columns)
    metric_map: dict[int, str] = {}
    for cell in headers_by_row[metric_row]:
        start_col = cell.start_col_offset_idx
        end_col = cell.end_col_offset_idx
        metric_text = cell.text.strip() if cell.text else "Unknown"
        for col_idx in range(start_col, end_col):
            metric_map[col_idx] = metric_text

    # Build column mapping
    column_mapping: dict[int, tuple[str | None, str | None]] = {}
    for cell in headers_by_row[entity_row]:
        col_idx = cell.start_col_offset_idx
        entity = cell.text.strip() if cell.text else "Unknown"
        metric = metric_map.get(col_idx, "Unknown")
        column_mapping[col_idx] = (metric, entity)

    # Build row period mapping
    row_period_map: dict[int, str] = {}
    for cell in row_headers:
        row_idx = cell.start_row_offset_idx
        row_period_map[row_idx] = cell.text.strip() if cell.text else None

    # Extract data cells
    for cell in data_cells:
        if not cell.text or not cell.text.strip():
            continue

        row_idx = cell.start_row_offset_idx
        col_idx = cell.start_col_offset_idx

        metric, entity = column_mapping.get(col_idx, (None, None))
        period = row_period_map.get(row_idx)

        # Parse value + unit
        value, unit = _parse_value_unit(cell.text)

        fiscal_year = _extract_year(period) if period else None

        row_dict = {
            "entity": entity,
            "metric": metric,
            "period": period,
            "fiscal_year": fiscal_year,
            "value": value,
            "unit": unit,
            "page_number": page_number,
            "table_index": table_index,
            "table_caption": _get_table_caption(table_item),
            "row_index": row_idx,
            "column_name": f"{metric}_{entity}" if metric and entity else None,
            "chunk_text": _get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
        }

        rows.append(row_dict)

    return rows


def _extract_temporal_cols_metric_rows(
    table_cells: list,
    num_rows: int,
    num_cols: int,
    metadata: dict,
    document_id: str,
    page_number: int,
    table_index: int,
    table_item: TableItem,
    result: ConversionResult,
) -> list[dict[str, Any]]:
    """Extract temporal columns + metric rows layout (common in financial reports)."""
    rows: list[dict[str, Any]] = []

    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]
    data_cells = [cell for cell in table_cells if not cell.column_header and not cell.row_header]

    # Build column → period mapping
    col_period_map: dict[int, str] = {}
    for cell in column_headers:
        col_idx = cell.start_col_offset_idx
        col_period_map[col_idx] = cell.text.strip() if cell.text else None

    # Build row → metric mapping
    row_metric_map: dict[int, str] = {}
    for cell in row_headers:
        row_idx = cell.start_row_offset_idx
        row_metric_map[row_idx] = cell.text.strip() if cell.text else None

    # Extract data cells
    for cell in data_cells:
        if not cell.text or not cell.text.strip():
            continue

        row_idx = cell.start_row_offset_idx
        col_idx = cell.start_col_offset_idx

        period = col_period_map.get(col_idx)
        metric = row_metric_map.get(row_idx)
        entity = None  # Will need inference or caption extraction

        value, unit = _parse_value_unit(cell.text)
        fiscal_year = _extract_year(period) if period else None

        row_dict = {
            "entity": entity,
            "metric": metric,
            "period": period,
            "fiscal_year": fiscal_year,
            "value": value,
            "unit": unit,
            "page_number": page_number,
            "table_index": table_index,
            "table_caption": _get_table_caption(table_item),
            "row_index": row_idx,
            "column_name": f"{metric}_{period}" if metric and period else None,
            "chunk_text": _get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
        }

        rows.append(row_dict)

    return rows


def _extract_entity_cols_metric_rows(
    table_cells: list,
    num_rows: int,
    num_cols: int,
    metadata: dict,
    document_id: str,
    page_number: int,
    table_index: int,
    table_item: TableItem,
    result: ConversionResult,
) -> list[dict[str, Any]]:
    """Extract entity columns + metric rows layout.

    Pattern:
          | Portugal | Angola | Brazil |
    ------|----------|--------|--------|
    EBITDA|   1.2M   |  0.8M  |  2.1M  |
    Sales |   5.4M   |  3.2M  |  7.8M  |
    """
    rows: list[dict[str, Any]] = []

    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]
    data_cells = [cell for cell in table_cells if not cell.column_header and not cell.row_header]

    # Build column → entity mapping
    col_entity_map: dict[int, str] = {}
    for cell in column_headers:
        col_idx = cell.start_col_offset_idx
        col_entity_map[col_idx] = cell.text.strip() if cell.text else None

    # Build row → metric mapping
    row_metric_map: dict[int, str] = {}
    for cell in row_headers:
        row_idx = cell.start_row_offset_idx
        row_metric_map[row_idx] = cell.text.strip() if cell.text else None

    # Try to infer period from table caption
    caption = _get_table_caption(table_item)
    period = None
    fiscal_year = None
    if caption:
        # Extract year if present
        fiscal_year = _extract_year(caption)
        # Use caption as period if it contains temporal info
        if fiscal_year or any(
            keyword in caption.lower()
            for keyword in ["ytd", "q1", "q2", "q3", "q4", "budget", "forecast"]
        ):
            period = caption

    # Extract data cells
    for cell in data_cells:
        if not cell.text or not cell.text.strip():
            continue

        row_idx = cell.start_row_offset_idx
        col_idx = cell.start_col_offset_idx

        entity = col_entity_map.get(col_idx)
        metric = row_metric_map.get(row_idx)

        value, unit = _parse_value_unit(cell.text)

        row_dict = {
            "entity": entity,
            "metric": metric,
            "period": period,  # May be NULL - acceptable for Entity-Metric tables
            "fiscal_year": fiscal_year,
            "value": value,
            "unit": unit,
            "page_number": page_number,
            "table_index": table_index,
            "table_caption": caption,
            "row_index": row_idx,
            "column_name": f"{metric}_{entity}" if metric and entity else None,
            "chunk_text": _get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
        }

        rows.append(row_dict)

    return rows


def _extract_transposed_entity_cols_metric_row_labels(
    table_cells: list,
    num_rows: int,
    num_cols: int,
    metadata: dict,
    document_id: str,
    page_number: int,
    table_index: int,
    table_item: TableItem,
    result: ConversionResult,
) -> list[dict[str, Any]]:
    """Extract transposed table: Entities in column headers, metrics in first column (row labels).

    Pattern (pages 20-21 "Cost per ton" tables):
                            Portugal        Tunisia         Lebanon         Brazil
                        Aug-25  Budget  Aug-25  Budget  Aug-25  Budget  Aug-25  Budget
    Variable Cost       -23.4   -20.4   -29.1   -27.3   -50.9   -44.4   -20.7   -22.0
    Thermal Energy      -5.9    -5.9    -11.1   -10.5   -9.7    -12.3   -8.8    -9.1

    Strategy:
    1. Extract entities from Row 0 column headers (Portugal, Tunisia, etc.)
    2. Extract periods from Row 1 sub-headers if present (Aug-25, Budget, Aug-24)
    3. Extract metrics from first column cells (col_idx=0)
    4. Map data cells to (entity, metric, period) tuples

    Args:
        table_cells: List of table cells
        num_rows: Number of rows
        num_cols: Number of columns
        metadata: Layout metadata from detect_table_layout
        document_id: Document filename
        page_number: Page number
        table_index: Table index on page
        table_item: Docling TableItem
        result: Docling ConversionResult

    Returns:
        List of structured row dicts ready for SQL insertion
    """
    rows: list[dict[str, Any]] = []

    column_headers = [cell for cell in table_cells if cell.column_header]
    first_col_cells = [
        cell for cell in table_cells if cell.start_col_offset_idx == 0 and not cell.column_header
    ]
    data_cells = [
        cell
        for cell in table_cells
        if not cell.column_header and cell.start_col_offset_idx > 0  # Exclude first column
    ]

    # Build column header mapping by row level
    headers_by_row: dict[int, list] = {}
    for cell in column_headers:
        row_idx = cell.start_row_offset_idx
        if row_idx not in headers_by_row:
            headers_by_row[row_idx] = []
        headers_by_row[row_idx].append(cell)

    row_levels = sorted(headers_by_row.keys())

    # Build column → (entity, period) mapping
    column_mapping: dict[int, tuple[str | None, str | None]] = {}
    # Build column → unit mapping (for 3+ header row tables)
    column_unit_map: dict[int, str | None] = {}

    if len(row_levels) >= 2:
        # Multi-header: Row 0 = Entities, Row 1 = Periods
        entity_row = row_levels[0]
        period_row = row_levels[1]

        # Build entity mapping (may span columns)
        entity_map: dict[int, str] = {}
        for cell in headers_by_row[entity_row]:
            start_col = cell.start_col_offset_idx
            end_col = cell.end_col_offset_idx
            entity_text = cell.text.strip() if cell.text else "Unknown"
            for col_idx in range(start_col, end_col):
                entity_map[col_idx] = entity_text

        # Build final mapping with periods
        for cell in headers_by_row[period_row]:
            col_idx = cell.start_col_offset_idx
            period = cell.text.strip() if cell.text else None
            entity = entity_map.get(col_idx, "Unknown")
            column_mapping[col_idx] = (entity, period)

        # Check for 3rd header row containing units
        if len(row_levels) >= 3:
            unit_row = row_levels[2]
            # Check if this row contains unit patterns
            unit_patterns = [
                "EUR",
                "ton",
                "Meur",
                "kt",
                "%",
                "GJ",
                "€",
                "$",
                "USD",
                "kWh",
                "m3",
                "MW",
            ]
            row_cells = headers_by_row[unit_row]

            # DEBUG
            print(f"[DEBUG] Table on page {page_number}, table_index={table_index}")
            print(f"[DEBUG] len(row_levels)={len(row_levels)}, checking for units in row_levels[2]")
            print(f"[DEBUG] Number of cells in unit row: {len(row_cells)}")

            # Sample a few cells to check if they look like units
            sample_cells = row_cells[: min(3, len(row_cells))]
            print("[DEBUG] Sample cells (first 3):")
            for i, cell in enumerate(sample_cells):
                print(
                    f"[DEBUG]   Cell {i}: text='{cell.text}' (column {cell.start_col_offset_idx})"
                )

            looks_like_units = any(
                cell.text and any(pattern in cell.text for pattern in unit_patterns)
                for cell in sample_cells
                if cell.text
            )

            print(f"[DEBUG] looks_like_units={looks_like_units}")

            if looks_like_units:
                # This is a unit header row - extract units
                print(f"[DEBUG] Extracting units from {len(row_cells)} cells")
                for cell in row_cells:
                    col_idx = cell.start_col_offset_idx
                    unit_text = cell.text.strip() if cell.text else None
                    if unit_text:
                        column_unit_map[col_idx] = unit_text
                        print(f"[DEBUG]   column_unit_map[{col_idx}] = '{unit_text}'")
                print(f"[DEBUG] Total units extracted: {len(column_unit_map)}")
            else:
                print("[DEBUG] Unit patterns NOT detected in sample cells")

    elif len(row_levels) == 1:
        # Single header row - assume entities (no periods)
        for cell in headers_by_row[row_levels[0]]:
            col_idx = cell.start_col_offset_idx
            entity = cell.text.strip() if cell.text else None
            column_mapping[col_idx] = (entity, None)

    # Build row → metric mapping from first column
    row_metric_map: dict[int, str] = {}
    for cell in first_col_cells:
        row_idx = cell.start_row_offset_idx
        # Parse metric name and unit from cell text
        metric_text = cell.text.strip() if cell.text else None
        if metric_text:
            row_metric_map[row_idx] = metric_text

    # PHASE 2.7.4: ADAPTIVE ORIENTATION-AWARE UNIT DETECTION
    # Research-validated approach: Detect orientation FIRST, then apply appropriate extraction strategy
    # Industry standard: TableRAG, FinRAG, Bloomberg all use this pattern

    unit_patterns = [
        "EUR",
        "ton",
        "Meur",
        "kt",
        "%",
        "GJ",
        "€",
        "$",
        "USD",
        "kWh",
        "m3",
        "MW",
        "kton",
        "m²",
        "m³",
        "kg",
        "g",
        "t",
        "l",
        "ml",
        "h",
        "min",
        "s",
        "kW",
        "GW",
        "MWh",
        "GWh",
        "million",
        "billion",
        "thousand",
        "M€",
        "k€",
        "bn",
        "mn",
        "ratio",
        "rate",
        "pts",
        "bps",
        "basis points",
        "percentage",
        "pct",
        "people",
        "FTE",
        "headcount",
        "units",
    ]

    # Step 1: Detect table orientation
    orientation, orientation_confidence = _detect_table_orientation(
        table_cells, num_rows, num_cols, unit_patterns
    )

    # Step 2: Apply orientation-specific unit extraction strategy (V2 - 4-type taxonomy)
    row_unit_map: dict[int, str] = {}
    col_unit_map_normal: dict[int, str] = {}  # For normal/Type B tables (column-based units)

    if orientation == "transposed_metric":
        # TYPE A: Transposed Metric-Entity (metrics in col 0, units in col 1)
        # Example: Row 0: Sales Volumes | kton | 1.381 | 1.378
        col_1_cells = [
            cell
            for cell in table_cells
            if cell.start_col_offset_idx == 1 and not cell.column_header
        ]

        col_1_has_units, unit_detection_confidence = _detect_unit_column_statistical(
            col_1_cells, unit_patterns, threshold=0.60, min_samples=3
        )

        logger.info(
            f"Type A (transposed_metric) unit detection: {len(row_unit_map)} units found",
            extra={
                "page_number": page_number,
                "table_index": table_index,
                "confidence": round(orientation_confidence, 3),
                "col_1_cells": len(col_1_cells),
                "has_units": col_1_has_units,
                "unit_confidence": round(unit_detection_confidence, 3),
            },
        )

        if col_1_has_units:
            # Extract units from column 1
            for cell in col_1_cells:
                row_idx = cell.start_row_offset_idx
                unit_text = cell.text.strip() if cell.text else None
                if unit_text:
                    row_unit_map[row_idx] = unit_text

            # Update data_cells to exclude column 1 (since it contains units, not data)
            data_cells = [
                cell
                for cell in table_cells
                if not cell.column_header and cell.start_col_offset_idx > 1
            ]

    elif orientation == "entity_column_junk":
        # TYPE B: Entity-Column with Junk Column 0
        # Example: Col 0: 14.003 | Col 1: Portugal | Col 2+: Data
        col_unit_map_normal = _extract_units_entity_column_junk(table_cells, unit_patterns)

        logger.info(
            f"Type B (entity_column_junk) unit detection: {len(col_unit_map_normal)} units found",
            extra={
                "page_number": page_number,
                "table_index": table_index,
                "confidence": round(orientation_confidence, 3),
                "units_found": len(col_unit_map_normal),
            },
        )

        # For Type B, skip column 0 (junk) and start from column 1
        data_cells = [
            cell
            for cell in table_cells
            if not cell.column_header and cell.start_col_offset_idx >= 1
        ]

    elif orientation == "normal_metric":
        # TYPE C: Normal Metric-Entity (metrics in col 0, data in col 1+)
        # Example: Col 0: EBITDA IFRS | Col 1+: 128.825, 91.438, etc.
        col_unit_map_normal = _extract_units_normal(table_cells, unit_patterns)

        logger.info(
            f"Type C (normal_metric) unit detection: {len(col_unit_map_normal)} units found",
            extra={
                "page_number": page_number,
                "table_index": table_index,
                "confidence": round(orientation_confidence, 3),
                "units_found": len(col_unit_map_normal),
            },
        )

    else:
        # UNKNOWN ORIENTATION: Fall back to transposed strategy (legacy behavior)
        logger.warning(
            f"Unknown orientation (confidence={orientation_confidence:.3f}) - using fallback",
            extra={"page_number": page_number, "table_index": table_index},
        )

        col_1_cells = [
            cell
            for cell in table_cells
            if cell.start_col_offset_idx == 1 and not cell.column_header
        ]

        col_1_has_units, unit_detection_confidence = _detect_unit_column_statistical(
            col_1_cells, unit_patterns, threshold=0.60, min_samples=3
        )

        if col_1_has_units:
            for cell in col_1_cells:
                row_idx = cell.start_row_offset_idx
                unit_text = cell.text.strip() if cell.text else None
                if unit_text:
                    row_unit_map[row_idx] = unit_text

            data_cells = [
                cell
                for cell in table_cells
                if not cell.column_header and cell.start_col_offset_idx > 1
            ]

    # Extract data cells
    caption = _get_table_caption(table_item)

    for cell in data_cells:
        if not cell.text or not cell.text.strip():
            continue

        row_idx = cell.start_row_offset_idx
        col_idx = cell.start_col_offset_idx

        # Get entity and period from column mapping
        entity, period = column_mapping.get(col_idx, (None, None))

        # Get metric from first column
        metric = row_metric_map.get(row_idx)

        # Get unit - priority order (PHASE 2.7.4 - Orientation-aware):
        # 1. From row-based unit map (column 1 - transposed tables)
        # 2. From column-based unit map (3rd header row - transposed tables)
        # 3. From normal table column units (dedicated unit row or metric names)
        # 4. Parse from data cell (fallback)
        if row_unit_map and row_idx in row_unit_map:
            # Transposed table: unit from column 1 (same row)
            unit = row_unit_map.get(row_idx)
            # Parse only value from data cell
            value, _ = _parse_value_unit(cell.text)
        elif column_unit_map and col_idx in column_unit_map:
            # Transposed table: unit from column header (3rd row)
            unit = column_unit_map.get(col_idx)
            # Parse only value from data cell
            value, _ = _parse_value_unit(cell.text)
        elif col_unit_map_normal and col_idx in col_unit_map_normal:
            # Normal table: unit from dedicated unit row or column headers
            unit = col_unit_map_normal.get(col_idx)
            # Parse only value from data cell
            value, _ = _parse_value_unit(cell.text)
        else:
            # Fallback: parse value + unit from data cell
            value, unit = _parse_value_unit(cell.text)

        # Extract fiscal year
        fiscal_year = _extract_year(period) if period else None

        row_dict = {
            "entity": entity,
            "metric": metric,
            "period": period,
            "fiscal_year": fiscal_year,
            "value": value,
            "unit": unit,
            "page_number": page_number,
            "table_index": table_index,
            "table_caption": caption,
            "row_index": row_idx,
            "column_name": f"{metric}_{entity}_{period}"
            if metric and entity and period
            else f"{metric}_{entity}"
            if metric and entity
            else None,
            "chunk_text": _get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
            "extraction_method": "transposed_entity_cols_metric_row_labels",
        }

        rows.append(row_dict)

    return rows


def _infer_metric_from_context(page_context: dict) -> str | None:
    """Infer metric from page/section context when not present in headers.

    Production-validated approach: Extract from section headings and nearby text.
    Used as fallback when orientation detection produces NULL metric.

    Args:
        page_context: Dict from _extract_page_context() with section_heading, nearby_text

    Returns:
        Inferred metric name or None
    """
    # Combine all available context
    context_text = []
    if page_context.get("section_heading"):
        context_text.append(page_context["section_heading"])
    if page_context.get("nearby_text"):
        context_text.extend(page_context["nearby_text"])
    if page_context.get("page_title"):
        context_text.append(page_context["page_title"])

    if not context_text:
        return None

    combined_text = " ".join(context_text).lower()

    # Common financial metrics (universal patterns)
    metric_keywords = {
        "revenue": "Revenue",
        "sales": "Sales",
        "turnover": "Turnover",
        "ebitda": "EBITDA",
        "ebit": "EBIT",
        "profit": "Profit",
        "margin": "Margin",
        "cost": "Cost",
        "expense": "Expense",
        "capex": "CAPEX",
        "opex": "OPEX",
        "cash": "Cash",
        "debt": "Debt",
        "equity": "Equity",
        "volume": "Volume",
        "production": "Production",
        "capacity": "Capacity",
        "price": "Price",
        "exchange": "Exchange Rate",
        "rate": "Rate",
        "ratio": "Ratio",
        "investment": "Investment",
        "balance": "Balance",
        "asset": "Assets",
        "liability": "Liabilities",
        "inventory": "Inventory",
        "receivable": "Receivables",
        "payable": "Payables",
        "indicator": "Indicator",
        "frequency": "Frequency",
        "severity": "Severity",
    }

    # Check for exact keyword matches in combined context
    for keyword, metric_name in metric_keywords.items():
        if keyword in combined_text:
            return metric_name

    # Fallback: use first meaningful text from section heading
    if page_context.get("section_heading"):
        words = [w for w in page_context["section_heading"].split() if len(w) > 2][:3]
        if words:
            return " ".join(words)

    return None


def _infer_entity_from_context(page_context: dict) -> str | None:
    """Infer entity from page/section context when not present in headers.

    Production-validated approach: Extract from section headings and nearby text.
    Used as fallback when orientation detection produces NULL entity.

    Args:
        page_context: Dict from _extract_page_context() with section_heading, nearby_text

    Returns:
        Inferred entity name or None
    """
    import re

    # Combine all available context
    context_text = []
    if page_context.get("section_heading"):
        context_text.append(page_context["section_heading"])
    if page_context.get("nearby_text"):
        context_text.extend(page_context["nearby_text"])
    if page_context.get("page_title"):
        context_text.append(page_context["page_title"])

    if not context_text:
        return None

    combined_text = " ".join(context_text).lower()

    # Common entity patterns (universal)
    entity_patterns = [
        # Geographic entities
        (
            r"\b(portugal|spain|france|italy|germany|uk|brazil|usa|canada|china|india|japan|angola|tunisia|lebanon)\b",
            "country",
        ),
        (r"\b(europe|asia|americas|africa|oceania)\b", "region"),
        (r"\b(north|south|east|west|central)\b", "direction"),
        # Corporate entities
        (r"\b(group|consolidated|conso|total|corporate)\b", "group"),
        (r"\b(division|segment|unit|department)\b", "division"),
        (r"\b(subsidiary|affiliate|joint\s*venture)\b", "subsidiary"),
        # Industry-specific (cement example, but add more universal)
        (r"\b(cement|concrete|aggregates|ready-mix|clinker)\b", "product"),
        # Multi-entity indicators
        (r"\bby\s+(country|region|entity|division|segment)\b", "multi-entity"),
    ]

    for pattern, _entity_type in entity_patterns:
        match = re.search(pattern, combined_text)
        if match:
            # Return the matched text capitalized
            return match.group(1).capitalize()

    # Check if context contains "by [something]" pattern
    by_match = re.search(r"\bby\s+([a-z]+)", combined_text)
    if by_match:
        return by_match.group(1).capitalize()

    # Fallback: if section heading mentions a specific entity term, use it
    if page_context.get("section_heading"):
        # Simple heuristic: if section heading is short (< 5 words), use it as entity
        heading_words = page_context["section_heading"].split()
        if 1 <= len(heading_words) <= 4:
            return page_context["section_heading"]

    return None


def _detect_orientation(column_headers: list, row_headers: list) -> tuple[str, dict]:
    """Detect table orientation from header classifications.

    Returns:
        (pattern, metadata) where pattern is one of:
        - 'temporal_rows_entity_cols': Dates in rows, entities in columns
        - 'metric_rows_temporal_cols': Metrics in rows, periods in columns
        - 'metric_rows_entity_cols': Metrics in rows, entities in columns
        - 'entity_rows_metric_cols': Entities in rows, metrics in columns
        - 'unknown': Cannot determine pattern
    """
    from collections import Counter

    # Classify all headers
    col_types = Counter()
    for cell in column_headers:
        if cell.text:
            h_type = classify_header(cell.text)
            col_types[h_type] += 1

    row_types = Counter()
    for cell in row_headers:
        if cell.text:
            h_type = classify_header(cell.text)
            row_types[h_type] += 1

    # Get dominant types (exclude UNKNOWN)
    dominant_row = None
    dominant_col = None

    for htype, _count in row_types.most_common():
        if htype != HeaderType.UNKNOWN:
            dominant_row = htype
            break

    for htype, _count in col_types.most_common():
        if htype != HeaderType.UNKNOWN:
            dominant_col = htype
            break

    # Determine pattern based on dominant types
    pattern = "unknown"
    metadata = {
        "dominant_row": dominant_row.value if dominant_row else "unknown",
        "dominant_col": dominant_col.value if dominant_col else "unknown",
        "row_type_counts": dict(row_types),
        "col_type_counts": dict(col_types),
    }

    # Pattern matching
    if dominant_row == HeaderType.TEMPORAL and dominant_col == HeaderType.ENTITY:
        pattern = "temporal_rows_entity_cols"
    elif dominant_row == HeaderType.METRIC and dominant_col == HeaderType.TEMPORAL:
        pattern = "metric_rows_temporal_cols"
    elif dominant_row == HeaderType.METRIC and dominant_col == HeaderType.ENTITY:
        pattern = "metric_rows_entity_cols"
    elif dominant_row == HeaderType.ENTITY and dominant_col == HeaderType.METRIC:
        pattern = "entity_rows_metric_cols"
    elif dominant_row == HeaderType.TEMPORAL and dominant_col == HeaderType.TEMPORAL:
        # Both temporal - use row as period (more common)
        pattern = "temporal_rows_temporal_cols"
    elif dominant_row == HeaderType.ENTITY and dominant_col == HeaderType.TEMPORAL:
        pattern = "entity_rows_temporal_cols"

    metadata["detected_pattern"] = pattern
    return pattern, metadata


def _extract_fallback(
    table_cells: list,
    num_rows: int,
    num_cols: int,
    metadata: dict,
    document_id: str,
    page_number: int,
    table_index: int,
    table_item: TableItem,
    result: ConversionResult,
) -> list[dict[str, Any]]:
    """Orientation-aware extraction with section context inference.

    Strategy (PHASE 2.6 - SECTION CONTEXT EXTRACTION):
    1. Extract page/section context (headings, nearby text) using spatial proximity
    2. Detect table orientation from classified headers
    3. Apply pattern-specific field assignment
    4. Use section context for missing entity/metric fields
    5. Mark confidence based on source (high=headers, medium=context, low=unknown)

    Production-validated approach from Unstructured.io, LLMSherpa research.
    Reduces NULL rates by inferring from document structure when table captions absent.
    """
    rows: list[dict[str, Any]] = []

    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]
    data_cells = [cell for cell in table_cells if not cell.column_header and not cell.row_header]

    # If no headers at all, skip (can't extract anything meaningful)
    if not column_headers and not row_headers:
        return []

    # PHASE 2: Detect table orientation FIRST
    orientation, orientation_meta = _detect_orientation(column_headers, row_headers)

    # Build header mappings
    col_header_map: dict[int, str] = {}
    for cell in column_headers:
        for col_idx in range(cell.start_col_offset_idx, cell.end_col_offset_idx):
            if col_idx not in col_header_map:  # First header wins if multiple rows
                col_header_map[col_idx] = cell.text.strip() if cell.text else None

    row_header_map: dict[int, str] = {}
    for cell in row_headers:
        row_idx = cell.start_row_offset_idx
        if row_idx not in row_header_map:
            row_header_map[row_idx] = cell.text.strip() if cell.text else None

    # PHASE 2.6: Extract page/section context for fallback inference
    page_context = _extract_page_context(table_item, result)

    # Try to infer period from table caption (legacy, rarely works)
    caption = _get_table_caption(table_item)
    caption_period = None
    caption_year = None
    if caption:
        caption_year = _extract_year(caption)
        if caption_year or any(
            kw in caption.lower() for kw in ["ytd", "q1", "q2", "q3", "q4", "budget", "forecast"]
        ):
            caption_period = caption

    # Also try to extract period from section heading
    if not caption_period and page_context.get("section_heading"):
        section_heading = page_context["section_heading"]
        section_year = _extract_year(section_heading)
        if section_year or any(
            kw in section_heading.lower()
            for kw in ["ytd", "q1", "q2", "q3", "q4", "budget", "forecast"]
        ):
            caption_period = section_heading
            caption_year = section_year

    # Extract data cells using ORIENTATION-AWARE field assignment
    for cell in data_cells:
        if not cell.text or not cell.text.strip():
            continue

        row_idx = cell.start_row_offset_idx
        col_idx = cell.start_col_offset_idx

        col_header = col_header_map.get(col_idx)
        row_header = row_header_map.get(row_idx)

        # PHASE 2: Apply orientation-specific field assignment
        entity = None
        metric = None
        period = None
        fiscal_year = None
        confidence = "medium"

        if orientation == "temporal_rows_entity_cols":
            # Dates in rows, entities in columns
            period = row_header
            entity = col_header
            metric = None  # May be inferred from caption
            fiscal_year = _extract_year(row_header) if row_header else None
            confidence = "high"

        elif orientation == "metric_rows_temporal_cols":
            # Metrics in rows, periods in columns
            metric = row_header
            period = col_header
            entity = None  # May be inferred from caption
            fiscal_year = _extract_year(col_header) if col_header else None
            confidence = "high"

        elif orientation == "metric_rows_entity_cols":
            # Metrics in rows, entities in columns
            metric = row_header
            entity = col_header
            period = caption_period  # From caption
            fiscal_year = caption_year
            confidence = "high"

        elif orientation == "entity_rows_metric_cols":
            # Entities in rows, metrics in columns
            entity = row_header
            metric = col_header
            period = caption_period  # From caption
            fiscal_year = caption_year
            confidence = "high"

        elif orientation == "entity_rows_temporal_cols":
            # Entities in rows, periods in columns
            entity = row_header
            period = col_header
            metric = None  # May be inferred from caption
            fiscal_year = _extract_year(col_header) if col_header else None
            confidence = "high"

        elif orientation == "temporal_rows_temporal_cols":
            # Both temporal - row as period, column as comparison
            period = row_header
            # Column might be "YTD", "LY", etc. - treat as part of period
            if col_header:
                period = f"{row_header} {col_header}" if row_header else col_header
            metric = None
            entity = None
            fiscal_year = _extract_year(row_header) if row_header else None
            confidence = "medium"

        else:
            # Unknown orientation - fallback to classification-based assignment
            col_type = classify_header(col_header) if col_header else HeaderType.UNKNOWN
            row_type = classify_header(row_header) if row_header else HeaderType.UNKNOWN

            if col_type == HeaderType.ENTITY:
                entity = col_header
            elif col_type == HeaderType.METRIC:
                metric = col_header
            elif col_type == HeaderType.TEMPORAL:
                period = col_header
                fiscal_year = _extract_year(col_header) if col_header else None

            if row_type == HeaderType.ENTITY and not entity:
                entity = row_header
            elif row_type == HeaderType.METRIC and not metric:
                metric = row_header
            elif row_type == HeaderType.TEMPORAL and not period:
                period = row_header
                fiscal_year = _extract_year(row_header) if row_header else None

            # Last resort: use caption
            if not period and caption_period:
                period = caption_period
                fiscal_year = caption_year

            confidence = "low"

        # PHASE 2.6: Section context-based inference for NULL fields
        # If orientation detection produced NULL entity/metric (correctly!),
        # try to infer from page/section context to enable SQL queries
        # Production-validated approach from Unstructured.io, LLMSherpa research
        inferred_from_context = False

        if not metric and page_context:
            inferred_metric = _infer_metric_from_context(page_context)
            if inferred_metric:
                metric = inferred_metric
                inferred_from_context = True

        if not entity and page_context:
            inferred_entity = _infer_entity_from_context(page_context)
            if inferred_entity:
                entity = inferred_entity
                inferred_from_context = True

        # Lower confidence if we had to infer from context (medium confidence)
        if inferred_from_context and confidence == "high":
            confidence = "medium"

        # Parse value
        value, unit = _parse_value_unit(cell.text)

        # Track extraction method (Phase 2.6 adds section context inference)
        extraction_method = f"orientation_aware_{orientation}"
        if inferred_from_context:
            extraction_method = f"{extraction_method}_context_inferred"

        row_dict = {
            "entity": entity,
            "metric": metric,
            "period": period,
            "fiscal_year": fiscal_year,
            "value": value,
            "unit": unit,
            "page_number": page_number,
            "table_index": table_index,
            "table_caption": caption,
            "row_index": row_idx,
            "column_name": f"{metric}_{period}"
            if metric and period
            else f"{metric}_{entity}"
            if metric and entity
            else None,
            "chunk_text": _get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
            "extraction_method": extraction_method,  # PHASE 2.5: Track orientation + caption inference
            "confidence": confidence,  # High for header-based, medium for caption-inferred, low for unknown
        }

        rows.append(row_dict)

    return rows


# Helper functions


def _is_numeric_value(text: str) -> bool:
    """Check if text contains a numeric value.

    Args:
        text: Text to analyze

    Returns:
        True if text appears to be a numeric value
    """
    if not text or not text.strip():
        return False

    # Remove common formatting characters
    clean_text = (
        text.strip()
        .replace(",", "")
        .replace(" ", "")
        .replace("€", "")
        .replace("$", "")
        .replace("%", "")
    )

    # Check if remaining text is numeric
    try:
        float(clean_text)
        return True
    except ValueError:
        # Check for patterns like "123.45" or "(123.45)" or "-123.45"
        import re

        numeric_pattern = r"^[\(\-]?\d+[\.,]?\d*[\)]?$"
        return bool(re.match(numeric_pattern, clean_text))


def _analyze_column(
    table_cells: list,
    col_idx: int,
    metric_patterns: list[str],
    entity_patterns: list[str],
    unit_patterns: list[str],
) -> dict:
    """Analyze single column content with multiple pattern types.

    Industry best practice (ENTRANT, TableRAG): Multi-dimensional analysis
    before classification.

    Args:
        table_cells: List of table cells
        col_idx: Column index to analyze
        metric_patterns: List of metric pattern strings
        entity_patterns: List of entity pattern strings
        unit_patterns: List of unit pattern strings

    Returns:
        Dictionary with pattern counts and ratios
    """
    col_cells = [
        c for c in table_cells if c.start_col_offset_idx == col_idx and not c.column_header
    ]

    if not col_cells:
        return {
            "metric_count": 0,
            "entity_count": 0,
            "unit_count": 0,
            "numeric_count": 0,
            "total": 0,
            "metric_ratio": 0.0,
            "entity_ratio": 0.0,
            "unit_ratio": 0.0,
            "numeric_ratio": 0.0,
        }

    metric_count = 0
    entity_count = 0
    unit_count = 0
    numeric_count = 0

    for cell in col_cells:
        if not cell.text:
            continue

        cell_text_upper = cell.text.upper()
        cell_text_lower = cell.text.lower()

        # Check metric patterns
        if any(p.upper() in cell_text_upper for p in metric_patterns):
            metric_count += 1
        # Check entity patterns
        elif any(p.upper() in cell_text_upper for p in entity_patterns):
            entity_count += 1
        # Check unit patterns
        elif any(p.lower() in cell_text_lower for p in unit_patterns):
            unit_count += 1
        # Check if numeric
        elif _is_numeric_value(cell.text):
            numeric_count += 1

    total = len(col_cells)

    return {
        "metric_count": metric_count,
        "entity_count": entity_count,
        "unit_count": unit_count,
        "numeric_count": numeric_count,
        "total": total,
        "metric_ratio": metric_count / total if total > 0 else 0,
        "entity_ratio": entity_count / total if total > 0 else 0,
        "unit_ratio": unit_count / total if total > 0 else 0,
        "numeric_ratio": numeric_count / total if total > 0 else 0,
    }


def _detect_table_orientation(
    table_cells: list, num_rows: int, num_cols: int, unit_patterns: list[str]
) -> tuple[str, float]:
    """Enhanced V2: Multi-column adaptive detection with 4-type taxonomy.

    Research-validated approach (ENTRANT, TableRAG, IEEE 2024):
    1. Multi-column content analysis (columns 0, 1, 2)
    2. Aspect ratio heuristics
    3. Header pattern analysis
    4. Type-specific classification with confidence scoring

    Table Types Detected:
    - 'transposed_metric': Metrics in col 0, units in col 1, entities in headers
    - 'entity_column_junk': Junk/indices in col 0, entities in col 1
    - 'normal_metric': Metrics in col 0, data in col 1+
    - 'unknown': Ambiguous structure

    Args:
        table_cells: List of table cells
        num_rows: Number of rows in table
        num_cols: Number of columns in table
        unit_patterns: List of unit pattern strings

    Returns:
        Tuple of (orientation, confidence)
    """
    # Expanded patterns based on research (ENTRANT dataset, financial docs)
    metric_patterns = [
        # Core financial metrics
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
        # Operational metrics
        "Volume",
        "Production",
        "Capacity",
        "Utilization",
        "Efficiency",
        "Productivity",
        # Investment metrics
        "CAPEX",
        "OPEX",
        "Investment",
        "Expenditure",
        "Spending",
        # Market metrics
        "Price",
        "Rate",
        "Ratio",
        "Yield",
        "Return",
        # Performance metrics
        "ROE",
        "ROA",
        "ROI",
        "ROCE",
        "EPS",
        "P/E",
        "Dividend",
        "FCF",
        # Tax & accounting
        "Tax",
        "Depreciation",
        "Amortization",
        "Impairment",
        # Working capital
        "Receivable",
        "Payable",
        "Inventory",
        "Working Capital",
        # Additional patterns
        "Interest",
        "Net",
        "Gross",
        "Operating",
        "COGS",
        "SG&A",
    ]

    entity_patterns = [
        "GROUP",
        "PORTUGAL",
        "ANGOLA",
        "TUNISIA",
        "LEBANON",
        "BRAZIL",
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
        "Cement",
        "Madeira",
        "Cape Verde",
        "Nederland",
        "Secil",
    ]

    # Calculate aspect ratio
    aspect_ratio = num_rows / num_cols if num_cols > 0 else 1.0

    # Multi-column analysis (industry best practice)
    col_0 = _analyze_column(table_cells, 0, metric_patterns, entity_patterns, unit_patterns)
    col_1 = _analyze_column(table_cells, 1, metric_patterns, entity_patterns, unit_patterns)
    # Header analysis
    col_headers = [c for c in table_cells if c.column_header]
    temporal_patterns = [
        "YTD",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "2024",
        "2025",
        "2023",
        "2022",
        "2021",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
        "Year",
        "Period",
        "Month",
        "Quarter",
        "Budget",
        "B ",
        "Aug-",
    ]

    entity_header_count = sum(
        1
        for h in col_headers
        if h.text and any(p.upper() in h.text.upper() for p in entity_patterns)
    )
    temporal_header_count = sum(
        1 for h in col_headers if h.text and any(p in h.text for p in temporal_patterns)
    )

    # ENHANCED DECISION TREE (4-type taxonomy)

    # TYPE A: Transposed Metric-Entity (metrics in col 0, units in col 1)
    if col_0["metric_ratio"] > 0.4 and col_1["unit_ratio"] > 0.5:  # LOWERED threshold from 0.5
        orientation = "transposed_metric"
        confidence = min(col_0["metric_ratio"] + col_1["unit_ratio"], 0.95)

    # TYPE B: Entity-Column with Junk Column 0 (numeric junk in col 0, entities in col 1)
    elif col_0["numeric_ratio"] > 0.7 and col_1["entity_ratio"] > 0.5 and aspect_ratio > 1.5:
        orientation = "entity_column_junk"
        confidence = 0.90

    # TYPE C: Normal Metric-Entity (metrics in col 0, data in col 1+)
    elif col_0["metric_ratio"] > 0.3 and col_1["numeric_ratio"] > 0.5:  # LOWERED threshold from 0.5
        orientation = "normal_metric"
        confidence = 0.85

    # Additional heuristics for edge cases
    elif col_0["metric_ratio"] > 0.5 and (entity_header_count > 0 or temporal_header_count > 0):
        # Strong metric patterns + entity/temporal headers = TRANSPOSED
        orientation = "transposed_metric"
        confidence = 0.85

    elif aspect_ratio < 0.7 and entity_header_count > 0:
        # More columns than rows + entity headers = TRANSPOSED
        orientation = "transposed_metric"
        confidence = 0.70

    else:
        # Unknown/ambiguous
        orientation = "unknown"
        confidence = 0.50

    # Logging with detailed metrics
    logger.info(
        f"Table orientation detected: {orientation} (confidence={confidence:.3f}, "
        f"aspect_ratio={aspect_ratio:.2f}, col_0_metric={col_0['metric_ratio']:.3f}, "
        f"col_0_numeric={col_0['numeric_ratio']:.3f}, col_1_unit={col_1['unit_ratio']:.3f}, "
        f"col_1_entity={col_1['entity_ratio']:.3f}, col_1_numeric={col_1['numeric_ratio']:.3f})"
    )

    return orientation, confidence


def _extract_units_normal(table_cells: list, unit_patterns: list[str]) -> dict[int, str]:
    """Extract units from normal table (entities in columns, metrics in rows).

    Strategy priorities for normal tables:
    1. Check for dedicated unit row (usually row 0, 1, or 2)
    2. Extract from row headers/metric names (e.g., "Revenue (EUR)")
    3. Extract from column headers

    Args:
        table_cells: List of table cells
        unit_patterns: List of unit pattern strings to match

    Returns:
        Dictionary mapping row index to unit string for normal tables

    Example:
        Normal table:
        Row 0: Entity    | GROUP   | PORTUGAL | ANGOLA
        Row 1: Unit      | EUR     | EUR      | EUR
        Row 2: Revenue   | 100M    | 50M      | 50M

        Returns: {0: 'EUR', 1: 'EUR', 2: 'EUR'} (from unit row)

        Alternative pattern (metric names with units):
        Row 0: Entity         | GROUP   | PORTUGAL | ANGOLA
        Row 1: Revenue (EUR)  | 100M    | 50M      | 50M

        Returns: {1: 'EUR'} (extracted from metric name)
    """
    units = {}

    # Strategy 1: Check for dedicated unit row (usually row 0, 1, or 2)
    for row_idx in [0, 1, 2]:
        row_cells = [c for c in table_cells if c.start_row_offset_idx == row_idx]

        if not row_cells:
            continue

        # Count cells with unit patterns
        unit_count = sum(
            1
            for c in row_cells
            if c.text and any(p.lower() in c.text.lower() for p in unit_patterns)
        )

        # If >60% of cells in this row contain units, it's a unit row
        if unit_count / len(row_cells) > 0.60:
            logger.info(
                "Found dedicated unit row in normal table",
                extra={
                    "row_index": row_idx,
                    "unit_count": unit_count,
                    "total_cells": len(row_cells),
                    "ratio": round(unit_count / len(row_cells), 3),
                },
            )

            # Extract units from this row
            for cell in row_cells:
                if cell.text and cell.text.strip():
                    units[cell.start_col_offset_idx] = cell.text.strip()

            return units

    # Strategy 2: Extract from row headers (metric names with units in parentheses)
    import re

    row_headers = [c for c in table_cells if c.start_col_offset_idx == 0]

    for cell in row_headers:
        if not cell.text:
            continue

        # Parse "Metric (Unit)" pattern
        match = re.search(r"\(([^)]+)\)", cell.text)
        if match:
            unit = match.group(1).strip()
            # Verify it's a valid unit pattern
            if any(p.lower() in unit.lower() for p in unit_patterns):
                units[cell.start_row_offset_idx] = unit
                logger.debug(
                    "Extracted unit from metric name",
                    extra={
                        "row_index": cell.start_row_offset_idx,
                        "metric": cell.text,
                        "unit": unit,
                    },
                )

    # Strategy 3: Extract from column headers (if units appear there)
    col_headers = [c for c in table_cells if c.column_header]
    for cell in col_headers:
        if not cell.text:
            continue

        # Check if header contains unit pattern
        for pattern in unit_patterns:
            if pattern.lower() in cell.text.lower():
                units[cell.start_col_offset_idx] = pattern
                break

    logger.info(
        "Normal table unit extraction completed",
        extra={
            "units_found": len(units),
            "extraction_strategies": "unit_row,metric_names,column_headers",
        },
    )

    return units


def _extract_units_entity_column_junk(
    table_cells: list, unit_patterns: list[str]
) -> dict[int, str]:
    """Extract units from Type B tables (junk column 0, entities in column 1).

    Structure:
    - Column 0: Numeric junk/indices (14.003, 8.430, 26, etc.)
    - Column 1: Entity names (Portugal, Portugal Cement, etc.)
    - Headers: Metric categories (Total R SUSTAINING, Total D DEVELOPMENT, etc.)

    Strategy:
    1. Check column headers for unit patterns (e.g., "CAPEX (EUR million)")
    2. Check rows 3-5 for dedicated unit row (beyond typical 0-2)
    3. Fallback to cell-level parsing

    Args:
        table_cells: List of table cells
        unit_patterns: List of unit pattern strings

    Returns:
        Dictionary mapping column index to unit string
    """
    import re

    units = {}

    # Strategy 1: Check column headers for unit patterns
    headers = [c for c in table_cells if c.column_header]
    for header in headers:
        if not header.text:
            continue

        # Check for pattern like "Total R SUSTAINING (EUR million)"
        match = re.search(r"\(([^)]+)\)", header.text)
        if match:
            potential_unit = match.group(1).strip()
            if any(p.lower() in potential_unit.lower() for p in unit_patterns):
                units[header.start_col_offset_idx] = potential_unit
                logger.debug(
                    "Extracted unit from header",
                    extra={"col_idx": header.start_col_offset_idx, "unit": potential_unit},
                )

    # Strategy 2: Check rows 3-5 for dedicated unit row (beyond typical 0-2)
    if not units:
        for row_idx in [3, 4, 5]:
            row_cells = [
                c for c in table_cells if c.start_row_offset_idx == row_idx and not c.column_header
            ]

            if not row_cells:
                continue

            # Count cells with unit patterns
            unit_count = sum(
                1
                for c in row_cells
                if c.text and any(p.lower() in c.text.lower() for p in unit_patterns)
            )

            # If >70% of cells contain units, it's a unit row
            if unit_count / len(row_cells) > 0.70:
                logger.info(
                    "Found dedicated unit row in Type B table",
                    extra={
                        "row_index": row_idx,
                        "unit_count": unit_count,
                        "total_cells": len(row_cells),
                        "ratio": round(unit_count / len(row_cells), 3),
                    },
                )

                # Extract units from this row
                for cell in row_cells:
                    if cell.text and cell.text.strip():
                        units[cell.start_col_offset_idx] = cell.text.strip()

                return units

    # Strategy 3: Check if all data cells have embedded units
    # (This means units might be in the data itself)
    if not units:
        logger.info(
            "No explicit units found in Type B table - units may be embedded in data",
            extra={"table_type": "entity_column_junk"},
        )

    return units


def _detect_unit_column_statistical(
    cells: list, unit_patterns: list[str], threshold: float = 0.60, min_samples: int = 3
) -> tuple[bool, float]:
    """Detect if a column contains units using statistical threshold analysis.

    This implements a production-grade framework for unit detection that works
    for ANY financial document, replacing the flawed "first 3 cells" positional
    sampling approach.

    Strategy:
    1. PRIMARY: Statistical analysis across ALL cells with configurable threshold
    2. SECONDARY: Pattern concentration in middle section (rows 3-10)
    3. FALLBACK: Extended unit patterns for edge cases

    Args:
        cells: List of cells to analyze
        unit_patterns: List of unit pattern strings to match
        threshold: Minimum ratio of cells with units (default: 0.60 = 60%)
        min_samples: Minimum number of cells required for analysis

    Returns:
        Tuple of (has_units: bool, confidence: float)
        - has_units: True if column contains units above threshold
        - confidence: Detection confidence score (0.0-1.0)

    Example:
        >>> cells = [cell1, cell2, cell3, ...] # 14 cells
        >>> patterns = ['EUR', 'ton', 'kt', '%']
        >>> has_units, confidence = _detect_unit_column_statistical(cells, patterns)
        >>> # has_units=True, confidence=0.857 if 12/14 cells match
    """
    if not cells:
        return False, 0.0

    # Filter to non-empty cells
    non_empty_cells = [cell for cell in cells if cell.text and cell.text.strip()]

    if len(non_empty_cells) < min_samples:
        # Not enough samples for statistical analysis
        return False, 0.0

    # STRATEGY 1: Statistical analysis across ALL cells
    cells_with_units = [
        cell for cell in non_empty_cells if any(pattern in cell.text for pattern in unit_patterns)
    ]

    unit_ratio = len(cells_with_units) / len(non_empty_cells)

    if unit_ratio >= threshold:
        # HIGH CONFIDENCE: Meets statistical threshold
        return True, unit_ratio

    # STRATEGY 2: Check middle section concentration (rows 3-10)
    # Units often concentrated in middle of table, sparse at edges
    middle_cells = [
        cell
        for cell in non_empty_cells
        if hasattr(cell, "start_row_offset_idx") and 3 <= cell.start_row_offset_idx <= 10
    ]

    if len(middle_cells) >= 3:
        middle_with_units = [
            cell for cell in middle_cells if any(pattern in cell.text for pattern in unit_patterns)
        ]
        middle_ratio = len(middle_with_units) / len(middle_cells)

        if middle_ratio >= 0.70:  # 70% in middle section
            # MEDIUM CONFIDENCE: Strong concentration in middle
            return True, 0.50 + (middle_ratio * 0.30)  # 0.50-0.80 confidence range

    # STRATEGY 3: Extended unit patterns (fallback)
    # Check for verbal unit indicators that might be missed
    extended_patterns = [
        "million",
        "billion",
        "thousand",
        "M€",
        "k€",
        "bn",
        "mn",
        "ratio",
        "rate",
        "percentage",
        "pct",
        "pts",
        "bps",
        "basis points",
        "people",
        "FTE",
        "headcount",
        "employees",
        "staff",
        "hours",
        "days",
        "months",
        "years",
        "weeks",
    ]

    extended_matches = [
        cell
        for cell in non_empty_cells
        if any(pattern.lower() in cell.text.lower() for pattern in extended_patterns)
    ]

    extended_ratio = len(extended_matches) / len(non_empty_cells)

    if extended_ratio >= 0.50:  # 50% threshold for extended patterns
        # LOW-MEDIUM CONFIDENCE: Extended patterns detected
        return True, 0.30 + (extended_ratio * 0.30)  # 0.30-0.60 confidence range

    # NO DETECTION: Column does not contain units
    return False, unit_ratio  # Return actual ratio for logging


def _parse_value_unit(text: str) -> tuple[float | None, str | None]:
    """Parse numeric value and unit from cell text."""
    if not text:
        return None, None

    text = text.strip().replace(",", ".")

    # Try to extract number
    number_match = re.search(r"[-+]?\d*\.?\d+", text)
    if number_match:
        try:
            value = float(number_match.group())
            # Extract unit (anything after the number)
            unit_text = text[number_match.end() :].strip()
            unit = unit_text if unit_text else None
            return value, unit
        except ValueError:
            return None, None

    return None, None


def _extract_year(period_text: str | None) -> int | None:
    """Extract fiscal year from period text."""
    if not period_text:
        return None

    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", period_text)
    if year_match:
        return int(year_match.group())

    return None


def _get_table_caption(table_item: TableItem) -> str | None:
    """Extract table caption if available.

    Note: Most financial PDFs don't have formal captions in Docling structure.
    Use _extract_page_context() for section-based context extraction.
    """
    if hasattr(table_item, "caption") and table_item.caption:
        return str(table_item.caption)
    return None


def _extract_page_context(table_item: TableItem, result: ConversionResult) -> dict:
    """Extract section headings and nearby text from page as table context.

    Production-validated approach from Unstructured.io, LLMSherpa research.
    Uses spatial proximity matching with Docling's document structure.

    Returns:
        dict with:
        - section_heading: Nearest section heading above table (if found)
        - nearby_text: Text elements near table (for additional context)
        - page_title: Largest/boldest text on page (potential title)
    """
    from docling_core.types.doc import SectionHeaderItem, TextItem

    if not result or not result.document:
        return {"section_heading": None, "nearby_text": [], "page_title": None}

    # Get table's page and position
    if not table_item.prov or len(table_item.prov) == 0:
        return {"section_heading": None, "nearby_text": [], "page_title": None}

    table_page = table_item.prov[0].page_no
    table_bbox = table_item.prov[0].bbox
    table_top = table_bbox.t  # Top coordinate

    section_heading = None
    nearby_text = []
    page_title = None

    best_heading_distance = float("inf")
    best_title_size = 0

    # Iterate through document to find text on same page
    for element, _level in result.document.iterate_items():
        # Only process text elements
        if not isinstance(element, (TextItem, SectionHeaderItem)):
            continue

        # Check if element has provenance and is on same page
        if not hasattr(element, "prov") or not element.prov or len(element.prov) == 0:
            continue

        elem_prov = element.prov[0]
        if elem_prov.page_no != table_page:
            continue

        # Get element text
        elem_text = getattr(element, "text", None)
        if not elem_text or not elem_text.strip():
            continue

        elem_bbox = elem_prov.bbox
        elem_top = elem_bbox.t

        # Section heading: text ABOVE table (higher t value in BOTTOMLEFT coords)
        if elem_top > table_top:  # Above table
            distance = elem_top - table_top

            # Prioritize section headers and closer proximity
            is_section_header = isinstance(element, SectionHeaderItem)
            weight = 0.5 if is_section_header else 1.0  # Section headers weighted 2x
            weighted_distance = distance * weight

            if weighted_distance < best_heading_distance:
                best_heading_distance = weighted_distance
                section_heading = elem_text.strip()

        # Collect nearby text (within vertical threshold)
        vertical_distance = abs(elem_top - table_top)
        if vertical_distance < 100:  # Within 100 units
            nearby_text.append(elem_text.strip())

        # Track potential page title (largest text)
        elem_height = abs(elem_bbox.t - elem_bbox.b)
        if elem_height > best_title_size:
            best_title_size = elem_height
            page_title = elem_text.strip()

    return {
        "section_heading": section_heading,
        "nearby_text": nearby_text[:5],  # Limit to 5 nearest
        "page_title": page_title,
    }


def _get_table_markdown(table_item: TableItem, result: ConversionResult | None) -> str:
    """Get markdown representation of table."""
    if result and hasattr(table_item, "export_to_markdown"):
        return table_item.export_to_markdown()
    return ""


# ============================================================================
# Phase 2.7.5: Context-Aware Unit Inference
# ============================================================================


def _infer_unit_from_context(
    metric: str,
    entity: str | None,
    table_caption: str | None,
    section_heading: str | None,
    page_title: str | None,
    nearby_text: list[str] | None,
) -> str | None:
    """Infer unit for a metric using LLM-based context analysis.

    Uses Mistral Small to analyze document context (titles, headers, captions) and
    infer the most likely unit for a metric when explicit unit extraction fails.

    This implements Phase 2.7.5 production strategy for handling implicit units
    that are common in financial documents (e.g., "All values in EUR million").

    Args:
        metric: Metric name (e.g., "EBITDA IFRS", "Variable Cost")
        entity: Entity name if available (e.g., "GROUP", "Portugal")
        table_caption: Table caption/title from Docling
        section_heading: Section header above table
        page_title: Page title or largest text on page
        nearby_text: List of text elements near table

    Returns:
        Inferred unit string (e.g., "EUR million", "Eur/ton"), or None if inference fails

    Example:
        >>> unit = _infer_unit_from_context(
        ...     metric="EBITDA IFRS",
        ...     entity="GROUP",
        ...     section_heading="Group Consolidated Results (EUR Million)",
        ...     table_caption="EBITDA by Region",
        ...     page_title="Financial Performance Report 2025",
        ...     nearby_text=["All monetary values in EUR million unless noted"]
        ... )
        >>> print(unit)
        'Meur'  # Inferred from section heading and context
    """
    from raglite.shared.config import settings

    # Check if Mistral API key is configured
    if not settings.mistral_api_key:
        logger.debug(
            "Mistral API key not configured - skipping unit inference", extra={"metric": metric}
        )
        return None

    # Build context string
    context_parts = []
    if page_title:
        context_parts.append(f"Page Title: {page_title}")
    if section_heading:
        context_parts.append(f"Section Heading: {section_heading}")
    if table_caption:
        context_parts.append(f"Table Caption: {table_caption}")
    if nearby_text:
        context_parts.append(f"Nearby Text: {', '.join(nearby_text[:3])}")

    context_str = "\n".join(context_parts) if context_parts else "No context available"

    # Build metric string
    metric_str = f"Metric: {metric}"
    if entity:
        metric_str += f" (Entity: {entity})"

    # Construct prompt for Mistral
    system_prompt = """You are analyzing a financial document table to infer the unit for a metric.

TASK:
Based on the document context, determine the most likely unit for this metric.

GUIDELINES:
1. Look for explicit unit statements in context (e.g., "All values in EUR million")
2. Consider common units for this metric type:
   - EBITDA, Net Income, Revenue → Meur, EUR million
   - Cost per ton, Price per ton → Eur/ton, EUR/ton
   - Production volume → kton, Mton
   - Ratios, margins → %
   - Days, periods → days
   - CAPEX → Meur, EUR million
3. If multiple possibilities exist, choose the most specific one mentioned in context
4. If no clear unit can be determined, respond with "UNKNOWN"

RESPONSE FORMAT:
Return ONLY the unit string (e.g., "Meur", "Eur/ton", "%", "kton") or "UNKNOWN".
Do NOT include explanations or additional text."""

    user_prompt = f"""DOCUMENT CONTEXT:
{context_str}

METRIC INFORMATION:
{metric_str}"""

    try:
        # Call Mistral API
        from mistralai import Mistral
        from mistralai.models import SystemMessage, UserMessage

        client = Mistral(api_key=settings.mistral_api_key)

        response = client.chat.complete(
            model=settings.metadata_extraction_model,  # "mistral-small-latest"
            messages=[SystemMessage(content=system_prompt), UserMessage(content=user_prompt)],
            temperature=0.0,  # Deterministic inference
            max_tokens=50,
        )

        # Extract inferred unit
        response_content = response.choices[0].message.content
        if not response_content:
            logger.debug("Empty response from Mistral", extra={"metric": metric, "entity": entity})
            return None

        inferred_unit = response_content.strip()

        # Validate response
        if inferred_unit == "UNKNOWN" or not inferred_unit:
            logger.debug(
                "Unit inference returned UNKNOWN", extra={"metric": metric, "entity": entity}
            )
            return None

        logger.info(
            "Unit inferred from context",
            extra={
                "metric": metric,
                "entity": entity,
                "inferred_unit": inferred_unit,
                "confidence": "llm_based",
            },
        )

        return inferred_unit

    except Exception as e:
        logger.warning(
            "Unit inference failed", extra={"metric": metric, "entity": entity, "error": str(e)}
        )
        return None


def _apply_context_aware_unit_inference(
    rows: list[dict[str, Any]], table_item: TableItem, result: ConversionResult
) -> list[dict[str, Any]]:
    """Apply LLM-based unit inference to rows with missing units.

    This is the main entry point for Phase 2.7.5 context-aware unit inference.
    It implements a hybrid strategy:
    1. Use explicit units when available (Phase 2.7.4)
    2. Infer units using LLM for rows with unit=None
    3. Cache inferred units for metric/entity consistency

    Args:
        rows: List of extracted row dictionaries (may have unit=None)
        table_item: Docling TableItem (for context extraction)
        result: Docling ConversionResult (for document-level context)

    Returns:
        Updated rows with inferred units where possible

    Example:
        >>> rows_in = [
        ...     {'metric': 'EBITDA IFRS', 'entity': 'GROUP', 'value': 128.825, 'unit': None},
        ...     {'metric': 'EBITDA IFRS', 'entity': 'PORTUGAL*', 'value': 91.438, 'unit': None}
        ... ]
        >>> rows_out = _apply_context_aware_unit_inference(rows_in, table_item, result)
        >>> rows_out[0]['unit']
        'Meur'  # Inferred from context
    """
    # Extract document context
    page_context = _extract_page_context(table_item, result)
    section_heading = page_context.get("section_heading")
    nearby_text = page_context.get("nearby_text", [])
    page_title = page_context.get("page_title")

    # Get table caption from Docling
    table_caption = getattr(table_item, "caption", None) if hasattr(table_item, "caption") else None

    # Cache for inferred units (metric -> unit)
    unit_cache: dict[str, str] = {}

    # Statistics
    inference_count = 0
    cache_hit_count = 0

    # Process rows
    for row in rows:
        # Skip rows that already have explicit units
        if row.get("unit") is not None:
            continue

        metric = row.get("metric")
        entity = row.get("entity")

        if not metric:
            continue  # Cannot infer without metric

        # Check cache first (metric-based consistency)
        cache_key = metric  # Use metric as key (same metric = same unit typically)
        if cache_key in unit_cache:
            row["unit"] = unit_cache[cache_key]
            row["unit_source"] = "cached_inference"
            cache_hit_count += 1
            continue

        # Infer unit using LLM
        inferred_unit = _infer_unit_from_context(
            metric=metric,
            entity=entity,
            table_caption=table_caption,
            section_heading=section_heading,
            page_title=page_title,
            nearby_text=nearby_text,
        )

        if inferred_unit:
            row["unit"] = inferred_unit
            row["unit_source"] = "llm_inference"
            unit_cache[cache_key] = inferred_unit  # Cache for next rows
            inference_count += 1

    # Log statistics
    total_null_units = sum(1 for row in rows if row.get("unit") is None)
    logger.info(
        "Context-aware unit inference complete",
        extra={
            "total_rows": len(rows),
            "inferred_count": inference_count,
            "cache_hits": cache_hit_count,
            "remaining_null": total_null_units,
        },
    )

    return rows
