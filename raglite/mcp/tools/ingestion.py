"""Document ingestion MCP tools."""

import base64
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError

from raglite.forecasting.auto_update import trigger_forecast_refresh
from raglite.ingestion.document_ingestion import (
    ALLOWED_URL_SCHEMES,
    MAX_BASE64_CONTENT_SIZE_BYTES,
    MAX_URL_DOWNLOAD_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    URL_DOMAIN_ALLOWLIST,
    URL_DOWNLOAD_TIMEOUT_TOTAL,
    temp_file_from_base64,
    temp_file_from_url,
)
from raglite.ingestion.job_tracker import create_job, get_job_status, start_background_job
from raglite.ingestion.pipeline import ingest_document
from raglite.main import mcp
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import (
    AsyncIngestionResponse,
    DocumentMetadata,
    IngestionJobStatus,
    IngestionResult,
)

logger = get_logger(__name__)


class DocumentProcessingError(Exception):
    pass


async def _perform_forecast_refresh(
    metadata: DocumentMetadata,
    auto_forecast: bool,
) -> IngestionResult:
    forecasts_updated: list[str] | None = None
    forecast_skip_reason: str | None = None
    if not auto_forecast:
        forecast_skip_reason = "auto_forecast=False"
    elif not settings.enable_forecast_auto_update:
        forecast_skip_reason = "forecast_auto_update disabled in settings"
    else:
        try:
            refresh_result = await trigger_forecast_refresh(
                metadata, timeout_seconds=settings.forecast_refresh_timeout
            )
            if refresh_result.success:
                forecasts_updated = refresh_result.metrics_refreshed
                if refresh_result.metrics_skipped:
                    logger.info(
                        "Some metrics skipped during forecast refresh",
                        extra={
                            "doc_filename": metadata.filename,
                            "skipped": refresh_result.metrics_skipped,
                        },
                    )
            else:
                forecast_skip_reason = refresh_result.error_message or "refresh failed"
                logger.warning(
                    "Forecast refresh failed",
                    extra={
                        "doc_filename": metadata.filename,
                        "error": forecast_skip_reason,
                    },
                )
        except Exception as e:
            forecast_skip_reason = f"unexpected error: {type(e).__name__}"
            logger.warning(
                "Forecast refresh failed unexpectedly",
                extra={"doc_filename": metadata.filename, "error": str(e)},
            )
    return IngestionResult.from_metadata(
        metadata,
        forecasts_updated=forecasts_updated,
        forecast_refresh_skipped_reason=forecast_skip_reason,
    )


