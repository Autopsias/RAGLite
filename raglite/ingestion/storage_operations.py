"""Storage operations for Qdrant vector database and PostgreSQL metadata.

Handles vector storage, metadata storage, and SQL table storage for the RAG pipeline.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from psycopg2.extras import execute_values
from qdrant_client.models import (
    Distance,
    PointStruct,
    SparseIndexParams,
    SparseVectorParams,
    VectorParams,
)

from raglite.shared.bm25 import create_bm25_index, save_bm25_index
from raglite.shared.clients import get_postgresql_connection, get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk
from raglite.shared.safety import SafetyGuard

logger = get_logger(__name__)

# Story 4.0.6: SafetyGuard instance for environment audit logging
_guard = SafetyGuard()


# Exception class for storage operations
class VectorStorageError(Exception):
    """Raised when vector storage operations fail."""

    pass


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
        # Story 4.0.6: Log environment for audit trail
        _guard.log_operation(f"create_collection:{collection_name}")
        logger.info(
            "Creating Qdrant collection",
            extra={
                "collection": collection_name,
                "vector_size": vector_size,
                "distance": distance.name,
                "indexing": "HNSW (default)",
                "sparse_vectors": "enabled (BM25)",
                "environment": "PRODUCTION" if _guard.is_production else "TEST",
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

    # Story 4.0.6: Log environment for audit trail
    _guard.log_operation(f"store_vectors:{collection_name}")
    logger.info(
        "Storing vectors in Qdrant",
        extra={
            "chunk_count": len(chunks),
            "collection": collection_name,
            "batch_size": batch_size,
            "environment": "PRODUCTION" if _guard.is_production else "TEST",
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
                "chunks_per_second": (
                    round(len(chunks) / (duration_ms / 1000), 2) if duration_ms > 0 else 0
                ),
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
    start_time = time.time()

    # Story 4.0.6: Log environment for audit trail
    _guard.log_operation("store_metadata_postgresql")
    logger.info(
        "Storing metadata in PostgreSQL",
        extra={
            "chunk_count": len(chunks),
            "batch_size": batch_size,
            "environment": "PRODUCTION" if _guard.is_production else "TEST",
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
                chunk.metadata.filename,  # document_id: use source document filename
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
                "records_per_second": (
                    round(len(chunks_with_metadata) / (duration_ms / 1000), 2)
                    if duration_ms > 0
                    else 0
                ),
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
    start_time = time.time()

    # Story 4.0.6: Log environment for audit trail
    _guard.log_operation("store_tables_postgresql")
    logger.info(
        "Storing table data in PostgreSQL",
        extra={
            "row_count": len(table_rows),
            "batch_size": batch_size,
            "environment": "PRODUCTION" if _guard.is_production else "TEST",
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
        skipped_no_document_id = 0
        for row in valid_rows:
            # CRITICAL FIX (EXC-006): Validate document_id is present
            # Some table extraction paths may not set document_id, causing
            # source attribution to fail with source_document='unknown'
            document_id = row.get("document_id")
            if not document_id:
                skipped_no_document_id += 1
                logger.warning(
                    "Skipping table row with missing document_id",
                    extra={
                        "row_index": row.get("row_index"),
                        "table_index": row.get("table_index"),
                        "entity": row.get("entity"),
                        "metric": row.get("metric"),
                    },
                )
                continue

            record = (
                document_id,
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
                "records_stored": len(records),
                "records_skipped": skipped_count,
                "records_skipped_no_document_id": skipped_no_document_id,
                "duration_ms": duration_ms,
                "records_per_second": (
                    round(len(valid_rows) / (duration_ms / 1000), 2) if duration_ms > 0 else 0
                ),
            },
        )

        # Return actual records stored (may be less than valid_rows if some had no document_id)
        total_skipped = skipped_count + skipped_no_document_id
        return (len(records), total_skipped)

    except Exception as e:
        logger.error(
            "PostgreSQL table storage failed",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(f"Failed to store tables in PostgreSQL: {e}") from e
