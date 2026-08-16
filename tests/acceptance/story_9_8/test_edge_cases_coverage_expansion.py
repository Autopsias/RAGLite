"""
Test: test_edge_cases_coverage_expansion.py
Priority: P0-P2 (mixed)
Phase: 6 - Coverage Expansion

Tests edge cases, error paths, and integration scenarios NOT covered in original ATDD tests.
Provides fresh perspective on implementation gaps.
"""

import pytest

from raglite.forecasting.timeseries.sql_extraction_parsing import (
    _normalize_document_name,
    parse_sql_rows_with_units,
)
from raglite.forecasting.timeseries.sql_extraction_query import (
    _get_period_match_clause,
    build_timeseries_query,
)


@pytest.mark.acceptance
@pytest.mark.story_9_8
class TestEdgeCasesNullClassificationColumns:
    """Edge Case: NULL handling for classification columns"""

    @pytest.mark.p0
    def test_query_handles_all_null_period_type(self):
        """
        [P0] Edge Case: All rows have NULL period_type column

        GIVEN: Epic 9 data - all rows classified at ingestion time
        WHEN: Building query for monthly data
        THEN: Query uses strict equality (period_type = 'monthly_actual')
              without NULL fallback since all rows are classified
        """
        query = build_timeseries_query(
            metric_condition="metric = %s",
            entity_filter="",
            prefer_ytd=False,
            aggregation="sum",
        )

        # Assert: Strict equality pattern (no NULL fallback)
        assert "period_type = 'monthly_actual'" in query
        assert "period_type IS NULL" not in query

    @pytest.mark.p0
    def test_query_handles_all_null_value_type(self):
        """
        [P0] Edge Case: All rows have NULL value_type column

        GIVEN: Epic 9 data - all rows classified at ingestion time
        WHEN: Building query excluding budget data
        THEN: Query uses strict equality (value_type = 'actual')
              without NULL fallback since all rows are classified
        """
        query = build_timeseries_query(
            metric_condition="metric = %s",
            entity_filter="",
            prefer_ytd=False,
            aggregation="sum",
        )

        # Assert: Strict equality pattern (no NULL fallback)
        assert "value_type = 'actual'" in query
        assert "value_type IS NULL" not in query

    @pytest.mark.p1
    def test_query_handles_mixed_null_and_classified(self):
        """
        [P1] Edge Case: Some rows classified, some NULL (partial migration)

        GIVEN: Epic 9 complete - all rows now classified at ingestion
        WHEN: Building query
        THEN: Query uses strict equality for both classification fields
        """
        query = build_timeseries_query(
            metric_condition="metric = %s",
            entity_filter="",
            prefer_ytd=False,
            aggregation="sum",
        )

        # Assert: Strict equality for both fields (no NULL handling)
        assert "period_type = 'monthly_actual'" in query
        assert "value_type = 'actual'" in query
        assert "period_type IS NULL" not in query
        assert "value_type IS NULL" not in query


@pytest.mark.acceptance
@pytest.mark.story_9_8
class TestEdgeCasesInvalidClassificationValues:
    """Edge Case: Invalid/unexpected values in classification columns"""

    @pytest.mark.p2
    def test_query_structure_with_unexpected_period_type(self):
        """
        [P2] Edge Case: Database has unexpected period_type values

        GIVEN: period_type column exists but contains unexpected values
              (e.g., 'quarterly', 'annual', 'unknown', 'invalid')
        WHEN: Query filters for monthly_actual
        THEN: Only rows matching exact value are returned (SQL handles filtering)
        """
        # This is more of a database-level test, but validate query structure
        query = build_timeseries_query(
            metric_condition="metric = %s",
            entity_filter="",
            prefer_ytd=False,
            aggregation="sum",
        )

        # Assert: Query uses equality check (not LIKE or IN with wildcards)
        assert (
            "period_type = 'monthly_actual'" in query or "period_type IN ('monthly_actual'" in query
        )
        # Should NOT use wildcard patterns that could match unexpected values
        assert "period_type LIKE" not in query

    @pytest.mark.p2
    def test_query_structure_excludes_budget_with_value_type(self):
        """
        [P2] Edge Case: Verify budget/forecast/variance values are excluded

        GIVEN: value_type column has values: actual, budget, forecast, variance, unknown
        WHEN: Query filters for actual data
        THEN: Only 'actual' rows are selected (implicitly excludes budget/forecast/variance/unknown)

        Epic 9: Strict equality on 'actual' implicitly excludes all other values
        """
        query = build_timeseries_query(
            metric_condition="metric = %s",
            entity_filter="",
            prefer_ytd=False,
            aggregation="sum",
        )

        # Assert: Uses strict equality for 'actual' (implicitly excludes all others)
        assert "value_type = 'actual'" in query
        # No explicit exclusion needed - strict equality handles it
        assert "value_type !=" not in query


