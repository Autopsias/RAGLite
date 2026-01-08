"""URL validation and filename extraction helpers."""

from __future__ import annotations

import http.client
import re
import urllib.parse
from pathlib import Path

from ..constants import ALLOWED_URL_SCHEMES, SUPPORTED_EXTENSIONS, URL_DOMAIN_ALLOWLIST


def validate_url(url: str, parsed: urllib.parse.ParseResult) -> tuple[str, str]:
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


def determine_filename_and_extension(
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


__all__ = ["validate_url", "determine_filename_and_extension"]
