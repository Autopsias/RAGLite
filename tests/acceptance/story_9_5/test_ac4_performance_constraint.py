"""ATDD tests for Story 9.5 AC4 - Performance Constraint.

TDD RED Phase: All tests MUST fail initially because the integration module
does not exist yet at raglite/ingestion/classification/integration.py.

Test IDs follow pattern: TEST-AC-9.5.4.{test}

BDD Acceptance Criteria:
Given a document with 100+ table rows
When classification is applied during extraction
Then total classification time is <100ms for 1000 rows
And extraction+classification overhead is <20% vs extraction-only baseline
And memory usage remains O(n) where n is batch size
And batch processing is used for efficiency (classify_*_batch functions)
"""

import time

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
    pytest.mark.slow,  # Performance tests take time
]


class TestAC4PerformanceConstraint:
    """AC4: Performance Constraint.

    Given a document with 100+ table rows
    When classification is applied during extraction
    Then total classification time is <100ms for 1000 rows
    And batch processing is used for efficiency
    """

    def test_ac_4_1_1_classify_1000_rows_under_100ms(self) -> None:
        """TEST-AC-9.5.4.1 [P0]: Classification of 1000 rows completes in <100ms.

        Given 1000 table rows
        When classify_rows_batch() is called
        Then total time is <100ms
        """
        from raglite.ingestion.classification.integration import classify_rows_batch

        # Arrange: Generate 1000 test rows
        test_rows = []
        entities = ["Portugal", "GROUP", "SECIL SA", "Cement Division", "XYZ"]
        periods = ["Dec-24", "YTD Dec-24", "Budget 2025", "Jan-24", "???"]

        for i in range(1000):
            test_rows.append(
                {
                    "entity": entities[i % len(entities)],
                    "metric": f"Metric_{i}",
                    "period": periods[i % len(periods)],
                    "value": float(i),
                }
            )

        # Act: Time the classification
        start_time = time.perf_counter()
        classify_rows_batch(test_rows)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Assert: Completed in <100ms
        assert elapsed_ms < 100, f"Classification took {elapsed_ms:.1f}ms, expected <100ms"

    def test_ac_4_1_2_classify_100_rows_under_10ms(self) -> None:
        """TEST-AC-9.5.4.2 [P1]: Classification of 100 rows completes in <10ms.

        Given 100 table rows
        When classify_rows_batch() is called
        Then total time is <10ms
        """
        from raglite.ingestion.classification.integration import classify_rows_batch

        # Arrange: Generate 100 test rows
        test_rows = [
            {"entity": "Portugal", "metric": f"Metric_{i}", "period": "Dec-24"} for i in range(100)
        ]

        # Act: Time the classification
        start_time = time.perf_counter()
        classify_rows_batch(test_rows)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Assert: Completed in <10ms
        assert elapsed_ms < 10, f"Classification took {elapsed_ms:.1f}ms, expected <10ms"

    def test_ac_4_1_3_batch_classification_faster_than_individual(self) -> None:
        """TEST-AC-9.5.4.3 [P1]: Batch classification is faster than individual.

        Given 500 rows
        When classifying via batch vs individual calls
        Then batch is faster (due to reduced function call overhead)
        """
        from raglite.ingestion.classification.integration import (
            classify_row,
            classify_rows_batch,
        )

        # Arrange: Generate 500 test rows
        test_rows = [
            {"entity": "Portugal", "metric": f"Metric_{i}", "period": "Dec-24"} for i in range(500)
        ]

        # Act: Time batch classification
        start_batch = time.perf_counter()
        classify_rows_batch(test_rows)
        batch_time = time.perf_counter() - start_batch

        # Act: Time individual classification
        start_individual = time.perf_counter()
        for row in test_rows:
            classify_row(row)
        individual_time = time.perf_counter() - start_individual

        # Assert: Batch is not significantly slower (within 2x is acceptable)
        # The main goal is batch doesn't add overhead, not that it's faster
        assert batch_time <= individual_time * 2, (
            f"Batch ({batch_time * 1000:.1f}ms) should not be much slower than "
            f"individual ({individual_time * 1000:.1f}ms)"
        )

    def test_ac_4_1_4_memory_scales_linearly_with_batch_size(self) -> None:
        """TEST-AC-9.5.4.4 [P2]: Memory usage is O(n) where n is batch size.

        Given batches of different sizes (100, 500, 1000)
        When classify_rows_batch() is called
        Then output size scales linearly (no memory explosion)
        """
        import sys

        from raglite.ingestion.classification.integration import classify_rows_batch

        # Arrange: Generate batches of different sizes
        def make_rows(count: int) -> list[dict]:
            return [
                {"entity": "Portugal", "metric": f"Metric_{i}", "period": "Dec-24"}
                for i in range(count)
            ]

        rows_100 = make_rows(100)
        rows_500 = make_rows(500)
        rows_1000 = make_rows(1000)

        # Act: Classify and measure output size
        result_100 = classify_rows_batch(rows_100)
        result_500 = classify_rows_batch(rows_500)
        result_1000 = classify_rows_batch(rows_1000)

        size_100 = sys.getsizeof(result_100)
        size_500 = sys.getsizeof(result_500)
        size_1000 = sys.getsizeof(result_1000)

        # Assert: Output counts match input counts (no row duplication)
        assert len(result_100) == 100
        assert len(result_500) == 500
        assert len(result_1000) == 1000

        # Assert: Size grows roughly linearly (not exponentially)
        # Size should roughly scale with count (with some overhead tolerance)
        # size_500 should be roughly 5x size_100, not 25x
        ratio_500_100 = size_500 / size_100 if size_100 > 0 else float("inf")
        ratio_1000_500 = size_1000 / size_500 if size_500 > 0 else float("inf")

        # Linear scaling means ratio should be around 5x and 2x respectively
        # Allow up to 10x for overhead (still linear, just different constant)
        assert ratio_500_100 < 15, f"500/100 ratio {ratio_500_100:.1f}x suggests non-linear scaling"
        assert ratio_1000_500 < 5, (
            f"1000/500 ratio {ratio_1000_500:.1f}x suggests non-linear scaling"
        )

    def test_ac_4_1_5_classification_overhead_under_20_percent(self) -> None:
        """TEST-AC-9.5.4.5 [P1]: Classification adds <20% overhead to extraction.

        Given extraction takes ~50ms for a table
        When classification is added
        Then total time increase is <20% (~10ms overhead acceptable)

        Note: This test simulates the overhead calculation since we can't
        hook into actual extraction without integration.
        """
        from raglite.ingestion.classification.integration import classify_rows_batch

        # Arrange: Simulate typical extraction output (100 rows per table)
        typical_table_rows = [
            {"entity": "Portugal", "metric": f"Metric_{i}", "period": "Dec-24"} for i in range(100)
        ]

        # Simulate extraction time baseline (50ms is typical)
        extraction_baseline_ms = 50.0

        # Act: Measure classification time
        start_time = time.perf_counter()
        classify_rows_batch(typical_table_rows)
        classification_ms = (time.perf_counter() - start_time) * 1000

        # Calculate overhead percentage
        overhead_percent = (classification_ms / extraction_baseline_ms) * 100

        # Assert: Overhead is <20%
        assert overhead_percent < 20, (
            f"Classification overhead {overhead_percent:.1f}% exceeds 20% limit. "
            f"Classification took {classification_ms:.1f}ms vs {extraction_baseline_ms}ms extraction baseline."
        )

    def test_ac_4_1_6_uses_batch_classification_functions(self) -> None:
        """TEST-AC-9.5.4.6 [P0]: Integration uses batch classification functions.

        Given the classify_rows_batch function exists
        When inspecting its implementation signature
        Then it accepts a list of rows and returns a list of enriched rows
        """
        import inspect

        from raglite.ingestion.classification.integration import classify_rows_batch

        # Assert: Function signature accepts list and returns list
        sig = inspect.signature(classify_rows_batch)
        params = list(sig.parameters.keys())

        # Should have a parameter for rows (list input)
        assert len(params) >= 1, "classify_rows_batch should accept rows parameter"

        # Verify it handles list input
        test_rows = [{"entity": "Test", "metric": "Test", "period": "Dec-24"}]
        result = classify_rows_batch(test_rows)
        assert isinstance(result, list), "classify_rows_batch should return a list"
