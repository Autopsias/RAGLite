"""Unit tests for document ingestion pipeline (PDF and Excel).

Tests the ingest_pdf and extract_excel functions with mocked dependencies.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from raglite.ingestion.pipeline import (
    ingest_document,
)
from raglite.shared.models import DocumentMetadata

pytestmark = [pytest.mark.unit]


class TestIngestDocument:
    """Test suite for unified document ingestion router."""

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_ingest_document_pdf(self, tmp_path):
        """Test that ingest_document routes PDF files to ingest_pdf."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        # Mock the ingest_pdf function - Patch where it's USED (in core.py), not where it's defined
        with patch("raglite.ingestion.document_ingestion.core.ingest_pdf") as mock_ingest_pdf:
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

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_ingest_document_excel(self, tmp_path):
        """Test that ingest_document routes Excel files to extract_excel."""
        excel_file = tmp_path / "test.xlsx"
        excel_file.write_bytes(b"excel content")

        # Mock the extract_excel function - Patch where it's USED (in core.py), not where it's defined
        with patch("raglite.ingestion.document_ingestion.core.extract_excel") as mock_extract_excel:
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

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_ingest_document_unsupported_format(self, tmp_path):
        """Test that ingest_document raises ValueError for unsupported formats."""
        unsupported_file = tmp_path / "test.txt"
        unsupported_file.write_bytes(b"text content")

        with pytest.raises(ValueError, match="Unsupported file format: .txt"):
            await ingest_document(str(unsupported_file))

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_ingest_document_file_not_found(self):
        """Test that ingest_document raises FileNotFoundError for missing files."""
        nonexistent_path = "/tmp/nonexistent_12345.pdf"

        with pytest.raises(FileNotFoundError, match="Document file not found"):
            await ingest_document(nonexistent_path)
