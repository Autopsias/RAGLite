"""Document ingestion pipeline for PDFs and Excel files.

Extracts text, tables, and page numbers from financial documents with high accuracy.
"""

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import openpyxl
import pandas as pd
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import ConversionResult, DocumentConverter, PdfFormatOption
from docling_core.types.doc import (
    DocItem,
    ListItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
)
from qdrant_client.models import (
    Distance,
    PointStruct,
    SparseIndexParams,
    SparseVectorParams,
    VectorParams,
)

from raglite.shared.bm25 import create_bm25_index, save_bm25_index
from raglite.shared.clients import get_embedding_model, get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk, DocumentElement, DocumentMetadata, ElementType

logger = get_logger(__name__)

# Initialize tiktoken encoding for token counting (Story 2.2)
try:
    import tiktoken

    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
except ImportError:
    logger.warning(
        "tiktoken not installed - token counting will be approximate",
        extra={"fallback": "word count estimation"},
    )
    encoding = None


# Exception classes
class EmbeddingGenerationError(Exception):
    """Raised when embedding generation fails."""

    pass


class VectorStorageError(Exception):
    """Raised when vector storage to Qdrant fails."""

    pass


def extract_elements(doc_result: ConversionResult) -> list[DocumentElement]:
    """Extract structured elements from Docling parsing result.

    Iterates through Docling document items and converts them to
    DocumentElement objects with type, content, and metadata. Tracks
    parent section headers for context attribution.

    Args:
        doc_result: Docling conversion result with parsed document

    Returns:
        List of DocumentElement objects sorted by page/position

    Strategy:
        - Use doc_result.document.iterate_items() to traverse elements
        - Map Docling types to ElementType enum (table, section_header, paragraph, list)
        - Track parent section headers for context
        - Count tokens for chunking decisions using tiktoken
        - Extract page numbers from provenance metadata

    Example:
        >>> doc_result = converter.convert("report.pdf")
        >>> elements = extract_elements(doc_result)
        >>> elements[0].type
        ElementType.TABLE

    Implementation Notes (Story 2.2 AC1):
        - Tables detected via TableItem → ElementType.TABLE
        - Section headers via SectionHeaderItem → ElementType.SECTION_HEADER
        - Paragraphs via TextItem → ElementType.PARAGRAPH
        - Lists via ListItem → ElementType.LIST
        - Unknown types → ElementType.PARAGRAPH (fallback)
    """
    elements: list[DocumentElement] = []
    current_section = None

    for item, _ in doc_result.document.iterate_items():
        # Determine element type via Docling type mapping
        if isinstance(item, TableItem):
            element_type = ElementType.TABLE
            content = item.export_to_markdown()
        elif isinstance(item, SectionHeaderItem):
            element_type = ElementType.SECTION_HEADER
            content = item.text if hasattr(item, "text") else str(item)
            current_section = content  # Update section context
        elif isinstance(item, TextItem):
            element_type = ElementType.PARAGRAPH
            content = item.text if hasattr(item, "text") else str(item)
        elif isinstance(item, ListItem):
            element_type = ElementType.LIST
            content = (
                item.export_to_markdown() if hasattr(item, "export_to_markdown") else str(item)
            )
        else:
            # Unknown element type - treat as paragraph with warning
            element_type = ElementType.PARAGRAPH
            content = str(item)
            logger.debug(
                "Unknown Docling element type - treating as paragraph",
                extra={"type": type(item).__name__, "has_text": hasattr(item, "text")},
            )

        # Get page number from provenance (first page if spans multiple)
        page_number = 1  # Default fallback
        if hasattr(item, "prov") and item.prov:
            page_number = item.prov[0].page_no

        # Count tokens for chunking decisions
        if encoding is not None:
            try:
                token_count = len(encoding.encode(content))
            except Exception as e:
                # Fallback to word count * 1.3 (rough approximation)
                token_count = int(len(content.split()) * 1.3)
                logger.debug(
                    "Token counting failed - using word count approximation",
                    extra={"error": str(e), "element_id": len(elements)},
                )
        else:
            # Fallback: word count * 1.3 (rough token approximation)
            token_count = int(len(content.split()) * 1.3)

        # Generate unique element ID
        element_id = f"elem_{len(elements)}"
        if isinstance(item, DocItem) and hasattr(item, "self_ref"):
            element_id = str(item.self_ref)

        elements.append(
            DocumentElement(
                element_id=element_id,
                type=element_type,
                content=content,
                page_number=page_number,
                section_title=current_section,
                token_count=token_count,
                metadata={"docling_type": type(item).__name__},
            )
        )

    logger.info(
        "Extracted elements from document",
        extra={
            "total_elements": len(elements),
            "tables": sum(1 for e in elements if e.type == ElementType.TABLE),
            "sections": sum(1 for e in elements if e.type == ElementType.SECTION_HEADER),
            "paragraphs": sum(1 for e in elements if e.type == ElementType.PARAGRAPH),
            "lists": sum(1 for e in elements if e.type == ElementType.LIST),
        },
    )

    return elements


