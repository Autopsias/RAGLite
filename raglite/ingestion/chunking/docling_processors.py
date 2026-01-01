"""Docling chunk processing for tables and text.

Handles creation of table and text chunks from extracted items.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk, DocumentMetadata

if TYPE_CHECKING:
    import tiktoken
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

logger = get_logger(__name__)


def process_table_chunks(
    tables: list[tuple[TableItem, int]],
    result: ConversionResult,
    encoding: tiktoken.Encoding,
    doc_metadata: DocumentMetadata,
    chunk_index: int,
) -> tuple[list[Chunk], int]:
    """Process tables and create table chunks.

    Args:
        tables: List of (TableItem, page_number)
        result: Docling ConversionResult
        encoding: tiktoken encoding
        doc_metadata: Document metadata
        chunk_index: Current chunk index

    Returns:
        Tuple of (chunks, updated_chunk_index)
    """
    from raglite.ingestion.chunking.table_splitting import split_large_table_by_rows

    chunks = []
    table_index = 0

    for table_item, page_num in tables:
        table_index += 1

        # Story 2.8 AC2: Split tables by rows if >4096 tokens, else keep intact
        table_chunks = split_large_table_by_rows(
            table_item=table_item,
            result=result,
            encoding=encoding,
            max_tokens=4096,  # AC1: 4096 token threshold
            table_index=table_index,
        )

        for chunk_content, _caption in table_chunks:
            word_count = len(chunk_content.split())
            token_count = len(encoding.encode(chunk_content))

            chunk = Chunk(
                chunk_id=f"{doc_metadata.filename}_{chunk_index}",
                content=chunk_content,
                metadata=doc_metadata,
                page_number=page_num,
                chunk_index=chunk_index,
                embedding=[],
                word_count=word_count,
                section_type="Table",
            )
            chunks.append(chunk)
            chunk_index += 1

            logger.debug(
                "Table chunk created (table-aware chunking with 4096-token threshold)",
                extra={
                    "chunk_index": chunk_index - 1,
                    "token_count": token_count,
                    "word_count": word_count,
                    "page": page_num,
                    "table_index": table_index,
                    "is_multi_part": len(table_chunks) > 1,
                    "total_parts": len(table_chunks),
                },
            )

    return chunks, chunk_index


def create_text_chunks(
    full_text: str,
    page_mapping: list[tuple[int, int, int]],
    encoding: tiktoken.Encoding,
    doc_metadata: DocumentMetadata,
    chunk_size: int,
    overlap: int,
    chunk_index: int,
) -> tuple[list[Chunk], int]:
    """Create text chunks with sliding window and sentence boundary preservation.

    Args:
        full_text: Concatenated text content
        page_mapping: List of (token_start, token_end, page_number)
        encoding: tiktoken encoding
        doc_metadata: Document metadata
        chunk_size: Target chunk size in tokens
        overlap: Token overlap between chunks
        chunk_index: Current chunk index

    Returns:
        Tuple of (chunks, updated_chunk_index)
    """
    chunks: list[Chunk] = []

    if not full_text.strip():
        return chunks, chunk_index

    tokens = encoding.encode(full_text)
    total_tokens = len(tokens)

    logger.info(
        "Tokenized document text",
        extra={
            "total_tokens": total_tokens,
            "estimated_chunks": (total_tokens // (chunk_size - overlap)) + 1,
            "page_mappings": len(page_mapping),
        },
    )

    idx = 0
    while idx < total_tokens:
        chunk_tokens = tokens[idx : idx + chunk_size]
        chunk_text = encoding.decode(chunk_tokens)

        # AC2: Preserve sentence boundaries when possible
        if idx + chunk_size < total_tokens and len(chunk_text) > 50:
            last_100_chars = chunk_text[-100:]
            sentence_end_positions = [
                last_100_chars.rfind(". "),
                last_100_chars.rfind("! "),
                last_100_chars.rfind("? "),
                last_100_chars.rfind(".\n"),
            ]
            max_pos = max(sentence_end_positions)

            if max_pos > 0:
                cut_position = len(chunk_text) - 100 + max_pos + 1
                trimmed_text = chunk_text[:cut_position].strip()
                trimmed_tokens = len(encoding.encode(trimmed_text))

                MIN_TRIMMED_SIZE = int(chunk_size * 0.75)

                if trimmed_tokens >= MIN_TRIMMED_SIZE:
                    chunk_text = trimmed_text

        # Find page number for this chunk
        chunk_page = 1  # Fallback default
        for token_start, token_end, page_num in page_mapping:
            if token_start <= idx < token_end:
                chunk_page = page_num
                break

        word_count = len(chunk_text.split())

        chunk = Chunk(
            chunk_id=f"{doc_metadata.filename}_{chunk_index}",
            content=chunk_text,
            metadata=doc_metadata,
            page_number=chunk_page,
            chunk_index=chunk_index,
            embedding=[],
            word_count=word_count,
        )
        chunks.append(chunk)
        chunk_index += 1

        # Advance with overlap
        actual_chunk_tokens = len(encoding.encode(chunk_text))

        if actual_chunk_tokens < chunk_size * 0.85:
            adjusted_overlap = max(10, int(overlap * (actual_chunk_tokens / chunk_size)))
            idx += chunk_size - adjusted_overlap
        else:
            idx += chunk_size - overlap

    return chunks, chunk_index
