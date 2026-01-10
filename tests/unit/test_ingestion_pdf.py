"""Unit tests for PDF ingestion pipeline (Story 1.3).

Tests the ingest_pdf function with mocked dependencies.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.models import DocumentMetadata
from tests.unit.pdf_ingestion_helpers import (
    create_mock_chunk,
    create_mock_element,
    create_mock_qdrant_client,
    create_standard_docling_patches,
)

# Group PDF ingestion tests that share mocked Docling/Qdrant state to run on same worker
pytestmark = pytest.mark.xdist_group(name="pdf_ingestion")


class TestIngestPDF:
    """Test suite for PDF ingestion pipeline."""

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_ingest_pdf_success(self, tmp_path):
        """Test successful PDF ingestion with valid file.

        Verifies that ingest_pdf returns correct DocumentMetadata
        when Docling successfully parses a PDF.
        """
        # Create a temporary PDF file
        pdf_file = tmp_path / "test_report.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake pdf content")

        # Mock Docling elements and document
        mock_element1 = create_mock_element("Financial Report Q4 2024", 1)
        mock_element2 = create_mock_element("Revenue Summary", 2)

        mock_document = Mock()
        mock_document.num_pages.return_value = 2
        mock_document.iterate_items.return_value = [
            (mock_element1, 1),
            (mock_element2, 1),
        ]
        mock_document.export_to_markdown.return_value = "Financial Report Q4 2024\nRevenue Summary"

        mock_result = Mock()
        mock_result.document = mock_document

        # Mock Qdrant client
        mock_qdrant_client = create_mock_qdrant_client(points_count=2)

        # Mock chunks
        mock_chunks = [
            create_mock_chunk(
                chunk_id="chunk1",
                content="Financial Report Q4 2024",
                filename="test_report.pdf",
                page_number=1,
                chunk_index=0,
                page_count=2,
                word_count=4,
            ),
            create_mock_chunk(
                chunk_id="chunk2",
                content="Revenue Summary",
                filename="test_report.pdf",
                page_number=2,
                chunk_index=1,
                page_count=2,
                word_count=2,
            ),
        ]

        # Patch Docling at the source for lazy imports inside ingest_pdf()
        docling_patches = create_standard_docling_patches()
        with (
            patch(docling_patches[0]) as MockConverter,
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.store_metadata_in_postgresql",
                return_value=(1, 0),
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.store_vectors_in_qdrant",
                return_value=None,
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.generate_embeddings",
                return_value=mock_chunks,
            ),
        ):
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.return_value = mock_result

            # Execute ingestion
            result = await ingest_pdf(str(pdf_file))

            # Assertions
            assert isinstance(result, DocumentMetadata)
            assert result.filename == "test_report.pdf"
            assert result.doc_type == "PDF"
            assert result.page_count == 2  # Two unique pages
            assert result.source_path == str(pdf_file)
            assert result.ingestion_timestamp  # Should have timestamp

            # Verify ISO8601 timestamp format
            datetime.fromisoformat(result.ingestion_timestamp)

    @pytest.mark.priority("P3")
    @pytest.mark.asyncio
    async def test_ingest_pdf_file_not_found(self):
        """Test that FileNotFoundError is raised for nonexistent file.

        Verifies error handling for missing PDF files.
        """
        nonexistent_path = "/tmp/does_not_exist_12345.pdf"

        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            await ingest_pdf(nonexistent_path)

    @pytest.mark.priority("P3")
    @pytest.mark.asyncio
    async def test_ingest_pdf_corrupted(self, tmp_path):
        """Test error handling for corrupted PDF that Docling can't parse.

        Verifies RuntimeError is raised with clear message.
        """
        # Create a corrupted PDF file (invalid content)
        corrupt_pdf = tmp_path / "corrupted.pdf"
        corrupt_pdf.write_bytes(b"not a real pdf")

        # Patch Docling at the source for lazy imports inside ingest_pdf()
        docling_patches = create_standard_docling_patches()
        with (
            patch(docling_patches[0]) as MockConverter,
        ):
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.side_effect = Exception("PDF parsing error")

            with pytest.raises(RuntimeError, match="Docling parsing failed"):
                await ingest_pdf(str(corrupt_pdf))

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_ingest_pdf_page_numbers_extracted(self, tmp_path):
        """CRITICAL: Verify page numbers are extracted and NOT None.

        This test addresses the Week 0 blocker (AC 10).
        Ensures page numbers are correctly extracted from Docling provenance.
        """
        pdf_file = tmp_path / "multipage.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 multipage content")

        # Mock elements with page numbers 1, 2, 3
        mock_elements = [
            create_mock_element(f"Content from page {page_num}", page_num)
            for page_num in [1, 2, 3, 2, 3]  # Includes duplicates
        ]

        mock_document = Mock()
        mock_document.num_pages.return_value = 3  # Unique pages
        mock_document.iterate_items.return_value = [(elem, 1) for elem in mock_elements]
        mock_document.export_to_markdown.return_value = (
            "Content from page 1\nContent from page 2\nContent from page 3"
        )

        mock_result = Mock()
        mock_result.document = mock_document

        # Mock Qdrant client
        mock_qdrant_client = create_mock_qdrant_client(points_count=5)

        # Mock chunks
        mock_chunks = [
            create_mock_chunk(
                chunk_id=f"chunk{i}",
                content=f"Content from page {i % 3 + 1}",
                filename="multipage.pdf",
                page_number=i % 3 + 1,
                chunk_index=i,
                page_count=3,
                word_count=5,
            )
            for i in range(5)
        ]

        # Patch Docling at the source for lazy imports inside ingest_pdf()
        docling_patches = create_standard_docling_patches()
        with (
            patch(docling_patches[0]) as MockConverter,
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.store_metadata_in_postgresql",
                return_value=(5, 0),
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.store_tables_in_postgresql",
                return_value=(0, 0),
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.store_vectors_in_qdrant",
                return_value=None,
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.generate_embeddings",
                return_value=mock_chunks,
            ),
        ):
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.return_value = mock_result

            result = await ingest_pdf(str(pdf_file))

            # Critical assertion: page numbers must be extracted
            assert result.page_count == 3  # Unique pages: 1, 2, 3
            assert result.page_count > 0, "Page numbers must NOT be None or zero"

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_ingest_pdf_no_page_metadata(self, tmp_path, caplog):
        """Test handling of PDFs where Docling extracts no page metadata.

        Should log warning but not crash.
        """
        pdf_file = tmp_path / "no_pages.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        # Mock elements WITHOUT page provenance
        mock_element = Mock()
        mock_element.text = "Content without page info"
        mock_element.prov = []  # No provenance

        mock_document = Mock()
        mock_document.num_pages.return_value = 0  # No pages found
        mock_document.iterate_items.return_value = [(mock_element, 1)]
        mock_document.export_to_markdown.return_value = "Content without page info"

        mock_result = Mock()
        mock_result.document = mock_document

        # Mock Qdrant client
        mock_qdrant_client = create_mock_qdrant_client(points_count=1)

        # Mock chunks
        mock_chunks = [
            create_mock_chunk(
                chunk_id="chunk1",
                content="Content without page info",
                filename="no_pages.pdf",
                page_number=0,
                chunk_index=0,
                page_count=0,
                word_count=4,
            ),
        ]

        # Patch Docling at the source for lazy imports inside ingest_pdf()
        docling_patches = create_standard_docling_patches()
        with (
            patch(docling_patches[0]) as MockConverter,
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.store_metadata_in_postgresql",
                return_value=(1, 0),
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.store_tables_in_postgresql",
                return_value=(0, 0),
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.store_vectors_in_qdrant",
                return_value=None,
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.generate_embeddings",
                return_value=mock_chunks,
            ),
        ):
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.return_value = mock_result

            result = await ingest_pdf(str(pdf_file))

            # Should return metadata but with page_count=0
            assert result.page_count == 0

            # Should log warning
            assert "No page numbers extracted" in caplog.text

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_ingest_pdf_docling_init_failure(self, tmp_path):
        """Test error handling when Docling converter initialization fails."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        # Patch Docling at the source for lazy imports inside ingest_pdf()
        with (
            patch("docling.document_converter.DocumentConverter") as MockConverter,
            patch("docling.datamodel.pipeline_options.PdfPipelineOptions"),
            patch("docling.datamodel.accelerator_options.AcceleratorOptions"),
            patch("docling.datamodel.base_models.InputFormat"),
            patch("docling.document_converter.PdfFormatOption"),
            patch("docling.backend.pypdfium2_backend.PyPdfiumDocumentBackend"),
        ):
            MockConverter.side_effect = Exception("Docling initialization failed")

            with pytest.raises(RuntimeError, match="Failed to initialize Docling converter"):
                await ingest_pdf(str(pdf_file))

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_ingest_pdf_logging(self, tmp_path, caplog):
        """Test that structured logging includes correct context.

        Verifies logging with extra={} fields.
        """
        import logging

        caplog.set_level(logging.INFO)

        pdf_file = tmp_path / "logging_test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        # Mock minimal Docling response
        mock_element = create_mock_element("Test PDF content", 1)

        mock_document = Mock()
        mock_document.num_pages.return_value = 1
        mock_document.iterate_items.return_value = [(mock_element, 1)]
        mock_document.export_to_markdown.return_value = "Test PDF content"

        mock_result = Mock()
        mock_result.document = mock_document

        # Mock Qdrant client
        mock_qdrant_client = create_mock_qdrant_client(points_count=1)

        # Mock chunks
        mock_chunks = [
            create_mock_chunk(
                chunk_id="chunk1",
                content="Test PDF content",
                filename="logging_test.pdf",
                page_number=1,
                chunk_index=0,
                page_count=1,
                word_count=3,
            ),
        ]

        # Patch Docling at the source for lazy imports inside ingest_pdf()
        # Story 3.0.1: Patch new module locations after refactoring
        docling_patches = create_standard_docling_patches()
        with (
            patch(docling_patches[0]) as MockConverter,
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.store_metadata_in_postgresql",
                return_value=(1, 0),
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.store_tables_in_postgresql",
                return_value=(0, 0),
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.store_vectors_in_qdrant",
                return_value=None,
            ),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.generate_embeddings",
                return_value=mock_chunks,
            ),
        ):
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.return_value = mock_result

            await ingest_pdf(str(pdf_file))

            # Verify log messages
            assert "Starting PDF ingestion" in caplog.text
            assert "PDF ingested successfully" in caplog.text

            # Verify structured logging context (check log records for extra fields)
            # Story 8.3: Logs now come from pdf_processing module after refactoring
            log_records = [
                r
                for r in caplog.records
                if r.name == "raglite.ingestion.document_ingestion.pdf_processing"
            ]
            assert len(log_records) >= 2  # Should have at least 2 log entries

            # Check first log record has doc_filename in extra
            start_log = next((r for r in log_records if "Starting" in r.message), None)
            assert start_log is not None
            assert hasattr(start_log, "doc_filename")
            assert start_log.doc_filename == "logging_test.pdf"
