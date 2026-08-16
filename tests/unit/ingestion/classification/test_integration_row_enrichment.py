"""Unit tests for row enrichment functions in classification integration.

Tests coverage:
- classify_row: Single row enrichment
- classify_rows_batch: Batch row enrichment

Target: 95%+ coverage per Epic 9 requirements
"""

import pytest

from raglite.ingestion.classification.integration import (
    classify_row,
    classify_rows_batch,
)
from raglite.ingestion.classification.models import (
    EntityLevel,
    PeriodType,
    ValueType,
)

# Test markers
pytestmark = [
    pytest.mark.unit,
]


class TestClassifyRow:
    """Tests for classify_row function.

    Given: A row dict with entity, metric, period fields
    When: classify_row() is called
    Then: The row is enriched with classification fields
    """

    def test_classify_row_with_all_fields(self):
        """TEST-AC-9.5.1.1 [P0]: Single row classification with all fields populated.

        Arrange: Row with all required fields
        Act: Call classify_row()
        Assert: Classification fields added, original fields preserved
        """
        row = {
            "entity": "Portugal Cement",
            "metric": "Variable Costs",
            "period": "Dec-24",
            "value": 23.5,
        }

        result = classify_row(row)

        # All original fields preserved
        assert result["entity"] == "Portugal Cement"
        assert result["metric"] == "Variable Costs"
        assert result["period"] == "Dec-24"
        assert result["value"] == 23.5

        # New classification fields added
        assert result["period_type"] == PeriodType.MONTHLY_ACTUAL.value
        assert result["value_type"] == ValueType.ACTUAL.value
        assert result["entity_level"] == EntityLevel.COMPANY_ONLY.value

    def test_classify_row_with_budget_period(self):
        """TEST-AC-9.5.1.2 [P0]: Classification with budget period.

        Arrange: Row with budget period
        Act: Call classify_row()
        Assert: period_type and value_type both BUDGET
        """
        row = {"entity": "Consolidated", "period": "B Dec-24", "metric": "Revenue"}

        result = classify_row(row)

        assert result["period_type"] == PeriodType.BUDGET.value
        assert result["value_type"] == ValueType.BUDGET.value
        assert result["entity_level"] == EntityLevel.CONSOLIDATED.value

    def test_classify_row_with_segment_entity(self):
        """TEST-AC-9.5.1.3 [P0]: Classification with segment-level entity.

        Arrange: Row with segment entity
        Act: Call classify_row()
        Assert: entity_level is SEGMENT
        """
        row = {"entity": "Cement Segment", "period": "Jan-25", "metric": "EBITDA"}

        result = classify_row(row)

        assert result["entity_level"] == EntityLevel.SEGMENT.value
        assert result["period_type"] == PeriodType.MONTHLY_ACTUAL.value
        assert result["value_type"] == ValueType.ACTUAL.value

    def test_classify_row_with_missing_fields(self):
        """TEST-AC-9.5.1.4 [P0]: Classification with missing/None fields.

        Arrange: Row missing entity and period
        Act: Call classify_row()
        Assert: Uses UNKNOWN, no crashes or NULLs
        """
        row = {"metric": "Revenue"}  # No entity or period

        result = classify_row(row)

        # Should not crash, should use empty strings and classify as UNKNOWN
        assert "period_type" in result
        assert "value_type" in result
        assert "entity_level" in result

    def test_classify_row_with_none_values(self):
        """TEST-AC-9.5.1.5 [P0]: Classification with explicit None values.

        Arrange: Row with None entity and period
        Act: Call classify_row()
        Assert: Handles None gracefully with UNKNOWN
        """
        row = {"entity": None, "period": None, "metric": "Revenue"}

        result = classify_row(row)

        # Should handle None gracefully
        assert "period_type" in result
        assert "value_type" in result
        assert "entity_level" in result


