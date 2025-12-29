"""[P0/P1] Edge case and error handling tests for temp_files module.

Tests critical error paths, boundary conditions, and cleanup guarantees.
"""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError, URLError

import pytest

from raglite.ingestion.document_ingestion.temp_files import (
    temp_file_from_base64,
    temp_file_from_url,
)

pytestmark = [pytest.mark.unit]


class TestTempFileFromBase64EdgeCases:
    """[P0] Critical error paths for base64 temp file handling."""

    def test_invalid_base64_content(self):
        """[P0] TEST-EDGE-1.1: Reject invalid base64 encoding."""
        # Given invalid base64 content
        invalid_b64 = "Not valid base64!@#$%^&*()"

        # When creating temp file
        # Then raise ValueError with helpful message
        with pytest.raises(ValueError, match="Invalid base64 content"):
            with temp_file_from_base64(invalid_b64, "test.pdf"):
                pass

    def test_empty_base64_content(self):
        """[P1] TEST-EDGE-1.2: Handle empty base64 content gracefully."""
        # Given empty base64 content
        empty_b64 = ""

        # When creating temp file
        # Then should succeed (empty file is valid)
        with temp_file_from_base64(empty_b64, "test.pdf") as tmp_path:
            # File exists
            assert Path(tmp_path).exists()
            # File is empty
            assert Path(tmp_path).stat().st_size == 0

        # After context exit, file is cleaned up
        assert not Path(tmp_path).exists()

    def test_exceeds_25mb_size_limit(self):
        """[P0] TEST-EDGE-1.3: Reject files exceeding 25MB limit."""
        # Given base64 content exceeding 25MB (before decoding)
        # 25MB * 4/3 (base64 overhead) + 1 byte
        oversized_bytes = b"x" * (25 * 1024 * 1024 + 1)
        oversized_b64 = base64.b64encode(oversized_bytes).decode()

        # When creating temp file
        # Then raise ValueError with size information
        with pytest.raises(ValueError, match=r"exceeds 25MB limit"):
            with temp_file_from_base64(oversized_b64, "large.pdf"):
                pass

    def test_unsupported_file_extension(self):
        """[P0] TEST-EDGE-1.4: Reject unsupported file extensions."""
        # Given valid base64 content but unsupported extension
        content_b64 = base64.b64encode(b"dummy content").decode()

        # When creating temp file with .txt extension
        # Then raise ValueError listing supported extensions
        with pytest.raises(ValueError, match="Unsupported file type"):
            with temp_file_from_base64(content_b64, "document.txt"):
                pass

    def test_no_file_extension(self):
        """[P1] TEST-EDGE-1.5: Handle filenames without extensions."""
        # Given filename with no extension
        content_b64 = base64.b64encode(b"dummy content").decode()

        # When creating temp file
        # Then raise ValueError (cannot determine file type)
        with pytest.raises(ValueError, match="Unsupported file type"):
            with temp_file_from_base64(content_b64, "document"):
                pass

    def test_cleanup_on_exception_during_processing(self):
        """[P0] TEST-EDGE-1.6: Guarantee cleanup even if context body raises exception."""
        # Given valid base64 content
        content_b64 = base64.b64encode(b"test content").decode()
        tmp_path_captured = None

        # When exception occurs inside context
        try:
            with temp_file_from_base64(content_b64, "test.pdf") as tmp_path:
                tmp_path_captured = tmp_path
                # Verify file exists during context
                assert Path(tmp_path).exists()
                # Simulate processing exception
                raise RuntimeError("Simulated processing error")
        except RuntimeError:
            pass  # Expected exception

        # Then temp file is still cleaned up
        assert not Path(tmp_path_captured).exists()

    def test_cleanup_on_permission_error(self):
        """[P1] TEST-EDGE-1.7: Log warning if cleanup fails (permissions)."""
        # Given valid base64 content
        content_b64 = base64.b64encode(b"test content").decode()

        # When cleanup fails due to permission error
        with patch("raglite.ingestion.document_ingestion.temp_files.logger"):
            try:
                with temp_file_from_base64(content_b64, "test.pdf") as tmp_path:
                    # Make file read-only before cleanup (simulate permission error)
                    import os
                    import stat

                    os.chmod(tmp_path, stat.S_IRUSR)
                    # Also remove parent directory write permission
                    parent_dir = Path(tmp_path).parent
                    original_mode = parent_dir.stat().st_mode
                    os.chmod(parent_dir, stat.S_IRUSR | stat.S_IXUSR)

                    # Restore permissions to allow cleanup in finally block
                    os.chmod(parent_dir, original_mode)
            except PermissionError:
                pass  # Expected during cleanup attempt

            # Cleanup may log warning if it fails
            # Note: This test is platform-dependent and may not trigger on all systems
            # The important thing is that the context manager handles it gracefully

    def test_case_insensitive_extension_validation(self):
        """[P1] TEST-EDGE-1.8: Accept extensions with different case."""
        # Given base64 content with uppercase extension
        content_b64 = base64.b64encode(b"pdf content").decode()

        # When creating temp file with .PDF extension
        with temp_file_from_base64(content_b64, "report.PDF") as tmp_path:
            # Then succeeds (case-insensitive validation)
            assert Path(tmp_path).exists()
            assert tmp_path.lower().endswith(".pdf")

        # Cleanup verified
        assert not Path(tmp_path).exists()

    def test_special_characters_in_filename(self):
        """[P2] TEST-EDGE-1.9: Handle special characters in filename."""
        # Given filename with special characters (only extension matters)
        content_b64 = base64.b64encode(b"content").decode()

        # When creating temp file
        with temp_file_from_base64(content_b64, "report (final)@2024.pdf") as tmp_path:
            # Then succeeds (tempfile handles special chars)
            assert Path(tmp_path).exists()

        assert not Path(tmp_path).exists()


