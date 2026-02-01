"""ATDD tests for Story 9.2 - Period Classification Module.

TDD RED Phase: All tests MUST fail initially because the implementation
at raglite/ingestion/classification/ does not exist yet.

Test IDs follow pattern: TEST-AC-9.2.{ac}.{test}

Coverage:
- AC1: Module exists with exports
- AC3: LLM API Resilience (exponential backoff, retries, fallback)
- AC4: Batch classification with caching
- AC6: Portuguese month support
"""

import time
from unittest.mock import patch

import pytest


class TestAC1ModuleExists:
    """AC1: Period Classifier Module Creation.

    Given the existing period classification logic in raglite/forecasting/timeseries/
    When Story 9.2 is implemented
    Then a new module exists at raglite/ingestion/classification/period_classifier.py
    And it exports PeriodType, ClassifiedPeriod, classify_period, and ClassificationReport
    """

    def test_ac1_1_module_imports_successfully(self) -> None:
        """TEST-AC-9.2.1.1 [P0]: Module can be imported."""
        # Given the classification module should exist
        # When we try to import it
        # Then import succeeds without ImportError
        from raglite.ingestion.classification import (
            ClassificationReport,
            ClassifiedPeriod,
            PeriodType,
            classify_period,
        )

        # Verify exports are callable/usable
        assert PeriodType is not None
        assert ClassifiedPeriod is not None
        assert classify_period is not None
        assert ClassificationReport is not None

    def test_ac1_2_period_type_enum_values(self) -> None:
        """TEST-AC-9.2.1.2 [P0]: PeriodType enum has required values."""
        from raglite.ingestion.classification import PeriodType

        # Given the PeriodType enum
        # When we check its values
        # Then all required period types are present
        expected_values = {
            "MONTHLY_ACTUAL",
            "YTD_ACTUAL",
            "BUDGET",
            "YTD_BUDGET",
            "UNKNOWN",
        }
        actual_values = {member.name for member in PeriodType}
        assert expected_values == actual_values

    def test_ac1_3_classified_period_has_required_fields(self) -> None:
        """TEST-AC-9.2.1.3 [P0]: ClassifiedPeriod dataclass has required fields."""
        from raglite.ingestion.classification import ClassifiedPeriod, PeriodType

        # Given the ClassifiedPeriod dataclass
        # When we create an instance
        # Then all required fields are accessible
        cp = ClassifiedPeriod(
            original="Dec-21",
            period_type=PeriodType.MONTHLY_ACTUAL,
            normalized="Dec-21",
            is_usable=True,
        )
        assert cp.original == "Dec-21"
        assert cp.period_type == PeriodType.MONTHLY_ACTUAL
        assert cp.normalized == "Dec-21"
        assert cp.is_usable is True

    def test_ac1_4_classify_period_returns_classified_period(self) -> None:
        """TEST-AC-9.2.1.4 [P0]: classify_period returns ClassifiedPeriod."""
        from raglite.ingestion.classification import (
            classify_period,
        )

        # Given a period string
        # When classify_period is called
        # Then it returns a ClassifiedPeriod instance
        result = classify_period("Dec-21")
        assert result.__class__.__name__ == "ClassifiedPeriod"
        assert hasattr(result, "original")
        assert hasattr(result, "period_type")
        assert hasattr(result, "normalized")
        assert hasattr(result, "is_usable")

    def test_ac1_5_batch_classification_export(self) -> None:
        """TEST-AC-9.2.1.5 [P1]: classify_periods_batch is exported."""
        from raglite.ingestion.classification import classify_periods_batch

        # Given the module
        # When we import classify_periods_batch
        # Then it is callable
        assert callable(classify_periods_batch)