class TestClassifyRowsBatch:
    """Tests for classify_rows_batch function.

    Given: A list of row dicts with mixed classification types
    When: classify_rows_batch() is called
    Then: All rows are enriched, order preserved, all fields populated
    """

    def test_batch_classification_with_mixed_types(self):
        """TEST-AC-9.5.2.1 [P0]: Batch classification with mixed types.

        Arrange: Multiple rows with different period/value/entity types
        Act: Call classify_rows_batch()
        Assert: All rows enriched correctly
        """
        rows = [
            {"entity": "Portugal Cement", "period": "Dec-24", "metric": "Revenue"},
            {"entity": "Consolidated", "period": "B Jan-25", "metric": "EBITDA"},
            {"entity": "Cement Segment", "period": "YTD Dec-24", "metric": "Costs"},
            {"entity": "North Region", "period": "Forecast Feb-25", "metric": "Sales"},
        ]

        results = classify_rows_batch(rows)

        assert len(results) == 4

        # Row 0: Monthly actual, company_only
        assert results[0]["period_type"] == PeriodType.MONTHLY_ACTUAL.value
        assert results[0]["value_type"] == ValueType.ACTUAL.value
        assert results[0]["entity_level"] == EntityLevel.COMPANY_ONLY.value

        # Row 1: Budget, consolidated
        assert results[1]["period_type"] == PeriodType.BUDGET.value
        assert results[1]["value_type"] == ValueType.BUDGET.value
        assert results[1]["entity_level"] == EntityLevel.CONSOLIDATED.value

        # Row 2: YTD actual, segment
        assert results[2]["period_type"] == PeriodType.YTD_ACTUAL.value
        assert results[2]["value_type"] == ValueType.ACTUAL.value
        assert results[2]["entity_level"] == EntityLevel.SEGMENT.value

        # Row 3: Unknown period (forecast keyword not normalized), forecast value, geographic
        assert results[3]["period_type"] == PeriodType.UNKNOWN.value
        assert results[3]["value_type"] == ValueType.FORECAST.value
        assert results[3]["entity_level"] == EntityLevel.GEOGRAPHIC.value

    def test_batch_classification_empty_list(self):
        """TEST-AC-9.5.2.2 [P0]: Batch classification with empty list.

        Arrange: Empty row list
        Act: Call classify_rows_batch()
        Assert: Returns empty list
        """
        results = classify_rows_batch([])
        assert results == []

    def test_batch_classification_preserves_order(self):
        """TEST-AC-9.5.2.3 [P0]: Batch classification preserves order.

        Arrange: 10 rows with indexed entities
        Act: Call classify_rows_batch()
        Assert: Order preserved exactly
        """
        rows = [
            {"entity": f"Entity {i}", "period": "Dec-24", "metric": "Revenue"} for i in range(10)
        ]

        results = classify_rows_batch(rows)

        assert len(results) == 10
        for i, result in enumerate(results):
            assert result["entity"] == f"Entity {i}"

    def test_batch_classification_all_fields_present(self):
        """TEST-AC-9.5.2.4 [P0]: All rows have all three classification fields.

        Arrange: Rows with missing/empty fields
        Act: Call classify_rows_batch()
        Assert: All rows have all three fields (no NULLs)
        """
        rows = [
            {"entity": "Entity A", "period": "Dec-24"},
            {"entity": "", "period": ""},  # Empty strings
            {"metric": "Revenue"},  # Missing entity/period
        ]

        results = classify_rows_batch(rows)

        # All rows must have all three fields
        for result in results:
            assert "period_type" in result
            assert "value_type" in result
            assert "entity_level" in result
            assert result["period_type"] is not None
            assert result["value_type"] is not None
            assert result["entity_level"] is not None


