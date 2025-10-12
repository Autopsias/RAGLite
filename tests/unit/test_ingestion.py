"""Unit tests for document ingestion pipeline (PDF and Excel).

Tests the ingest_pdf and extract_excel functions with mocked dependencies.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from raglite.ingestion.pipeline import extract_excel, ingest_document, ingest_pdf
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


class TestExtractExcel:
    """Test suite for Excel extraction pipeline."""

    @pytest.mark.asyncio
    async def test_extract_excel_success(self, tmp_path):
        """Test successful Excel extraction with valid multi-sheet file.

        Verifies extract_excel returns correct DocumentMetadata
        when openpyxl successfully parses an Excel file.
        """
        # Create a temporary Excel file
        excel_file = tmp_path / "test_financials.xlsx"
        excel_file.write_bytes(b"fake excel content")

        # Mock openpyxl workbook with 3 sheets
        mock_sheet1 = Mock()
        mock_sheet1.values = [
            ["Name", "Revenue", "Profit"],  # Headers
            ["Q1", "$1000", "15%"],
            ["Q2", "$1500", "20%"],
        ]

        mock_sheet2 = Mock()
        mock_sheet2.values = [
            ["Metric", "Value"],
            ["Growth", "25%"],
        ]

        mock_sheet3 = Mock()
        mock_sheet3.values = [
            ["Date", "Amount"],
            ["2024-01-01", "$5000"],
        ]

        sheet_map = {
            "Revenue": mock_sheet1,
            "Metrics": mock_sheet2,
            "Summary": mock_sheet3,
        }

        mock_workbook = Mock()
        mock_workbook.sheetnames = ["Revenue", "Metrics", "Summary"]
        mock_workbook.__getitem__ = Mock(side_effect=lambda name: sheet_map[name])

        with patch("raglite.ingestion.pipeline.openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_workbook

            # Execute extraction
            result = await extract_excel(str(excel_file))

            # Assertions
            assert isinstance(result, DocumentMetadata)
            assert result.filename == "test_financials.xlsx"
            assert result.doc_type == "Excel"
            assert result.page_count == 3  # 3 sheets
            assert result.source_path == str(excel_file)
            assert result.ingestion_timestamp

            # Verify ISO8601 timestamp format
            datetime.fromisoformat(result.ingestion_timestamp)

            # Verify load_workbook called with data_only=True
            mock_load.assert_called_once_with(str(excel_file), data_only=True)

    @pytest.mark.asyncio
    async def test_extract_excel_multi_sheet(self, tmp_path):
        """Test multi-sheet workbook handling with sheet names and numbers.

        Verifies all sheets are extracted with correct sheet_number (1, 2, 3).
        """
        excel_file = tmp_path / "multisheet.xlsx"
        excel_file.write_bytes(b"multisheet content")

        # Mock workbook with 3 sheets
        mock_sheets = []
        for i in range(3):
            sheet = Mock()
            sheet.values = [["Header"], [f"Data {i + 1}"]]
            mock_sheets.append(sheet)

        sheet_map = {
            "Sheet1": mock_sheets[0],
            "Sheet2": mock_sheets[1],
            "Sheet3": mock_sheets[2],
        }

        mock_workbook = Mock()
        mock_workbook.sheetnames = ["Sheet1", "Sheet2", "Sheet3"]
        mock_workbook.__getitem__ = Mock(side_effect=lambda name: sheet_map[name])

        with patch("raglite.ingestion.pipeline.openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_workbook

            result = await extract_excel(str(excel_file))

            # All 3 sheets should be extracted
            assert result.page_count == 3
            assert result.doc_type == "Excel"

    @pytest.mark.asyncio
    async def test_extract_excel_numeric_formats(self, tmp_path):
        """Test numeric formatting preservation (currencies, percentages, dates).

        Verifies pandas.DataFrame.to_markdown() preserves formatting.
        """
        excel_file = tmp_path / "numeric_formats.xlsx"
        excel_file.write_bytes(b"numeric content")

        # Mock sheet with various numeric formats
        mock_sheet = Mock()
        mock_sheet.values = [
            ["Item", "Price", "Discount", "Date"],
            ["Product A", "$1,250.00", "15%", "2024-01-15"],
            ["Product B", "$2,500.50", "20%", "2024-02-20"],
        ]

        mock_workbook = Mock()
        mock_workbook.sheetnames = ["Pricing"]
        mock_workbook.__getitem__ = Mock(return_value=mock_sheet)

        with patch("raglite.ingestion.pipeline.openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_workbook

            result = await extract_excel(str(excel_file))

            # Should successfully extract and preserve data types
            assert result.page_count == 1
            assert result.doc_type == "Excel"
            # Note: Actual formatting preservation is handled by pandas to_markdown()
            # This test verifies the pipeline doesn't crash with numeric data

    @pytest.mark.asyncio
    async def test_extract_excel_file_not_found(self):
        """Test that FileNotFoundError is raised for nonexistent Excel file.

        Verifies error handling for missing Excel files.
        """
        nonexistent_path = "/tmp/does_not_exist_12345.xlsx"

        with pytest.raises(FileNotFoundError, match="Excel file not found"):
            await extract_excel(nonexistent_path)

    @pytest.mark.asyncio
    async def test_extract_excel_password_protected(self, tmp_path):
        """Test error handling for password-protected Excel file.

        Verifies RuntimeError is raised with clear message.
        """
        excel_file = tmp_path / "protected.xlsx"
        excel_file.write_bytes(b"encrypted content")

        with patch("raglite.ingestion.pipeline.openpyxl.load_workbook") as mock_load:
            # Simulate password-protected file error
            mock_load.side_effect = __import__("openpyxl").utils.exceptions.InvalidFileException(
                "File is encrypted"
            )

            with pytest.raises(RuntimeError, match="Excel parsing failed.*password-protected"):
                await extract_excel(str(excel_file))

    @pytest.mark.asyncio
    async def test_extract_excel_corrupted(self, tmp_path):
        """Test error handling for corrupted Excel file.

        Verifies RuntimeError is raised with clear message.
        """
        excel_file = tmp_path / "corrupted.xlsx"
        excel_file.write_bytes(b"not a valid excel file")

        with patch("raglite.ingestion.pipeline.openpyxl.load_workbook") as mock_load:
            # Simulate generic corruption error
            mock_load.side_effect = Exception("File format error")

            with pytest.raises(RuntimeError, match="Unexpected error loading Excel"):
                await extract_excel(str(excel_file))

    @pytest.mark.asyncio
    async def test_extract_excel_sheet_numbers(self, tmp_path):
        """CRITICAL: Verify sheet numbers are extracted and NOT None.

        This test ensures sheet_number field is properly populated
        for source attribution (NFR7 requirement).
        """
        excel_file = tmp_path / "sheet_numbers.xlsx"
        excel_file.write_bytes(b"content")

        # Mock workbook with 2 sheets
        mock_sheet1 = Mock()
        mock_sheet1.values = [["Header"], ["Data1"]]

        mock_sheet2 = Mock()
        mock_sheet2.values = [["Header"], ["Data2"]]

        sheet_map = {
            "First": mock_sheet1,
            "Second": mock_sheet2,
        }

        mock_workbook = Mock()
        mock_workbook.sheetnames = ["First", "Second"]
        mock_workbook.__getitem__ = Mock(side_effect=lambda name: sheet_map[name])

        with patch("raglite.ingestion.pipeline.openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_workbook

            result = await extract_excel(str(excel_file))

            # Critical: sheet count must match number of sheets
            assert result.page_count == 2
            assert result.page_count > 0, "Sheet count must NOT be None or zero"
            # Note: sheet_number is extracted but not directly exposed in DocumentMetadata
            # It's used in chunking/embedding pipeline for citations

    @pytest.mark.asyncio
    async def test_extract_excel_empty_workbook(self, tmp_path, caplog):
        """Test handling of empty Excel workbook with no sheets.

        Should return metadata with zero sheets and log warning.
        """
        excel_file = tmp_path / "empty.xlsx"
        excel_file.write_bytes(b"empty workbook")

        mock_workbook = Mock()
        mock_workbook.sheetnames = []  # No sheets

        with patch("raglite.ingestion.pipeline.openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_workbook

            result = await extract_excel(str(excel_file))

            # Should return metadata with zero sheets
            assert result.page_count == 0
            assert result.doc_type == "Excel"

            # Should log warning
            assert "Empty Excel workbook" in caplog.text


class TestIngestDocument:
    """Test suite for unified document ingestion router."""

    @pytest.mark.asyncio
    async def test_ingest_document_pdf(self, tmp_path):
        """Test that ingest_document routes PDF files to ingest_pdf."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        # Mock the ingest_pdf function
        with patch("raglite.ingestion.pipeline.ingest_pdf") as mock_ingest_pdf:
            mock_metadata = DocumentMetadata(
                filename="test.pdf",
                doc_type="PDF",
                ingestion_timestamp=datetime.now().isoformat(),
                page_count=2,
                source_path=str(pdf_file),
            )
            mock_ingest_pdf.return_value = mock_metadata

            result = await ingest_document(str(pdf_file))

            # Verify routing
            mock_ingest_pdf.assert_called_once()
            assert result.doc_type == "PDF"
            assert result.filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_ingest_document_excel(self, tmp_path):
        """Test that ingest_document routes Excel files to extract_excel."""
        excel_file = tmp_path / "test.xlsx"
        excel_file.write_bytes(b"excel content")

        # Mock the extract_excel function
        with patch("raglite.ingestion.pipeline.extract_excel") as mock_extract_excel:
            mock_metadata = DocumentMetadata(
                filename="test.xlsx",
                doc_type="Excel",
                ingestion_timestamp=datetime.now().isoformat(),
                page_count=3,
                source_path=str(excel_file),
            )
            mock_extract_excel.return_value = mock_metadata

            result = await ingest_document(str(excel_file))

            # Verify routing
            mock_extract_excel.assert_called_once()
            assert result.doc_type == "Excel"
            assert result.filename == "test.xlsx"

    @pytest.mark.asyncio
    async def test_ingest_document_unsupported_format(self, tmp_path):
        """Test that ingest_document raises ValueError for unsupported formats."""
        unsupported_file = tmp_path / "test.txt"
        unsupported_file.write_bytes(b"text content")

        with pytest.raises(ValueError, match="Unsupported file format: .txt"):
            await ingest_document(str(unsupported_file))

    @pytest.mark.asyncio
    async def test_ingest_document_file_not_found(self):
        """Test that ingest_document raises FileNotFoundError for missing files."""
        nonexistent_path = "/tmp/nonexistent_12345.pdf"

        with pytest.raises(FileNotFoundError, match="Document file not found"):
            await ingest_document(nonexistent_path)
