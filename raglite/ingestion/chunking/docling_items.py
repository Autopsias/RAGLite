"""Docling-based document chunking with provenance tracking.

Handles PDF chunking using Docling ConversionResult with accurate page numbers.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk, DocumentMetadata

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult

logger = get_logger(__name__)


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
    # Lazy import TableItem: Only needed when chunking documents, not at module load
    from docling_core.types.doc import TableItem

    # Import from core module for tiktoken encoding
    from raglite.ingestion.chunking.core import _get_tiktoken_encoding

    # Import table splitting function
    from raglite.ingestion.chunking.table_splitting import split_large_table_by_rows

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

    chunks = []
    chunk_index = 0

    # Story 2.8 AC1: Extract tables separately to preserve table boundaries
    tables: list[tuple[TableItem, int]] = []  # (table_item, page_number)
    text_items: list[tuple[str, int]] = []  # (text_content, page_number)

    for item, _ in result.document.iterate_items():
        # Get page number from provenance
        page_number = 1  # Default fallback
        if hasattr(item, "prov") and item.prov:
            page_number = item.prov[0].page_no

        if isinstance(item, TableItem):
            # Story 2.8 AC1: Store tables separately to preserve table boundaries
            tables.append((item, page_number))
        elif hasattr(item, "text"):
            # Text content (paragraphs, sections, lists)
            text_items.append((item.text, page_number))

    # Story 2.8 AC1 + AC2: Process tables with 4096-token threshold and row-based splitting
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

            # Story 2.8 AC1: Set section_type='Table' metadata for table chunks
            chunk = Chunk(
                chunk_id=f"{doc_metadata.filename}_{chunk_index}",
                content=chunk_content,
                metadata=doc_metadata,
                page_number=page_num,
                chunk_index=chunk_index,
                embedding=[],
                word_count=word_count,
                section_type="Table",  # AC1: Mark as table chunk
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

    # Process text content with fixed 512-token chunking (AC2)
    # Build page number mapping for accurate attribution (Story 2.3 P1-ENHANCE fix)
    # Track token ranges → page numbers during concatenation
    page_mapping: list[tuple[int, int, int]] = []  # (token_start, token_end, page_number)
    full_text_parts: list[str] = []
    current_token_offset = 0

    for text_content, page_num in text_items:
        if text_content.strip():
            # Tokenize this text item
            item_tokens = encoding.encode(text_content)
            item_token_count = len(item_tokens)

            # Record page mapping: [start_token, end_token) → page_number
            page_mapping.append(
                (
                    current_token_offset,
                    current_token_offset + item_token_count,
                    page_num,
                )
            )

            full_text_parts.append(text_content)
            current_token_offset += item_token_count

            # Add separator tokens (2 newlines = ~1-2 tokens)
            separator_tokens = encoding.encode("\n\n")
            current_token_offset += len(separator_tokens)

    full_text = "\n\n".join(full_text_parts)

    if full_text.strip():
        # Tokenize full text
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

        # Create chunks with sliding window
        idx = 0
        while idx < total_tokens:
            # Extract chunk tokens
            chunk_tokens = tokens[idx : idx + chunk_size]
            chunk_text = encoding.decode(chunk_tokens)

            # AC2: Preserve sentence boundaries when possible
            # If not at the end, try to end at a sentence boundary
            # FIXED: Ensure trimming doesn't create chunks that are too small (causes high variance)
            if idx + chunk_size < total_tokens and len(chunk_text) > 50:
                # Look for sentence-ending punctuation near the end
                last_100_chars = chunk_text[-100:]  # Increased search range
                sentence_end_positions = [
                    last_100_chars.rfind(". "),
                    last_100_chars.rfind("! "),
                    last_100_chars.rfind("? "),
                    last_100_chars.rfind(".\n"),
                ]
                max_pos = max(sentence_end_positions)

                if max_pos > 0:
                    # Calculate what the trimmed chunk size would be
                    cut_position = len(chunk_text) - 100 + max_pos + 1
                    trimmed_text = chunk_text[:cut_position].strip()
                    trimmed_tokens = len(encoding.encode(trimmed_text))

                    # Only trim if it doesn't make the chunk too small (causes high variance)
                    # Minimum chunk size should be at least 75% of target (384 tokens for 512 target)
                    MIN_TRIMMED_SIZE = int(chunk_size * 0.75)

                    if trimmed_tokens >= MIN_TRIMMED_SIZE:
                        # Safe to trim - chunk remains reasonably sized
                        chunk_text = trimmed_text
                    else:
                        # Trimming would make chunk too small - keep original size
                        # This prevents creating tiny chunks that increase variance
                        pass

            # Story 2.3 P1-ENHANCE: Accurate page number from provenance mapping
            # Find the page number for this chunk's starting token position
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
                page_number=chunk_page,  # Story 2.3: Accurate page from provenance mapping
                chunk_index=chunk_index,
                embedding=[],
                word_count=word_count,
            )
            chunks.append(chunk)
            chunk_index += 1

            # Advance with overlap (AC2: 50-token overlap)
            # IMPROVED: Adjust overlap based on actual chunk size to maintain consistency
            actual_chunk_tokens = len(encoding.encode(chunk_text))

            # If chunk was trimmed significantly, reduce overlap proportionally
            # This helps maintain consistent stride and reduces variance
            if actual_chunk_tokens < chunk_size * 0.85:
                # Chunk was trimmed - reduce overlap proportionally
                adjusted_overlap = max(10, int(overlap * (actual_chunk_tokens / chunk_size)))
                idx += chunk_size - adjusted_overlap
            else:
                # Normal chunk - use standard overlap
                idx += chunk_size - overlap

    # Story 2.3 AC6 FIX: Merge tiny text chunks to reduce variance
    # Problem: Sentence boundary trimming creates orphan chunks <100 tokens
    # Solution: Merge tiny chunks with previous chunk (or next if first chunk)
    # IMPROVED: Also merge chunks that are much smaller than target to reduce variance
    MIN_CHUNK_TOKENS = 100  # Minimum viable chunk size
    SMALL_CHUNK_THRESHOLD = 256  # Chunks smaller than this are candidates for merging

    # Separate table chunks from text chunks for filtering
    table_chunk_count = len(tables)  # Tables were added first
    text_chunks_only = chunks[table_chunk_count:]  # Text chunks come after tables

    if text_chunks_only:
        # Filter and merge tiny text chunks
        merged_text_chunks: list[Chunk] = []
        i = 0
        while i < len(text_chunks_only):
            current_chunk = text_chunks_only[i]
            current_token_count = len(encoding.encode(current_chunk.content))

            # If chunk is tiny and we have a previous chunk to merge with
            if current_token_count < MIN_CHUNK_TOKENS and merged_text_chunks:
                # Merge with previous chunk
                prev_chunk = merged_text_chunks[-1]
                merged_content = prev_chunk.content + "\n\n" + current_chunk.content
                prev_chunk.content = merged_content
                prev_chunk.word_count = len(merged_content.split())

                logger.debug(
                    "Merged tiny text chunk with previous chunk",
                    extra={
                        "tiny_chunk_tokens": current_token_count,
                        "merged_chunk_tokens": len(encoding.encode(merged_content)),
                        "chunk_index": current_chunk.chunk_index,
                    },
                )
            # If chunk is small (not tiny) and next chunk exists, consider merging
            # This helps reduce variance by balancing chunk sizes
            elif (
                SMALL_CHUNK_THRESHOLD <= current_token_count < chunk_size * 0.85
                and i + 1 < len(text_chunks_only)
                and not merged_text_chunks
            ):
                # Small first chunk - merge with next to avoid tiny first chunk
                next_chunk = text_chunks_only[i + 1]
                next_token_count = len(encoding.encode(next_chunk.content))

                # Only merge if combined size is reasonable (not too large)
                combined_tokens = current_token_count + next_token_count
                if combined_tokens <= chunk_size * 1.25:  # Allow 25% over target
                    merged_content = current_chunk.content + "\n\n" + next_chunk.content
                    next_chunk.content = merged_content
                    next_chunk.word_count = len(merged_content.split())
                    # Skip current chunk, keep next (which now has merged content)
                    i += 1
                    merged_text_chunks.append(next_chunk)

                    logger.debug(
                        "Merged small first chunk with next chunk",
                        extra={
                            "current_tokens": current_token_count,
                            "next_tokens": next_token_count,
                            "combined_tokens": combined_tokens,
                            "chunk_index": current_chunk.chunk_index,
                        },
                    )
                else:
                    # Combined too large - keep as separate chunks
                    merged_text_chunks.append(current_chunk)
            # If chunk is tiny and first chunk, try to merge with next
            elif current_token_count < MIN_CHUNK_TOKENS and i + 1 < len(text_chunks_only):
                # Merge with next chunk
                next_chunk = text_chunks_only[i + 1]
                merged_content = current_chunk.content + "\n\n" + next_chunk.content
                next_chunk.content = merged_content
                next_chunk.word_count = len(merged_content.split())
                # Skip current chunk, keep next (which now has merged content)
                i += 1
                merged_text_chunks.append(next_chunk)

                logger.debug(
                    "Merged tiny text chunk with next chunk",
                    extra={
                        "tiny_chunk_tokens": current_token_count,
                        "merged_chunk_tokens": len(encoding.encode(merged_content)),
                        "chunk_index": current_chunk.chunk_index,
                    },
                )
            else:
                # Normal-sized chunk or orphan at end (keep as-is)
                merged_text_chunks.append(current_chunk)

            i += 1

        # Rebuild chunks list: tables first (unchanged), then merged text chunks
        chunks = chunks[:table_chunk_count] + merged_text_chunks

        # Reindex chunks after merging
        for idx, chunk in enumerate(chunks):
            chunk.chunk_index = idx
            chunk.chunk_id = f"{doc_metadata.filename}_{idx}"

    # Calculate metrics
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

    return chunks
