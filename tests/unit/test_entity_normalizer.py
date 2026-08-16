"""Unit tests for entity_normalizer module (Phase 2.1).

Tests entity normalization, synonym expansion, and canonical entity mapping.
Addresses the 22-88% entity coverage variance identified in Story 5.0.7.
"""

from raglite.ingestion.entity_normalizer import (
    ENTITY_CANONICAL_MAP,
    expand_entity_synonyms,
    get_all_canonical_entities,
    get_entity_aliases,
    get_entity_ilike_pattern,
    normalize_entity,
)


class TestNormalizeEntity:
    """Test normalize_entity() function - core normalization logic."""

    def test_exact_match(self):
        """Test exact match normalization."""
        assert normalize_entity("PT") == "Portugal"
        assert normalize_entity("BR") == "Brazil"
        assert normalize_entity("TN") == "Tunisia"

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        assert normalize_entity("pt") == "Portugal"
        assert normalize_entity("PORTUGAL") == "Portugal"
        assert normalize_entity("brasil") == "Brazil"
        assert normalize_entity("BRAZIL") == "Brazil"

    def test_fuzzy_pattern_matching(self):
        """Test fuzzy pattern matching for partial matches."""
        assert normalize_entity("Portuguese Cement") == "Portugal"
        assert normalize_entity("Brazil Operations") == "Brazil"
        assert normalize_entity("Tunisian Cement") == "Tunisia"

    def test_group_variations(self):
        """Test group/consolidated entity variations."""
        assert normalize_entity("Conso") == "Group"
        assert normalize_entity("CONSO") == "Group"
        assert normalize_entity("Consolidated") == "Group"
        assert normalize_entity("Total") == "Group"
        assert normalize_entity("Secil GROUP") == "Group"

    def test_no_match_returns_original(self):
        """Test that unknown entities return original value."""
        assert normalize_entity("Unknown Corp") == "Unknown Corp"
        assert normalize_entity("Random Entity") == "Random Entity"

    def test_none_input(self):
        """Test None input handling."""
        assert normalize_entity(None) is None

    def test_empty_string(self):
        """Test empty string handling."""
        assert normalize_entity("") is None
        assert normalize_entity("   ") is None

    def test_whitespace_stripped(self):
        """Test whitespace stripping."""
        assert normalize_entity("  PT  ") == "Portugal"
        assert normalize_entity("\tBR\n") == "Brazil"

    def test_ready_mix_variations(self):
        """Test ready-mix entity variations."""
        assert normalize_entity("Ready-Mix") == "Ready-Mix"
        assert normalize_entity("RMC") == "Ready-Mix"
        assert normalize_entity("Ready Mix") == "Ready-Mix"

    def test_trading_variations(self):
        """Test trading entity variations."""
        assert normalize_entity("Trading") == "Trading"
        assert normalize_entity("Secil Trading") == "Trading"

    def test_cement_unit_variations(self):
        """Test cement unit variations."""
        assert normalize_entity("Cement Unit") == "Cement"
        assert normalize_entity("Cimento") == "Cement"

    def test_cape_verde_variations(self):
        """Test Cape Verde entity variations (multi-word entity)."""
        assert normalize_entity("CV") == "Cape Verde"
        assert normalize_entity("Cabo Verde") == "Cape Verde"
        assert normalize_entity("Cape Verde Cement") == "Cape Verde"


class TestGetEntityAliases:
    """Test get_entity_aliases() function."""

    def test_portugal_aliases(self):
        """Test Portugal alias retrieval."""
        aliases = get_entity_aliases("Portugal")
        assert "PT" in aliases
        assert "Portugal Cement" in aliases
        assert "Cimento de Portugal" in aliases
        assert "Secil Portugal" in aliases
        # Canonical name should be included
        assert "Portugal" in aliases

    def test_brazil_aliases(self):
        """Test Brazil alias retrieval."""
        aliases = get_entity_aliases("Brazil")
        assert "BR" in aliases
        assert "Brasil" in aliases
        assert "Brazil Cement" in aliases
        assert "Brazil" in aliases

    def test_group_aliases(self):
        """Test Group alias retrieval."""
        aliases = get_entity_aliases("Group")
        assert "Conso" in aliases
        assert "CONSO" in aliases
        assert "Consolidated" in aliases
        assert "Total" in aliases
        assert "Group" in aliases

    def test_unknown_entity_returns_canonical_only(self):
        """Test unknown entity returns only canonical name."""
        aliases = get_entity_aliases("UnknownEntity")
        assert aliases == ["UnknownEntity"]


