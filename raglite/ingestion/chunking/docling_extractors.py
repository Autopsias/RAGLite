"""Docling extraction utilities for tables and text items.

Handles extraction of tables and text from Docling ConversionResult with page mapping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tiktoken
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem


def extract_tables_and_text(
    result: ConversionResult,
) -> tuple[list[tuple[TableItem, int]], list[tuple[str, int]]]:
    """Extract tables and text items from Docling conversion result.

    Args:
        result: Docling ConversionResult

    Returns:
        Tuple of (tables, text_items) where:
        - tables: List of (TableItem, page_number)
        - text_items: List of (text_content, page_number)
    """
    from docling_core.types.doc import TableItem

    tables: list[tuple[TableItem, int]] = []
    text_items: list[tuple[str, int]] = []

    for item, _ in result.document.iterate_items():
        # Get page number from provenance
        page_number = 1  # Default fallback
        if hasattr(item, "prov") and item.prov:
            page_number = item.prov[0].page_no

        if isinstance(item, TableItem):
            tables.append((item, page_number))
        elif hasattr(item, "text"):
            text_items.append((item.text, page_number))

    return tables, text_items


def build_page_mapping(
    text_items: list[tuple[str, int]],
    encoding: tiktoken.Encoding,
) -> tuple[str, list[tuple[int, int, int]]]:
    """Build page mapping for text items.

    Args:
        text_items: List of (text_content, page_number)
        encoding: tiktoken encoding

    Returns:
        Tuple of (full_text, page_mapping) where:
        - full_text: Concatenated text
        - page_mapping: List of (token_start, token_end, page_number)
    """
    page_mapping: list[tuple[int, int, int]] = []
    full_text_parts: list[str] = []
    current_token_offset = 0

    for text_content, page_num in text_items:
        if text_content.strip():
            item_tokens = encoding.encode(text_content)
            item_token_count = len(item_tokens)

            page_mapping.append(
                (
                    current_token_offset,
                    current_token_offset + item_token_count,
                    page_num,
                )
            )

            full_text_parts.append(text_content)
            current_token_offset += item_token_count

            separator_tokens = encoding.encode("\n\n")
            current_token_offset += len(separator_tokens)

    full_text = "\n\n".join(full_text_parts)
    return full_text, page_mapping
