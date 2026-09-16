"""Unit tests for URL-based document ingestion (Story 4.0.8).

Tests the temp_file_from_url utility and URL validation logic.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from raglite.ingestion.document_ingestion import (
    ALLOWED_URL_SCHEMES,
    MAX_URL_DOWNLOAD_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    temp_file_from_url,
)


class TestURLValidation:
    """Test URL validation logic."""

    def test_allowed_schemes(self):
        """AC1: Only http and https schemes are allowed."""
        assert "http" in ALLOWED_URL_SCHEMES
        assert "https" in ALLOWED_URL_SCHEMES
        assert "ftp" not in ALLOWED_URL_SCHEMES
        assert "file" not in ALLOWED_URL_SCHEMES

    def test_supported_extensions(self):
        """Verify supported file extensions."""
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".xlsx" in SUPPORTED_EXTENSIONS
        assert ".xls" in SUPPORTED_EXTENSIONS
        assert ".doc" not in SUPPORTED_EXTENSIONS

    def test_max_download_size(self):
        """Verify download size limit is 50MB."""
        assert MAX_URL_DOWNLOAD_SIZE_BYTES == 50 * 1024 * 1024


class TestTempFileFromURL:
    """Test temp_file_from_url context manager."""

    def test_invalid_scheme_raises_error(self):
        """AC1: Invalid URL schemes should raise ValueError."""
        with pytest.raises(ValueError, match="scheme.*not allowed"):
            with temp_file_from_url("ftp://example.com/report.pdf"):
                pass

    def test_file_scheme_raises_error(self):
        """Security: file:// scheme should be rejected."""
        with pytest.raises(ValueError, match="scheme.*not allowed"):
            with temp_file_from_url("file:///etc/passwd"):
                pass

    def test_unsupported_extension_raises_error(self):
        """AC6: Unsupported file extensions should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            with temp_file_from_url("https://example.com/document.doc"):
                pass

    @patch("urllib.request.urlopen")
    def test_successful_pdf_download(self, mock_urlopen):
        """Test successful PDF download creates temp file."""
        # Mock response
        mock_response = MagicMock()
        mock_response.headers = {
            "Content-Length": "1000",
            "Content-Type": "application/pdf",
        }
        mock_response.read.side_effect = [b"%PDF-1.4 test content", b""]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with temp_file_from_url("https://example.com/report.pdf") as (
            tmp_path,
            filename,
        ):
            assert tmp_path is not None
            assert tmp_path.endswith(".pdf")
            assert filename == "report.pdf"
            # File should exist during context
            assert Path(tmp_path).exists()

        # File should be cleaned up after context
        # Note: cleanup happens in finally block

    @patch("urllib.request.urlopen")
    def test_filename_from_content_disposition(self, mock_urlopen):
        """Test filename extraction from Content-Disposition header."""
        mock_response = MagicMock()
        mock_response.headers = {
            "Content-Length": "1000",
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="Q3_Report_2024.pdf"',
        }
        mock_response.read.side_effect = [b"%PDF-1.4 test", b""]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with temp_file_from_url("https://example.com/download?id=123") as (
            tmp_path,
            filename,
        ):
            assert filename == "Q3_Report_2024.pdf"

    @patch("urllib.request.urlopen")
    def test_content_type_fallback_for_pdf(self, mock_urlopen):
        """Test Content-Type based extension detection when URL has no extension."""
        mock_response = MagicMock()
        mock_response.headers = {
            "Content-Length": "1000",
            "Content-Type": "application/pdf",
        }
        mock_response.read.side_effect = [b"%PDF-1.4 test", b""]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with temp_file_from_url("https://example.com/download") as (tmp_path, filename):
            assert tmp_path.endswith(".pdf")
            assert filename == "downloaded_document.pdf"

    @patch("urllib.request.urlopen")
    def test_content_type_fallback_for_excel(self, mock_urlopen):
        """Test Content-Type based extension detection for Excel files."""
        mock_response = MagicMock()
        mock_response.headers = {
            "Content-Length": "1000",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        mock_response.read.side_effect = [b"PK\x03\x04 excel content", b""]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with temp_file_from_url("https://example.com/download") as (tmp_path, filename):
            assert tmp_path.endswith(".xlsx")
            assert filename == "downloaded_document.xlsx"

    @patch("urllib.request.urlopen")
    def test_size_limit_from_content_length(self, mock_urlopen):
        """Test that files exceeding size limit are rejected via Content-Length."""
        mock_response = MagicMock()
        mock_response.headers = {
            "Content-Length": str(MAX_URL_DOWNLOAD_SIZE_BYTES + 1),
            "Content-Type": "application/pdf",
        }
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with pytest.raises(ValueError, match="File too large"):
            with temp_file_from_url("https://example.com/huge.pdf"):
                pass

    @patch("urllib.request.urlopen")
    def test_size_limit_during_download(self, mock_urlopen):
        """Test that size limit is enforced during streaming download."""
        mock_response = MagicMock()
        mock_response.headers = {
            "Content-Type": "application/pdf",
        }
        # Return chunks that exceed limit
        large_chunk = b"x" * (MAX_URL_DOWNLOAD_SIZE_BYTES + 1000)
        mock_response.read.side_effect = [large_chunk]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with pytest.raises(ValueError, match="exceeded size limit"):
            with temp_file_from_url("https://example.com/report.pdf"):
                pass

    @patch("urllib.request.urlopen")
    def test_http_error_raises_runtime_error(self, mock_urlopen):
        """Test HTTP errors are converted to RuntimeError."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            url="https://example.com/report.pdf",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )

        with pytest.raises(RuntimeError, match="HTTP 404"):
            with temp_file_from_url("https://example.com/report.pdf"):
                pass

    @patch("urllib.request.urlopen")
    def test_network_error_raises_runtime_error(self, mock_urlopen):
        """Test network errors are converted to RuntimeError."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        with pytest.raises(RuntimeError, match="Connection refused"):
            with temp_file_from_url("https://example.com/report.pdf"):
                pass


class TestMCPToolValidation:
    """Test MCP tool input validation for URL mode."""

    @pytest.mark.asyncio
    async def test_no_input_raises_error(self):
        """Test that providing no input raises descriptive error."""
        from raglite.main import DocumentProcessingError, ingest_financial_document

        with pytest.raises(DocumentProcessingError, match="Must provide one of"):
            await ingest_financial_document.fn()

    @pytest.mark.asyncio
    async def test_multiple_inputs_raises_error(self):
        """Test that providing multiple input modes raises error."""
        from raglite.main import DocumentProcessingError, ingest_financial_document

        with pytest.raises(DocumentProcessingError, match="Only one input mode"):
            await ingest_financial_document.fn(
                doc_path="/some/path.pdf",
                doc_url="https://example.com/report.pdf",
            )

    @pytest.mark.asyncio
    async def test_url_and_base64_raises_error(self):
        """Test that providing both URL and base64 raises error."""
        from raglite.main import DocumentProcessingError, ingest_financial_document

        with pytest.raises(DocumentProcessingError, match="Only one input mode"):
            await ingest_financial_document.fn(
                file_content="base64content",
                filename="report.pdf",
                doc_url="https://example.com/report.pdf",
            )