@mcp.tool()
async def ingest_financial_document(
    doc_path: str | None = None,
    file_content: str | None = None,
    filename: str | None = None,
    doc_url: str | None = None,
    auto_forecast: bool = True,
) -> IngestionResult:
    has_path = doc_path is not None
    has_content = file_content is not None
    has_filename = filename is not None
    has_url = doc_url is not None
    input_modes = sum([has_path, has_content, has_url])
    if input_modes == 0:
        raise DocumentProcessingError(
            "Must provide one of: doc_path, file_content+filename, or doc_url"
            "⚠️  If you dragged a file into Claude.ai or Claude Desktop, use Mode 3:\n"
            "    1. Upload file to Google Drive/Dropbox/S3\n"
            "    2. Get shareable download link\n"
            "    3. Call this tool with doc_url parameter"
        )
    if input_modes > 1:
        raise DocumentProcessingError("Only one input mode allowed")
    if has_content and not has_filename:
        raise DocumentProcessingError(
            "filename is required when using file_content. "
            "Provide the original filename with extension (e.g., 'report.pdf')."
        )
    if has_url:
        assert doc_url is not None
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
                return await _perform_forecast_refresh(metadata, auto_forecast)
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
    elif has_content:
        assert file_content is not None and filename is not None
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
                return await _perform_forecast_refresh(metadata, auto_forecast)
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
    else:
        assert doc_path is not None
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
            return await _perform_forecast_refresh(metadata, auto_forecast)
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
async def ingest_financial_document_async(
    doc_path: str | None = None,
    file_content: str | None = None,
    filename: str | None = None,
    doc_url: str | None = None,
) -> AsyncIngestionResponse:
    import urllib.request

    has_path = doc_path is not None
    has_content = file_content is not None
    has_filename = filename is not None
    has_url = doc_url is not None
    input_modes = sum([has_path, has_content, has_url])
    if input_modes == 0:
        raise DocumentProcessingError(
            "Must provide one of: doc_path, file_content + filename, or doc_url.\n"
            "For Claude.ai/Desktop: Use doc_url with a shareable download link."
        )
    if input_modes > 1:
        raise DocumentProcessingError("Only one input mode allowed")
    if has_content and not has_filename:
        raise DocumentProcessingError(
            "filename is required when using file_content. "
            "Provide the original filename with extension (e.g., 'report.pdf')."
        )
    effective_path: str
    display_name: str
    temp_path_to_cleanup: str | None = None
    original_filename: str | None = None
    if has_url:
        assert doc_url is not None
        logger.info(
            "Async ingestion requested (URL)",
            extra={"url_truncated": doc_url[:80] + "..." if len(doc_url) > 80 else doc_url},
        )
        parsed = urllib.parse.urlparse(doc_url)
        if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
            raise DocumentProcessingError(
                f"URL scheme '{parsed.scheme}' not allowed. Use http or https."
            )
        if URL_DOMAIN_ALLOWLIST and parsed.netloc.lower() not in URL_DOMAIN_ALLOWLIST:
            raise DocumentProcessingError(f"Domain '{parsed.netloc}' not in allowlist.")
        url_path = urllib.parse.unquote(parsed.path)
        filename_from_url = Path(url_path).name if url_path else "downloaded_document"
        try:
            request = urllib.request.Request(
                doc_url,
                headers={
                    "User-Agent": "RAGLite/1.0 (Financial Document Ingestion)",
                    "Accept": "application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, */*",
                },
            )
            with urllib.request.urlopen(request, timeout=URL_DOWNLOAD_TIMEOUT_TOTAL) as response:
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_URL_DOWNLOAD_SIZE_BYTES:
                    raise DocumentProcessingError(
                        f"File too large. Maximum: {MAX_URL_DOWNLOAD_SIZE_BYTES / (1024 * 1024):.0f}MB"
                    )
                content_disposition = response.headers.get("Content-Disposition", "")
                if "filename=" in content_disposition:
                    import re

                    match = re.search(r'filename[*]?=["\']?([^"\';\n]+)', content_disposition)
                    if match:
                        filename_from_url = match.group(1).strip()
                suffix = Path(filename_from_url).suffix.lower()
                if not suffix:
                    content_type = response.headers.get("Content-Type", "")
                    if "pdf" in content_type:
                        suffix = ".pdf"
                        filename_from_url = "downloaded_document.pdf"
                    elif "spreadsheet" in content_type or "excel" in content_type:
                        suffix = ".xlsx"
                        filename_from_url = "downloaded_document.xlsx"
                    else:
                        raise DocumentProcessingError(
                            "Cannot determine file type from URL. "
                            "Ensure URL ends with .pdf, .xlsx, or .xls"
                        )
                if suffix not in SUPPORTED_EXTENSIONS:
                    raise DocumentProcessingError(
                        f"Unsupported file type: {suffix}. Supported: .pdf, .xlsx, .xls"
                    )
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    downloaded_size = 0
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        downloaded_size += len(chunk)
                        if downloaded_size > MAX_URL_DOWNLOAD_SIZE_BYTES:
                            raise DocumentProcessingError("Download exceeded size limit")
                        tmp.write(chunk)
                    temp_path = tmp.name
                effective_path = temp_path
                display_name = filename_from_url
                temp_path_to_cleanup = temp_path
                original_filename = filename_from_url
                logger.info(
                    "Downloaded file for async ingestion",
                    extra={
                        "url_domain": parsed.netloc,
                        "filename": filename_from_url,
                        "size_bytes": downloaded_size,
                        "temp_path": temp_path,
                    },
                )
        except HTTPError as e:
            raise DocumentProcessingError(f"URL download failed: HTTP {e.code} {e.reason}") from e
        except URLError as e:
            raise DocumentProcessingError(f"URL download failed: {e.reason}") from e
        except TimeoutError:
            raise DocumentProcessingError(
                f"Download timed out after {URL_DOWNLOAD_TIMEOUT_TOTAL}s"
            ) from None
    elif has_content:
        assert file_content is not None and filename is not None
        logger.info(
            "Async ingestion requested (base64)",
            extra={"doc_filename": filename, "content_size": len(file_content)},
        )
        if len(file_content) > MAX_BASE64_CONTENT_SIZE_BYTES:
            size_mb = len(file_content) / (1024 * 1024)
            raise DocumentProcessingError(
                f"File content ({size_mb:.1f}MB encoded) exceeds 25MB limit. "
                "For larger files, save to filesystem and use doc_path parameter."
            )
        try:
            file_bytes = base64.b64decode(file_content)
        except Exception as e:
            raise DocumentProcessingError(f"Invalid base64 content: {e}") from e
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise DocumentProcessingError(
                f"Unsupported file type: {suffix}. Supported extensions: {supported}"
            )
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_bytes)
                temp_path = tmp.name
            effective_path = temp_path
            display_name = filename
            temp_path_to_cleanup = temp_path
            original_filename = filename
            logger.info(
                "Created persistent temp file for async base64 ingestion",
                extra={
                    "doc_filename": filename,
                    "temp_path": temp_path,
                    "size_bytes": len(file_bytes),
                },
            )
        except Exception as e:
            raise DocumentProcessingError(f"Failed to create temp file: {e}") from e
    else:
        assert doc_path is not None
        logger.info("Async ingestion requested", extra={"path": doc_path})
        doc_file = Path(doc_path).resolve()
        if not doc_file.exists():
            error_msg = f"Document not found: {doc_path}"
            logger.error(
                "Async ingestion failed - file not found",
                extra={"path": str(doc_file), "error": error_msg},
            )
            raise DocumentProcessingError(error_msg)
        effective_path = str(doc_file)
        display_name = doc_file.name
    job_id = create_job(effective_path)
    start_background_job(
        job_id,
        effective_path,
        temp_path_to_cleanup=temp_path_to_cleanup,
        original_filename=original_filename,
    )
    estimated_time_s = None
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
            "input_mode": "base64" if has_content else "path",
        },
    )
    return AsyncIngestionResponse(
        job_id=job_id,
        status="started",
        message=message,
        estimated_time_s=estimated_time_s,
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
