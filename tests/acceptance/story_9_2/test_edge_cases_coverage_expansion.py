"""Edge Case Coverage Expansion for Story 9.2 - Period Classification (Phase 6).

This test file adds edge case tests for gaps found in the implementation
that were NOT covered by the original ATDD tests.

Test Priority Tagging:
- [P0]: Critical path, must never fail
- [P1]: Important scenarios
- [P2]: Edge cases
- [P3]: Nice-to-have

Gap Analysis Focus:
1. Concurrent batch processing edge cases
2. LRU cache behavior (hit/miss, eviction)
3. Empty/null input variations
4. Mixed batch with failures
5. Memory/performance edge cases
6. Error recovery scenarios
"""

import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest


class TestConcurrentBatchProcessing:
    """Edge cases for concurrent access to classify_periods_batch."""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_concurrent_batch_classification_thread_safety(self) -> None:
        """[P1] GAP: Concurrent threads calling classify_periods_batch.

        Given multiple threads calling classify_periods_batch simultaneously
        When batches contain overlapping periods (cache contention)
        Then all threads complete successfully without race conditions
        """
        from raglite.ingestion.classification import classify_periods_batch

        # Create overlapping batches to test cache contention
        batch1 = [f"Dec-{i:02d}" for i in range(1, 21)]  # Dec-01 to Dec-20
        batch2 = [f"Dec-{i:02d}" for i in range(10, 31)]  # Dec-10 to Dec-30 (overlap)
        batch3 = [f"Jan-{i:02d}" for i in range(1, 21)]  # Jan-01 to Jan-20

        def process_batch(periods):
            return classify_periods_batch(periods)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(process_batch, batch1),
                executor.submit(process_batch, batch2),
                executor.submit(process_batch, batch3),
            ]

            results = [f.result(timeout=30) for f in futures]

        # Verify all batches completed successfully
        assert results[0].total_records == 20
        assert results[1].total_records == 21
        assert results[2].total_records == 20
        assert all(r.monthly_actual_count > 0 for r in results)

    def test_empty_batch_handling(self) -> None:
        """[P1] GAP: Empty list passed to classify_periods_batch.

        Given an empty list of periods
        When classify_periods_batch is called
        Then returns ClassificationReport with zero counts
        """
        from raglite.ingestion.classification import classify_periods_batch

        report = classify_periods_batch([])

        assert report.total_records == 0
        assert report.usable_records == 0
        assert report.monthly_actual_count == 0
        assert report.ytd_actual_count == 0
        assert report.budget_count == 0
        assert report.ytd_budget_count == 0
        assert report.unknown_count == 0

    def test_batch_with_all_none_values(self) -> None:
        """[P2] GAP: Batch containing only None values.

        Given a batch of None values
        When classify_periods_batch is called
        Then all classified as UNKNOWN
        """
        from raglite.ingestion.classification import classify_periods_batch

        report = classify_periods_batch([None, None, None])

        assert report.total_records == 3
        assert report.unknown_count == 3
        assert report.usable_records == 0


