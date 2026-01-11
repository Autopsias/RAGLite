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


def _build_header_mappings(
    table_cells: list,
) -> tuple[dict[int, str | None], dict[int, str | None], list]:
    """Build column and row header mappings from table cells.

    Returns:
        Tuple of (col_header_map, row_header_map, data_cells)
    """
    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]
    data_cells = [cell for cell in table_cells if not cell.column_header and not cell.row_header]

    # If no headers at all, skip (can't extract anything meaningful)
    if not column_headers and not row_headers:
        return {}, {}, []

    # Build column header mapping
    col_header_map: dict[int, str | None] = {}
    for cell in column_headers:
        for col_idx in range(cell.start_col_offset_idx, cell.end_col_offset_idx):
            if col_idx not in col_header_map:  # First header wins if multiple rows
                col_header_map[col_idx] = cell.text.strip() if cell.text else None

    # Build row header mapping
    row_header_map: dict[int, str | None] = {}
    for cell in row_headers:
        row_idx = cell.start_row_offset_idx
        if row_idx not in row_header_map:
            row_header_map[row_idx] = cell.text.strip() if cell.text else None

    return col_header_map, row_header_map, data_cells


def _extract_caption_period_info(
    table_item: TableItem,
    result: ConversionResult,
    page_context: dict,
) -> tuple[str | None, str | None]:
    """Extract period information from table caption and section heading.

    Returns:
        Tuple of (caption_period, caption_year)
    """

    caption = get_table_caption(table_item)
    caption_period = None
    caption_year = None

    # Try to infer period from table caption (legacy, rarely works)
    if caption:
        year = extract_year(caption)
        caption_year = str(year) if year is not None else None
        if caption_year or any(
            kw in caption.lower() for kw in ["ytd", "q1", "q2", "q3", "q4", "budget", "forecast"]
        ):
            caption_period = caption

    # Also try to extract period from section heading
    if not caption_period and page_context.get("section_heading"):
        section_heading = page_context["section_heading"]
        year = extract_year(section_heading)
        section_year = str(year) if year is not None else None
        if section_year or any(
            kw in section_heading.lower()
            for kw in ["ytd", "q1", "q2", "q3", "q4", "budget", "forecast"]
        ):
            caption_period = section_heading
            caption_year = section_year

    return caption_period, caption_year


def _build_hierarchical_parent_map(
    row_header_map: dict[int, str | None],
    data_cells: list,
    page_number: int,
    table_index: int,
) -> dict[int, str | None]:
    """Build map of parent entities for hierarchical table structures.

    Identifies rows that are "parent" headers (entity-only rows that define
    context for following rows). Pattern: Working Capital tables often have
    "Portugal" as a parent row, then "Trade Receivables" etc. below.

    Returns:
        Dictionary mapping row_idx to parent_entity (or None)
    """
    from ..classification import HeaderType, classify_header

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

    return parent_entity_by_row


def _apply_context_inference(
    entity: str | None,
    metric: str | None,
    page_context: dict,
    page_number: int,
    table_index: int,
    row_idx: int,
    col_idx: int,
) -> tuple[str | None, str | None, bool]:
    """Apply section context-based inference for NULL entity/metric fields.

    Returns:
        Tuple of (entity, metric, inferred_from_context)
    """
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

    return entity, metric, inferred_from_context


def _apply_hierarchical_entity_fallback(
    entity: str | None,
    row_idx: int,
    parent_entity_by_row: dict[int, str | None],
    page_number: int,
    table_index: int,
) -> tuple[str | None, bool]:
    """Apply hierarchical parent entity fallback for missing entity.

    Returns:
        Tuple of (entity, inferred_from_parent)
    """
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
        return entity, True

    return entity, False


def _build_extraction_row(
    entity: str | None,
    metric: str | None,
    period: str | None,
    fiscal_year: str | None,
    value: float | int | None,
    unit: str | None,
    confidence: str,
    extraction_method: str,
    page_number: int,
    table_index: int,
    caption: str | None,
    row_idx: int,
    document_id: str,
    table_item: TableItem,
    result: ConversionResult,
) -> dict[str, Any]:
    """Build extraction row dictionary with all required fields."""
    return {
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
        "extraction_method": extraction_method,
        "confidence": confidence,
    }