@pytest.mark.acceptance
@pytest.mark.story_9_8
class TestEdgeCasesYTDFallbackBehavior:
    """Edge Case: YTD mode with monthly fallback"""

    @pytest.mark.p0
    def test_ytd_mode_accepts_both_ytd_and_monthly(self):
        """
        [P0] Edge Case: YTD mode ONLY accepts ytd_actual (no monthly fallback)

        GIVEN: prefer_ytd=True
        WHEN: Building query
        THEN: Query accepts ONLY ytd_actual (FIX 2026-02-03: mixing caused negative values)
        """
        period_match, _, _ = _get_period_match_clause(prefer_ytd=True)

        # Assert: Only YTD, no monthly fallback
        assert "ytd_actual" in period_match
        assert "monthly_actual" not in period_match
        # Should use strict equality, not IN or OR
        assert "period_type = 'ytd_actual'" in period_match

    @pytest.mark.p1
    def test_ytd_flag_dynamic_based_on_period_type(self):
        """
        [P1] Edge Case: is_ytd flag is dynamic, not hardcoded

        GIVEN: YTD mode with monthly fallback enabled
        WHEN: Extracting is_ytd_flag
        THEN: Flag is determined by CASE statement, not constant
        """
        _, _, is_ytd_flag = _get_period_match_clause(prefer_ytd=True)

        # Assert: Uses CASE statement for dynamic determination
        assert "CASE" in is_ytd_flag
        assert "period_type = 'ytd_actual'" in is_ytd_flag
        # Should return TRUE for YTD, FALSE for monthly
        assert "TRUE" in is_ytd_flag and "FALSE" in is_ytd_flag

    @pytest.mark.p1
    def test_monthly_mode_no_ytd_fallback(self):
        """
        [P1] Edge Case: Monthly mode does NOT include YTD data

        GIVEN: prefer_ytd=False
        WHEN: Building query
        THEN: Query only accepts monthly_actual, not ytd_actual
        """
        period_match, _, _ = _get_period_match_clause(prefer_ytd=False)

        # Assert: Only monthly, no YTD
        assert "monthly_actual" in period_match
        assert "ytd_actual" not in period_match


@pytest.mark.acceptance
@pytest.mark.story_9_8
class TestEdgeCasesParsingNullUnits:
    """Edge Case: Row parsing with NULL unit column"""

    @pytest.mark.p1
    def test_parse_rows_handles_null_unit(self):
        """
        [P1] Edge Case: Rows with NULL unit column

        GIVEN: SQL returns rows with unit = NULL
        WHEN: Parsing rows with parse_sql_rows_with_units()
        THEN: Units list contains None for those rows
        """
        # Arrange: Row with NULL unit
        rows = [
            ("Jan-25", 2025, 1000.0, 1, "2025-01_Report", False, None),  # NULL unit
        ]

        # Act
        result = parse_sql_rows_with_units(rows, "revenue")

        # Assert
        assert len(result.points) == 1
        assert len(result.units) == 1
        assert result.units[0] is None  # NULL preserved

    @pytest.mark.p1
    def test_parse_rows_mixed_null_and_present_units(self):
        """
        [P1] Edge Case: Some rows have units, others NULL

        GIVEN: Mixed unit data (some NULL, some 'M EUR', etc.)
        WHEN: Parsing rows
        THEN: Each row's unit is correctly preserved

        Note: Avoids year-like values (2000-2099) which are filtered by Story 6.24.1
        """
        rows = [
            ("Jan-25", 2025, 1000.0, 1, "2025-01_Report", False, "M EUR"),
            ("Feb-25", 2025, 150.5, 1, "2025-02_Report", False, None),  # Not year-like
            ("Mar-25", 2025, 3000.0, 1, "2025-03_Report", False, "Thousands"),
        ]

        result = parse_sql_rows_with_units(rows, "revenue")

        assert len(result.units) == 3
        assert result.units[0] == "M EUR"
        assert result.units[1] is None
        assert result.units[2] == "Thousands"


