"""Document ingestion MCP tools."""

import time

from raglite.ingestion.document_ingestion.temp_files import (
    temp_file_from_base64,
    temp_file_from_url,
)
from raglite.ingestion.job_tracker import create_job, get_job_status, start_background_job
from raglite.ingestion.pipeline import ingest_document
from raglite.main import mcp
from raglite.mcp.tools.ingestion_helpers import (
    DocumentProcessingError,
    _create_temp_file_from_base64,
    _download_document_from_url,
    _perform_forecast_refresh,
    _prepare_path_for_async,
    _validate_ingestion_inputs,
)
from raglite.shared.logging import get_logger
from raglite.shared.models import (
    AsyncIngestionResponse,
    IngestionJobStatus,
    IngestionResult,
)

logger = get_logger(__name__)


async def _ingest_from_url(
    doc_url: str,
    auto_forecast: bool,
    retrain_models: bool = False,
) -> IngestionResult:
    """Ingest document from URL.

    Args:
        doc_url: URL to download document from
        auto_forecast: Whether to trigger forecast refresh
        retrain_models: Whether to trigger model retraining after ingestion

    Returns:
        IngestionResult with metadata and forecast status
    """
    logger.info(
        "Ingesting document from URL",
        extra={"url_truncated": doc_url[:80] + "..." if len(doc_url) > 80 else doc_url},
    )
    try:
        with temp_file_from_url(doc_url) as (tmp_path, detected_filename):
            start_time = time.perf_counter()
            metadata = await ingest_document(tmp_path)
            duration_ms = (time.perf_counter() - start_time) * 1000
            metadata.filename = detected_filename
            logger.info(
                "Ingestion complete (URL)",
                extra={
                    "doc_id": metadata.filename,
                    "doc_type": metadata.doc_type,
                    "chunks": metadata.chunk_count,
                    "pages": metadata.page_count,
                    "duration_ms": f"{duration_ms:.2f}",
                    "input_mode": "url",
                },
            )
            return await _perform_forecast_refresh(metadata, auto_forecast, retrain_models)
    except ValueError as e:
        logger.error(
            "URL ingestion failed - validation error",
            extra={"url_truncated": doc_url[:80], "error": str(e)},
        )
        raise DocumentProcessingError(str(e)) from e
    except RuntimeError as e:
        logger.error(
            "URL ingestion failed - download error",
            extra={"url_truncated": doc_url[:80], "error": str(e)},
        )
        raise DocumentProcessingError(str(e)) from e
    except Exception as e:
        logger.error(
            "Ingestion failed (URL)",
            extra={
                "url_truncated": doc_url[:80],
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise DocumentProcessingError(f"Failed to ingest from URL: {e}") from e


async def _ingest_from_base64(
    file_content: str,
    filename: str,
    auto_forecast: bool,
    retrain_models: bool = False,
) -> IngestionResult:
    """Ingest document from base64 content.

    Args:
        file_content: Base64-encoded file content
        filename: Original filename with extension
        auto_forecast: Whether to trigger forecast refresh
        retrain_models: Whether to trigger model retraining after ingestion

    Returns:
        IngestionResult with metadata and forecast status
    """
    logger.info(
        "Ingesting document from base64 content",
        extra={"doc_filename": filename, "content_size": len(file_content)},
    )
    try:
        with temp_file_from_base64(file_content, filename) as tmp_path:
            start_time = time.perf_counter()
            metadata = await ingest_document(tmp_path)
            duration_ms = (time.perf_counter() - start_time) * 1000
            metadata.filename = filename
            logger.info(
                "Ingestion complete (base64)",
                extra={
                    "doc_id": metadata.filename,
                    "doc_type": metadata.doc_type,
                    "chunks": metadata.chunk_count,
                    "pages": metadata.page_count,
                    "duration_ms": f"{duration_ms:.2f}",
                    "input_mode": "base64",
                },
            )
            return await _perform_forecast_refresh(metadata, auto_forecast, retrain_models)
    except ValueError as e:
        logger.error(
            "Base64 ingestion failed - validation error",
            extra={"doc_filename": filename, "error": str(e)},
        )
        raise DocumentProcessingError(str(e)) from e
    except Exception as e:
        logger.error(
            "Ingestion failed (base64)",
            extra={
                "doc_filename": filename,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise DocumentProcessingError(f"Failed to ingest {filename}: {e}") from e


async def _ingest_from_path(
    doc_path: str,
    auto_forecast: bool,
    retrain_models: bool = False,
) -> IngestionResult:
    """Ingest document from filesystem path.

    Args:
        doc_path: Path to document file
        auto_forecast: Whether to trigger forecast refresh
        retrain_models: Whether to trigger model retraining after ingestion

    Returns:
        IngestionResult with metadata and forecast status
    """
    effective_path = doc_path
    logger.info("Ingesting document", extra={"path": effective_path})
    try:
        start_time = time.perf_counter()
        metadata = await ingest_document(effective_path)
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Ingestion complete",
            extra={
                "doc_id": metadata.filename,
                "doc_type": metadata.doc_type,
                "chunks": metadata.chunk_count,
                "pages": metadata.page_count,
                "duration_ms": f"{duration_ms:.2f}",
                "input_mode": "path",
            },
        )
        return await _perform_forecast_refresh(metadata, auto_forecast, retrain_models)
    except FileNotFoundError as e:
        logger.error(
            "Document not found",
            extra={"path": effective_path, "error": str(e)},
            exc_info=True,
        )
        raise DocumentProcessingError(f"Document not found: {effective_path}") from e
    except Exception as e:
        logger.error(
            "Ingestion failed",
            extra={
                "path": effective_path,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise DocumentProcessingError(f"Failed to ingest {effective_path}: {e}") from e


@mcp.tool()
async def ingest_financial_document(
    doc_path: str | None = None,
    file_content: str | None = None,
    filename: str | None = None,
    doc_url: str | None = None,
    auto_forecast: bool = True,
    retrain_models: bool = False,
) -> IngestionResult:
    """Ingest financial document from path, base64 content, or URL.

    Args:
        doc_path: Filesystem path to document
        file_content: Base64-encoded file content
        filename: Original filename (required with file_content)
        doc_url: URL to download document from
        auto_forecast: Whether to trigger forecast refresh after ingestion
        retrain_models: Whether to trigger full model retraining after ingestion.
            This is slow (~5 min) but ensures forecasting models are up-to-date
            with the latest data. Use sparingly, typically after major data updates.

    Returns:
        IngestionResult with document metadata and forecast status

    Raises:
        DocumentProcessingError: If inputs are invalid or ingestion fails
    """
    has_path, has_content, has_url, _ = _validate_ingestion_inputs(
        doc_path, file_content, filename, doc_url
    )

    if has_url:
        assert doc_url is not None
        return await _ingest_from_url(doc_url, auto_forecast, retrain_models)
    elif has_content:
        assert file_content is not None and filename is not None
        return await _ingest_from_base64(file_content, filename, auto_forecast, retrain_models)
    else:
        assert doc_path is not None
        return await _ingest_from_path(doc_path, auto_forecast, retrain_models)


@mcp.tool()
async def ingest_financial_document_async(
    doc_path: str | None = None,
    file_content: str | None = None,
    filename: str | None = None,
    doc_url: str | None = None,
) -> AsyncIngestionResponse:
    """Start asynchronous ingestion of financial document.

    Args:
        doc_path: Filesystem path to document
        file_content: Base64-encoded file content
        filename: Original filename (required with file_content)
        doc_url: URL to download document from

    Returns:
        AsyncIngestionResponse with job_id to track progress

    Raises:
        DocumentProcessingError: If inputs are invalid
    """
    has_path, has_content, has_url, _ = _validate_ingestion_inputs(
        doc_path, file_content, filename, doc_url
    )

    effective_path: str
    display_name: str
    temp_path_to_cleanup: str | None = None
    original_filename: str | None = None

    if has_url:
        assert doc_url is not None
        effective_path, display_name, original_filename = _download_document_from_url(doc_url)
        temp_path_to_cleanup = effective_path
    elif has_content:
        assert file_content is not None and filename is not None
        effective_path, display_name, original_filename = _create_temp_file_from_base64(
            file_content, filename
        )
        temp_path_to_cleanup = effective_path
    else:
        assert doc_path is not None
        effective_path, display_name, original_filename = _prepare_path_for_async(doc_path)
        temp_path_to_cleanup = None

    job_id = create_job(effective_path)
    start_background_job(
        job_id,
        effective_path,
        temp_path_to_cleanup=temp_path_to_cleanup,
        original_filename=original_filename,
    )

    message = (
        f"Ingestion started for {display_name}. "
        f"Use get_ingestion_status('{job_id}') to check progress. "
        f"Large documents (150-200 pages) may take 15-30 minutes."
    )

    logger.info(
        "Async ingestion job started",
        extra={
            "job_id": job_id,
            "doc_path": effective_path,
            "input_mode": "base64" if has_content else "url" if has_url else "path",
        },
    )

    return AsyncIngestionResponse(
        job_id=job_id,
        status="started",
        message=message,
        estimated_time_s=None,
    )


@mcp.tool()
async def get_ingestion_status(job_id: str) -> IngestionJobStatus:
    logger.info("Checking job status", extra={"job_id": job_id})
    job_status = get_job_status(job_id)
    if job_status is None:
        error_msg = f"Job not found: {job_id}. Job may have expired or server restarted."
        logger.warning("Job status check failed - job not found", extra={"job_id": job_id})
        raise ValueError(error_msg)
    logger.info(
        "Job status retrieved",
        extra={
            "job_id": job_id,
            "status": job_status.status,
            "progress": job_status.progress,
        },
    )
    return job_status
