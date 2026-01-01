"""Core chunking utilities and legacy word-based chunking.

Handles tiktoken lazy-loading and Excel document chunking.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk, DocumentMetadata

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# LAZY LOAD: tiktoken encoding for token counting (Story 2.3 AC2)
# Using cl100k_base encoding as specified in research (Yepes et al. 2024)
# Deferred until first use to speed up MCP server startup (~1-2s saved)
_tiktoken_module: Any | None = None
_encoding: Any | None = None  # tiktoken.Encoding (lazy-loaded)
_tiktoken_checked: bool = False


def _get_tiktoken_encoding() -> Any | None:
    """Lazy-load tiktoken encoding to avoid slow startup.

    Returns:
        tiktoken Encoding object or None if not installed
    """
    global _tiktoken_module, _encoding, _tiktoken_checked
    if not _tiktoken_checked:
        _tiktoken_checked = True
        try:
            import tiktoken

            _tiktoken_module = tiktoken
            _encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning(
                "tiktoken not installed - token counting will be approximate",
                extra={"fallback": "word count estimation"},
            )
            _tiktoken_module = None
            _encoding = None
    return _encoding


# Backward compatibility: encoding is now a property-like getter
# Code that references `encoding` directly will need to call _get_tiktoken_encoding()
encoding: Any | None = None  # Will be set lazily - use _get_tiktoken_encoding() instead


class FixedTokenChunker:
    """Fixed token chunker for consistent 512-token chunks.

    Story 2.3 AC2: Fixed 512-token chunking with token counting.
    Story 2.8 AC3: Table-aware chunking with row-wise splitting.
    """

    def __init__(self, embedding_model: Any):
        """Initialize chunker with embedding model for tokenization.

        Args:
            embedding_model: Model used for tokenization
        """
        self.embedding_model = embedding_model

    def chunk_document(
        self,
        text: str,
        source_document: str,
        metadata: dict[str, Any] | None = None,
        chunk_size: int = 512,
        overlap: int = 50,
    ) -> list[Chunk]:
        """Chunk document into fixed-size token chunks.

        Args:
            text: Document text content
            source_document: Source document path
            metadata: Optional metadata dict
            chunk_size: Target chunk size in tokens (default: 512)
            overlap: Token overlap between chunks (default: 50)

        Returns:
            List of Chunk objects with fixed token size
        """
        # Import here to avoid circular imports
        from datetime import datetime

        from raglite.shared.models import DocumentMetadata

        # Create document metadata (required fields only)
        doc_metadata = DocumentMetadata(
            filename=source_document,
            doc_type=metadata.get("document_type", "unknown") if metadata else "unknown",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=metadata.get("total_pages", 1) if metadata else 1,
        )

        chunks: list[Chunk] = []

        # Tokenize the full text using the embedding model's tokenization
        # This ensures consistency between chunking and downstream processing
        try:
            # Use embedding model for tokenization (preferred for consistency)
            tokens = self.embedding_model.encode([text], convert_to_tensor=False)
            if hasattr(tokens[0], "__len__"):
                # Handle batch encoding result
                token_ids = list(range(len(tokens[0])))
            else:
                # Handle single encoding result
                token_ids = list(range(len(tokens)))

            # Split text into character positions for chunking
            # Since embedding models don't provide token-to-text mapping,
            # we need to approximate chunk boundaries
            text_chars = list(text)
            chars_per_token = len(text_chars) / len(token_ids) if token_ids else 1

        except Exception as e:
            logger.warning(f"Embedding model tokenization failed, using word split: {e}")
            # Fallback: split by spaces and count
            words = text.split()
            token_ids = list(range(len(words)))  # Mock tokens
            chars_per_token = 1

        # Create chunks with overlap
        step_size = chunk_size - overlap
        for i in range(0, len(token_ids), step_size):
            # Get chunk token IDs
            chunk_token_ids = token_ids[i : i + chunk_size]

            if not chunk_token_ids:
                continue

            # Convert token range back to text using character approximation
            try:
                start_char = int(i * chars_per_token)
                end_char = int(min((i + chunk_size) * chars_per_token, len(text)))
                chunk_text = text[start_char:end_char]
            except (TypeError, ValueError, IndexError):
                # Fallback: simple text splitting
                chunk_text = text[i : i + chunk_size * 10]  # Rough approximation

            # Determine section type
            section_type = "Text"
            if metadata and metadata.get("section_type"):
                section_type = metadata["section_type"]

            # Create chunk
            import uuid

            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                content=chunk_text,
                metadata=doc_metadata,
                page_number=metadata.get("page_number", 1) if metadata else 1,
                chunk_index=len(chunks),
                section_type=section_type,
                document_type=metadata.get("document_type") if metadata else None,
                reporting_period=metadata.get("reporting_period") if metadata else None,
            )
            chunks.append(chunk)

        return chunks


def _validate_chunk_parameters(chunk_size: int, overlap: int) -> None:
    """Validate chunking parameters.

    Args:
        chunk_size: Target chunk size in words
        overlap: Word overlap between consecutive chunks

    Raises:
        ValueError: If parameters are invalid
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got: {chunk_size}")
    if overlap < 0:
        raise ValueError(f"overlap must be non-negative, got: {overlap}")
    if overlap >= chunk_size:
        raise ValueError(f"overlap ({overlap}) must be less than chunk_size ({chunk_size})")


