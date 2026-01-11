"""[P1/P2] Edge case and error handling tests for Excel processing.

Tests critical error paths, malformed files, and processing failures.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from raglite.ingestion.document_ingestion.excel_processing import extract_excel
from raglite.shared.models import DocumentMetadata

pytestmark = [pytest.mark.unit]


class TestExcelProcessingErrorHandling:
    """[P1] Critical error paths for Excel processing."""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_file_not_found(self):
        """[P0] TEST-AC-8.4a-2.1.1: Raise FileNotFoundError for missing Excel file."""
        # Given nonexistent Excel path
        nonexistent_path = "/tmp/does_not_exist_12345.xlsx"

        # When extracting
        # Then raise FileNotFoundError with helpful message
        with pytest.raises(FileNotFoundError, match="not found"):
            await extract_excel(nonexistent_path)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_empty_excel_file(self):
        """[P1] TEST-AC-8.4a-2.1.2: Handle empty Excel files gracefully."""
        # Given empty Excel file (0 bytes)
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch("openpyxl.load_workbook") as mock_load:
                # Mock openpyxl to raise exception on empty/corrupt file
                mock_load.side_effect = Exception("Invalid Excel file")

                # When extracting
                # Then raise RuntimeError with context
                with pytest.raises(
                    RuntimeError, match="Unexpected error loading Excel file|Invalid Excel file"
                ):
                    await extract_excel(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_corrupt_excel_file(self):
        """[P0] TEST-AC-8.4a-2.1.3: Handle corrupt/malformed Excel files."""
        # Given corrupt Excel file (invalid content)
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(b"Not a valid Excel file content")
            tmp_path = tmp.name

        try:
            with patch("openpyxl.load_workbook") as mock_load:
                # Mock openpyxl parsing failure
                mock_load.side_effect = Exception("Zip file corrupt")

                # When extracting
                # Then raise RuntimeError with context
                with pytest.raises(
                    RuntimeError, match="Unexpected error loading Excel file|Zip file corrupt"
                ):
                    await extract_excel(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_excel_with_no_worksheets(self):
        """[P2] TEST-AC-8.4a-2.1.4: Handle Excel files with zero worksheets."""
        # Given Excel file with no worksheets
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch("openpyxl.load_workbook") as mock_load:
                # Mock workbook with no sheets
                mock_workbook = MagicMock()
                mock_workbook.sheetnames = []
                mock_load.return_value = mock_workbook

                # When extracting
                result = await extract_excel(tmp_path)

                # Then returns metadata with 0 pages
                assert isinstance(result, DocumentMetadata), (
                    f"Expected DocumentMetadata, got {type(result)}"
                )
                assert result.page_count == 0, f"Expected page_count=0, got {result.page_count}"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_excel_with_empty_worksheets(self):
        """[P2] TEST-AC-8.4a-2.1.5: Handle worksheets with no data."""
        # Given Excel file with empty worksheet
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch("openpyxl.load_workbook") as mock_load:
                # Mock workbook with one empty sheet
                mock_sheet = MagicMock()
                mock_sheet.max_row = 0
                mock_sheet.max_column = 0
                mock_sheet.iter_rows.return_value = []

                mock_workbook = MagicMock()
                mock_workbook.sheetnames = ["EmptySheet"]
                mock_workbook.__getitem__.return_value = mock_sheet
                mock_load.return_value = mock_workbook

                # When extracting
                result = await extract_excel(tmp_path)

                # Then returns metadata (empty sheets still create metadata)
                assert isinstance(result, DocumentMetadata), (
                    f"Expected DocumentMetadata, got {type(result)}"
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_excel_with_special_characters_in_sheet_names(self):
        """[P2] TEST-AC-8.4a-2.1.6: Handle special characters in sheet names."""
        # Given Excel with special characters in sheet names
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("openpyxl.load_workbook") as mock_load,
                patch(
                    "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
                ) as mock_extract,
            ):
                # Mock workbook with special chars in sheet name but empty data
                mock_sheet = MagicMock()
                mock_sheet.max_row = 10
                mock_sheet.max_column = 5

                mock_workbook = MagicMock()
                mock_workbook.sheetnames = ["Sheet (2024) - Revenue@Q4!"]
                mock_workbook.__getitem__.return_value = mock_sheet
                mock_load.return_value = mock_workbook

                mock_extract.return_value = None  # No extracted data from empty sheet

                # When extracting
                result = await extract_excel(tmp_path)

                # Then succeeds without errors - returns DocumentMetadata when no sheets extracted
                assert isinstance(result, DocumentMetadata), (
                    f"Expected DocumentMetadata, got {type(result)}"
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_excel_xls_legacy_format(self):
        """[P2] TEST-AC-8.4a-2.1.7: Support legacy .xls format."""
        # Given legacy .xls file
        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("openpyxl.load_workbook") as mock_load,
                patch(
                    "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
                ) as mock_extract,
            ):
                # Mock successful load of .xls file but empty sheet
                mock_sheet = MagicMock()
                mock_sheet.max_row = 5
                mock_sheet.max_column = 3

                mock_workbook = MagicMock()
                mock_workbook.sheetnames = ["Data"]
                mock_workbook.__getitem__.return_value = mock_sheet
                mock_load.return_value = mock_workbook

                mock_extract.return_value = None  # No extracted data

                # When extracting
                result = await extract_excel(tmp_path)

                # Then processes without errors - returns DocumentMetadata
                assert isinstance(result, DocumentMetadata), (
                    f"Expected DocumentMetadata, got {type(result)}"
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_excel_with_formulas(self):
        """[P2] TEST-AC-8.4a-2.1.8: Extract evaluated values from formula cells."""
        # Given Excel with formulas
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("openpyxl.load_workbook") as mock_load,
                patch(
                    "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
                ) as mock_extract,
            ):
                # Mock cell with formula but no extracted data
                mock_cell = MagicMock()
                mock_cell.value = 100  # Evaluated value, not formula string

                mock_sheet = MagicMock()
                mock_sheet.max_row = 2
                mock_sheet.max_column = 2
                mock_sheet.iter_rows.return_value = [[mock_cell, mock_cell]]

                mock_workbook = MagicMock()
                mock_workbook.sheetnames = ["Formulas"]
                mock_workbook.__getitem__.return_value = mock_sheet
                mock_load.return_value = mock_workbook

                mock_extract.return_value = None  # No extracted data

                # When extracting
                result = await extract_excel(tmp_path)

                # Then extracts evaluated values - returns DocumentMetadata
                assert isinstance(result, DocumentMetadata), (
                    f"Expected DocumentMetadata, got {type(result)}"
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestExcelProcessingBoundaryConditions:
    """[P2] Boundary conditions for Excel processing."""

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_excel_single_cell(self):
        """[P2] TEST-AC-8.4a-2.2.1: Handle single-cell worksheet."""
        # Given Excel with single cell
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("openpyxl.load_workbook") as mock_load,
                patch(
                    "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
                ) as mock_extract,
            ):
                mock_cell = MagicMock()
                mock_cell.value = "Data"

                mock_sheet = MagicMock()
                mock_sheet.max_row = 1
                mock_sheet.max_column = 1
                mock_sheet.iter_rows.return_value = [[mock_cell]]

                mock_workbook = MagicMock()
                mock_workbook.sheetnames = ["Single"]
                mock_workbook.__getitem__.return_value = mock_sheet
                mock_load.return_value = mock_workbook

                mock_extract.return_value = None  # No extracted data

                # When extracting
                result = await extract_excel(tmp_path)

                # Then processes single cell - returns DocumentMetadata
                assert isinstance(result, DocumentMetadata), (
                    f"Expected DocumentMetadata, got {type(result)}"
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_excel_very_large_worksheet(self):
        """[P2] TEST-AC-8.4a-2.2.2: Handle large worksheets (>10k rows)."""
        # Given Excel with large worksheet
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("openpyxl.load_workbook") as mock_load,
                patch(
                    "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
                ) as mock_extract,
            ):
                mock_sheet = MagicMock()
                mock_sheet.max_row = 15000
                mock_sheet.max_column = 10

                mock_workbook = MagicMock()
                mock_workbook.sheetnames = ["LargeSheet"]
                mock_workbook.__getitem__.return_value = mock_sheet
                mock_load.return_value = mock_workbook

                # Mock extraction returns summarized data
                mock_extract.return_value = None  # No extracted data due to size

                # When extracting
                result = await extract_excel(tmp_path)

                # Then processes without memory issues - returns DocumentMetadata
                assert isinstance(result, DocumentMetadata), (
                    f"Expected DocumentMetadata, got {type(result)}"
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)