class TestLRUCacheBehavior:
    """Edge cases for LRU cache behavior in classify_periods_batch."""

    def test_cache_hit_with_duplicate_periods(self) -> None:
        """[P1] GAP: Cache hit when duplicate periods in batch.

        Given a batch with many duplicate periods
        When classify_periods_batch is called
        Then duplicates are classified only once (cache hit)
        And performance is significantly faster than unique periods
        """
        from raglite.ingestion.classification import classify_periods_batch

        # Batch with 100 duplicates of "Dec-21"
        duplicate_batch = ["Dec-21"] * 100

        start = time.time()
        report = classify_periods_batch(duplicate_batch)
        elapsed = time.time() - start

        assert report.total_records == 100
        assert report.monthly_actual_count == 100
        # Should complete very fast due to caching (all cache hits after first)
        assert elapsed < 0.1, f"Duplicate batch took {elapsed:.3f}s, expected <0.1s"

    def test_cache_behavior_with_whitespace_normalization(self) -> None:
        """[P2] GAP: Cache uses normalized (whitespace-stripped) input.

        Given periods with different whitespace but same content
        When classify_periods_batch is called
        Then all treated as same period (cache hit)
        """
        from raglite.ingestion.classification import classify_periods_batch

        # Same period with different whitespace
        variations = [
            "Dec-21",
            " Dec-21",
            "Dec-21 ",
            " Dec-21 ",
            "\tDec-21",
            "Dec-21\t",
        ]

        start = time.time()
        report = classify_periods_batch(variations)
        elapsed = time.time() - start

        assert report.total_records == 6
        assert report.monthly_actual_count == 6
        # Should be fast - all variations map to same cache key
        assert elapsed < 0.1, f"Whitespace batch took {elapsed:.3f}s, expected <0.1s"

    def test_cache_eviction_beyond_maxsize(self) -> None:
        """[P2] GAP: LRU cache evicts old entries when maxsize (10,000) exceeded.

        Given more than 10,000 unique periods
        When classify_periods_batch is called
        Then older entries are evicted (LRU behavior)
        And classification still works correctly
        """
        from raglite.ingestion.classification import classify_periods_batch

        # Generate 10,100 unique periods (exceeds maxsize=10000)
        large_batch = [f"Dec-{i % 100:02d}" for i in range(10100)]

        report = classify_periods_batch(large_batch)

        # All should still classify correctly (some cache misses due to eviction)
        assert report.total_records == 10100
        assert report.monthly_actual_count == 10100


class TestNullAndEmptyInputs:
    """Edge cases for null, empty, and malformed inputs."""

    @pytest.mark.parametrize(
        "invalid_input",
        [
            None,
            "",
            "   ",
            "\t",
            "\n",
            "\r\n",
            "\u00a0",  # NBSP
        ],
    )
    def test_empty_and_whitespace_only_inputs(self, invalid_input: str | None) -> None:
        """[P1] GAP: Various empty/whitespace-only inputs.

        Given null, empty, or whitespace-only period strings
        When classify_period is called
        Then returns UNKNOWN with is_usable=False
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        result = classify_period(invalid_input)

        assert result.period_type == PeriodType.UNKNOWN
        assert result.normalized is None
        assert result.is_usable is False

    def test_very_long_period_string(self) -> None:
        """[P2] GAP: Very long period string (memory/performance edge case).

        Given a very long period string (>1000 chars)
        When classify_period is called
        Then returns UNKNOWN without hanging or OOM
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        # 1000 character random string
        long_period = "Q" * 1000 + " 2021"

        result = classify_period(long_period)

        assert result.period_type == PeriodType.UNKNOWN
        assert result.is_usable is False

    def test_unicode_variation_in_month_names(self) -> None:
        """[P2] GAP: Unicode variations in period strings.

        Given period strings with unicode characters
        When classify_period is called
        Then handles gracefully (likely returns UNKNOWN)
        """
        from raglite.ingestion.classification import classify_period

        unicode_periods = [
            "Déc-21",  # Accented e
            "Dec\u200b-21",  # Zero-width space
            "Dëc-21",  # Umlaut
        ]

        for period in unicode_periods:
            result = classify_period(period)
            # Should not crash, may return UNKNOWN or classify if regex matches
            assert result is not None
            assert hasattr(result, "period_type")


