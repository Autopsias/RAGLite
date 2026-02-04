"""ATDD tests for Story 9.5 AC3 - Classification Report Generation.

TDD RED Phase: All tests MUST fail initially because the integration module
does not exist yet at raglite/ingestion/classification/integration.py.

Test IDs follow pattern: TEST-AC-9.5.3.{test}

BDD Acceptance Criteria:
Given a document is being ingested with multiple tables
When all tables are extracted and classified
Then a ClassificationSummary is generated with:
  - period_type_breakdown: counts by PeriodType enum
  - value_type_breakdown: counts by ValueType enum
  - entity_level_breakdown: counts by EntityLevel enum
  - total_rows_classified: count of all rows
  - classification_duration_ms: time spent on classification
And the summary is logged at INFO level for audit trail
And classification reports enable quality monitoring without database queries
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
]


class TestAC3ClassificationReportGeneration:
    """AC3: Classification Report Generation.

    Given a document is being ingested with multiple tables
    When all tables are extracted and classified
    Then a ClassificationSummary is generated with breakdown counts
    """

    def test_ac_3_1_1_classification_summary_dataclass_exists(self) -> None:
        """TEST-AC-9.5.3.1 [P0]: ClassificationSummary dataclass exists.

        Given the integration module exists
        When we import ClassificationSummary
        Then it is a dataclass with required fields
        """
        from dataclasses import fields

        from raglite.ingestion.classification.integration import ClassificationSummary

        # Assert: It's a dataclass with expected fields
        field_names = {f.name for f in fields(ClassificationSummary)}
        assert "total_rows" in field_names
        assert "classification_duration_ms" in field_names

    def test_ac_3_1_2_summary_has_period_type_breakdown(self) -> None:
        """TEST-AC-9.5.3.2 [P0]: Summary has period_type breakdown counts.

        Given a ClassificationSummary
        When inspecting its fields
        Then it has period type breakdown fields
        """
        from dataclasses import fields

        from raglite.ingestion.classification.integration import ClassificationSummary

        # Assert: Period type breakdown fields exist
        field_names = {f.name for f in fields(ClassificationSummary)}
        assert "period_monthly_actual" in field_names
        assert "period_ytd_actual" in field_names
        assert "period_budget" in field_names
        assert "period_ytd_budget" in field_names
        assert "period_unknown" in field_names

    def test_ac_3_1_3_summary_has_value_type_breakdown(self) -> None:
        """TEST-AC-9.5.3.3 [P0]: Summary has value_type breakdown counts.

        Given a ClassificationSummary
        When inspecting its fields
        Then it has value type breakdown fields
        """
        from dataclasses import fields

        from raglite.ingestion.classification.integration import ClassificationSummary

        # Assert: Value type breakdown fields exist
        field_names = {f.name for f in fields(ClassificationSummary)}
        assert "value_actual" in field_names
        assert "value_budget" in field_names
        assert "value_forecast" in field_names
        assert "value_variance" in field_names
        assert "value_unknown" in field_names

    def test_ac_3_1_4_summary_has_entity_level_breakdown(self) -> None:
        """TEST-AC-9.5.3.4 [P0]: Summary has entity_level breakdown counts.

        Given a ClassificationSummary
        When inspecting its fields
        Then it has entity level breakdown fields
        """
        from dataclasses import fields

        from raglite.ingestion.classification.integration import ClassificationSummary

        # Assert: Entity level breakdown fields exist
        field_names = {f.name for f in fields(ClassificationSummary)}
        assert "entity_consolidated" in field_names
        assert "entity_company_only" in field_names
        assert "entity_segment" in field_names
        assert "entity_geographic" in field_names
        assert "entity_unknown" in field_names

    def test_ac_3_1_5_generate_classification_summary_function_exists(self) -> None:
        """TEST-AC-9.5.3.5 [P0]: generate_classification_summary function exists.

        Given the integration module exists
        When we import generate_classification_summary
        Then it is a callable function
        """
        from raglite.ingestion.classification.integration import (
            generate_classification_summary,
        )

        # Assert: Function is callable
        assert callable(generate_classification_summary)

    def test_ac_3_1_6_generate_summary_returns_classification_summary(self) -> None:
        """TEST-AC-9.5.3.6 [P0]: generate_classification_summary returns ClassificationSummary.

        Given a list of classified rows
        When generate_classification_summary() is called
        Then it returns a ClassificationSummary instance
        """
        from raglite.ingestion.classification.integration import (
            generate_classification_summary,
        )

        # Arrange: Classified rows
        classified_rows = [
            {
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            {"period_type": "ytd_actual", "value_type": "actual", "entity_level": "consolidated"},
        ]

        # Act: Generate summary
        summary = generate_classification_summary(classified_rows)

        # Assert: Returns ClassificationSummary
        assert summary.__class__.__name__ == "ClassificationSummary"

    def test_ac_3_1_7_summary_counts_total_rows(self) -> None:
        """TEST-AC-9.5.3.7 [P0]: Summary counts total rows correctly.

        Given 5 classified rows
        When generate_classification_summary() is called
        Then total_rows equals 5
        """
        from raglite.ingestion.classification.integration import (
            generate_classification_summary,
        )

        # Arrange: 5 classified rows
        classified_rows = [
            {
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            {
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            {"period_type": "budget", "value_type": "budget", "entity_level": "consolidated"},
            {"period_type": "ytd_actual", "value_type": "actual", "entity_level": "geographic"},
            {"period_type": "unknown", "value_type": "unknown", "entity_level": "unknown"},
        ]

        # Act: Generate summary
        summary = generate_classification_summary(classified_rows)

        # Assert: Total rows counted correctly
        assert summary.total_rows == 5

    def test_ac_3_1_8_summary_counts_period_types_correctly(self) -> None:
        """TEST-AC-9.5.3.8 [P0]: Summary counts period types correctly.

        Given rows with mixed period types
        When generate_classification_summary() is called
        Then period type counts are accurate
        """
        from raglite.ingestion.classification.integration import (
            generate_classification_summary,
        )

        # Arrange: Rows with specific period types
        classified_rows = [
            {
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            {
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            {"period_type": "ytd_actual", "value_type": "actual", "entity_level": "consolidated"},
            {"period_type": "budget", "value_type": "budget", "entity_level": "geographic"},
        ]

        # Act: Generate summary
        summary = generate_classification_summary(classified_rows)

        # Assert: Period type counts correct
        assert summary.period_monthly_actual == 2
        assert summary.period_ytd_actual == 1
        assert summary.period_budget == 1
        assert summary.period_ytd_budget == 0
        assert summary.period_unknown == 0

    def test_ac_3_1_9_summary_counts_value_types_correctly(self) -> None:
        """TEST-AC-9.5.3.9 [P0]: Summary counts value types correctly.

        Given rows with mixed value types
        When generate_classification_summary() is called
        Then value type counts are accurate
        """
        from raglite.ingestion.classification.integration import (
            generate_classification_summary,
        )

        # Arrange: Rows with specific value types
        classified_rows = [
            {
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            {
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            {"period_type": "budget", "value_type": "budget", "entity_level": "consolidated"},
            {"period_type": "ytd_actual", "value_type": "variance", "entity_level": "geographic"},
        ]

        # Act: Generate summary
        summary = generate_classification_summary(classified_rows)

        # Assert: Value type counts correct
        assert summary.value_actual == 2
        assert summary.value_budget == 1
        assert summary.value_variance == 1
        assert summary.value_forecast == 0
        assert summary.value_unknown == 0

    def test_ac_3_1_10_summary_counts_entity_levels_correctly(self) -> None:
        """TEST-AC-9.5.3.10 [P0]: Summary counts entity levels correctly.

        Given rows with mixed entity levels
        When generate_classification_summary() is called
        Then entity level counts are accurate
        """
        from raglite.ingestion.classification.integration import (
            generate_classification_summary,
        )

        # Arrange: Rows with specific entity levels
        classified_rows = [
            {
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            {
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            {"period_type": "budget", "value_type": "budget", "entity_level": "consolidated"},
            {"period_type": "ytd_actual", "value_type": "actual", "entity_level": "geographic"},
            {"period_type": "monthly_actual", "value_type": "actual", "entity_level": "segment"},
        ]

        # Act: Generate summary
        summary = generate_classification_summary(classified_rows)

        # Assert: Entity level counts correct
        assert summary.entity_company_only == 2
        assert summary.entity_consolidated == 1
        assert summary.entity_geographic == 1
        assert summary.entity_segment == 1
        assert summary.entity_unknown == 0

    def test_ac_3_1_11_summary_includes_duration_ms(self) -> None:
        """TEST-AC-9.5.3.11 [P1]: Summary includes classification_duration_ms.

        Given rows are classified
        When generate_classification_summary() is called
        Then classification_duration_ms is populated (>= 0)
        """
        from raglite.ingestion.classification.integration import (
            generate_classification_summary,
        )

        # Arrange: Classified rows
        classified_rows = [
            {
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
        ]

        # Act: Generate summary (with timing)
        summary = generate_classification_summary(classified_rows)

        # Assert: Duration is a non-negative integer
        assert hasattr(summary, "classification_duration_ms")
        assert isinstance(summary.classification_duration_ms, int)
        assert summary.classification_duration_ms >= 0

    def test_ac_3_1_12_empty_rows_returns_zero_counts(self) -> None:
        """TEST-AC-9.5.3.12 [P1]: Empty rows list returns zero counts.

        Given an empty list of rows
        When generate_classification_summary() is called
        Then all counts are zero
        """
        from raglite.ingestion.classification.integration import (
            generate_classification_summary,
        )

        # Arrange: Empty rows list
        classified_rows: list[dict] = []

        # Act: Generate summary
        summary = generate_classification_summary(classified_rows)

        # Assert: All counts are zero
        assert summary.total_rows == 0
        assert summary.period_monthly_actual == 0
        assert summary.value_actual == 0
        assert summary.entity_company_only == 0