class TestGetEntityIlikePattern:
    """Test get_entity_ilike_pattern() SQL generation."""

    def test_portugal_pattern(self):
        """Test Portugal ILIKE pattern generation.

        Story 6.10.3: Pattern uses %% for psycopg2 escaping by default.
        """
        pattern = get_entity_ilike_pattern("Portugal")
        assert "entity ILIKE ANY" in pattern
        # Pattern uses %% for psycopg2 compatibility (escapes to single % in SQL)
        assert "'%%Portugal%%'" in pattern
        assert "'%%PT%%'" in pattern
        assert "ARRAY[" in pattern

    def test_brazil_pattern(self):
        """Test Brazil ILIKE pattern generation.

        Story 6.10.3: Pattern uses %% for psycopg2 escaping by default.
        """
        pattern = get_entity_ilike_pattern("Brazil")
        assert "entity ILIKE ANY" in pattern
        # Pattern uses %% for psycopg2 compatibility (escapes to single % in SQL)
        assert "'%%Brazil%%'" in pattern
        assert "'%%BR%%'" in pattern
        assert "'%%Brasil%%'" in pattern

    def test_unknown_entity_fallback(self):
        """Test unknown entity generates ILIKE ANY pattern with canonical name.

        Story 6.10.3: Pattern uses %% for psycopg2 escaping by default.
        """
        pattern = get_entity_ilike_pattern("UnknownEntity")
        # Function returns ILIKE ANY pattern even for unknown entities (includes canonical name)
        assert "entity ILIKE ANY" in pattern
        # Pattern uses %% for psycopg2 compatibility (escapes to single % in SQL)
        assert "'%%UnknownEntity%%'" in pattern


class TestGetAllCanonicalEntities:
    """Test get_all_canonical_entities() function."""

    def test_returns_sorted_unique_list(self):
        """Test function returns sorted unique canonical entities."""
        entities = get_all_canonical_entities()
        assert isinstance(entities, list)
        assert len(entities) > 0
        # Check for expected entities
        assert "Portugal" in entities
        assert "Brazil" in entities
        assert "Tunisia" in entities
        assert "Group" in entities
        # Verify sorted
        assert entities == sorted(entities)
        # Verify unique
        assert len(entities) == len(set(entities))


class TestExpandEntitySynonyms:
    """Test expand_entity_synonyms() query expansion."""

    def test_portugal_expansion(self):
        """Test Portugal synonym expansion in query."""
        result = expand_entity_synonyms("What is revenue for Portugal?")
        assert "Portugal" in result
        assert "PT" in result
        assert "Portugal Cement" in result
        assert "Secil Portugal" in result

    def test_brazil_expansion(self):
        """Test Brazil synonym expansion in query."""
        result = expand_entity_synonyms("Show Brazil performance")
        assert "Brazil" in result
        assert "BR" in result
        assert "Brasil" in result

    def test_group_expansion(self):
        """Test Group synonym expansion in query."""
        result = expand_entity_synonyms("What is the group total?")
        assert "Group" in result
        assert "Conso" in result
        assert "Consolidated" in result
        assert "Total" in result

    def test_no_match_empty_list(self):
        """Test query with no entity matches returns empty list."""
        result = expand_entity_synonyms("Hello world random query")
        assert result == []

    def test_case_insensitive_matching(self):
        """Test case-insensitive query matching."""
        result = expand_entity_synonyms("PORTUGAL revenue")
        assert len(result) > 0
        assert "Portugal" in result

    def test_multiple_entities(self):
        """Test query with multiple entities."""
        result = expand_entity_synonyms("Compare Portugal and Brazil revenue")
        # Should have synonyms for both entities
        assert "Portugal" in result
        assert "PT" in result
        assert "Brazil" in result
        assert "BR" in result


class TestEntityCanonicalMapCompleteness:
    """Test ENTITY_CANONICAL_MAP data structure."""

    def test_map_not_empty(self):
        """Test canonical map is populated."""
        assert len(ENTITY_CANONICAL_MAP) > 0
        assert len(ENTITY_CANONICAL_MAP) >= 50  # Story spec: 50+ variations

    def test_country_variations_exist(self):
        """Test expected country variations exist."""
        # Portugal
        assert "PT" in ENTITY_CANONICAL_MAP
        assert ENTITY_CANONICAL_MAP["PT"] == "Portugal"
        # Brazil
        assert "BR" in ENTITY_CANONICAL_MAP
        assert ENTITY_CANONICAL_MAP["BR"] == "Brazil"
        # Tunisia
        assert "TN" in ENTITY_CANONICAL_MAP
        assert ENTITY_CANONICAL_MAP["TN"] == "Tunisia"

    def test_no_duplicate_keys(self):
        """Test no duplicate keys in mapping."""
        keys = list(ENTITY_CANONICAL_MAP.keys())
        assert len(keys) == len(set(keys))