def _extract_fields_from_cell(
    cell: Any,
    orientation: str,
    col_header_map: dict[int, str | None],
    row_header_map: dict[int, str | None],
    caption_period: str | None,
    caption_year: str | None,
    page_context: dict,
    parent_entity_by_row: dict[int, str | None],
    page_number: int,
    table_index: int,
) -> dict[str, Any] | None:
    """Extract all fields from a single data cell.

    Returns:
        Dictionary with extracted fields or None if cell is empty
    """
    from ..unit_inference import _parse_value_unit
    from .field_assignment import _assign_fields_by_orientation
    from .processing import validate_entity

    if not cell.text or not cell.text.strip():
        return None

    row_idx = cell.start_row_offset_idx
    col_idx = cell.start_col_offset_idx

    col_header = col_header_map.get(col_idx)
    row_header = row_header_map.get(row_idx)

    # Apply orientation-specific field assignment
    entity, metric, period, fiscal_year, confidence = _assign_fields_by_orientation(
        orientation, col_header, row_header, caption_period, caption_year
    )

    # SAFETY NET: Validate entity before context inference (June 2025 fix)
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
    entity, metric, inferred_from_context = _apply_context_inference(
        entity, metric, page_context, page_number, table_index, row_idx, col_idx
    )

    # PHASE 3.1: Hierarchical parent entity fallback
    entity, inferred_from_parent = _apply_hierarchical_entity_fallback(
        entity, row_idx, parent_entity_by_row, page_number, table_index
    )
    if inferred_from_parent:
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

    return {
        "entity": entity,
        "metric": metric,
        "period": period,
        "fiscal_year": fiscal_year,
        "value": value,
        "unit": unit,
        "confidence": confidence,
        "extraction_method": extraction_method,
        "row_idx": row_idx,
    }


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
    from ..classification import _detect_orientation

    rows: list[dict[str, Any]] = []

    # Build header mappings and get data cells
    col_header_map, row_header_map, data_cells = _build_header_mappings(table_cells)

    # If no headers at all, skip (can't extract anything meaningful)
    if not col_header_map and not row_header_map:
        return []

    # PHASE 2: Detect table orientation FIRST
    orientation, orientation_meta = _detect_orientation(
        [cell for cell in table_cells if cell.column_header],
        [cell for cell in table_cells if cell.row_header],
    )

    # PHASE 2.6: Extract page/section context for fallback inference
    page_context = extract_page_context(table_item, result)

    # Extract caption and section heading period information
    caption = get_table_caption(table_item)
    caption_period, caption_year = _extract_caption_period_info(table_item, result, page_context)

    # PHASE 3.1: Build hierarchical parent entity map
    parent_entity_by_row = _build_hierarchical_parent_map(
        row_header_map, data_cells, page_number, table_index
    )

    # Extract data cells using ORIENTATION-AWARE field assignment
    for cell in data_cells:
        fields = _extract_fields_from_cell(
            cell=cell,
            orientation=orientation,
            col_header_map=col_header_map,
            row_header_map=row_header_map,
            caption_period=caption_period,
            caption_year=caption_year,
            page_context=page_context,
            parent_entity_by_row=parent_entity_by_row,
            page_number=page_number,
            table_index=table_index,
        )

        if fields:
            row_dict = _build_extraction_row(
                entity=fields["entity"],
                metric=fields["metric"],
                period=fields["period"],
                fiscal_year=fields["fiscal_year"],
                value=fields["value"],
                unit=fields["unit"],
                confidence=fields["confidence"],
                extraction_method=fields["extraction_method"],
                page_number=page_number,
                table_index=table_index,
                caption=caption,
                row_idx=fields["row_idx"],
                document_id=document_id,
                table_item=table_item,
                result=result,
            )
            rows.append(row_dict)

    return rows