def chunk_elements(
    elements: list[DocumentElement],
    doc_metadata: DocumentMetadata,
    max_tokens: int = 512,
    overlap_tokens: int = 128,
) -> list[Chunk]:
    """Create chunks respecting element boundaries.

    Implements structure-aware chunking that preserves semantic coherence
    by respecting element boundaries (tables, sections, paragraphs).

    Args:
        elements: List of DocumentElement from Docling
        doc_metadata: Document metadata for chunk provenance
        max_tokens: Target chunk size in tokens (default: 512)
        overlap_tokens: Overlap between chunks in tokens (default: 128)

    Returns:
        List of Chunk objects with element-type metadata

    Strategy (Story 2.2 AC1):
        1. Tables <2,048 tokens → single chunk (indivisible)
        2. Tables >2,048 tokens → split at row boundaries (parse Markdown)
        3. Section headers → group with first paragraph
        4. Paragraphs → accumulate until max_tokens, no mid-sentence splits
        5. Preserve section_title context for all chunks

    Example:
        >>> elements = extract_elements(doc_result)
        >>> chunks = chunk_elements(elements, metadata, max_tokens=512)
        >>> assert chunks[0].element_type in [ElementType.TABLE, ElementType.SECTION_HEADER, ...]

    Implementation Notes (Story 2.2):
        - AC1: Chunks MUST NOT split tables mid-row or section headers from content
        - AC2: Each chunk includes element_type and section_title metadata
        - AC4: Chunk count should be within 20% of baseline (321 ± 64 chunks)
    """
    chunks = []
    current_buffer: list[DocumentElement] = []
    current_tokens = 0
    current_section = None
    chunk_index = 0

    for elem in elements:
        # Update section context
        if elem.type == ElementType.SECTION_HEADER:
            current_section = elem.content

        # Strategy 1: Tables are indivisible (unless >2,048 tokens)
        if elem.type == ElementType.TABLE:
            # Use element's section_title if available, else current_section
            table_section_title = elem.section_title if elem.section_title else current_section

            if elem.token_count > 2048:
                # Large table - split at row boundaries
                logger.warning(
                    "Large table detected - splitting at row boundaries",
                    extra={"token_count": elem.token_count, "page": elem.page_number},
                )
                table_chunks = _split_large_table(elem, max_tokens=512)
                for table_chunk_content in table_chunks:
                    chunk = _create_chunk(
                        content=table_chunk_content,
                        element_type=ElementType.TABLE,
                        section_title=table_section_title,
                        page_number=elem.page_number,
                        chunk_index=chunk_index,
                        doc_metadata=doc_metadata,
                    )
                    chunks.append(chunk)
                    chunk_index += 1
            else:
                # Small/medium table - single chunk
                if current_buffer:
                    # Flush buffer first
                    chunk = _create_chunk_from_buffer(
                        buffer=current_buffer,
                        section_title=current_section,
                        chunk_index=chunk_index,
                        doc_metadata=doc_metadata,
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_buffer = []
                    current_tokens = 0

                # Store table as standalone chunk
                chunk = _create_chunk(
                    content=elem.content,
                    element_type=ElementType.TABLE,
                    section_title=table_section_title,
                    page_number=elem.page_number,
                    chunk_index=chunk_index,
                    doc_metadata=doc_metadata,
                )
                chunks.append(chunk)
                chunk_index += 1

        # Strategy 2: Section headers - group with first paragraph
        elif elem.type == ElementType.SECTION_HEADER:
            # Start new chunk with section header
            if current_buffer:
                chunk = _create_chunk_from_buffer(
                    buffer=current_buffer,
                    section_title=current_section,
                    chunk_index=chunk_index,
                    doc_metadata=doc_metadata,
                )
                chunks.append(chunk)
                chunk_index += 1
            current_buffer = [elem]
            current_tokens = elem.token_count

        # Strategy 3: Paragraphs and lists - accumulate until limit
        else:
            if current_tokens + elem.token_count > max_tokens:
                # Flush buffer
                if current_buffer:
                    chunk = _create_chunk_from_buffer(
                        buffer=current_buffer,
                        section_title=current_section,
                        chunk_index=chunk_index,
                        doc_metadata=doc_metadata,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                # Start new chunk with overlap
                overlap_buffer = _get_overlap(current_buffer, overlap_tokens)
                current_buffer = overlap_buffer + [elem]
                current_tokens = sum(e.token_count for e in current_buffer)
            else:
                current_buffer.append(elem)
                current_tokens += elem.token_count

    # Flush final buffer
    if current_buffer:
        chunk = _create_chunk_from_buffer(
            buffer=current_buffer,
            section_title=current_section,
            chunk_index=chunk_index,
            doc_metadata=doc_metadata,
        )
        chunks.append(chunk)

    logger.info(
        "Created element-aware chunks",
        extra={
            "chunk_count": len(chunks),
            "avg_tokens": int(sum(c.word_count * 1.3 for c in chunks) / len(chunks))
            if chunks
            else 0,
            "table_chunks": sum(1 for c in chunks if c.element_type == ElementType.TABLE),
            "section_chunks": sum(
                1 for c in chunks if c.element_type == ElementType.SECTION_HEADER
            ),
            "mixed_chunks": sum(1 for c in chunks if c.element_type == ElementType.MIXED),
        },
    )

    return chunks


def _split_large_table(elem: DocumentElement, max_tokens: int) -> list[str]:
    """Split table >2,048 tokens at row boundaries.

    Parses Markdown table, preserves header row in each chunk, splits at row boundaries.
    Ensures no partial rows in any chunk.

    Args:
        elem: DocumentElement with type=TABLE and token_count >2,048
        max_tokens: Maximum tokens per chunk (default: 512)

    Returns:
        List of Markdown table strings, each with header row preserved

    Strategy (Story 2.2 AC1):
        - Parse Markdown table into header + rows
        - Preserve header row (first 2 lines: header + separator)
        - Split remaining rows across chunks
        - Each chunk includes header + N rows (no partial rows)
    """
    lines = elem.content.split("\n")
    if len(lines) < 3:
        # Table too small to split (header + separator only)
        return [elem.content]

    header = lines[0:2]  # Header row + separator (|---|---|)
    rows = lines[2:]

    chunks = []
    current_chunk = header.copy()
    current_tokens = (
        len(encoding.encode("\n".join(current_chunk))) if encoding else len(header) * 10
    )

    for row in rows:
        row_tokens = len(encoding.encode(row)) if encoding else len(row.split()) * 1.3
        if current_tokens + row_tokens > max_tokens and len(current_chunk) > 2:
            # Flush current chunk (only if it has data rows beyond header)
            chunks.append("\n".join(current_chunk))
            current_chunk = header.copy() + [row]
            current_tokens = int(
                len(encoding.encode("\n".join(current_chunk)))
                if encoding
                else (len(header) * 10 + row_tokens)
            )
        else:
            current_chunk.append(row)
            current_tokens += int(row_tokens)

    # Add final chunk if it has data beyond header
    if len(current_chunk) > 2:
        chunks.append("\n".join(current_chunk))

    logger.info(
        "Split large table into chunks",
        extra={
            "original_tokens": elem.token_count,
            "chunk_count": len(chunks),
            "original_rows": len(rows),
        },
    )

    return chunks


def _create_chunk_from_buffer(
    buffer: list[DocumentElement],
    section_title: str | None,
    chunk_index: int,
    doc_metadata: DocumentMetadata,
) -> Chunk:
    """Create Chunk from element buffer.

    Combines multiple elements into a single chunk, determines primary
    element type, and populates all required metadata fields.

    Args:
        buffer: List of DocumentElement objects to combine
        section_title: Parent section header for context
        chunk_index: Sequential chunk index
        doc_metadata: Document metadata for provenance

    Returns:
        Chunk object with combined content and metadata
    """
    content = "\n\n".join(e.content for e in buffer)

    # Determine primary element type
    element_counts: dict[ElementType, int] = {}
    for elem in buffer:
        element_counts[elem.type] = element_counts.get(elem.type, 0) + 1

    # Primary type = most frequent (or MIXED if multiple types tied)
    if len(element_counts) == 1:
        element_type = list(element_counts.keys())[0]
    else:
        # Multiple element types - mark as MIXED
        element_type = ElementType.MIXED

    # Page number = first element's page
    page_number = buffer[0].page_number

    # Word count for metadata
    word_count = len(content.split())

    return Chunk(
        chunk_id=f"{doc_metadata.filename}_{chunk_index}",
        content=content,
        metadata=doc_metadata,
        page_number=page_number,
        chunk_index=chunk_index,
        embedding=[],
        # Story 2.2 fields
        element_type=element_type,
        section_title=section_title,
        parent_chunk_id=None,
        word_count=word_count,
    )


def _create_chunk(
    content: str,
    element_type: ElementType,
    section_title: str | None,
    page_number: int,
    chunk_index: int,
    doc_metadata: DocumentMetadata,
) -> Chunk:
    """Create single Chunk from element content.

    Args:
        content: Element content (Markdown for tables, text for others)
        element_type: Element type classification
        section_title: Parent section header for context
        page_number: Page number where element appears
        chunk_index: Sequential chunk index
        doc_metadata: Document metadata for provenance

    Returns:
        Chunk object with element metadata
    """
    word_count = len(content.split())

    return Chunk(
        chunk_id=f"{doc_metadata.filename}_{chunk_index}",
        content=content,
        metadata=doc_metadata,
        page_number=page_number,
        chunk_index=chunk_index,
        embedding=[],
        # Story 2.2 fields
        element_type=element_type,
        section_title=section_title,
        parent_chunk_id=None,
        word_count=word_count,
    )


def _get_overlap(buffer: list[DocumentElement], overlap_tokens: int) -> list[DocumentElement]:
    """Get last N tokens from buffer for overlap.

    Selects elements from end of buffer until overlap token limit is reached.
    Used to create smooth transitions between chunks.

    Args:
        buffer: Current buffer of elements
        overlap_tokens: Target overlap size in tokens

    Returns:
        List of elements from end of buffer totaling ~overlap_tokens
    """
    overlap: list[DocumentElement] = []
    tokens = 0

    for elem in reversed(buffer):
        if tokens + elem.token_count <= overlap_tokens:
            overlap.insert(0, elem)
            tokens += elem.token_count
        else:
            break

    return overlap


async def generate_embeddings(chunks: list[Chunk]) -> list[Chunk]:
    """Generate Fin-E5 embeddings for document chunks.

    Processes chunks in batches of 32 for memory efficiency. Populates the
    embedding field of each Chunk with 1024-dimensional vectors.

    Args:
        chunks: List of Chunk objects from chunking pipeline

    Returns:
        Same list with embedding field populated (1024-dimensional vectors)

    Raises:
        EmbeddingGenerationError: If embedding generation fails

    Strategy:
        - Batch processing: 32 chunks per batch for memory efficiency
        - Fin-E5 model: intfloat/e5-large-v2 (1024 dimensions)
        - Model cached: Loaded once at module level, reused across calls
        - Empty chunks: Handled gracefully (skip or zero vector)
        - Performance: <2 minutes target for 300-chunk document

    Example:
        >>> chunks = await chunk_document("Document text...", metadata)
        >>> chunks_with_embeddings = await generate_embeddings(chunks)
        >>> assert all(len(c.embedding) == 1024 for c in chunks_with_embeddings)
    """
    start_time = time.time()

    logger.info(
        "Generating embeddings",
        extra={"chunk_count": len(chunks), "model": "intfloat/e5-large-v2"},
    )

    if not chunks:
        logger.warning("No chunks provided for embedding generation")
        return []

    # Load model (singleton pattern)
    model = get_embedding_model()
    batch_size = 32

    # Process in batches
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [chunk.content for chunk in batch]

        try:
            # Generate embeddings for batch
            embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)

            # Populate embedding field (convert numpy array to list for JSON serialization)
            for chunk, embedding in zip(batch, embeddings, strict=False):
                chunk.embedding = embedding.tolist()

            logger.info(
                f"Batch {i // batch_size + 1} complete",
                extra={
                    "batch_size": len(batch),
                    "embeddings_shape": str(embeddings.shape),
                    "batch_index": i // batch_size + 1,
                },
            )

        except Exception as e:
            error_msg = f"Failed to generate embeddings for batch {i // batch_size + 1}: {e}"
            logger.error(
                "Embedding generation failed for batch",
                extra={
                    "batch_index": i // batch_size + 1,
                    "batch_size": len(batch),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise EmbeddingGenerationError(error_msg) from e

    # Calculate final metrics
    duration_ms = int((time.time() - start_time) * 1000)
    embedding_dim = len(chunks[0].embedding) if chunks and chunks[0].embedding else 0

    logger.info(
        "Embedding generation complete",
        extra={
            "chunk_count": len(chunks),
            "dimensions": embedding_dim,
            "duration_ms": duration_ms,
            "chunks_per_second": round(len(chunks) / (duration_ms / 1000), 2)
            if duration_ms > 0
            else 0,
        },
    )

    return chunks


def create_collection(
    collection_name: str = "financial_docs",
    vector_size: int = 1024,
    distance: Distance = Distance.COSINE,
) -> None:
    """Create Qdrant collection if it doesn't exist.

    Checks for existing collection before creation to ensure idempotency.
    Configures collection with HNSW indexing (default) for optimal retrieval
    performance and COSINE distance for semantic similarity.

    Args:
        collection_name: Name of the collection (default: financial_docs)
        vector_size: Vector dimension (default: 1024 for Fin-E5)
        distance: Distance metric (default: COSINE for embeddings)

    Raises:
        VectorStorageError: If collection creation fails

    Strategy:
        - Check if collection exists (idempotent operation)
        - Create with HNSW indexing (default, O(log n) search complexity)
        - COSINE distance for semantic similarity (best for embeddings)
        - No manual index configuration needed (Qdrant uses optimal defaults)

    Example:
        >>> create_collection("financial_docs", vector_size=1024)
        >>> # Safe to call multiple times - won't error if exists
        >>> create_collection("financial_docs", vector_size=1024)
    """
    client = get_qdrant_client()

    try:
        # Check if collection exists
        collections = client.get_collections().collections
        existing = [c.name for c in collections]

        if collection_name in existing:
            logger.info(
                "Collection already exists",
                extra={"collection": collection_name, "status": "exists"},
            )
            return

        # Create collection with HNSW indexing (default) + sparse vectors for BM25
        logger.info(
            "Creating Qdrant collection",
            extra={
                "collection": collection_name,
                "vector_size": vector_size,
                "distance": distance.name,
                "indexing": "HNSW (default)",
                "sparse_vectors": "enabled (BM25)",
            },
        )

        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "text-dense": VectorParams(size=vector_size, distance=distance),
            },
            sparse_vectors_config={
                "text-sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False),
                )
            },
        )

        logger.info("Collection created successfully", extra={"collection": collection_name})

    except Exception as e:
        # If collection already exists (409 error), that's OK - don't raise error
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "409" in error_msg:
            logger.info(
                "Collection already exists",
                extra={"collection": collection_name, "status": "exists"},
            )
            return

        # For other errors, log and raise
        logger.error(
            "Collection creation failed",
            extra={"collection": collection_name, "error": error_msg},
            exc_info=True,
        )
        raise VectorStorageError(f"Failed to create collection {collection_name}: {e}") from e


