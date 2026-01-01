"""Unit tests for table extraction core functionality (Story 2.13).

Tests the TableExtractor class core methods for extracting tables from documents
and initializing the extractor.

Coverage target: 80%+ for raglite/ingestion/table_extraction.py
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from raglite.ingestion.table_extraction import TableExtractor

pytestmark = [pytest.mark.unit]


class TestTableExtractorCoreExtraction:
    """Test suite for TableExtractor core extraction methods."""

    def setup_method(self):
        """Simple setup - create extractor with mock converter."""
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

        with patch(
            "raglite.ingestion.table_extraction.extraction.extract_table_data_adaptive",
            side_effect=mock_extract,
        ):
            # Act
            result = await self.extractor.extract_tables_from_result(mock_result, "test_doc")

            # Assert - only table item processed
            assert len(result) == 1
            assert result[0]["table_index"] == 0

    def test_init_with_provided_converter(self):
        """Test TableExtractor initialization with custom converter."""
        # Arrange
        custom_converter = Mock()

        # Act
        extractor = TableExtractor(converter=custom_converter)

        # Assert
        assert extractor.converter is custom_converter

    def test_init_creates_default_converter_when_none_provided(self):
        """Test TableExtractor creates default converter when none provided."""
        # Act - create extractor without converter
        # This will import Docling modules (lazy loading)
        extractor = TableExtractor(converter=None)

        # Assert - converter should be created
        assert extractor.converter is not None

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

    def test_parse_markdown_row_basic(self):
        """Test markdown row parsing."""
        # Act
        cells = self.extractor._parse_markdown_row("| Entity | Metric | Value |")

        # Assert
        assert cells == ["Entity", "Metric", "Value"]

    def test_parse_markdown_row_with_whitespace(self):
        """Test markdown row parsing with extra whitespace."""
        # Act
        cells = self.extractor._parse_markdown_row("|  Entity  |  Metric  |  Value  |")

        # Assert - verify whitespace is stripped
        assert cells == ["Entity", "Metric", "Value"]
