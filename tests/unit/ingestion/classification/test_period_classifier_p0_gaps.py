"""Coverage Expansion Tests for Story 9.2 - Period Classification Module.

Phase 6: [P0] Critical path coverage gaps - must never fail.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def cleanup_cache():
    """Clean up classification cache before each test."""
    from raglite.ingestion.classification.period_classifier import _classify_cached

    _classify_cached.cache_clear()
    yield
    _classify_cached.cache_clear()


class TestP0CriticalGaps:
    """[P0] Critical path coverage gaps - must never fail."""

    def test_llm_successfully_classifies_budget_type(self) -> None:
        """[P0] LLM successfully classifying BUDGET (lines 238-239)."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given an ambiguous period that LLM classifies as BUDGET
        # When LLM returns BUDGET classification
        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "budget"
            mock_client.return_value.chat.complete.return_value = mock_response

            result = classify_period("random string that needs LLM")

            # Then result has BUDGET type and is not usable
            assert result.period_type == PeriodType.BUDGET
            assert result.is_usable is False
            assert result.normalized is None

    def test_llm_successfully_classifies_ytd_budget_type(self) -> None:
        """[P0] LLM successfully classifying YTD_BUDGET (lines 238-239)."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given an ambiguous period that LLM classifies as YTD_BUDGET
        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "ytd_budget"
            mock_client.return_value.chat.complete.return_value = mock_response

            result = classify_period("random ytd budget string")

            # Then result has YTD_BUDGET type and is not usable
            assert result.period_type == PeriodType.YTD_BUDGET
            assert result.is_usable is False
            assert result.normalized is None

    def test_llm_successfully_classifies_monthly_actual_type(self) -> None:
        """[P0] LLM successfully classifying MONTHLY_ACTUAL (lines 238-239)."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given an ambiguous period that LLM classifies as MONTHLY_ACTUAL
        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "monthly_actual"
            mock_client.return_value.chat.complete.return_value = mock_response

            result = classify_period("some weird month format")

            # Then result has MONTHLY_ACTUAL type and is usable
            assert result.period_type == PeriodType.MONTHLY_ACTUAL
            assert result.is_usable is True
            assert result.normalized is None  # LLM doesn't provide normalized

    def test_llm_successfully_classifies_ytd_actual_type(self) -> None:
        """[P0] LLM successfully classifying YTD_ACTUAL (lines 238-239)."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given an ambiguous period that LLM classifies as YTD_ACTUAL
        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "ytd_actual"
            mock_client.return_value.chat.complete.return_value = mock_response

            result = classify_period("ytd something weird")

            # Then result has YTD_ACTUAL type and is usable
            assert result.period_type == PeriodType.YTD_ACTUAL
            assert result.is_usable is True
            assert result.normalized is None

    def test_classification_report_usability_rate_property(self) -> None:
        """[P0] ClassificationReport.usability_rate property (lines 48-52)."""
        from raglite.ingestion.classification import ClassificationReport

        # Given a classification report with known counts
        report = ClassificationReport(
            total_records=100,
            usable_records=75,
            monthly_actual_count=50,
            ytd_actual_count=25,
            budget_count=15,
            ytd_budget_count=5,
            unknown_count=5,
        )

        # When usability_rate is accessed
        rate = report.usability_rate

        # Then it returns correct percentage
        assert rate == 75.0  # 75/100 * 100

    def test_classification_report_usability_rate_empty(self) -> None:
        """[P0] ClassificationReport.usability_rate with zero records (line 50)."""
        from raglite.ingestion.classification import ClassificationReport

        # Given a report with zero records
        report = ClassificationReport(
            total_records=0,
            usable_records=0,
            monthly_actual_count=0,
            ytd_actual_count=0,
            budget_count=0,
            ytd_budget_count=0,
            unknown_count=0,
        )

        # When usability_rate is accessed
        rate = report.usability_rate

        # Then it returns 0.0 (not division by zero)
        assert rate == 0.0

    def test_classification_report_exclusion_breakdown_property(self) -> None:
        """[P0] ClassificationReport.exclusion_breakdown property (line 55-61)."""
        from raglite.ingestion.classification import ClassificationReport

        # Given a classification report
        report = ClassificationReport(
            total_records=100,
            usable_records=75,
            monthly_actual_count=50,
            ytd_actual_count=25,
            budget_count=15,
            ytd_budget_count=5,
            unknown_count=5,
        )

        # When exclusion_breakdown is accessed
        breakdown = report.exclusion_breakdown

        # Then it returns correct breakdown
        assert breakdown == {
            "budget": 15,
            "ytd_budget": 5,
            "unknown": 5,
        }

    def test_mixed_case_period_patterns(self) -> None:
        """[P0] Mixed case inputs are handled correctly."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given mixed case period strings (regex is case-insensitive)
        test_cases = [
            ("dec-21", PeriodType.MONTHLY_ACTUAL),
            ("DEC-21", PeriodType.MONTHLY_ACTUAL),
            ("DeC-21", PeriodType.MONTHLY_ACTUAL),
            ("ytd dec-21", PeriodType.YTD_ACTUAL),
            ("YTD DEC-21", PeriodType.YTD_ACTUAL),
            ("b dec-21", PeriodType.BUDGET),
            ("B DEC-21", PeriodType.BUDGET),
        ]

        for period, expected_type in test_cases:
            # When classified
            result = classify_period(period)

            # Then case doesn't matter
            assert result.period_type == expected_type, f"Failed for: {period}"

    def test_double_spaces_in_patterns(self) -> None:
        """[P0] Double spaces in period patterns are handled."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given periods with double spaces (regex uses \s+)
        test_cases = [
            ("YTD  Dec-21", PeriodType.YTD_ACTUAL),  # Double space after YTD
            ("B  Jan-22", PeriodType.BUDGET),  # Double space after B
            ("YTD B  Mar-22", PeriodType.YTD_BUDGET),  # Double spaces
        ]

        for period, expected_type in test_cases:
            # When classified
            result = classify_period(period)

            # Then extra spaces are tolerated
            assert result.period_type == expected_type, f"Failed for: {period}"
