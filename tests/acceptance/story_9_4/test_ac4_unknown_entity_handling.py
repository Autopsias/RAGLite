"""ATDD Tests for Story 9-4 AC4: Unknown Entity Handling.

This module validates AC4 from the story:
- AC4.1: Empty strings return UNKNOWN with source "empty"
- AC4.2: "N/A", "None", "null" markers return UNKNOWN with source "unknown_marker"
- AC4.3: Ambiguous patterns (numbers only, generic text) return UNKNOWN
- AC4.4: Classification never raises exceptions for malformed inputs

Test IDs follow pattern: TEST-AC-{story}.{ac}.{test}
Example: TEST-AC-9.4.4.1 = Story 9.4, AC4, Test 1

TDD RED PHASE: These tests import from modules that DO NOT EXIST YET.
All tests MUST fail initially.
"""

import pytest

pytestmark = [
    pytest.mark.atdd,
]


class TestAC4UnknownEntityHandling:
    """AC4: Unknown Entity Handling.

    Given entity strings that cannot be classified
    When classifying invalid or ambiguous inputs
    Then they are handled gracefully as UNKNOWN
    """

    def test_ac_4_4_1_empty_string_returns_unknown(self) -> None:
        """TEST-AC-9.4.4.1 [P0]: Empty strings return UNKNOWN with source "empty".

        Scenario: Empty string returns unknown
          Given the entity string ""
          When classify_entity_level() is called
          Then entity_level is UNKNOWN
          And source is "empty"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("")

        assert result.entity_level == EntityLevel.UNKNOWN
        assert result.source == "empty"

    def test_ac_4_4_2_whitespace_only_returns_unknown(self) -> None:
        """TEST-AC-9.4.4.2 [P0]: Whitespace-only strings return UNKNOWN with source "empty".

        Given whitespace-only entity strings
        When classify_entity_level() is called
        Then entity_level is UNKNOWN and source is "empty"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        whitespace_inputs = ["   ", "\t", "\n", "\t\n  "]

        for entity in whitespace_inputs:
            result = classify_entity_level(entity)
            assert result.entity_level == EntityLevel.UNKNOWN, (
                f"Whitespace '{repr(entity)}' expected UNKNOWN"
            )
            assert result.source == "empty", (
                f"Whitespace '{repr(entity)}' expected source 'empty'"
            )

    def test_ac_4_4_3_na_marker_returns_unknown(self) -> None:
        """TEST-AC-9.4.4.3 [P0]: N/A marker returns UNKNOWN with source "unknown_marker".

        Scenario: N/A marker returns unknown
          Given the entity string "N/A"
          When classify_entity_level() is called
          Then entity_level is UNKNOWN
          And source is "unknown_marker"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("N/A")

        assert result.entity_level == EntityLevel.UNKNOWN
        assert result.source == "unknown_marker"

    def test_ac_4_4_4_various_na_markers_return_unknown(self) -> None:
        """TEST-AC-9.4.4.4 [P0]: Various N/A markers return UNKNOWN.

        Given various N/A marker strings
        When classify_entity_level() is called
        Then all return UNKNOWN with source "unknown_marker"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        na_markers = ["N/A", "None", "null", "n/a", "NONE", "NULL", "-", "--"]

        for marker in na_markers:
            result = classify_entity_level(marker)
            assert result.entity_level == EntityLevel.UNKNOWN, (
                f"N/A marker '{marker}' expected UNKNOWN, got {result.entity_level.value}"
            )
            assert result.source == "unknown_marker", (
                f"N/A marker '{marker}' expected source 'unknown_marker', got {result.source}"
            )

    def test_ac_4_4_5_ambiguous_numeric_returns_unknown(self) -> None:
        """TEST-AC-9.4.4.5 [P1]: Ambiguous numeric returns UNKNOWN.

        Scenario: Ambiguous numeric returns unknown
          Given the entity string "12345"
          When classify_entity_level() is called
          Then entity_level is UNKNOWN
          And source is "ambiguous"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("12345")

        assert result.entity_level == EntityLevel.UNKNOWN
        assert result.source == "ambiguous"

    def test_ac_4_4_6_ambiguous_patterns_return_unknown(self) -> None:
        """TEST-AC-9.4.4.6 [P1]: Ambiguous patterns return UNKNOWN.

        Given entity strings with ambiguous patterns
        When classify_entity_level() is called
        Then all return UNKNOWN
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        ambiguous_inputs = [
            "12345",
            "123.456",
            "XYZ",
            "ABC123",
            "???",
            "##@@!!",
        ]

        for entity in ambiguous_inputs:
            result = classify_entity_level(entity)
            assert result.entity_level == EntityLevel.UNKNOWN, (
                f"Ambiguous '{entity}' expected UNKNOWN, got {result.entity_level.value}"
            )

    def test_ac_4_4_7_no_exceptions_for_malformed_inputs(self) -> None:
        """TEST-AC-9.4.4.7 [P0]: No exceptions raised for malformed inputs.

        Given various malformed entity strings
        When classify_entity_level() is called
        Then no exceptions are raised and all return valid results
        """
        from raglite.ingestion.classification import classify_entity_level

        malformed_inputs = [
            "",
            "   ",
            "N/A",
            "None",
            "null",
            "12345",
            "??##$$",
            "completely random text",
            "\x00\x01\x02",  # Non-printable characters
            "a" * 10000,  # Very long string
        ]

        for entity in malformed_inputs:
            try:
                result = classify_entity_level(entity)
                # Just verify we got a result without exception
                assert result is not None
                assert hasattr(result, "entity_level")
                assert hasattr(result, "source")
            except Exception as e:
                pytest.fail(f"Exception raised for input '{repr(entity)}': {e}")

    def test_ac_4_4_8_conservative_approach_defaults_unknown(self) -> None:
        """TEST-AC-9.4.4.8 [P1]: Conservative approach defaults to UNKNOWN.

        Given entity strings that don't match any pattern
        When classify_entity_level() is called
        Then they default to UNKNOWN (never assume)
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        # Generic business terms that aren't specific patterns
        generic_entities = [
            "Revenue",
            "Costs",
            "Profit",
            "Assets",
            "Liabilities",
        ]

        for entity in generic_entities:
            result = classify_entity_level(entity)
            # Without table context, generic terms should be UNKNOWN
            # (conservative approach - don't assume)
            assert result.entity_level == EntityLevel.UNKNOWN, (
                f"Generic term '{entity}' should default to UNKNOWN, got {result.entity_level.value}"
            )
