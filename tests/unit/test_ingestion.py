"""Unit tests for PDF ingestion pipeline.

Tests the ingest_pdf function with mocked Docling responses.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.models import DocumentMetadata


class TestIngestPDF:
    """Test suite for PDF ingestion pipeline."""

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
        mock_document.iterate_items.return_value = [(mock_element1, 1), (mock_element2, 1)]

        mock_result = Mock()
        mock_result.document = mock_document

        with patch("raglite.ingestion.pipeline.DocumentConverter") as MockConverter:
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

    @pytest.mark.asyncio
    async def test_ingest_pdf_file_not_found(self):
        """Test that FileNotFoundError is raised for nonexistent file.

        Verifies error handling for missing PDF files.
        """
        nonexistent_path = "/tmp/does_not_exist_12345.pdf"

        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            await ingest_pdf(nonexistent_path)

    @pytest.mark.asyncio
    async def test_ingest_pdf_corrupted(self, tmp_path):
        """Test error handling for corrupted PDF that Docling can't parse.

        Verifies RuntimeError is raised with clear message.
        """
        # Create a corrupted PDF file (invalid content)
        corrupt_pdf = tmp_path / "corrupted.pdf"
        corrupt_pdf.write_bytes(b"not a real pdf")

        with patch("raglite.ingestion.pipeline.DocumentConverter") as MockConverter:
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.side_effect = Exception("PDF parsing error")

            with pytest.raises(RuntimeError, match="Docling parsing failed"):
                await ingest_pdf(str(corrupt_pdf))

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

        mock_result = Mock()
        mock_result.document = mock_document

        with patch("raglite.ingestion.pipeline.DocumentConverter") as MockConverter:
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.return_value = mock_result

            result = await ingest_pdf(str(pdf_file))

            # Critical assertion: page numbers must be extracted
            assert result.page_count == 3  # Unique pages: 1, 2, 3
            assert result.page_count > 0, "Page numbers must NOT be None or zero"

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

        mock_result = Mock()
        mock_result.document = mock_document

        with patch("raglite.ingestion.pipeline.DocumentConverter") as MockConverter:
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.return_value = mock_result

            result = await ingest_pdf(str(pdf_file))

            # Should return metadata but with page_count=0
            assert result.page_count == 0

            # Should log warning
            assert "No page numbers extracted" in caplog.text

    @pytest.mark.asyncio
    async def test_ingest_pdf_docling_init_failure(self, tmp_path):
        """Test error handling when Docling converter initialization fails."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        with patch("raglite.ingestion.pipeline.DocumentConverter") as MockConverter:
            MockConverter.side_effect = Exception("Docling initialization failed")

            with pytest.raises(RuntimeError, match="Failed to initialize Docling converter"):
                await ingest_pdf(str(pdf_file))

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
        mock_prov = Mock()
        mock_prov.page_no = 1
        mock_element.prov = [mock_prov]

        mock_document = Mock()
        mock_document.num_pages.return_value = 1
        mock_document.iterate_items.return_value = [(mock_element, 1)]

        mock_result = Mock()
        mock_result.document = mock_document

        with patch("raglite.ingestion.pipeline.DocumentConverter") as MockConverter:
            mock_converter_instance = MockConverter.return_value
            mock_converter_instance.convert.return_value = mock_result

            await ingest_pdf(str(pdf_file))

            # Verify log messages
            assert "Starting PDF ingestion" in caplog.text
            assert "PDF ingested successfully" in caplog.text

            # Verify structured logging context (check log records for extra fields)
            log_records = [r for r in caplog.records if r.name == "raglite.ingestion.pipeline"]
            assert len(log_records) >= 2  # Should have at least 2 log entries

            # Check first log record has doc_filename in extra
            start_log = next((r for r in log_records if "Starting" in r.message), None)
            assert start_log is not None
            assert hasattr(start_log, "doc_filename")
            assert start_log.doc_filename == "logging_test.pdf"