class TestAC3LLMResilience:
    """AC3: LLM API Resilience for Ambiguous Periods.

    Given a period string that cannot be classified by regex patterns
    When LLM-based classification is attempted
    Then the classifier uses exponential backoff on API failures (1s, 2s, 4s)
    And a maximum of 3 retries are attempted before fallback
    And fallback returns PeriodType.UNKNOWN with is_usable=False
    And all failures are logged with structured logging
    """

    def test_ac3_1_exponential_backoff_on_api_failure(self) -> None:
        """TEST-AC-9.2.3.1 [P0]: Uses exponential backoff on API failures."""
        from raglite.ingestion.classification import PeriodType
        from raglite.ingestion.classification.period_classifier import (
            _classify_with_llm,
        )

        # Given an ambiguous period string and a failing LLM API
        # When classification is attempted
        # Then exponential backoff is applied (1s, 2s, 4s delays)

        call_times: list[float] = []

        def mock_api_call(*args, **kwargs):
            call_times.append(time.time())
            raise Exception("API Error")

        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_client.return_value.chat.complete = mock_api_call

            # Should attempt 3 retries with backoff
            result = _classify_with_llm("ambiguous period string")

            # Verify exponential backoff timing (approximate)
            assert len(call_times) == 3, "Should attempt exactly 3 calls"

            if len(call_times) >= 2:
                first_delay = call_times[1] - call_times[0]
                assert first_delay >= 0.9, f"First retry delay should be ~1s, got {first_delay}"

            if len(call_times) >= 3:
                second_delay = call_times[2] - call_times[1]
                assert second_delay >= 1.8, f"Second retry delay should be ~2s, got {second_delay}"

            # Fallback should return UNKNOWN
            assert result == PeriodType.UNKNOWN

    def test_ac3_2_max_three_retries(self) -> None:
        """TEST-AC-9.2.3.2 [P0]: Maximum 3 retries before fallback."""
        from raglite.ingestion.classification.period_classifier import (
            _classify_with_llm,
        )

        # Given an API that always fails
        # When classification is attempted
        # Then exactly 3 attempts are made (initial + 2 retries)

        call_count = 0

        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("API Error")

        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_client.return_value.chat.complete = mock_api_call

            _classify_with_llm("ambiguous period")

            assert call_count == 3, f"Expected 3 attempts, got {call_count}"

    def test_ac3_3_fallback_returns_unknown_not_usable(self) -> None:
        """TEST-AC-9.2.3.3 [P0]: Fallback returns UNKNOWN with is_usable=False."""
        from raglite.ingestion.classification import (
            PeriodType,
            classify_period,
        )

        # Given an unclassifiable period that exhausts LLM retries
        # When classify_period is called
        # Then result has period_type=UNKNOWN and is_usable=False

        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_client.return_value.chat.complete.side_effect = Exception("API Error")

            # Using a string that regex cannot classify
            result = classify_period("completely random gibberish 12345 xyz")

            assert result.period_type == PeriodType.UNKNOWN
            assert result.is_usable is False

    def test_ac3_4_failures_logged_with_structured_logging(self) -> None:
        """TEST-AC-9.2.3.4 [P1]: Failures are logged with structured logging."""
        from raglite.ingestion.classification.period_classifier import (
            _classify_with_llm,
        )

        # Given an API failure
        # When classification is attempted
        # Then failures are logged with structured extra fields

        with patch(
            "raglite.ingestion.classification.period_classifier.get_mistral_client"
        ) as mock_client:
            mock_client.return_value.chat.complete.side_effect = Exception("API Error")

            with patch(
                "raglite.ingestion.classification.period_classifier.logger"
            ) as mock_logger:
                _classify_with_llm("ambiguous period")

                # Verify structured logging was called
                assert mock_logger.warning.called or mock_logger.error.called

                # Check for structured extra fields in any call
                log_calls = (
                    mock_logger.warning.call_args_list + mock_logger.error.call_args_list
                )
                has_structured_logging = any(
                    "extra" in call.kwargs for call in log_calls if call.kwargs
                )
                assert has_structured_logging, "Logs should include structured extra fields"


