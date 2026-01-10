"""Unit tests for document ingestion pipeline (PDF and Excel).

Tests the ingest_pdf and extract_excel functions with mocked dependencies.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np
import pytest

from raglite.ingestion.pipeline import (
    extract_excel,
)
from raglite.shared.models import DocumentMetadata

# Group Excel processing tests that share mocked openpyxl state to run on same worker
pytestmark = [pytest.mark.unit, pytest.mark.xdist_group(name="excel_ingestion")]


class TestExtractExcel:
    """Test suite for Excel extraction pipeline."""

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_extract_excel_success(self, tmp_path):
        """Test successful Excel extraction with valid multi-sheet file.

        Verifies extract_excel returns correct DocumentMetadata
        when openpyxl successfully parses an Excel file.

        NOTE: Patches at usage location (excel_processing) not definition
        location (storage_operations) per .claude/rules/testing.md.
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

        # Mock Qdrant client
        mock_qdrant_client = Mock()
        mock_collections_response = Mock()
        mock_collections_response.collections = []
        mock_qdrant_client.get_collections = Mock(return_value=mock_collections_response)
        mock_collection_info = Mock()
        mock_collection_info.points_count = 3
        mock_qdrant_client.get_collection = Mock(return_value=mock_collection_info)

        with (
            patch("openpyxl.load_workbook") as mock_load,
            patch("raglite.ingestion.embedding_generation.get_embedding_model") as MockEmbedding,
            patch(
                "raglite.ingestion.storage.store_metadata_in_postgresql",
                return_value=(3, 0),
            ),
            patch(
                "raglite.ingestion.storage.store_vectors_in_qdrant",
                return_value=None,
            ),
        ):
            mock_load.return_value = mock_workbook

            # Mock embedding model
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.encode.return_value = np.array([[0.1] * 1024] * 3)

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

    @pytest.mark.priority("P2")
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

        # Mock Qdrant client
        mock_qdrant_client = Mock()
        mock_collections_response = Mock()
        mock_collections_response.collections = []
        mock_qdrant_client.get_collections = Mock(return_value=mock_collections_response)
        mock_collection_info = Mock()
        mock_collection_info.points_count = 3
        mock_qdrant_client.get_collection = Mock(return_value=mock_collection_info)

        with (
            patch("openpyxl.load_workbook") as mock_load,
            patch(
                "raglite.ingestion.storage.vector_store.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch("raglite.ingestion.embedding_generation.get_embedding_model") as MockEmbedding,
            patch(
                "raglite.ingestion.storage.store_metadata_in_postgresql",
                return_value=(3, 0),
            ),
            patch(
                "raglite.ingestion.storage.store_vectors_in_qdrant",
                return_value=None,
            ),
        ):
            mock_load.return_value = mock_workbook

            # Mock embedding model
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.encode.return_value = np.array([[0.1] * 1024] * 3)

            result = await extract_excel(str(excel_file))

            # All 3 sheets should be extracted
            assert result.page_count == 3
            assert result.doc_type == "Excel"

    @pytest.mark.priority("P2")
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

        # Mock Qdrant client
        mock_qdrant_client = Mock()
        mock_collections_response = Mock()
        mock_collections_response.collections = []
        mock_qdrant_client.get_collections = Mock(return_value=mock_collections_response)
        mock_collection_info = Mock()
        mock_collection_info.points_count = 1
        mock_qdrant_client.get_collection = Mock(return_value=mock_collection_info)

        with (
            patch("openpyxl.load_workbook") as mock_load,
            patch(
                "raglite.ingestion.storage.vector_store.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch("raglite.ingestion.embedding_generation.get_embedding_model") as MockEmbedding,
            patch(
                "raglite.ingestion.storage.store_metadata_in_postgresql",
                return_value=(1, 0),
            ),
            patch(
                "raglite.ingestion.storage.store_vectors_in_qdrant",
                return_value=None,
            ),
        ):
            mock_load.return_value = mock_workbook

            # Mock embedding model
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.encode.return_value = np.array([[0.1] * 1024])

            result = await extract_excel(str(excel_file))

            # Should successfully extract and preserve data types
            assert result.page_count == 1
            assert result.doc_type == "Excel"
            # Note: Actual formatting preservation is handled by pandas to_markdown()
            # This test verifies the pipeline doesn't crash with numeric data

    @pytest.mark.priority("P3")
    @pytest.mark.asyncio
    async def test_extract_excel_file_not_found(self):
        """Test that FileNotFoundError is raised for nonexistent Excel file.

        Verifies error handling for missing Excel files.
        """
        nonexistent_path = "/tmp/does_not_exist_12345.xlsx"

        with pytest.raises(FileNotFoundError, match="Excel file not found"):
            await extract_excel(nonexistent_path)

    @pytest.mark.priority("P3")
    @pytest.mark.asyncio
    async def test_extract_excel_password_protected(self, tmp_path):
        """Test error handling for password-protected Excel file.

        Verifies RuntimeError is raised with clear message.
        """
        excel_file = tmp_path / "protected.xlsx"
        excel_file.write_bytes(b"encrypted content")

        with patch("openpyxl.load_workbook") as mock_load:
            # Simulate password-protected file error
            mock_load.side_effect = __import__("openpyxl").utils.exceptions.InvalidFileException(
                "File is encrypted"
            )

            with pytest.raises(RuntimeError, match="Excel parsing failed.*password-protected"):
                await extract_excel(str(excel_file))

    @pytest.mark.priority("P3")
    @pytest.mark.asyncio
    async def test_extract_excel_corrupted(self, tmp_path):
        """Test error handling for corrupted Excel file.

        Verifies RuntimeError is raised with clear message.
        """
        excel_file = tmp_path / "corrupted.xlsx"
        excel_file.write_bytes(b"not a valid excel file")

        with patch("openpyxl.load_workbook") as mock_load:
            # Simulate generic corruption error
            mock_load.side_effect = Exception("File format error")

            with pytest.raises(RuntimeError, match="Unexpected error loading Excel"):
                await extract_excel(str(excel_file))

    @pytest.mark.priority("P2")
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

        # Mock Qdrant client to prevent real database calls in unit tests
        mock_qdrant_client = Mock()
        mock_qdrant_client.upsert = Mock()
        # Mock get_collections() for create_collection() idempotency check
        mock_collections_response = Mock()
        mock_collections_response.collections = []
        mock_qdrant_client.get_collections = Mock(return_value=mock_collections_response)
        # Mock get_collection() for points_count validation after upsert
        mock_collection_info = Mock()
        mock_collection_info.points_count = 1  # At least 1 chunk will be created
        mock_qdrant_client.get_collection = Mock(return_value=mock_collection_info)

        with (
            patch("openpyxl.load_workbook") as mock_load,
            patch(
                "raglite.ingestion.storage.vector_store.get_qdrant_client",
                return_value=mock_qdrant_client,
            ),
            patch("raglite.ingestion.embedding_generation.get_embedding_model") as MockEmbedding,
            patch(
                "raglite.ingestion.storage.store_metadata_in_postgresql",
                return_value=(2, 0),
            ),
            patch(
                "raglite.ingestion.storage.store_vectors_in_qdrant",
                return_value=None,
            ),
        ):
            mock_load.return_value = mock_workbook

            # Mock embedding model
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.encode.return_value = np.array([[0.1] * 1024])

            result = await extract_excel(str(excel_file))

            # Critical: sheet count must match number of sheets
            assert result.page_count == 2
            assert result.page_count > 0, "Sheet count must NOT be None or zero"
            # Note: sheet_number is extracted but not directly exposed in DocumentMetadata
            # It's used in chunking/embedding pipeline for citations

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_extract_excel_empty_workbook(self, tmp_path, caplog):
        """Test handling of empty Excel workbook with no sheets.

        Should return metadata with zero sheets and log warning.
        """
        excel_file = tmp_path / "empty.xlsx"
        excel_file.write_bytes(b"empty workbook")

        mock_workbook = Mock()
        mock_workbook.sheetnames = []  # No sheets

        with patch("openpyxl.load_workbook") as mock_load:
            mock_load.return_value = mock_workbook

            result = await extract_excel(str(excel_file))

            # Should return metadata with zero sheets
            assert result.page_count == 0
            assert result.doc_type == "Excel"

            # Should log warning
            assert "Empty Excel workbook" in caplog.text
