"""Unit tests for Story 4.0.7: MCP Base64 File Content Ingestion.

Tests cover:
- AC1: New parameters accepted by ingestion tools
- AC2: Mutual exclusivity validation (doc_path vs file_content)
- AC3: Base64 decoding and temp file creation
- AC4: Temp file cleanup on success and failure
- AC5: Size limit enforcement (25MB)
- AC6: Unsupported extension rejection
- AC7: Backward compatibility with doc_path
- AC8: Async tool has same parameters as sync
"""

import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.ingestion.document_ingestion import (
    MAX_BASE64_CONTENT_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    temp_file_from_base64,
)
from raglite.main import (
    DocumentProcessingError,
    ingest_financial_document,
    ingest_financial_document_async,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def valid_pdf_content() -> str:
    """Generate valid base64-encoded minimal PDF content."""
    # Minimal valid PDF (enough for extension detection, not for actual parsing)
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    return base64.b64encode(pdf_bytes).decode("utf-8")


@pytest.fixture
def valid_excel_content() -> str:
    """Generate valid base64-encoded minimal Excel content (XLSX is a ZIP file)."""
    # Minimal ZIP header (XLSX files are ZIP archives)
    # This is enough to pass extension validation but not actual parsing
    xlsx_bytes = b"PK\x03\x04" + b"\x00" * 100
    return base64.b64encode(xlsx_bytes).decode("utf-8")


@pytest.fixture
def invalid_base64() -> str:
    """Return invalid base64 string."""
    return "not-valid-base64!!!"


@pytest.fixture
def oversized_content() -> str:
    """Generate base64 content exceeding 25MB limit."""
    # Create content just over 25MB
    size = MAX_BASE64_CONTENT_SIZE_BYTES + 1024
    return base64.b64encode(b"x" * size).decode("utf-8")


# =============================================================================
# Tests for temp_file_from_base64 helper (AC3, AC4, AC5, AC6)
# =============================================================================


class TestTempFileFromBase64:
    """Tests for the temp_file_from_base64 context manager."""

    def test_creates_temp_file_with_correct_extension_pdf(self, valid_pdf_content: str) -> None:
        """AC3: Verify temp file is created with correct .pdf extension."""
        with temp_file_from_base64(valid_pdf_content, "report.pdf") as tmp_path:
            assert Path(tmp_path).exists()
            assert Path(tmp_path).suffix == ".pdf"

    def test_creates_temp_file_with_correct_extension_xlsx(self, valid_excel_content: str) -> None:
        """AC3: Verify temp file is created with correct .xlsx extension."""
        with temp_file_from_base64(valid_excel_content, "data.xlsx") as tmp_path:
            assert Path(tmp_path).exists()
            assert Path(tmp_path).suffix == ".xlsx"

    def test_creates_temp_file_with_correct_extension_xls(self, valid_excel_content: str) -> None:
        """AC3: Verify temp file is created with correct .xls extension."""
        with temp_file_from_base64(valid_excel_content, "data.xls") as tmp_path:
            assert Path(tmp_path).exists()
            assert Path(tmp_path).suffix == ".xls"

    def test_temp_file_contains_decoded_content(self, valid_pdf_content: str) -> None:
        """AC3: Verify temp file contains correctly decoded base64 content."""
        expected_bytes = base64.b64decode(valid_pdf_content)

        with temp_file_from_base64(valid_pdf_content, "report.pdf") as tmp_path:
            actual_bytes = Path(tmp_path).read_bytes()
            assert actual_bytes == expected_bytes

    def test_temp_file_cleanup_on_success(self, valid_pdf_content: str) -> None:
        """AC4: Verify temp file is deleted after context exits successfully."""
        tmp_path = None
        with temp_file_from_base64(valid_pdf_content, "report.pdf") as path:
            tmp_path = path
            assert Path(tmp_path).exists()

        # After context exits, file should be deleted
        assert not Path(tmp_path).exists()

    def test_temp_file_cleanup_on_exception(self, valid_pdf_content: str) -> None:
        """AC4: Verify temp file is deleted even when exception occurs in context."""
        tmp_path = None

        with pytest.raises(RuntimeError):
            with temp_file_from_base64(valid_pdf_content, "report.pdf") as path:
                tmp_path = path
                assert Path(tmp_path).exists()
                raise RuntimeError("Simulated processing error")

        # After exception, file should still be cleaned up
        assert not Path(tmp_path).exists()

    def test_size_limit_25mb_rejected(self, oversized_content: str) -> None:
        """AC5: Verify content exceeding 25MB raises ValueError."""
        with pytest.raises(ValueError, match="exceeds 25MB limit"):
            with temp_file_from_base64(oversized_content, "large.pdf"):
                pass  # Should not reach here

    def test_invalid_base64_raises_valueerror(self, invalid_base64: str) -> None:
        """AC3: Verify invalid base64 content raises ValueError."""
        with pytest.raises(ValueError, match="Invalid base64"):
            with temp_file_from_base64(invalid_base64, "report.pdf"):
                pass

    def test_unsupported_extension_docx_rejected(self, valid_pdf_content: str) -> None:
        """AC6: Verify .docx extension is rejected."""
        with pytest.raises(ValueError, match="Unsupported file type: .docx"):
            with temp_file_from_base64(valid_pdf_content, "document.docx"):
                pass

    def test_unsupported_extension_txt_rejected(self, valid_pdf_content: str) -> None:
        """AC6: Verify .txt extension is rejected."""
        with pytest.raises(ValueError, match="Unsupported file type: .txt"):
            with temp_file_from_base64(valid_pdf_content, "notes.txt"):
                pass

    def test_unsupported_extension_csv_rejected(self, valid_pdf_content: str) -> None:
        """AC6: Verify .csv extension is rejected."""
        with pytest.raises(ValueError, match="Unsupported file type: .csv"):
            with temp_file_from_base64(valid_pdf_content, "data.csv"):
                pass

    def test_supported_extensions_constant(self) -> None:
        """Verify supported extensions are correctly defined."""
        assert SUPPORTED_EXTENSIONS == {".pdf", ".xlsx", ".xls"}

    def test_max_content_size_constant(self) -> None:
        """Verify max content size is correctly defined as 25MB."""
        assert MAX_BASE64_CONTENT_SIZE_BYTES == 25 * 1024 * 1024


# =============================================================================
# Tests for ingest_financial_document sync tool (AC1, AC2, AC7)
# =============================================================================


class TestIngestFinancialDocumentSync:
    """Tests for sync ingestion tool with base64 support."""

    @pytest.mark.asyncio
    async def test_accepts_file_content_and_filename_params(self, valid_pdf_content: str) -> None:
        """AC1: Verify tool accepts file_content and filename parameters."""
        from raglite.shared.models import DocumentMetadata

        # Mock ingest_document to avoid actual processing - use real Pydantic model
        mock_metadata = DocumentMetadata(
            filename="report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2024-01-01T00:00:00Z",
            page_count=5,
            source_path="/tmp/test.pdf",
            chunk_count=10,
        )

        with patch(
            "raglite.mcp.tools.ingestion.ingest_document",
            new_callable=AsyncMock,
            return_value=mock_metadata,
        ):
            # Use .fn to access the underlying async function (FastMCP wraps it)
            result = await ingest_financial_document.fn(
                file_content=valid_pdf_content, filename="report.pdf"
            )
            assert result.filename == "report.pdf"

    @pytest.mark.asyncio
    async def test_mutual_exclusivity_both_inputs_raises_error(
        self, valid_pdf_content: str
    ) -> None:
        """AC2: Verify error when both doc_path and file_content provided."""
        with pytest.raises(DocumentProcessingError, match="Only one input mode allowed"):
            await ingest_financial_document.fn(
                doc_path="/some/path.pdf",
                file_content=valid_pdf_content,
                filename="report.pdf",
            )

    @pytest.mark.asyncio
    async def test_no_input_raises_error(self) -> None:
        """AC2: Verify error when neither doc_path nor file_content provided."""
        with pytest.raises(DocumentProcessingError, match="Must provide one of"):
            await ingest_financial_document.fn()

    @pytest.mark.asyncio
    async def test_file_content_without_filename_raises_error(self, valid_pdf_content: str) -> None:
        """AC2: Verify error when file_content provided without filename."""
        with pytest.raises(DocumentProcessingError, match="filename is required"):
            await ingest_financial_document.fn(file_content=valid_pdf_content)

    @pytest.mark.asyncio
    async def test_doc_path_backward_compatible(self, tmp_path: Path) -> None:
        """AC7: Verify existing doc_path usage remains backward compatible."""
        from raglite.shared.models import DocumentMetadata

        # Create a test file
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4\n")

        mock_metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2024-01-01T00:00:00Z",
            page_count=1,
            source_path=str(test_file),
            chunk_count=5,
        )

        with patch(
            "raglite.mcp.tools.ingestion.ingest_document",
            new_callable=AsyncMock,
            return_value=mock_metadata,
        ):
            result = await ingest_financial_document.fn(doc_path=str(test_file))
            assert result.filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_base64_size_limit_enforced(self, oversized_content: str) -> None:
        """AC5: Verify size limit is enforced for base64 content."""
        with pytest.raises(DocumentProcessingError, match="exceeds 25MB limit"):
            await ingest_financial_document.fn(file_content=oversized_content, filename="large.pdf")

    @pytest.mark.asyncio
    async def test_base64_unsupported_extension_rejected(self, valid_pdf_content: str) -> None:
        """AC6: Verify unsupported extensions rejected for base64 content."""
        with pytest.raises(DocumentProcessingError, match="Unsupported file type"):
            await ingest_financial_document.fn(
                file_content=valid_pdf_content, filename="document.docx"
            )

    @pytest.mark.asyncio
    async def test_base64_invalid_content_rejected(self, invalid_base64: str) -> None:
        """AC3: Verify invalid base64 content is rejected."""
        with pytest.raises(DocumentProcessingError, match="Invalid base64"):
            await ingest_financial_document.fn(file_content=invalid_base64, filename="report.pdf")

    @pytest.mark.asyncio
    async def test_metadata_filename_uses_original_name(self, valid_pdf_content: str) -> None:
        """AC1: Verify metadata.filename shows original name, not temp path."""
        from raglite.shared.models import DocumentMetadata

        # Mock returns temp filename, but result should have original name
        mock_metadata = DocumentMetadata(
            filename="tmp_12345.pdf",  # Simulated temp filename
            doc_type="PDF",
            ingestion_timestamp="2024-01-01T00:00:00Z",
            page_count=5,
            source_path="/tmp/tmp_12345.pdf",
            chunk_count=10,
        )

        with patch(
            "raglite.mcp.tools.ingestion.ingest_document",
            new_callable=AsyncMock,
            return_value=mock_metadata,
        ):
            result = await ingest_financial_document.fn(
                file_content=valid_pdf_content, filename="Q3_Report.pdf"
            )
            # Should override with original filename
            assert result.filename == "Q3_Report.pdf"


