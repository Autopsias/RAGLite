"""Tests for entity validation (June 2025 safety net).

These tests validate the _validate_entity() function which acts as a
safety net to catch misclassified headers that slip through the primary
classification logic.
"""

import unittest


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