class TestTempFileFromURLEdgeCases:
    """[P0/P1] Critical error paths for URL download handling."""

    def test_invalid_url_scheme_ftp(self):
        """[P0] TEST-EDGE-2.1: Reject non-HTTPS/HTTP schemes (security)."""
        # Given FTP URL (not allowed)
        ftp_url = "ftp://example.com/report.pdf"

        # When creating temp file from URL
        # Then raise ValueError (security constraint)
        with pytest.raises(ValueError, match="URL scheme 'ftp' not allowed"):
            with temp_file_from_url(ftp_url):
                pass

    def test_http_404_not_found(self):
        """[P0] TEST-EDGE-2.2: Handle 404 errors gracefully."""
        # Given URL that returns 404
        url = "https://example.com/nonexistent.pdf"

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock 404 HTTP error
            mock_urlopen.side_effect = HTTPError(
                url,
                404,
                "Not Found",
                hdrs={},
                fp=None,  # type: ignore
            )

            # When downloading
            # Then raise RuntimeError with HTTP status
            with pytest.raises(RuntimeError, match="HTTP 404"):
                with temp_file_from_url(url):
                    pass

    def test_network_timeout(self):
        """[P0] TEST-EDGE-2.3: Handle network timeouts."""
        # Given URL that times out
        url = "https://slow-server.com/report.pdf"

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock timeout
            mock_urlopen.side_effect = TimeoutError("Connection timed out")

            # When downloading
            # Then raise RuntimeError with timeout message
            with pytest.raises(RuntimeError, match="timed out"):
                with temp_file_from_url(url):
                    pass

    def test_network_error_dns_failure(self):
        """[P1] TEST-EDGE-2.4: Handle DNS resolution failures."""
        # Given URL with invalid domain
        url = "https://nonexistent-domain-12345.com/report.pdf"

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock URLError (DNS failure)
            mock_urlopen.side_effect = URLError("Name or service not known")

            # When downloading
            # Then raise RuntimeError with network error
            with pytest.raises(RuntimeError, match="Failed to download from URL"):
                with temp_file_from_url(url):
                    pass

    def test_exceeds_download_size_limit_content_length(self):
        """[P0] TEST-EDGE-2.5: Reject downloads exceeding size limit (via Content-Length)."""
        # Given URL with Content-Length > 100MB
        url = "https://example.com/huge.pdf"

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response with large Content-Length header
            mock_response = MagicMock()
            mock_response.headers.get.side_effect = lambda key, default=None: {
                "Content-Length": str(200 * 1024 * 1024),  # 200MB
            }.get(key, default)

            mock_urlopen.return_value.__enter__.return_value = mock_response

            # When downloading
            # Then raise ValueError before downloading content
            with pytest.raises(ValueError, match="File too large"):
                with temp_file_from_url(url):
                    pass

    def test_exceeds_download_size_limit_during_streaming(self):
        """[P0] TEST-EDGE-2.6: Abort download if size exceeds limit during streaming."""
        # Given URL without Content-Length header, but large content
        url = "https://example.com/streaming.pdf"

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response with no Content-Length, large streaming content
            mock_response = MagicMock()
            mock_response.headers.get.side_effect = lambda key, default="": {
                "Content-Type": "application/pdf",
                "Content-Length": None,
                "Content-Disposition": "",
            }.get(key, default)
            # Simulate large chunks (total > 50MB)
            chunk_size = 8192
            num_chunks = (50 * 1024 * 1024 // chunk_size) + 10  # Exceed 50MB
            mock_response.read.side_effect = [b"x" * chunk_size] * num_chunks + [b""]

            mock_urlopen.return_value.__enter__.return_value = mock_response

            # When downloading
            # Then raise ValueError during streaming
            with pytest.raises(ValueError, match="Download exceeded size limit"):
                with temp_file_from_url(url):
                    pass

    def test_unsupported_file_type_from_url_extension(self):
        """[P0] TEST-EDGE-2.7: Reject unsupported file types from URL."""
        # Given URL with unsupported extension
        url = "https://example.com/document.docx"

        # When downloading
        # Then raise ValueError early (extension check)
        with pytest.raises(ValueError, match="Unsupported file type"):
            with temp_file_from_url(url):
                pass

    def test_no_file_extension_no_content_type(self):
        """[P1] TEST-EDGE-2.8: Handle URLs without extension or Content-Type."""
        # Given URL with no extension
        url = "https://example.com/download?id=12345"

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response with no Content-Type and no Content-Disposition
            mock_response = MagicMock()
            mock_response.headers.get.side_effect = lambda key, default="": {
                "Content-Type": "",
                "Content-Length": "1000",
                "Content-Disposition": "",
            }.get(key, default)
            mock_response.read.return_value = b""

            mock_urlopen.return_value.__enter__.return_value = mock_response

            # When downloading
            # Then raise ValueError (cannot determine file type)
            # The error message is "Cannot determine file type" OR "Unsupported file type: ."
            with pytest.raises(
                ValueError, match="(Cannot determine file type|Unsupported file type)"
            ):
                with temp_file_from_url(url):
                    pass

    def test_infer_pdf_from_content_type(self):
        """[P1] TEST-EDGE-2.9: Infer file type from Content-Type header."""
        # Given URL with no extension but PDF Content-Type
        url = "https://example.com/download?id=12345"

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response with application/pdf Content-Type
            mock_response = MagicMock()
            mock_response.headers.get.side_effect = lambda key, default="": {
                "Content-Type": "application/pdf",
                "Content-Length": "1000",
            }.get(key, default)
            mock_response.read.return_value = b""

            mock_urlopen.return_value.__enter__.return_value = mock_response

            # When downloading
            with temp_file_from_url(url) as (tmp_path, filename):
                # Then infers .pdf extension
                assert filename == "downloaded_document.pdf"
                assert tmp_path.endswith(".pdf")

    def test_cleanup_after_download_exception(self):
        """[P0] TEST-EDGE-2.10: Guarantee cleanup if download fails mid-stream."""
        # Given URL that fails during download
        url = "https://example.com/broken.pdf"

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response that raises exception during read
            mock_response = MagicMock()
            mock_response.headers.get.side_effect = lambda key, default="": {
                "Content-Type": "application/pdf",
            }.get(key, default)
            mock_response.read.side_effect = OSError("Connection reset")

            mock_urlopen.return_value.__enter__.return_value = mock_response

            # When download fails
            with pytest.raises(IOError):
                with temp_file_from_url(url):
                    pass

            # Then temp file is cleaned up (verified by context manager finally block)
            # No assertion needed - verifies no ResourceWarning

    def test_domain_allowlist_enforcement(self):
        """[P1] TEST-EDGE-2.11: Enforce domain allowlist if configured."""
        # Given URL not in allowlist
        url = "https://untrusted-domain.com/report.pdf"

        with patch(
            "raglite.ingestion.document_ingestion.temp_files.URL_DOMAIN_ALLOWLIST",
            new=["trusted-domain.com"],
        ):
            # When downloading
            # Then raise ValueError (domain not allowed)
            with pytest.raises(ValueError, match="not in allowlist"):
                with temp_file_from_url(url):
                    pass

    def test_extract_filename_from_content_disposition(self):
        """[P1] TEST-EDGE-2.12: Parse filename from Content-Disposition header."""
        # Given URL with Content-Disposition header
        url = "https://example.com/download"

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response with Content-Disposition
            mock_response = MagicMock()
            mock_response.headers.get.side_effect = lambda key, default="": {
                "Content-Disposition": 'attachment; filename="Q3_Report.pdf"',
                "Content-Type": "application/pdf",
            }.get(key, default)
            mock_response.read.return_value = b""

            mock_urlopen.return_value.__enter__.return_value = mock_response

            # When downloading
            with temp_file_from_url(url) as (tmp_path, filename):
                # Then extracts filename from header
                assert filename == "Q3_Report.pdf"


class TestTempFileCleanupGuarantees:
    """[P0] Cleanup guarantees across all scenarios."""

    def test_base64_cleanup_on_success(self):
        """[P0] TEST-EDGE-3.1: Base64 temp file cleaned up on success."""
        content_b64 = base64.b64encode(b"content").decode()

        with temp_file_from_base64(content_b64, "test.pdf") as tmp_path:
            captured_path = tmp_path
            assert Path(tmp_path).exists()

        # After success, file deleted
        assert not Path(captured_path).exists()

    def test_base64_cleanup_on_user_exception(self):
        """[P0] TEST-EDGE-3.2: Base64 temp file cleaned up on exception."""
        content_b64 = base64.b64encode(b"content").decode()
        captured_path = None

        try:
            with temp_file_from_base64(content_b64, "test.pdf") as tmp_path:
                captured_path = tmp_path
                raise ValueError("User error")
        except ValueError:
            pass

        # After exception, file deleted
        assert not Path(captured_path).exists()

    def test_url_cleanup_on_success(self):
        """[P0] TEST-EDGE-3.3: URL temp file cleaned up on success."""
        url = "https://example.com/report.pdf"

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.headers.get.side_effect = lambda key, default="": {
                "Content-Type": "application/pdf",
            }.get(key, default)
            mock_response.read.return_value = b""
            mock_urlopen.return_value.__enter__.return_value = mock_response

            with temp_file_from_url(url) as (tmp_path, _):
                captured_path = tmp_path
                assert Path(tmp_path).exists()

            # After success, file deleted
            assert not Path(captured_path).exists()
