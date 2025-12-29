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
)
from raglite.main import (
    DocumentProcessingError,
    ingest_financial_document_async,
)
from raglite.mcp.tools import ingestion as ingestion_module

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


class TestIngestFinancialDocumentAsync:
    """Tests for async ingestion tool with base64 support (AC8)."""

    @pytest.mark.asyncio
    async def test_async_accepts_same_parameters_as_sync(self, valid_pdf_content: str) -> None:
        """AC8: Verify async tool accepts file_content and filename parameters."""
        with patch.object(ingestion_module, "create_job", return_value="test-job-123"):
            with patch.object(ingestion_module, "start_background_job"):
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

        with patch.object(ingestion_module, "create_job", return_value="test-job-456"):
            with patch.object(ingestion_module, "start_background_job"):
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

        with patch.object(ingestion_module, "create_job", return_value="test-job-789"):
            with patch.object(
                ingestion_module, "start_background_job", side_effect=capture_start_job
            ):
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
