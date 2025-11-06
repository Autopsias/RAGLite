"""Unit tests for query preprocessing (raglite/retrieval/query_preprocessing.py).

Test Coverage:
    - Stopword removal from queries
    - Temporal filter extraction (month+year patterns)
    - Keyword extraction for table search
    - Date normalization (August 2025 → Aug-25%)
    - Edge cases (empty queries, no temporal info, multiple dates)

Priority: P1 (Critical for SQL routing accuracy)
"""

import pytest

from raglite.retrieval.query_preprocessing import (
    MONTH_MAPPINGS,
    STOPWORDS,
    _extract_temporal_filters,
    preprocess_query_for_table_search,
)


class TestQueryPreprocessing:
    """Test query preprocessing for table search."""

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_preprocess_removes_stopwords(self):
        """Preprocess query - should remove common stopwords."""
        # GIVEN: Query with stopwords
        query = "What is the revenue for the company"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: Stopwords removed, business terms preserved
        assert "what" not in keywords.lower()
        assert "is" not in keywords.lower()
        assert "the" not in keywords.lower()
        assert "for" not in keywords.lower()
        assert "revenue" in keywords
        assert "company" in keywords

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_preprocess_extracts_temporal_filters(self):
        """Preprocess query - should extract temporal filters."""
        # GIVEN: Query with month and year
        query = "What is the EBITDA margin in August 2025?"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: Temporal filter extracted
        assert filters is not None
        assert "reporting_period" in filters
        assert filters["reporting_period"] == "Aug-25%"

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_preprocess_removes_temporal_terms_from_keywords(self):
        """Preprocess query - should remove temporal terms from keywords."""
        # GIVEN: Query with temporal information
        query = "EBITDA margin August 2025"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: Temporal terms removed from keywords
        assert "august" not in keywords.lower()
        assert "2025" not in keywords
        assert "EBITDA" in keywords
        assert "margin" in keywords

    @pytest.mark.unit
    @pytest.mark.priority("P0")
    def test_preprocess_preserves_business_term_case(self):
        """Preprocess query - should preserve case of business terms."""
        # GIVEN: Query with mixed case business terms
        query = "What is the EBITDA for Secil Group?"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: Case preserved (EBITDA stays uppercase)
        assert "EBITDA" in keywords
        assert "Secil" in keywords
        assert "Group" in keywords

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_preprocess_removes_question_marks(self):
        """Preprocess query - should remove question marks."""
        # GIVEN: Query with question mark
        query = "What is revenue?"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: Question mark removed
        assert "?" not in keywords

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_preprocess_empty_query_returns_empty_keywords(self):
        """Preprocess empty query - should return empty keywords."""
        # GIVEN: Empty query
        query = ""

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: Empty keywords returned
        assert keywords == ""
        assert filters is None

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_preprocess_only_stopwords_returns_empty(self):
        """Preprocess query with only stopwords - should return empty keywords."""
        # GIVEN: Query with only stopwords
        query = "what is the for and or"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: Empty keywords (all stopwords removed)
        assert keywords == ""

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_preprocess_no_temporal_info_returns_none_filters(self):
        """Preprocess query without temporal info - should return None filters."""
        # GIVEN: Query without dates
        query = "What is the variable cost per ton?"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: No temporal filters
        assert filters is None
        assert "variable" in keywords
        assert "cost" in keywords
        assert "ton" in keywords


class TestTemporalFilterExtraction:
    """Test temporal filter extraction."""

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_extract_temporal_full_month_name_and_year(self):
        """Extract temporal filters - should handle full month name + year."""
        # GIVEN: Query with full month name and year
        query_lower = "ebitda margin in august 2025"

        # WHEN: Extracting temporal filters
        filters = _extract_temporal_filters(query_lower)

        # THEN: Filter extracted with normalized format
        assert filters is not None
        assert filters["reporting_period"] == "Aug-25%"

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_extract_temporal_abbreviated_month_and_year(self):
        """Extract temporal filters - should handle abbreviated month + year."""
        # GIVEN: Query with abbreviated month
        query_lower = "revenue in aug 2025"

        # WHEN: Extracting temporal filters
        filters = _extract_temporal_filters(query_lower)

        # THEN: Filter extracted correctly
        assert filters is not None
        assert filters["reporting_period"] == "Aug-25%"

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_extract_temporal_normalizes_month_names(self):
        """Extract temporal filters - should normalize all month variations."""
        # GIVEN: Various month name formats
        test_cases = [
            ("january 2025", "Jan-25%"),
            ("february 2024", "Feb-24%"),
            ("september 2025", "Sep-25%"),
            ("december 2023", "Dec-23%"),
            ("jan 2025", "Jan-25%"),
            ("sep 2024", "Sep-24%"),
        ]

        for query_lower, expected_period in test_cases:
            # WHEN: Extracting temporal filters
            filters = _extract_temporal_filters(query_lower)

            # THEN: Month normalized correctly
            assert filters is not None, f"Failed for: {query_lower}"
            assert filters["reporting_period"] == expected_period, f"Failed for: {query_lower}"

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_extract_temporal_year_only(self):
        """Extract temporal filters - should handle year-only queries."""
        # GIVEN: Query with only year (no month)
        query_lower = "revenue in 2025"

        # WHEN: Extracting temporal filters
        filters = _extract_temporal_filters(query_lower)

        # THEN: Year filter extracted with wildcard
        assert filters is not None
        assert filters["reporting_period"] == "%-25%"

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_extract_temporal_no_temporal_info_returns_none(self):
        """Extract temporal filters - should return None when no dates."""
        # GIVEN: Query without temporal information
        query_lower = "what is the ebitda margin"

        # WHEN: Extracting temporal filters
        filters = _extract_temporal_filters(query_lower)

        # THEN: None returned
        assert filters is None

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_extract_temporal_prefers_month_year_over_year_only(self):
        """Extract temporal filters - should prefer month+year over year-only."""
        # GIVEN: Query with both month+year and standalone year
        query_lower = "revenue in august 2025 compared to 2024"

        # WHEN: Extracting temporal filters
        filters = _extract_temporal_filters(query_lower)

        # THEN: Month+year pattern takes precedence
        assert filters is not None
        assert filters["reporting_period"] == "Aug-25%"


