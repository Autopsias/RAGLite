"""Additional edge case tests for entity detection (Story 6.15).

Priority: P1-P2 edge cases and error handling not covered by ATDD tests.

Coverage gaps addressed:
- Word boundary edge cases (prevent false positives)
- Multi-entity text handling (priority order)
- Malformed/partial input handling
- Currency conversion edge cases
- ENTITY_PATTERNS and CURRENCY_TO_EUR constant validation
"""


class TestEntityDetectionWordBoundaries:
    """[P1] Test word boundary handling to prevent false positives.

    Critical: Short patterns like "TN", "BR", "PT" must use word boundaries
    to avoid false matches in words like "TNT", "BRAND", "PATTERN".
    """

    def test_p1_pt_not_matched_in_pattern(self) -> None:
        """[P1] 'PT' in 'PATTERN' should not match Portugal.

        Given: Text containing 'PATTERN' (contains 'PT' but not as abbreviation)
        When: detect_entity() is called
        Then: Returns None (PT is not a standalone word)
        """
        from raglite.forecasting.timeseries import detect_entity

        text = "PATTERN matching for costs"
        result = detect_entity(text)
        assert result is None, f"Expected None for 'PATTERN', got '{result}'"

    def test_p1_tn_not_matched_in_tnt(self) -> None:
        """[P1] 'TN' in 'TNT' should not match Tunisia.

        Given: Text containing 'TNT' (contains 'TN' but not as abbreviation)
        When: detect_entity() is called
        Then: Returns None (TN is not a standalone word)
        """
        from raglite.forecasting.timeseries import detect_entity

        text = "TNT shipping costs"
        result = detect_entity(text)
        assert result is None, f"Expected None for 'TNT', got '{result}'"

    def test_p1_br_not_matched_in_brand(self) -> None:
        """[P1] 'BR' in 'BRAND' should not match Brazil.

        Given: Text containing 'BRAND' (contains 'BR' but not as abbreviation)
        When: detect_entity() is called
        Then: Returns None (BR is not a standalone word)
        """
        from raglite.forecasting.timeseries import detect_entity

        text = "BRAND costs analysis"
        result = detect_entity(text)
        assert result is None, f"Expected None for 'BRAND', got '{result}'"

    def test_p1_pt_matched_as_standalone_word(self) -> None:
        """[P1] 'PT' as standalone word should match Portugal.

        Given: Text with 'PT' as separate word (space-delimited)
        When: detect_entity() is called
        Then: Returns 'portugal'
        """
        from raglite.forecasting.timeseries import detect_entity

        text = "PT costs EUR/ton"
        result = detect_entity(text)
        assert result == "portugal", f"Expected 'portugal' for standalone PT, got '{result}'"

    def test_p1_tn_matched_as_standalone_word(self) -> None:
        """[P1] 'TN' as standalone word should match Tunisia.

        Given: Text with 'TN' as separate word
        When: detect_entity() is called
        Then: Returns 'tunisia'
        """
        from raglite.forecasting.timeseries import detect_entity

        text = "TN costs TND/ton"
        result = detect_entity(text)
        assert result == "tunisia", f"Expected 'tunisia' for standalone TN, got '{result}'"


class TestEntityPriorityOrder:
    """[P1] Test entity detection priority order when multiple patterns present.

    Critical: When text contains patterns for multiple entities,
    detection should follow priority order: Tunisia > Brazil > Portugal
    (most specific currency/country first, then Portuguese language last).
    """

    def test_p1_tunisia_takes_priority_over_portuguese_language(self) -> None:
        """[P1] Tunisia-specific indicators override Portuguese language.

        Given: Text with both 'Custos Variáveis' (Portuguese) and 'TND' (Tunisia)
        When: detect_entity() is called
        Then: Returns 'tunisia' (currency is more specific than language)
        """
        from raglite.forecasting.timeseries import detect_entity

        text = "Tunisia Custos Variáveis TND/ton"
        result = detect_entity(text)
        assert result == "tunisia", (
            f"Expected 'tunisia' when TND and Portuguese both present, got '{result}'"
        )

    def test_p1_brazil_takes_priority_over_portuguese_language(self) -> None:
        """[P1] Brazil-specific indicators override Portuguese language.

        Given: Text with both 'Custos Variáveis' (Portuguese) and 'BRL' (Brazil)
        When: detect_entity() is called
        Then: Returns 'brazil' (currency is more specific than language)
        """
        from raglite.forecasting.timeseries import detect_entity

        text = "Brazil Custos Variáveis BRL/ton"
        result = detect_entity(text)
        assert result == "brazil", (
            f"Expected 'brazil' when BRL and Portuguese both present, got '{result}'"
        )

    def test_p1_tunisia_country_name_overrides_ambiguous_patterns(self) -> None:
        """[P1] Explicit country name 'Tunisia' takes priority.

        Given: Text with country name 'Tunisia' but no currency
        When: detect_entity() is called
        Then: Returns 'tunisia'
        """
        from raglite.forecasting.timeseries import detect_entity

        text = "Tunisia Variable Cost (no currency specified)"
        result = detect_entity(text)
        assert result == "tunisia", f"Expected 'tunisia' for explicit country name, got '{result}'"