async def store_vectors_in_qdrant(
    chunks: list[Chunk], collection_name: str = "financial_docs", batch_size: int = 100
) -> int:
    """Store document chunks with embeddings in Qdrant vector database.

    Processes chunks in batches for memory efficiency. Generates unique UUIDs for
    each point and stores all chunk metadata for retrieval and attribution.
    Creates and persists BM25 index for hybrid search (Story 2.1).

    Args:
        chunks: List of Chunk objects with embeddings from Story 1.5
        collection_name: Qdrant collection name (default: financial_docs)
        batch_size: Vectors per batch (default: 100 for memory efficiency)

    Returns:
        Number of points successfully stored in Qdrant

    Raises:
        VectorStorageError: If storage fails

    Strategy:
        - Ensure collection exists (create if needed)
        - Create BM25 index and save to disk (Story 2.1 AC1)
        - Batch upload: 100 vectors per batch to prevent memory issues
        - Generate unique UUID for each point (Qdrant requirement)
        - Store metadata: chunk_id, text, word_count, source_document, page_number, chunk_index
        - Validate: points_count == len(chunks) after storage
        - Performance target: <30 seconds for 300 chunks (AC10)

    Example:
        >>> chunks = await generate_embeddings(chunks)
        >>> points_stored = await store_vectors_in_qdrant(chunks)
        >>> assert points_stored == len(chunks)
    """
    start_time = time.time()

    logger.info(
        "Storing vectors in Qdrant",
        extra={
            "chunk_count": len(chunks),
            "collection": collection_name,
            "batch_size": batch_size,
        },
    )

    if not chunks:
        logger.warning("No chunks provided for storage", extra={"collection": collection_name})
        return 0

    # Ensure collection exists
    create_collection(collection_name, vector_size=settings.embedding_dimension)

    # Create BM25 index for hybrid search (Story 2.1 AC1.2)
    try:
        bm25, tokenized_docs = create_bm25_index(chunks, k1=1.7, b=0.6)

        # Create chunk metadata for BM25-to-Qdrant mapping
        chunk_metadata = [
            {
                "source_document": chunk.metadata.filename,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
            }
            for chunk in chunks
        ]

        save_bm25_index(bm25, tokenized_docs, chunk_metadata=chunk_metadata)
        logger.info(
            "BM25 index created and saved",
            extra={"chunk_count": len(chunks), "collection": collection_name},
        )
    except Exception as e:
        logger.warning(
            "BM25 index creation failed - continuing with semantic-only",
            extra={"error": str(e), "collection": collection_name},
        )

    client = get_qdrant_client()

    # Prepare points for upload
    points = []
    for chunk in chunks:
        if not chunk.embedding:
            logger.warning(
                "Chunk has no embedding, skipping",
                extra={"chunk_id": chunk.chunk_id, "collection": collection_name},
            )
            continue

        # Calculate word count from content (use chunk.word_count if available from Story 2.2)
        word_count = (
            chunk.word_count
            if hasattr(chunk, "word_count") and chunk.word_count > 0
            else len(chunk.content.split())
        )

        point = PointStruct(
            id=str(uuid.uuid4()),
            vector={"text-dense": chunk.embedding},  # Named vector for Story 2.1 sparse support
            payload={
                "chunk_id": chunk.chunk_id,
                "text": chunk.content,
                "word_count": word_count,
                "source_document": chunk.metadata.filename,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,  # Use explicit field from Chunk model
                # NEW FIELDS for Story 2.2: Element-aware chunking metadata
                "element_type": chunk.element_type.value
                if hasattr(chunk, "element_type")
                else "mixed",
                "section_title": chunk.section_title if hasattr(chunk, "section_title") else None,
            },
        )
        points.append(point)

    if not points:
        logger.warning(
            "No valid chunks with embeddings to store", extra={"collection": collection_name}
        )
        return 0

    # Upload in batches
    total_batches = (len(points) + batch_size - 1) // batch_size

    try:
        for i in range(0, len(points), batch_size):
            batch_num = (i // batch_size) + 1
            batch_points = points[i : i + batch_size]

            logger.info(
                f"Uploading batch {batch_num}/{total_batches}",
                extra={
                    "batch_num": batch_num,
                    "batch_size": len(batch_points),
                    "total_batches": total_batches,
                    "collection": collection_name,
                },
            )

            client.upsert(collection_name=collection_name, points=batch_points)

        # Verify storage (critical validation for AC9)
        collection_info = client.get_collection(collection_name)
        points_stored: int = collection_info.points_count or 0  # Handle None case

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Vector storage complete",
            extra={
                "points_stored": points_stored,
                "collection": collection_name,
                "duration_ms": duration_ms,
                "chunks_per_second": round(len(chunks) / (duration_ms / 1000), 2)
                if duration_ms > 0
                else 0,
            },
        )

        # Critical validation: points_count should match chunk_count (AC9)
        if points_stored < len(chunks):
            logger.warning(
                "Storage count mismatch - some chunks may not be stored",
                extra={
                    "expected": len(chunks),
                    "actual": points_stored,
                    "missing": len(chunks) - points_stored,
                },
            )

        return points_stored

    except Exception as e:
        logger.error(
            "Vector storage failed",
            extra={"collection": collection_name, "error": str(e)},
            exc_info=True,
        )
        raise VectorStorageError(f"Failed to store vectors in Qdrant: {e}") from e


