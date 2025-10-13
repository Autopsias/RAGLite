"""Unit tests for document ingestion pipeline (PDF and Excel).

Tests the ingest_pdf and extract_excel functions with mocked dependencies.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np
import pytest

from raglite.ingestion.pipeline import (
    EmbeddingGenerationError,
    VectorStorageError,
    chunk_document,
    create_collection,
    extract_excel,
    generate_embeddings,
    get_embedding_model,
    ingest_document,
    ingest_pdf,
    store_vectors_in_qdrant,
)
from raglite.shared.clients import get_qdrant_client
from raglite.shared.models import Chunk, DocumentMetadata


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
        mock_document.export_to_markdown.return_value = "Financial Report Q4 2024\nRevenue Summary"

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
        mock_document.export_to_markdown.return_value = (
            "Content from page 1\nContent from page 2\nContent from page 3"
        )

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
        mock_document.export_to_markdown.return_value = "Content without page info"

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
        mock_document.export_to_markdown.return_value = "Test PDF content"

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


class TestChunkDocument:
    """Test suite for document chunking functionality."""

    @pytest.mark.asyncio
    async def test_chunk_document_basic(self):
        """Test basic chunking with 1000-word document.

        Verifies chunk_document returns correct number of chunks with proper
        size and overlap. AC1, AC6.
        """
        # Create 1000-word test text
        words = [f"word{i}" for i in range(1000)]
        full_text = " ".join(words)

        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=10,
            source_path="/tmp/test.pdf",
        )

        # Chunk with default parameters (500 words, 50 overlap)
        chunks = await chunk_document(full_text, metadata, chunk_size=500, overlap=50)

        # Should create 3 chunks: [0:500], [450:950], [900:1000]
        # Chunk 1: words 0-499 (500 words)
        # Chunk 2: words 450-949 (500 words, 50-word overlap with chunk 1)
        # Chunk 3: words 900-999 (100 words, 50-word overlap with chunk 2)
        assert len(chunks) == 3
        assert isinstance(chunks[0], Chunk)
        assert chunks[0].chunk_id == "test.pdf_0"
        assert chunks[1].chunk_id == "test.pdf_1"
        assert chunks[2].chunk_id == "test.pdf_2"

        # Verify chunk sizes
        chunk1_words = chunks[0].content.split()
        chunk2_words = chunks[1].content.split()
        chunk3_words = chunks[2].content.split()

        assert len(chunk1_words) == 500
        assert len(chunk2_words) == 500
        assert len(chunk3_words) == 100  # Last chunk is shorter

    @pytest.mark.asyncio
    async def test_chunk_overlap(self):
        """Test that chunks have correct 50-word overlap.

        Verifies last 50 words of chunk N match first 50 words of chunk N+1.
        AC1, AC6.
        """
        # Create 1000-word test text with numbered words
        words = [f"word{i}" for i in range(1000)]
        full_text = " ".join(words)

        metadata = DocumentMetadata(
            filename="overlap_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=5,
            source_path="/tmp/overlap_test.pdf",
        )

        chunks = await chunk_document(full_text, metadata, chunk_size=500, overlap=50)

        # Verify overlap between chunk 0 and chunk 1
        chunk0_words = chunks[0].content.split()
        chunk1_words = chunks[1].content.split()

        # Last 50 words of chunk 0
        chunk0_last_50 = chunk0_words[-50:]

        # First 50 words of chunk 1
        chunk1_first_50 = chunk1_words[:50]

        # Should match exactly
        assert chunk0_last_50 == chunk1_first_50

        # Verify specific word positions
        assert chunk0_last_50[0] == "word450"
        assert chunk0_last_50[-1] == "word499"
        assert chunk1_first_50[0] == "word450"
        assert chunk1_first_50[-1] == "word499"

    @pytest.mark.asyncio
    async def test_chunk_page_numbers(self):
        """CRITICAL: Verify all chunks have page_number != None.

        This test addresses AC8 and AC9 - ensures page numbers are populated
        for all chunks to enable source attribution (NFR7 requirement).
        """
        # Create multi-page document (2000 words ~ 10 pages)
        words = [f"page{i % 10}_word{i}" for i in range(2000)]
        full_text = " ".join(words)

        metadata = DocumentMetadata(
            filename="multipage.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=10,
            source_path="/tmp/multipage.pdf",
        )

        chunks = await chunk_document(full_text, metadata, chunk_size=500, overlap=50)

        # CRITICAL: All chunks must have page_number != None and > 0
        for idx, chunk in enumerate(chunks):
            assert chunk.page_number is not None, f"Chunk {idx} has None page_number"
            assert chunk.page_number > 0, (
                f"Chunk {idx} has invalid page_number: {chunk.page_number}"
            )
            assert chunk.page_number <= metadata.page_count, (
                f"Chunk {idx} page_number {chunk.page_number} exceeds page_count {metadata.page_count}"
            )

        # Verify page numbers are reasonable (should increase through document)
        # First chunk should be page 1
        assert chunks[0].page_number == 1

        # Last chunk should be near last page (within 1-2 pages)
        assert chunks[-1].page_number >= metadata.page_count - 2

    @pytest.mark.asyncio
    async def test_chunk_short_document(self):
        """Test document shorter than chunk size.

        Should return single chunk with correct page number. AC1, AC6.
        """
        # Create 200-word document (less than 500-word chunk size)
        words = [f"short{i}" for i in range(200)]
        full_text = " ".join(words)

        metadata = DocumentMetadata(
            filename="short.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=2,
            source_path="/tmp/short.pdf",
        )

        chunks = await chunk_document(full_text, metadata, chunk_size=500, overlap=50)

        # Should return exactly 1 chunk
        assert len(chunks) == 1
        assert chunks[0].chunk_id == "short.pdf_0"
        assert len(chunks[0].content.split()) == 200
        assert chunks[0].page_number == 1  # Should be page 1

    @pytest.mark.asyncio
    async def test_chunk_empty_document(self):
        """Test empty document handling.

        Should return empty list without crashing. AC6.
        """
        metadata = DocumentMetadata(
            filename="empty.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=0,
            source_path="/tmp/empty.pdf",
        )

        # Test with empty string
        chunks = await chunk_document("", metadata)
        assert chunks == []

        # Test with whitespace only
        chunks = await chunk_document("   \n\n  ", metadata)
        assert chunks == []

    @pytest.mark.asyncio
    async def test_chunk_invalid_parameters(self):
        """Test invalid chunk_size or overlap parameters.

        Should raise ValueError with clear message. AC6.
        """
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=5,
            source_path="/tmp/test.pdf",
        )

        full_text = "Some test content here"

        # Test negative chunk_size
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            await chunk_document(full_text, metadata, chunk_size=-100, overlap=50)

        # Test zero chunk_size
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            await chunk_document(full_text, metadata, chunk_size=0, overlap=50)

        # Test negative overlap
        with pytest.raises(ValueError, match="overlap must be non-negative"):
            await chunk_document(full_text, metadata, chunk_size=500, overlap=-10)

        # Test overlap >= chunk_size
        with pytest.raises(ValueError, match="overlap.*must be less than chunk_size"):
            await chunk_document(full_text, metadata, chunk_size=500, overlap=500)

        with pytest.raises(ValueError, match="overlap.*must be less than chunk_size"):
            await chunk_document(full_text, metadata, chunk_size=500, overlap=600)


class TestGenerateEmbeddings:
    """Test suite for embedding generation functionality (Story 1.5)."""

    @pytest.mark.asyncio
    async def test_generate_embeddings_basic(self):
        """Test basic embedding generation with sample chunks.

        Verifies generate_embeddings populates embedding field for all chunks
        with 1024-dimensional vectors. AC1, AC2.
        """
        # Create 10 sample chunks
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=5,
            source_path="/tmp/test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"test.pdf_{i}",
                content=f"Sample financial content for chunk {i}",
                metadata=metadata,
                page_number=i % 5 + 1,
                embedding=[],
            )
            for i in range(10)
        ]

        # Mock SentenceTransformer model
        with patch("raglite.ingestion.pipeline.get_embedding_model") as mock_get_model:
            mock_model = Mock()
            # Mock encode to return 1024-dimensional embeddings
            mock_embeddings = np.random.rand(10, 1024).astype(np.float32)
            mock_model.encode.return_value = mock_embeddings
            mock_get_model.return_value = mock_model

            # Generate embeddings
            result_chunks = await generate_embeddings(chunks)

            # Assertions
            assert len(result_chunks) == 10
            assert result_chunks is chunks  # Should modify in-place and return same list

            # Verify all chunks have embeddings populated
            for idx, chunk in enumerate(result_chunks):
                assert chunk.embedding is not None, f"Chunk {idx} has None embedding"
                assert len(chunk.embedding) == 1024, (
                    f"Chunk {idx} embedding has wrong dimensions: {len(chunk.embedding)}"
                )
                assert isinstance(chunk.embedding, list), (
                    "Embedding should be list for JSON serialization"
                )
                assert all(isinstance(x, float) for x in chunk.embedding), (
                    "All embedding values should be floats"
                )

            # Verify model.encode was called with batch_size=32
            mock_model.encode.assert_called_once()
            call_kwargs = mock_model.encode.call_args[1]
            assert call_kwargs["batch_size"] == 32
            assert call_kwargs["show_progress_bar"] is False

    @pytest.mark.asyncio
    async def test_embedding_dimensions(self):
        """Test that embeddings have exactly 1024 dimensions.

        Verifies Fin-E5 model generates correct vector dimensions. AC2.
        """
        metadata = DocumentMetadata(
            filename="dimensions_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=1,
            source_path="/tmp/dimensions_test.pdf",
        )

        chunk = Chunk(
            chunk_id="dimensions_test.pdf_0",
            content="Test content for dimension validation",
            metadata=metadata,
            page_number=1,
            embedding=[],
        )

        # Mock model to return 1024-dimensional embedding
        with patch("raglite.ingestion.pipeline.get_embedding_model") as mock_get_model:
            mock_model = Mock()
            mock_embedding = np.random.rand(1, 1024).astype(np.float32)
            mock_model.encode.return_value = mock_embedding
            mock_get_model.return_value = mock_model

            result_chunks = await generate_embeddings([chunk])

            # CRITICAL: Verify exact dimension count
            assert len(result_chunks[0].embedding) == 1024, (
                f"Expected 1024 dimensions, got {len(result_chunks[0].embedding)}"
            )

            # Verify all elements are floats
            for idx, value in enumerate(result_chunks[0].embedding):
                assert isinstance(value, float), (
                    f"Embedding value at index {idx} is not float: {type(value)}"
                )

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test batch processing with 100+ chunks.

        Verifies chunks are processed in batches of 32 for memory efficiency. AC3.
        """
        # Create 100 chunks to test batching
        metadata = DocumentMetadata(
            filename="batch_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=50,
            source_path="/tmp/batch_test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"batch_test.pdf_{i}",
                content=f"Batch content {i}",
                metadata=metadata,
                page_number=i % 50 + 1,
                embedding=[],
            )
            for i in range(100)
        ]

        # Mock model and track batch calls
        with patch("raglite.ingestion.pipeline.get_embedding_model") as mock_get_model:
            mock_model = Mock()

            # Track encode calls
            encode_call_count = 0
            batch_sizes = []

            def mock_encode(texts, batch_size=None, show_progress_bar=True):
                nonlocal encode_call_count
                encode_call_count += 1
                batch_sizes.append(len(texts))
                # Return embeddings matching input size
                return np.random.rand(len(texts), 1024).astype(np.float32)

            mock_model.encode.side_effect = mock_encode
            mock_get_model.return_value = mock_model

            # Generate embeddings
            result_chunks = await generate_embeddings(chunks)

            # Assertions
            assert len(result_chunks) == 100

            # Verify batching: 100 chunks / 32 batch_size = 4 batches (32, 32, 32, 4)
            assert encode_call_count == 4, f"Expected 4 batch calls, got {encode_call_count}"
            assert batch_sizes == [32, 32, 32, 4], (
                f"Expected batch sizes [32, 32, 32, 4], got {batch_sizes}"
            )

            # Verify all chunks have embeddings
            for chunk in result_chunks:
                assert len(chunk.embedding) == 1024

    @pytest.mark.asyncio
    async def test_empty_chunk_handling(self):
        """Test handling of empty chunk list.

        Verifies graceful handling when no chunks provided. AC6.
        """
        # Test with empty list
        result = await generate_embeddings([])

        # Should return empty list without error
        assert result == []

    @pytest.mark.asyncio
    async def test_embeddings_not_none(self):
        """CRITICAL: Verify all chunks have embeddings != None.

        This test validates AC8 - all chunks must have valid embeddings
        before Qdrant storage. Critical for retrieval accuracy (NFR6).
        """
        # Create 50 chunks
        metadata = DocumentMetadata(
            filename="validation_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=25,
            source_path="/tmp/validation_test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"validation_test.pdf_{i}",
                content=f"Content for validation chunk {i}",
                metadata=metadata,
                page_number=i % 25 + 1,
                embedding=[],
            )
            for i in range(50)
        ]

        # Mock model
        with patch("raglite.ingestion.pipeline.get_embedding_model") as mock_get_model:
            mock_model = Mock()

            def mock_encode(texts, batch_size=None, show_progress_bar=True):
                return np.random.rand(len(texts), 1024).astype(np.float32)

            mock_model.encode.side_effect = mock_encode
            mock_get_model.return_value = mock_model

            # Generate embeddings
            result_chunks = await generate_embeddings(chunks)

            # CRITICAL VALIDATION: All chunks must have embeddings != None and not empty
            for idx, chunk in enumerate(result_chunks):
                assert chunk.embedding is not None, (
                    f"Chunk {idx} has None embedding (CRITICAL FAILURE)"
                )
                assert chunk.embedding != [], (
                    f"Chunk {idx} has empty embedding list (CRITICAL FAILURE)"
                )
                assert len(chunk.embedding) == 1024, (
                    f"Chunk {idx} has invalid embedding dimension: {len(chunk.embedding)}"
                )

    @pytest.mark.asyncio
    async def test_embedding_generation_error_handling(self):
        """Test error handling when embedding generation fails.

        Verifies EmbeddingGenerationError is raised with clear message.
        """
        metadata = DocumentMetadata(
            filename="error_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=1,
            source_path="/tmp/error_test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id="error_test.pdf_0",
                content="Test content",
                metadata=metadata,
                page_number=1,
                embedding=[],
            )
        ]

        # Mock model to raise exception
        with patch("raglite.ingestion.pipeline.get_embedding_model") as mock_get_model:
            mock_model = Mock()
            mock_model.encode.side_effect = Exception("GPU out of memory")
            mock_get_model.return_value = mock_model

            # Should raise EmbeddingGenerationError
            with pytest.raises(EmbeddingGenerationError, match="Failed to generate embeddings"):
                await generate_embeddings(chunks)

    @pytest.mark.asyncio
    async def test_get_embedding_model_singleton(self):
        """Test that get_embedding_model returns cached model (singleton pattern).

        Verifies model is loaded once and reused. AC1.
        """
        # Clear the global embedding model cache before testing
        import raglite.ingestion.pipeline as pipeline_module

        original_model = pipeline_module._embedding_model
        pipeline_module._embedding_model = None

        try:
            with patch("raglite.ingestion.pipeline.SentenceTransformer") as MockST:
                # Mock SentenceTransformer
                mock_model = Mock()
                mock_model.get_sentence_embedding_dimension.return_value = 1024
                MockST.return_value = mock_model

                # First call should load model
                model1 = get_embedding_model()
                assert model1 is mock_model
                MockST.assert_called_once_with("intfloat/e5-large-v2")

                # Second call should return cached model (no new instantiation)
                model2 = get_embedding_model()
                assert model2 is model1
                MockST.assert_called_once()  # Still only called once
        finally:
            # Restore original model state
            pipeline_module._embedding_model = original_model

    @pytest.mark.asyncio
    async def test_generate_embeddings_logging(self, caplog):
        """Test that structured logging includes correct context.

        Verifies logging with extra={} fields for monitoring. AC1.
        """
        import logging

        caplog.set_level(logging.INFO)

        metadata = DocumentMetadata(
            filename="logging_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=1,
            source_path="/tmp/logging_test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"logging_test.pdf_{i}",
                content=f"Logging test content {i}",
                metadata=metadata,
                page_number=1,
                embedding=[],
            )
            for i in range(5)
        ]

        # Mock model
        with patch("raglite.ingestion.pipeline.get_embedding_model") as mock_get_model:
            mock_model = Mock()
            mock_model.encode.return_value = np.random.rand(5, 1024).astype(np.float32)
            mock_get_model.return_value = mock_model

            await generate_embeddings(chunks)

            # Verify log messages
            assert "Generating embeddings" in caplog.text
            assert "Embedding generation complete" in caplog.text

            # Verify structured logging context
            log_records = [r for r in caplog.records if r.name == "raglite.ingestion.pipeline"]
            assert len(log_records) >= 2

            # Check log has chunk_count in extra
            start_log = next((r for r in log_records if "Generating" in r.message), None)
            assert start_log is not None
            assert hasattr(start_log, "chunk_count")
            assert start_log.chunk_count == 5


