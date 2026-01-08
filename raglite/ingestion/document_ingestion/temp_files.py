"""Temporary file handling for document ingestion.

Story 8.3: Extracted from document_ingestion.py for better modularity.
Handles base64 and URL-based temporary file creation with automatic cleanup.
"""

from __future__ import annotations

import base64
import http.client
import re
import tempfile
import urllib.parse
import urllib.request
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError, URLError

from raglite.shared.logging import get_logger

from .constants import (
    ALLOWED_URL_SCHEMES,
    MAX_BASE64_CONTENT_SIZE_BYTES,
    MAX_URL_DOWNLOAD_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    URL_DOMAIN_ALLOWLIST,
    URL_DOWNLOAD_TIMEOUT_TOTAL,
)

logger = get_logger(__name__)


@contextmanager
def temp_file_from_base64(content_b64: str, filename: str) -> Generator[str, None, None]:
    """Create temporary file from base64 content with automatic cleanup.

    Story 4.0.7 AC3/AC4: Context manager for safe temporary file handling.
    Decodes base64 content, writes to temp file, and ensures cleanup on exit.

    Args:
        content_b64: Base64-encoded file content (max 25MB encoded).
        filename: Original filename with extension (e.g., "report.pdf").
                  Used for extension detection and validation.

    Yields:
        str: Absolute path to temporary file with correct extension.

    Raises:
        ValueError: If base64 content is invalid, extension unsupported,
                    or size exceeds 25MB limit.

    Example:
        >>> with temp_file_from_base64(pdf_b64, "report.pdf") as tmp_path:
        ...     metadata = await ingest_document(tmp_path)
        >>> # tmp_path is automatically deleted after context exits
    """
    # AC5: Size check (before decoding to fail fast)
    if len(content_b64) > MAX_BASE64_CONTENT_SIZE_BYTES:
        size_mb = len(content_b64) / (1024 * 1024)
        raise ValueError(
            f"File content ({size_mb:.1f}MB encoded) exceeds 25MB limit. "
            "For larger files, save to filesystem and use doc_path parameter."
        )

    # AC3: Decode base64
    try:
        file_bytes = base64.b64decode(content_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64 content: {e}") from e

    # AC6: Extension validation
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type: {suffix}. Supported extensions: {supported}")

    # Create temp file with correct extension (required for format detection)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        logger.info(
            "Created temp file from base64 content",
            extra={
                "original_filename": filename,
                "extension": suffix,
                "size_bytes": len(file_bytes),
                "temp_path": tmp_path,
            },
        )

        yield tmp_path

    finally:
        # AC4: Guaranteed cleanup on success or failure
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
                logger.debug(
                    "Cleaned up temp file",
                    extra={"temp_path": tmp_path},
                )
            except Exception as e:
                logger.warning(
                    "Failed to clean up temp file",
                    extra={"temp_path": tmp_path, "error": str(e)},
                )


def _validate_url(url: str, parsed: urllib.parse.ParseResult) -> tuple[str, str]:
    """Validate URL scheme, domain, and extract filename.

    Args:
        url: Original URL string
        parsed: Parsed URL components

    Returns:
        tuple[str, str]: (url_path, filename_from_url)

    Raises:
        ValueError: If URL scheme not allowed, domain not in allowlist,
                    or extension not supported.
    """
    # AC1: Scheme validation (security)
    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        raise ValueError(
            f"URL scheme '{parsed.scheme}' not allowed. "
            f"Supported schemes: {', '.join(sorted(ALLOWED_URL_SCHEMES))}"
        )

    # AC2: Domain allowlist check (if configured)
    if URL_DOMAIN_ALLOWLIST and parsed.netloc.lower() not in URL_DOMAIN_ALLOWLIST:
        raise ValueError(
            f"Domain '{parsed.netloc}' not in allowlist. "
            "Contact administrator to add trusted domains."
        )

    # Extract filename from URL path
    url_path = urllib.parse.unquote(parsed.path)
    filename_from_url = Path(url_path).name if url_path else ""

    # Validate extension from URL (preliminary check)
    if filename_from_url:
        suffix = Path(filename_from_url).suffix.lower()
        if suffix and suffix not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValueError(
                f"Unsupported file type from URL: {suffix}. Supported extensions: {supported}"
            )

    return url_path, filename_from_url


def _create_download_request(url: str) -> urllib.request.Request:
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


def _determine_filename_and_extension(
    response: http.client.HTTPResponse, filename_from_url: str
) -> tuple[str, str]:
    """Determine filename and file extension from response headers.

    Args:
        response: HTTP response object
        filename_from_url: Filename extracted from URL path

    Returns:
        tuple[str, str]: (filename, suffix)

    Raises:
        ValueError: If file type cannot be determined or extension not supported
    """
    # Try to get filename from Content-Disposition header
    content_disposition = response.headers.get("Content-Disposition", "")
    if "filename=" in content_disposition:
        match = re.search(r'filename[*]?=["\']?([^"\';\n]+)', content_disposition)
        if match:
            filename_from_url = match.group(1).strip()

    # Determine file extension
    suffix = ""
    if filename_from_url:
        suffix = Path(filename_from_url).suffix.lower()

    # If no extension from URL/headers, try Content-Type
    if not suffix:
        content_type = response.headers.get("Content-Type", "")
        if "pdf" in content_type:
            suffix = ".pdf"
            filename_from_url = "downloaded_document.pdf"
        elif "spreadsheet" in content_type or "excel" in content_type:
            suffix = ".xlsx"
            filename_from_url = "downloaded_document.xlsx"
        elif not filename_from_url:
            raise ValueError(
                "Cannot determine file type from URL. "
                "Ensure URL ends with .pdf, .xlsx, or .xls, "
                "or server provides Content-Type header."
            )

    # Final extension validation
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type: {suffix}. Supported: {supported}")

    return filename_from_url, suffix


def _download_file_streaming(
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


def _handle_download_error(e: Exception, parsed: urllib.parse.ParseResult) -> None:
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
    url_path, filename_from_url = _validate_url(url, parsed)

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
        # Create request with timeout and headers
        request = _create_download_request(url)

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
            filename_from_url, suffix = _determine_filename_and_extension(
                response, filename_from_url
            )

            # Create temp file
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp_path = tmp.name

            # Download file content with streaming
            downloaded_size = _download_file_streaming(response, tmp_path, parsed)

            logger.info(
                "URL download complete",
                extra={
                    "url_domain": parsed.netloc,
                    "doc_filename": filename_from_url,
                    "size_bytes": downloaded_size,
                    "temp_path": tmp_path,
                },
            )

            yield tmp_path, filename_from_url

    except Exception as e:
        _handle_download_error(e, parsed)

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
    "temp_file_from_base64",
    "temp_file_from_url",
]
