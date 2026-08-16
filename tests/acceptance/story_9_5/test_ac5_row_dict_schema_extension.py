"""ATDD tests for Story 9.5 AC5 - Row Dict Schema Extension.

TDD RED Phase: All tests MUST fail initially because the integration module
does not exist yet at raglite/ingestion/classification/integration.py.

Test IDs follow pattern: TEST-AC-9.5.5.{test}

BDD Acceptance Criteria:
Given the current row dict schema from extract_table_data_adaptive:
  {entity, metric, period, fiscal_year, value, unit, ...}
When classification integration is complete
Then row dict includes additional fields:
  - period_type: str (PeriodType.value)
  - value_type: str (ValueType.value)
  - entity_level: str (EntityLevel.value)
And existing fields remain unchanged (backward compatible)
And new fields use string values (not enum objects) for JSON serialization
"""

import json

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
]


class TestAC5RowDictSchemaExtension:
    """AC5: Row Dict Schema Extension.

    Given the current row dict schema from extract_table_data_adaptive
    When classification integration is complete
    Then row dict includes additional string classification fields
    And existing fields remain unchanged (backward compatible)
    """

    def test_ac_5_1_1_period_type_is_string_not_enum(self) -> None:
        """TEST-AC-9.5.5.1 [P0]: period_type field is a string, not enum object.

        Given a classified row
        When inspecting period_type
        Then it is a string value (for JSON serialization)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row to classify
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "Dec-24"}

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: period_type is a string
        assert isinstance(enriched_row["period_type"], str)

    def test_ac_5_1_2_value_type_is_string_not_enum(self) -> None:
        """TEST-AC-9.5.5.2 [P0]: value_type field is a string, not enum object.

        Given a classified row
        When inspecting value_type
        Then it is a string value (for JSON serialization)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row to classify
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "Dec-24"}

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: value_type is a string
        assert isinstance(enriched_row["value_type"], str)

    def test_ac_5_1_3_entity_level_is_string_not_enum(self) -> None:
        """TEST-AC-9.5.5.3 [P0]: entity_level field is a string, not enum object.

        Given a classified row
        When inspecting entity_level
        Then it is a string value (for JSON serialization)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row to classify
        raw_row = {"entity": "Test", "metric": "Revenue", "period": "Dec-24"}

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: entity_level is a string
        assert isinstance(enriched_row["entity_level"], str)

    def test_ac_5_1_4_enriched_row_is_json_serializable(self) -> None:
        """TEST-AC-9.5.5.4 [P0]: Enriched row is JSON serializable.

        Given a classified row
        When attempting JSON serialization
        Then it succeeds (no enum objects blocking serialization)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Full row with all typical fields
        raw_row = {
            "entity": "Portugal Cement",
            "metric": "Variable Costs",
            "period": "Dec-24",
            "fiscal_year": 2024,
            "value": 23.5,
            "unit": "EUR/ton",
            "page_number": 12,
            "table_index": 0,
        }

        # Act: Classify and serialize
        enriched_row = classify_row(raw_row)
        json_str = json.dumps(enriched_row)

        # Assert: Serialization succeeded
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Verify we can deserialize back
        deserialized = json.loads(json_str)
        assert deserialized["period_type"] == enriched_row["period_type"]
        assert deserialized["value_type"] == enriched_row["value_type"]
        assert deserialized["entity_level"] == enriched_row["entity_level"]

    def test_ac_5_1_5_original_fields_unchanged(self) -> None:
        """TEST-AC-9.5.5.5 [P0]: Original fields remain unchanged after classification.

        Given a row with existing fields
        When classify_row() is called
        Then all original field values are preserved exactly
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with all typical extraction fields
        raw_row = {
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
            "chunk_text": "Sample chunk text here...",
            "document_id": "2024-12-performance-review",
        }

        # Act: Classify the row
        enriched_row = classify_row(raw_row)

        # Assert: All original fields preserved exactly
        assert enriched_row["entity"] == "Portugal Cement"
        assert enriched_row["metric"] == "Variable Costs"
        assert enriched_row["period"] == "Dec-24"
        assert enriched_row["fiscal_year"] == 2024
        assert enriched_row["value"] == 23.5
        assert enriched_row["unit"] == "EUR/ton"
        assert enriched_row["page_number"] == 12
        assert enriched_row["table_index"] == 0
        assert enriched_row["table_caption"] == "Performance Summary"
        assert enriched_row["row_index"] == 5
        assert enriched_row["column_name"] == "Dec-24"
        assert enriched_row["chunk_text"] == "Sample chunk text here..."
        assert enriched_row["document_id"] == "2024-12-performance-review"

    def test_ac_5_1_6_backward_compatible_with_existing_consumers(self) -> None:
        """TEST-AC-9.5.5.6 [P0]: Schema is backward compatible.

        Given downstream consumers expect original fields
        When row is classified
        Then accessing original fields works as before (no breaking changes)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Minimal row
        raw_row = {
            "entity": "Test",
            "metric": "Revenue",
            "period": "Dec-24",
            "value": 100.0,
        }

        # Act: Classify
        enriched_row = classify_row(raw_row)

        # Assert: Can access fields the "old way" (backward compatible)
        # Simulate downstream consumer code that existed before Story 9.5
        entity = enriched_row.get("entity")
        metric = enriched_row.get("metric")
        period = enriched_row.get("period")
        value = enriched_row.get("value")

        assert entity == "Test"
        assert metric == "Revenue"
        assert period == "Dec-24"
        assert value == 100.0

    def test_ac_5_1_7_new_fields_use_valid_enum_values(self) -> None:
        """TEST-AC-9.5.5.7 [P1]: New fields use valid enum string values.

        Given classification fields
        When inspecting their values
        Then they match expected enum value strings
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row that should classify clearly
        raw_row = {"entity": "GROUP", "metric": "EBITDA", "period": "Dec-24"}

        # Act: Classify
        enriched_row = classify_row(raw_row)

        # Assert: Values are valid enum strings
        valid_period_types = {"monthly_actual", "ytd_actual", "budget", "ytd_budget", "unknown"}
        valid_value_types = {"actual", "budget", "forecast", "variance", "unknown"}
        valid_entity_levels = {"consolidated", "company_only", "segment", "geographic", "unknown"}

        assert enriched_row["period_type"] in valid_period_types
        assert enriched_row["value_type"] in valid_value_types
        assert enriched_row["entity_level"] in valid_entity_levels

    def test_ac_5_1_8_extra_fields_preserved(self) -> None:
        """TEST-AC-9.5.5.8 [P1]: Extra/unknown fields are preserved.

        Given a row with non-standard fields
        When classify_row() is called
        Then those extra fields are preserved (extensible schema)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Row with extra fields
        raw_row = {
            "entity": "Test",
            "metric": "Revenue",
            "period": "Dec-24",
            "custom_field_1": "custom_value_1",
            "custom_field_2": 42,
            "nested_data": {"key": "value"},
        }

        # Act: Classify
        enriched_row = classify_row(raw_row)

        # Assert: Extra fields preserved
        assert enriched_row["custom_field_1"] == "custom_value_1"
        assert enriched_row["custom_field_2"] == 42
        assert enriched_row["nested_data"] == {"key": "value"}

    def test_ac_5_1_9_no_modification_of_input_row(self) -> None:
        """TEST-AC-9.5.5.9 [P1]: classify_row does not modify input row.

        Given an input row dict
        When classify_row() is called
        Then the original input dict is not modified (pure function)
        """
        from raglite.ingestion.classification.integration import classify_row

        # Arrange: Original row
        original_row = {"entity": "Test", "metric": "Revenue", "period": "Dec-24"}
        original_keys = set(original_row.keys())

        # Act: Classify
        classify_row(original_row)

        # Assert: Original row not modified
        assert set(original_row.keys()) == original_keys
        assert "period_type" not in original_row
        assert "value_type" not in original_row
        assert "entity_level" not in original_row
