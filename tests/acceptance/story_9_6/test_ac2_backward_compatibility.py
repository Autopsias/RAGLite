"""ATDD tests for Story 9.6 AC2 - Backward Compatibility for Rows Without Classification.

TDD RED Phase: All tests MUST fail initially because the storage module
has not been updated to handle rows without classification fields gracefully.

Test IDs follow pattern: TEST-AC-9.6.2.{test}

BDD Acceptance Criteria:
Given existing code paths may produce rows without classification fields
When store_tables_in_postgresql() receives a row without period_type, value_type, or entity_level
Then NULL is inserted for missing classification fields (columns are nullable)
And existing rows (without classification) are stored successfully
And no errors are raised for missing classification fields
And backward compatibility is maintained for pre-Epic-9 code paths
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
]


class TestAC2BackwardCompatibilityWithoutClassification:
    """AC2: Backward Compatibility for Rows Without Classification.

    Given existing code paths may produce rows without classification fields
    When store_tables_in_postgresql() receives a row without classification
    Then NULL is inserted for missing fields and no errors occur
    """

    def test_ac_2_1_1_row_without_classification_stores_successfully(self) -> None:
        """TEST-AC-9.6.2.1 [P0]: Row without classification fields stores successfully.

        Given a row dict without any classification fields
        When _prepare_table_records() processes the row
        Then the record is created without errors and has 16 fields
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row without classification fields (pre-Epic-9 format)
        rows = [
            {
                "document_id": "test-doc-legacy-001",
                "entity": "Portugal Cement",
                "metric": "Revenue",
                "period": "Dec-24",
                "fiscal_year": 2024,
                "value": 100.0,
                "unit": "EUR millions",
            }
        ]

        # Act: Prepare records for insertion (should not raise)
        records, skipped = _prepare_table_records(rows)

        # Assert: Record created successfully with 16 fields
        # RED STATE: Current implementation creates 13-field tuples
        assert len(records) == 1
        assert len(records[0]) == 16

    def test_ac_2_1_2_missing_period_type_becomes_null(self) -> None:
        """TEST-AC-9.6.2.2 [P0]: Missing period_type becomes NULL.

        Given a row without period_type field
        When _prepare_table_records() processes the row
        Then the period_type position in the record tuple is None
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row without period_type
        rows = [
            {
                "document_id": "test-doc-legacy-002",
                "entity": "SECIL",
                "metric": "EBITDA",
                "period": "Jan-24",
                "fiscal_year": 2024,
                "value": 50.0,
                "value_type": "actual",  # Has value_type but not period_type
                "entity_level": "consolidated",
            }
        ]

        # Act: Prepare records
        records, skipped = _prepare_table_records(rows)

        # Assert: period_type position is None
        # RED STATE: Tuple doesn't have position 13 (only 13 elements 0-12)
        record = records[0]
        assert record[13] is None  # period_type at position 13

    def test_ac_2_1_3_missing_value_type_becomes_null(self) -> None:
        """TEST-AC-9.6.2.3 [P0]: Missing value_type becomes NULL.

        Given a row without value_type field
        When _prepare_table_records() processes the row
        Then the value_type position in the record tuple is None
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row without value_type
        rows = [
            {
                "document_id": "test-doc-legacy-003",
                "entity": "GROUP",
                "metric": "Revenue",
                "period": "Dec-24",
                "fiscal_year": 2024,
                "value": 500.0,
                "period_type": "monthly_actual",  # Has period_type but not value_type
                "entity_level": "consolidated",
            }
        ]

        # Act: Prepare records
        records, skipped = _prepare_table_records(rows)

        # Assert: value_type position is None
        # RED STATE: Tuple doesn't have position 14
        record = records[0]
        assert record[14] is None  # value_type at position 14

    def test_ac_2_1_4_missing_entity_level_becomes_null(self) -> None:
        """TEST-AC-9.6.2.4 [P0]: Missing entity_level becomes NULL.

        Given a row without entity_level field
        When _prepare_table_records() processes the row
        Then the entity_level position in the record tuple is None
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row without entity_level
        rows = [
            {
                "document_id": "test-doc-legacy-004",
                "entity": "Spain Division",
                "metric": "Costs",
                "period": "Budget 2025",
                "fiscal_year": 2025,
                "value": 120.0,
                "period_type": "budget",  # Has period_type but not entity_level
                "value_type": "budget",
            }
        ]

        # Act: Prepare records
        records, skipped = _prepare_table_records(rows)

        # Assert: entity_level position is None
        # RED STATE: Tuple doesn't have position 15
        record = records[0]
        assert record[15] is None  # entity_level at position 15

    def test_ac_2_1_5_all_classification_missing_becomes_three_nulls(self) -> None:
        """TEST-AC-9.6.2.5 [P0]: All classification missing becomes three NULLs.

        Given a row without any classification fields
        When _prepare_table_records() processes the row
        Then positions 13, 14, 15 are all None
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row without any classification fields
        rows = [
            {
                "document_id": "test-doc-legacy-005",
                "entity": "Portugal",
                "metric": "Sales",
                "period": "Dec-24",
                "fiscal_year": 2024,
                "value": 100.0,
            }
        ]

        # Act: Prepare records
        records, skipped = _prepare_table_records(rows)

        # Assert: All classification positions are None
        # RED STATE: Tuple only has 13 elements
        record = records[0]
        assert record[13] is None  # period_type
        assert record[14] is None  # value_type
        assert record[15] is None  # entity_level

    def test_ac_2_1_6_mixed_rows_some_with_classification(self) -> None:
        """TEST-AC-9.6.2.6 [P0]: Mixed rows with and without classification.

        Given a list with some rows having classification and some without
        When _prepare_table_records() processes all rows
        Then all rows are processed correctly with 16-field tuples
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Mixed rows
        rows = [
            # Row with classification
            {
                "document_id": "test-doc-mixed-001",
                "entity": "Portugal",
                "metric": "Sales",
                "period": "Dec-24",
                "value": 100.0,
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "geographic",
            },
            # Row without classification (legacy)
            {
                "document_id": "test-doc-mixed-002",
                "entity": "Spain",
                "metric": "Sales",
                "period": "Dec-24",
                "value": 150.0,
            },
            # Row with partial classification
            {
                "document_id": "test-doc-mixed-003",
                "entity": "GROUP",
                "metric": "Total",
                "period": "YTD Dec-24",
                "value": 250.0,
                "period_type": "ytd_actual",
            },
        ]

        # Act: Prepare records
        records, skipped = _prepare_table_records(rows)

        # Assert: All rows processed with 16 fields
        # RED STATE: Current implementation returns 13-field tuples
        assert len(records) == 3

        # First row: full classification
        assert records[0][13] == "monthly_actual"
        assert records[0][14] == "actual"
        assert records[0][15] == "geographic"

        # Second row: no classification
        assert records[1][13] is None
        assert records[1][14] is None
        assert records[1][15] is None

        # Third row: partial classification
        assert records[2][13] == "ytd_actual"
        assert records[2][14] is None  # Missing
        assert records[2][15] is None  # Missing

    def test_ac_2_1_7_empty_string_classification_preserved(self) -> None:
        """TEST-AC-9.6.2.7 [P1]: Empty string classification preserved.

        Given a row with empty string classification field
        When _prepare_table_records() processes the row
        Then empty string is preserved (not converted to NULL)
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row with empty string classification
        rows = [
            {
                "document_id": "test-doc-empty-001",
                "entity": "Unknown Entity",
                "metric": "Unknown Metric",
                "period": "Unknown",
                "value": 0.0,
                "period_type": "",  # Empty string
                "value_type": "",
                "entity_level": "",
            }
        ]

        # Act: Prepare records
        records, skipped = _prepare_table_records(rows)

        # Assert: Empty strings are preserved (or converted to None - implementation choice)
        # RED STATE: Tuple doesn't have these positions
        record = records[0]
        # Accept either empty string or None for empty values
        assert record[13] in ("", None)
        assert record[14] in ("", None)
        assert record[15] in ("", None)

    def test_ac_2_1_8_no_error_on_legacy_row_format(self) -> None:
        """TEST-AC-9.6.2.8 [P0]: No error on legacy row format.

        Given a row in the legacy format (pre-Epic-9) without any new fields
        When _prepare_table_records() processes the row
        Then no exception is raised and record has 16 fields
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Complete legacy row format
        rows = [
            {
                "document_id": "test-doc-legacy-complete",
                "page_number": 10,
                "table_index": 2,
                "table_caption": "Revenue Table",
                "entity": "Portugal",
                "metric": "Sales",
                "period": "Dec-24",
                "fiscal_year": 2024,
                "value": 100.0,
                "unit": "EUR",
                "row_index": 5,
                "column_name": "December",
                "chunk_text": "Portugal Sales December 2024: 100 EUR",
                # No classification fields
            }
        ]

        # Act & Assert: No exception raised
        records, skipped = _prepare_table_records(rows)

        # RED STATE: Current implementation returns 13-field tuple
        assert len(records) == 1
        assert len(records[0]) == 16
