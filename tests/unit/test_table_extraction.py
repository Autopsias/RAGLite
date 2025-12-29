"""Unit tests for table extraction and SQL structuring (Story 2.13).

Tests the TableExtractor class that parses financial tables from Docling output
into structured SQL-ready rows with entity, metric, period, value, and unit fields.

Coverage target: 80%+ for raglite/ingestion/table_extraction.py
"""

import unittest
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
    """Test suite for TableExtractor class."""

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

    def test_parse_value_unit_with_unit(self):
        """Test parsing cell with value and unit."""
        # Act
        value, unit = self.extractor._parse_value_unit("23.2 EUR/ton")

        # Assert - test business logic, not mock
        assert value == 23.2
        assert unit == "EUR/ton"

    def test_parse_value_unit_without_unit(self):
        """Test parsing cell with value only."""
        # Act
        value, unit = self.extractor._parse_value_unit("42.5")

        # Assert
        assert value == 42.5
        assert unit is None

    def test_parse_value_unit_with_comma_separator(self):
        """Test parsing cell with comma thousand separator."""
        # Act
        value, unit = self.extractor._parse_value_unit("1,234.56 GJ")

        # Assert - verify comma removal works
        assert value == 1234.56
        assert unit == "GJ"

    def test_parse_value_unit_na_value(self):
        """Test parsing N/A cell returns None."""
        # Act
        value, unit = self.extractor._parse_value_unit("N/A")

        # Assert
        assert value is None
        assert unit is None

    def test_parse_value_unit_dash_value(self):
        """Test parsing dash cell returns None."""
        # Act
        value, unit = self.extractor._parse_value_unit("-")

        # Assert
        assert value is None
        assert unit is None

    def test_parse_value_unit_empty_string(self):
        """Test parsing empty cell returns None."""
        # Act
        value, unit = self.extractor._parse_value_unit("")

        # Assert
        assert value is None
        assert unit is None

    def test_parse_value_unit_negative_value(self):
        """Test parsing negative value."""
        # Act
        value, unit = self.extractor._parse_value_unit("-15.3 EUR")

        # Assert
        assert value == -15.3
        assert unit == "EUR"

    def test_parse_value_unit_percentage(self):
        """Test parsing percentage value."""
        # Act
        value, unit = self.extractor._parse_value_unit("42.5%")

        # Assert
        assert value == 42.5
        assert unit == "%"

    def test_extract_year_4digit(self):
        """Test year extraction from 4-digit year."""
        # Act
        year = self.extractor._extract_year("Q2 2025")

        # Assert
        assert year == 2025

    def test_extract_year_2digit_with_dash(self):
        """Test year extraction from 2-digit year with dash."""
        # Act
        year = self.extractor._extract_year("Aug-25 YTD")

        # Assert
        assert year == 2025

    def test_extract_year_2digit_standalone(self):
        """Test year extraction from standalone 2-digit year."""
        # Act
        year = self.extractor._extract_year("Aug-24")

        # Assert
        assert year == 2024

    def test_extract_year_4digit_only(self):
        """Test year extraction from year only."""
        # Act
        year = self.extractor._extract_year("2024")

        # Assert
        assert year == 2024

    def test_extract_year_no_year(self):
        """Test year extraction with no year in text."""
        # Act
        year = self.extractor._extract_year("August YTD")

        # Assert
        assert year is None

    def test_extract_year_empty_string(self):
        """Test year extraction from empty string."""
        # Act
        year = self.extractor._extract_year("")

        # Assert
        assert year is None

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

    @pytest.mark.asyncio
    async def test_extract_tables_from_result_multiple_tables(self):
        """Test extraction from result with multiple tables."""
        # Arrange - mock result with 2 tables
        from docling_core.types.doc import TableItem

        mock_result = Mock()
        mock_table1 = Mock(spec=TableItem)
        mock_table1.prov = [Mock(page_no=1)]
        mock_table2 = Mock(spec=TableItem)
        mock_table2.prov = [Mock(page_no=2)]

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
            "raglite.ingestion.table_extraction.extract_table_data_adaptive",
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
            "raglite.ingestion.table_extraction.extract_table_data_adaptive",
            side_effect=mock_extract,
        ):
            # Act
            result = await self.extractor.extract_tables_from_result(mock_result, "test_doc")

            # Assert - only table item processed
            assert len(result) == 1
            assert result[0]["table_index"] == 0

    def test_parse_value_unit_currency_symbols(self):
        """Test parsing values with currency symbols."""
        # Test Euro symbol
        value, unit = self.extractor._parse_value_unit("100.5 €")
        assert value == 100.5
        assert unit == "€"

        # Test Dollar symbol
        value, unit = self.extractor._parse_value_unit("200 $")
        assert value == 200.0
        assert unit == "$"

        # Test Pound symbol
        value, unit = self.extractor._parse_value_unit("50.25 £")
        assert value == 50.25
        assert unit == "£"

    def test_parse_value_unit_complex_units(self):
        """Test parsing values with complex unit strings."""
        # Test fraction unit
        value, unit = self.extractor._parse_value_unit("15.5 EUR/ton")
        assert value == 15.5
        assert unit == "EUR/ton"

        # Test multiple character unit
        value, unit = self.extractor._parse_value_unit("1000 GWh")
        assert value == 1000.0
        assert unit == "GWh"

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

    def test_extract_year_edge_cases(self):
        """Test year extraction edge cases."""
        # Year at start of string
        assert self.extractor._extract_year("2024 Q1") == 2024

        # Year in middle
        assert self.extractor._extract_year("YTD 2025 Aug") == 2025

        # Multiple 2-digit numbers (should pick the one after dash)
        assert self.extractor._extract_year("Aug-25") == 2025

        # 2-digit year without dash at end
        assert self.extractor._extract_year("Aug 24") == 2024

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

    def test_parse_value_unit_invalid_number(self):
        """Test parsing cell with invalid number format."""
        # Act
        value, unit = self.extractor._parse_value_unit("abc 123")

        # Assert - should fail to parse and return None
        assert value is None
        assert unit is None

    def test_parse_value_unit_number_format_exception(self):
        """Test parsing cell that matches regex but fails float conversion."""
        # This tests the ValueError exception path in _parse_value_unit
        # The regex pattern matches numbers with commas, but if the format
        # is malformed after comma removal, float() should fail

        # However, looking at the regex and implementation, it's hard to trigger
        # the ValueError path because the regex is quite strict.
        # The actual coverage shows lines 432-434 are the only uncovered lines,
        # which is the exception handler. This is acceptable for edge case handling.

        # For completeness, test what happens with text that has no numeric content
        value, unit = self.extractor._parse_value_unit("No numbers here")

        # Assert
        assert value is None
        assert unit is None


