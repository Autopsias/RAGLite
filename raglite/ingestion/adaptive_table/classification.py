"""
Header classification and table layout detection for adaptive table extraction.

This module provides:
1. Header cell classification (TEMPORAL, ENTITY, METRIC)
2. Table layout pattern detection
3. Table orientation detection

Used as the base module for all other table extraction modules.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from enum import Enum
from typing import Any

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
        type_counts: dict[HeaderType, int] = {}
        for cell in cells:
            h_type = classify_header(cell.text)
            type_counts[h_type] = type_counts.get(h_type, 0) + 1
        col_header_types[row_idx] = type_counts

    # Classify row headers
    row_header_type_counts: dict[HeaderType, int] = {}
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
        first_col_types: dict[HeaderType, int] = {}
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
    # Classify all headers
    col_types: Counter[HeaderType] = Counter()
    for cell in column_headers:
        if cell.text:
            h_type = classify_header(cell.text)
            col_types[h_type] += 1

    row_types: Counter[HeaderType] = Counter()
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