class TestQdrantStorage:
    """Test suite for Qdrant vector storage (Story 1.6)."""

    @pytest.mark.asyncio
    async def test_create_collection_success(self):
        """Test successful collection creation with mocked Qdrant client.

        Verifies create_collection creates collection with correct parameters. AC2.
        """
        with patch("raglite.ingestion.pipeline.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections
            mock_get_client.return_value = mock_client

            # Create collection
            create_collection("financial_docs", vector_size=1024)

            # Verify collection was created with correct parameters
            mock_client.create_collection.assert_called_once()
            call_args = mock_client.create_collection.call_args
            assert call_args.kwargs["collection_name"] == "financial_docs"
            assert call_args.kwargs["vectors_config"].size == 1024
            assert call_args.kwargs["vectors_config"].distance.name == "COSINE"

    @pytest.mark.asyncio
    async def test_create_collection_idempotent(self):
        """Test collection creation is idempotent (doesn't error if exists).

        Verifies calling create_collection twice doesn't raise error. AC2.
        """
        with patch("raglite.ingestion.pipeline.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.name = "financial_docs"
            mock_collections = Mock()
            mock_collections.collections = [mock_collection]
            mock_client.get_collections.return_value = mock_collections
            mock_get_client.return_value = mock_client

            # Create collection (should skip because it exists)
            create_collection("financial_docs", vector_size=1024)

            # Verify create_collection was NOT called (already exists)
            mock_client.create_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_vectors_basic(self):
        """Test storing 10 chunks with embeddings successfully.

        Verifies store_vectors_in_qdrant stores all chunks and metadata. AC3, AC9.
        """
        metadata = DocumentMetadata(
            filename="test_doc.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=2,
            source_path="/tmp/test_doc.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"test_doc.pdf_{i}",
                content=f"Test chunk content {i} with financial data",
                metadata=metadata,
                page_number=1,
                embedding=[float(x) for x in range(1024)],
            )
            for i in range(10)
        ]

        with patch("raglite.ingestion.pipeline.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            # Mock get_collection to return points_count
            mock_collection_info = Mock()
            mock_collection_info.points_count = 10
            mock_client.get_collection.return_value = mock_collection_info

            mock_get_client.return_value = mock_client

            # Store vectors
            points_stored = await store_vectors_in_qdrant(chunks)

            # Assertions
            assert points_stored == 10
            mock_client.upsert.assert_called_once()

            # Verify metadata is preserved in payload
            call_args = mock_client.upsert.call_args
            points = call_args.kwargs["points"]
            assert len(points) == 10

            # Check first point has all required metadata
            first_point = points[0]
            assert first_point.payload["chunk_id"] == "test_doc.pdf_0"
            assert first_point.payload["text"] == "Test chunk content 0 with financial data"
            assert (
                first_point.payload["word_count"] == 7
            )  # "Test chunk content 0 with financial data"
            assert first_point.payload["source_document"] == "test_doc.pdf"
            assert first_point.payload["page_number"] == 1
            assert first_point.payload["chunk_index"] == 0

    @pytest.mark.asyncio
    async def test_batch_upload_processing(self):
        """Test batch processing for 250 chunks (batches of 100).

        Verifies chunks are uploaded in batches to prevent memory issues. AC10.
        """
        metadata = DocumentMetadata(
            filename="large_doc.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=50,
            source_path="/tmp/large_doc.pdf",
        )

        # Create 250 chunks
        chunks = [
            Chunk(
                chunk_id=f"large_doc.pdf_{i}",
                content=f"Chunk content {i}",
                metadata=metadata,
                page_number=i // 5,
                embedding=[float(x) for x in range(1024)],
            )
            for i in range(250)
        ]

        with patch("raglite.ingestion.pipeline.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            mock_collection_info = Mock()
            mock_collection_info.points_count = 250
            mock_client.get_collection.return_value = mock_collection_info

            mock_get_client.return_value = mock_client

            # Store vectors with batch_size=100
            points_stored = await store_vectors_in_qdrant(chunks, batch_size=100)

            # Verify 3 batches were uploaded (100, 100, 50)
            assert mock_client.upsert.call_count == 3
            assert points_stored == 250

            # Verify batch sizes
            calls = mock_client.upsert.call_args_list
            assert len(calls[0].kwargs["points"]) == 100  # First batch
            assert len(calls[1].kwargs["points"]) == 100  # Second batch
            assert len(calls[2].kwargs["points"]) == 50  # Third batch

    @pytest.mark.asyncio
    async def test_metadata_preservation(self):
        """Test all metadata fields are preserved in Qdrant payload.

        Verifies page_number, source_document, chunk_index, etc. preserved. AC3.
        """
        metadata = DocumentMetadata(
            filename="metadata_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=3,
            source_path="/tmp/metadata_test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"metadata_test.pdf_{i}",
                content=f"Content for page {i + 1}",
                metadata=metadata,
                page_number=i + 1,
                chunk_index=i,
                embedding=[float(x) for x in range(1024)],
            )
            for i in range(3)
        ]

        with patch("raglite.ingestion.pipeline.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            mock_collection_info = Mock()
            mock_collection_info.points_count = 3
            mock_client.get_collection.return_value = mock_collection_info

            mock_get_client.return_value = mock_client

            await store_vectors_in_qdrant(chunks)

            # Get uploaded points
            call_args = mock_client.upsert.call_args
            points = call_args.kwargs["points"]

            # Verify all metadata fields for each chunk
            for i, point in enumerate(points):
                payload = point.payload
                assert payload["chunk_id"] == f"metadata_test.pdf_{i}"
                assert payload["text"] == f"Content for page {i + 1}"
                assert payload["source_document"] == "metadata_test.pdf"
                assert payload["page_number"] == i + 1
                assert payload["chunk_index"] == i
                assert "word_count" in payload

    @pytest.mark.asyncio
    async def test_empty_chunks_handling(self):
        """Test graceful handling of empty chunk list.

        Verifies function returns 0 and doesn't call Qdrant for empty input. AC7.
        """
        with patch("raglite.ingestion.pipeline.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            # Store empty list
            points_stored = await store_vectors_in_qdrant([])

            # Assertions
            assert points_stored == 0
            mock_client.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_storage_error_handling(self):
        """Test VectorStorageError raised on storage failures.

        Verifies proper error handling when Qdrant upsert fails. AC6.
        """
        metadata = DocumentMetadata(
            filename="error_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=1,
            source_path="/tmp/error_test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id="error_test.pdf_0",
                content="Test content",
                metadata=metadata,
                page_number=1,
                embedding=[float(x) for x in range(1024)],
            )
        ]

        with patch("raglite.ingestion.pipeline.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            # Mock upsert to raise exception
            mock_client.upsert.side_effect = Exception("Connection timeout")

            mock_get_client.return_value = mock_client

            # Verify VectorStorageError is raised
            with pytest.raises(VectorStorageError, match="Failed to store vectors in Qdrant"):
                await store_vectors_in_qdrant(chunks)

    def test_get_qdrant_client_singleton(self):
        """Test Qdrant client singleton pattern (client reuse).

        Verifies get_qdrant_client returns same instance on multiple calls. AC6.
        """
        # Reset singleton (clean state for test)
        import raglite.shared.clients as clients_module

        clients_module._qdrant_client = None

        with patch("raglite.shared.clients.QdrantClient") as MockQdrantClient:
            mock_client_instance = Mock()
            MockQdrantClient.return_value = mock_client_instance

            # Call twice
            client1 = get_qdrant_client()
            client2 = get_qdrant_client()

            # Verify same instance returned
            assert client1 is client2
            # Verify QdrantClient constructor called only once
            MockQdrantClient.assert_called_once()

        # Reset singleton after test
        clients_module._qdrant_client = None
