"""Docling chunk merging utilities.

Handles merging of tiny chunks to reduce variance and improve quality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk, DocumentMetadata

if TYPE_CHECKING:
    import tiktoken

logger = get_logger(__name__)


def merge_with_previous(
    current_chunk: Chunk,
    merged_chunks: list[Chunk],
    encoding: tiktoken.Encoding,
) -> bool:
    """Merge tiny chunk with previous chunk.

    Args:
        current_chunk: Chunk to potentially merge
        merged_chunks: List of already merged chunks
        encoding: tiktoken encoding

    Returns:
        True if merged, False otherwise
    """
    if not merged_chunks:
        return False

    prev_chunk = merged_chunks[-1]
    merged_content = prev_chunk.content + "\n\n" + current_chunk.content
    prev_chunk.content = merged_content
    prev_chunk.word_count = len(merged_content.split())

    logger.debug(
        "Merged tiny text chunk with previous chunk",
        extra={
            "tiny_chunk_tokens": len(encoding.encode(current_chunk.content)),
            "merged_chunk_tokens": len(encoding.encode(merged_content)),
            "chunk_index": current_chunk.chunk_index,
        },
    )
    return True


def merge_with_next(
    current_chunk: Chunk,
    next_chunk: Chunk,
    encoding: tiktoken.Encoding,
) -> int:
    """Merge chunk with next chunk.

    Args:
        current_chunk: Current chunk
        next_chunk: Next chunk to merge with
        encoding: tiktoken encoding

    Returns:
        Combined token count
    """
    current_tokens = len(encoding.encode(current_chunk.content))
    merged_content = current_chunk.content + "\n\n" + next_chunk.content
    next_chunk.content = merged_content
    next_chunk.word_count = len(merged_content.split())

    combined_tokens = len(encoding.encode(merged_content))

    logger.debug(
        "Merged chunks",
        extra={
            "current_tokens": current_tokens,
            "combined_tokens": combined_tokens,
            "chunk_index": current_chunk.chunk_index,
        },
    )
    return combined_tokens


def merge_tiny_chunks(
    chunks: list[Chunk],
    table_chunk_count: int,
    encoding: tiktoken.Encoding,
    chunk_size: int,
    doc_metadata: DocumentMetadata,
) -> list[Chunk]:
    """Merge tiny text chunks to reduce variance.

    Args:
        chunks: All chunks (tables + text)
        table_chunk_count: Number of table chunks
        encoding: tiktoken encoding
        chunk_size: Target chunk size
        doc_metadata: Document metadata

    Returns:
        Merged chunks with reindexed chunk_id and chunk_index
    """
    MIN_CHUNK_TOKENS = 100
    SMALL_CHUNK_THRESHOLD = 256

    text_chunks_only = chunks[table_chunk_count:]

    if not text_chunks_only:
        return chunks

    merged_text_chunks: list[Chunk] = []
    i = 0
    while i < len(text_chunks_only):
        current_chunk = text_chunks_only[i]
        current_token_count = len(encoding.encode(current_chunk.content))

        # Tiny chunk: merge with previous if possible
        if current_token_count < MIN_CHUNK_TOKENS and merge_with_previous(
            current_chunk, merged_text_chunks, encoding
        ):
            i += 1
            continue

        # Small first chunk: try merging with next
        if (
            SMALL_CHUNK_THRESHOLD <= current_token_count < chunk_size * 0.85
            and i + 1 < len(text_chunks_only)
            and not merged_text_chunks
        ):
            next_chunk = text_chunks_only[i + 1]
            combined_tokens = merge_with_next(current_chunk, next_chunk, encoding)

            if combined_tokens <= chunk_size * 1.25:
                i += 1
                merged_text_chunks.append(next_chunk)
                i += 1
                continue

        # Tiny first chunk: merge with next
        if current_token_count < MIN_CHUNK_TOKENS and i + 1 < len(text_chunks_only):
            next_chunk = text_chunks_only[i + 1]
            merge_with_next(current_chunk, next_chunk, encoding)
            i += 1
            merged_text_chunks.append(next_chunk)
            i += 1
            continue

        # Normal chunk
        merged_text_chunks.append(current_chunk)
        i += 1

    # Rebuild and reindex chunks
    final_chunks = chunks[:table_chunk_count] + merged_text_chunks
    for idx, chunk in enumerate(final_chunks):
        chunk.chunk_index = idx
        chunk.chunk_id = f"{doc_metadata.filename}_{idx}"

    return final_chunks