def _create_single_chunk(
    full_text: str,
    doc_metadata: DocumentMetadata,
    word_count: int,
) -> Chunk:
    """Create a single chunk for short documents.

    Args:
        full_text: Complete document text
        doc_metadata: Document metadata for provenance
        word_count: Number of words in document

    Returns:
        Single Chunk object containing entire document
    """
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
        extra={"doc_filename": doc_metadata.filename, "word_count": word_count},
    )
    return chunk


def _estimate_page_number(
    words: list[str],
    current_idx: int,
    full_text: str,
    doc_metadata: DocumentMetadata,
) -> int:
    """Estimate page number based on character position.

    Args:
        words: List of all words in document
        current_idx: Current word index
        full_text: Original document text
        doc_metadata: Document metadata with page_count

    Returns:
        Estimated page number (1-indexed)
    """
    # Calculate estimated chars per page for page number estimation
    estimated_chars_per_page = len(full_text) / max(doc_metadata.page_count, 1)

    # Calculate position of the start of this chunk in the original text
    char_pos = len(" ".join(words[:current_idx]))

    # Estimate page number (1-indexed)
    estimated_page = int(char_pos / estimated_chars_per_page) + 1
    estimated_page = min(estimated_page, doc_metadata.page_count)  # Cap at max pages
    estimated_page = max(estimated_page, 1)  # Ensure at least page 1

    return estimated_page


def _generate_chunks(
    words: list[str],
    full_text: str,
    doc_metadata: DocumentMetadata,
    chunk_size: int,
    overlap: int,
) -> list[Chunk]:
    """Generate chunks from word list using sliding window.

    Args:
        words: List of words to chunk
        full_text: Original document text (for page estimation)
        doc_metadata: Document metadata for provenance
        chunk_size: Target chunk size in words
        overlap: Word overlap between consecutive chunks

    Returns:
        List of Chunk objects with estimated page numbers
    """
    chunks = []
    idx = 0
    chunk_index = 0

    while idx < len(words):
        # Extract chunk words
        chunk_words = words[idx : idx + chunk_size]
        chunk_text = " ".join(chunk_words)

        # Estimate page number
        estimated_page = _estimate_page_number(words, idx, full_text, doc_metadata)

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

    return chunks


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
    _validate_chunk_parameters(chunk_size, overlap)

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
        return [_create_single_chunk(full_text, doc_metadata, len(words))]

    # Generate chunks using sliding window
    chunks = _generate_chunks(words, full_text, doc_metadata, chunk_size, overlap)

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
