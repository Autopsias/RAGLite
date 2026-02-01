"""Unit tests for table period and year extraction (Story 2.13).

Tests the TableExtractor class methods for extracting fiscal years,
periods, and row periods from table data.

Coverage target: 80%+ for raglite/ingestion/table_extraction.py
"""

from unittest.mock import Mock

import pytest

from raglite.ingestion.table_extraction import TableExtractor

pytestmark = [pytest.mark.unit]


class TestTableExtractorPeriodExtraction:
    """Test suite for TableExtractor period and year extraction methods."""

    def setup_method(self):
        """Simple setup - create extractor with mock converter."""
        self.mock_converter = Mock()
        self.extractor = TableExtractor(converter=self.mock_converter)

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
