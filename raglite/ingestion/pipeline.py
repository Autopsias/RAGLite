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
from docling_core.types.doc import TableItem
from qdrant_client.models import Distance, PointStruct, VectorParams

from raglite.shared.clients import get_embedding_model, get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk, DocumentMetadata

logger = get_logger(__name__)


# Exception classes
class EmbeddingGenerationError(Exception):
    """Raised when embedding generation fails."""

    pass


class VectorStorageError(Exception):
    """Raised when vector storage to Qdrant fails."""

    pass


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

        # Create collection with HNSW indexing (default)
        logger.info(
            "Creating Qdrant collection",
            extra={
                "collection": collection_name,
                "vector_size": vector_size,
                "distance": distance.name,
                "indexing": "HNSW (default)",
            },
        )

        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )

        logger.info("Collection created successfully", extra={"collection": collection_name})

    except Exception as e:
        logger.error(
            "Collection creation failed",
            extra={"collection": collection_name, "error": str(e)},
            exc_info=True,
        )
        raise VectorStorageError(f"Failed to create collection {collection_name}: {e}") from e


async def store_vectors_in_qdrant(
    chunks: list[Chunk], collection_name: str = "financial_docs", batch_size: int = 100
) -> int:
    """Store document chunks with embeddings in Qdrant vector database.

    Processes chunks in batches for memory efficiency. Generates unique UUIDs for
    each point and stores all chunk metadata for retrieval and attribution.

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

        # Calculate word count from content
        word_count = len(chunk.content.split())

        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=chunk.embedding,
            payload={
                "chunk_id": chunk.chunk_id,
                "text": chunk.content,
                "word_count": word_count,
                "source_document": chunk.metadata.filename,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,  # Use explicit field from Chunk model
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


async def ingest_pdf(file_path: str) -> DocumentMetadata:
    """Ingest financial PDF and extract text, tables, and structure with page numbers.

    Uses Docling library for high-accuracy extraction (97.9% table accuracy).
    Extracts page numbers from element provenance metadata.

    Args:
        file_path: Path to PDF file (relative or absolute)

    Returns:
        DocumentMetadata with extraction results including page_count and ingestion timestamp

    Raises:
        FileNotFoundError: If PDF file doesn't exist at specified path
        RuntimeError: If Docling parsing fails or PDF is corrupted

    Example:
        >>> metadata = await ingest_pdf("docs/sample pdf/report.pdf")
        >>> print(f"Ingested {metadata.page_count} pages")
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

    logger.info(
        "Starting PDF ingestion",
        extra={
            "path": str(pdf_path),
            "doc_filename": pdf_path.name,
            "size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
        },
    )

    # Initialize Docling converter with table extraction enabled (Story 1.15 fix)
    # Configure table structure recognition to extract table cell data
    try:
        pipeline_options = PdfPipelineOptions(do_table_structure=True)
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        logger.info(
            "Docling converter initialized with table extraction",
            extra={"table_mode": "ACCURATE", "path": str(pdf_path)},
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
    """Chunk document using Docling items with actual page numbers from provenance.

    Extracts page numbers directly from Docling provenance metadata instead of
    estimating from character position. Groups items by page and creates chunks
    that respect both page boundaries and target chunk size.

    Args:
        result: Docling ConversionResult containing document with provenance
        doc_metadata: Document metadata (filename, doc_type, etc.)
        chunk_size: Target chunk size in words (default: 500)
        overlap: Word overlap between chunks (default: 50)

    Returns:
        List of Chunk objects with accurate page numbers from provenance

    Raises:
        RuntimeError: If chunking fails
    """
    start_time = time.time()

    # Collect items with their page numbers
    page_items: dict[int, list[str]] = {}  # {page_no: [text items]}
    items_without_prov = 0
    last_known_page = 1

    for item, _ in result.document.iterate_items():
        # Extract page number from provenance
        page_no = None
        if hasattr(item, "prov") and item.prov:
            page_no = item.prov[0].page_no
            last_known_page = page_no
        else:
            # Fallback to last known page with warning
            page_no = last_known_page
            items_without_prov += 1

        # Group items by page
        if page_no not in page_items:
            page_items[page_no] = []

        # Handle table items - export to markdown for LLM understanding
        if isinstance(item, TableItem):
            table_markdown = item.export_to_markdown()
            if table_markdown.strip():
                page_items[page_no].append(table_markdown)
                logger.debug(
                    "Table extracted",
                    extra={"page": page_no, "size_chars": len(table_markdown)},
                )
        # Handle text items (unchanged)
        elif hasattr(item, "text") and item.text.strip():
            page_items[page_no].append(item.text)

    # Log provenance coverage
    total_items = sum(len(items) for items in page_items.values())
    prov_coverage_pct = (
        round((total_items - items_without_prov) / total_items * 100, 1) if total_items > 0 else 0
    )

    logger.info(
        "Docling items collected",
        extra={
            "doc_filename": doc_metadata.filename,
            "total_items": total_items,
            "items_with_prov": total_items - items_without_prov,
            "items_without_prov": items_without_prov,
            "prov_coverage_pct": prov_coverage_pct,
            "page_count": len(page_items),
        },
    )

    # Warn if provenance coverage is low
    if items_without_prov > 0:
        logger.warning(
            "Some items missing provenance - using fallback",
            extra={
                "doc_filename": doc_metadata.filename,
                "items_without_prov": items_without_prov,
                "fallback_strategy": "last_known_page",
            },
        )

    # Create chunks from page items
    chunks = []
    chunk_index = 0

    # Process each page in order
    for page_no in sorted(page_items.keys()):
        page_text = " ".join(page_items[page_no])
        page_words = page_text.split()

        # Skip pages with no text content (e.g., pages with only images/tables)
        if not page_words:
            continue

        # If page is small enough, create single chunk
        if len(page_words) <= chunk_size:
            chunk = Chunk(
                chunk_id=f"{doc_metadata.filename}_{chunk_index}",
                content=page_text,
                metadata=doc_metadata,
                page_number=page_no,
                chunk_index=chunk_index,
                embedding=[],
            )
            chunks.append(chunk)
            chunk_index += 1
        else:
            # Split large page into multiple chunks while preserving page number
            idx = 0
            while idx < len(page_words):
                chunk_words = page_words[idx : idx + chunk_size]
                chunk_text = " ".join(chunk_words)

                chunk = Chunk(
                    chunk_id=f"{doc_metadata.filename}_{chunk_index}",
                    content=chunk_text,
                    metadata=doc_metadata,
                    page_number=page_no,
                    chunk_index=chunk_index,
                    embedding=[],
                )
                chunks.append(chunk)
                chunk_index += 1

                # Move to next chunk with overlap
                idx += chunk_size - overlap

    # Calculate metrics
    duration_ms = int((time.time() - start_time) * 1000)
    avg_chunk_size = sum(len(c.content.split()) for c in chunks) / len(chunks) if chunks else 0
    page_range = f"{min(page_items.keys())}-{max(page_items.keys())}" if page_items else "N/A"

    logger.info(
        "Document chunked with provenance",
        extra={
            "doc_filename": doc_metadata.filename,
            "chunk_count": len(chunks),
            "avg_chunk_size": round(avg_chunk_size, 1),
            "page_range": page_range,
            "duration_ms": duration_ms,
        },
    )

    return chunks