class TestAC4BatchClassificationCaching:
    """AC4: Batch Classification with Caching.

    Given a list of 100+ period strings to classify
    When classify_periods_batch() is called
    Then classification results are cached by normalized input
    And duplicate periods are only classified once
    And a ClassificationReport is generated summarizing the batch
    And batch processing completes in <500ms for 1000 periods
    """

    def test_ac4_1_batch_returns_classification_report(self) -> None:
        """TEST-AC-9.2.4.1 [P0]: Batch returns ClassificationReport."""
        from raglite.ingestion.classification import (
            classify_periods_batch,
        )

        # Given a list of period strings
        periods = ["Dec-21", "Jan-22", "B Dec-21", "YTD Feb-22"]

        # When classify_periods_batch is called
        report = classify_periods_batch(periods)

        # Then a ClassificationReport is returned
        assert report.__class__.__name__ == "ClassificationReport"
        assert hasattr(report, "total_records")
        assert hasattr(report, "usable_records")

    def test_ac4_2_duplicates_classified_once(self) -> None:
        """TEST-AC-9.2.4.2 [P0]: Duplicate periods classified only once."""
        from raglite.ingestion.classification import classify_periods_batch
        from raglite.ingestion.classification.period_classifier import _classify_cached

        # Given a list with duplicate periods
        periods = ["Dec-21", "Dec-21", "Dec-21", "Jan-22", "Jan-22"]

        # When classify_periods_batch is called
        # Then cache should only have 2 unique entries

        # Clear cache before test
        _classify_cached.cache_clear()

        initial_info = _classify_cached.cache_info()
        classify_periods_batch(periods)
        final_info = _classify_cached.cache_info()

        # Should have exactly 2 cache misses (unique periods)
        misses = final_info.misses - initial_info.misses
        assert misses == 2, f"Expected 2 unique classifications, got {misses}"

    def test_ac4_3_results_cached_by_normalized_input(self) -> None:
        """TEST-AC-9.2.4.3 [P1]: Results cached by normalized input."""
        from raglite.ingestion.classification import classify_periods_batch
        from raglite.ingestion.classification.period_classifier import _classify_cached

        # Given periods with varying whitespace
        periods = ["Dec-21", " Dec-21", "Dec-21 ", "  Dec-21  "]

        # When classify_periods_batch is called
        # Then all variations hit the same cache entry

        # Clear cache before test
        _classify_cached.cache_clear()

        initial_info = _classify_cached.cache_info()
        classify_periods_batch(periods)
        final_info = _classify_cached.cache_info()

        # Should only have 1 cache miss (all normalize to "Dec-21")
        misses = final_info.misses - initial_info.misses
        assert misses == 1, f"Expected 1 classification (cached), got {misses}"

    def test_ac4_4_performance_under_500ms_for_1000_periods(self) -> None:
        """TEST-AC-9.2.4.4 [P1]: <500ms for 1000 periods."""
        from raglite.ingestion.classification import classify_periods_batch

        # Given 1000 period strings
        periods = [f"Dec-{i % 30:02d}" for i in range(1000)]

        # When classify_periods_batch is called
        start = time.time()
        classify_periods_batch(periods)
        elapsed = time.time() - start

        # Then processing completes in <500ms
        assert elapsed < 0.5, f"Batch took {elapsed:.3f}s, expected <0.5s"

    def test_ac4_5_report_has_correct_counts(self) -> None:
        """TEST-AC-9.2.4.5 [P0]: Report has correct type counts."""
        from raglite.ingestion.classification import classify_periods_batch

        # Given a mixed list of period types
        periods = [
            "Dec-21",  # MONTHLY_ACTUAL
            "YTD Jan-22",  # YTD_ACTUAL
            "B Feb-22",  # BUDGET
            "YTD B Mar-22",  # YTD_BUDGET
            "N/A",  # UNKNOWN
        ]

        # When classify_periods_batch is called
        report = classify_periods_batch(periods)

        # Then report reflects correct counts
        assert report.total_records == 5
        assert report.monthly_actual_count == 1
        assert report.ytd_actual_count == 1
        assert report.budget_count == 1
        assert report.ytd_budget_count == 1
        assert report.unknown_count == 1

    def test_ac4_6_batch_handles_none_values(self) -> None:
        """TEST-AC-9.2.4.6 [M2]: Batch handles None values correctly."""
        from raglite.ingestion.classification import classify_periods_batch

        # Given a list with None values
        periods = [None, "Dec-21", None, "Jan-22", None]

        # When classify_periods_batch is called
        report = classify_periods_batch(periods)

        # Then None values are classified as UNKNOWN
        assert report.total_records == 5
        assert report.monthly_actual_count == 2
        assert report.unknown_count == 3


