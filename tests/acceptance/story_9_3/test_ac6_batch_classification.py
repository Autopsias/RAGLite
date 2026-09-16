"""ATDD tests for Story 9.3 AC6 - Batch Classification Support.

TDD RED Phase: All tests MUST fail initially because the value_type_classifier
does not exist yet.

Test IDs follow pattern: TEST-AC-9.3.6.{test}

BDD Acceptance Criteria:
Given a list of period strings and optional headers to classify
When classify_value_types_batch() is called
Then all items are classified efficiently
And a ClassificationReport is generated with value_type breakdown
And batch processing completes in <100ms for 1000 items
"""

import time


class TestAC6BatchClassificationSupport:
    """AC6: Batch Classification Support.

    Given a list of period strings and optional headers to classify
    When classify_value_types_batch() is called
    Then all items are classified efficiently
    And a ClassificationReport is generated with value_type breakdown
    And batch processing completes in <100ms for 1000 items
    """

    def test_ac_6_1_1_batch_classification_returns_results(self) -> None:
        """TEST-AC-9.3.6.1 [P0]: Batch classification returns results for all items.

        Given a list of period strings
        When classify_value_types_batch is called
        Then results are returned for all items
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import classify_value_types_batch

        periods = ["Dec-21", "B Jan-22", "F Feb-23", "Var Mar-24", "N/A"]

        # Act: Classify batch
        results, report = classify_value_types_batch(periods)

        # Assert: Results for all items
        assert len(results) == 5
        assert report.total_records == 5

    def test_ac_6_1_2_batch_returns_classification_report(self) -> None:
        """TEST-AC-9.3.6.2 [P0]: Batch returns ClassificationReport with breakdown.

        Given a mixed list of value types
        When classify_value_types_batch is called
        Then a ClassificationReport with value_type breakdown is returned
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import classify_value_types_batch

        # One of each type
        periods = [
            "Dec-21",  # ACTUAL
            "B Jan-22",  # BUDGET
            "F Feb-23",  # FORECAST
            "Var Mar-24",  # VARIANCE
            "N/A",  # UNKNOWN
        ]

        # Act: Classify batch
        results, report = classify_value_types_batch(periods)

        # Assert: Report has correct breakdown
        assert hasattr(report, "actual_count")
        assert hasattr(report, "budget_count")
        assert hasattr(report, "forecast_count")
        assert hasattr(report, "variance_count")
        assert hasattr(report, "unknown_count")

        assert report.actual_count == 1
        assert report.budget_count == 1
        assert report.forecast_count == 1
        assert report.variance_count == 1
        assert report.unknown_count == 1

    def test_ac_6_2_1_batch_classification_efficient(self) -> None:
        """TEST-AC-9.3.6.3 [P0]: Batch is more efficient than individual calls.

        Given many periods to classify
        When using batch vs individual calls
        Then batch is faster (due to caching/optimization)
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import (
            classify_value_type,
            classify_value_types_batch,
        )

        # Generate 100 periods with duplicates (tests caching)
        periods = [f"Dec-{i % 30:02d}" for i in range(100)]

        # Act: Time both approaches
        start_individual = time.time()
        for period in periods:
            classify_value_type(period)
        individual_time = time.time() - start_individual

        start_batch = time.time()
        classify_value_types_batch(periods)
        batch_time = time.time() - start_batch

        # Assert: Batch should be at least as fast (ideally faster due to caching)
        # Allow some variance, but batch should not be significantly slower
        assert batch_time <= individual_time * 1.5, (
            f"Batch ({batch_time:.3f}s) should not be slower than "
            f"individual ({individual_time:.3f}s)"
        )

    def test_ac_6_3_1_performance_under_100ms_for_1000_items(self) -> None:
        """TEST-AC-9.3.6.4 [P0]: Batch completes in <100ms for 1000 items.

        Given 1000 period strings
        When classify_value_types_batch is called
        Then processing completes in <100ms
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import classify_value_types_batch

        # Generate 1000 diverse periods
        periods = []
        for i in range(1000):
            if i % 5 == 0:
                periods.append(f"Dec-{i % 30:02d}")  # ACTUAL
            elif i % 5 == 1:
                periods.append(f"B Jan-{i % 30:02d}")  # BUDGET
            elif i % 5 == 2:
                periods.append(f"F Feb-{i % 30:02d}")  # FORECAST
            elif i % 5 == 3:
                periods.append(f"Var Mar-{i % 30:02d}")  # VARIANCE
            else:
                periods.append("")  # UNKNOWN

        # Act: Time the batch
        start = time.time()
        classify_value_types_batch(periods)
        elapsed = time.time() - start

        # Assert: <100ms (0.1 seconds)
        assert elapsed < 0.1, f"Batch took {elapsed * 1000:.1f}ms, expected <100ms"

    def test_ac_6_4_1_batch_handles_empty_list(self) -> None:
        """TEST-AC-9.3.6.5 [P1]: Batch handles empty list gracefully.

        Given an empty list of periods
        When classify_value_types_batch is called
        Then it returns empty results and zero-count report
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import classify_value_types_batch

        # Act: Classify empty batch
        results, report = classify_value_types_batch([])

        # Assert: Empty results, zero counts
        assert len(results) == 0
        assert report.total_records == 0

    def test_ac_6_4_2_batch_handles_none_values(self) -> None:
        """TEST-AC-9.3.6.6 [P1]: Batch handles None values as UNKNOWN.

        Given a list with None values
        When classify_value_types_batch is called
        Then None values are classified as UNKNOWN
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import (
            ValueType,
            classify_value_types_batch,
        )

        periods = [None, "Dec-21", None, "B Jan-22", None]

        # Act: Classify batch
        results, report = classify_value_types_batch(periods)

        # Assert: None values become UNKNOWN
        assert results[0].value_type == ValueType.UNKNOWN
        assert results[2].value_type == ValueType.UNKNOWN
        assert results[4].value_type == ValueType.UNKNOWN
        assert report.unknown_count == 3

    def test_ac_6_5_1_batch_with_headers(self) -> None:
        """TEST-AC-9.3.6.7 [P1]: Batch supports optional headers list.

        Given periods and matching headers lists
        When classify_value_types_batch is called with headers
        Then headers are used for classification
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import (
            ValueType,
            classify_value_types_batch,
        )

        periods = ["Dec-21", "Jan-22", "Feb-23"]
        headers = ["Actual", "Budget", "Forecast"]

        # Act: Classify batch with headers
        results, report = classify_value_types_batch(periods, headers=headers)

        # Assert: Headers influence classification
        assert results[0].value_type == ValueType.ACTUAL
        assert results[1].value_type == ValueType.BUDGET
        assert results[2].value_type == ValueType.FORECAST

    def test_ac_6_5_2_report_has_value_type_breakdown(self) -> None:
        """TEST-AC-9.3.6.8 [P0]: Report has value_type_breakdown property.

        Given a classified batch
        When accessing the report
        Then it has a value_type_breakdown with counts
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import classify_value_types_batch

        periods = ["Dec-21", "B Jan-22", "F Feb-23"]

        # Act: Classify batch
        _, report = classify_value_types_batch(periods)

        # Assert: Report has breakdown
        assert hasattr(report, "value_type_breakdown")
        breakdown = report.value_type_breakdown
        assert isinstance(breakdown, dict)
        assert "actual" in breakdown
        assert "budget" in breakdown
        assert "forecast" in breakdown
        assert "variance" in breakdown
        assert "unknown" in breakdown
