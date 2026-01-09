"""URL-based file download with streaming and validation."""

from __future__ import annotations

import http.client
import tempfile
import urllib.parse
import urllib.request
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError, URLError

from raglite.shared.logging import get_logger

from ..constants import MAX_URL_DOWNLOAD_SIZE_BYTES, URL_DOWNLOAD_TIMEOUT_TOTAL
from .url_validation import determine_filename_and_extension, validate_url

logger = get_logger(__name__)


def create_download_request(url: str) -> urllib.request.Request:
    """Create HTTP request with appropriate headers.

    Args:
        url: URL to download from

    Returns:
        urllib.request.Request: Configured request object
    """
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": "RAGLite/1.0 (Financial Document Ingestion)",
            "Accept": "application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel, */*",
        },
    )


def download_file_streaming(
    response: http.client.HTTPResponse, tmp_path: str, parsed: urllib.parse.ParseResult
) -> int:
    """Download file content with streaming and size validation.

    Args:
        response: HTTP response object
        tmp_path: Temporary file path to write to
        parsed: Parsed URL for logging

    Returns:
        int: Total downloaded size in bytes

    Raises:
        ValueError: If download exceeds size limit
    """
    downloaded_size = 0
    chunk_size = 8192  # 8KB chunks

    with open(tmp_path, "wb") as tmp:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            downloaded_size += len(chunk)

            # Check size limit during download
            if downloaded_size > MAX_URL_DOWNLOAD_SIZE_BYTES:
                raise ValueError(
                    f"Download exceeded size limit during transfer. "
                    f"Maximum: {MAX_URL_DOWNLOAD_SIZE_BYTES / (1024 * 1024):.0f}MB"
                )

            tmp.write(chunk)

    return downloaded_size


def handle_download_error(e: Exception, parsed: urllib.parse.ParseResult) -> None:
    """Handle and log download errors with appropriate error messages.

    Args:
        e: The exception that occurred
        parsed: Parsed URL for logging

    Raises:
        RuntimeError: Always raises with appropriate error message
    """
    if isinstance(e, HTTPError):
        logger.error(
            "HTTP error during URL download",
            extra={
                "url_domain": parsed.netloc,
                "status_code": e.code,
                "reason": e.reason,
            },
        )
        raise RuntimeError(f"Failed to download from URL: HTTP {e.code} {e.reason}") from e

    elif isinstance(e, URLError):
        logger.error(
            "Network error during URL download",
            extra={"url_domain": parsed.netloc, "error": str(e.reason)},
        )
        raise RuntimeError(f"Failed to download from URL: {e.reason}") from e

    elif isinstance(e, TimeoutError):
        logger.error(
            "Timeout during URL download",
            extra={
                "url_domain": parsed.netloc,
                "timeout_seconds": URL_DOWNLOAD_TIMEOUT_TOTAL,
            },
        )
        raise RuntimeError(
            f"Download timed out after {URL_DOWNLOAD_TIMEOUT_TOTAL} seconds. "
            "Try a faster connection or smaller file."
        ) from None

    else:
        # Re-raise unexpected errors
        raise


def execute_download(
    url: str, parsed: urllib.parse.ParseResult, filename_from_url: str
) -> tuple[str, str, int]:
    """Execute the actual file download from URL.

    Args:
        url: URL to download from
        parsed: Parsed URL object for logging
        filename_from_url: Initial filename from URL path

    Returns:
        tuple[str, str, int]: (temp_file_path, final_filename, downloaded_size)

    Raises:
        ValueError: If file too large or extension not supported
        RuntimeError: If download fails
    """
    # Create request with timeout and headers
    request = create_download_request(url)

    # Download with streaming to handle large files
    with urllib.request.urlopen(request, timeout=URL_DOWNLOAD_TIMEOUT_TOTAL) as response:  # nosec B310 - URL scheme validated above
        # Check Content-Length if available
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_URL_DOWNLOAD_SIZE_BYTES:
            size_mb = int(content_length) / (1024 * 1024)
            raise ValueError(
                f"File too large ({size_mb:.1f}MB). Maximum allowed: "
                f"{MAX_URL_DOWNLOAD_SIZE_BYTES / (1024 * 1024):.0f}MB"
            )

        # Determine filename and extension from headers
        final_filename, suffix = determine_filename_and_extension(response, filename_from_url)

        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name

        # Download file content with streaming
        downloaded_size = download_file_streaming(response, tmp_path, parsed)

        logger.info(
            "URL download complete",
            extra={
                "url_domain": parsed.netloc,
                "doc_filename": final_filename,
                "size_bytes": downloaded_size,
                "temp_path": tmp_path,
            },
        )

        return tmp_path, final_filename, downloaded_size


@contextmanager
def temp_file_from_url(url: str) -> Generator[tuple[str, str], None, None]:
    """Download file from URL to temporary file with automatic cleanup.

    Story 4.0.8: URL-based ingestion for Claude.ai and Claude Desktop compatibility.
    Downloads file from HTTP/HTTPS URL, validates, and provides temp file path.

    This solves the MCP file transfer limitation where:
    - Claude.ai cannot access uploaded files (sandboxed at /mnt/user-data/uploads/)
    - Claude Desktop uploads are also sandboxed, not accessible to MCP servers
    - URL-based ingestion works universally across all Claude clients

    Args:
        url: HTTP or HTTPS URL to download file from.
             Supports direct download links from:
             - Google Drive (use export links)
             - Dropbox (use dl=1 parameter)
             - S3 presigned URLs
             - Any direct file URL

    Yields:
        tuple[str, str]: (temp_file_path, detected_filename)

    Raises:
        ValueError: If URL scheme is not allowed, domain not in allowlist,
                    file too large, or extension not supported.
        RuntimeError: If download fails (network error, 404, etc.)

    Example:
        >>> with temp_file_from_url("https://example.com/report.pdf") as (path, name):
        ...     metadata = await ingest_document(path)
        >>> # temp file automatically cleaned up
    """
    # Parse and validate URL
    parsed = urllib.parse.urlparse(url)
    url_path, filename_from_url = validate_url(url, parsed)

    logger.info(
        "Starting URL download",
        extra={
            "url_domain": parsed.netloc,
            "url_path": url_path[:100],  # Truncate for logging
            "detected_filename": filename_from_url,
        },
    )

    tmp_path = None
    try:
        tmp_path, filename_from_url, downloaded_size = execute_download(
            url, parsed, filename_from_url
        )
        yield tmp_path, filename_from_url

    except Exception as e:
        handle_download_error(e, parsed)

    finally:
        # Cleanup temp file
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
                logger.debug(
                    "Cleaned up temp file from URL download",
                    extra={"temp_path": tmp_path},
                )
            except Exception as e:
                logger.warning(
                    "Failed to clean up temp file from URL download",
                    extra={"temp_path": tmp_path, "error": str(e)},
                )


__all__ = [
    "temp_file_from_url",
    "create_download_request",
    "download_file_streaming",
    "handle_download_error",
]
