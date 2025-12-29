"""
Fallback extraction logic for tables that don't match standard patterns.

This module provides orientation-aware extraction with section context inference
for tables that can't be classified into standard layouts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

# Phase 2: Import safe wrapper functions from centralized validation module
from ..validation import safe_infer_entity_from_context, safe_infer_metric_from_context
from .context import extract_page_context, get_table_caption, get_table_markdown
from .processing import extract_year

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

logger = logging.getLogger(__name__)


def extract_fallback(
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
    from ..classification import HeaderType, _detect_orientation, classify_header
    from ..unit_inference import _parse_value_unit
    from .processing import validate_entity

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
    page_context = extract_page_context(table_item, result)

    # Try to infer period from table caption (legacy, rarely works)
    caption = get_table_caption(table_item)
    caption_period = None
    caption_year = None
    if caption:
        caption_year = extract_year(caption)
        if caption_year or any(
            kw in caption.lower() for kw in ["ytd", "q1", "q2", "q3", "q4", "budget", "forecast"]
        ):
            caption_period = caption

    # Also try to extract period from section heading
    if not caption_period and page_context.get("section_heading"):
        section_heading = page_context["section_heading"]
        section_year = extract_year(section_heading)
        if section_year or any(
            kw in section_heading.lower()
            for kw in ["ytd", "q1", "q2", "q3", "q4", "budget", "forecast"]
        ):
            caption_period = section_heading
            caption_year = section_year

    # PHASE 3.1: Pre-scan row headers for hierarchical parent entity tracking
    # Identifies rows that are "parent" headers (entity-only rows that define context for following rows)
    # Pattern: Working Capital tables often have "Portugal" as a parent row, then "Trade Receivables" etc. below
    parent_entity_by_row: dict[int, str | None] = {}
    current_parent_entity: str | None = None

    # Build list of rows sorted by row index
    all_row_indices = sorted({cell.start_row_offset_idx for cell in data_cells})

    for row_idx in all_row_indices:
        row_header = row_header_map.get(row_idx)
        if not row_header:
            # No row header - inherit parent
            parent_entity_by_row[row_idx] = current_parent_entity
            continue

        # Check if this row header looks like a parent entity (standalone entity name)
        # Pattern: Row header is an ENTITY but row has very few data cells or mostly empty
        row_data_cells = [c for c in data_cells if c.start_row_offset_idx == row_idx]
        non_empty_cells = [c for c in row_data_cells if c.text and c.text.strip()]

        # Heuristic: If row header is entity-like and most data cells are empty,
        # this is likely a parent header row

        header_type = classify_header(row_header)
        is_likely_parent = (
            header_type == HeaderType.ENTITY
            and len(non_empty_cells) <= 1  # 0 or 1 data cell with values
        )

        if is_likely_parent:
            # This row defines a new parent entity context
            current_parent_entity = row_header
            logger.debug(
                "Hierarchical parent entity detected",
                extra={
                    "parent_entity": current_parent_entity,
                    "row_idx": row_idx,
                    "page_number": page_number,
                    "table_index": table_index,
                },
            )

        parent_entity_by_row[row_idx] = current_parent_entity

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
            fiscal_year = extract_year(row_header) if row_header else None
            confidence = "high"

        elif orientation == "metric_rows_temporal_cols":
            # Metrics in rows, periods in columns
            metric = row_header
            period = col_header
            entity = None  # May be inferred from caption
            fiscal_year = extract_year(col_header) if col_header else None
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
            fiscal_year = extract_year(col_header) if col_header else None
            confidence = "high"

        elif orientation == "temporal_rows_temporal_cols":
            # Both temporal - row as period, column as comparison
            period = row_header
            # Column might be "YTD", "LY", etc. - treat as part of period
            if col_header:
                period = f"{row_header} {col_header}" if row_header else col_header
            metric = None
            entity = None
            fiscal_year = extract_year(row_header) if row_header else None
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
                fiscal_year = extract_year(col_header) if col_header else None

            if row_type == HeaderType.ENTITY and not entity:
                entity = row_header
            elif row_type == HeaderType.METRIC and not metric:
                metric = row_header
            elif row_type == HeaderType.TEMPORAL and not period:
                period = row_header
                fiscal_year = extract_year(row_header) if row_header else None

            # Last resort: use caption
            if not period and caption_period:
                period = caption_period
                fiscal_year = caption_year

            confidence = "low"

        # SAFETY NET: Validate entity before context inference (June 2025 fix)
        # If entity is invalid (e.g., "Currency (1000 EUR)"), clear it so
        # context inference can set the correct value
        if entity and not validate_entity(entity):
            logger.warning(
                "Invalid entity detected in table extraction - clearing for context inference",
                extra={
                    "invalid_entity": entity,
                    "row_idx": row_idx,
                    "col_idx": col_idx,
                    "orientation": orientation,
                },
            )
            entity = None

        # PHASE 2.6: Section context-based inference for NULL fields
        # Phase 2: Use safe wrapper functions for context inference
        # These wrappers ALWAYS validate and are IMPOSSIBLE to bypass
        # Replaces 30 lines of manual validation logic with 6 lines of safe calls
        inferred_from_context = False

        if not metric and page_context:
            metric = safe_infer_metric_from_context(
                page_context,
                page_number=page_number,
                table_index=table_index,
                row_idx=row_idx,
                col_idx=col_idx,
            )
            if metric:
                inferred_from_context = True

        if not entity and page_context:
            entity = safe_infer_entity_from_context(
                page_context,
                page_number=page_number,
                table_index=table_index,
                row_idx=row_idx,
                col_idx=col_idx,
            )
            if entity:
                inferred_from_context = True

        # PHASE 3.1: Hierarchical parent entity fallback
        # If entity is STILL None, try to inherit from parent entity in hierarchical table
        if not entity and parent_entity_by_row.get(row_idx):
            entity = parent_entity_by_row[row_idx]
            logger.debug(
                "Entity inherited from hierarchical parent",
                extra={
                    "inherited_entity": entity,
                    "row_idx": row_idx,
                    "page_number": page_number,
                    "table_index": table_index,
                },
            )
            # Track as context-inferred but medium confidence (hierarchical inheritance)
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
            "chunk_text": get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
            "extraction_method": extraction_method,  # PHASE 2.5: Track orientation + caption inference
            "confidence": confidence,  # High for header-based, medium for caption-inferred, low for unknown
        }

        rows.append(row_dict)

    return rows
