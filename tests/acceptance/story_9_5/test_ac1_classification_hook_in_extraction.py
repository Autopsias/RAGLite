"""ATDD tests for Story 9.5 AC1 - Classification Hook in Extraction Pipeline.

TDD RED Phase: All tests MUST fail initially because the integration module
does not exist yet at raglite/ingestion/classification/integration.py.

Test IDs follow pattern: TEST-AC-9.5.1.{test}

BDD Acceptance Criteria:
Given the table extraction produces raw rows with entity, metric, period fields
When extract_table_data_adaptive() completes extraction
Then each row is automatically enriched with classification fields:
  - period_type: from classify_period()
  - value_type: from classify_value_type()
  - entity_level: from classify_entity_level()
And classification runs synchronously after row extraction (before unit inference)
And classification adds <20% overhead to extraction time (per Epic 9 AC4)
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
]


class TestAC1ClassificationHookInExtractionPipeline:
    """AC1: Classification Hook in Extraction Pipeline.

    Given the table extraction produces raw rows with entity, metric, period fields
    When extract_table_data_adaptive() completes extraction
    Then each row is automatically enriched with classification fields
    And classification runs synchronously after row extraction
    """

    def test_ac_1_1_1_integration_module_can_be_imported(self) -> None:
        """TEST-AC-9.5.1.1 [P0]: Integration module can be imported.

        Given the classification package exists
        When we import the integration module
        Then the import succeeds without errors
        """
        # Arrange: Classification package exists
        # Act: Import the integration module
        from raglite.ingestion.classification import integration

        # Assert: Module is importable
        assert integration is not None

    def test_ac_1_1_2_classify_row_function_exported(self) -> None:
        """TEST-AC-9.5.1.2 [P0]: classify_row function is exported from integration.

        Given the integration module exists
        When we import classify_row
        Then it is a callable function
        """
        # Arrange/Act: Import the function
        from raglite.ingestion.classification.integration import classify_row

        # Assert: Function is callable
        assert callable(classify_row)

    def test_ac_1_1_3_classify_rows_batch_function_exported(self) -> None:
        """TEST-AC-9.5.1.3 [P0]: classify_rows_batch function is exported.

        Given the integration module exists
        When we import classify_rows_batch
        Then it is a callable function
        """
        # Arrange/Act: Import the function
        from raglite.ingestion.classification.integration import classify_rows_batch

        # Assert: Function is callable
        assert callable(classify_rows_batch)

    def test_ac_1_1_4_classify_row_returns_enriched_row(self) -> None:
        """TEST-AC-9.5.1.4 [P0]: classify_row returns row with classification fields.

        Given a raw row dict with entity, metric, period fields
        When classify_row() is called
        Then the returned dict includes period_type, value_type, entity_level fields
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Raw row from extraction
        raw_row = {
            "entity": "Portugal Cement",
            "metric": "Variable Costs",
            "period": "Dec-24",
            "fiscal_year": 2024,
            "value": 23.5,
            "unit": "EUR/ton",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Classification fields are present
        assert "period_type" in enriched_row
        assert "value_type" in enriched_row
        assert "entity_level" in enriched_row

    def test_ac_1_1_5_classify_row_preserves_original_fields(self) -> None:
        """TEST-AC-9.5.1.5 [P0]: classify_row preserves all original row fields.

        Given a raw row dict with existing fields
        When classify_row() is called
        Then all original fields remain unchanged
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Raw row with multiple fields
        raw_row = {
            "entity": "SECIL SA",
            "metric": "Revenue",
            "period": "Jan-24",
            "fiscal_year": 2024,
            "value": 100.0,
            "unit": "EUR millions",
            "page_number": 12,
            "table_index": 0,
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: All original fields preserved
        assert enriched_row["entity"] == "SECIL SA"
        assert enriched_row["metric"] == "Revenue"
        assert enriched_row["period"] == "Jan-24"
        assert enriched_row["fiscal_year"] == 2024
        assert enriched_row["value"] == 100.0
        assert enriched_row["unit"] == "EUR millions"
        assert enriched_row["page_number"] == 12
        assert enriched_row["table_index"] == 0

    def test_ac_1_1_6_classify_rows_batch_processes_multiple_rows(self) -> None:
        """TEST-AC-9.5.1.6 [P0]: classify_rows_batch processes list of rows.

        Given a list of raw row dicts
        When classify_rows_batch() is called
        Then each row is enriched with classification fields
        """
        from raglite.ingestion.classification.integration import classify_rows_batch

        # Arrange: Multiple raw rows
        raw_rows = [
            {"entity": "Portugal", "metric": "Sales", "period": "Dec-24"},
            {"entity": "GROUP", "metric": "EBITDA", "period": "YTD Dec-24"},
            {"entity": "Cement Division", "metric": "Costs", "period": "Budget 2025"},
        ]

        # Act: Classify all rows
        enriched_rows = classify_rows_batch(raw_rows)

        # Assert: All rows have classification fields
        assert len(enriched_rows) == 3
        for row in enriched_rows:
            assert "period_type" in row
            assert "value_type" in row
            assert "entity_level" in row

    def test_ac_1_1_7_classification_invokes_period_classifier(self) -> None:
        """TEST-AC-9.5.1.7 [P1]: Classification uses existing period classifier.

        Given a row with period field
        When classify_row() is called
        Then it invokes the period_classifier module (not duplicate logic)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with period that should be classified as monthly_actual
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "Dec-24"}

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Period type is set (specific value depends on classifier)
        assert enriched_row["period_type"] is not None
        assert enriched_row["period_type"] != ""

    def test_ac_1_1_8_classification_invokes_value_type_classifier(self) -> None:
        """TEST-AC-9.5.1.8 [P1]: Classification uses existing value_type classifier.

        Given a row with period field
        When classify_row() is called
        Then it invokes the value_type_classifier module
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with period that indicates actual value
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "Dec-24"}

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Value type is set
        assert enriched_row["value_type"] is not None
        assert enriched_row["value_type"] != ""

    def test_ac_1_1_9_classification_invokes_entity_level_classifier(self) -> None:
        """TEST-AC-9.5.1.9 [P1]: Classification uses existing entity_level classifier.

        Given a row with entity field
        When classify_row() is called
        Then it invokes the entity_level_classifier module
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with entity that should be classified
        raw_row = {"entity": "GROUP", "metric": "Revenue", "period": "Dec-24"}

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Entity level is set
        assert enriched_row["entity_level"] is not None
        assert enriched_row["entity_level"] != ""