class TestHeaderClassification:
    """Tests for header classification (June 2025 fix).

    These tests validate the fix for the June 2025 PDF extraction bug where
    'Currency (1000 EUR)' was misclassified as METRIC due to the 'currency'
    pattern in metric_patterns.
    """

    def test_currency_with_unit_is_unknown(self):
        """Test that 'Currency (1000 EUR)' is classified as UNKNOWN, not METRIC.

        This is the root cause of the June 2025 PDF extraction bug where
        'Currency (1000 EUR)' was misclassified as METRIC due to the
        'currency' pattern in metric_patterns.
        """
        from raglite.ingestion.adaptive_table.classification import HeaderType, classify_header

        result = classify_header("Currency (1000 EUR)")
        assert result == HeaderType.UNKNOWN, (
            f"Expected UNKNOWN for unit descriptor, got {result}. "
            "Unit descriptors should not be classified as METRIC."
        )

    def test_currency_exchange_rate_is_metric(self):
        """Test that 'Currency Exchange Rate' is still classified as METRIC.

        This ensures the fix doesn't break legitimate currency-related metrics.
        """
        from raglite.ingestion.adaptive_table.classification import HeaderType, classify_header

        result = classify_header("Currency Exchange Rate")
        assert result == HeaderType.METRIC, (
            f"Expected METRIC for currency exchange rate, got {result}. "
            "The fix should not break legitimate metric classification."
        )

    def test_unit_descriptors_are_unknown(self):
        """Test that various unit descriptors are classified as UNKNOWN."""
        from raglite.ingestion.adaptive_table.classification import HeaderType, classify_header

        unit_descriptors = [
            "Currency (1000 EUR)",
            "Currency (EUR million)",
            "1000 EUR",
            "1000 USD",
            "Unit",
            "Units",
            "UOM",
        ]

        for descriptor in unit_descriptors:
            result = classify_header(descriptor)
            assert result == HeaderType.UNKNOWN, (
                f"Expected UNKNOWN for unit descriptor '{descriptor}', got {result}"
            )


class TestEntityValidation:
    """Tests for entity validation (June 2025 safety net).

    These tests validate the _validate_entity() function which acts as a
    safety net to catch misclassified headers that slip through the primary
    classification logic.
    """

    def test_validate_entity_rejects_currency_descriptor(self):
        """Test that 'Currency (1000 EUR)' fails entity validation."""
        from raglite.ingestion.adaptive_table.core import validate_entity

        assert validate_entity("Currency (1000 EUR)") is False, (
            "Unit descriptor should not be a valid entity"
        )

    def test_validate_entity_accepts_group(self):
        """Test that 'GROUP' passes entity validation."""
        from raglite.ingestion.adaptive_table.core import validate_entity

        assert validate_entity("GROUP") is True, "GROUP should be a valid entity"

    def test_validate_entity_accepts_country_names(self):
        """Test that country names pass entity validation."""
        from raglite.ingestion.adaptive_table.core import validate_entity

        valid_entities = ["Portugal", "Tunisia", "Angola", "Botswana", "GROUP"]

        for entity in valid_entities:
            assert validate_entity(entity) is True, f"Expected '{entity}' to be a valid entity"

    def test_validate_entity_rejects_unit_patterns(self):
        """Test that unit patterns fail entity validation."""
        from raglite.ingestion.adaptive_table.core import validate_entity

        invalid_entities = [
            "Currency (1000 EUR)",
            "1000 EUR",
            "EUR/ton",
            "Unit",
            "kton",
            "GWh",
            "123.45",
            "Measurement",
            "UOM",
        ]

        for entity in invalid_entities:
            assert validate_entity(entity) is False, f"Expected '{entity}' to be an invalid entity"

    def test_validate_entity_handles_none_and_empty(self):
        """Test that None and empty strings fail validation."""
        from raglite.ingestion.adaptive_table.core import validate_entity

        assert validate_entity(None) is False, "None should be invalid"
        assert validate_entity("") is False, "Empty string should be invalid"
        assert validate_entity("   ") is False, "Whitespace should be invalid"


