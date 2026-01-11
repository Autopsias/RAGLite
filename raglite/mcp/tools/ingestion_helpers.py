"""Helper functions for document ingestion MCP tools."""

import base64
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from raglite.ingestion.document_ingestion.constants import (
    ALLOWED_URL_SCHEMES,
    MAX_BASE64_CONTENT_SIZE_BYTES,
    MAX_URL_DOWNLOAD_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    URL_DOMAIN_ALLOWLIST,
    URL_DOWNLOAD_TIMEOUT_TOTAL,
)
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from raglite.shared.models import IngestionResult

logger = get_logger(__name__)


class DocumentProcessingError(Exception):
    pass


def _validate_ingestion_inputs(
    doc_path: str | None,
    file_content: str | None,
    filename: str | None,
    doc_url: str | None,
) -> tuple[bool, bool, bool, int]:
    """Validate ingestion input parameters.

    Returns:
        Tuple of (has_path, has_content, has_url, input_mode_count)

    Raises:
        DocumentProcessingError: If inputs are invalid
    """
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

    return has_path, has_content, has_url, input_modes


def _validate_and_parse_url(doc_url: str) -> tuple[str, str]:
    """Validate URL and extract filename.

    Args:
        doc_url: URL to validate

    Returns:
        Tuple of (filename_from_url, netloc)

    Raises:
        DocumentProcessingError: If URL is invalid
    """
    import urllib.request

    parsed = urllib.parse.urlparse(doc_url)
    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        raise DocumentProcessingError(
            f"URL scheme '{parsed.scheme}' not allowed. Use http or https."
        )
    if URL_DOMAIN_ALLOWLIST and parsed.netloc.lower() not in URL_DOMAIN_ALLOWLIST:
        raise DocumentProcessingError(f"Domain '{parsed.netloc}' not in allowlist.")

    url_path = urllib.parse.unquote(parsed.path)
    filename_from_url = Path(url_path).name if url_path else "downloaded_document"
    return filename_from_url, parsed.netloc


def _extract_filename_from_response(
    filename_from_url: str,
    response: Any,
) -> tuple[str, str]:
    """Extract filename and file suffix from HTTP response.

    Args:
        filename_from_url: Initial filename from URL path
        response: HTTP response object

    Returns:
        Tuple of (filename, suffix)

    Raises:
        DocumentProcessingError: If file type cannot be determined
    """
    import re

    content_disposition = response.headers.get("Content-Disposition", "")
    filename = filename_from_url
    if "filename=" in content_disposition:
        match = re.search(r'filename[*]?=["\']?([^"\';\n]+)', content_disposition)
        if match:
            filename = match.group(1).strip()

    suffix = Path(filename).suffix.lower()
    if not suffix:
        content_type = response.headers.get("Content-Type", "")
        if "pdf" in content_type:
            suffix = ".pdf"
            filename = "downloaded_document.pdf"
        elif "spreadsheet" in content_type or "excel" in content_type:
            suffix = ".xlsx"
            filename = "downloaded_document.xlsx"
        else:
            raise DocumentProcessingError(
                "Cannot determine file type from URL. Ensure URL ends with .pdf, .xlsx, or .xls"
            )
    return filename, suffix


def _download_document_from_url(
    doc_url: str,
) -> tuple[str, str, str]:
    """Download document from URL for async ingestion.

    Args:
        doc_url: URL to download from

    Returns:
        Tuple of (temp_path, display_name, original_filename)

    Raises:
        DocumentProcessingError: If download fails
    """
    import urllib.request

    logger.info(
        "Async ingestion requested (URL)",
        extra={"url_truncated": doc_url[:80] + "..." if len(doc_url) > 80 else doc_url},
    )

    filename_from_url, netloc = _validate_and_parse_url(doc_url)

    try:
        request = urllib.request.Request(
            doc_url,
            headers={
                "User-Agent": "RAGLite/1.0 (Financial Document Ingestion)",
                "Accept": "application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, */*",
            },
        )
        with urllib.request.urlopen(  # nosec
            request, timeout=URL_DOWNLOAD_TIMEOUT_TOTAL
        ) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_URL_DOWNLOAD_SIZE_BYTES:
                raise DocumentProcessingError(
                    f"File too large. Maximum: {MAX_URL_DOWNLOAD_SIZE_BYTES / (1024 * 1024):.0f}MB"
                )

            filename_from_url, suffix = _extract_filename_from_response(filename_from_url, response)

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

            logger.info(
                "Downloaded file for async ingestion",
                extra={
                    "url_domain": netloc,
                    "filename": filename_from_url,
                    "size_bytes": downloaded_size,
                    "temp_path": temp_path,
                },
            )
            return temp_path, filename_from_url, filename_from_url

    except urllib.error.HTTPError as e:
        raise DocumentProcessingError(f"URL download failed: HTTP {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise DocumentProcessingError(f"URL download failed: {e.reason}") from e
    except TimeoutError:
        raise DocumentProcessingError(
            f"Download timed out after {URL_DOWNLOAD_TIMEOUT_TOTAL}s"
        ) from None


def _create_temp_file_from_base64(
    file_content: str,
    filename: str,
) -> tuple[str, str, str]:
    """Create temporary file from base64 content for async ingestion.

    Args:
        file_content: Base64-encoded file content
        filename: Original filename

    Returns:
        Tuple of (temp_path, display_name, original_filename)

    Raises:
        DocumentProcessingError: If file creation fails
    """
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

        logger.info(
            "Created persistent temp file for async base64 ingestion",
            extra={
                "doc_filename": filename,
                "temp_path": temp_path,
                "size_bytes": len(file_bytes),
            },
        )
        return temp_path, filename, filename
    except Exception as e:
        raise DocumentProcessingError(f"Failed to create temp file: {e}") from e


def _prepare_path_for_async(
    doc_path: str,
) -> tuple[str, str, str | None]:
    """Prepare document path for async ingestion.

    Args:
        doc_path: Path to document

    Returns:
        Tuple of (effective_path, display_name, None)

    Raises:
        DocumentProcessingError: If file not found
    """
    logger.info("Async ingestion requested", extra={"path": doc_path})
    doc_file = Path(doc_path).resolve()
    if not doc_file.exists():
        error_msg = f"Document not found: {doc_path}"
        logger.error(
            "Async ingestion failed - file not found",
            extra={"path": str(doc_file), "error": error_msg},
        )
        raise DocumentProcessingError(error_msg)
    return str(doc_file), doc_file.name, None


async def _perform_forecast_refresh(
    metadata: Any,
    auto_forecast: bool,
) -> "IngestionResult":
    """Perform forecast refresh after document ingestion.

    Args:
        metadata: DocumentMetadata from ingestion
        auto_forecast: Whether to trigger forecast refresh

    Returns:
        IngestionResult with forecast status
    """
    from raglite.forecasting.auto_update import trigger_forecast_refresh
    from raglite.shared.config import settings
    from raglite.shared.models import IngestionResult

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