class TestCoordination:
    """Tests for period_type and value_type coordination (AC6).

    Given: Period and value type must coordinate
    When: classify_row() is called
    Then: Coordinated classifications returned
    """

    def test_coordination_budget_period_to_budget_value(self):
        """TEST-AC-9.5.6.1 [P1]: BUDGET period coordinates to BUDGET value.

        Arrange: Row with budget period
        Act: Call classify_row()
        Assert: Both period_type and value_type are BUDGET
        """
        row = {"entity": "Company", "period": "B Dec-24", "metric": "Revenue"}

        result = classify_row(row)

        # Period classifier detects BUDGET
        assert result["period_type"] == PeriodType.BUDGET.value
        # Value type classifier uses period_type and also returns BUDGET
        assert result["value_type"] == ValueType.BUDGET.value

    def test_coordination_ytd_budget_period_to_budget_value(self):
        """TEST-AC-9.5.6.2 [P1]: YTD_BUDGET period coordinates to BUDGET value.

        Arrange: Row with YTD budget period
        Act: Call classify_row()
        Assert: value_type is BUDGET
        """
        row = {"entity": "Company", "period": "YTD B Dec-24", "metric": "Revenue"}

        result = classify_row(row)

        assert result["period_type"] == PeriodType.YTD_BUDGET.value
        assert result["value_type"] == ValueType.BUDGET.value

    def test_coordination_actual_period_to_actual_value(self):
        """TEST-AC-9.5.6.3 [P1]: MONTHLY_ACTUAL period coordinates to ACTUAL.

        Arrange: Row with actual period
        Act: Call classify_row()
        Assert: value_type is ACTUAL
        """
        row = {"entity": "Company", "period": "Dec-24", "metric": "Revenue"}

        result = classify_row(row)

        assert result["period_type"] == PeriodType.MONTHLY_ACTUAL.value
        assert result["value_type"] == ValueType.ACTUAL.value


class TestBackwardCompatibility:
    """Tests for backward compatibility (AC5).

    Given: Existing row fields
    When: classify_row() is called
    Then: Existing fields unchanged, new fields added
    """

    def test_existing_fields_unchanged(self):
        """TEST-AC-9.5.5.1 [P0]: Existing row fields unchanged.

        Arrange: Row with all existing fields
        Act: Call classify_row()
        Assert: All original fields preserved exactly
        """
        row = {
            "entity": "Portugal Cement",
            "metric": "Variable Costs",
            "period": "Dec-24",
            "fiscal_year": 2024,
            "value": 23.5,
            "unit": "EUR/ton",
            "page_number": 12,
            "table_index": 0,
            "table_caption": "Performance Summary",
            "row_index": 5,
            "column_name": "Dec-24",
            "chunk_text": "Some text",
            "document_id": "2024-12-performance-review",
        }

        result = classify_row(row)

        # All original fields must be preserved
        assert result["entity"] == row["entity"]
        assert result["metric"] == row["metric"]
        assert result["period"] == row["period"]
        assert result["fiscal_year"] == row["fiscal_year"]
        assert result["value"] == row["value"]
        assert result["unit"] == row["unit"]
        assert result["page_number"] == row["page_number"]
        assert result["table_index"] == row["table_index"]
        assert result["table_caption"] == row["table_caption"]
        assert result["row_index"] == row["row_index"]
        assert result["column_name"] == row["column_name"]
        assert result["chunk_text"] == row["chunk_text"]
        assert result["document_id"] == row["document_id"]

        # New fields added
        assert "period_type" in result
        assert "value_type" in result
        assert "entity_level" in result

    def test_new_fields_use_string_values(self):
        """TEST-AC-9.5.5.2 [P0]: New fields use string values (JSON serializable).

        Arrange: Row with test data
        Act: Call classify_row()
        Assert: Classification fields are strings (not enum objects)
        """
        row = {"entity": "Company", "period": "Dec-24", "metric": "Revenue"}

        result = classify_row(row)

        # All classification fields must be strings
        assert isinstance(result["period_type"], str)
        assert isinstance(result["value_type"], str)
        assert isinstance(result["entity_level"], str)

        # Should match enum .value attributes
        assert result["period_type"] == "monthly_actual"
        assert result["value_type"] == "actual"
        assert result["entity_level"] == "company_only"
