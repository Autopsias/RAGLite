"""Constants for document ingestion.

Story 8.3: Extracted from document_ingestion.py for better modularity.
"""

from __future__ import annotations

# Story 4.0.7: Maximum base64 content size (25MB encoded ≈ 18MB decoded)
MAX_BASE64_CONTENT_SIZE_BYTES = 25 * 1024 * 1024  # 25MB

# Story 4.0.8: Maximum URL download size (50MB - larger than base64 since no encoding overhead)
MAX_URL_DOWNLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

# Story 4.0.8: URL download timeout (30 seconds for connection, 300 seconds total for large files)
URL_DOWNLOAD_TIMEOUT_CONNECT = 30
URL_DOWNLOAD_TIMEOUT_TOTAL = 300

# Story 4.0.7: Supported file extensions for base64 ingestion
SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".xls"}

# Story 4.0.8: Allowed URL schemes for security
ALLOWED_URL_SCHEMES = {"http", "https"}

# Story 4.0.8: Domain allowlist for URL downloads (empty = all domains allowed)
# Can be configured via environment variable URL_DOMAIN_ALLOWLIST (comma-separated)
URL_DOMAIN_ALLOWLIST: set[str] = (
    set()
)  # e.g., {"drive.google.com", "dropbox.com", "s3.amazonaws.com"}


__all__ = [
    "MAX_BASE64_CONTENT_SIZE_BYTES",
    "MAX_URL_DOWNLOAD_SIZE_BYTES",
    "URL_DOWNLOAD_TIMEOUT_CONNECT",
    "URL_DOWNLOAD_TIMEOUT_TOTAL",
    "SUPPORTED_EXTENSIONS",
    "ALLOWED_URL_SCHEMES",
    "URL_DOMAIN_ALLOWLIST",
]