async def ingest_document(file_path: str) -> DocumentMetadata:
    """Ingest financial document (PDF or Excel) with automatic format detection.

    Routes documents to appropriate extraction handler based on file extension.
    Supports PDF (.pdf) and Excel (.xlsx, .xls) formats.

    Args:
        file_path: Path to document file (relative or absolute)

    Returns:
        DocumentMetadata with extraction results

    Raises:
        FileNotFoundError: If document file doesn't exist
        RuntimeError: If parsing fails or format is unsupported
        ValueError: If file extension is not supported

    Example:
        >>> metadata = await ingest_document("reports/Q4_2024.pdf")
        >>> metadata = await ingest_document("data/financials.xlsx")
    """
    # Resolve file path to check extension
    doc_path = Path(file_path).resolve()

    if not doc_path.exists():
        error_msg = f"Document file not found: {file_path}"
        logger.error(
            "Document ingestion failed - file not found",
            extra={"path": str(doc_path), "error": error_msg},
        )
        raise FileNotFoundError(error_msg)

    # Route based on file extension
    extension = doc_path.suffix.lower()

    if extension == ".pdf":
        return await ingest_pdf(str(doc_path))
    elif extension in [".xlsx", ".xls"]:
        return await extract_excel(str(doc_path))
    else:
        error_msg = f"Unsupported file format: {extension}. Supported formats: .pdf, .xlsx, .xls"
        logger.error(
            "Unsupported document format",
            extra={"path": str(doc_path), "extension": extension},
        )
        raise ValueError(error_msg)