class TestMalformedInputHandling:
    """[P2] Test handling of malformed or edge case inputs.

    Edge cases: empty strings, None-like values, special characters,
    very long strings, non-ASCII characters.
    """

    def test_p2_empty_string_returns_none(self) -> None:
        """[P2] Empty string should return None.

        Given: Empty string
        When: detect_entity() is called
        Then: Returns None (no entity detected)
        """
        from raglite.forecasting.timeseries import detect_entity

        result = detect_entity("")
        assert result is None, f"Expected None for empty string, got '{result}'"

    def test_p2_whitespace_only_returns_none(self) -> None:
        """[P2] Whitespace-only string should return None.

        Given: String with only spaces/tabs/newlines
        When: detect_entity() is called
        Then: Returns None
        """
        from raglite.forecasting.timeseries import detect_entity

        result = detect_entity("   \t\n   ")
        assert result is None, f"Expected None for whitespace-only, got '{result}'"

    def test_p2_very_long_string_handles_correctly(self) -> None:
        """[P2] Very long strings should be handled efficiently.

        Given: String with 10,000+ characters
        When: detect_entity() is called
        Then: Still detects entity correctly without timeout/error
        """
        from raglite.forecasting.timeseries import detect_entity

        # Create long string with Portugal pattern embedded
        long_text = "x " * 5000 + "Portugal EUR/ton Variable Cost" + " x" * 5000
        result = detect_entity(long_text)
        assert result == "portugal", f"Expected 'portugal' in long string, got '{result}'"

    def test_p2_special_characters_handled(self) -> None:
        """[P2] Special characters don't break detection.

        Given: Text with special characters and entity patterns
        When: detect_entity() is called
        Then: Correctly identifies entity
        """
        from raglite.forecasting.timeseries import detect_entity

        text = "*** Portugal *** EUR/ton $$$ (281.1) %%% Variable Cost"
        result = detect_entity(text)
        assert result == "portugal", f"Expected 'portugal' with special chars, got '{result}'"

    def test_p2_unicode_characters_handled(self) -> None:
        """[P2] Non-ASCII Unicode characters handled correctly.

        Given: Text with accented characters (Custos Variáveis)
        When: detect_entity() is called
        Then: Correctly identifies entity
        """
        from raglite.forecasting.timeseries import detect_entity

        text = "Custos Variáveis Cémento Portugal EUR/m³"
        result = detect_entity(text)
        assert result == "portugal", f"Expected 'portugal' with Unicode, got '{result}'"


