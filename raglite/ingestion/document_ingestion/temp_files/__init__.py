"""Temporary file handling for document ingestion.

Story 8.3: Extracted from document_ingestion.py for better modularity.
Handles base64 and URL-based temporary file creation with automatic cleanup.
"""

from __future__ import annotations

# Re-export constants for test compatibility (from parent module)
from ..constants import (
    ALLOWED_URL_SCHEMES,
    MAX_BASE64_CONTENT_SIZE_BYTES,
    MAX_URL_DOWNLOAD_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    URL_DOMAIN_ALLOWLIST,
    URL_DOWNLOAD_TIMEOUT_TOTAL,
)

# Re-export public API from submodules
from .base64_handler import temp_file_from_base64
from .url_download import temp_file_from_url

# Note: logger is no longer exposed at package level
# Tests should use raglite.shared.logging.get_logger(__name__) if needed

__all__ = [
    "temp_file_from_base64",
    "temp_file_from_url",
    "ALLOWED_URL_SCHEMES",
    "MAX_BASE64_CONTENT_SIZE_BYTES",
    "MAX_URL_DOWNLOAD_SIZE_BYTES",
    "SUPPORTED_EXTENSIONS",
    "URL_DOMAIN_ALLOWLIST",
    "URL_DOWNLOAD_TIMEOUT_TOTAL",
]
