"""ATDD tests for Story 9.5 AC6 - Integration with Existing Classifiers.

TDD RED Phase: All tests MUST fail initially because the integration module
does not exist yet at raglite/ingestion/classification/integration.py.

Test IDs follow pattern: TEST-AC-9.5.6.{test}

BDD Acceptance Criteria:
Given the classification modules from Stories 9.2, 9.3, 9.4 exist:
  - raglite/ingestion/classification/period_classifier.py
  - raglite/ingestion/classification/value_type_classifier.py
  - raglite/ingestion/classification/entity_level_classifier.py
When Story 9.5 integration is implemented
Then it uses the existing classify_*() and classify_*_batch() functions
And it does NOT duplicate classification logic
And it coordinates period_type and value_type (BUDGET period_type -> BUDGET value_type)
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
]


class TestAC6IntegrationWithExistingClassifiers:
    """AC6: Integration with Existing Classifiers.

    Given the classification modules from Stories 9.2, 9.3, 9.4 exist
    When Story 9.5 integration is implemented
    Then it uses existing classifiers and coordinates period_type with value_type
    """

    def test_ac_6_1_1_period_classifier_module_used(self) -> None:
        """TEST-AC-9.5.6.1 [P0]: Integration uses period_classifier module.

        Given the period_classifier module exists (Story 9.2)
        When classify_row() classifies period
        Then it uses classify_period() from period_classifier (not duplicate logic)
        """
        # Verify period_classifier exists
        from raglite.ingestion.classification import classify_period

        # Verify integration module uses it
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with known period
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "Dec-24"}

        # Act: Classify using integration
        enriched_row = classify_row(raw_row)

        # Also classify directly with period classifier
        direct_result = classify_period("Dec-24")

        # Assert: Integration result matches direct classifier result
        assert enriched_row["period_type"] == direct_result.period_type.value

    def test_ac_6_1_2_value_type_classifier_module_used(self) -> None:
        """TEST-AC-9.5.6.2 [P0]: Integration uses value_type_classifier module.

        Given the value_type_classifier module exists (Story 9.3)
        When classify_row() classifies value type
        Then it uses classify_value_type() from value_type_classifier
        """
        # Verify value_type_classifier exists
        from raglite.ingestion.classification import (
            PeriodType,
            classify_value_type,
        )

        # Verify integration module uses it
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with known period
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "Dec-24"}

        # Act: Classify using integration
        enriched_row = classify_row(raw_row)

        # Also classify directly with value type classifier
        direct_result = classify_value_type(period="Dec-24", period_type=PeriodType.MONTHLY_ACTUAL)

        # Assert: Integration result matches direct classifier result
        assert enriched_row["value_type"] == direct_result.value_type.value

    def test_ac_6_1_3_entity_level_classifier_module_used(self) -> None:
        """TEST-AC-9.5.6.3 [P0]: Integration uses entity_level_classifier module.

        Given the entity_level_classifier module exists (Story 9.4)
        When classify_row() classifies entity level
        Then it uses classify_entity_level() from entity_level_classifier
        """
        # Verify entity_level_classifier exists
        from raglite.ingestion.classification import classify_entity_level

        # Verify integration module uses it
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with known entity
        raw_row = {"entity": "GROUP", "metric": "Revenue", "period": "Dec-24"}

        # Act: Classify using integration
        enriched_row = classify_row(raw_row)

        # Also classify directly with entity level classifier
        direct_result = classify_entity_level("GROUP")

        # Assert: Integration result matches direct classifier result
        assert enriched_row["entity_level"] == direct_result.entity_level.value

    def test_ac_6_1_4_budget_period_coordinates_with_value_type(self) -> None:
        """TEST-AC-9.5.6.4 [P0]: BUDGET period_type coordinates to BUDGET value_type.

        Given a row with period="Budget 2025"
        When classify_row() is called
        Then period_type="budget" AND value_type="budget" (coordinated)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with budget period
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "Budget 2025"}

        # Act: Classify
        enriched_row = classify_row(raw_row)

        # Assert: Both period and value type are budget
        assert enriched_row["period_type"] == "budget"
        assert enriched_row["value_type"] == "budget"

    def test_ac_6_1_5_ytd_budget_period_coordinates_with_value_type(self) -> None:
        """TEST-AC-9.5.6.5 [P0]: YTD_BUDGET period_type coordinates to BUDGET value_type.

        Given a row with period="YTD Budget 2025"
        When classify_row() is called
        Then period_type="ytd_budget" AND value_type="budget" (coordinated)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with YTD budget period
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "YTD Budget 2025"}

        # Act: Classify
        enriched_row = classify_row(raw_row)

        # Assert: Period is ytd_budget, value is budget
        assert enriched_row["period_type"] == "ytd_budget"
        assert enriched_row["value_type"] == "budget"

    def test_ac_6_1_6_actual_period_coordinates_with_value_type(self) -> None:
        """TEST-AC-9.5.6.6 [P0]: Actual period_type coordinates to ACTUAL value_type.

        Given a row with period="Dec-24" (monthly actual)
        When classify_row() is called
        Then period_type="monthly_actual" AND value_type="actual" (coordinated)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with actual period
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "Dec-24"}

        # Act: Classify
        enriched_row = classify_row(raw_row)

        # Assert: Both period and value type reflect actual
        assert enriched_row["period_type"] == "monthly_actual"
        assert enriched_row["value_type"] == "actual"

    def test_ac_6_1_7_ytd_actual_period_coordinates_with_value_type(self) -> None:
        """TEST-AC-9.5.6.7 [P0]: YTD_ACTUAL period_type coordinates to ACTUAL value_type.

        Given a row with period="YTD Dec-24"
        When classify_row() is called
        Then period_type="ytd_actual" AND value_type="actual" (coordinated)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with YTD actual period
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "YTD Dec-24"}

        # Act: Classify
        enriched_row = classify_row(raw_row)

        # Assert: Period is ytd_actual, value is actual
        assert enriched_row["period_type"] == "ytd_actual"
        assert enriched_row["value_type"] == "actual"

    def test_ac_6_1_8_no_duplicate_classification_logic(self) -> None:
        """TEST-AC-9.5.6.8 [P1]: Integration does not duplicate classification logic.

        Given the integration module
        When inspecting its implementation
        Then it imports and calls existing classifiers (no regex/pattern duplication)
        """
        import inspect

        from raglite.ingestion.classification import integration

        # Get source code
        source = inspect.getsource(integration)

        # Assert: Source imports from existing classifiers
        assert "classify_period" in source, "Should import classify_period"
        assert "classify_value_type" in source, "Should import classify_value_type"
        assert "classify_entity_level" in source, "Should import classify_entity_level"

        # Assert: No duplicate regex patterns (these belong in individual classifiers)
        # The integration module should NOT have its own pattern matching
        assert source.count("re.compile") == 0, (
            "Integration should not have compiled regex patterns - use existing classifiers"
        )

    def test_ac_6_1_9_batch_classification_uses_existing_batch_functions(self) -> None:
        """TEST-AC-9.5.6.9 [P1]: Batch classification uses existing batch functions.

        Given the classify_rows_batch function
        When classifying multiple rows
        Then it uses classify_periods_batch, classify_value_types_batch, etc.
        """
        from raglite.ingestion.classification.integration import classify_rows_batch

        # Arrange: Multiple rows
        rows = [
            {"entity": "Portugal", "metric": "Sales", "period": "Dec-24"},
            {"entity": "GROUP", "metric": "EBITDA", "period": "Budget 2025"},
        ]

        # Act: Batch classify
        results = classify_rows_batch(rows)

        # Assert: Results are correct (uses underlying batch functions)
        assert len(results) == 2
        assert results[0]["period_type"] == "monthly_actual"
        assert results[1]["period_type"] == "budget"

    def test_ac_6_1_10_passes_period_type_to_value_classifier(self) -> None:
        """TEST-AC-9.5.6.10 [P1]: Integration passes period_type to value type classifier.

        Given the coordination requirement between classifiers
        When classify_row() is called
        Then period_type is passed to classify_value_type() for coordination
        """
        from raglite.ingestion.classification.integration import classify_row

        # Test case: YTD Budget period should result in budget value type
        # This can only happen if period_type is passed to value_type classifier
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "YTD Budget 2025"}

        enriched_row = classify_row(raw_row)

        # If period_type wasn't passed, value_type might be wrong
        # Correct coordination: ytd_budget period -> budget value
        assert enriched_row["value_type"] == "budget", (
            "Value type should be 'budget' when period is YTD Budget. "
            "This requires passing period_type to value classifier."
        )