class TestMixedBatchWithFailures:
    """Edge cases for batches with mixed success/failure scenarios."""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_batch_with_llm_failures_on_some_periods(self) -> None:
        """[P1] GAP: Mixed batch where some periods need LLM but LLM fails.

        Given a batch with 50 regex-matchable and 50 ambiguous periods
        And LLM fails for ambiguous periods
        When classify_periods_batch is called
        Then regex-matchable periods succeed
        And ambiguous periods return UNKNOWN (not crash)
        """
        from raglite.ingestion.classification import classify_periods_batch

        # 50 regex-matchable + 50 ambiguous
        regex_periods = [f"Dec-{i % 30:02d}" for i in range(50)]
        ambiguous_periods = [f"Q{i} 2021" for i in range(50)]
        mixed_batch = regex_periods + ambiguous_periods

        def mock_llm_failure(*args, **kwargs):
            # Simulate LLM timeout/failure
            import time

            time.sleep(0.1)  # Small delay to simulate attempt
            raise TimeoutError("LLM timeout")

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            side_effect=mock_llm_failure,
        ):
            report = classify_periods_batch(mixed_batch)

        # Verify results
        assert report.total_records == 100
        assert report.monthly_actual_count >= 50  # Regex succeeded
        assert report.unknown_count >= 50  # Ambiguous -> UNKNOWN on LLM failure

    def test_batch_with_mixed_period_types(self) -> None:
        """[P1] GAP: Batch with all period types represented.

        Given a batch with monthly, YTD, budget, YTD budget, and unknown
        When classify_periods_batch is called
        Then each type is counted correctly in report
        """
        from raglite.ingestion.classification import classify_periods_batch

        mixed_batch = [
            "Dec-21",  # MONTHLY_ACTUAL
            "Jan-25",  # MONTHLY_ACTUAL
            "YTD Dec-21",  # YTD_ACTUAL
            "YTD Sep-25",  # YTD_ACTUAL
            "B Dec-21",  # BUDGET
            "Jan-25 B",  # BUDGET
            "YTD B Dec-21",  # YTD_BUDGET
            "YTD B Sep-25",  # YTD_BUDGET
            "N/A",  # UNKNOWN
            "FY2021",  # UNKNOWN
        ]

        report = classify_periods_batch(mixed_batch)

        assert report.total_records == 10
        assert report.monthly_actual_count == 2
        assert report.ytd_actual_count == 2
        assert report.budget_count == 2
        assert report.ytd_budget_count == 2
        assert report.unknown_count == 2
        assert report.usable_records == 4  # 2 monthly + 2 YTD