class TestAC6PortugueseMonthSupport:
    """AC6: Portuguese Month Support.

    Given period strings with Portuguese month abbreviations
    When classification is performed
    Then Portuguese months are correctly translated and classified
    """

    @pytest.mark.parametrize(
        "portuguese_period,expected_normalized",
        [
            ("Dez-21", "Dec-21"),  # Portuguese December
            ("Fev-24", "Feb-24"),  # Portuguese February
            ("Abr-23", "Apr-23"),  # Portuguese April
            ("Mai-22", "May-22"),  # Portuguese May
            ("Ago-21", "Aug-21"),  # Portuguese August
            ("Set-20", "Sep-20"),  # Portuguese September
            ("Out-19", "Oct-19"),  # Portuguese October
        ],
    )
    def test_ac6_1_monthly_actual_portuguese(
        self, portuguese_period: str, expected_normalized: str
    ) -> None:
        """TEST-AC-9.2.6.1 [P0]: Portuguese monthly periods classified correctly."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given a Portuguese month abbreviation
        # When classify_period is called
        result = classify_period(portuguese_period)

        # Then it is classified as MONTHLY_ACTUAL with correct normalization
        assert result.period_type == PeriodType.MONTHLY_ACTUAL
        assert result.normalized == expected_normalized
        assert result.is_usable is True

    @pytest.mark.parametrize(
        "portuguese_ytd,expected_normalized",
        [
            ("YTD Dez-21", "Dec-21"),
            ("YTD Out-19", "Oct-19"),
            ("YTD Fev-24", "Feb-24"),
        ],
    )
    def test_ac6_2_ytd_actual_portuguese(
        self, portuguese_ytd: str, expected_normalized: str
    ) -> None:
        """TEST-AC-9.2.6.2 [P0]: Portuguese YTD periods classified correctly."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given a YTD period with Portuguese month
        # When classify_period is called
        result = classify_period(portuguese_ytd)

        # Then it is classified as YTD_ACTUAL with correct normalization
        assert result.period_type == PeriodType.YTD_ACTUAL
        assert result.normalized == expected_normalized
        assert result.is_usable is True

    def test_ac6_3_portuguese_translation_consistency(self) -> None:
        """TEST-AC-9.2.6.3 [P1]: Portuguese translation is consistent."""
        from raglite.ingestion.classification import classify_period

        # Given the same Portuguese month in different contexts
        monthly = classify_period("Dez-21")
        ytd = classify_period("YTD Dez-21")

        # Then both normalize to the same English month
        assert monthly.normalized == "Dec-21"
        assert ytd.normalized == "Dec-21"

    def test_ac6_4_mixed_portuguese_english_batch(self) -> None:
        """TEST-AC-9.2.6.4 [P1]: Batch handles mixed Portuguese/English."""
        from raglite.ingestion.classification import classify_periods_batch

        # Given a mix of Portuguese and English periods
        periods = ["Dec-21", "Dez-21", "Feb-24", "Fev-24"]

        # When batch classification is performed
        report = classify_periods_batch(periods)

        # Then all are correctly classified
        assert report.monthly_actual_count == 4
        assert report.usable_records == 4
