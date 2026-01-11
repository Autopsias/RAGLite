"""
Context extraction helpers for table processing.

This module provides functions to extract context from page/section structure
for improved table understanding.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

# Type-checking imports for Docling types
try:
    from docling_core.types.doc import SectionHeaderItem, TextItem
except ImportError:
    SectionHeaderItem = None  # type: ignore
    TextItem = None  # type: ignore


def get_table_caption(table_item: TableItem) -> str | None:
    """Extract table caption if available.

    Note: Most financial PDFs don't have formal captions in Docling structure.
    Use extract_page_context() for section-based context extraction.
    """
    if hasattr(table_item, "caption") and table_item.caption:
        return str(table_item.caption)
    return None


def extract_page_context(table_item: TableItem, result: ConversionResult) -> dict:
    """Extract section headings and nearby text from page as table context.

    Production-validated approach from Unstructured.io, LLMSherpa research.
    Uses spatial proximity matching with Docling's document structure.

    Returns:
        dict with:
        - section_heading: Nearest section heading above table (if found)
        - nearby_text: Text elements near table (for additional context)
        - page_title: Largest/boldest text on page (potential title)
    """
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


def get_table_markdown(table_item: TableItem, result: ConversionResult | None) -> str:
    """Get markdown representation of table."""
    if result and hasattr(table_item, "export_to_markdown"):
        markdown_result = table_item.export_to_markdown()
        return str(markdown_result) if markdown_result is not None else ""
    return ""


# Backward compatibility aliases (with underscore prefix for internal use)
_extract_page_context = extract_page_context
_get_table_caption = get_table_caption
_get_table_markdown = get_table_markdown