async def ingest_pdf(file_path: str, clear_collection: bool = True) -> DocumentMetadata:
    """Ingest financial PDF and extract text, tables, and structure with page numbers.

    Uses Docling library for high-accuracy extraction (97.9% table accuracy).
    Extracts page numbers from element provenance metadata.

    Args:
        file_path: Path to PDF file (relative or absolute)
        clear_collection: If True, clears existing Qdrant collection before ingestion
                         to prevent data contamination. Default True for clean state.

    Returns:
        DocumentMetadata with extraction results including page_count and ingestion timestamp

    Raises:
        FileNotFoundError: If PDF file doesn't exist at specified path
        RuntimeError: If Docling parsing fails or PDF is corrupted

    Example:
        >>> metadata = await ingest_pdf("docs/sample pdf/report.pdf")
        >>> print(f"Ingested {metadata.page_count} pages")

        >>> # Append to existing collection without clearing
        >>> metadata = await ingest_pdf("report2.pdf", clear_collection=False)
    """
    start_time = time.time()

    # Resolve file path
    pdf_path = Path(file_path).resolve()

    if not pdf_path.exists():
        error_msg = f"PDF file not found: {file_path}"
        logger.error(
            "PDF ingestion failed - file not found",
            extra={"path": str(pdf_path), "error": error_msg},
        )
        raise FileNotFoundError(error_msg)

    # Clear Qdrant collection if requested (Story 2.2 fix - prevent data contamination)
    if clear_collection:
        client = get_qdrant_client()
        try:
            client.delete_collection(settings.qdrant_collection_name)
            logger.info(
                "Cleared existing collection",
                extra={"collection": settings.qdrant_collection_name},
            )
        except Exception:
            logger.info(
                "Collection doesn't exist, will create new",
                extra={"collection": settings.qdrant_collection_name},
            )

        # Recreate collection with proper config (named vectors + sparse for BM25)
        try:
            client.create_collection(
                collection_name=settings.qdrant_collection_name,
                vectors_config={
                    "text-dense": VectorParams(size=1024, distance=Distance.COSINE),
                },
                sparse_vectors_config={
                    "text-sparse": SparseVectorParams(
                        index=SparseIndexParams(on_disk=False),
                    )
                },
            )
            logger.info(
                "Created fresh collection",
                extra={"collection": settings.qdrant_collection_name, "vector_size": 1024},
            )
        except Exception as e:
            logger.warning(
                "Collection may already exist",
                extra={"collection": settings.qdrant_collection_name, "error": str(e)},
            )

    logger.info(
        "Starting PDF ingestion",
        extra={
            "path": str(pdf_path),
            "doc_filename": pdf_path.name,
            "size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
            "clear_collection": clear_collection,
        },
    )

    # Initialize Docling converter with table extraction enabled (Story 1.15 fix)
    # Configure table structure recognition to extract table cell data
    # Story 2.1: Use pypdfium backend for 50-60% memory reduction
    try:
        pipeline_options = PdfPipelineOptions(do_table_structure=True)
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

        # Story 2.1: PyPdfium backend (optimized)
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options, backend=PyPdfiumDocumentBackend
                )
            }
        )
        logger.info(
            "Docling converter initialized with pypdfium backend and table extraction",
            extra={"table_mode": "ACCURATE", "backend": "pypdfium", "path": str(pdf_path)},
        )
    except Exception as e:
        error_msg = f"Failed to initialize Docling converter: {e}"
        logger.error(
            "Docling initialization failed",
            extra={"path": str(pdf_path), "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

    # Convert PDF with Docling
    try:
        result = converter.convert(str(pdf_path))
    except Exception as e:
        error_msg = f"Docling parsing failed for {pdf_path.name}: {e}"
        logger.error(
            "PDF parsing failed",
            extra={"path": str(pdf_path), "doc_filename": pdf_path.name, "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

    # Extract page count from DoclingDocument
    # Use num_pages() method which returns total page count
    page_count = result.document.num_pages()

    # Count elements with provenance data for metrics
    total_elements = 0
    elements_with_pages = 0

    for item, _ in result.document.iterate_items():
        total_elements += 1
        if hasattr(item, "prov") and item.prov:
            elements_with_pages += 1

    # Validate page extraction
    if page_count == 0:
        logger.warning(
            "No page numbers extracted - verify PDF structure",
            extra={"path": str(pdf_path), "total_elements": total_elements},
        )

    # Extract full text from Docling result
    # Use export_to_markdown() to get structured text with tables
    try:
        result.document.export_to_markdown()
    except Exception as e:
        logger.warning(
            "Failed to export markdown - falling back to plain text",
            extra={"path": str(pdf_path), "error": str(e)},
        )
        # Fallback: concatenate all text from elements
        "\n".join(item.text for item, _ in result.document.iterate_items() if hasattr(item, "text"))

    # Create initial metadata for chunking
    metadata = DocumentMetadata(
        filename=pdf_path.name,
        doc_type="PDF",
        ingestion_timestamp=datetime.now(UTC).isoformat(),
        page_count=page_count,
        source_path=str(pdf_path),
        chunk_count=0,  # Will be updated after chunking
    )

    # Chunk the document using Docling items with provenance (Story 1.13 fix)
    # This extracts actual page numbers from Docling metadata instead of estimating
    chunks = await chunk_by_docling_items(result, metadata)

    # Generate embeddings for chunks (Story 1.5)
    chunks_with_embeddings = await generate_embeddings(chunks)

    # Store vectors in Qdrant (Story 1.6)
    if chunks_with_embeddings:
        points_stored = await store_vectors_in_qdrant(
            chunks_with_embeddings, collection_name=settings.qdrant_collection_name
        )
        logger.info(
            "Vectors stored in Qdrant",
            extra={
                "doc_filename": pdf_path.name,
                "points_stored": points_stored,
                "collection": settings.qdrant_collection_name,
            },
        )

    # Update metadata with chunk count
    metadata.chunk_count = len(chunks_with_embeddings)

    # Calculate ingestion metrics
    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "PDF ingested successfully",
        extra={
            "doc_filename": pdf_path.name,
            "page_count": page_count,
            "chunk_count": len(chunks_with_embeddings),
            "total_elements": total_elements,
            "elements_with_pages": elements_with_pages,
            "duration_ms": duration_ms,
            "pages_per_second": (
                round(page_count / (duration_ms / 1000), 2) if duration_ms > 0 else 0
            ),
        },
    )

    return metadata


async def extract_excel(file_path: str) -> DocumentMetadata:
    """Extract financial data from Excel spreadsheet with multi-sheet support.

    Uses openpyxl for Excel parsing and pandas for data manipulation.
    Extracts all sheets preserving numeric formatting and sheet numbers for citations.

    Note: This function is marked async for consistency with the ingestion pipeline
    pattern (ingest_pdf, future chunking/embedding operations). While openpyxl and
    pandas operations are currently synchronous, this allows for future async
    enhancements like streaming large files or parallel sheet processing.

    Args:
        file_path: Path to Excel file (relative or absolute, .xlsx or .xls)

    Returns:
        DocumentMetadata with extraction results including sheet_count as page_count

    Raises:
        FileNotFoundError: If Excel file doesn't exist at specified path
        RuntimeError: If Excel parsing fails, file is password-protected, or corrupted

    Example:
        >>> metadata = await extract_excel("data/financial_report.xlsx")
        >>> print(f"Extracted {metadata.page_count} sheets")
    """
    start_time = time.time()

    # Resolve file path
    excel_path = Path(file_path).resolve()

    if not excel_path.exists():
        error_msg = f"Excel file not found: {file_path}"
        logger.error(
            "Excel extraction failed - file not found",
            extra={"path": str(excel_path), "error": error_msg},
        )
        raise FileNotFoundError(error_msg)

    logger.info(
        "Starting Excel extraction",
        extra={
            "path": str(excel_path),
            "doc_filename": excel_path.name,
            "size_mb": round(excel_path.stat().st_size / (1024 * 1024), 2),
        },
    )

    # Load Excel workbook
    try:
        # data_only=True: Load computed values instead of formulas
        workbook = openpyxl.load_workbook(str(excel_path), data_only=True)
    except openpyxl.utils.exceptions.InvalidFileException as e:
        error_msg = (
            f"Excel parsing failed for {excel_path.name}: Invalid or password-protected file"
        )
        logger.error(
            "Excel file is invalid or password-protected",
            extra={"path": str(excel_path), "doc_filename": excel_path.name, "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error loading Excel file {excel_path.name}: {e}"
        logger.error(
            "Excel loading failed",
            extra={"path": str(excel_path), "doc_filename": excel_path.name, "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

    # Check for empty workbook
    if not workbook.sheetnames:
        logger.warning(
            "Empty Excel workbook - no sheets found",
            extra={"path": str(excel_path), "doc_filename": excel_path.name},
        )
        # Return metadata with zero sheets for empty workbook
        metadata = DocumentMetadata(
            filename=excel_path.name,
            doc_type="Excel",
            ingestion_timestamp=datetime.now(UTC).isoformat(),
            page_count=0,
            source_path=str(excel_path),
        )
        return metadata

    # Extract all sheets with sheet numbers
    sheets_data = []
    total_rows = 0
    skipped_sheets = 0

    try:
        for sheet_number, sheet_name in enumerate(workbook.sheetnames, start=1):
            sheet = workbook[sheet_name]

            # Convert sheet to pandas DataFrame
            # Get all cell values from the sheet
            data = list(sheet.values)

            if not data:
                # Empty sheet - skip but log
                skipped_sheets += 1
                logger.info(
                    "Empty sheet skipped",
                    extra={"sheet_name": sheet_name, "sheet_number": sheet_number},
                )
                continue

            # First row as column headers
            headers = data[0] if data else []
            rows = data[1:] if len(data) > 1 else []

            # Create DataFrame with proper headers
            df = pd.DataFrame(rows, columns=headers)

            # Convert to markdown table format (preserves numeric formatting)
            # to_markdown() preserves numbers, dates, currencies as-is
            sheet_markdown = f"## Sheet {sheet_number}: {sheet_name}\n\n"
            sheet_markdown += df.to_markdown(index=False)

            sheets_data.append(
                {
                    "sheet_name": sheet_name,
                    "sheet_number": sheet_number,
                    "content": sheet_markdown,
                    "row_count": len(df),
                }
            )

            total_rows += len(df)

    except Exception as e:
        error_msg = f"Failed to extract data from sheets in {excel_path.name}: {e}"
        logger.error(
            "Sheet extraction failed",
            extra={"path": str(excel_path), "doc_filename": excel_path.name, "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

    # Calculate extraction metrics
    sheet_count = len(sheets_data)

    # Validate sheet extraction
    if sheet_count == 0:
        logger.warning(
            "No sheets extracted - verify Excel file structure",
            extra={"path": str(excel_path), "total_sheets": len(workbook.sheetnames)},
        )

    # Concatenate all sheet markdown for chunking
    full_text = "\n\n".join(sheet["content"] for sheet in sheets_data)

    # Create initial metadata for chunking (use sheet_count as page_count)
    metadata = DocumentMetadata(
        filename=excel_path.name,
        doc_type="Excel",
        ingestion_timestamp=datetime.now(UTC).isoformat(),
        page_count=sheet_count,
        source_path=str(excel_path),
        chunk_count=0,  # Will be updated after chunking
    )

    # Chunk the document if there's content
    chunks = []
    if full_text.strip():
        chunks = await chunk_document(full_text, metadata)

    # Generate embeddings for chunks (Story 1.5)
    chunks_with_embeddings = []
    if chunks:
        chunks_with_embeddings = await generate_embeddings(chunks)

    # Store vectors in Qdrant (Story 1.6)
    if chunks_with_embeddings:
        points_stored = await store_vectors_in_qdrant(
            chunks_with_embeddings, collection_name=settings.qdrant_collection_name
        )
        logger.info(
            "Vectors stored in Qdrant",
            extra={
                "doc_filename": excel_path.name,
                "points_stored": points_stored,
                "collection": settings.qdrant_collection_name,
            },
        )

    # Update metadata with chunk count
    metadata.chunk_count = len(chunks_with_embeddings)

    # Calculate final metrics
    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "Excel extracted successfully",
        extra={
            "doc_filename": excel_path.name,
            "sheet_count": sheet_count,
            "chunk_count": len(chunks_with_embeddings),
            "total_rows": total_rows,
            "skipped_sheets": skipped_sheets,
            "duration_ms": duration_ms,
            "sheets_per_second": (
                round(sheet_count / (duration_ms / 1000), 2) if duration_ms > 0 else 0
            ),
        },
    )

    return metadata


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


async def chunk_by_docling_items(
    result: ConversionResult,
    doc_metadata: DocumentMetadata,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    """Chunk document using element-aware boundaries from Docling.

    MODIFIED in Story 2.2: Now uses extract_elements() and chunk_elements() for
    structure-aware chunking that respects element boundaries (tables, sections, paragraphs).

    Extracts page numbers directly from Docling provenance metadata and preserves
    element type and section context for improved retrieval accuracy.

    Args:
        result: Docling ConversionResult containing document with provenance
        doc_metadata: Document metadata (filename, doc_type, etc.)
        chunk_size: Target chunk size in words (default: 500) - converted to ~650 tokens
        overlap: Word overlap between chunks (default: 50) - converted to ~65 tokens

    Returns:
        List of Chunk objects with element-type metadata and accurate page numbers

    Raises:
        RuntimeError: If chunking fails

    Strategy (Story 2.2):
        1. Extract structured elements from Docling (tables, sections, paragraphs)
        2. Apply element-aware chunking algorithm
        3. Preserve element_type and section_title metadata in each chunk
    """
    start_time = time.time()

    # Story 2.2: Extract structured elements from Docling
    logger.info(
        "Extracting structured elements from document",
        extra={"doc_filename": doc_metadata.filename},
    )
    elements = extract_elements(result)

    # Story 2.2: Apply element-aware chunking algorithm
    # Convert word-based parameters to token-based parameters
    # Rough approximation: 1 word ≈ 1.3 tokens
    max_tokens = int(chunk_size * 1.3)  # 500 words ≈ 650 tokens
    overlap_tokens = int(overlap * 1.3)  # 50 words ≈ 65 tokens

    logger.info(
        "Applying element-aware chunking",
        extra={
            "doc_filename": doc_metadata.filename,
            "max_tokens": max_tokens,
            "overlap_tokens": overlap_tokens,
        },
    )
    chunks = chunk_elements(
        elements=elements,
        doc_metadata=doc_metadata,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
    )

    # Calculate metrics
    duration_ms = int((time.time() - start_time) * 1000)
    avg_chunk_size = sum(c.word_count for c in chunks) / len(chunks) if chunks else 0

    logger.info(
        "Document chunked with element-aware boundaries",
        extra={
            "doc_filename": doc_metadata.filename,
            "chunk_count": len(chunks),
            "avg_chunk_size": round(avg_chunk_size, 1),
            "element_count": len(elements),
            "duration_ms": duration_ms,
        },
    )

    return chunks
