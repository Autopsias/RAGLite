"""ATDD Tests for Story 9-4 AC2: Table Context Integration.

This module validates AC2 from the story:
- AC2.1: Table title "GROUP Financial Statements" classifies entities as CONSOLIDATED
- AC2.2: Table title "Portugal Operations" classifies entities as GEOGRAPHIC
- AC2.3: Table title "Cement Division Results" classifies entities as SEGMENT
- AC2.4: Entity pattern overrides conflicting table title when entity is more specific

Test IDs follow pattern: TEST-AC-{story}.{ac}.{test}
Example: TEST-AC-9.4.2.1 = Story 9.4, AC2, Test 1

TDD RED PHASE: These tests import from modules that DO NOT EXIST YET.
All tests MUST fail initially.
"""

import pytest

pytestmark = [
    pytest.mark.atdd,
]


class TestAC2TableContextIntegration:
    """AC2: Table Context Integration.

    Given an entity string with a table title/caption for context
    When classifying entity levels with table_title parameter
    Then table title provides context for classification
    """

    def test_ac_2_2_1_table_title_group_financial_statements(self) -> None:
        """TEST-AC-9.4.2.1 [P0]: Table title "GROUP Financial Statements" provides CONSOLIDATED context.

        Scenario: Table title provides consolidated context
          Given the entity string "Revenue"
          And table_title is "GROUP Financial Statements"
          When classify_entity_level() is called
          Then entity_level is CONSOLIDATED
          And source is "table_title"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("Revenue", table_title="GROUP Financial Statements")

        assert result.entity_level == EntityLevel.CONSOLIDATED
        assert result.source == "table_title"

    def test_ac_2_2_2_table_title_portugal_operations(self) -> None:
        """TEST-AC-9.4.2.2 [P1]: Table title "Portugal Operations" provides GEOGRAPHIC context.

        Given the entity string "Revenue"
        And table_title is "Portugal Operations"
        When classify_entity_level() is called
        Then entity_level is GEOGRAPHIC
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("Revenue", table_title="Portugal Operations")

        assert result.entity_level == EntityLevel.GEOGRAPHIC

    def test_ac_2_2_3_table_title_cement_division_results(self) -> None:
        """TEST-AC-9.4.2.3 [P1]: Table title "Cement Division Results" provides SEGMENT context.

        Given the entity string "Revenue"
        And table_title is "Cement Division Results"
        When classify_entity_level() is called
        Then entity_level is SEGMENT
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("Revenue", table_title="Cement Division Results")

        assert result.entity_level == EntityLevel.SEGMENT

    def test_ac_2_2_4_entity_pattern_overrides_table_title(self) -> None:
        """TEST-AC-9.4.2.4 [P0]: Entity pattern overrides conflicting table title.

        Scenario: Entity pattern overrides table title
          Given the entity string "SECIL Portugal SA"
          And table_title is "GROUP Financial Statements"
          When classify_entity_level() is called
          Then entity_level is COMPANY_ONLY
          And source is "entity_pattern"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level(
            "SECIL Portugal SA", table_title="GROUP Financial Statements"
        )

        assert result.entity_level == EntityLevel.COMPANY_ONLY
        assert result.source == "entity_pattern"

    def test_ac_2_2_5_table_title_consolidated_variations(self) -> None:
        """TEST-AC-9.4.2.5 [P1]: Various consolidated table title patterns.

        Given various table titles indicating consolidated data
        When classify_entity_level() is called with generic entity
        Then entity_level is CONSOLIDATED
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        table_titles = [
            "GROUP Financial Statements",
            "Consolidated Report",
            "Group Results",
            "Total Group Summary",
        ]

        for title in table_titles:
            result = classify_entity_level("Revenue", table_title=title)
            assert result.entity_level == EntityLevel.CONSOLIDATED, (
                f"Table title '{title}' expected CONSOLIDATED, got {result.entity_level.value}"
            )

    def test_ac_2_2_6_table_title_geographic_variations(self) -> None:
        """TEST-AC-9.4.2.6 [P1]: Various geographic table title patterns.

        Given various table titles indicating geographic data
        When classify_entity_level() is called with generic entity
        Then entity_level is GEOGRAPHIC
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        table_titles = [
            "Portugal Operations",
            "Tunisia Results",
            "Iberia Summary",
            "Europe Performance",
        ]

        for title in table_titles:
            result = classify_entity_level("Revenue", table_title=title)
            assert result.entity_level == EntityLevel.GEOGRAPHIC, (
                f"Table title '{title}' expected GEOGRAPHIC, got {result.entity_level.value}"
            )

    def test_ac_2_2_7_empty_table_title_uses_entity_only(self) -> None:
        """TEST-AC-9.4.2.7 [P1]: Empty table title falls back to entity pattern.

        Given an entity string with empty/None table_title
        When classify_entity_level() is called
        Then classification uses entity pattern only
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        # With None table_title
        result1 = classify_entity_level("GROUP", table_title=None)
        assert result1.entity_level == EntityLevel.CONSOLIDATED

        # With empty string table_title
        result2 = classify_entity_level("Portugal", table_title="")
        assert result2.entity_level == EntityLevel.GEOGRAPHIC

    def test_ac_2_2_8_specific_entity_overrides_generic_table(self) -> None:
        """TEST-AC-9.4.2.8 [P1]: Specific entity pattern always takes precedence.

        Given specific entity patterns and generic table titles
        When classify_entity_level() is called
        Then entity pattern takes precedence
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        # Company entity with geographic table title
        result1 = classify_entity_level("SECIL SA", table_title="Portugal Operations")
        assert result1.entity_level == EntityLevel.COMPANY_ONLY, (
            "Company entity should override geographic table title"
        )

        # Geographic entity with consolidated table title
        result2 = classify_entity_level("Tunisia", table_title="GROUP Financial Statements")
        assert result2.entity_level == EntityLevel.GEOGRAPHIC, (
            "Geographic entity should override consolidated table title"
        )
