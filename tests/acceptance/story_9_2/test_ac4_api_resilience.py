"""Acceptance tests for AC4: API Resilience (5s Timeout, Fail-Fast).

TEST-AC-9.2.4.x tests validate that classification remains resilient when
LLM API is unavailable, with fail-fast behavior to regex.

TDD RED Phase: These tests define EXPECTED BEHAVIOR from acceptance criteria.
All tests MUST fail initially.
"""

import time
from unittest.mock import patch

import pytest


class TestAC4APIResilience:
    """AC4: API Resilience (5s Timeout, Fail-Fast to Regex).

    Given the LLM API is unavailable (429, 503, timeout)
    When classifying periods in batch
    Then classification completes within timeout limits
    """

    @pytest.mark.slow
    @pytest.mark.integration
    def test_ac4_1_single_period_classification_under_5s(self) -> None:
        """TEST-AC-9.2.4.1 [P0]: Total classification time for any single period <5s.

        Given an ambiguous period that needs LLM classification
        And the LLM API times out
        When classify_period() is called
        Then the function returns within 5s (ThreadPoolExecutor timeout enforces this)
        """
        from raglite.ingestion.classification import classify_period

        def mock_slow_llm(*args, **kwargs):
            # Simulate a slow API that would exceed 5s if not caught by executor timeout
            time.sleep(10)  # Executor timeout of 4.9s will catch this
            raise TimeoutError("Request timed out")

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            side_effect=mock_slow_llm
        ):
            start = time.time()
            result = classify_period("Q1 2021")  # Ambiguous - needs LLM
            elapsed = time.time() - start

        # ThreadPoolExecutor timeout of 4.9s ensures completion within 5s
        assert elapsed < 5.5, f"Classification took {elapsed:.1f}s, expected <5.5s"
        # Should return UNKNOWN on timeout
        assert result.period_type.name == "UNKNOWN"

    def test_ac4_2_regex_periods_classify_correctly_despite_api_status(self) -> None:
        """TEST-AC-9.2.4.2 [P0]: Regex-matchable periods classify regardless of API status.

        Given the LLM API is returning 503 Service Unavailable
        When classifying periods that match regex patterns
        Then classification succeeds via regex (no API dependency)
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        # Simulate complete API failure
        def mock_api_unavailable(*args, **kwargs):
            raise ConnectionError("503 Service Unavailable")

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            side_effect=mock_api_unavailable
        ):
            # These should all work via regex without needing LLM
            result1 = classify_period("Dec-21")
            result2 = classify_period("YTD Jan-25")
            result3 = classify_period("B Feb-24")

        assert result1.period_type == PeriodType.MONTHLY_ACTUAL
        assert result2.period_type == PeriodType.YTD_ACTUAL
        assert result3.period_type == PeriodType.BUDGET

    def test_ac4_3_non_regex_periods_return_unknown_not_exception(self) -> None:
        """TEST-AC-9.2.4.3 [P0]: Non-regex periods return UNKNOWN (not hang/exception).

        Given a period that cannot be classified by regex
        And the LLM API fails
        When classify_period() is called
        Then UNKNOWN is returned (not exception raised)
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        # Mock the _classify_with_llm to return UNKNOWN (simulating failure handling)
        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            return_value=PeriodType.UNKNOWN
        ):
            # Should not raise exception, should return UNKNOWN
            result = classify_period("FY2021")  # Ambiguous format

        assert result.period_type == PeriodType.UNKNOWN
        assert result.is_usable is False

    @pytest.mark.slow
    @pytest.mark.integration
    def test_ac4_4_structured_logging_captures_api_failures(self) -> None:
        """TEST-AC-9.2.4.4 [P1]: Structured logging captures API failures with context.

        Given an LLM API failure
        When classification falls back to UNKNOWN
        Then structured logs capture error context (period, error type, attempt)
        """
        from raglite.ingestion.classification import classify_period

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm"
        ) as mock_llm:
            mock_llm.side_effect = TimeoutError("API timeout after 5s")

            with patch(
                "raglite.ingestion.classification.period_classifier.logger"
            ) as mock_logger:
                classify_period("random format abc")

                # Check logging was called
                log_called = (
                    mock_logger.warning.called or
                    mock_logger.error.called or
                    mock_logger.info.called
                )
                assert log_called, "Expected log calls for API failure"

    @pytest.mark.slow
    @pytest.mark.integration
    def test_ac4_5_batch_processing_not_blocked_by_api_failures(self) -> None:
        """TEST-AC-9.2.4.5 [P0]: Ingestion pipeline continues despite API failures.

        Given a batch of 100 periods with 90 regex-matchable and 10 ambiguous
        And the LLM API is unavailable
        When classify_periods_batch() is called
        Then 90 periods are classified correctly via regex
        And 10 periods return UNKNOWN within 5s each
        And total batch time is reasonable (not 10 * full retry timeout)
        """
        from raglite.ingestion.classification import classify_periods_batch

        # Create batch: 90 regex-matchable + 10 ambiguous
        regex_periods = [f"Dec-{i % 30:02d}" for i in range(90)]
        ambiguous_periods = [f"Q{i} 2021" for i in range(1, 11)]  # Q1 2021, etc.
        all_periods = regex_periods + ambiguous_periods

        def mock_api_failure(*args, **kwargs):
            # Simulate slow failure
            time.sleep(0.5)
            raise TimeoutError("API unavailable")

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            side_effect=mock_api_failure
        ):
            start = time.time()
            report = classify_periods_batch(all_periods)
            elapsed = time.time() - start

        # Verify classification results
        assert report.total_records == 100
        assert report.monthly_actual_count >= 90  # Regex-matched
        assert report.unknown_count >= 10  # Ambiguous returned UNKNOWN

        # Batch should complete in reasonable time (not 10 * full retry)
        # With 10 ambiguous periods and ~1s LLM fallback each, expect <60s
        assert elapsed < 60.0, f"Batch took {elapsed:.1f}s, expected <60s"

    @pytest.mark.slow
    @pytest.mark.integration
    def test_ac4_6_timeout_per_period_enforced(self) -> None:
        """TEST-AC-9.2.4.6 [P0]: Per-period timeout ensures bounded execution.

        Given an ambiguous period and executor enforces 4.9s timeout
        When classify_period() is called
        Then function returns within 5s (ThreadPoolExecutor timeout)
        And result is UNKNOWN
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        # Mock _classify_with_llm to simulate slow LLM (would exceed timeout)
        def mock_slow_response(*args, **kwargs):
            time.sleep(10)  # Would exceed 5s if not caught by executor timeout
            return PeriodType.MONTHLY_ACTUAL

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            side_effect=mock_slow_response
        ):
            start = time.time()
            result = classify_period("ambiguous-format-xyz")
            elapsed = time.time() - start

        # Should complete within 5s due to executor timeout
        assert elapsed < 5.5, f"Classification took {elapsed:.1f}s, expected <5.5s"
        assert result.period_type == PeriodType.UNKNOWN

    def test_ac4_7_regex_bypass_for_throughput(self) -> None:
        """TEST-AC-9.2.4.7 [P1]: Regex bypass protects throughput.

        Given a batch of 1000 periods with 990 regex-matchable
        When classify_periods_batch() is called
        Then batch completes in <500ms (per caching target)
        And no LLM calls are made for regex-matchable periods
        """
        from raglite.ingestion.classification import classify_periods_batch

        # 990 regex-matchable periods + 10 ambiguous
        periods = [f"Dec-{i % 30:02d}" for i in range(990)]
        periods.extend(["N/A"] * 10)  # Unknown formats

        llm_call_count = 0

        def track_llm_calls(*args, **kwargs):
            nonlocal llm_call_count
            llm_call_count += 1
            # Return UNKNOWN for ambiguous
            from raglite.ingestion.classification import PeriodType
            return PeriodType.UNKNOWN

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            side_effect=track_llm_calls
        ):
            start = time.time()
            classify_periods_batch(periods)  # Report not needed, just testing performance
            elapsed = time.time() - start

        # Verify fast execution for regex-matchable
        assert elapsed < 0.5, f"Batch took {elapsed:.3f}s, expected <0.5s"
        # LLM should only be called for ambiguous periods (or not at all if cached)
        assert llm_call_count <= 10, f"LLM called {llm_call_count} times, expected <=10"
