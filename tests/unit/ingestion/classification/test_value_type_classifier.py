"""Unit tests for value type classifier - coverage expansion (Phase 6).

This module tests edge cases, error paths, and integration points NOT covered by
the 26 acceptance tests in test_story_9_3_value_type_classification.py.

Focus areas:
- Error handling and malformed inputs
- Edge cases (whitespace, case sensitivity, special chars)
- Cache behavior and performance characteristics
- Batch processing edge cases
- Integration with PeriodType classification
- Unicode and internationalization

Test IDs follow pattern: TEST-UNIT-VTC-{priority}-{number}
"""

import time

import pytest

from raglite.ingestion.classification import (
    PeriodType,
    ValueType,
    classify_value_type,
    classify_value_types_batch,
)

# =============================================================================
# P0 - Critical Paths (Must Pass)
# =============================================================================


class TestP0CriticalPaths:
    """P0: Critical path tests - must always pass."""

    def test_p0_001_batch_empty_list_returns_empty_results(self) -> None:
        """TEST-UNIT-VTC-P0-001: Empty list returns empty results without error."""
        results, report = classify_value_types_batch([])

        assert results == []
        assert report.total_records == 0
        assert report.actual_count == 0
        assert report.budget_count == 0
        assert report.forecast_count == 0
        assert report.variance_count == 0
        assert report.unknown_count == 0

    def test_p0_002_batch_single_item_processes_correctly(self) -> None:
        """TEST-UNIT-VTC-P0-002: Single-item batch works correctly."""
        results, report = classify_value_types_batch(["Dec-21"])

        assert len(results) == 1
        assert results[0].value_type == ValueType.ACTUAL
        assert report.total_records == 1
        assert report.actual_count == 1

    def test_p0_003_concurrent_calls_thread_safe(self) -> None:
        """TEST-UNIT-VTC-P0-003: Multiple concurrent calls don't corrupt state."""
        import threading

        results_list = []

        def classify_batch():
            periods = ["Dec-21", "B Jan-22", "F Feb-23"] * 10
            results, _ = classify_value_types_batch(periods)
            results_list.append(results)

        threads = [threading.Thread(target=classify_batch) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get consistent results
        assert len(results_list) == 5
        for results in results_list:
            assert len(results) == 30
            assert results[0].value_type == ValueType.ACTUAL
            assert results[1].value_type == ValueType.BUDGET
            assert results[2].value_type == ValueType.FORECAST

    def test_p0_004_none_period_type_does_not_override_prefix(self) -> None:
        """TEST-UNIT-VTC-P0-004: None period_type falls through to prefix detection."""
        result = classify_value_type("B Dec-21", period_type=None)

        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_prefix"

    def test_p0_005_batch_validates_headers_length_mismatch(self) -> None:
        """TEST-UNIT-VTC-P0-005: Batch raises ValueError on headers length mismatch."""
        periods = ["Dec-21", "Jan-22", "Feb-23"]
        headers = ["Actual", "Budget"]  # Length 2 vs periods length 3

        with pytest.raises(ValueError, match="same length"):
            classify_value_types_batch(periods, headers=headers)

    def test_p0_006_batch_validates_period_types_length_mismatch(self) -> None:
        """TEST-UNIT-VTC-P0-006: Batch raises ValueError on period_types length mismatch."""
        periods = ["Dec-21", "Jan-22", "Feb-23"]
        period_types = [PeriodType.MONTHLY_ACTUAL]  # Length 1 vs periods length 3

        with pytest.raises(ValueError, match="same length"):
            classify_value_types_batch(periods, period_types=period_types)


# =============================================================================
# P1 - Important Error Paths (Should Pass)
# =============================================================================


class TestP1ErrorHandling:
    """P1: Important error handling and validation."""

    def test_p1_001_whitespace_only_period_returns_unknown(self) -> None:
        """TEST-UNIT-VTC-P1-001: Various whitespace-only inputs return UNKNOWN."""
        whitespace_inputs = [
            "   ",  # Spaces
            "\t",  # Tab
            "\n",  # Newline
            "\r\n",  # Windows newline
            "  \t\n  ",  # Mixed whitespace
        ]

        for period in whitespace_inputs:
            result = classify_value_type(period)
            assert result.value_type == ValueType.UNKNOWN, f"Failed for: {repr(period)}"
            assert result.source == "empty", f"Wrong source for: {repr(period)}"

    def test_p1_002_leading_trailing_whitespace_stripped(self) -> None:
        """TEST-UNIT-VTC-P1-002: Leading/trailing whitespace is stripped correctly."""
        test_cases = [
            ("  Dec-21  ", ValueType.ACTUAL),
            ("  B Dec-21  ", ValueType.BUDGET),
            ("\tF Jun-24\t", ValueType.FORECAST),
            ("\nVar Apr-22\n", ValueType.VARIANCE),
        ]

        for period, expected in test_cases:
            result = classify_value_type(period)
            assert result.value_type == expected, f"Failed for: {repr(period)}"

    def test_p1_003_empty_header_string_vs_none(self) -> None:
        """TEST-UNIT-VTC-P1-003: Empty string header behaves same as None."""
        period = "Dec-21"

        result_none = classify_value_type(period, header=None)
        result_empty = classify_value_type(period, header="")
        result_whitespace = classify_value_type(period, header="   ")

        assert result_none.value_type == result_empty.value_type == result_whitespace.value_type
        assert result_none.source == result_empty.source == result_whitespace.source == "default"

    def test_p1_004_case_insensitive_matching(self) -> None:
        """TEST-UNIT-VTC-P1-004: Classification is case-insensitive."""
        test_cases = [
            ("BUDGET DEC-21", ValueType.BUDGET),
            ("budget dec-21", ValueType.BUDGET),
            ("BuDgEt DeC-21", ValueType.BUDGET),
            ("FORECAST JAN-22", ValueType.FORECAST),
            ("forecast jan-22", ValueType.FORECAST),
            ("VAR MAR-24", ValueType.VARIANCE),
            ("var mar-24", ValueType.VARIANCE),
        ]

        for period, expected in test_cases:
            result = classify_value_type(period)
            assert result.value_type == expected, f"Case sensitivity failed for: {period}"

    def test_p1_005_special_characters_in_period_string(self) -> None:
        """TEST-UNIT-VTC-P1-005: Special characters don't break regex matching.

        NOTE: Current implementation does NOT detect keywords within special char wrappers.
        This documents current behavior - keywords must have word boundaries.
        """
        # These work - keywords at word boundaries
        working_cases = [
            ("Dec-21 | Budget", ValueType.BUDGET),  # Space before keyword
            ("Dec-21 @ Forecast", ValueType.FORECAST),  # Space before keyword
            ("Dec-21 # Variance", ValueType.VARIANCE),  # Space before keyword
        ]

        for period, expected in working_cases:
            result = classify_value_type(period)
            assert result.value_type == expected, f"Special char failed for: {period}"

        # These DON'T work - keywords wrapped in special chars (no word boundary)
        # Documenting current limitation
        non_working_cases = [
            ("Dec-21 (Budget)", ValueType.ACTUAL),  # Parentheses break word boundary
            ("Dec-21 [Actual]", ValueType.ACTUAL),  # Brackets break word boundary
        ]

        for period, expected in non_working_cases:
            result = classify_value_type(period)
            assert result.value_type == expected, f"Documented behavior for: {period}"

    def test_p1_006_multiple_conflicting_signals_priority(self) -> None:
        """TEST-UNIT-VTC-P1-006: Priority hierarchy enforced with conflicts."""
        # period_type > period_prefix > header
        result = classify_value_type(
            "F Dec-21",  # Forecast prefix
            header="Budget",  # Budget header
            period_type=PeriodType.MONTHLY_ACTUAL,  # Actual period_type (highest)
        )

        assert result.value_type == ValueType.ACTUAL
        assert result.source == "period_type"

    def test_p1_007_prefix_overrides_conflicting_header(self) -> None:
        """TEST-UNIT-VTC-P1-007: Period prefix wins over conflicting header."""
        result = classify_value_type(
            "B Dec-21",  # Budget prefix
            header="Forecast",  # Conflicting forecast header
        )

        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_prefix"

    def test_p1_008_header_ignored_when_prefix_present(self) -> None:
        """TEST-UNIT-VTC-P1-008: Header not used when period has clear prefix."""
        test_cases = [
            ("B Dec-21", "Forecast", ValueType.BUDGET, "period_prefix"),
            ("F Jun-24", "Budget", ValueType.FORECAST, "period_prefix"),
            ("Var Mar-25", "Actual", ValueType.VARIANCE, "period_prefix"),
        ]

        for period, header, expected_type, expected_source in test_cases:
            result = classify_value_type(period, header=header)
            assert result.value_type == expected_type
            assert result.source == expected_source

    def test_p1_009_batch_with_mixed_none_and_values(self) -> None:
        """TEST-UNIT-VTC-P1-009: Batch handles mixed None and string headers."""
        periods = ["Dec-21", "Jan-22", "Feb-23"]
        headers = [None, "Budget", None]

        results, report = classify_value_types_batch(periods, headers=headers)

        assert results[0].value_type == ValueType.ACTUAL  # No header
        assert results[1].value_type == ValueType.BUDGET  # Budget header
        assert results[2].value_type == ValueType.ACTUAL  # No header

    def test_p1_010_unknown_marker_case_insensitive(self) -> None:
        """TEST-UNIT-VTC-P1-010: Unknown markers are case-insensitive."""
        unknown_markers = [
            "N/A",
            "n/a",
            "N/a",
            "None",
            "none",
            "NONE",
            "null",
            "NULL",
            "Null",
        ]

        for marker in unknown_markers:
            result = classify_value_type(marker)
            assert result.value_type == ValueType.UNKNOWN, f"Failed for: {marker}"
            assert result.source == "unknown_marker", f"Wrong source for: {marker}"


# =============================================================================
# P1 - Integration with PeriodType
# =============================================================================


class TestP1PeriodTypeIntegration:
    """P1: Integration with period classification module."""

    def test_p1_101_all_period_types_handled(self) -> None:
        """TEST-UNIT-VTC-P1-101: All PeriodType enum values are handled."""
        period = "Dec-21"

        # MONTHLY_ACTUAL -> ACTUAL
        result = classify_value_type(period, period_type=PeriodType.MONTHLY_ACTUAL)
        assert result.value_type == ValueType.ACTUAL
        assert result.source == "period_type"

        # YTD_ACTUAL -> ACTUAL
        result = classify_value_type(period, period_type=PeriodType.YTD_ACTUAL)
        assert result.value_type == ValueType.ACTUAL
        assert result.source == "period_type"

        # BUDGET -> BUDGET
        result = classify_value_type(period, period_type=PeriodType.BUDGET)
        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_type"

        # YTD_BUDGET -> BUDGET
        result = classify_value_type(period, period_type=PeriodType.YTD_BUDGET)
        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_type"

        # UNKNOWN -> fallthrough to other rules
        result = classify_value_type(period, period_type=PeriodType.UNKNOWN)
        assert result.value_type == ValueType.ACTUAL  # Default for plain period
        assert result.source == "default"

    def test_p1_102_period_type_precedence_over_header(self) -> None:
        """TEST-UNIT-VTC-P1-102: PeriodType takes precedence over header."""
        result = classify_value_type(
            "Dec-21",
            header="Forecast",
            period_type=PeriodType.BUDGET,
        )

        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_type"

    def test_p1_103_batch_with_mixed_period_types(self) -> None:
        """TEST-UNIT-VTC-P1-103: Batch handles mixed period_types correctly."""
        periods = ["Dec-21", "Jan-22", "Feb-23", "Mar-24"]
        period_types = [
            PeriodType.MONTHLY_ACTUAL,
            PeriodType.BUDGET,
            PeriodType.YTD_ACTUAL,
            None,
        ]

        results, report = classify_value_types_batch(periods, period_types=period_types)

        assert results[0].value_type == ValueType.ACTUAL
        assert results[0].source == "period_type"
        assert results[1].value_type == ValueType.BUDGET
        assert results[1].source == "period_type"
        assert results[2].value_type == ValueType.ACTUAL
        assert results[2].source == "period_type"
        assert results[3].value_type == ValueType.ACTUAL
        assert results[3].source == "default"


# =============================================================================
# P2 - Edge Cases (Nice to Have)
# =============================================================================


class TestP2EdgeCases:
    """P2: Edge cases and boundary conditions."""

    def test_p2_001_very_long_period_string(self) -> None:
        """TEST-UNIT-VTC-P2-001: Very long period strings don't break processing."""
        # 500 character string
        long_period = "B " + "Dec-21" + " extra data" * 50

        result = classify_value_type(long_period)

        # Should still detect budget prefix
        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_prefix"

    def test_p2_002_unicode_characters_in_period(self) -> None:
        """TEST-UNIT-VTC-P2-002: Unicode characters don't break classification.

        NOTE: Portuguese keywords with full diacritics have mixed support:
        - "Variação" works (matches ^var prefix pattern)
        - "Orçamento" and "Previsão" DON'T work (no word boundary match)
        This documents current behavior.
        """
        # These work
        working_cases = [
            ("Orcamento Dez-21", ValueType.BUDGET),  # ASCII version
            ("Previsao Jan-22", ValueType.FORECAST),  # ASCII version
            ("Variacao Mar-24", ValueType.VARIANCE),  # ASCII version
            ("Variação Mar-24", ValueType.VARIANCE),  # Unicode - matches ^var prefix
            ("Dec-21 • Budget", ValueType.BUDGET),  # Unicode separator, ASCII keyword
            ("Dec-21 → Forecast", ValueType.FORECAST),  # Unicode arrow, ASCII keyword
        ]

        for period, expected in working_cases:
            result = classify_value_type(period)
            assert result.value_type == expected, f"Unicode handling for: {period}"

        # These DON'T work - documenting current limitation
        non_working_cases = [
            ("Orçamento Dez-21", ValueType.ACTUAL),  # Cedilla breaks word boundary
            ("Previsão Jan-22", ValueType.ACTUAL),  # Tilde breaks word boundary
        ]

        for period, expected in non_working_cases:
            result = classify_value_type(period)
            assert result.value_type == expected, f"Documented limitation for: {period}"

    def test_p2_003_regex_special_chars_escaped_correctly(self) -> None:
        """TEST-UNIT-VTC-P2-003: Regex metacharacters don't cause errors."""
        regex_metachar_inputs = [
            "Dec-21 $Budget$",  # Dollar signs
            "Dec-21 .Forecast.",  # Dots
            "Dec-21 *Variance*",  # Asterisks
            "Dec-21 +Actual+",  # Plus signs
            "Dec-21 ?Budget?",  # Question marks
        ]

        for period in regex_metachar_inputs:
            # Should not raise regex errors
            result = classify_value_type(period)
            assert result.value_type is not None  # Just verify it processes

    def test_p2_004_cache_performance_with_duplicates(self) -> None:
        """TEST-UNIT-VTC-P2-004: Cache provides speedup with duplicate periods."""
        # Test with 5000 duplicate periods (should hit cache)
        periods_duplicates = ["Dec-21"] * 5000

        start = time.time()
        results, _ = classify_value_types_batch(periods_duplicates)
        duration_duplicates = time.time() - start

        assert len(results) == 5000
        assert duration_duplicates < 0.05  # <50ms for cache hits

    def test_p2_005_cache_performance_with_unique_periods(self) -> None:
        """TEST-UNIT-VTC-P2-005: Performance acceptable with unique periods."""
        # Test with 1000 unique periods (cache misses)
        periods_unique = [f"Dec-{year:04d}" for year in range(1000, 2000)]

        start = time.time()
        results, _ = classify_value_types_batch(periods_unique)
        duration_unique = time.time() - start

        assert len(results) == 1000
        assert duration_unique < 0.5  # <500ms for 1000 unique classifications

    def test_p2_006_batch_report_breakdown_correctness(self) -> None:
        """TEST-UNIT-VTC-P2-006: ValueTypeReport breakdown sums correctly."""
        periods = [
            "Dec-21",  # ACTUAL
            "B Jan-22",  # BUDGET
            "F Feb-23",  # FORECAST
            "Var Mar-24",  # VARIANCE
            "N/A",  # UNKNOWN
        ] * 20  # 100 total

        results, report = classify_value_types_batch(periods)

        assert report.total_records == 100
        assert report.actual_count == 20
        assert report.budget_count == 20
        assert report.forecast_count == 20
        assert report.variance_count == 20
        assert report.unknown_count == 20

        # Breakdown sums to total
        breakdown = report.value_type_breakdown
        assert sum(breakdown.values()) == report.total_records

    def test_p2_007_batch_handles_all_none_headers(self) -> None:
        """TEST-UNIT-VTC-P2-007: Batch with all None headers works correctly."""
        periods = ["Dec-21", "B Jan-22", "F Feb-23"]
        headers = [None, None, None]

        results, report = classify_value_types_batch(periods, headers=headers)

        assert len(results) == 3
        assert results[0].value_type == ValueType.ACTUAL
        assert results[1].value_type == ValueType.BUDGET
        assert results[2].value_type == ValueType.FORECAST

    def test_p2_008_batch_handles_all_none_period_types(self) -> None:
        """TEST-UNIT-VTC-P2-008: Batch with all None period_types works correctly."""
        periods = ["Dec-21", "B Jan-22", "F Feb-23"]
        period_types = [None, None, None]

        results, report = classify_value_types_batch(periods, period_types=period_types)

        assert len(results) == 3
        assert results[0].value_type == ValueType.ACTUAL
        assert results[1].value_type == ValueType.BUDGET
        assert results[2].value_type == ValueType.FORECAST

    def test_p2_009_variance_prefix_takes_precedence(self) -> None:
        """TEST-UNIT-VTC-P2-009: Variance patterns checked before budget patterns."""
        # "Var" could be misinterpreted as containing "var" substring
        variance_patterns = [
            "Var Dec-21",
            "%Var Jun-24",
            "Delta Mar-25",
            "Variance Apr-22",
            "Diff May-23",
        ]

        for period in variance_patterns:
            result = classify_value_type(period)
            assert result.value_type == ValueType.VARIANCE, f"Failed for: {period}"

    def test_p2_010_budget_trailing_b_pattern(self) -> None:
        """TEST-UNIT-VTC-P2-010: Trailing 'B' is detected as budget."""
        trailing_b_patterns = [
            "Dec-21 B",
            "Jan-22 b",
            "Feb-23 B",
            "Mar-24  B",  # Extra space
        ]

        for period in trailing_b_patterns:
            result = classify_value_type(period)
            assert result.value_type == ValueType.BUDGET, f"Failed for: {period}"

    def test_p2_011_year_only_format_returns_unknown(self) -> None:
        """TEST-UNIT-VTC-P2-011: Year-only format classified as invalid."""
        year_only_inputs = ["2021", "2022", "2023", "2024"]

        for period in year_only_inputs:
            result = classify_value_type(period)
            assert result.value_type == ValueType.UNKNOWN
            assert result.source == "invalid_format"

    def test_p2_012_random_text_returns_unknown(self) -> None:
        """TEST-UNIT-VTC-P2-012: Random text without period pattern returns unknown."""
        random_inputs = [
            "invalid",
            "random text",
            "completely random",
            "??##$$",
            "abcdefgh",
        ]

        for period in random_inputs:
            result = classify_value_type(period)
            assert result.value_type == ValueType.UNKNOWN
            assert result.source == "invalid_format"

    def test_p2_013_portuguese_header_case_insensitive(self) -> None:
        """TEST-UNIT-VTC-P2-013: Portuguese headers work with case variations."""
        test_cases = [
            ("Dec-21", "ORCAMENTO", ValueType.BUDGET),
            ("Dec-21", "orcamento", ValueType.BUDGET),
            ("Dec-21", "Orcamento", ValueType.BUDGET),
            ("Dec-21", "PREVISAO", ValueType.FORECAST),
            ("Dec-21", "previsao", ValueType.FORECAST),
        ]

        for period, header, expected in test_cases:
            result = classify_value_type(period, header=header)
            assert result.value_type == expected, f"Failed for header: {header}"

    def test_p2_014_actual_keyword_in_period(self) -> None:
        """TEST-UNIT-VTC-P2-014: 'Actual' keyword in period string detected."""
        actual_periods = [
            "Actual Dec-21",
            "Real Sep-23",
            "Actual Jan-25",
        ]

        for period in actual_periods:
            result = classify_value_type(period)
            assert result.value_type == ValueType.ACTUAL
            assert result.source == "period_prefix"

    def test_p2_015_batch_performance_stress_test(self) -> None:
        """TEST-UNIT-VTC-P2-015: Batch handles 10,000 periods efficiently."""
        # Stress test with 10,000 mixed periods
        periods = ["Dec-21", "B Jan-22", "F Feb-23", "Var Mar-24", "N/A"] * 2000  # 10,000 total

        start = time.time()
        results, report = classify_value_types_batch(periods)
        duration = time.time() - start

        assert len(results) == 10000
        assert report.total_records == 10000
        assert duration < 1.0  # Should complete in <1 second with caching
