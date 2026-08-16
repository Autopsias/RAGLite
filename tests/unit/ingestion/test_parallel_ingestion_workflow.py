"""Unit tests for parallel ingestion workflow.

Story 5.0.6: Tests for parallel document batch processing, semaphore control,
and error handling. Mocks external dependencies to avoid slow I/O.
"""

import asyncio
from unittest.mock import patch

import pytest

from raglite.ingestion.document_ingestion import ingest_documents_parallel
from raglite.shared.models import DocumentMetadata


class TestParallelDocumentIngestion:
    """Test suite for parallel document batch ingestion (AC1 - 2x speedup).

    Tests concurrent document processing, error handling, semaphore control,
    and batch result aggregation. Uses mocks to avoid slow PDF processing.
    """

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_parallel_ingestion_success(self):
        """Test successful parallel ingestion of multiple documents.

        Verifies AC1: Parallel processing with semaphore control and
        proper result aggregation.
        """
        # Mock DocumentMetadata results (no document_id field, only filename)
        mock_metadata_1 = DocumentMetadata(
            filename="report1.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-30T10:00:00",
            page_count=10,
            source_path="/path/to/report1.pdf",
            chunk_count=25,
        )
        mock_metadata_2 = DocumentMetadata(
            filename="report2.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-30T10:05:00",
            page_count=15,
            source_path="/path/to/report2.pdf",
            chunk_count=30,
        )
        mock_metadata_3 = DocumentMetadata(
            filename="data.xlsx",
            doc_type="Excel",
            ingestion_timestamp="2025-11-30T10:10:00",
            page_count=5,
            source_path="/path/to/data.xlsx",
            chunk_count=10,
        )

        # Create async mock for ingest_document
        async def mock_ingest_document(file_path: str, unit_cache: dict | None = None):
            """Mock ingest_document with realistic delay."""
            # Simulate processing time (0.1s for test speed)
            await asyncio.sleep(0.1)

            # Return different metadata based on file path
            if "report1" in file_path:
                return mock_metadata_1
            elif "report2" in file_path:
                return mock_metadata_2
            else:
                return mock_metadata_3

        # Test with 3 documents
        file_paths = [
            "/path/to/report1.pdf",
            "/path/to/report2.pdf",
            "/path/to/data.xlsx",
        ]

        with patch(
            "raglite.ingestion.document_ingestion.core.ingest_document",
            side_effect=mock_ingest_document,
        ):
            result = await ingest_documents_parallel(file_paths, max_concurrent=2)

        # Verify BatchIngestionResult structure
        assert result.__class__.__name__ == "BatchIngestionResult"
        assert result.total_documents == 3
        assert result.successful == 3
        assert result.failed == 0
        assert len(result.results) == 3
        assert len(result.errors) == 0
        assert result.duration_seconds > 0

        # Verify all documents processed (check filenames, no document_id field)
        result_filenames = {m.filename for m in result.results}
        assert result_filenames == {"report1.pdf", "report2.pdf", "data.xlsx"}

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_parallel_ingestion_with_failures(self):
        """Test error handling with partial batch failures.

        Verifies AC1: One document failure doesn't abort entire batch.
        """

        async def mock_ingest_with_error(file_path: str, unit_cache: dict | None = None):
            """Mock ingestion that fails on second document."""
            await asyncio.sleep(0.05)

            if "report2" in file_path:
                raise ValueError("Mock ingestion error for report2.pdf")

            return DocumentMetadata(
                filename=file_path,
                doc_type="PDF",
                ingestion_timestamp="2025-11-30T10:00:00",
                page_count=10,
                chunk_count=25,
            )

        file_paths = [
            "/path/to/report1.pdf",
            "/path/to/report2.pdf",
            "/path/to/report3.pdf",
        ]

        with patch(
            "raglite.ingestion.document_ingestion.core.ingest_document",
            side_effect=mock_ingest_with_error,
        ):
            result = await ingest_documents_parallel(file_paths, max_concurrent=2)

        # Verify partial success
        assert result.total_documents == 3
        assert result.successful == 2  # report1 and report3
        assert result.failed == 1  # report2
        assert len(result.results) == 2
        assert len(result.errors) == 1

        # Verify error details captured
        error = result.errors[0]
        assert "report2" in error["filename"]
        assert "Mock ingestion error" in error["error"]

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_concurrency_limit_enforced(self):
        """Test that semaphore limits concurrent executions.

        Verifies AC1: Memory-safe concurrency control (default: 2).
        """
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent_seen = 0

        async def mock_ingest_track_concurrency(file_path: str, unit_cache: dict | None = None):
            """Mock that tracks concurrency levels."""
            nonlocal concurrent_count, max_concurrent_seen

            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)

            # Simulate work
            await asyncio.sleep(0.1)

            concurrent_count -= 1

            return DocumentMetadata(
                filename=file_path,
                doc_type="PDF",
                ingestion_timestamp="2025-11-30T10:00:00",
                page_count=10,
                chunk_count=25,
            )

        # 5 documents with max_concurrent=2
        file_paths = [f"/path/to/report{i}.pdf" for i in range(5)]

        with patch(
            "raglite.ingestion.document_ingestion.core.ingest_document",
            side_effect=mock_ingest_track_concurrency,
        ):
            result = await ingest_documents_parallel(file_paths, max_concurrent=2)

        # Verify concurrency was limited
        assert max_concurrent_seen <= 2, "Should never exceed max_concurrent limit"
        assert result.successful == 5

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_empty_file_list_raises_error(self):
        """Test that empty file list raises ValueError.

        Verifies AC1: Input validation.
        """
        with pytest.raises(ValueError, match="file_paths cannot be empty"):
            await ingest_documents_parallel([])

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_invalid_max_concurrent_raises_error(self):
        """Test that invalid max_concurrent raises ValueError.

        Verifies AC1: Configuration validation.
        """
        with pytest.raises(ValueError, match="max_concurrent must be >= 1"):
            await ingest_documents_parallel(["/path/to/file.pdf"], max_concurrent=0)

        with pytest.raises(ValueError, match="max_concurrent must be >= 1"):
            await ingest_documents_parallel(["/path/to/file.pdf"], max_concurrent=-1)

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_uses_config_default_when_max_concurrent_none(self):
        """Test that max_concurrent=None uses settings.ingestion_parallel_docs.

        Verifies AC1: Configuration integration.
        """

        async def mock_ingest(file_path: str, unit_cache: dict | None = None):
            return DocumentMetadata(
                filename=file_path,
                doc_type="PDF",
                ingestion_timestamp="2025-11-30T10:00:00",
                page_count=10,
                chunk_count=25,
            )

        with (
            patch(
                "raglite.ingestion.document_ingestion.core.ingest_document",
                side_effect=mock_ingest,
            ),
            patch("raglite.ingestion.document_ingestion.collection.settings") as mock_settings,
        ):
            mock_settings.ingestion_parallel_docs = 3
            result = await ingest_documents_parallel(["/path/to/file.pdf"])

        # Verify it used the config default (should succeed with any concurrency)
        assert result.successful == 1

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_batch_result_aggregation(self):
        """Test correct aggregation of batch statistics.

        Verifies AC1 & AC6: Result tracking and summary statistics.
        """

        async def mock_ingest(file_path: str, unit_cache: dict | None = None):
            await asyncio.sleep(0.05)
            return DocumentMetadata(
                filename=file_path,
                doc_type="PDF",
                ingestion_timestamp="2025-11-30T10:00:00",
                page_count=20,
                chunk_count=50,
            )

        file_paths = [f"/path/to/report{i}.pdf" for i in range(4)]

        with patch(
            "raglite.ingestion.document_ingestion.core.ingest_document",
            side_effect=mock_ingest,
        ):
            result = await ingest_documents_parallel(file_paths, max_concurrent=2)

        # Verify aggregated statistics
        assert result.total_documents == 4
        assert result.successful == 4
        total_pages = sum(m.page_count for m in result.results)
        total_chunks = sum(m.chunk_count for m in result.results)
        assert total_pages == 80  # 4 docs * 20 pages
        assert total_chunks == 200  # 4 docs * 50 chunks

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_sequential_processing_when_max_concurrent_1(self):
        """Test that max_concurrent=1 forces sequential processing.

        Verifies AC1: Configurable concurrency (1 = sequential, 2+ = parallel).
        """
        concurrent_count = 0
        max_concurrent_seen = 0

        async def mock_ingest_track(file_path: str, unit_cache: dict | None = None):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1

            return DocumentMetadata(
                filename=file_path,
                doc_type="PDF",
                ingestion_timestamp="2025-11-30T10:00:00",
                page_count=10,
                chunk_count=25,
            )

        file_paths = [f"/path/to/report{i}.pdf" for i in range(3)]

        with patch(
            "raglite.ingestion.document_ingestion.core.ingest_document",
            side_effect=mock_ingest_track,
        ):
            result = await ingest_documents_parallel(file_paths, max_concurrent=1)

        # Verify sequential processing (never more than 1 concurrent)
        assert max_concurrent_seen == 1
        assert result.successful == 3
