"""In-memory job tracking for async document ingestion.

Story 4.0.3 AC5: Simple in-memory job tracker for MVP.
No persistence required - jobs lost on server restart (acceptable for MVP).
"""

import asyncio
import uuid
from datetime import UTC, datetime

from raglite.shared.logging import get_logger
from raglite.shared.models import DocumentMetadata, IngestionJobStatus

logger = get_logger(__name__)

# In-memory job storage
# Format: {job_id: IngestionJobStatus}
_jobs: dict[str, IngestionJobStatus] = {}


def create_job(doc_path: str) -> str:
    """Create a new async ingestion job and return job ID.

    Args:
        doc_path: Path to document being ingested

    Returns:
        Unique job ID (UUID v4)
    """
    job_id = str(uuid.uuid4())

    job_status = IngestionJobStatus(
        job_id=job_id,
        status="pending",
        progress=0,
        started_at=datetime.now(UTC).isoformat(),
    )

    _jobs[job_id] = job_status

    logger.info(
        "Async ingestion job created",
        extra={"job_id": job_id, "doc_path": doc_path},
    )

    return job_id


def update_job_status(
    job_id: str,
    status: str,
    progress: int | None = None,
    result: DocumentMetadata | None = None,
    error: str | None = None,
) -> None:
    """Update job status in memory.

    Args:
        job_id: Job identifier
        status: New status ('pending', 'in_progress', 'completed', 'failed')
        progress: Progress percentage (0-100)
        result: Ingestion result (only for 'completed')
        error: Error message (only for 'failed')
    """
    if job_id not in _jobs:
        logger.warning("Attempted to update non-existent job", extra={"job_id": job_id})
        return

    job = _jobs[job_id]
    job.status = status

    if progress is not None:
        job.progress = progress

    if result is not None:
        job.result = result

    if error is not None:
        job.error = error

    # Set completion timestamp for terminal states
    if status in ["completed", "failed"]:
        job.completed_at = datetime.now(UTC).isoformat()

    logger.info(
        "Job status updated",
        extra={
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "has_result": result is not None,
            "has_error": error is not None,
        },
    )


def get_job_status(job_id: str) -> IngestionJobStatus | None:
    """Get current job status.

    Args:
        job_id: Job identifier

    Returns:
        IngestionJobStatus or None if job not found
    """
    return _jobs.get(job_id)


async def run_async_ingestion(job_id: str, doc_path: str) -> None:
    """Run document ingestion in background and update job status.

    Args:
        job_id: Job identifier for status updates
        doc_path: Path to document file
    """
    from raglite.ingestion.pipeline import ingest_document

    try:
        # Update to in_progress
        update_job_status(job_id, "in_progress", progress=10)

        logger.info(
            "Starting async ingestion",
            extra={"job_id": job_id, "doc_path": doc_path},
        )

        # Run ingestion (this will take minutes for large PDFs)
        metadata = await ingest_document(doc_path)

        # Mark as completed
        update_job_status(job_id, "completed", progress=100, result=metadata)

        logger.info(
            "Async ingestion completed",
            extra={
                "job_id": job_id,
                "doc_id": metadata.filename,
                "chunks": metadata.chunk_count,
                "pages": metadata.page_count,
            },
        )

    except Exception as e:
        # Mark as failed
        error_msg = f"Ingestion failed: {str(e)}"
        update_job_status(job_id, "failed", error=error_msg)

        logger.error(
            "Async ingestion failed",
            extra={
                "job_id": job_id,
                "doc_path": doc_path,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )


def start_background_job(job_id: str, doc_path: str) -> None:
    """Start background ingestion job (fire-and-forget).

    Args:
        job_id: Job identifier
        doc_path: Path to document file
    """
    # Create background task (fire-and-forget)
    asyncio.create_task(run_async_ingestion(job_id, doc_path))

    logger.info(
        "Background ingestion job started",
        extra={"job_id": job_id, "doc_path": doc_path},
    )
