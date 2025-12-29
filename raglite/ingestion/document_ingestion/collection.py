"""Document collection management for parallel ingestion.

Handles batch ingestion operations with concurrency control.
"""

from __future__ import annotations

import asyncio
import time

from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import BatchIngestionResult, DocumentMetadata

logger = get_logger(__name__)


async def ingest_documents_parallel(
    file_paths: list[str],
    max_concurrent: int | None = None,
) -> BatchIngestionResult:
    """Ingest multiple documents in parallel with concurrency control.

    Story 5.0.6 AC1: Parallel document ingestion with memory-safe concurrency limits.
    Uses asyncio.Semaphore to limit concurrent ingestions and prevent memory exhaustion.

    Args:
        file_paths: List of document file paths to ingest (PDF, Excel)
        max_concurrent: Maximum concurrent documents (default: settings.ingestion_parallel_docs).
                       Set to 1 for sequential processing, 2-4 for parallel.

    Returns:
        BatchIngestionResult with success/failure counts and per-document results

    Raises:
        ValueError: If file_paths is empty or max_concurrent < 1

    Example:
        >>> paths = ["report1.pdf", "report2.pdf", "data.xlsx"]
        >>> result = await ingest_documents_parallel(paths, max_concurrent=2)
        >>> print(f"Success: {result.successful}/{result.total_documents}")
        Success: 3/3
        >>> print(f"Duration: {result.duration_seconds:.1f}s")
        Duration: 45.2s

    Performance (Story 5.0.6 AC8):
        - Sequential (max_concurrent=1): ~4-5 hours for 10 PDFs (40 pages each)
        - Parallel (max_concurrent=2): ~45 minutes for 10 PDFs (6-10x speedup target)
        - Memory usage: ~4GB per concurrent document, max 8GB with default limit
    """
    # Import here to avoid circular dependency
    from raglite.ingestion.document_ingestion.core import ingest_document

    # AC1: Validation
    if not file_paths:
        raise ValueError("file_paths cannot be empty")

    # AC1: Use config default if not specified
    if max_concurrent is None:
        max_concurrent = settings.ingestion_parallel_docs

    if max_concurrent < 1:
        raise ValueError(f"max_concurrent must be >= 1, got {max_concurrent}")

    # Start timing for batch
    batch_start = time.time()
    total_docs = len(file_paths)

    logger.info(
        "Starting parallel document ingestion",
        extra={
            "total_documents": total_docs,
            "max_concurrent": max_concurrent,
            "batch_size": total_docs,
        },
    )

    # AC1: Semaphore for concurrency control (max 2 by default to stay within 8GB memory)
    semaphore = asyncio.Semaphore(max_concurrent)

    # AC3: Create shared unit cache for cross-document inference (30% API reduction)
    # Cache persists across all documents in the batch, enabling metric unit reuse
    shared_unit_cache: dict[str, str] = {}

    # Results tracking
    successful_results: list[DocumentMetadata] = []
    error_details: list[dict[str, str]] = []
    completed_count = 0

    async def process_document(file_path: str, doc_index: int) -> None:
        """Process single document with semaphore control and error handling."""
        nonlocal completed_count

        async with semaphore:
            try:
                # AC1/AC8: Progress logging (before processing)
                logger.info(
                    "Processing document",
                    extra={
                        "doc_index": doc_index + 1,
                        "total_documents": total_docs,
                        "file_path": file_path,
                        "concurrent_slots": max_concurrent,
                    },
                )

                # AC3: Ingest document with shared cache for cross-document unit reuse
                metadata = await ingest_document(file_path, unit_cache=shared_unit_cache)

                successful_results.append(metadata)
                completed_count += 1

                # AC1/AC8: Progress logging (after success)
                logger.info(
                    "Document ingested successfully",
                    extra={
                        "doc_index": doc_index + 1,
                        "total_documents": total_docs,
                        "completed": completed_count,
                        "file_path": file_path,
                        "chunk_count": metadata.chunk_count,
                        "page_count": metadata.page_count,
                    },
                )

            except Exception as e:
                # AC1: Error tracking (don't fail entire batch on single document error)
                error_msg = str(e)
                error_details.append({"filename": str(file_path), "error": error_msg})
                completed_count += 1

                logger.error(
                    "Document ingestion failed",
                    extra={
                        "doc_index": doc_index + 1,
                        "total_documents": total_docs,
                        "completed": completed_count,
                        "file_path": file_path,
                        "error": error_msg,
                    },
                )

    # AC1: Launch all ingestion tasks (asyncio schedules them with semaphore control)
    tasks = [process_document(path, idx) for idx, path in enumerate(file_paths)]
    await asyncio.gather(*tasks)

    # Calculate batch duration
    batch_duration = time.time() - batch_start

    # AC1/AC8: Final batch summary logging
    success_count = len(successful_results)
    fail_count = len(error_details)
    total_chunks = sum(m.chunk_count for m in successful_results)
    total_pages = sum(m.page_count for m in successful_results)

    logger.info(
        "Parallel batch ingestion complete",
        extra={
            "total_documents": total_docs,
            "successful": success_count,
            "failed": fail_count,
            "duration_seconds": round(batch_duration, 1),
            "duration_minutes": round(batch_duration / 60, 1),
            "docs_per_minute": round(success_count / (batch_duration / 60), 2)
            if batch_duration > 0
            else 0,
            "total_chunks": total_chunks,
            "total_pages": total_pages,
            "max_concurrent": max_concurrent,
        },
    )

    # AC1: Return BatchIngestionResult
    return BatchIngestionResult(
        total_documents=total_docs,
        successful=success_count,
        failed=fail_count,
        duration_seconds=round(batch_duration, 2),
        results=successful_results,
        errors=error_details,
    )
