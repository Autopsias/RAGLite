"""PDF processing utilities and helper functions.

Extracted from pdf_processing.py to maintain file size limits.
"""

from __future__ import annotations

__all__ = [
    "clear_existing_data",
    "create_qdrant_collection",
    "extract_metadata_for_chunks",
]

import asyncio
from typing import TYPE_CHECKING, Any

from qdrant_client.models import Distance, SparseIndexParams, SparseVectorParams, VectorParams

from raglite.ingestion.embedding_generation import extract_chunk_metadata
from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

    from raglite.shared.models import Chunk, ExtractedMetadata

logger = get_logger(__name__)


async def clear_existing_data(force_production: bool = False) -> None:
    """Clear existing Qdrant collection and PostgreSQL tables.

    Story 4.0.6: SafetyGuard protection enforced by caller.

    Args:
        force_production: If True, allows clearing production database.
                         Required for intentional production data replacement.
    """
    from raglite.shared.safety import SafetyGuard

    guard = SafetyGuard()

    # AC1/AC2: Check environment before destructive operation
    guard.check_environment("clear_collection", force_production=force_production)

    # AC2: Require confirmation in interactive mode for production
    if guard.is_production and not force_production:
        if not guard.require_confirmation("About to DELETE ALL DATA in production database"):
            raise SystemExit("Operation cancelled by user")

    client = get_qdrant_client()
    try:
        client.delete_collection(settings.qdrant_collection_name)
        logger.info(
            "Cleared existing collection",
            extra={
                "collection": settings.qdrant_collection_name,
                "environment": "PRODUCTION" if guard.is_production else "TEST",
            },
        )
    except Exception:
        logger.info(
            "Collection doesn't exist, will create new",
            extra={"collection": settings.qdrant_collection_name},
        )

    # CRITICAL FIX: Also clear PostgreSQL to maintain symmetric data lifecycle
    # This prevents mixed document IDs from accumulating across ingestion runs
    try:
        import psycopg2

        conn_str = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()

        # Delete all data from both PostgreSQL tables
        cursor.execute("DELETE FROM financial_chunks")
        chunks_deleted = cursor.rowcount
        cursor.execute("DELETE FROM financial_tables")
        tables_deleted = cursor.rowcount

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(
            "Cleared PostgreSQL tables",
            extra={
                "financial_chunks_deleted": chunks_deleted,
                "financial_tables_deleted": tables_deleted,
                "environment": "PRODUCTION" if guard.is_production else "TEST",
            },
        )
    except Exception as e:
        logger.warning(
            "Failed to clear PostgreSQL tables (might not exist yet)",
            extra={"error": str(e)},
        )


def create_qdrant_collection(client: QdrantClient) -> None:
    """Create Qdrant collection with proper configuration.

    Args:
        client: Qdrant client instance
    """
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
            extra={
                "collection": settings.qdrant_collection_name,
                "vector_size": 1024,
            },
        )
    except Exception as e:
        logger.warning(
            "Collection may already exist",
            extra={"collection": settings.qdrant_collection_name, "error": str(e)},
        )


async def extract_metadata_for_chunks(
    chunks: list[Chunk],
    doc_filename: str,
    mistral_client: Any,
    skip_metadata: bool = False,
) -> int:
    """Extract business context metadata for all chunks using Mistral Small.

    Story 2.4 AC1 (REVISED): Per-chunk extraction avoids reasoning token overflow
    and provides more accurate metadata for each chunk.

    Args:
        chunks: List of chunks to extract metadata for
        doc_filename: Name of source document (for logging)
        mistral_client: Shared Mistral client instance
        skip_metadata: If True, skips metadata extraction

    Returns:
        Number of successful metadata extractions
    """
    if not settings.mistral_api_key or skip_metadata:
        skip_reason = "skip_metadata=True" if skip_metadata else "MISTRAL_API_KEY not configured"
        logger.info(
            f"Metadata extraction skipped - {skip_reason}",
            extra={"doc_filename": doc_filename, "skip_metadata": skip_metadata},
        )
        return 0

    logger.info(
        "Starting per-chunk metadata extraction with Mistral Small",
        extra={
            "doc_filename": doc_filename,
            "chunk_count": len(chunks),
            "model": settings.metadata_extraction_model,
            "expected_time_sec": len(chunks) * 2,  # ~2 sec per chunk estimate
        },
    )

    # Story 2.5 OPTIMIZATION: Semaphore limits concurrent API calls
    # RATE LIMIT FIX: Reduced from 20 to 5 concurrent requests to avoid 429 errors
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests to Mistral API

    async def extract_for_chunk(
        chunk: Chunk,
    ) -> tuple[Chunk, ExtractedMetadata | None]:
        """Extract metadata for a single chunk with error handling and rate limiting."""
        async with semaphore:  # Limit concurrent requests
            try:
                # Story 2.6 AC6 FIX: Pass shared client instance to enable connection pooling
                extracted = await extract_chunk_metadata(
                    text=chunk.content,
                    chunk_id=chunk.chunk_id,
                    client=mistral_client,
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

    # Calculate success rate, handling empty chunks case
    success_rate = (
        "0.0%" if len(chunks) == 0 else f"{successful_extractions / len(chunks) * 100:.1f}%"
    )

    logger.info(
        "Per-chunk metadata extraction complete",
        extra={
            "doc_filename": doc_filename,
            "total_chunks": len(chunks),
            "successful_extractions": successful_extractions,
            "success_rate": success_rate,
        },
    )

    return successful_extractions