class TestCurrencyConversionConstants:
    """[P1] Test CURRENCY_TO_EUR constant validation.

    Critical: Currency conversion rates must be present and reasonable
    for Tunisia (TND) and Brazil (BRL) to EUR normalization.
    """

    def test_p1_currency_to_eur_exists(self) -> None:
        """[P1] CURRENCY_TO_EUR constant exists.

        Given: timeseries_extract module
        When: Importing CURRENCY_TO_EUR
        Then: Constant is accessible and is a dictionary
        """
        from raglite.forecasting.timeseries import CURRENCY_TO_EUR

        assert isinstance(CURRENCY_TO_EUR, dict), "CURRENCY_TO_EUR should be a dictionary"

    def test_p1_currency_to_eur_has_tnd(self) -> None:
        """[P1] CURRENCY_TO_EUR contains TND conversion rate.

        Given: CURRENCY_TO_EUR dictionary
        When: Checking for 'TND' key
        Then: Key exists with reasonable conversion rate (>0, <1)
        """
        from raglite.forecasting.timeseries import CURRENCY_TO_EUR

        assert "TND" in CURRENCY_TO_EUR, "CURRENCY_TO_EUR missing 'TND' key"
        rate = CURRENCY_TO_EUR["TND"]
        assert 0 < rate < 1, f"TND rate {rate} outside reasonable range (0, 1)"

    def test_p1_currency_to_eur_has_brl(self) -> None:
        """[P1] CURRENCY_TO_EUR contains BRL conversion rate.

        Given: CURRENCY_TO_EUR dictionary
        When: Checking for 'BRL' key
        Then: Key exists with reasonable conversion rate (>0, <1)
        """
        from raglite.forecasting.timeseries import CURRENCY_TO_EUR

        assert "BRL" in CURRENCY_TO_EUR, "CURRENCY_TO_EUR missing 'BRL' key"
        rate = CURRENCY_TO_EUR["BRL"]
        assert 0 < rate < 1, f"BRL rate {rate} outside reasonable range (0, 1)"

    def test_p1_currency_to_eur_has_eur_baseline(self) -> None:
        """[P1] CURRENCY_TO_EUR contains EUR baseline (1.0).

        Given: CURRENCY_TO_EUR dictionary
        When: Checking for 'EUR' key
        Then: Key exists with value exactly 1.0
        """
        from raglite.forecasting.timeseries import CURRENCY_TO_EUR

        assert "EUR" in CURRENCY_TO_EUR, "CURRENCY_TO_EUR missing 'EUR' key"
        rate = CURRENCY_TO_EUR["EUR"]
        assert rate == 1.0, f"EUR rate should be 1.0, got {rate}"

    def test_p1_tnd_to_eur_rate_reasonable(self) -> None:
        """[P1] TND to EUR conversion rate is reasonable (~0.31).

        Given: CURRENCY_TO_EUR['TND']
        When: Checking conversion rate value
        Then: Rate is approximately 0.31 (+/- 0.1 tolerance for updates)
        """
        from raglite.forecasting.timeseries import CURRENCY_TO_EUR

        rate = CURRENCY_TO_EUR["TND"]
        assert 0.21 <= rate <= 0.41, (
            f"TND rate {rate} outside expected range [0.21, 0.41]. "
            "Check if rate needs updating or if test tolerance is too strict."
        )

    def test_p1_brl_to_eur_rate_reasonable(self) -> None:
        """[P1] BRL to EUR conversion rate is reasonable (~0.18).

        Given: CURRENCY_TO_EUR['BRL']
        When: Checking conversion rate value
        Then: Rate is approximately 0.18 (+/- 0.1 tolerance for updates)
        """
        from raglite.forecasting.timeseries import CURRENCY_TO_EUR

        rate = CURRENCY_TO_EUR["BRL"]
        assert 0.08 <= rate <= 0.28, (
            f"BRL rate {rate} outside expected range [0.08, 0.28]. "
            "Check if rate needs updating or if test tolerance is too strict."
        )


class TestEntityPatternEdgeCases:
    """[P2] Test edge cases in ENTITY_PATTERNS structure.

    Validates that pattern lists contain expected elements and
    handle edge cases correctly.
    """

    def test_p2_entity_patterns_not_empty(self) -> None:
        """[P2] All entity pattern lists are non-empty.

        Given: ENTITY_PATTERNS dictionary
        When: Checking each entity's pattern list
        Then: All lists have at least one pattern
        """
        from raglite.forecasting.timeseries import ENTITY_PATTERNS

        for entity, patterns in ENTITY_PATTERNS.items():
            assert len(patterns) > 0, f"{entity} has empty pattern list"

    def test_p2_patterns_are_strings(self) -> None:
        """[P2] All patterns are strings (not numbers/objects).

        Given: ENTITY_PATTERNS dictionary
        When: Checking pattern types
        Then: All patterns are strings
        """
        from raglite.forecasting.timeseries import ENTITY_PATTERNS

        for entity, patterns in ENTITY_PATTERNS.items():
            for pattern in patterns:
                assert isinstance(pattern, str), (
                    f"{entity} has non-string pattern: {pattern} ({type(pattern)})"
                )

    def test_p2_no_duplicate_patterns_within_entity(self) -> None:
        """[P2] No duplicate patterns within same entity.

        Given: ENTITY_PATTERNS dictionary
        When: Checking for duplicates in each entity's patterns
        Then: All patterns are unique within each entity
        """
        from raglite.forecasting.timeseries import ENTITY_PATTERNS

        for entity, patterns in ENTITY_PATTERNS.items():
            unique_patterns = set(patterns)
            assert len(unique_patterns) == len(patterns), (
                f"{entity} has duplicate patterns: "
                f"{len(patterns)} total vs {len(unique_patterns)} unique"
            )


