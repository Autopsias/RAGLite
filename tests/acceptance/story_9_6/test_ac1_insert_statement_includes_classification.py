"""ATDD tests for Story 9.6 AC1 - Classification Fields Included in INSERT Statement.

TDD RED Phase: All tests MUST fail initially because the storage module
has not been updated to include classification fields in INSERT statements.

Test IDs follow pattern: TEST-AC-9.6.1.{test}

BDD Acceptance Criteria:
Given the financial_tables table has classification columns (Story 9.1):
  - period_type VARCHAR(50)
  - value_type VARCHAR(50)
  - entity_level VARCHAR(100)
When store_tables_in_postgresql() receives rows with classification fields from Story 9.5
Then the INSERT statement includes all three classification columns
And classification values are extracted from row dict keys:
  - row.get("period_type") -> period_type column
  - row.get("value_type") -> value_type column
  - row.get("entity_level") -> entity_level column
And the column order in INSERT matches the VALUES tuple order
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
]


class TestAC1InsertStatementIncludesClassification:
    """AC1: Classification Fields Included in INSERT Statement.

    Given the financial_tables table has classification columns
    When store_tables_in_postgresql() receives rows with classification fields
    Then the INSERT statement includes all three classification columns
    """

    def test_ac_1_1_1_storage_module_can_be_imported(self) -> None:
        """TEST-AC-9.6.1.1 [P0]: Storage module can be imported.

        Given the storage package exists
        When we import the table_store module
        Then the import succeeds without errors
        """
        # Arrange: Storage package exists
        # Act: Import the storage module
        from raglite.ingestion.storage import table_store

        # Assert: Module is importable
        assert table_store is not None

    def test_ac_1_1_2_store_tables_function_exists(self) -> None:
        """TEST-AC-9.6.1.2 [P0]: store_tables_in_postgresql function exists.

        Given the table_store module exists
        When we import store_tables_in_postgresql
        Then it is a callable function
        """
        # Arrange/Act: Import the function
        from raglite.ingestion.storage.table_store import store_tables_in_postgresql

        # Assert: Function is callable
        assert callable(store_tables_in_postgresql)

    def test_ac_1_1_3_row_with_classification_stores_period_type(self) -> None:
        """TEST-AC-9.6.1.3 [P0]: Row with classification stores period_type.

        Given a row dict with period_type field
        When _prepare_table_records() processes the row
        Then the period_type value is stored in the database
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row with classification field (document_id in row dict)
        rows = [
            {
                "document_id": "test-doc-123",
                "entity": "Portugal Cement",
                "metric": "Revenue",
                "period": "Dec-24",
                "fiscal_year": 2024,
                "value": 100.0,
                "unit": "EUR millions",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            }
        ]

        # Act: Prepare records for insertion
        records, skipped = _prepare_table_records(rows)

        # Assert: Record tuple contains period_type
        assert len(records) == 1
        record = records[0]
        # RED STATE: Current implementation has 13 fields, should have 16
        # This assertion will FAIL because period_type is not in the tuple
        assert "monthly_actual" in record

    def test_ac_1_1_4_row_with_classification_stores_value_type(self) -> None:
        """TEST-AC-9.6.1.4 [P0]: Row with classification stores value_type.

        Given a row dict with value_type field
        When _prepare_table_records() processes the row
        Then the value_type value is stored in the database
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row with classification field
        rows = [
            {
                "document_id": "test-doc-456",
                "entity": "SECIL SA",
                "metric": "EBITDA",
                "period": "Jan-24",
                "fiscal_year": 2024,
                "value": 50.0,
                "unit": "EUR millions",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "consolidated",
            }
        ]

        # Act: Prepare records for insertion
        records, skipped = _prepare_table_records(rows)

        # Assert: Record tuple contains value_type
        assert len(records) == 1
        record = records[0]
        # Check value_type "actual" is in the record (at position 14 after implementation)
        # RED STATE: This will fail because value_type is not in current tuple
        assert record[14] == "actual"

    def test_ac_1_1_5_row_with_classification_stores_entity_level(self) -> None:
        """TEST-AC-9.6.1.5 [P0]: Row with classification stores entity_level.

        Given a row dict with entity_level field
        When _prepare_table_records() processes the row
        Then the entity_level value is stored in the database
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row with classification field
        rows = [
            {
                "document_id": "test-doc-789",
                "entity": "GROUP",
                "metric": "Total Revenue",
                "period": "YTD Dec-24",
                "fiscal_year": 2024,
                "value": 500.0,
                "unit": "EUR millions",
                "period_type": "ytd_actual",
                "value_type": "actual",
                "entity_level": "consolidated",
            }
        ]

        # Act: Prepare records for insertion
        records, skipped = _prepare_table_records(rows)

        # Assert: Record tuple contains entity_level (at position 15 after implementation)
        assert len(records) == 1
        record = records[0]
        # RED STATE: This will fail because entity_level is not in current tuple
        assert record[15] == "consolidated"

    def test_ac_1_1_6_all_three_classification_fields_in_record(self) -> None:
        """TEST-AC-9.6.1.6 [P0]: All three classification fields in record tuple.

        Given a row with all three classification fields
        When _prepare_table_records() processes the row
        Then the record tuple contains period_type, value_type, entity_level
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row with all classification fields
        rows = [
            {
                "document_id": "test-doc-abc",
                "entity": "Spain Division",
                "metric": "Operating Costs",
                "period": "Budget 2025",
                "fiscal_year": 2025,
                "value": 120.0,
                "unit": "EUR millions",
                "period_type": "budget",
                "value_type": "budget",
                "entity_level": "geographic",
            }
        ]

        # Act: Prepare records for insertion
        records, skipped = _prepare_table_records(rows)

        # Assert: Record tuple contains all three classification fields
        assert len(records) == 1
        record = records[0]
        # RED STATE: Tuple has 13 fields, these indices don't exist yet
        assert record[13] == "budget"  # period_type
        assert record[14] == "budget"  # value_type
        assert record[15] == "geographic"  # entity_level

    def test_ac_1_1_7_record_tuple_has_16_fields(self) -> None:
        """TEST-AC-9.6.1.7 [P0]: Record tuple has 16 fields (13 original + 3 classification).

        Given a row with classification fields
        When _prepare_table_records() processes the row
        Then the record tuple has 16 fields
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Complete row
        rows = [
            {
                "document_id": "test-doc-def",
                "page_number": 5,
                "table_index": 0,
                "table_caption": "Revenue Summary",
                "entity": "Portugal",
                "metric": "Sales",
                "period": "Dec-24",
                "fiscal_year": 2024,
                "value": 100.0,
                "unit": "EUR",
                "row_index": 1,
                "column_name": "Dec",
                "chunk_text": "Portugal Sales Dec-24: 100 EUR",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "geographic",
            }
        ]

        # Act: Prepare records for insertion
        records, skipped = _prepare_table_records(rows)

        # Assert: Record tuple has 16 fields
        # RED STATE: Current implementation returns 13 fields
        assert len(records) == 1
        record = records[0]
        assert len(record) == 16

    def test_ac_1_1_8_classification_fields_at_end_of_tuple(self) -> None:
        """TEST-AC-9.6.1.8 [P1]: Classification fields are at end of tuple.

        Given a row with classification fields
        When _prepare_table_records() processes the row
        Then classification fields are at positions 13, 14, 15 (0-indexed)
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Complete row
        rows = [
            {
                "document_id": "test-doc-ghi",
                "page_number": 5,
                "table_index": 0,
                "table_caption": "Revenue Summary",
                "entity": "Portugal",
                "metric": "Sales",
                "period": "Dec-24",
                "fiscal_year": 2024,
                "value": 100.0,
                "unit": "EUR",
                "row_index": 1,
                "column_name": "Dec",
                "chunk_text": "Portugal Sales Dec-24: 100 EUR",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "geographic",
            }
        ]

        # Act: Prepare records for insertion
        records, skipped = _prepare_table_records(rows)

        # Assert: Classification fields at expected positions
        # RED STATE: Tuple only has 13 elements, indices 13-15 don't exist
        record = records[0]
        assert record[13] == "monthly_actual"  # period_type
        assert record[14] == "actual"  # value_type
        assert record[15] == "geographic"  # entity_level
