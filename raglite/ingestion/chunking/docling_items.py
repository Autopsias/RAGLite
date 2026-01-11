"""Docling-based document chunking with provenance tracking.

Handles PDF chunking using Docling ConversionResult with accurate page numbers.

This module serves as a facade that re-exports functionality from specialized modules:
- docling_extractors: Table and text extraction
- docling_processors: Chunk creation for tables and text
- docling_merging: Chunk merging utilities
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from raglite.ingestion.chunking.docling_extractors import (
    build_page_mapping as _build_page_mapping,
)
from raglite.ingestion.chunking.docling_extractors import (
    extract_tables_and_text as _extract_tables_and_text,
)
from raglite.ingestion.chunking.docling_merging import (
    merge_tiny_chunks as _merge_tiny_chunks,
)
from raglite.ingestion.chunking.docling_processors import (
    create_text_chunks as _create_text_chunks,
)
from raglite.ingestion.chunking.docling_processors import (
    process_table_chunks as _process_table_chunks,
)
from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk, DocumentMetadata

if TYPE_CHECKING:
    import tiktoken
    from docling.document_converter import ConversionResult

logger = get_logger(__name__)


def _log_chunking_metrics(
    chunks: list[Chunk],
    table_chunk_count: int,
    doc_metadata: DocumentMetadata,
    encoding: tiktoken.Encoding,
    start_time: float,
) -> None:
    """Log chunking completion metrics.

    Args:
        chunks: Final list of chunks
        table_chunk_count: Number of table chunks
        doc_metadata: Document metadata
        encoding: tiktoken encoding
        start_time: Start time of chunking
    """
    duration_ms = int((time.time() - start_time) * 1000)
    avg_chunk_size = sum(c.word_count for c in chunks) / len(chunks) if chunks else 0
    token_counts = [len(encoding.encode(c.content)) for c in chunks]
    avg_tokens = sum(token_counts) / len(token_counts) if token_counts else 0

    logger.info(
        "Fixed 512-token chunking complete",
        extra={
            "doc_filename": doc_metadata.filename,
            "chunk_count": len(chunks),
            "table_chunks": table_chunk_count,
            "text_chunks": len(chunks) - table_chunk_count,
            "avg_chunk_size_words": round(avg_chunk_size, 1),
            "avg_chunk_size_tokens": round(avg_tokens, 1),
            "duration_ms": duration_ms,
        },
    )


async def chunk_by_docling_items(
    result: ConversionResult,
    doc_metadata: DocumentMetadata,
    chunk_size: int = 512,
    overlap: int = 50,
) -> list[Chunk]:
    """Chunk document using fixed 512-token approach with table-aware splitting.

    Story 2.5 Enhancement: Added table-aware chunking to split oversized tables.

    MODIFIED in Story 2.3: Replaced element-aware chunking with research-validated
    fixed 512-token chunking (Yepes et al. 2024: 68.09% accuracy on financial reports).

    Implements AC2 (Fixed 512-token chunking) and AC3 (Table boundary preservation).

    Args:
        result: Docling ConversionResult containing document with provenance
        doc_metadata: Document metadata (filename, doc_type, etc.)
        chunk_size: Target chunk size in tokens (default: 512 as per AC2)
        overlap: Token overlap between chunks (default: 50 as per AC2)

    Returns:
        List of Chunk objects with fixed 512-token size

    Raises:
        RuntimeError: If chunking fails

    Strategy (Story 2.3 AC2, AC3):
        1. Extract tables as separate items (preserve table boundaries - AC3)
        2. Extract text content from non-table elements
        3. Tokenize using tiktoken cl100k_base (AC2)
        4. Create 512-token chunks with 50-token overlap (AC2)
        5. Preserve sentence boundaries when possible (AC2)
        6. Keep tables as single chunks even if >512 tokens (AC3 exception)
    """
    from raglite.ingestion.chunking.core import _get_tiktoken_encoding

    start_time = time.time()

    # Lazy-load tiktoken encoding
    encoding = _get_tiktoken_encoding()
    if encoding is None:
        raise RuntimeError("tiktoken not available - required for Story 2.3 fixed chunking")

    logger.info(
        "Starting fixed 512-token chunking",
        extra={
            "doc_filename": doc_metadata.filename,
            "chunk_size": chunk_size,
            "overlap": overlap,
        },
    )

    chunk_index = 0

    # Extract tables and text items
    tables, text_items = _extract_tables_and_text(result)

    # Process table chunks
    table_chunks, chunk_index = _process_table_chunks(
        tables=tables,
        result=result,
        encoding=encoding,
        doc_metadata=doc_metadata,
        chunk_index=chunk_index,
    )

    # Build page mapping and concatenate text
    full_text, page_mapping = _build_page_mapping(text_items, encoding)

    # Create text chunks
    text_chunks, chunk_index = _create_text_chunks(
        full_text=full_text,
        page_mapping=page_mapping,
        encoding=encoding,
        doc_metadata=doc_metadata,
        chunk_size=chunk_size,
        overlap=overlap,
        chunk_index=chunk_index,
    )

    # Combine table and text chunks
    chunks = table_chunks + text_chunks

    # Merge tiny chunks to reduce variance
    chunks = _merge_tiny_chunks(
        chunks=chunks,
        table_chunk_count=len(table_chunks),
        encoding=encoding,
        chunk_size=chunk_size,
        doc_metadata=doc_metadata,
    )

    # Log completion metrics
    _log_chunking_metrics(chunks, len(table_chunks), doc_metadata, encoding, start_time)

    return chunks
