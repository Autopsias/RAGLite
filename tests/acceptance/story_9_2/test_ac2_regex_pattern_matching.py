"""Acceptance tests for AC2: Regex Pattern Matching for Known Formats.

TEST-AC-9.2.2.x tests validate that regex patterns match BEFORE LLM fallback
and handle various formats deterministically and efficiently.

TDD RED Phase: These tests define EXPECTED BEHAVIOR from acceptance criteria.
All tests MUST fail initially.
"""

import time
from unittest.mock import patch

import pytest


class TestAC2RegexPatternMatching:
    """AC2: Regex Pattern Matching for Known Formats.

    Given the need for deterministic classification without LLM dependency
    When classifying periods with known formats
    Then regex patterns match BEFORE LLM fallback is attempted
    """

    def test_ac2_1_regex_matches_before_llm_for_known_format(self) -> None:
        """TEST-AC-9.2.2.1 [P0]: Regex matches BEFORE LLM for known formats.

        Given a period string "Dec-21" that matches regex pattern
        When classify_period() is called
        Then the result is returned without calling the LLM API
        And classification time is <100ms
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        llm_called = False

        def mock_llm_call(*args, **kwargs):
            nonlocal llm_called
            llm_called = True
            raise AssertionError("LLM should not be called for regex-matchable period")

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            side_effect=mock_llm_call
        ):
            start = time.time()
            result = classify_period("Dec-21")
            elapsed = time.time() - start

        assert not llm_called, "LLM was called for regex-matchable period"
        assert result.period_type == PeriodType.MONTHLY_ACTUAL
        assert elapsed < 0.1, f"Classification took {elapsed:.3f}s, expected <0.1s"

    @pytest.mark.parametrize(
        "format_variant,expected_type",
        [
            # Mon-YY format
            ("Dec-21", "MONTHLY_ACTUAL"),
            ("Jan-25", "MONTHLY_ACTUAL"),
            # Mon-YYYY format
            ("Dec-2017", "MONTHLY_ACTUAL"),
            ("Jan-2025", "MONTHLY_ACTUAL"),
            # YTD Mon-YY
            ("YTD Dec-21", "YTD_ACTUAL"),
            ("YTD Jan-25", "YTD_ACTUAL"),
            # B Mon-YY (budget prefix)
            ("B Dec-21", "BUDGET"),
            ("B Jan-25", "BUDGET"),
            # YTD B Mon-YY (YTD budget)
            ("YTD B Dec-21", "YTD_BUDGET"),
            ("YTD B Jan-25", "YTD_BUDGET"),
            # Mon-YY B (budget suffix)
            ("Dec-21 B", "BUDGET"),
            ("Jan-25 B", "BUDGET"),
        ],
    )
    def test_ac2_2_patterns_handle_all_formats(
        self, format_variant: str, expected_type: str
    ) -> None:
        """TEST-AC-9.2.2.2 [P0]: Patterns handle Mon-YY, Mon-YYYY, YTD, B prefix/suffix.

        Given various period format variants
        When classify_period() is called
        Then correct period type is returned
        """
        from raglite.ingestion.classification import classify_period

        result = classify_period(format_variant)

        assert result.period_type.name == expected_type

    @pytest.mark.parametrize(
        "case_variant,expected_normalized",
        [
            ("dec-21", "Dec-21"),
            ("DEC-21", "Dec-21"),
            ("DeC-21", "Dec-21"),
            ("jan-25", "Jan-25"),
            ("JaN-25", "Jan-25"),
            ("dez-21", "Dec-21"),  # Portuguese lowercase
            ("FEV-24", "Feb-24"),  # Portuguese uppercase
        ],
    )
    def test_ac2_3_case_insensitive_month_matching(
        self, case_variant: str, expected_normalized: str
    ) -> None:
        """TEST-AC-9.2.2.3 [P0]: Case-insensitive month abbreviation matching.

        Given period strings with varying case
        When classify_period() is called
        Then all return correct period_type and normalized output
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        result = classify_period(case_variant)

        assert result.period_type == PeriodType.MONTHLY_ACTUAL
        assert result.normalized == expected_normalized

    @pytest.mark.slow
    @pytest.mark.integration
    def test_ac2_4_classification_within_5s_even_without_llm(self) -> None:
        """TEST-AC-9.2.2.4 [P0]: Classification completes within 5s when LLM unavailable.

        Given LLM API is unavailable (R-007 mitigation)
        When classifying a batch of periods
        Then classification completes within 5s even for non-regex periods
        """
        from raglite.ingestion.classification import classify_period

        # Mock LLM to simulate unavailability with delays
        def mock_unavailable_llm(*args, **kwargs):
            raise TimeoutError("LLM API unavailable")

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            side_effect=mock_unavailable_llm
        ):
            # Test non-regex period that would normally need LLM
            start = time.time()
            result = classify_period("Q1 2021")  # Ambiguous format
            elapsed = time.time() - start

        assert elapsed < 5.0, f"Classification took {elapsed:.1f}s, expected <5s"
        # Should fallback to UNKNOWN when LLM unavailable
        assert result.period_type.name == "UNKNOWN"

    @pytest.mark.parametrize(
        "whitespace_period,expected_normalized",
        [
            ("Dec-21\t", "Dec-21"),      # Trailing tab
            ("\tJan-25", "Jan-25"),      # Leading tab
            ("Dec-21\u00a0", "Dec-21"),  # NBSP (non-breaking space)
            ("  Feb-24  ", "Feb-24"),    # Surrounding spaces
        ],
    )
    def test_ac2_5_whitespace_handling(
        self, whitespace_period: str, expected_normalized: str
    ) -> None:
        """TEST-AC-9.2.2.5 [P1]: Whitespace handling for tabs and NBSP.

        Given period strings with trailing tabs, leading tabs, or NBSP
        When classify_period() is called
        Then classification succeeds with correct type
        And whitespace is stripped from normalized output
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        result = classify_period(whitespace_period)

        assert result.period_type == PeriodType.MONTHLY_ACTUAL
        assert result.normalized == expected_normalized
        # Verify no trailing/leading whitespace
        assert result.normalized == result.normalized.strip()
