"""Unit tests for PDF ingestion pipeline (Story 1.3).

Tests the ingest_pdf function with mocked dependencies.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np
import pytest

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.models import DocumentMetadata


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

        # Mock Docling converter and result
        mock_element1 = Mock()
        mock_element1.text = "Financial Report Q4 2024"
        mock_prov1 = Mock()
        mock_prov1.page_no = 1
        mock_element1.prov = [mock_prov1]

        mock_element2 = Mock()
        mock_element2.text = "Revenue Summary"
        mock_prov2 = Mock()
        mock_prov2.page_no = 2
        mock_element2.prov = [mock_prov2]

        mock_document = Mock()
        mock_document.num_pages.return_value = 2
        mock_document.iterate_items.return_value = [
            (mock_element1, 1),
            (mock_element2, 1),
        ]
        mock_document.export_to_markdown.return_value = "Financial Report Q4 2024\nRevenue Summary"

        mock_result = Mock()
        mock_result.document = mock_document

        # Mock Qdrant client to prevent real database calls in unit tests
        mock_qdrant_client = Mock()
        mock_qdrant_client.delete_collection = Mock()
        mock_qdrant_client.create_collection = Mock()
        mock_qdrant_client.upsert = Mock()
        # Mock get_collections() for create_collection() idempotency check
        mock_collections_response = Mock()
        mock_collections_response.collections = []
        mock_qdrant_client.get_collections = Mock(return_value=mock_collections_response)
        # Mock get_collection() for points_count validation after upsert
        mock_collection_info = Mock()
        mock_collection_info.points_count = 2  # Match number of mock chunks
        mock_qdrant_client.get_collection = Mock(return_value=mock_collection_info)

        # Patch Docling at the source for lazy imports inside ingest_pdf()
        # Critical: patch both DocumentConverter and the required imports
        with (
            patch("docling.document_converter.DocumentConverter") as MockConverter,
            patch("docling.datamodel.pipeline_options.PdfPipelineOptions"),
            patch("docling.datamodel.accelerator_options.AcceleratorOptions"),
            patch("docling.datamodel.base_models.InputFormat"),
            patch("docling.document_converter.PdfFormatOption"),
            patch("docling.backend.pypdfium2_backend.PyPdfiumDocumentBackend"),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch(
                "raglite.shared.clients.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch("raglite.ingestion.embedding_generation.get_embedding_model") as MockEmbedding,
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
        ):
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.return_value = mock_result

            # Mock embedding model
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.encode.return_value = np.array([[0.1] * 1024, [0.2] * 1024])

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
        with (
            patch("docling.document_converter.DocumentConverter") as MockConverter,
            patch("docling.datamodel.pipeline_options.PdfPipelineOptions"),
            patch("docling.datamodel.accelerator_options.AcceleratorOptions"),
            patch("docling.datamodel.base_models.InputFormat"),
            patch("docling.document_converter.PdfFormatOption"),
            patch("docling.backend.pypdfium2_backend.PyPdfiumDocumentBackend"),
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
        mock_elements = []
        for page_num in [1, 2, 3, 2, 3]:  # Includes duplicates
            element = Mock()
            element.text = f"Content from page {page_num}"
            prov = Mock()
            prov.page_no = page_num
            element.prov = [prov]
            mock_elements.append(element)

        mock_document = Mock()
        mock_document.num_pages.return_value = 3  # Unique pages
        mock_document.iterate_items.return_value = [(elem, 1) for elem in mock_elements]
        mock_document.export_to_markdown.return_value = (
            "Content from page 1\nContent from page 2\nContent from page 3"
        )

        mock_result = Mock()
        mock_result.document = mock_document

        # Mock Qdrant client
        mock_qdrant_client = Mock()
        mock_collections_response = Mock()
        mock_collections_response.collections = []
        mock_qdrant_client.get_collections = Mock(return_value=mock_collections_response)
        mock_collection_info = Mock()
        mock_collection_info.points_count = 5  # 5 mock elements
        mock_qdrant_client.get_collection = Mock(return_value=mock_collection_info)

        # Patch Docling at the source for lazy imports inside ingest_pdf()
        with (
            patch("docling.document_converter.DocumentConverter") as MockConverter,
            patch("docling.datamodel.pipeline_options.PdfPipelineOptions"),
            patch("docling.datamodel.accelerator_options.AcceleratorOptions"),
            patch("docling.datamodel.base_models.InputFormat"),
            patch("docling.document_converter.PdfFormatOption"),
            patch("docling.backend.pypdfium2_backend.PyPdfiumDocumentBackend"),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch(
                "raglite.shared.clients.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch("raglite.ingestion.embedding_generation.get_embedding_model") as MockEmbedding,
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
        ):
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.return_value = mock_result

            # Mock embedding model
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.encode.return_value = np.array([[0.1] * 1024] * 5)

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
        mock_qdrant_client = Mock()
        mock_collections_response = Mock()
        mock_collections_response.collections = []
        mock_qdrant_client.get_collections = Mock(return_value=mock_collections_response)
        mock_collection_info = Mock()
        mock_collection_info.points_count = 1
        mock_qdrant_client.get_collection = Mock(return_value=mock_collection_info)

        # Patch Docling at the source for lazy imports inside ingest_pdf()
        with (
            patch("docling.document_converter.DocumentConverter") as MockConverter,
            patch("docling.datamodel.pipeline_options.PdfPipelineOptions"),
            patch("docling.datamodel.accelerator_options.AcceleratorOptions"),
            patch("docling.datamodel.base_models.InputFormat"),
            patch("docling.document_converter.PdfFormatOption"),
            patch("docling.backend.pypdfium2_backend.PyPdfiumDocumentBackend"),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch(
                "raglite.shared.clients.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch("raglite.ingestion.embedding_generation.get_embedding_model") as MockEmbedding,
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
        ):
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.return_value = mock_result

            # Mock embedding model
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.encode.return_value = np.array([[0.1] * 1024])

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
        mock_element = Mock()
        mock_element.text = "Test PDF content"  # Story 1.13: chunk_by_docling_items needs item.text
        mock_prov = Mock()
        mock_prov.page_no = 1
        mock_element.prov = [mock_prov]

        mock_document = Mock()
        mock_document.num_pages.return_value = 1
        mock_document.iterate_items.return_value = [(mock_element, 1)]
        mock_document.export_to_markdown.return_value = "Test PDF content"

        mock_result = Mock()
        mock_result.document = mock_document

        # Mock Qdrant client
        mock_qdrant_client = Mock()
        mock_collections_response = Mock()
        mock_collections_response.collections = []
        mock_qdrant_client.get_collections = Mock(return_value=mock_collections_response)
        mock_collection_info = Mock()
        mock_collection_info.points_count = 1
        mock_qdrant_client.get_collection = Mock(return_value=mock_collection_info)

        # Patch Docling at the source for lazy imports inside ingest_pdf()
        # Story 3.0.1: Patch new module locations after refactoring
        with (
            patch("docling.document_converter.DocumentConverter") as MockConverter,
            patch("docling.datamodel.pipeline_options.PdfPipelineOptions"),
            patch("docling.datamodel.accelerator_options.AcceleratorOptions"),
            patch("docling.datamodel.base_models.InputFormat"),
            patch("docling.document_converter.PdfFormatOption"),
            patch("docling.backend.pypdfium2_backend.PyPdfiumDocumentBackend"),
            patch(
                "raglite.ingestion.document_ingestion.pdf_processing.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch(
                "raglite.shared.clients.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch("raglite.ingestion.embedding_generation.get_embedding_model") as MockEmbedding,
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
        ):
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.return_value = mock_result

            # Mock embedding model
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.encode.return_value = np.array([[0.1] * 1024])

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
