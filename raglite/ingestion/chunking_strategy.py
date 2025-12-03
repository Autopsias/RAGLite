"""Chunking strategy for document segmentation.

Handles text and table-aware chunking with token counting.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk, DocumentMetadata

logger = get_logger(__name__)

# Initialize tiktoken encoding for token counting (Story 2.3 AC2)
# Using cl100k_base encoding as specified in research (Yepes et al. 2024)
encoding: Encoding | None = None  # Forward reference to avoid import errors
try:
    import tiktoken
    from tiktoken import Encoding

    encoding = tiktoken.get_encoding("cl100k_base")
except ImportError:
    logger.warning(
        "tiktoken not installed - token counting will be approximate",
        extra={"fallback": "word count estimation"},
    )


async def chunk_document(
    full_text: str,
    doc_metadata: DocumentMetadata,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    """Chunk document content into semantic segments for embedding.

    .. deprecated:: Story 1.13
        For PDF documents, use chunk_by_docling_items() instead to extract actual
        page numbers from Docling provenance. This function is kept for Excel
        extraction only, which doesn't have provenance metadata.

    DEPRECATION NOTICE (Story 1.13):
        - Used by Excel extraction only (extract_excel)
        - PDF ingestion now uses chunk_by_docling_items() for accurate page numbers
        - TODO: Refactor Excel chunking in future story to use similar approach

    Uses word-based sliding window with overlap. Estimates page numbers based on
    character position within the document (INACCURATE for PDFs - see deprecation).

    Args:
        full_text: Complete document text (from PDF or Excel extraction)
        doc_metadata: Document metadata for provenance
        chunk_size: Target chunk size in words (default: 500)
        overlap: Word overlap between consecutive chunks (default: 50)

    Returns:
        List of Chunk objects with content, page numbers, and metadata

    Raises:
        ValueError: If chunk_size or overlap parameters are invalid

    Example:
        >>> metadata = DocumentMetadata(filename="report.pdf", doc_type="PDF", page_count=10, ...)
        >>> chunks = await chunk_document("Full document text here...", metadata)
        >>> assert all(chunk.page_number > 0 for chunk in chunks)

    Strategy:
        - 500 words per chunk with 50-word overlap
        - Preserve page numbers (estimate from character position)
        - Respect paragraph boundaries where possible
        - Keep tables within single chunks (detect via markdown)
        - Generate unique chunk_id per chunk

    Note:
        This function is declared async for consistency with the ingestion pipeline
        pattern (ingest_pdf, extract_excel), enabling future async optimizations
        such as parallel embedding generation. Current implementation is synchronous.
    """
    start_time = time.time()

    # Validate parameters
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got: {chunk_size}")
    if overlap < 0:
        raise ValueError(f"overlap must be non-negative, got: {overlap}")
    if overlap >= chunk_size:
        raise ValueError(f"overlap ({overlap}) must be less than chunk_size ({chunk_size})")

    logger.info(
        "Chunking document",
        extra={
            "doc_filename": doc_metadata.filename,
            "text_length": len(full_text),
            "chunk_size": chunk_size,
            "overlap": overlap,
        },
    )

    # Handle empty document
    if not full_text or not full_text.strip():
        logger.warning(
            "Empty document provided for chunking",
            extra={"doc_filename": doc_metadata.filename},
        )
        return []

    # Split into words
    words = full_text.split()

    # Handle document shorter than chunk size
    if len(words) <= chunk_size:
        # Single chunk for short document
        estimated_page = 1 if doc_metadata.page_count > 0 else 0
        chunk = Chunk(
            chunk_id=f"{doc_metadata.filename}_0",
            content=full_text.strip(),
            metadata=doc_metadata,
            page_number=estimated_page,
            chunk_index=0,
            embedding=[],
        )
        logger.info(
            "Document shorter than chunk size - created single chunk",
            extra={"doc_filename": doc_metadata.filename, "word_count": len(words)},
        )
        return [chunk]

    chunks = []

    # Calculate estimated chars per page for page number estimation
    # Avoid division by zero if page_count is 0
    estimated_chars_per_page = len(full_text) / max(doc_metadata.page_count, 1)

    idx = 0
    chunk_index = 0

    while idx < len(words):
        # Extract chunk words
        chunk_words = words[idx : idx + chunk_size]
        chunk_text = " ".join(chunk_words)

        # Estimate page number based on character position
        # Calculate position of the start of this chunk in the original text
        char_pos = len(" ".join(words[:idx]))

        # Estimate page number (1-indexed)
        estimated_page = int(char_pos / estimated_chars_per_page) + 1
        estimated_page = min(estimated_page, doc_metadata.page_count)  # Cap at max pages
        estimated_page = max(estimated_page, 1)  # Ensure at least page 1

        # Create Chunk object
        chunk = Chunk(
            chunk_id=f"{doc_metadata.filename}_{chunk_index}",
            content=chunk_text,
            metadata=doc_metadata,
            page_number=estimated_page,
            chunk_index=chunk_index,
            embedding=[],  # Populated later by Story 1.5
        )
        chunks.append(chunk)

        # Move to next chunk with overlap
        idx += chunk_size - overlap
        chunk_index += 1

    # Calculate metrics
    duration_ms = int((time.time() - start_time) * 1000)
    avg_chunk_size = sum(len(c.content.split()) for c in chunks) / len(chunks) if chunks else 0

    logger.info(
        "Document chunked successfully",
        extra={
            "doc_filename": doc_metadata.filename,
            "chunk_count": len(chunks),
            "avg_chunk_size": round(avg_chunk_size, 1),
            "duration_ms": duration_ms,
        },
    )

    return chunks


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

    start_time = time.time()

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
            if idx + chunk_size < total_tokens and len(chunk_text) > 50:
                # Look for sentence-ending punctuation near the end
                last_50_chars = chunk_text[-50:]
                sentence_end_positions = [
                    last_50_chars.rfind(". "),
                    last_50_chars.rfind("! "),
                    last_50_chars.rfind("? "),
                    last_50_chars.rfind(".\n"),
                ]
                max_pos = max(sentence_end_positions)

                if max_pos > 0:
                    # Trim to sentence boundary
                    cut_position = len(chunk_text) - 50 + max_pos + 1
                    chunk_text = chunk_text[:cut_position].strip()

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
            idx += chunk_size - overlap

    # Story 2.3 AC6 FIX: Merge tiny text chunks to reduce variance
    # Problem: Sentence boundary trimming creates orphan chunks <100 tokens
    # Solution: Merge tiny chunks with previous chunk (or next if first chunk)
    MIN_CHUNK_TOKENS = 100  # Minimum viable chunk size

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