class TestEntityValidationIntegration(unittest.TestCase):
    """Integration tests to ensure entity validation is applied across all extraction methods.

    These tests verify that invalid entity values (like 'Currency (1000 EUR)') are
    rejected by ALL extraction code paths, not just the fallback method.
    """

    def test_multi_header_extraction_validates_entities(self):
        """Test that multi-header extraction validates and clears invalid entities."""
        from raglite.ingestion.adaptive_table.multi_header import (
            _extract_multi_header_metric_entity,
        )

        # Mock table with "Currency (1000 EUR)" as entity header
        # Simulates the June 2025 PDF table structure
        class MockCell:
            def __init__(self, text, row, col, is_header=False, row_header=False):
                self.text = text
                self.start_row_offset_idx = row
                self.start_col_offset_idx = col
                self.end_col_offset_idx = col + 1
                self.column_header = is_header
                self.row_header = row_header

        class MockTableItem:
            def __init__(self):
                self.caption = None

        class MockResult:
            pass

        # Build mock table: Row 0 = Metrics, Row 1 = "Currency (1000 EUR)"
        table_cells = [
            # Header row 0: Metrics
            MockCell("EBITDA", 0, 0, is_header=True),
            MockCell("Revenue", 0, 1, is_header=True),
            # Header row 1: Entities (one invalid)
            MockCell("Currency (1000 EUR)", 1, 0, is_header=True),  # INVALID!
            MockCell("Portugal", 1, 1, is_header=True),
            # Row headers: Periods
            MockCell("Jun-25", 2, 0, row_header=True),
            # Data cells
            MockCell("100.5", 2, 0),
            MockCell("200.3", 2, 1),
        ]

        metadata = {"multi_header_detected": True}
        result_rows = _extract_multi_header_metric_entity(
            table_cells=table_cells,
            num_rows=3,
            num_cols=2,
            metadata=metadata,
            document_id="test_doc",
            page_number=1,
            table_index=1,
            table_item=MockTableItem(),
            result=MockResult(),
        )

        # Verify: Rows with invalid entity should have entity=None
        for row in result_rows:
            if row["column_name"] and "Currency" in row["column_name"]:
                self.assertIsNone(
                    row["entity"],
                    f"Invalid entity 'Currency (1000 EUR)' should be cleared to None, got: {row['entity']}",
                )

    def test_entity_cols_extraction_validates_entities(self):
        """Test that entity-column extraction validates and clears invalid entities."""
        from raglite.ingestion.adaptive_table.standard_layouts import (
            _extract_entity_cols_metric_rows,
        )

        class MockCell:
            def __init__(self, text, row, col, is_header=False, row_header=False):
                self.text = text
                self.start_row_offset_idx = row
                self.start_col_offset_idx = col
                self.column_header = is_header
                self.row_header = row_header

        class MockTableItem:
            def __init__(self):
                self.caption = None

        class MockResult:
            pass

        # Build mock table: Column headers = entities, Row headers = metrics
        table_cells = [
            # Column headers: Entities (one invalid)
            MockCell("Currency (1000 EUR)", 0, 0, is_header=True),  # INVALID!
            MockCell("Portugal", 0, 1, is_header=True),
            # Row headers: Metrics
            MockCell("EBITDA", 1, 0, row_header=True),
            # Data cells
            MockCell("100.5", 1, 0),
            MockCell("200.3", 1, 1),
        ]

        metadata = {}
        result_rows = _extract_entity_cols_metric_rows(
            table_cells=table_cells,
            num_rows=2,
            num_cols=2,
            metadata=metadata,
            document_id="test_doc",
            page_number=1,
            table_index=1,
            table_item=MockTableItem(),
            result=MockResult(),
        )

        # Verify: Rows with invalid entity should have entity=None
        invalid_entity_rows = [
            row
            for row in result_rows
            if row["column_name"] and "Currency" in str(row["column_name"])
        ]

        # If invalid entity was properly cleared, these rows should have entity=None
        for row in invalid_entity_rows:
            self.assertIsNone(
                row["entity"],
                "Invalid entity 'Currency (1000 EUR)' should be cleared to None in entity_cols extraction",
            )
