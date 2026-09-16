"""Column mapping tests for TableExtractor.

Tests the _build_column_mapping and _get_row_period methods which construct
column metadata from table headers for both single-header and multi-header tables.
"""

from unittest.mock import Mock

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
    """Test suite for column mapping functionality."""

    def setup_method(self):
        """Simple setup - create extractor with mock converter."""
        TableExtractor = _get_table_extractor()
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

    def test_get_row_period_found(self):
        """Test period extraction when row header exists."""
        # Arrange
        mock_row_headers = [
            Mock(start_row_offset_idx=0, text="Jan-25"),
            Mock(start_row_offset_idx=1, text="Feb-25"),
        ]

        # Act
        period = self.extractor._get_row_period(mock_row_headers, row_idx=1)

        # Assert
        assert period == "Feb-25"

    def test_get_row_period_not_found(self):
        """Test period extraction when row header doesn't exist."""
        # Arrange
        mock_row_headers = [
            Mock(start_row_offset_idx=0, text="Jan-25"),
        ]

        # Act
        period = self.extractor._get_row_period(mock_row_headers, row_idx=5)

        # Assert
        assert period is None

    def test_get_row_period_empty_headers(self):
        """Test period extraction with no row headers."""
        # Act
        period = self.extractor._get_row_period([], row_idx=0)

        # Assert
        assert period is None