class TestStopwordsAndMappings:
    """Test stopwords and month mappings constants."""

    @pytest.mark.unit
    @pytest.mark.priority("P3")
    def test_stopwords_contains_common_words(self):
        """STOPWORDS constant should contain common query words."""
        # GIVEN/WHEN: STOPWORDS constant
        # THEN: Contains expected common words
        assert "what" in STOPWORDS
        assert "is" in STOPWORDS
        assert "the" in STOPWORDS
        assert "in" in STOPWORDS
        assert "for" in STOPWORDS
        assert "show" in STOPWORDS
        assert "find" in STOPWORDS

    @pytest.mark.unit
    @pytest.mark.priority("P3")
    def test_month_mappings_contains_all_months(self):
        """MONTH_MAPPINGS should contain all 12 months (full and abbreviated)."""
        # GIVEN/WHEN: MONTH_MAPPINGS constant
        # THEN: Contains all months
        full_months = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]
        abbr_months = [
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        ]

        for month in full_months + abbr_months:
            assert month in MONTH_MAPPINGS, f"Missing month: {month}"

    @pytest.mark.unit
    @pytest.mark.priority("P3")
    def test_month_mappings_normalizes_correctly(self):
        """MONTH_MAPPINGS should normalize to 3-letter abbreviations."""
        # GIVEN/WHEN: MONTH_MAPPINGS constant
        # THEN: All values are 3-letter abbreviations
        assert MONTH_MAPPINGS["january"] == "Jan"
        assert MONTH_MAPPINGS["february"] == "Feb"
        assert MONTH_MAPPINGS["august"] == "Aug"
        assert MONTH_MAPPINGS["september"] == "Sep"
        assert MONTH_MAPPINGS["december"] == "Dec"
        # Abbreviated forms map to themselves (capitalized)
        assert MONTH_MAPPINGS["jan"] == "Jan"
        assert MONTH_MAPPINGS["aug"] == "Aug"


class TestQueryPreprocessingEdgeCases:
    """Test edge cases and complex scenarios."""

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_preprocess_multiple_business_terms(self):
        """Preprocess query with multiple business terms - all preserved."""
        # GIVEN: Query with multiple important terms
        query = "variable cost per ton EBITDA margin revenue"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: All business terms preserved
        assert "variable" in keywords
        assert "cost" in keywords
        assert "ton" in keywords
        assert "EBITDA" in keywords
        assert "margin" in keywords
        assert "revenue" in keywords

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_preprocess_whitespace_normalized(self):
        """Preprocess query - should normalize excess whitespace."""
        # GIVEN: Query with extra whitespace
        query = "What  is   the    revenue"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: Whitespace normalized (single spaces)
        assert "  " not in keywords  # No double spaces

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_preprocess_special_characters_in_business_terms(self):
        """Preprocess query - should preserve special chars in business terms."""
        # GIVEN: Query with hyphenated terms
        query = "year-over-year growth Q3-specific data"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: Hyphenated terms preserved
        assert "year-over-year" in keywords
        assert "Q3-specific" in keywords

    @pytest.mark.unit
    @pytest.mark.priority("P3")
    def test_preprocess_case_insensitive_stopword_removal(self):
        """Preprocess query - stopword removal should be case-insensitive."""
        # GIVEN: Query with capitalized stopwords
        query = "What Is The Revenue For Company"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: Stopwords removed regardless of case
        assert "What" not in keywords
        assert "Is" not in keywords
        assert "The" not in keywords
        assert "For" not in keywords
        # Business terms preserved
        assert "Revenue" in keywords
        assert "Company" in keywords

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_preprocess_real_world_financial_query(self):
        """Preprocess real-world financial query - end-to-end test."""
        # GIVEN: Complex real-world query
        query = "What is the variable cost per ton for the Secil Group in August 2025?"

        # WHEN: Preprocessing query
        keywords, filters = preprocess_query_for_table_search(query)

        # THEN: Keywords extracted correctly
        assert "variable" in keywords
        assert "cost" in keywords
        assert "ton" in keywords
        assert "Secil" in keywords
        assert "Group" in keywords
        # Stopwords removed
        assert "what" not in keywords.lower()
        assert "is" not in keywords.lower()
        assert "the" not in keywords.lower()
        # Temporal filter extracted
        assert filters is not None
        assert filters["reporting_period"] == "Aug-25%"