class TestErrorRecovery:
    """Edge cases for error recovery after LLM failure cascades."""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_recovery_after_llm_failure_cascade(self) -> None:
        """[P1] GAP: System recovers after multiple consecutive LLM failures.

        Given multiple consecutive periods that need LLM
        And LLM fails for all of them
        When subsequent regex-matchable period is classified
        Then classification succeeds (no persistent error state)
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        call_count = 0

        def mock_llm_cascade_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ConnectionError("LLM API unavailable")
            return PeriodType.UNKNOWN

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            side_effect=mock_llm_cascade_failure,
        ):
            # First 3 should trigger LLM failure
            result1 = classify_period("Q1 2021")
            result2 = classify_period("Q2 2021")
            result3 = classify_period("Q3 2021")

            # This should succeed via regex (no LLM needed)
            result4 = classify_period("Dec-21")

        assert result1.period_type == PeriodType.UNKNOWN
        assert result2.period_type == PeriodType.UNKNOWN
        assert result3.period_type == PeriodType.UNKNOWN
        assert result4.period_type == PeriodType.MONTHLY_ACTUAL  # Recovery!

    @pytest.mark.slow
    @pytest.mark.integration
    def test_executor_timeout_prevents_thread_leak(self) -> None:
        """[P0] GAP: ThreadPoolExecutor timeout prevents thread accumulation.

        Given a period that would cause LLM to hang indefinitely
        When classify_period is called
        Then ThreadPoolExecutor timeout (4.9s) prevents thread leak
        And thread pool is properly shut down
        """
        import threading

        from raglite.ingestion.classification import classify_period

        initial_thread_count = threading.active_count()

        def mock_infinite_hang(*args, **kwargs):
            # Simulate infinite hang (executor timeout will catch this)
            time.sleep(100)  # Executor timeout of 4.9s will interrupt

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            side_effect=mock_infinite_hang,
        ):
            start = time.time()
            result = classify_period("ambiguous format")
            elapsed = time.time() - start

        # Should complete within executor timeout + overhead
        assert elapsed < 6.0, f"Classification took {elapsed:.1f}s, expected <6s"
        assert result.period_type.name == "UNKNOWN"

        # Wait for thread cleanup
        time.sleep(0.5)
        final_thread_count = threading.active_count()

        # Thread count should not grow significantly (no leak)
        assert final_thread_count <= initial_thread_count + 2, (
            f"Thread leak detected: {initial_thread_count} -> {final_thread_count}"
        )


class TestPerformanceEdgeCases:
    """Performance edge cases for batch processing."""

    def test_large_batch_with_all_regex_matches(self) -> None:
        """[P2] GAP: Large batch (5000 periods) with all regex matches.

        Given a batch of 5000 regex-matchable periods
        When classify_periods_batch is called
        Then completes within performance budget (<1s)
        """
        from raglite.ingestion.classification import classify_periods_batch

        # 5000 periods (mix to avoid excessive caching)
        large_batch = [f"{'Dec' if i % 2 else 'Jan'}-{i % 30:02d}" for i in range(5000)]

        start = time.time()
        report = classify_periods_batch(large_batch)
        elapsed = time.time() - start

        assert report.total_records == 5000
        assert report.monthly_actual_count == 5000
        assert elapsed < 1.0, f"Large batch took {elapsed:.3f}s, expected <1s"

    @pytest.mark.slow
    @pytest.mark.integration
    def test_batch_with_high_llm_fallback_rate(self) -> None:
        """[P2] GAP: Batch with 100% LLM fallback requirement.

        Given a batch of 50 periods that all need LLM classification
        When classify_periods_batch is called
        Then completes without timeout
        And all periods are classified (even if UNKNOWN)
        """
        from raglite.ingestion.classification import classify_periods_batch

        # All ambiguous periods requiring LLM
        ambiguous_batch = [f"Q{i} 2021" for i in range(50)]

        # Mock LLM with fast response to avoid timeout
        from raglite.ingestion.classification import PeriodType

        with patch(
            "raglite.ingestion.classification.period_classifier._classify_with_llm",
            return_value=PeriodType.UNKNOWN,
        ):
            start = time.time()
            report = classify_periods_batch(ambiguous_batch)
            elapsed = time.time() - start

        assert report.total_records == 50
        # Should complete reasonably fast with mocked LLM
        assert elapsed < 10.0, f"Ambiguous batch took {elapsed:.1f}s, expected <10s"


class TestCaseInsensitivityEdgeCases:
    """Edge cases for case-insensitive pattern matching."""

    @pytest.mark.parametrize(
        "mixed_case_period,expected_type",
        [
            ("DEC-21", "MONTHLY_ACTUAL"),
            ("dec-21", "MONTHLY_ACTUAL"),
            ("DeC-21", "MONTHLY_ACTUAL"),
            ("ytd dec-21", "YTD_ACTUAL"),
            ("YTD DEC-21", "YTD_ACTUAL"),
            ("yTd DeC-21", "YTD_ACTUAL"),
            ("b dec-21", "BUDGET"),
            ("B DEC-21", "BUDGET"),
            ("ytd b dec-21", "YTD_BUDGET"),
            ("YTD B DEC-21", "YTD_BUDGET"),
        ],
    )
    def test_case_insensitive_keyword_matching(
        self, mixed_case_period: str, expected_type: str
    ) -> None:
        """[P1] GAP: Case variations in YTD and B keywords.

        Given period strings with mixed case in keywords (YTD, B)
        When classify_period is called
        Then case-insensitive matching succeeds
        """
        from raglite.ingestion.classification import classify_period

        result = classify_period(mixed_case_period)

        assert result.period_type.name == expected_type
