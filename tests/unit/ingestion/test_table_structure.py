"""Unit tests for table structure parsing (Story 2.13).

Tests the TableExtractor class methods for parsing table structures,
headers, column mappings, and data cells.

Coverage target: 80%+ for raglite/ingestion/table_extraction.py
"""

from unittest.mock import Mock

import pytest

from raglite.ingestion.table_extraction import TableExtractor

pytestmark = [pytest.mark.unit]


class TestTableExtractorStructure:
    """Test suite for TableExtractor structure parsing methods."""

    def setup_method(self):
        """Simple setup - create extractor with mock converter."""
        self.mock_converter = Mock()
        self.extractor = TableExtractor(converter=self.mock_converter)

    def test_build_column_mapping_single_header(self):
        """Test column mapping for single-header table."""
        # Arrange - mock column headers for single-header table
        mock_headers = [
            Mock(start_row_offset_idx=0, start_col_offset_idx=0, text="Aug-25 YTD"),
            Mock(start_row_offset_idx=0, start_col_offset_idx=1, text="Sep-25"),
        ]

        # Act
        mapping = self.extractor._build_column_mapping(mock_headers, is_multi_header=False)

        # Assert - verify periods are mapped
        assert len(mapping) == 2
        assert mapping[0] == ("Aug-25 YTD", None)
        assert mapping[1] == ("Sep-25", None)

    def test_build_column_mapping_multi_header(self):
        """Test column mapping for multi-header table."""
        # Arrange - mock multi-header structure
        # Row 0: Metrics (may span multiple columns)
        # Row 1: Entities
        mock_headers = [
            Mock(
                start_row_offset_idx=0,
                start_col_offset_idx=0,
                end_col_offset_idx=2,
                text="Revenue",
            ),
            Mock(start_row_offset_idx=1, start_col_offset_idx=0, text="Portugal"),
            Mock(start_row_offset_idx=1, start_col_offset_idx=1, text="Tunisia"),
        ]

        # Act
        mapping = self.extractor._build_column_mapping(mock_headers, is_multi_header=True)

        # Assert - verify hierarchical mapping
        assert mapping[0] == ("Revenue", "Portugal")
        assert mapping[1] == ("Revenue", "Tunisia")

    def test_build_column_mapping_empty_headers(self):
        """Test column mapping with no headers."""
        # Act
        mapping = self.extractor._build_column_mapping([], is_multi_header=False)

        # Assert
        assert mapping == {}

    def test_build_column_mapping_multi_header_with_span(self):
        """Test multi-header mapping with metric spanning multiple columns."""
        # Arrange - metric "EBITDA" spans columns 0-1, entities in row 1
        mock_headers = [
            # Metric row (spans 2 columns)
            Mock(
                start_row_offset_idx=0,
                start_col_offset_idx=0,
                end_col_offset_idx=2,
                text="EBITDA",
            ),
            # Entity row
            Mock(start_row_offset_idx=1, start_col_offset_idx=0, text="Portugal"),
            Mock(start_row_offset_idx=1, start_col_offset_idx=1, text="Angola"),
        ]

        # Act
        mapping = self.extractor._build_column_mapping(mock_headers, is_multi_header=True)

        # Assert - EBITDA metric applied to both columns
        assert mapping[0] == ("EBITDA", "Portugal")
        assert mapping[1] == ("EBITDA", "Angola")

    def test_build_column_mapping_multi_header_three_levels(self):
        """Test multi-header mapping with 3+ header rows (uses first 2)."""
        # Arrange - mock 3 header rows (should use rows 0 and 1)
        mock_headers = [
            # Row 0: Category (should be metric)
            Mock(
                start_row_offset_idx=0,
                start_col_offset_idx=0,
                end_col_offset_idx=1,
                text="Financial",
            ),
            # Row 1: Metric (should be entity in hierarchical structure)
            Mock(start_row_offset_idx=1, start_col_offset_idx=0, text="EBITDA"),
            # Row 2: Extra level (should be ignored)
            Mock(start_row_offset_idx=2, start_col_offset_idx=0, text="Extra"),
        ]

        # Act
        mapping = self.extractor._build_column_mapping(mock_headers, is_multi_header=True)

        # Assert - uses first 2 rows only
        assert mapping[0] == ("Financial", "EBITDA")

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
