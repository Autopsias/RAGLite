"""Core TableExtractor tests - basic functionality and initialization.

Tests the TableExtractor class basic operations:
- Initialization (with/without custom converter)
- Table extraction workflow
- Caption extraction
- Table structure parsing
"""

from unittest.mock import AsyncMock, Mock

import pytest

# Lazy import pattern: defer heavy module import until test execution
# raglite.ingestion.table_extraction imports Docling which is slow
_TableExtractor = None


def _get_table_extractor():
    """Lazy load TableExtractor to avoid slow import during test collection."""
    global _TableExtractor
    if _TableExtractor is None:
        from raglite.ingestion.table_extraction import TableExtractor

        _TableExtractor = TableExtractor
    return _TableExtractor


class TestTableExtractor:
    """Test suite for TableExtractor class basic functionality."""

    def setup_method(self):
        """Simple setup - create extractor with mock converter."""
        TableExtractor = _get_table_extractor()
        self.mock_converter = Mock()
        self.extractor = TableExtractor(converter=self.mock_converter)

    @pytest.mark.asyncio
    async def test_extract_tables_success(self):
        """Test successful table extraction from document."""
        # Arrange: Mock converter result
        mock_result = Mock()
        mock_table_item = Mock()
        mock_table_item.prov = [Mock(page_no=1)]

        # Mock document iteration to return one table
        mock_result.document.iterate_items.return_value = [(mock_table_item, Mock())]

        self.mock_converter.convert.return_value = mock_result

        # Mock the async extraction to return sample rows
        sample_rows = [
            {
                "entity": "Portugal",
                "metric": "Revenue",
                "value": 100.0,
                "unit": "EUR/ton",
                "period": "Aug-25",
                "fiscal_year": 2025,
            }
        ]

        # Patch the async extraction method
        self.extractor.extract_tables_from_result = AsyncMock(return_value=sample_rows)

        # Act
        result = await self.extractor.extract_tables("test.pdf")

        # Assert - verify real functionality
        assert len(result) == 1
        assert result[0]["entity"] == "Portugal"
        assert result[0]["value"] == 100.0
        self.mock_converter.convert.assert_called_once_with("test.pdf")

    @pytest.mark.asyncio
    async def test_extract_tables_empty_document(self):
        """Test extraction from document with no tables."""
        # Arrange
        mock_result = Mock()
        mock_result.document.iterate_items.return_value = []
        self.mock_converter.convert.return_value = mock_result

        # Mock empty extraction
        self.extractor.extract_tables_from_result = AsyncMock(return_value=[])

        # Act
        result = await self.extractor.extract_tables("empty.pdf")

        # Assert
        assert result == []
        assert len(result) == 0

    def test_extract_caption_from_markdown(self):
        """Test caption extraction from table markdown."""
        # Arrange - markdown with caption
        markdown_with_caption = """Financial Performance Summary
| Entity | Revenue |
|--------|---------|
| Portugal | 100 |"""

        # Act
        caption = self.extractor._extract_caption(markdown_with_caption)

        # Assert
        assert caption == "Financial Performance Summary"

    def test_extract_caption_no_caption(self):
        """Test caption extraction when no caption exists."""
        # Arrange - markdown without caption (starts with table)
        markdown_no_caption = """| Entity | Revenue |
|--------|---------|
| Portugal | 100 |"""

        # Act
        caption = self.extractor._extract_caption(markdown_no_caption)

        # Assert
        assert caption is None

    def test_extract_caption_with_headers(self):
        """Test caption extraction skips markdown headers."""
        # Arrange - markdown with header and table
        markdown_with_header = """# Section Header
| Entity | Revenue |
|--------|---------|"""

        # Act
        caption = self.extractor._extract_caption(markdown_with_header)

        # Assert
        assert caption is None  # Header lines are skipped

    def test_init_with_provided_converter(self):
        """Test TableExtractor initialization with custom converter."""
        # Arrange
        TableExtractor = _get_table_extractor()
        custom_converter = Mock()

        # Act
        extractor = TableExtractor(converter=custom_converter)

        # Assert
        assert extractor.converter is custom_converter

    def test_init_creates_default_converter_when_none_provided(self):
        """Test TableExtractor creates default converter when none provided."""
        # Act - create extractor without converter
        # This will import Docling modules (lazy loading)
        TableExtractor = _get_table_extractor()
        extractor = TableExtractor(converter=None)

        # Assert - converter should be created
        assert extractor.converter is not None

    def test_parse_table_structure_empty_table_cells(self):
        """Test parsing table with no table cells returns empty list."""
        # Arrange - mock table with empty table_cells
        mock_table_item = Mock()
        mock_table_item.data.table_cells = None  # Empty table
        mock_table_item.prov = [Mock(page_no=1)]
        mock_table_item.export_to_markdown.return_value = "| Empty |"

        mock_result = Mock()
        mock_result.document = Mock()

        # Act
        rows = self.extractor._parse_table_structure(
            mock_table_item, mock_result, table_index=0, document_id="test"
        )

        # Assert
        assert rows == []

    def test_parse_table_structure_with_data_cells(self):
        """Test parsing table structure with actual data cells."""
        # Arrange - create mock table with headers and data
        mock_table_item = Mock()

        # Mock column headers
        mock_col_header = Mock()
        mock_col_header.column_header = True
        mock_col_header.row_header = False
        mock_col_header.start_row_offset_idx = 0
        mock_col_header.start_col_offset_idx = 0
        mock_col_header.text = "Aug-25"

        # Mock row header
        mock_row_header = Mock()
        mock_row_header.column_header = False
        mock_row_header.row_header = True
        mock_row_header.start_row_offset_idx = 1
        mock_row_header.text = "Aug-25 YTD"

        # Mock data cell
        mock_data_cell = Mock()
        mock_data_cell.column_header = False
        mock_data_cell.row_header = False
        mock_data_cell.text = "100.5 EUR/ton"
        mock_data_cell.start_row_offset_idx = 1
        mock_data_cell.start_col_offset_idx = 0

        # Setup table cells
        mock_table_item.data.table_cells = [
            mock_col_header,
            mock_row_header,
            mock_data_cell,
        ]
        mock_table_item.data.num_rows = 2
        mock_table_item.data.num_cols = 1
        mock_table_item.prov = [Mock(page_no=5)]
        mock_table_item.export_to_markdown.return_value = "Test Table\n| Aug-25 |\n| 100.5 |"

        mock_result = Mock()
        mock_result.document = Mock()

        # Act
        rows = self.extractor._parse_table_structure(
            mock_table_item, mock_result, table_index=2, document_id="financial_report"
        )

        # Assert - verify real business logic
        assert len(rows) == 1
        assert rows[0]["value"] == 100.5
        assert rows[0]["unit"] == "EUR/ton"
        assert rows[0]["period"] == "Aug-25 YTD"
        assert rows[0]["fiscal_year"] == 2025
        assert rows[0]["page_number"] == 5
        assert rows[0]["table_index"] == 2
        assert rows[0]["document_id"] == "financial_report"

    def test_parse_table_structure_skips_empty_cells(self):
        """Test that empty data cells are skipped during parsing."""
        # Arrange
        mock_table_item = Mock()

        # Data cell with empty text
        mock_empty_cell = Mock()
        mock_empty_cell.column_header = False
        mock_empty_cell.row_header = False
        mock_empty_cell.text = "   "  # Whitespace only

        # Data cell with None text
        mock_none_cell = Mock()
        mock_none_cell.column_header = False
        mock_none_cell.row_header = False
        mock_none_cell.text = None

        mock_table_item.data.table_cells = [mock_empty_cell, mock_none_cell]
        mock_table_item.data.num_rows = 1
        mock_table_item.data.num_cols = 2
        mock_table_item.prov = [Mock(page_no=1)]
        mock_table_item.export_to_markdown.return_value = "| | |"

        mock_result = Mock()
        mock_result.document = Mock()

        # Act
        rows = self.extractor._parse_table_structure(
            mock_table_item, mock_result, table_index=0, document_id="test"
        )

        # Assert - empty cells should be skipped
        assert rows == []

    def test_parse_table_structure_no_prov_defaults_page_1(self):
        """Test that missing prov defaults to page 1."""
        # Arrange
        mock_table_item = Mock()
        mock_table_item.data.table_cells = []
        mock_table_item.prov = []  # No provenance info
        mock_table_item.export_to_markdown.return_value = "| Test |"

        mock_result = Mock()
        mock_result.document = Mock()

        # Act
        rows = self.extractor._parse_table_structure(
            mock_table_item, mock_result, table_index=0, document_id="test"
        )

        # Assert - should handle missing prov gracefully
        assert rows == []

    @pytest.mark.asyncio
    async def test_extract_tables_from_result_multiple_tables(self):
        """Test extraction from result with multiple tables."""
        # Arrange - mock result with 2 tables
        from docling_core.types.doc import TableItem

        mock_result = Mock()
        mock_table1 = Mock(spec=TableItem)
        mock_table1.prov = [Mock(page_no=1)]
        mock_table1.data = Mock()
        mock_table1.data.table_cells = []
        mock_table1.data.num_rows = 1
        mock_table1.data.num_cols = 1
        mock_table2 = Mock(spec=TableItem)
        mock_table2.prov = [Mock(page_no=2)]
        mock_table2.data = Mock()
        mock_table2.data.table_cells = []
        mock_table2.data.num_rows = 1
        mock_table2.data.num_cols = 1

        # Mock iteration to return 2 tables
        mock_result.document.iterate_items.return_value = [
            (mock_table1, Mock()),
            (mock_table2, Mock()),
        ]

        # Mock adaptive extraction to return rows for each table
        async def mock_extract(
            table_item, result, table_index, document_id, page_number, unit_cache=None
        ):
            return [{"table_index": table_index, "page_number": page_number}]

        # Patch the adaptive extraction function
        from unittest.mock import patch

        with patch(
            "raglite.ingestion.table_extraction.extraction.extract_table_data_adaptive",
            side_effect=mock_extract,
        ):
            # Act
            result = await self.extractor.extract_tables_from_result(mock_result, "test_doc")

            # Assert - verify both tables processed
            assert len(result) == 2
            assert result[0]["table_index"] == 0
            assert result[1]["table_index"] == 1
            assert result[0]["page_number"] == 1
            assert result[1]["page_number"] == 2

    @pytest.mark.asyncio
    async def test_extract_tables_from_result_non_table_items(self):
        """Test extraction skips non-table items."""
        # Arrange - mock result with mixed items (text + table)
        from docling_core.types.doc import TableItem

        mock_result = Mock()
        mock_text_item = Mock()  # Not a TableItem
        mock_table_item = Mock(spec=TableItem)
        mock_table_item.prov = [Mock(page_no=1)]
        mock_table_item.data = Mock()
        mock_table_item.data.table_cells = []
        mock_table_item.data.num_rows = 1
        mock_table_item.data.num_cols = 1

        mock_result.document.iterate_items.return_value = [
            (mock_text_item, Mock()),  # Should be skipped
            (mock_table_item, Mock()),  # Should be processed
        ]

        # Mock adaptive extraction
        async def mock_extract(
            table_item, result, table_index, document_id, page_number, unit_cache=None
        ):
            return [{"table_index": table_index}]

        from unittest.mock import patch

        with patch(
            "raglite.ingestion.table_extraction.extraction.extract_table_data_adaptive",
            side_effect=mock_extract,
        ):
            # Act
            result = await self.extractor.extract_tables_from_result(mock_result, "test_doc")

            # Assert - only table item processed
            assert len(result) == 1
            assert result[0]["table_index"] == 0
