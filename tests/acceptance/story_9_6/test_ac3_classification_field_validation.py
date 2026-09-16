"""ATDD tests for Story 9.6 AC3 - Classification Field Validation.

TDD RED Phase: All tests MUST fail initially because the storage module
has not been updated to handle classification field values correctly.

Test IDs follow pattern: TEST-AC-9.6.3.{test}

BDD Acceptance Criteria:
Given classification fields use enum string values:
  - period_type: "monthly_actual", "ytd_actual", "budget", "ytd_budget", "unknown"
  - value_type: "actual", "budget", "forecast", "variance", "unknown"
  - entity_level: "consolidated", "company_only", "segment", "geographic", "unknown"
When a row is stored with classification fields
Then string values are stored exactly as provided (no transformation)
And VARCHAR column size accommodates all enum values (50/50/100 chars)
And storage does NOT validate enum membership (classifiers handle validation)
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
]


class TestAC3ClassificationFieldValidation:
    """AC3: Classification Field Validation.

    Given classification fields use enum string values
    When a row is stored with classification fields
    Then string values are stored exactly as provided
    """

    def test_ac_3_1_1_period_type_monthly_actual_stored(self) -> None:
        """TEST-AC-9.6.3.1 [P0]: period_type monthly_actual stored correctly.

        Given a row with period_type = "monthly_actual"
        When _prepare_table_records() processes the row
        Then "monthly_actual" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-period-001",
                "entity": "Portugal",
                "metric": "Sales",
                "period": "Dec-24",
                "period_type": "monthly_actual",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert: period_type at position 13
        # RED STATE: Tuple doesn't have position 13
        assert records[0][13] == "monthly_actual"

    def test_ac_3_1_2_period_type_ytd_actual_stored(self) -> None:
        """TEST-AC-9.6.3.2 [P0]: period_type ytd_actual stored correctly.

        Given a row with period_type = "ytd_actual"
        When _prepare_table_records() processes the row
        Then "ytd_actual" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-period-002",
                "entity": "GROUP",
                "metric": "Revenue",
                "period": "YTD Dec-24",
                "period_type": "ytd_actual",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][13] == "ytd_actual"

    def test_ac_3_1_3_period_type_budget_stored(self) -> None:
        """TEST-AC-9.6.3.3 [P0]: period_type budget stored correctly.

        Given a row with period_type = "budget"
        When _prepare_table_records() processes the row
        Then "budget" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-period-003",
                "entity": "Portugal",
                "metric": "Sales",
                "period": "Budget 2025",
                "period_type": "budget",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][13] == "budget"

    def test_ac_3_1_4_period_type_ytd_budget_stored(self) -> None:
        """TEST-AC-9.6.3.4 [P0]: period_type ytd_budget stored correctly.

        Given a row with period_type = "ytd_budget"
        When _prepare_table_records() processes the row
        Then "ytd_budget" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-period-004",
                "entity": "GROUP",
                "metric": "Revenue",
                "period": "YTD Budget 2025",
                "period_type": "ytd_budget",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][13] == "ytd_budget"

    def test_ac_3_1_5_period_type_unknown_stored(self) -> None:
        """TEST-AC-9.6.3.5 [P0]: period_type unknown stored correctly.

        Given a row with period_type = "unknown"
        When _prepare_table_records() processes the row
        Then "unknown" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-period-005",
                "entity": "Unknown",
                "metric": "Unknown",
                "period": "???",
                "period_type": "unknown",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][13] == "unknown"

    def test_ac_3_1_6_value_type_actual_stored(self) -> None:
        """TEST-AC-9.6.3.6 [P0]: value_type actual stored correctly.

        Given a row with value_type = "actual"
        When _prepare_table_records() processes the row
        Then "actual" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-value-001",
                "entity": "Portugal",
                "metric": "Sales",
                "period": "Dec-24",
                "value_type": "actual",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert: value_type at position 14
        assert records[0][14] == "actual"

    def test_ac_3_1_7_value_type_budget_stored(self) -> None:
        """TEST-AC-9.6.3.7 [P0]: value_type budget stored correctly.

        Given a row with value_type = "budget"
        When _prepare_table_records() processes the row
        Then "budget" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-value-002",
                "entity": "Portugal",
                "metric": "Sales",
                "period": "Budget 2025",
                "value_type": "budget",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][14] == "budget"

    def test_ac_3_1_8_value_type_forecast_stored(self) -> None:
        """TEST-AC-9.6.3.8 [P0]: value_type forecast stored correctly.

        Given a row with value_type = "forecast"
        When _prepare_table_records() processes the row
        Then "forecast" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-value-003",
                "entity": "Portugal",
                "metric": "Sales",
                "period": "Forecast Q1 2025",
                "value_type": "forecast",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][14] == "forecast"

    def test_ac_3_1_9_value_type_variance_stored(self) -> None:
        """TEST-AC-9.6.3.9 [P0]: value_type variance stored correctly.

        Given a row with value_type = "variance"
        When _prepare_table_records() processes the row
        Then "variance" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-value-004",
                "entity": "Portugal",
                "metric": "Sales Variance",
                "period": "Dec-24",
                "value_type": "variance",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][14] == "variance"

    def test_ac_3_1_10_value_type_unknown_stored(self) -> None:
        """TEST-AC-9.6.3.10 [P0]: value_type unknown stored correctly.

        Given a row with value_type = "unknown"
        When _prepare_table_records() processes the row
        Then "unknown" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-value-005",
                "entity": "Unknown",
                "metric": "Unknown",
                "period": "???",
                "value_type": "unknown",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][14] == "unknown"

    def test_ac_3_1_11_entity_level_consolidated_stored(self) -> None:
        """TEST-AC-9.6.3.11 [P0]: entity_level consolidated stored correctly.

        Given a row with entity_level = "consolidated"
        When _prepare_table_records() processes the row
        Then "consolidated" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-entity-001",
                "entity": "GROUP",
                "metric": "Total Revenue",
                "period": "Dec-24",
                "entity_level": "consolidated",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert: entity_level at position 15
        assert records[0][15] == "consolidated"

    def test_ac_3_1_12_entity_level_company_only_stored(self) -> None:
        """TEST-AC-9.6.3.12 [P0]: entity_level company_only stored correctly.

        Given a row with entity_level = "company_only"
        When _prepare_table_records() processes the row
        Then "company_only" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-entity-002",
                "entity": "SECIL SA",
                "metric": "Revenue",
                "period": "Dec-24",
                "entity_level": "company_only",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][15] == "company_only"

    def test_ac_3_1_13_entity_level_segment_stored(self) -> None:
        """TEST-AC-9.6.3.13 [P0]: entity_level segment stored correctly.

        Given a row with entity_level = "segment"
        When _prepare_table_records() processes the row
        Then "segment" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-entity-003",
                "entity": "Cement Division",
                "metric": "Revenue",
                "period": "Dec-24",
                "entity_level": "segment",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][15] == "segment"

    def test_ac_3_1_14_entity_level_geographic_stored(self) -> None:
        """TEST-AC-9.6.3.14 [P0]: entity_level geographic stored correctly.

        Given a row with entity_level = "geographic"
        When _prepare_table_records() processes the row
        Then "geographic" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-entity-004",
                "entity": "Portugal",
                "metric": "Revenue",
                "period": "Dec-24",
                "entity_level": "geographic",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][15] == "geographic"

    def test_ac_3_1_15_entity_level_unknown_stored(self) -> None:
        """TEST-AC-9.6.3.15 [P0]: entity_level unknown stored correctly.

        Given a row with entity_level = "unknown"
        When _prepare_table_records() processes the row
        Then "unknown" is in the record tuple unchanged
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange
        rows = [
            {
                "document_id": "test-doc-entity-005",
                "entity": "Unknown Entity",
                "metric": "Unknown",
                "period": "???",
                "entity_level": "unknown",
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert
        assert records[0][15] == "unknown"

    def test_ac_3_1_16_storage_does_not_validate_enum_values(self) -> None:
        """TEST-AC-9.6.3.16 [P1]: Storage does NOT validate enum membership.

        Given a row with non-standard classification values
        When _prepare_table_records() processes the row
        Then the values are stored without validation errors
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row with non-standard values (classifiers handle validation)
        rows = [
            {
                "document_id": "test-doc-custom",
                "entity": "Test",
                "metric": "Test",
                "period": "Test",
                "period_type": "custom_period_type",  # Not in enum
                "value_type": "custom_value_type",  # Not in enum
                "entity_level": "custom_entity_level",  # Not in enum
            }
        ]

        # Act & Assert: Should not raise (storage doesn't validate)
        records, skipped = _prepare_table_records(rows)

        # RED STATE: These positions don't exist in current tuple
        assert records[0][13] == "custom_period_type"
        assert records[0][14] == "custom_value_type"
        assert records[0][15] == "custom_entity_level"

    def test_ac_3_1_17_values_stored_case_sensitive(self) -> None:
        """TEST-AC-9.6.3.17 [P1]: Classification values are stored case-sensitive.

        Given classification values in various cases
        When _prepare_table_records() processes the row
        Then values are stored exactly as provided (case-sensitive)
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Arrange: Row with mixed case values
        rows = [
            {
                "document_id": "test-doc-case",
                "entity": "Test",
                "metric": "Test",
                "period": "Test",
                "period_type": "Monthly_Actual",  # Mixed case
                "value_type": "ACTUAL",  # Upper case
                "entity_level": "Consolidated",  # Title case
            }
        ]

        # Act
        records, skipped = _prepare_table_records(rows)

        # Assert: Values preserved exactly
        # RED STATE: These positions don't exist
        assert records[0][13] == "Monthly_Actual"
        assert records[0][14] == "ACTUAL"
        assert records[0][15] == "Consolidated"
