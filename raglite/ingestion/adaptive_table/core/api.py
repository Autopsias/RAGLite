"""
Main API for adaptive table extraction.

This module provides the primary entry point for table data extraction.
"""

from __future__ import annotations

import logging
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
    unit_cache: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Extract table data using adaptive pattern detection with async unit inference.

    This is the main entry point for adaptive extraction. Implements Milestone 1 async
    conversion for 10x speedup in unit inference (62 min → 6 min for 942 rows).

    Story 5.0.6 AC3: Supports cross-document unit cache for 30% additional API reduction.

    Args:
        table_item: Docling TableItem
        result: Docling ConversionResult
        table_index: Table number on page
        document_id: Document filename
        page_number: Page number
        unit_cache: Optional shared cache for cross-document unit inference (AC3).
                   If None, creates local cache per table. If provided, enables reuse across documents.

    Returns:
        List of structured row dictionaries ready for PostgreSQL insertion

    Performance:
        - Async unit inference with 10 concurrent API calls
        - Rate limiting via MISTRAL_SEMAPHORE
        - 5-second timeout per call
        - Connection pooling via shared Mistral client
        - Story 5.0.6 AC3: Cross-document cache reduces duplicate API calls by 30%
    """
    from ..classification import TableLayout, detect_table_layout
    from ..multi_header import _extract_multi_header_metric_entity
    from ..standard_layouts import (
        _extract_entity_cols_metric_rows,
        _extract_temporal_cols_metric_rows,
        _extract_transposed_entity_cols_metric_row_labels,
    )
    from ..unit_inference import _apply_context_aware_unit_inference_async
    from .fallback import extract_fallback

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
        rows = extract_fallback(
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
    # Story 5.0.6 AC3: Pass unit_cache for cross-document reuse
    rows = await _apply_context_aware_unit_inference_async(rows, table_item, result, unit_cache)

    return rows
