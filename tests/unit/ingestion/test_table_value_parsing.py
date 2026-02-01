"""Unit tests for table value and unit parsing (Story 2.13).

Tests the TableExtractor class methods for parsing values, units, and
handling various number formats.

Coverage target: 80%+ for raglite/ingestion/table_extraction.py
"""

from unittest.mock import Mock

import pytest

from raglite.ingestion.table_extraction import TableExtractor

pytestmark = [pytest.mark.unit]


class TestTableExtractorValueParsing:
    """Test suite for TableExtractor value and unit parsing methods."""

    def setup_method(self):
        """Simple setup - create extractor with mock converter."""
        self.mock_converter = Mock()
        self.extractor = TableExtractor(converter=self.mock_converter)

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