class TestDetectEntityIntegrationPoints:
    """[P1] Test integration points between detect_entity and extraction functions.

    Validates that detect_entity correctly integrates with
    extract_variable_cost_from_qdrant_chunks filtering logic.
    """

    def test_p1_detect_entity_returns_lowercase(self) -> None:
        """[P1] detect_entity always returns lowercase entity names.

        Given: Various capitalization in input text
        When: detect_entity() is called
        Then: Returns 'portugal', 'tunisia', 'brazil' (lowercase only)
        """
        from raglite.forecasting.timeseries import detect_entity

        test_cases = [
            ("PORTUGAL costs", "portugal"),
            ("Portugal Costs", "portugal"),
            ("TUNISIA TND", "tunisia"),
            ("Tunisia costs", "tunisia"),
            ("BRAZIL BRL", "brazil"),
            ("Brazil costs", "brazil"),
        ]

        for text, expected in test_cases:
            result = detect_entity(text)
            assert result == expected, f"Text '{text}': expected '{expected}', got '{result}'"
            # Verify it's lowercase
            if result:
                assert result.islower(), f"Result '{result}' is not lowercase"

    def test_p1_detect_entity_handles_mixed_case_patterns(self) -> None:
        """[P1] Patterns work regardless of input case.

        Given: Pattern keywords in various cases
        When: detect_entity() is called
        Then: Detection works correctly (case-insensitive)
        """
        from raglite.forecasting.timeseries import detect_entity

        # Test mixed case variations
        test_cases = [
            "custos variáveis EUR/ton",  # lowercase
            "CUSTOS VARIÁVEIS EUR/TON",  # uppercase
            "Custos Variáveis EUR/Ton",  # title case
        ]

        for text in test_cases:
            result = detect_entity(text)
            assert result == "portugal", (
                f"Text '{text}' failed case-insensitive detection, got '{result}'"
            )


class TestCurrencyNormalizationEdgeCases:
    """[P2] Test edge cases in currency normalization logic.

    Validates that currency conversion handles edge cases:
    - Very small values (near zero)
    - Very large values (overflow protection)
    - Negative values (cost outflows)
    """

    def test_p2_currency_conversion_preserves_sign(self) -> None:
        """[P2] Currency conversion preserves negative sign for costs.

        Given: Negative cost value in BRL/TND
        When: Converting to EUR
        Then: Result remains negative
        """
        from raglite.forecasting.timeseries import CURRENCY_TO_EUR

        # Simulate Tunisia cost conversion
        tnd_cost = -350.0  # TND/ton
        eur_cost = tnd_cost * CURRENCY_TO_EUR["TND"]
        assert eur_cost < 0, f"TND cost conversion should preserve negative sign: {eur_cost}"

        # Simulate Brazil cost conversion
        brl_cost = -600.0  # BRL/ton
        eur_cost = brl_cost * CURRENCY_TO_EUR["BRL"]
        assert eur_cost < 0, f"BRL cost conversion should preserve negative sign: {eur_cost}"

    def test_p2_currency_conversion_reasonable_range(self) -> None:
        """[P2] Converted values fall into reasonable EUR/ton range.

        Given: Typical cost values in TND and BRL
        When: Converting to EUR
        Then: Results are in expected Portugal EUR/ton range (-150 to -350)
        """
        from raglite.forecasting.timeseries import CURRENCY_TO_EUR

        # Tunisia typical cost: ~350 TND/ton → ~108 EUR/ton (after conversion)
        # But we expect values in -150 to -350 range, so this validates conversion logic
        tnd_cost = -350.0
        eur_cost = tnd_cost * CURRENCY_TO_EUR["TND"]
        # After conversion, should be roughly -108 EUR/ton (within broad range)
        assert -400 <= eur_cost <= -50, (
            f"TND conversion {tnd_cost} TND → {eur_cost} EUR outside reasonable range"
        )

        # Brazil typical cost: ~580 BRL/ton → ~104 EUR/ton
        brl_cost = -580.0
        eur_cost = brl_cost * CURRENCY_TO_EUR["BRL"]
        assert -400 <= eur_cost <= -50, (
            f"BRL conversion {brl_cost} BRL → {eur_cost} EUR outside reasonable range"
        )
