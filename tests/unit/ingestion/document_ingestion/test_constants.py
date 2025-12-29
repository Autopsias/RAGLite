"""Unit tests for document_ingestion.constants module.

Tests constants and configuration values for document ingestion.
"""

from __future__ import annotations

from raglite.ingestion.document_ingestion.constants import (
    ALLOWED_URL_SCHEMES,
    MAX_BASE64_CONTENT_SIZE_BYTES,
    MAX_URL_DOWNLOAD_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    URL_DOMAIN_ALLOWLIST,
    URL_DOWNLOAD_TIMEOUT_CONNECT,
    URL_DOWNLOAD_TIMEOUT_TOTAL,
)


class TestConstants:
    """Test constants module configuration values."""

    def test_max_base64_size_is_25mb(self):
        """Verify base64 size limit is 25MB."""
        assert MAX_BASE64_CONTENT_SIZE_BYTES == 25 * 1024 * 1024

    def test_max_url_download_size_is_50mb(self):
        """Verify URL download limit is 50MB."""
        assert MAX_URL_DOWNLOAD_SIZE_BYTES == 50 * 1024 * 1024

    def test_supported_extensions_includes_pdf_xlsx_xls(self):
        """Verify all required extensions are supported."""
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".xlsx" in SUPPORTED_EXTENSIONS
        assert ".xls" in SUPPORTED_EXTENSIONS
        assert len(SUPPORTED_EXTENSIONS) == 3

    def test_allowed_url_schemes_includes_http_https(self):
        """Verify HTTP and HTTPS are allowed."""
        assert "http" in ALLOWED_URL_SCHEMES
        assert "https" in ALLOWED_URL_SCHEMES

    def test_url_domain_allowlist_is_set(self):
        """Verify domain allowlist is a set (default empty)."""
        assert isinstance(URL_DOMAIN_ALLOWLIST, set)

    def test_url_timeouts_are_reasonable(self):
        """Verify timeout values are within reasonable ranges."""
        assert URL_DOWNLOAD_TIMEOUT_CONNECT > 0
        assert URL_DOWNLOAD_TIMEOUT_TOTAL > 0
        assert URL_DOWNLOAD_TIMEOUT_TOTAL >= URL_DOWNLOAD_TIMEOUT_CONNECT
