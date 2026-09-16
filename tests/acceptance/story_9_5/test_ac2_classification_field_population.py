"""ATDD tests for Story 9.5 AC2 - Classification Field Population.

TDD RED Phase: All tests MUST fail initially because the integration module
does not exist yet at raglite/ingestion/classification/integration.py.

Test IDs follow pattern: TEST-AC-9.5.2.{test}

BDD Acceptance Criteria:
Given a table row with period="Dec-24", entity="Portugal Cement", metric="Variable Costs"
When classification is applied during extraction
Then the row includes:
  - period_type="monthly_actual" (from period classifier)
  - value_type="actual" (from value type classifier)
  - entity_level="company_only" (from entity level classifier)
And all three fields are populated for every extracted row
And UNKNOWN is used when classification cannot determine type (no NULLs)
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
]


class TestAC2ClassificationFieldPopulation:
    """AC2: Classification Field Population.

    Given a table row with specific fields
    When classification is applied during extraction
    Then the row includes correctly classified period_type, value_type, entity_level
    And UNKNOWN is used when classification cannot determine type
    """

    def test_ac_2_1_1_monthly_actual_period_classified_correctly(self) -> None:
        """TEST-AC-9.5.2.1 [P0]: Monthly actual period classified correctly.

        Given a row with period="Dec-24"
        When classify_row() is called
        Then period_type="monthly_actual"
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with monthly actual period
        raw_row = {
            "entity": "Portugal Cement",
            "metric": "Variable Costs",
            "period": "Dec-24",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Period type is monthly_actual
        assert enriched_row["period_type"] == "monthly_actual"

    def test_ac_2_1_2_actual_value_type_classified_correctly(self) -> None:
        """TEST-AC-9.5.2.2 [P0]: Actual value type classified correctly.

        Given a row with period="Dec-24" (actual period)
        When classify_row() is called
        Then value_type="actual"
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with actual period
        raw_row = {
            "entity": "Portugal Cement",
            "metric": "Variable Costs",
            "period": "Dec-24",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Value type is actual
        assert enriched_row["value_type"] == "actual"

    def test_ac_2_1_3_company_entity_level_classified_correctly(self) -> None:
        """TEST-AC-9.5.2.3 [P0]: Company entity level classified correctly.

        Given a row with entity="Portugal Cement" (company name)
        When classify_row() is called
        Then entity_level="company_only"
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with company entity
        raw_row = {
            "entity": "Portugal Cement",
            "metric": "Variable Costs",
            "period": "Dec-24",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Entity level is company_only
        assert enriched_row["entity_level"] == "company_only"

    def test_ac_2_1_4_all_three_fields_populated(self) -> None:
        """TEST-AC-9.5.2.4 [P0]: All three classification fields populated.

        Given any extracted row
        When classify_row() is called
        Then all three fields (period_type, value_type, entity_level) are populated
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with minimal fields
        raw_row = {
            "entity": "Test Entity",
            "metric": "Test Metric",
            "period": "Jan-24",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: All three fields present and non-empty
        assert "period_type" in enriched_row
        assert "value_type" in enriched_row
        assert "entity_level" in enriched_row
        assert enriched_row["period_type"] is not None
        assert enriched_row["value_type"] is not None
        assert enriched_row["entity_level"] is not None

    def test_ac_2_1_5_unknown_period_type_no_nulls(self) -> None:
        """TEST-AC-9.5.2.5 [P0]: UNKNOWN used for unclassifiable period (no NULLs).

        Given a row with unclassifiable period="???"
        When classify_row() is called
        Then period_type="unknown" (not NULL)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with unclassifiable period
        raw_row = {
            "entity": "Test Entity",
            "metric": "Test Metric",
            "period": "???",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: period_type is "unknown", not None
        assert enriched_row["period_type"] == "unknown"

    def test_ac_2_1_6_unknown_value_type_no_nulls(self) -> None:
        """TEST-AC-9.5.2.6 [P0]: UNKNOWN used for unclassifiable value type (no NULLs).

        Given a row where value type cannot be determined
        When classify_row() is called
        Then value_type="unknown" (not NULL)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with ambiguous context
        raw_row = {
            "entity": "Test Entity",
            "metric": "Test Metric",
            "period": "???",  # Unclassifiable period leads to unknown value type
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: value_type is "unknown", not None
        assert enriched_row["value_type"] == "unknown"

    def test_ac_2_1_7_unknown_entity_level_no_nulls(self) -> None:
        """TEST-AC-9.5.2.7 [P0]: UNKNOWN used for unclassifiable entity (no NULLs).

        Given a row with ambiguous entity="XYZ123"
        When classify_row() is called
        Then entity_level="unknown" (not NULL)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with ambiguous entity
        raw_row = {
            "entity": "XYZ123",  # Ambiguous - no clear pattern
            "metric": "Test Metric",
            "period": "Dec-24",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: entity_level is "unknown", not None
        assert enriched_row["entity_level"] == "unknown"

    def test_ac_2_1_8_budget_period_classified_correctly(self) -> None:
        """TEST-AC-9.5.2.8 [P1]: Budget period classified correctly.

        Given a row with period="Budget 2025"
        When classify_row() is called
        Then period_type="budget" and value_type="budget"
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with budget period
        raw_row = {
            "entity": "Portugal",
            "metric": "Revenue",
            "period": "Budget 2025",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Both period and value type reflect budget
        assert enriched_row["period_type"] == "budget"
        assert enriched_row["value_type"] == "budget"

    def test_ac_2_1_9_ytd_actual_period_classified_correctly(self) -> None:
        """TEST-AC-9.5.2.9 [P1]: YTD actual period classified correctly.

        Given a row with period="YTD Dec-24"
        When classify_row() is called
        Then period_type="ytd_actual"
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with YTD actual period
        raw_row = {
            "entity": "GROUP",
            "metric": "EBITDA",
            "period": "YTD Dec-24",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Period type is ytd_actual
        assert enriched_row["period_type"] == "ytd_actual"

    def test_ac_2_1_10_consolidated_entity_level_classified_correctly(self) -> None:
        """TEST-AC-9.5.2.10 [P1]: Consolidated entity level classified correctly.

        Given a row with entity="GROUP"
        When classify_row() is called
        Then entity_level="consolidated"
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with consolidated entity
        raw_row = {
            "entity": "GROUP",
            "metric": "Total Revenue",
            "period": "Dec-24",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Entity level is consolidated
        assert enriched_row["entity_level"] == "consolidated"

    def test_ac_2_1_11_geographic_entity_level_classified_correctly(self) -> None:
        """TEST-AC-9.5.2.11 [P1]: Geographic entity level classified correctly.

        Given a row with entity="Portugal" (country name)
        When classify_row() is called
        Then entity_level="geographic"
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with geographic entity
        raw_row = {
            "entity": "Portugal",
            "metric": "Sales",
            "period": "Dec-24",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Entity level is geographic
        assert enriched_row["entity_level"] == "geographic"

    def test_ac_2_1_12_segment_entity_level_classified_correctly(self) -> None:
        """TEST-AC-9.5.2.12 [P1]: Segment entity level classified correctly.

        Given a row with entity="Cement Division"
        When classify_row() is called
        Then entity_level="segment"
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with segment entity
        raw_row = {
            "entity": "Cement Division",
            "metric": "Operating Margin",
            "period": "Dec-24",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: Entity level is segment
        assert enriched_row["entity_level"] == "segment"

    def test_ac_2_1_13_empty_period_returns_unknown(self) -> None:
        """TEST-AC-9.5.2.13 [P1]: Empty period returns unknown (no NULL).

        Given a row with empty period=""
        When classify_row() is called
        Then period_type="unknown" (handles gracefully)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with empty period
        raw_row = {
            "entity": "Test Entity",
            "metric": "Test Metric",
            "period": "",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: period_type is unknown (graceful handling)
        assert enriched_row["period_type"] == "unknown"

    def test_ac_2_1_14_none_period_returns_unknown(self) -> None:
        """TEST-AC-9.5.2.14 [P1]: None period returns unknown (no NULL).

        Given a row with period=None
        When classify_row() is called
        Then period_type="unknown" (handles gracefully)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with None period
        raw_row = {
            "entity": "Test Entity",
            "metric": "Test Metric",
            "period": None,
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: period_type is unknown (graceful handling)
        assert enriched_row["period_type"] == "unknown"
