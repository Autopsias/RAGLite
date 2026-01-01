"""
Table orientation detection for adaptive table extraction.

This module provides table orientation detection using multi-column analysis
and aspect ratio heuristics.
"""

from __future__ import annotations

import logging
import re
from collections import Counter

from .header import HeaderType, classify_header

logger = logging.getLogger(__name__)


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
        # ====== CEMENT INDUSTRY SPECIFIC (Phase 1.1) ======
        # Fuels - CRITICAL for petcoke queries
        "Petcoke",
        "Pet Coke",
        "Petroleum Coke",
        "Coal",
        "Lignite",
        "Natural Gas",
        "Fuel Oil",
        "Alternative Fuel",
        "AF Rate",
        "Biomass",
        # Production metrics
        "Clinker",
        "Clinker Factor",
        "Clinker Ratio",
        "Slag",
        "Fly Ash",
        "Gypsum",
        "Limestone",
        "Kiln",
        "Raw Mill",
        "Cement Mill",
        # Sustainability
        "CO2",
        "Emissions",
        "Carbon",
        "Scope 1",
        "Scope 2",
        "Scope 3",
        "TSR",
        "Thermal Substitution",
        # Units
        "kcal/kg",
        "GJ/ton",
        "kWh/ton",
        "MTPA",
        "TPD",
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