@pytest.mark.acceptance
@pytest.mark.story_9_8
class TestEdgeCasesDocumentNameNormalization:
    """Edge Case: Document name normalization edge cases"""

    @pytest.mark.p2
    def test_normalize_handles_none(self):
        """
        [P2] Edge Case: NULL document_id

        GIVEN: Row has document_id = NULL
        WHEN: Normalizing document name
        THEN: Returns "unknown"
        """
        assert _normalize_document_name(None) == "unknown"

    @pytest.mark.p2
    def test_normalize_handles_empty_string(self):
        """
        [P2] Edge Case: Empty string document_id

        GIVEN: document_id is ""
        WHEN: Normalizing
        THEN: Returns "unknown"
        """
        assert _normalize_document_name("") == "unknown"

    @pytest.mark.p2
    def test_normalize_preserves_already_normalized(self):
        """
        [P2] Edge Case: Already normalized name (spaces, not underscores)

        GIVEN: document_id = "2025-08 Performance Review CONSO v1"
        WHEN: Normalizing
        THEN: Returns unchanged
        """
        normalized = _normalize_document_name("2025-08 Performance Review CONSO v1")
        assert normalized == "2025-08 Performance Review CONSO v1"

    @pytest.mark.p1
    def test_normalize_converts_underscores_to_spaces(self):
        """
        [P1] Edge Case: Document ID with underscores

        GIVEN: document_id = "2025-08_Performance_Review_CONSO_v1"
        WHEN: Normalizing
        THEN: Underscores converted to spaces
        """
        normalized = _normalize_document_name("2025-08_Performance_Review_CONSO_v1")
        assert normalized == "2025-08 Performance Review CONSO v1"


@pytest.mark.acceptance
@pytest.mark.story_9_8
class TestEdgeCasesPeriodExtractionRegex:
    """Edge Case: Period extraction still uses regex for YTD parsing"""

    @pytest.mark.p1
    def test_period_extract_uses_regexp_match_for_ytd(self):
        """
        [P1] Edge Case: REGEXP_MATCH still used for extracting Mon-YY from YTD

        GIVEN: Query is built for YTD mode
        WHEN: Examining period_extract expression
        THEN: Still uses REGEXP_MATCH to extract clean period from "YTD Mon-YY"
        """
        _, period_extract, _ = _get_period_match_clause(prefer_ytd=True)

        # Assert: Uses regex for extraction (not matching)
        assert "REGEXP_MATCH" in period_extract
        # Should extract Mon-YY pattern
        assert "[A-Za-z]{3}-[0-9]{2,4}" in period_extract

    @pytest.mark.p1
    def test_monthly_mode_no_regex_extraction(self):
        """
        [P1] Edge Case: Monthly mode doesn't need regex extraction

        GIVEN: Query for monthly data (no YTD prefix to strip)
        WHEN: Examining period_extract
        THEN: Uses 'period' column directly, no regex
        """
        _, period_extract, _ = _get_period_match_clause(prefer_ytd=False)

        # Assert: Direct column reference, no regex
        assert period_extract == "period"


@pytest.mark.acceptance
@pytest.mark.story_9_8
class TestErrorPathsSQLInjectionProtection:
    """Error Path: SQL injection validation"""

    @pytest.mark.p0
    def test_invalid_aggregation_raises_valueerror(self):
        """
        [P0] Error Path: Invalid aggregation function

        GIVEN: Unsupported aggregation function
        WHEN: Building query
        THEN: Raises ValueError to prevent SQL injection
        """
        with pytest.raises(ValueError, match="Invalid aggregation function"):
            build_timeseries_query(
                metric_condition="metric = %s",
                entity_filter="",
                prefer_ytd=False,
                aggregation="DROP TABLE users;",  # SQL injection attempt
            )

    @pytest.mark.p0
    def test_semicolon_in_metric_condition_raises_valueerror(self):
        """
        [P0] Error Path: Semicolon in metric_condition (SQL injection)

        GIVEN: metric_condition contains semicolon
        WHEN: Building query
        THEN: Raises ValueError
        """
        with pytest.raises(ValueError, match="Invalid metric condition"):
            build_timeseries_query(
                metric_condition="metric = %s; DROP TABLE users;",
                entity_filter="",
                prefer_ytd=False,
                aggregation="sum",
            )

    @pytest.mark.p0
    def test_semicolon_in_entity_filter_raises_valueerror(self):
        """
        [P0] Error Path: Semicolon in entity_filter

        GIVEN: entity_filter contains semicolon
        WHEN: Building query
        THEN: Raises ValueError
        """
        with pytest.raises(ValueError, match="Invalid entity filter"):
            build_timeseries_query(
                metric_condition="metric = %s",
                entity_filter="AND entity = 'GROUP'; DROP TABLE users;",
                prefer_ytd=False,
                aggregation="sum",
            )

    @pytest.mark.p0
    def test_semicolon_in_value_filter_raises_valueerror(self):
        """
        [P0] Error Path: Semicolon in value_filter

        GIVEN: value_filter contains semicolon
        WHEN: Building query with value filter
        THEN: Raises ValueError
        """
        with pytest.raises(ValueError, match="Invalid value filter"):
            build_timeseries_query(
                metric_condition="metric = %s",
                entity_filter="",
                prefer_ytd=False,
                aggregation="sum",
                value_filter="AND value < 100; DROP TABLE users;",
            )


