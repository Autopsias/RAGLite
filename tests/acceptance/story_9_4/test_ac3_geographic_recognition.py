"""ATDD Tests for Story 9-4 AC3: Geographic Entity Recognition.

This module validates AC3 from the story:
- AC3.1: Country names recognized (Portugal, Tunisia, Brazil, Lebanon, etc.)
- AC3.2: Region names recognized (Iberia, Europe, MENA, etc.)
- AC3.3: Portuguese geographic keywords work (Pais, Regiao)
- AC3.4: Geographic takes precedence over generic names

Test IDs follow pattern: TEST-AC-{story}.{ac}.{test}
Example: TEST-AC-9.4.3.1 = Story 9.4, AC3, Test 1

TDD RED PHASE: These tests import from modules that DO NOT EXIST YET.
All tests MUST fail initially.
"""

import pytest

pytestmark = [
    pytest.mark.atdd,
]


class TestAC3GeographicEntityRecognition:
    """AC3: Geographic Entity Recognition.

    Given entity strings containing geographic names
    When classifying entity levels
    Then geographic patterns are correctly identified
    """

    def test_ac_3_3_1_country_name_tunisia(self) -> None:
        """TEST-AC-9.4.3.1 [P1]: Classify country name Tunisia.

        Scenario: Classify country name
          Given the entity string "Tunisia"
          When classify_entity_level() is called
          Then entity_level is GEOGRAPHIC
          And source is "entity_pattern"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("Tunisia")

        assert result.entity_level == EntityLevel.GEOGRAPHIC
        assert result.source == "entity_pattern"

    def test_ac_3_3_2_region_name_iberia(self) -> None:
        """TEST-AC-9.4.3.2 [P1]: Classify region name Iberia.

        Scenario: Classify region name
          Given the entity string "Iberia"
          When classify_entity_level() is called
          Then entity_level is GEOGRAPHIC
          And source is "entity_pattern"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("Iberia")

        assert result.entity_level == EntityLevel.GEOGRAPHIC
        assert result.source == "entity_pattern"

    def test_ac_3_3_3_portuguese_geographic_term(self) -> None:
        """TEST-AC-9.4.3.3 [P1]: Classify Portuguese geographic term.

        Scenario: Classify Portuguese geographic term
          Given the entity string "Pais: Portugal"
          When classify_entity_level() is called
          Then entity_level is GEOGRAPHIC
          And source is "entity_pattern"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("Pais: Portugal")

        assert result.entity_level == EntityLevel.GEOGRAPHIC
        assert result.source == "entity_pattern"

    def test_ac_3_3_4_common_countries_in_financial_data(self) -> None:
        """TEST-AC-9.4.3.4 [P1]: Classify common countries in financial data.

        Given common country names found in financial reports
        When classify_entity_level() is called
        Then all are classified as GEOGRAPHIC
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        countries = [
            "Portugal",
            "Spain",
            "Tunisia",
            "Brazil",
            "Lebanon",
            "Angola",
            "Mozambique",
            "France",
            "Germany",
        ]

        for country in countries:
            result = classify_entity_level(country)
            assert result.entity_level == EntityLevel.GEOGRAPHIC, (
                f"Country '{country}' expected GEOGRAPHIC, got {result.entity_level.value}"
            )

    def test_ac_3_3_5_common_regions_in_financial_data(self) -> None:
        """TEST-AC-9.4.3.5 [P1]: Classify common regions in financial data.

        Given common region names found in financial reports
        When classify_entity_level() is called
        Then all are classified as GEOGRAPHIC
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        regions = [
            "Iberia",
            "Europe",
            "MENA",
            "LATAM",
            "Americas",
            "Asia",
            "Africa",
        ]

        for region in regions:
            result = classify_entity_level(region)
            assert result.entity_level == EntityLevel.GEOGRAPHIC, (
                f"Region '{region}' expected GEOGRAPHIC, got {result.entity_level.value}"
            )

    def test_ac_3_3_6_portuguese_geographic_keywords(self) -> None:
        """TEST-AC-9.4.3.6 [P1]: Portuguese geographic keywords work.

        Given entities with Portuguese geographic keywords
        When classify_entity_level() is called
        Then they are classified as GEOGRAPHIC
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        portuguese_geo = [
            "Pais: Portugal",
            "Pais Portugal",
            "Regiao Sul",
            "Regiao: Iberia",
        ]

        for entity in portuguese_geo:
            result = classify_entity_level(entity)
            assert result.entity_level == EntityLevel.GEOGRAPHIC, (
                f"'{entity}' expected GEOGRAPHIC, got {result.entity_level.value}"
            )

    def test_ac_3_3_7_geographic_precedence_over_generic(self) -> None:
        """TEST-AC-9.4.3.7 [P1]: Geographic takes precedence over generic names.

        Given entity strings that could be generic but contain geographic names
        When classify_entity_level() is called
        Then geographic classification takes precedence
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        # "Portugal" embedded in longer strings should still be GEOGRAPHIC
        geo_entities = [
            "Portugal Operations",
            "Tunisia Business",
            "Europe Region",
            "Iberia Market",
        ]

        for entity in geo_entities:
            result = classify_entity_level(entity)
            assert result.entity_level == EntityLevel.GEOGRAPHIC, (
                f"'{entity}' expected GEOGRAPHIC, got {result.entity_level.value}"
            )

    def test_ac_3_3_8_case_insensitive_geographic(self) -> None:
        """TEST-AC-9.4.3.8 [P1]: Geographic matching is case-insensitive.

        Given geographic names in various cases
        When classify_entity_level() is called
        Then all are classified as GEOGRAPHIC
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        case_variants = [
            "PORTUGAL",
            "portugal",
            "Portugal",
            "EUROPE",
            "europe",
            "Europe",
            "IBERIA",
            "iberia",
        ]

        for entity in case_variants:
            result = classify_entity_level(entity)
            assert result.entity_level == EntityLevel.GEOGRAPHIC, (
                f"'{entity}' expected GEOGRAPHIC, got {result.entity_level.value}"
            )
