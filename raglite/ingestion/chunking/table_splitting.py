"""Table-aware splitting for large tables.

Handles row-based table splitting with header duplication for tables exceeding token limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

logger = get_logger(__name__)


def split_large_table_by_rows(
    table_item: TableItem,
    result: ConversionResult,
    encoding: Any,
    max_tokens: int = 4096,
    table_index: int = 0,
) -> list[tuple[str, str | None]]:
    """Split large tables by logical rows while preserving column headers.

    Story 2.8 AC2: Row-based table splitting strategy for tables exceeding 4096 tokens.

    Args:
        table_item: Docling TableItem to split
        result: ConversionResult for markdown export
        encoding: tiktoken encoding for token counting
        max_tokens: Token threshold for splitting (default: 4096)
        table_index: Index of table in document (for context prefix)

    Returns:
        List of (table_chunk_content, table_caption) tuples

    Strategy (AC2):
        - Split by table rows (preserve row boundaries)
        - Duplicate column headers in each chunk
        - Add table context prefix: "Table {index} (Part {n} of {total}): {caption}"
        - Ensure all chunks <4096 tokens
    """
    # Export table to markdown
    table_content = table_item.export_to_markdown(doc=result.document)
    token_count = len(encoding.encode(table_content))

    # If table is small enough, return as-is (AC1: tables <4096 tokens kept intact)
    if token_count < max_tokens:
        return [(table_content, None)]

    logger.info(
        f"Splitting large table ({token_count} tokens) by rows",
        extra={
            "token_count": token_count,
            "threshold": max_tokens,
            "table_index": table_index,
        },
    )

    # Split table into lines
    lines = table_content.split("\n")

    # Extract table caption (first non-empty line before table header)
    caption = None
    table_start_idx = 0
    for i, line in enumerate(lines):
        if "|" in line:
            table_start_idx = i
            break
        elif line.strip() and not line.startswith("#"):
            caption = line.strip()

    # Extract table header (first 2-3 lines of markdown table)
    # Markdown tables have: header row | separator row | data rows
    header_lines = []
    data_start_idx = table_start_idx
    for i in range(table_start_idx, min(table_start_idx + 3, len(lines))):
        if i < len(lines) and "|" in lines[i]:
            header_lines.append(lines[i])
            data_start_idx = i + 1
        else:
            break

    # Extract data rows (everything after header)
    data_rows = [line for line in lines[data_start_idx:] if "|" in line]

    if not header_lines or not data_rows:
        logger.warning(
            "Table splitting failed - no headers or data rows found",
            extra={"table_index": table_index},
        )
        return [(table_content, caption)]

    # AC2: Split rows into chunks, accumulating until max_tokens
    header_text = "\n".join(header_lines)
    header_tokens = len(encoding.encode(header_text))

    chunks: list[tuple[str, str | None]] = []
    current_chunk_rows: list[str] = []
    current_token_count = header_tokens

    for row in data_rows:
        row_tokens = len(encoding.encode(row + "\n"))

        # Check if adding this row would exceed limit
        if current_token_count + row_tokens > max_tokens and current_chunk_rows:
            # Create chunk from accumulated rows
            chunk_content = header_text + "\n" + "\n".join(current_chunk_rows)
            chunks.append((chunk_content, caption))

            # Reset for next chunk
            current_chunk_rows = [row]
            current_token_count = header_tokens + row_tokens
        else:
            current_chunk_rows.append(row)
            current_token_count += row_tokens

    # Add final chunk
    if current_chunk_rows:
        chunk_content = header_text + "\n" + "\n".join(current_chunk_rows)
        chunks.append((chunk_content, caption))

    # AC2: Add table context prefix to each chunk
    total_parts = len(chunks)
    chunks_with_prefix: list[tuple[str, str | None]] = []

    for part_num, (chunk_content, chunk_caption) in enumerate(chunks, start=1):
        # Format: "Table {index} (Part {n} of {total}): {caption}"
        if total_parts > 1:
            prefix = f"Table {table_index} (Part {part_num} of {total_parts})"
            if chunk_caption:
                prefix += f": {chunk_caption}"
            prefixed_content = f"{prefix}\n\n{chunk_content}"
        else:
            # Single chunk doesn't need part number
            if chunk_caption:
                prefixed_content = f"Table {table_index}: {chunk_caption}\n\n{chunk_content}"
            else:
                prefixed_content = chunk_content

        chunks_with_prefix.append((prefixed_content, chunk_caption))

    logger.info(
        f"Split large table into {total_parts} row-based chunks",
        extra={
            "original_tokens": token_count,
            "num_chunks": total_parts,
            "avg_chunk_tokens": token_count // total_parts if total_parts else 0,
            "table_index": table_index,
        },
    )

    return chunks_with_prefix