# =============================================================================
# Tests for ingest_financial_document_async tool (AC8)
# =============================================================================


class TestIngestFinancialDocumentAsync:
    """Tests for async ingestion tool with base64 support (AC8)."""

    @pytest.mark.asyncio
    async def test_async_accepts_same_parameters_as_sync(self, valid_pdf_content: str) -> None:
        """AC8: Verify async tool accepts file_content and filename parameters."""
        with patch("raglite.mcp.tools.ingestion.create_job", return_value="test-job-123"):
            with patch("raglite.mcp.tools.ingestion.start_background_job"):
                # Use .fn to access the underlying async function
                result = await ingest_financial_document_async.fn(
                    file_content=valid_pdf_content, filename="report.pdf"
                )
                assert result.job_id == "test-job-123"
                assert result.status == "started"
                assert "report.pdf" in result.message

    @pytest.mark.asyncio
    async def test_async_mutual_exclusivity_both_inputs_raises_error(
        self, valid_pdf_content: str
    ) -> None:
        """AC8/AC2: Verify async tool validates mutual exclusivity."""
        with pytest.raises(DocumentProcessingError, match="Only one input mode allowed"):
            await ingest_financial_document_async.fn(
                doc_path="/some/path.pdf",
                file_content=valid_pdf_content,
                filename="report.pdf",
            )

    @pytest.mark.asyncio
    async def test_async_no_input_raises_error(self) -> None:
        """AC8/AC2: Verify async tool requires input."""
        with pytest.raises(DocumentProcessingError, match="Must provide one of"):
            await ingest_financial_document_async.fn()

    @pytest.mark.asyncio
    async def test_async_file_content_without_filename_raises_error(
        self, valid_pdf_content: str
    ) -> None:
        """AC8/AC2: Verify async tool requires filename with file_content."""
        with pytest.raises(DocumentProcessingError, match="filename is required"):
            await ingest_financial_document_async.fn(file_content=valid_pdf_content)

    @pytest.mark.asyncio
    async def test_async_doc_path_backward_compatible(self, tmp_path: Path) -> None:
        """AC8/AC7: Verify async tool backward compatibility with doc_path."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4\n")

        with patch("raglite.mcp.tools.ingestion.create_job", return_value="test-job-456"):
            with patch("raglite.mcp.tools.ingestion.start_background_job"):
                result = await ingest_financial_document_async.fn(doc_path=str(test_file))
                assert result.job_id == "test-job-456"
                assert "test.pdf" in result.message

    @pytest.mark.asyncio
    async def test_async_base64_size_limit_enforced(self, oversized_content: str) -> None:
        """AC8/AC5: Verify async tool enforces size limit."""
        with pytest.raises(DocumentProcessingError, match="exceeds 25MB limit"):
            await ingest_financial_document_async.fn(
                file_content=oversized_content, filename="large.pdf"
            )

    @pytest.mark.asyncio
    async def test_async_base64_unsupported_extension_rejected(
        self, valid_pdf_content: str
    ) -> None:
        """AC8/AC6: Verify async tool rejects unsupported extensions."""
        with pytest.raises(DocumentProcessingError, match="Unsupported file type"):
            await ingest_financial_document_async.fn(
                file_content=valid_pdf_content, filename="document.txt"
            )

    @pytest.mark.asyncio
    async def test_async_base64_invalid_content_rejected(self, invalid_base64: str) -> None:
        """AC8/AC3: Verify async tool rejects invalid base64."""
        with pytest.raises(DocumentProcessingError, match="Invalid base64"):
            await ingest_financial_document_async.fn(
                file_content=invalid_base64, filename="report.pdf"
            )

    @pytest.mark.asyncio
    async def test_async_passes_temp_path_and_filename_to_background_job(
        self, valid_pdf_content: str
    ) -> None:
        """AC8/AC4: Verify async tool passes cleanup info to background job."""
        captured_args: dict = {}

        def capture_start_job(job_id, path, temp_path_to_cleanup=None, original_filename=None):
            captured_args["temp_path_to_cleanup"] = temp_path_to_cleanup
            captured_args["original_filename"] = original_filename

        with patch("raglite.mcp.tools.ingestion.create_job", return_value="test-job-789"):
            with patch("raglite.mcp.tools.ingestion.start_background_job", side_effect=capture_start_job):
                await ingest_financial_document_async.fn(
                    file_content=valid_pdf_content, filename="quarterly_report.pdf"
                )

                # Verify temp path is passed for cleanup
                assert captured_args["temp_path_to_cleanup"] is not None
                assert captured_args["temp_path_to_cleanup"].endswith(".pdf")
                assert captured_args["original_filename"] == "quarterly_report.pdf"


# =============================================================================
# Tests for job_tracker temp file cleanup (AC4 for async)
# =============================================================================


class TestJobTrackerTempFileCleanup:
    """Tests for job_tracker temp file cleanup after async ingestion."""

    @pytest.mark.asyncio
    async def test_run_async_ingestion_cleans_up_temp_file_on_success(
        self, tmp_path: Path, valid_pdf_content: str
    ) -> None:
        """AC4: Verify temp file is cleaned up after successful async ingestion."""
        from raglite.ingestion.job_tracker import run_async_ingestion

        # Create actual temp file
        temp_file = tmp_path / "temp_test.pdf"
        temp_file.write_bytes(base64.b64decode(valid_pdf_content))
        assert temp_file.exists()

        mock_metadata = MagicMock()
        mock_metadata.filename = "temp_test.pdf"
        mock_metadata.doc_type = "PDF"
        mock_metadata.chunk_count = 5
        mock_metadata.page_count = 1

        # Mock at source module since job_tracker imports from pipeline
        with patch(
            "raglite.ingestion.pipeline.ingest_document",
            new_callable=AsyncMock,
            return_value=mock_metadata,
        ):
            with patch("raglite.ingestion.job_tracker.update_job_status"):
                await run_async_ingestion(
                    job_id="test-job",
                    doc_path=str(temp_file),
                    temp_path_to_cleanup=str(temp_file),
                    original_filename="report.pdf",
                )

        # Verify temp file was cleaned up
        assert not temp_file.exists()

    @pytest.mark.asyncio
    async def test_run_async_ingestion_cleans_up_temp_file_on_failure(
        self, tmp_path: Path, valid_pdf_content: str
    ) -> None:
        """AC4: Verify temp file is cleaned up even when ingestion fails."""
        from raglite.ingestion.job_tracker import run_async_ingestion

        # Create actual temp file
        temp_file = tmp_path / "temp_fail.pdf"
        temp_file.write_bytes(base64.b64decode(valid_pdf_content))
        assert temp_file.exists()

        # Mock at source module since job_tracker imports from pipeline
        with patch(
            "raglite.ingestion.pipeline.ingest_document",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Simulated ingestion failure"),
        ):
            with patch("raglite.ingestion.job_tracker.update_job_status"):
                await run_async_ingestion(
                    job_id="test-job",
                    doc_path=str(temp_file),
                    temp_path_to_cleanup=str(temp_file),
                    original_filename="report.pdf",
                )

        # Verify temp file was cleaned up despite failure
        assert not temp_file.exists()

    @pytest.mark.asyncio
    async def test_run_async_ingestion_overrides_filename_in_metadata(
        self, tmp_path: Path, valid_pdf_content: str
    ) -> None:
        """AC8: Verify original filename is used in result metadata."""
        from raglite.ingestion.job_tracker import create_job, get_job_status, run_async_ingestion

        temp_file = tmp_path / "temp_abc123.pdf"
        temp_file.write_bytes(base64.b64decode(valid_pdf_content))

        mock_metadata = MagicMock()
        mock_metadata.filename = "temp_abc123.pdf"  # Temp filename
        mock_metadata.doc_type = "PDF"
        mock_metadata.chunk_count = 10
        mock_metadata.page_count = 2

        # Create the job first (required for run_async_ingestion to work)
        job_id = create_job(str(temp_file))

        # Mock at source module since job_tracker imports from pipeline
        with patch(
            "raglite.ingestion.pipeline.ingest_document",
            new_callable=AsyncMock,
            return_value=mock_metadata,
        ):
            await run_async_ingestion(
                job_id=job_id,
                doc_path=str(temp_file),
                temp_path_to_cleanup=str(temp_file),
                original_filename="Annual_Report_2024.pdf",
            )

        # Verify filename was overridden
        job_status = get_job_status(job_id)
        assert job_status is not None
        assert job_status.result is not None
        assert job_status.result.filename == "Annual_Report_2024.pdf"