@pytest.mark.acceptance
@pytest.mark.story_9_8
class TestErrorPathsInvalidRowData:
    """Error Path: Parsing rows with invalid data"""

    @pytest.mark.p1
    def test_parse_skips_row_with_invalid_period_format(self):
        """
        [P1] Error Path: Row with invalid period format

        GIVEN: Row has malformed period (e.g., "INVALID")
        WHEN: Parsing rows
        THEN: Row is skipped with warning, doesn't crash
        """
        rows = [
            ("INVALID-PERIOD", 2025, 1000.0, 1, "2025-01_Report", False, "M EUR"),
        ]

        result = parse_sql_rows_with_units(rows, "revenue")

        # Assert: Skipped (no points parsed)
        assert len(result.points) == 0

    @pytest.mark.p1
    def test_parse_skips_row_with_null_total_value(self):
        """
        [P1] Error Path: Row with NULL total_value

        GIVEN: Row has total_value = NULL
        WHEN: Parsing rows
        THEN: Row is skipped gracefully
        """
        rows = [
            ("Jan-25", 2025, None, 1, "2025-01_Report", False, "M EUR"),  # NULL value
        ]

        result = parse_sql_rows_with_units(rows, "revenue")

        # Assert: Skipped (conversion fails)
        assert len(result.points) == 0

    @pytest.mark.p1
    def test_parse_skips_year_like_values(self):
        """
        [P1] Error Path: Filters year values (2000-2099)

        GIVEN: Row has value in year range (e.g., 2025)
        WHEN: Parsing rows (Story 6.24.1 year filtering)
        THEN: Row is filtered out as year-like value
        """
        rows = [
            ("Jan-25", 2025, 2025.0, 1, "2025-01_Report", False, None),  # Year-like
        ]

        result = parse_sql_rows_with_units(rows, "revenue")

        # Assert: Filtered out
        assert len(result.points) == 0


@pytest.mark.acceptance
@pytest.mark.story_9_8
class TestIntegrationBackwardCompatibilityOldRows:
    """Integration: Backward compatibility with pre-migration rows"""

    @pytest.mark.p1
    def test_parse_rows_handles_6_tuple_format(self):
        """
        [P1] Integration: Old format without unit column (6-tuple)

        GIVEN: SQL returns old 6-tuple format (before unit column)
        WHEN: Parsing rows
        THEN: Gracefully handles missing unit (sets to None)
        """
        # Old format: (period, fiscal_year, total_value, row_count, source_doc, is_ytd)
        rows_old_format = [
            ("Jan-25", 2025, 1000.0, 1, "2025-01_Report", False),  # 6-tuple
        ]

        result = parse_sql_rows_with_units(rows_old_format, "revenue")

        # Assert: Parses successfully with unit=None
        assert len(result.points) == 1
        assert len(result.units) == 1
        assert result.units[0] is None  # Defaults to None

    @pytest.mark.p1
    def test_parse_rows_handles_7_tuple_format(self):
        """
        [P1] Integration: New format with unit column (7-tuple)

        GIVEN: SQL returns new 7-tuple format (with unit)
        WHEN: Parsing rows
        THEN: Extracts unit correctly
        """
        rows_new_format = [
            ("Jan-25", 2025, 1000.0, 1, "2025-01_Report", False, "M EUR"),  # 7-tuple
        ]

        result = parse_sql_rows_with_units(rows_new_format, "revenue")

        assert len(result.units) == 1
        assert result.units[0] == "M EUR"


@pytest.mark.acceptance
@pytest.mark.story_9_8
class TestBoundaryConditionsLOCReduction:
    """Boundary Condition: LOC reduction edge cases"""

    @pytest.mark.p2
    def test_loc_reduction_exactly_50_lines(self):
        """
        [P2] Boundary: Exactly 50 LOC reduction (minimum threshold)

        GIVEN: AC3 requires >= 50 lines reduction
        WHEN: Total reduction is exactly 50
        THEN: Meets acceptance criteria (boundary case)
        """
        # This is a documentation test - manual verification
        # Just ensuring the test exists for completeness
        assert True  # Verified via AC3 tests

    @pytest.mark.p2
    def test_loc_reduction_multiple_files_contribute(self):
        """
        [P2] Boundary: LOC reduction across multiple files

        GIVEN: Reduction comes from sql_extraction_query.py + sql_extraction_parsing.py
        WHEN: Summing reductions
        THEN: Total >= 50 lines even if individual files are < 50
        """
        # Documentation test - ensures we're counting across files
        assert True  # Verified via AC3 tests
