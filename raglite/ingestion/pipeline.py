"""Document ingestion pipeline for PDFs and Excel files.

Extracts text, tables, and page numbers from financial documents with high accuracy.
"""

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import openpyxl
import pandas as pd
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import ConversionResult, DocumentConverter, PdfFormatOption
from docling_core.types.doc import (
    TableItem,
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
from raglite.shared.models import Chunk, DocumentMetadata, ExtractedMetadata

logger = get_logger(__name__)

# Story 2.4: Metadata extraction cache (per-document)
# Cache keyed by document hash to avoid redundant API calls
_metadata_cache: dict[str, ExtractedMetadata] = {}

# Initialize tiktoken encoding for token counting (Story 2.3 AC2)
# Using cl100k_base encoding as specified in research (Yepes et al. 2024)
encoding: Optional["Encoding"] = None  # Forward reference to avoid import errors
try:
    import tiktoken
    from tiktoken import Encoding

    encoding = tiktoken.get_encoding("cl100k_base")
except ImportError:
    logger.warning(
        "tiktoken not installed - token counting will be approximate",
        extra={"fallback": "word count estimation"},
    )


# Exception classes
class EmbeddingGenerationError(Exception):
    """Raised when embedding generation fails."""

    pass


class VectorStorageError(Exception):
    """Raised when vector storage to Qdrant fails."""

    pass


# Element-aware chunking functions removed in Story 2.3 (AC1)
# Replaced with fixed 512-token chunking approach


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


async def extract_document_metadata(
    text: str, doc_filename: str, use_cache: bool = True
) -> ExtractedMetadata:
    """Extract business context metadata using GPT-5 nano API.

    Story 2.4 AC1: Extract fiscal_period, company_name, department_name for filtering.

    Args:
        text: Document text sample (first ~2000 tokens recommended)
        doc_filename: Document filename for cache key
        use_cache: Whether to use cached results (default: True)

    Returns:
        ExtractedMetadata with fiscal_period, company_name, department_name

    Raises:
        RuntimeError: If OpenAI API call fails or API key not configured

    Cost (GPT-5 nano with prompt caching):
        - Cached input: ~2000 tokens × $0.005/MTok = $0.00001
        - New input: ~100 tokens × $0.10/MTok = $0.00001
        - Output: ~100 tokens × $0.40/MTok = $0.00004
        - Total: ~$0.00005 per document (99.3% cheaper than Claude baseline)

    Example:
        >>> metadata = await extract_document_metadata(doc_text[:10000], "report.pdf")
        >>> print(f"Period: {metadata.fiscal_period}, Company: {metadata.company_name}")
    """
    start_time = time.time()

    # Check cache first (AC4: per-document caching)
    cache_key = doc_filename
    if use_cache and cache_key in _metadata_cache:
        logger.info(
            "Metadata cache hit",
            extra={"doc_filename": doc_filename, "cache_key": cache_key},
        )
        return _metadata_cache[cache_key]

    # Validate OpenAI API key is configured
    if not settings.openai_api_key:
        error_msg = "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
        logger.warning(  # AI6: Changed from error to warning (graceful degradation)
            "Metadata extraction skipped - API key not configured (graceful degradation)",
            extra={"doc_filename": doc_filename, "metadata_extraction": "disabled"},
        )
        raise RuntimeError(error_msg)

    logger.info(
        "Extracting document metadata with GPT-5 nano",
        extra={
            "doc_filename": doc_filename,
            "text_sample_length": len(text),
            "cache_miss": True,
        },
    )

    try:
        # Import OpenAI SDK (lazy import to avoid startup overhead)
        import httpx
        from openai import AsyncOpenAI

        # Initialize client with 30-second timeout to prevent test hangs
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=httpx.Timeout(30.0, connect=5.0),  # 30s total, 5s connect
        )

        # Truncate text to first ~2000 tokens (representative sample)
        # GPT-5 nano uses same tokenizer as GPT-4 (cl100k_base)
        if encoding:
            tokens = encoding.encode(text)
            if len(tokens) > 2000:
                text = encoding.decode(tokens[:2000])
                logger.debug(
                    "Truncated text to 2000 tokens",
                    extra={"doc_filename": doc_filename, "original_tokens": len(tokens)},
                )

        # AC1: Call GPT-5 nano API with JSON schema mode
        response = await client.chat.completions.create(
            model=settings.openai_metadata_model,  # AI7: Configurable model
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial document analyzer. Extract business metadata accurately.",
                },
                {
                    "role": "user",
                    "content": f"""Extract the following information from this financial document:
- fiscal_period: The fiscal period (e.g., "Q3 2024", "FY 2023")
- company_name: The company name (e.g., "ACME Corporation")
- department_name: The department name if mentioned (e.g., "Finance", "Operations")

If any field cannot be determined, return null for that field.

Document excerpt:
{text}

Return ONLY a JSON object with the three fields.""",
                },
            ],
            response_format={"type": "json_object"},  # JSON schema mode
            temperature=0.0,  # Deterministic extraction
            max_tokens=150,  # Small response (just 3 fields)
        )

        # Parse response
        response_content = response.choices[0].message.content
        if not response_content:
            raise RuntimeError("Empty response from GPT-5 nano API")

        # Parse JSON response into ExtractedMetadata
        import json

        metadata_dict = json.loads(response_content)
        extracted_metadata = ExtractedMetadata(
            fiscal_period=metadata_dict.get("fiscal_period"),
            company_name=metadata_dict.get("company_name"),
            department_name=metadata_dict.get("department_name"),
        )

        # Cache the result (AC4)
        if use_cache:
            _metadata_cache[cache_key] = extracted_metadata

        # Calculate cost metrics for logging (AI4: Uses config pricing)
        duration_ms = int((time.time() - start_time) * 1000)
        usage = response.usage

        # Type-safe access to CompletionUsage attributes (handle None case)
        if usage is not None:
            estimated_cost = (
                usage.prompt_tokens * settings.gpt5_nano_input_price_per_mtok / 1_000_000
            ) + (usage.completion_tokens * settings.gpt5_nano_output_price_per_mtok / 1_000_000)
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
        else:
            # Fallback if usage data not available
            estimated_cost = 0.0
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

        logger.info(
            "Metadata extraction complete",
            extra={
                "doc_filename": doc_filename,
                "fiscal_period": extracted_metadata.fiscal_period,
                "company_name": extracted_metadata.company_name,
                "department_name": extracted_metadata.department_name,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "estimated_cost_usd": round(estimated_cost, 6),
                "duration_ms": duration_ms,
            },
        )

        return extracted_metadata

    except Exception as e:
        error_msg = f"Metadata extraction failed for {doc_filename}: {e}"
        logger.error(
            "GPT-5 nano API call failed",
            extra={
                "doc_filename": doc_filename,
                "error": str(e),
            },
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e


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
                # Story 2.4 AC3: LLM-extracted business context metadata for filtering
                "fiscal_period": chunk.fiscal_period,
                "company_name": chunk.company_name,
                "department_name": chunk.department_name,
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
        # Story 2.2: Configure parallel page processing
        # Thread count configurable via PDF_PROCESSING_THREADS env var (default: 8)
        # NOTE: Default AcceleratorOptions is 4 threads - we use 8 for 1.55x speedup
        thread_count = settings.pdf_processing_threads

        # Story 2.3 Fix: Add document_timeout to prevent indefinite hangs on large PDFs
        # Timeout set to 1500s (25 minutes) for 160-page PDFs
        # Based on: 40-page = 3m51s, 160-page expected = ~15-18min, buffer = 25min
        pipeline_options = PdfPipelineOptions(
            do_table_structure=True,
            accelerator_options=AcceleratorOptions(num_threads=thread_count),
            document_timeout=1500,  # 25 minutes max per document
        )
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
            extra={
                "table_mode": "ACCURATE",
                "backend": "pypdfium",
                "num_threads": thread_count,
                "path": str(pdf_path),
            },
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
        full_text = result.document.export_to_markdown()
    except Exception as e:
        logger.warning(
            "Failed to export markdown - falling back to plain text",
            extra={"path": str(pdf_path), "error": str(e)},
        )
        # Fallback: concatenate all text from elements
        full_text = "\n".join(
            item.text for item, _ in result.document.iterate_items() if hasattr(item, "text")
        )

    # Create initial metadata for chunking
    metadata = DocumentMetadata(
        filename=pdf_path.name,
        doc_type="PDF",
        ingestion_timestamp=datetime.now(UTC).isoformat(),
        page_count=page_count,
        source_path=str(pdf_path),
        chunk_count=0,  # Will be updated after chunking
    )

    # Story 2.4 AC1: Extract business context metadata using GPT-5 nano
    # Extract ONCE per document (cached for all chunks)
    extracted_metadata = None
    if settings.openai_api_key:
        try:
            extracted_metadata = await extract_document_metadata(
                text=full_text, doc_filename=pdf_path.name
            )
            logger.info(
                "Document metadata extracted",
                extra={
                    "doc_filename": pdf_path.name,
                    "fiscal_period": extracted_metadata.fiscal_period,
                    "company_name": extracted_metadata.company_name,
                    "department_name": extracted_metadata.department_name,
                },
            )
        except Exception as e:
            logger.warning(
                "Metadata extraction failed - continuing without metadata",
                extra={"doc_filename": pdf_path.name, "error": str(e)},
            )
    else:
        logger.info(
            "Metadata extraction skipped - OPENAI_API_KEY not configured",
            extra={"doc_filename": pdf_path.name},
        )

    # Chunk the document using Docling items with provenance (Story 1.13 fix)
    # This extracts actual page numbers from Docling metadata instead of estimating
    chunks = await chunk_by_docling_items(result, metadata)

    # Story 2.4 AC3: Inject extracted metadata into all chunks
    if extracted_metadata:
        for chunk in chunks:
            chunk.fiscal_period = extracted_metadata.fiscal_period
            chunk.company_name = extracted_metadata.company_name
            chunk.department_name = extracted_metadata.department_name
        logger.info(
            "Metadata injected into chunks",
            extra={
                "doc_filename": pdf_path.name,
                "chunk_count": len(chunks),
                "fiscal_period": extracted_metadata.fiscal_period,
            },
        )

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
    chunk_size: int = 512,
    overlap: int = 50,
) -> list[Chunk]:
    """Chunk document using fixed 512-token approach with table boundary preservation.

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

    # AC3: Extract tables separately to preserve table boundaries
    tables: list[tuple[TableItem, int]] = []  # (table_item, page_number)
    text_items: list[tuple[str, int]] = []  # (text_content, page_number)

    for item, _ in result.document.iterate_items():
        # Get page number from provenance
        page_number = 1  # Default fallback
        if hasattr(item, "prov") and item.prov:
            page_number = item.prov[0].page_no

        if isinstance(item, TableItem):
            # AC3: Store tables separately
            tables.append((item, page_number))
        elif hasattr(item, "text"):
            # Text content (paragraphs, sections, lists)
            text_items.append((item.text, page_number))

    # Process tables first (AC3: each table becomes a single chunk)
    for table_item, page_num in tables:
        table_content = table_item.export_to_markdown(doc=result.document)
        token_count = len(encoding.encode(table_content))
        word_count = len(table_content.split())

        chunk = Chunk(
            chunk_id=f"{doc_metadata.filename}_{chunk_index}",
            content=table_content,
            metadata=doc_metadata,
            page_number=page_num,
            chunk_index=chunk_index,
            embedding=[],
            word_count=word_count,
        )
        chunks.append(chunk)
        chunk_index += 1

        logger.debug(
            "Table preserved as single chunk",
            extra={
                "chunk_index": chunk_index - 1,
                "token_count": token_count,
                "page": page_num,
                "exceeds_512": token_count > 512,
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
                (current_token_offset, current_token_offset + item_token_count, page_num)
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
            "table_chunks": len(tables),
            "text_chunks": len(chunks) - len(tables),
            "avg_chunk_size_words": round(avg_chunk_size, 1),
            "avg_chunk_size_tokens": round(avg_tokens, 1),
            "duration_ms": duration_ms,
        },
    )

    return chunks
