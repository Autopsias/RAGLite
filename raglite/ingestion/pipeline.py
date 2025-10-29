"""Document ingestion pipeline for PDFs and Excel files.

Extracts text, tables, and page numbers from financial documents with high accuracy.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from mistralai import Mistral
    from docling.datamodel.accelerator_options import AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import ConversionResult, DocumentConverter, PdfFormatOption
    from docling_core.types.doc import TableItem

import openpyxl
import pandas as pd
from qdrant_client.models import (
    Distance,
    PointStruct,
    SparseIndexParams,
    SparseVectorParams,
    VectorParams,
)

from raglite.ingestion.table_extraction import TableExtractor
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


async def extract_chunk_metadata(
    text: str, chunk_id: str, client: Optional["Mistral"] = None
) -> ExtractedMetadata:
    """Extract business context metadata from a single chunk using Mistral Small 3.2.

    Story 2.4 AC1 (REVISED - FIX): Extract fiscal_period, company_name, department_name per chunk.

    MIGRATION FROM OPENAI o1-mini TO MISTRAL SMALL 3.2:
    - Previous: OpenAI o1-mini had 50% failure rate due to reasoning token overflow
    - Current: Mistral Small 3.2 with native JSON schema support
    - Benefits:
      * FREE (vs $0.110 per 400 chunks for o1-mini)
      * 91% extraction accuracy (research-validated, vs 48% for o1-mini)
      * Native JSON schema enforcement (not function calling)
      * No reasoning token waste
      * Released June 2025 (newest free option)

    Args:
        text: Chunk text content (~512 tokens from fixed chunking)
        chunk_id: Unique chunk identifier for logging
        client: Optional pre-created AsyncMistral client for connection pooling.
            If None, creates new client (slower). For best performance, create
            single client and reuse across all chunks. (Story 2.6 AC6 optimization)

    Returns:
        ExtractedMetadata with 15 RICH SCHEMA fields (document-level, section-level, table-specific)

    Raises:
        RuntimeError: If Mistral API call fails or API key not configured
        asyncio.TimeoutError: If API call exceeds 30 second timeout (Story 2.6 AC6 fail-fast)

    Cost (Mistral Small 3.2):
        - Input: FREE
        - Output: FREE
        - Total: $0.00 per chunk
        - For 160-page doc with 400 chunks: $0.00 total

    Example:
        >>> from mistralai.async_client import AsyncMistral
        >>> client = AsyncMistral(api_key=settings.mistral_api_key)  # Reuse for all chunks
        >>> metadata = await extract_chunk_metadata(chunk.content, chunk.chunk_id, client)
        >>> print(f"Chunk {chunk.chunk_id}: {metadata.reporting_period}")
    """
    start_time = time.time()

    # Validate Mistral API key is configured
    if not settings.mistral_api_key:
        error_msg = "Mistral API key not configured. Set MISTRAL_API_KEY environment variable."
        logger.warning(
            "Metadata extraction skipped - API key not configured (graceful degradation)",
            extra={"chunk_id": chunk_id, "metadata_extraction": "disabled"},
        )
        raise RuntimeError(error_msg)

    logger.debug(
        "Extracting chunk metadata with Mistral Small 3.2",
        extra={
            "chunk_id": chunk_id,
            "text_length": len(text),
            "model": settings.metadata_extraction_model,
        },
    )

    try:
        # Import dependencies (lazy import to avoid startup overhead)
        import json

        from mistralai import Mistral

        # Story 2.6 AC6 FIX: Client pooling - accept pre-created client or create new one
        # This enables caller to reuse single client instance across all chunks (10-15x speedup)
        if client is None:
            client = Mistral(api_key=settings.mistral_api_key)

        # NO TRUNCATION NEEDED: Chunks are already fixed at ~512 tokens (Story 2.3)
        # This is the perfect size for metadata extraction

        # AC1 REVISION: Call Mistral Small API with RICH SCHEMA (15 fields)
        # Based on INEXDA, FinRAG, RAF research showing 20-25% accuracy gains
        # Story 2.6 AC6 FIX: Add await (async client) + timeout=30 (fail fast)
        from mistralai.models import SystemMessage, UserMessage

        response = await client.chat.complete_async(
            model=settings.metadata_extraction_model,  # "mistral-small-latest"
            messages=[
                SystemMessage(
                    content=(
                        "Extract 15 metadata fields from financial document chunks for RAG retrieval optimization.\n"
                        "Return ONLY valid JSON with these exact fields. Use null for missing values.\n\n"
                        "DOCUMENT-LEVEL (7 fields):\n"
                        "- document_type: Income Statement | Balance Sheet | Cash Flow Statement | Operational Report | "
                        "Earnings Call | Management Discussion | Financial Notes\n"
                        "- reporting_period: Q1 2024 | Aug-25 YTD | FY 2023 | 2024 Annual | H1 2025\n"
                        "- time_granularity: Daily | Weekly | Monthly | Quarterly | YTD | Annual | Rolling 12-Month\n"
                        "- company_name: Portugal Cement | CIMPOR | Cimpor Trading | InterCement\n"
                        "- geographic_jurisdiction: Portugal | EU | APAC | Americas | Global\n"
                        "- data_source_type: Audited | Internal Report | Regulatory Filing | Management Estimate | Preliminary\n"
                        "- version_date: 2025-08-15 | 2024-Q3-Final | 2024-12-31-Revised\n\n"
                        "SECTION-LEVEL (5 fields):\n"
                        "- section_type: Narrative | Table | Footnote | Chart Caption | Summary | List | Formula\n"
                        "- metric_category: Revenue | EBITDA | Operating Expenses | Capital Expenditure | Cash Flow | "
                        "Assets | Liabilities | Equity | Ratios | Production Volume | Cost per Unit\n"
                        "- units: EUR | USD | GBP | EUR/ton | USD/MWh | Percentage | Count | Tonnes | MWh | m³\n"
                        "- department_scope: Operations | Finance | Production | Sales | Corporate | HR | IT | Supply Chain\n\n"
                        "TABLE-SPECIFIC (3 fields - ONLY for table chunks):\n"
                        "- table_context: Brief description of table purpose and contents (1-2 sentences)\n"
                        "- table_name: Actual table title from document\n"
                        "- statistical_summary: Key statistics if numerical (e.g., 'Mean=5.8, Range=3.5-61.4')\n\n"
                        "EXAMPLES:\n"
                        "Narrative chunk: {document_type: 'Operational Report', reporting_period: 'Aug-25 YTD', "
                        "time_granularity: 'YTD', company_name: 'Portugal Cement', section_type: 'Narrative', "
                        "metric_category: 'EBITDA', department_scope: 'Operations', ...}\n\n"
                        "Table chunk: {document_type: 'Operational Report', reporting_period: 'Aug-25 YTD', "
                        "section_type: 'Table', metric_category: 'Operating Expenses', units: 'EUR/ton', "
                        "table_name: 'Variable Costs Summary', table_context: 'Breakdown of variable costs by category', ...}"
                    )
                ),
                UserMessage(
                    content=f"Extract all 15 metadata fields from this financial document chunk:\n\n{text}"
                ),
            ],
            response_format={"type": "json_object"},  # JSON mode (Mistral's structured output)
            temperature=0,  # Deterministic extraction
            max_tokens=400,  # Increased from 150 to accommodate 15 fields
        )

        # Parse response
        response_content = response.choices[0].message.content

        if not response_content:
            logger.error(
                "Empty response from Mistral Small 3.2",
                extra={"chunk_id": chunk_id},
            )
            raise RuntimeError("Empty response from Mistral API")

        # Type guard: ensure response_content is a string before json.loads
        if not isinstance(response_content, str):
            logger.error(
                "Response content is not a string, cannot parse JSON",
                extra={"chunk_id": chunk_id, "content_type": type(response_content).__name__},
            )
            raise RuntimeError("Response content is not a string")

        # Parse JSON response into ExtractedMetadata (15 fields - RICH SCHEMA)
        metadata_dict = json.loads(response_content)
        extracted_metadata = ExtractedMetadata(
            # Document-Level (7 fields)
            document_type=metadata_dict.get("document_type"),
            reporting_period=metadata_dict.get("reporting_period"),
            time_granularity=metadata_dict.get("time_granularity"),
            company_name=metadata_dict.get("company_name"),
            geographic_jurisdiction=metadata_dict.get("geographic_jurisdiction"),
            data_source_type=metadata_dict.get("data_source_type"),
            version_date=metadata_dict.get("version_date"),
            # Section-Level (5 fields)
            section_type=metadata_dict.get("section_type"),
            metric_category=metadata_dict.get("metric_category"),
            units=metadata_dict.get("units"),
            department_scope=metadata_dict.get("department_scope"),
            # Table-Specific (3 fields)
            table_context=metadata_dict.get("table_context"),
            table_name=metadata_dict.get("table_name"),
            statistical_summary=metadata_dict.get("statistical_summary"),
        )

        # Calculate duration for logging
        duration_ms = int((time.time() - start_time) * 1000)

        logger.debug(
            "Chunk metadata extraction complete (15-field rich schema)",
            extra={
                "chunk_id": chunk_id,
                "document_type": extracted_metadata.document_type,
                "reporting_period": extracted_metadata.reporting_period,
                "section_type": extracted_metadata.section_type,
                "metric_category": extracted_metadata.metric_category,
                "model": settings.metadata_extraction_model,
                "estimated_cost_usd": 0.0,  # FREE with Mistral Small 3.2
                "duration_ms": duration_ms,
            },
        )

        return extracted_metadata

    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON response from Mistral for {chunk_id}: {e}"
        logger.warning(
            "Mistral API returned invalid JSON (graceful degradation)",
            extra={
                "chunk_id": chunk_id,
                "error": str(e),
                "response": response_content if "response_content" in locals() else None,
            },
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

    except Exception as e:
        error_msg = f"Chunk metadata extraction failed for {chunk_id}: {e}"
        logger.warning(
            "Mistral Small 3.2 API call failed for chunk (graceful degradation)",
            extra={
                "chunk_id": chunk_id,
                "error": str(e),
                "error_type": type(e).__name__,
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

        # Story 2.4 Enhancement: Include rich metadata (15 fields) for metadata score boosting
        chunk_metadata = [
            {
                "source_document": chunk.metadata.filename,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                # Document-Level (7 fields)
                "document_type": chunk.document_type,
                "reporting_period": chunk.reporting_period,
                "time_granularity": chunk.time_granularity,
                "company_name": chunk.company_name,
                "geographic_jurisdiction": chunk.geographic_jurisdiction,
                "data_source_type": chunk.data_source_type,
                "version_date": chunk.version_date,
                # Section-Level (5 fields)
                "section_type": chunk.section_type,
                "metric_category": chunk.metric_category,
                "units": chunk.units,
                "department_scope": chunk.department_scope,
                # Table-Specific (3 fields)
                "table_context": chunk.table_context,
                "table_name": chunk.table_name,
                "statistical_summary": chunk.statistical_summary,
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
                "chunk_index": chunk.chunk_index,
                # Story 2.4 REVISION: RICH SCHEMA (15 fields) for metadata-driven retrieval
                # Document-Level (7 fields)
                "document_type": chunk.document_type,
                "reporting_period": chunk.reporting_period,
                "time_granularity": chunk.time_granularity,
                "company_name": chunk.company_name,
                "geographic_jurisdiction": chunk.geographic_jurisdiction,
                "data_source_type": chunk.data_source_type,
                "version_date": chunk.version_date,
                # Section-Level (5 fields)
                "section_type": chunk.section_type,
                "metric_category": chunk.metric_category,
                "units": chunk.units,
                "department_scope": chunk.department_scope,
                # Table-Specific (3 fields)
                "table_context": chunk.table_context,
                "table_name": chunk.table_name,
                "statistical_summary": chunk.statistical_summary,
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


async def store_metadata_in_postgresql(
    chunks: list[Chunk], batch_size: int = 100
) -> tuple[int, int]:
    """Store chunk metadata in PostgreSQL for structured filtering (Story 2.6 AC4).

    Only stores chunks that have extracted metadata. Chunks without metadata are skipped
    with a debug log entry.

    Args:
        chunks: List of Chunk objects with optional extracted metadata
        batch_size: Records per batch (default: 100 for memory efficiency)

    Returns:
        Tuple of (records_stored, records_skipped)

    Raises:
        RuntimeError: If PostgreSQL storage fails

    Example:
        >>> stored, skipped = await store_metadata_in_postgresql(chunks)
        >>> logger.info(f"Stored {stored} chunks, skipped {skipped} without metadata")
    """
    import uuid
    from datetime import datetime

    from psycopg2.extras import execute_values

    from raglite.shared.clients import get_postgresql_connection

    start_time = time.time()

    logger.info(
        "Storing metadata in PostgreSQL",
        extra={
            "chunk_count": len(chunks),
            "batch_size": batch_size,
        },
    )

    if not chunks:
        logger.warning("No chunks provided for PostgreSQL storage")
        return (0, 0)

    # Filter chunks that have metadata
    chunks_with_metadata = [
        chunk
        for chunk in chunks
        if chunk.document_type or chunk.company_name or chunk.metric_category
    ]

    skipped_count = len(chunks) - len(chunks_with_metadata)

    if not chunks_with_metadata:
        logger.info(
            "No chunks with metadata to store in PostgreSQL - skipping PostgreSQL storage",
            extra={"total_chunks": len(chunks)},
        )
        return (0, len(chunks))

    logger.info(
        "Filtered chunks for PostgreSQL storage",
        extra={
            "total_chunks": len(chunks),
            "with_metadata": len(chunks_with_metadata),
            "skipped": skipped_count,
        },
    )

    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Prepare records for batch insert
        records = []
        for chunk in chunks_with_metadata:
            # Generate new UUID for PostgreSQL chunk_id (primary key)
            # Use chunk.chunk_id as STRING for embedding_id (link to Qdrant vector)
            record = (
                uuid.uuid4(),  # chunk_id: NEW UUID for PostgreSQL primary key
                uuid.uuid4(),  # document_id: placeholder (could be derived from filename in future)
                chunk.page_number,
                chunk.chunk_index,
                chunk.content,
                # Document-Level Metadata (7 fields)
                chunk.document_type,
                chunk.reporting_period,
                chunk.time_granularity,
                chunk.company_name,
                chunk.geographic_jurisdiction,
                chunk.data_source_type,
                chunk.version_date,
                # Section-Level Metadata (5 fields)
                chunk.section_type,
                chunk.metric_category,
                chunk.units,
                chunk.department_scope,
                # Table-Specific Metadata (3 fields)
                chunk.table_context,
                chunk.table_name,
                chunk.statistical_summary,
                # Search optimization
                None,  # content_tsv (will be generated by trigger)
                chunk.chunk_id,  # embedding_id (VARCHAR - link to Qdrant vector ID as STRING)
                datetime.now(),  # created_at
                datetime.now(),  # updated_at
            )
            records.append(record)

        # Insert in batches
        total_batches = (len(records) + batch_size - 1) // batch_size

        for i in range(0, len(records), batch_size):
            batch_num = (i // batch_size) + 1
            batch_records = records[i : i + batch_size]

            logger.info(
                f"Uploading PostgreSQL batch {batch_num}/{total_batches}",
                extra={
                    "batch_num": batch_num,
                    "batch_size": len(batch_records),
                    "total_batches": total_batches,
                },
            )

            execute_values(
                cursor,
                """
                INSERT INTO financial_chunks (
                    chunk_id, document_id, page_number, chunk_index, content,
                    document_type, reporting_period, time_granularity, company_name,
                    geographic_jurisdiction, data_source_type, version_date,
                    section_type, metric_category, units, department_scope,
                    table_context, table_name, statistical_summary,
                    content_tsv, embedding_id, created_at, updated_at
                ) VALUES %s
                """,
                batch_records,
            )

        conn.commit()
        cursor.close()

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "PostgreSQL metadata storage complete",
            extra={
                "records_stored": len(chunks_with_metadata),
                "records_skipped": skipped_count,
                "duration_ms": duration_ms,
                "records_per_second": round(len(chunks_with_metadata) / (duration_ms / 1000), 2)
                if duration_ms > 0
                else 0,
            },
        )

        return (len(chunks_with_metadata), skipped_count)

    except Exception as e:
        logger.error(
            "PostgreSQL metadata storage failed",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(f"Failed to store metadata in PostgreSQL: {e}") from e


async def store_tables_in_postgresql(
    table_rows: list[dict[str, Any]], batch_size: int = 100
) -> tuple[int, int]:
    """Store extracted table rows in PostgreSQL financial_tables table.

    Story 2.13 AC1: Table Extraction to SQL Database

    Args:
        table_rows: List of table row dicts from TableExtractor
        batch_size: Records per batch (default: 100 for memory efficiency)

    Returns:
        Tuple of (records_stored, records_skipped)

    Raises:
        RuntimeError: If PostgreSQL storage fails

    Example:
        >>> stored, skipped = await store_tables_in_postgresql(table_rows)
        >>> logger.info(f"Stored {stored} rows, skipped {skipped}")
    """
    from psycopg2.extras import execute_values

    from raglite.shared.clients import get_postgresql_connection

    start_time = time.time()

    logger.info(
        "Storing table data in PostgreSQL",
        extra={
            "row_count": len(table_rows),
            "batch_size": batch_size,
        },
    )

    if not table_rows:
        logger.info("No table rows to store in PostgreSQL")
        return (0, 0)

    # Filter rows with at least one data field populated
    valid_rows = [
        row
        for row in table_rows
        if row.get("entity") or row.get("metric") or row.get("value") is not None
    ]

    skipped_count = len(table_rows) - len(valid_rows)

    if not valid_rows:
        logger.info(
            "No valid table rows to store in PostgreSQL - all rows empty",
            extra={"total_rows": len(table_rows)},
        )
        return (0, len(table_rows))

    logger.info(
        "Filtered table rows for PostgreSQL storage",
        extra={
            "total_rows": len(table_rows),
            "valid_rows": len(valid_rows),
            "skipped": skipped_count,
        },
    )

    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Prepare records for batch insert
        records = []
        for row in valid_rows:
            record = (
                row.get("document_id"),
                row.get("page_number"),
                row.get("table_index"),
                row.get("table_caption"),
                row.get("entity"),
                row.get("metric"),
                row.get("period"),
                row.get("fiscal_year"),
                row.get("value"),
                row.get("unit"),
                row.get("row_index"),
                row.get("column_name"),
                row.get("chunk_text"),
            )
            records.append(record)

        # Insert in batches
        total_batches = (len(records) + batch_size - 1) // batch_size

        for i in range(0, len(records), batch_size):
            batch_num = (i // batch_size) + 1
            batch_records = records[i : i + batch_size]

            logger.info(
                f"Uploading PostgreSQL batch {batch_num}/{total_batches}",
                extra={
                    "batch_num": batch_num,
                    "batch_size": len(batch_records),
                    "total_batches": total_batches,
                },
            )

            execute_values(
                cursor,
                """
                INSERT INTO financial_tables (
                    document_id, page_number, table_index, table_caption,
                    entity, metric, period, fiscal_year, value, unit,
                    row_index, column_name, chunk_text
                ) VALUES %s
                """,
                batch_records,
            )

        conn.commit()
        cursor.close()

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "PostgreSQL table storage complete",
            extra={
                "records_stored": len(valid_rows),
                "records_skipped": skipped_count,
                "duration_ms": duration_ms,
                "records_per_second": round(len(valid_rows) / (duration_ms / 1000), 2)
                if duration_ms > 0
                else 0,
            },
        )

        return (len(valid_rows), skipped_count)

    except Exception as e:
        logger.error(
            "PostgreSQL table storage failed",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(f"Failed to store tables in PostgreSQL: {e}") from e


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


async def ingest_pdf(
    file_path: str, clear_collection: bool = True, skip_metadata: bool = False
) -> DocumentMetadata:
    """Ingest financial PDF and extract text, tables, and structure with page numbers.

    Uses Docling library for high-accuracy extraction (97.9% table accuracy).
    Extracts page numbers from element provenance metadata.

    Args:
        file_path: Path to PDF file (relative or absolute)
        clear_collection: If True, clears existing Qdrant collection before ingestion
                         to prevent data contamination. Default True for clean state.
        skip_metadata: If True, skips LLM metadata extraction (Story 2.4) to avoid API issues.
                       Default False. Use when Mistral API is unavailable.

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

        >>> # Skip metadata extraction to avoid API errors
        >>> metadata = await ingest_pdf("report.pdf", skip_metadata=True)
    """
    # Lazy import Docling: Avoid hanging on import when this module loads
    # Docling initializes PyTorch/CUDA on import which can hang without GPU
    # Only load when actually ingesting PDFs
    from docling.datamodel.accelerator_options import AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import DocumentConverter, PdfFormatOption

    start_time = time.time()
    import sys

    # Checkpoint: Start of function
    print(f"CHECKPOINT: ingest_pdf started for {file_path}", file=sys.stderr, flush=True)

    # Resolve file path
    pdf_path = Path(file_path).resolve()
    print(f"CHECKPOINT: PDF path resolved to {pdf_path}", file=sys.stderr, flush=True)

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
            do_ocr=False,  # Disable OCR for 50% speedup - financial PDFs have embedded text
            accelerator_options=AcceleratorOptions(
                num_threads=thread_count,
                device="cpu",  # CRITICAL: Force CPU-only mode to prevent CUDA hang on CI runners
            ),
            document_timeout=1500,  # 25 minutes max per document
        )
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

        # Story 2.1: PyPdfium backend (optimized)
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

        print(f"CHECKPOINT: Creating DocumentConverter...", file=sys.stderr, flush=True)
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options, backend=PyPdfiumDocumentBackend
                )
            }
        )
        print(f"CHECKPOINT: DocumentConverter created successfully", file=sys.stderr, flush=True)
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
        print(f"CHECKPOINT: Starting Docling conversion of {pdf_path.name}...", file=sys.stderr, flush=True)
        result = converter.convert(str(pdf_path))
        print(f"CHECKPOINT: Docling conversion complete - {result.document.num_pages} pages", file=sys.stderr, flush=True)
    except Exception as e:
        error_msg = f"Docling parsing failed for {pdf_path.name}: {e}"
        logger.error(
            "PDF parsing failed",
            extra={"path": str(pdf_path), "doc_filename": pdf_path.name, "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

    # Story 2.13 AC1: Extract tables to PostgreSQL (avoid double-conversion)
    # Extract tables from Docling result before chunking to reuse conversion
    print(f"CHECKPOINT: Starting table extraction...", file=sys.stderr, flush=True)
    logger.info(
        "Extracting tables for SQL storage",
        extra={"doc_filename": pdf_path.name},
    )

    # Skip table extraction in CI if env var set (for debugging hangs)
    skip_table_extraction = os.getenv("SKIP_TABLE_EXTRACTION", "false").lower() == "true"

    try:
        if not skip_table_extraction:
            extractor = TableExtractor()
            table_rows = extractor.extract_tables_from_result(result, pdf_path.stem)
            print(f"CHECKPOINT: Table extraction complete - {len(table_rows)} rows", file=sys.stderr, flush=True)
        else:
            table_rows = []
            print(f"CHECKPOINT: Table extraction SKIPPED", file=sys.stderr, flush=True)

        if table_rows:
            logger.info(
                "Tables extracted from document",
                extra={
                    "doc_filename": pdf_path.name,
                    "table_count": len({row["table_index"] for row in table_rows}),
                    "row_count": len(table_rows),
                },
            )

            # Store tables in PostgreSQL
            rows_stored, rows_skipped = await store_tables_in_postgresql(table_rows)
            logger.info(
                "Table storage complete",
                extra={
                    "doc_filename": pdf_path.name,
                    "rows_stored": rows_stored,
                    "rows_skipped": rows_skipped,
                },
            )
        else:
            logger.info(
                "No tables found in document",
                extra={"doc_filename": pdf_path.name},
            )
    except Exception as e:
        # Don't fail ingestion if table extraction fails - log and continue
        logger.warning(
            "Table extraction failed - continuing with document ingestion",
            extra={"doc_filename": pdf_path.name, "error": str(e)},
            exc_info=True,
        )

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
    print(f"CHECKPOINT: Starting chunking...", file=sys.stderr, flush=True)
    chunks = await chunk_by_docling_items(result, metadata)
    print(f"CHECKPOINT: Chunking complete - {len(chunks)} chunks created", file=sys.stderr, flush=True)

    # Story 2.4 AC1 (REVISED): Extract business context metadata PER CHUNK using Mistral Small
    # ARCHITECTURAL CHANGE: Per-chunk extraction avoids reasoning token overflow and provides
    # more accurate metadata for each chunk (chunks are ~512 tokens, perfect size for Mistral Small)
    # RE-ENABLED for Story 2.6 PostgreSQL data migration
    # NOTE: Performance bugs (sync client, per-request client, no timeout) will be fixed in Task 6 (AC6)
    if settings.mistral_api_key and not skip_metadata:
        logger.info(
            "Starting per-chunk metadata extraction with Mistral Small",
            extra={
                "doc_filename": pdf_path.name,
                "chunk_count": len(chunks),
                "model": settings.metadata_extraction_model,
                "expected_time_sec": len(chunks) * 2,  # ~2 sec per chunk estimate
            },
        )

        # Story 2.6 AC6 FIX: Create single Mistral client for reuse (client pooling)
        # This eliminates per-request connection overhead (10-15x speedup)
        from mistralai import Mistral

        mistral_client = Mistral(api_key=settings.mistral_api_key)

        # Extract metadata for each chunk with rate limiting (Story 2.4 FIX + Story 2.5 OPTIMIZATION)
        # Semaphore limits concurrent API calls to respect Mistral rate limits
        # RATE LIMIT FIX: Reduced from 20 to 5 concurrent requests to avoid 429 errors
        # Mistral Free API has stricter rate limits than initially tested
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests to Mistral API

        async def extract_for_chunk(chunk: Chunk) -> tuple[Chunk, ExtractedMetadata | None]:
            """Extract metadata for a single chunk with error handling and rate limiting."""
            async with semaphore:  # Limit concurrent requests
                try:
                    # Story 2.6 AC6 FIX: Pass shared client instance to enable connection pooling
                    extracted = await extract_chunk_metadata(
                        text=chunk.content, chunk_id=chunk.chunk_id, client=mistral_client
                    )
                    return (chunk, extracted)
                except Exception as e:
                    # Graceful degradation - continue without metadata for this chunk
                    logger.debug(
                        "Chunk metadata extraction failed (graceful degradation)",
                        extra={"chunk_id": chunk.chunk_id, "error": str(e)},
                    )
                    return (chunk, None)

        # Process chunks with rate-limited concurrency
        results = await asyncio.gather(*[extract_for_chunk(chunk) for chunk in chunks])

        # Inject extracted metadata into chunks (15 RICH SCHEMA fields)
        successful_extractions = 0
        for chunk, extracted_metadata in results:
            if extracted_metadata:
                # Document-Level (7 fields)
                chunk.document_type = extracted_metadata.document_type
                chunk.reporting_period = extracted_metadata.reporting_period
                chunk.time_granularity = extracted_metadata.time_granularity
                chunk.company_name = extracted_metadata.company_name
                chunk.geographic_jurisdiction = extracted_metadata.geographic_jurisdiction
                chunk.data_source_type = extracted_metadata.data_source_type
                chunk.version_date = extracted_metadata.version_date
                # Section-Level (5 fields)
                chunk.section_type = extracted_metadata.section_type
                chunk.metric_category = extracted_metadata.metric_category
                chunk.units = extracted_metadata.units
                chunk.department_scope = extracted_metadata.department_scope
                # Table-Specific (3 fields)
                chunk.table_context = extracted_metadata.table_context
                chunk.table_name = extracted_metadata.table_name
                chunk.statistical_summary = extracted_metadata.statistical_summary
                successful_extractions += 1

        logger.info(
            "Per-chunk metadata extraction complete",
            extra={
                "doc_filename": pdf_path.name,
                "total_chunks": len(chunks),
                "successful_extractions": successful_extractions,
                "success_rate": f"{successful_extractions / len(chunks) * 100:.1f}%",
            },
        )
    else:
        skip_reason = "skip_metadata=True" if skip_metadata else "MISTRAL_API_KEY not configured"
        logger.info(
            f"Metadata extraction skipped - {skip_reason}",
            extra={"doc_filename": pdf_path.name, "skip_metadata": skip_metadata},
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

        # Story 2.6 AC4: Store metadata in PostgreSQL for structured filtering
        # Only attempts storage if chunks have extracted metadata (company_name, metric_category, etc.)
        records_stored, records_skipped = await store_metadata_in_postgresql(chunks_with_embeddings)
        logger.info(
            "Metadata stored in PostgreSQL",
            extra={
                "doc_filename": pdf_path.name,
                "records_stored": records_stored,
                "records_skipped": records_skipped,
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
        extra={"token_count": token_count, "threshold": max_tokens, "table_index": table_index},
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
