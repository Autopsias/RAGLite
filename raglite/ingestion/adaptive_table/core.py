"""
Core API and helper functions for adaptive table extraction.

This module provides:
1. Main async extraction API (extract_table_data_adaptive)
2. Context extraction from page/section structure
3. Fallback extraction with orientation detection
4. Helper utilities for year, caption, and markdown extraction

This is the main entry point for table data extraction.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

logger = logging.getLogger(__name__)


async def extract_table_data_adaptive(
    table_item: TableItem,
    result: ConversionResult,
    table_index: int,
    document_id: str,
    page_number: int,
) -> list[dict[str, Any]]:
    """Extract table data using adaptive pattern detection with async unit inference.

    This is the main entry point for adaptive extraction. Implements Milestone 1 async
    conversion for 10x speedup in unit inference (62 min → 6 min for 942 rows).

    Args:
        table_item: Docling TableItem
        result: Docling ConversionResult
        table_index: Table number on page
        document_id: Document filename
        page_number: Page number

    Returns:
        List of structured row dictionaries ready for PostgreSQL insertion

    Performance:
        - Async unit inference with 10 concurrent API calls
        - Rate limiting via MISTRAL_SEMAPHORE
        - 5-second timeout per call
        - Connection pooling via shared Mistral client
    """
    from .classification import (
        TableLayout,
        detect_table_layout,
    )
    from .multi_header import _extract_multi_header_metric_entity
    from .standard_layouts import (
        _extract_entity_cols_metric_rows,
        _extract_temporal_cols_metric_rows,
        _extract_transposed_entity_cols_metric_row_labels,
    )
    from .unit_inference import _apply_context_aware_unit_inference_async

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

    # Phase 2.7.5: Apply async context-aware unit inference for rows with null units
    # Milestone 1: Uses concurrent processing for 10x speedup (62 min → 6 min)
    rows = await _apply_context_aware_unit_inference_async(rows, table_item, result)

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
    section_heading_value = page_context.get("section_heading")
    if section_heading_value and isinstance(section_heading_value, str):
        # Simple heuristic: if section heading is short (< 5 words), use it as entity
        heading_words = section_heading_value.split()
        if 1 <= len(heading_words) <= 4:
            # Type narrowing: section_heading_value is confirmed str at this point
            result: str = section_heading_value
            return result

    return None


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
    from .classification import HeaderType, _detect_orientation, classify_header
    from .unit_inference import _parse_value_unit

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
    col_header_map: dict[int, str | None] = {}
    for cell in column_headers:
        for col_idx in range(cell.start_col_offset_idx, cell.end_col_offset_idx):
            if col_idx not in col_header_map:  # First header wins if multiple rows
                col_header_map[col_idx] = cell.text.strip() if cell.text else None

    row_header_map: dict[int, str | None] = {}
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
            "column_name": (
                f"{metric}_{period}"
                if metric and period
                else f"{metric}_{entity}"
                if metric and entity
                else None
            ),
            "chunk_text": _get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
            "extraction_method": extraction_method,  # PHASE 2.5: Track orientation + caption inference
            "confidence": confidence,  # High for header-based, medium for caption-inferred, low for unknown
        }

        rows.append(row_dict)

    return rows


# Helper functions


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
    best_title_size: float = 0.0

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
        markdown_result = table_item.export_to_markdown()
        return str(markdown_result) if markdown_result is not None else ""
    return ""
