"""Unit tests for entity detection in Variable Cost extraction (Story 6.15).

ATDD RED PHASE: These tests define the expected behavior for entity detection.
Tests MUST FAIL initially because the implementation doesn't exist yet.

Tests cover:
- AC1: Entity detection identifies Portugal/Tunisia/Brazil context with >95% accuracy

Story 6.15: Entity-Specific Variable Cost Extraction
- Problem: Variable Cost MAPE is 41.43% (target <8%) due to multi-entity data mixing
- Solution: Implement entity detection to filter Portugal-only data and normalize to EUR/ton
"""


class TestDetectEntityFunction:
    """Test detect_entity() function for Variable Cost extraction (AC1).

    Given: A financial document chunk containing Variable Cost data with entity context
    When: The entity detection algorithm processes the chunk text
    Then: The algorithm correctly identifies Portugal/Tunisia/Brazil with >95% accuracy
    """

    def test_ac1_detect_portugal_explicit_keyword(self) -> None:
        """AC1: Detect Portugal from explicit 'Portugal' keyword.

        Given: Chunk text containing 'Portugal' keyword
        When: detect_entity() is called
        Then: Returns 'portugal' as the detected entity
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "Portugal | Variable Costs | (281,1) EUR/ton"
        result = detect_entity(text)
        assert result == "portugal", f"Expected 'portugal', got '{result}'"

    def test_ac1_detect_portugal_from_eur_ton_currency(self) -> None:
        """AC1: Detect Portugal from EUR/ton currency indicator.

        Given: Chunk text containing 'EUR/ton' without explicit country name
        When: detect_entity() is called
        Then: Returns 'portugal' (EUR/ton implies Portugal)
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "Variable Cost | EUR/ton | (281.1)"
        result = detect_entity(text)
        assert result == "portugal", f"Expected 'portugal', got '{result}'"

    def test_ac1_detect_portugal_from_portuguese_language(self) -> None:
        """AC1: Detect Portugal from Portuguese language text.

        Given: Chunk text containing Portuguese term 'Custos Variáveis'
        When: detect_entity() is called
        Then: Returns 'portugal' (Portuguese text implies Portugal)
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "Custos Variáveis | (260.5)"
        result = detect_entity(text)
        assert result == "portugal", f"Expected 'portugal', got '{result}'"

    def test_ac1_detect_portugal_pt_abbreviation(self) -> None:
        """AC1: Detect Portugal from 'PT' abbreviation.

        Given: Chunk text containing 'PT' abbreviation
        When: detect_entity() is called
        Then: Returns 'portugal'
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "PT Variable Cost (285.0) EUR/ton"
        result = detect_entity(text)
        assert result == "portugal", f"Expected 'portugal', got '{result}'"

    def test_ac1_detect_tunisia_explicit_keyword(self) -> None:
        """AC1: Detect Tunisia from explicit keyword.

        Given: Chunk text containing 'Tunisia' keyword
        When: detect_entity() is called
        Then: Returns 'tunisia' as the detected entity
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "Tunisia Variable Cost TND/ton"
        result = detect_entity(text)
        assert result == "tunisia", f"Expected 'tunisia', got '{result}'"

    def test_ac1_detect_tunisia_from_tnd_currency(self) -> None:
        """AC1: Detect Tunisia from TND currency indicator.

        Given: Chunk text containing 'TND' or 'TND/ton'
        When: detect_entity() is called
        Then: Returns 'tunisia' (TND implies Tunisia)
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "Variable Cost | TND/ton | (350.2)"
        result = detect_entity(text)
        assert result == "tunisia", f"Expected 'tunisia', got '{result}'"

    def test_ac1_detect_tunisia_tn_abbreviation(self) -> None:
        """AC1: Detect Tunisia from 'TN' abbreviation.

        Given: Chunk text containing 'TN' abbreviation
        When: detect_entity() is called
        Then: Returns 'tunisia'
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "TN Variable Costs (320.5) TND"
        result = detect_entity(text)
        assert result == "tunisia", f"Expected 'tunisia', got '{result}'"

    def test_ac1_detect_brazil_explicit_keyword(self) -> None:
        """AC1: Detect Brazil from explicit keyword.

        Given: Chunk text containing 'Brazil' keyword
        When: detect_entity() is called
        Then: Returns 'brazil' as the detected entity
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "Brazil Custos Variáveis BRL/ton"
        result = detect_entity(text)
        assert result == "brazil", f"Expected 'brazil', got '{result}'"

    def test_ac1_detect_brazil_from_brl_currency(self) -> None:
        """AC1: Detect Brazil from BRL currency indicator.

        Given: Chunk text containing 'BRL' or 'BRL/ton'
        When: detect_entity() is called
        Then: Returns 'brazil' (BRL implies Brazil)
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "Variable Cost | BRL/ton | (580.0)"
        result = detect_entity(text)
        assert result == "brazil", f"Expected 'brazil', got '{result}'"

    def test_ac1_detect_brazil_brasil_variant(self) -> None:
        """AC1: Detect Brazil from Portuguese spelling 'Brasil'.

        Given: Chunk text containing 'Brasil' (Portuguese spelling)
        When: detect_entity() is called
        Then: Returns 'brazil'
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "Brasil Custos Variáveis (600.0) BRL"
        result = detect_entity(text)
        assert result == "brazil", f"Expected 'brazil', got '{result}'"

    def test_ac1_detect_brazil_br_abbreviation(self) -> None:
        """AC1: Detect Brazil from 'BR' abbreviation.

        Given: Chunk text containing 'BR' abbreviation
        When: detect_entity() is called
        Then: Returns 'brazil'
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "BR Variable Cost (590.0) BRL/ton"
        result = detect_entity(text)
        assert result == "brazil", f"Expected 'brazil', got '{result}'"

    def test_ac1_unknown_entity_returns_none(self) -> None:
        """AC1: Return None for text without entity indicators.

        Given: Chunk text without any entity indicators
        When: detect_entity() is called
        Then: Returns None (unknown entity)
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        text = "Some random text without entity indicators"
        result = detect_entity(text)
        assert result is None, f"Expected None, got '{result}'"

    def test_ac1_case_insensitive_detection(self) -> None:
        """AC1: Entity detection is case-insensitive.

        Given: Chunk text with mixed case entity keywords
        When: detect_entity() is called
        Then: Correctly identifies entity regardless of case
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        test_cases = [
            ("PORTUGAL variable cost", "portugal"),
            ("portugal Variable Cost", "portugal"),
            ("TUNISIA variable cost", "tunisia"),
            ("BRAZIL variable cost", "brazil"),
        ]

        for text, expected in test_cases:
            result = detect_entity(text)
            assert result == expected, f"Text '{text}': expected '{expected}', got '{result}'"


class TestEntityPatternsConstant:
    """Test ENTITY_PATTERNS constant structure (AC1).

    Story 6.15: Validates the entity pattern dictionary exists and
    contains the required patterns for Portugal, Tunisia, and Brazil.
    """

    def test_entity_patterns_exists(self) -> None:
        """AC1: ENTITY_PATTERNS constant exists in timeseries_extract module.

        Given: timeseries_extract module
        When: Importing ENTITY_PATTERNS
        Then: Constant is accessible and is a dictionary
        """
        from raglite.forecasting.timeseries_extract import ENTITY_PATTERNS

        assert isinstance(ENTITY_PATTERNS, dict), "ENTITY_PATTERNS should be a dictionary"

    def test_entity_patterns_has_portugal(self) -> None:
        """AC1: ENTITY_PATTERNS contains Portugal patterns.

        Given: ENTITY_PATTERNS dictionary
        When: Checking for 'portugal' key
        Then: Key exists with list of patterns including 'Portugal', 'PT', 'EUR/ton'
        """
        from raglite.forecasting.timeseries_extract import ENTITY_PATTERNS

        assert "portugal" in ENTITY_PATTERNS, "ENTITY_PATTERNS missing 'portugal' key"

        portugal_patterns = ENTITY_PATTERNS["portugal"]
        assert isinstance(portugal_patterns, list), "Portugal patterns should be a list"
        assert "Portugal" in portugal_patterns, "Portugal patterns missing 'Portugal'"
        assert "PT" in portugal_patterns, "Portugal patterns missing 'PT'"
        # Note: Checking for "EUR/ton" or "EUR/m³" (one of them should be present)
        has_eur_pattern = "EUR/ton" in portugal_patterns or "EUR/m³" in portugal_patterns
        assert has_eur_pattern, "Portugal patterns missing EUR currency patterns"
        assert "Custos Variáveis" in portugal_patterns, (
            "Portugal patterns missing 'Custos Variáveis'"
        )

    def test_entity_patterns_has_tunisia(self) -> None:
        """AC1: ENTITY_PATTERNS contains Tunisia patterns.

        Given: ENTITY_PATTERNS dictionary
        When: Checking for 'tunisia' key
        Then: Key exists with list of patterns including 'Tunisia', 'TN', 'TND'
        """
        from raglite.forecasting.timeseries_extract import ENTITY_PATTERNS

        assert "tunisia" in ENTITY_PATTERNS, "ENTITY_PATTERNS missing 'tunisia' key"

        tunisia_patterns = ENTITY_PATTERNS["tunisia"]
        assert isinstance(tunisia_patterns, list), "Tunisia patterns should be a list"
        assert "Tunisia" in tunisia_patterns, "Tunisia patterns missing 'Tunisia'"
        assert "TN" in tunisia_patterns, "Tunisia patterns missing 'TN'"
        # Check for TND currency (may be "TND" or "TND/ton")
        has_tnd = "TND" in tunisia_patterns or "TND/ton" in tunisia_patterns
        assert has_tnd, "Tunisia patterns missing TND currency patterns"

    def test_entity_patterns_has_brazil(self) -> None:
        """AC1: ENTITY_PATTERNS contains Brazil patterns.

        Given: ENTITY_PATTERNS dictionary
        When: Checking for 'brazil' key
        Then: Key exists with list of patterns including 'Brazil', 'BR', 'BRL'
        """
        from raglite.forecasting.timeseries_extract import ENTITY_PATTERNS

        assert "brazil" in ENTITY_PATTERNS, "ENTITY_PATTERNS missing 'brazil' key"

        brazil_patterns = ENTITY_PATTERNS["brazil"]
        assert isinstance(brazil_patterns, list), "Brazil patterns should be a list"
        assert "Brazil" in brazil_patterns, "Brazil patterns missing 'Brazil'"
        assert "BR" in brazil_patterns, "Brazil patterns missing 'BR'"
        # Check for BRL currency (may be "BRL" or "BRL/ton")
        has_brl = "BRL" in brazil_patterns or "BRL/ton" in brazil_patterns
        assert has_brl, "Brazil patterns missing BRL currency patterns"
        assert "Brasil" in brazil_patterns, "Brazil patterns missing 'Brasil'"


class TestEntityDetectionAccuracy:
    """Test entity detection achieves >95% accuracy (AC1).

    Story 6.15: Validates that entity detection correctly identifies
    Portugal, Tunisia, and Brazil with >95% accuracy on test corpus.
    """

    def test_ac1_entity_detection_accuracy_above_95_percent(self) -> None:
        """AC1: Entity detection accuracy >95% on test corpus.

        Given: A corpus of labeled test chunks from financial documents
        When: detect_entity() is called on each chunk
        Then: Accuracy is >95% (correctly identifies >=19 of 20 test cases)
        """
        from raglite.forecasting.timeseries_extract import detect_entity

        # Test corpus with labeled entity context (chunk_text, expected_entity)
        test_corpus = [
            # Portugal test cases
            ("Portugal | Variable Costs | (281,1) EUR/ton", "portugal"),
            ("Variable Cost | EUR/ton | (281.1)", "portugal"),
            ("Custos Variáveis | EUR/ton | (260.5)", "portugal"),
            ("PT Variable Cost (285.0) EUR/ton", "portugal"),
            ("EUR/m³ Variable Costs Portugal (290.0)", "portugal"),
            # Tunisia test cases
            ("Tunisia Variable Cost TND/ton", "tunisia"),
            ("Variable Cost | TND/ton | (350.2)", "tunisia"),
            ("TN Variable Costs (320.5) TND", "tunisia"),
            ("Tunisie Coûts Variables TND/ton", "tunisia"),
            ("TND Variable Cost Tunisia (340.0)", "tunisia"),
            # Brazil test cases
            ("Brazil Custos Variáveis BRL/ton", "brazil"),
            ("Variable Cost | BRL/ton | (580.0)", "brazil"),
            ("BR Variable Cost (590.0) BRL/ton", "brazil"),
            ("Brasil Custos Variáveis (600.0) BRL", "brazil"),
            ("BRL/ton Variable Cost Brazil (620.0)", "brazil"),
            # Mixed/edge cases (should still detect correctly)
            ("Portugal Cement Variable Cost EUR/ton (275.0)", "portugal"),
            ("Tunisia Cement TND/ton Variable (310.0)", "tunisia"),
            ("Brazil Cement BRL/ton Variable (570.0)", "brazil"),
            ("Variable Costs PT EUR/ton (280.0)", "portugal"),
            ("Var Costs TN TND (330.0)", "tunisia"),
        ]

        correct = 0
        total = len(test_corpus)
        failed_cases = []

        for chunk_text, expected_entity in test_corpus:
            result = detect_entity(chunk_text)
            if result == expected_entity:
                correct += 1
            else:
                failed_cases.append((chunk_text, expected_entity, result))

        accuracy = (correct / total) * 100

        # Report failures for debugging
        if failed_cases:
            for text, expected, actual in failed_cases:
                print(f"FAILED: '{text[:50]}...' expected='{expected}' got='{actual}'")

        assert accuracy > 95, (
            f"Entity detection accuracy {accuracy:.1f}% (target >95%). "
            f"Failed {len(failed_cases)}/{total} cases."
        )
