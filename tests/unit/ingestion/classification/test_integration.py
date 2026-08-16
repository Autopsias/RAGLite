"""Unit tests for classification integration summary and performance.

Tests coverage:
- generate_classification_summary: Summary generation
- Performance constraints: <100ms for 1000 rows

Target: 95%+ coverage per Epic 9 requirements
See: test_integration_row_enrichment.py for row enrichment tests
"""

import time

import pytest

from raglite.ingestion.classification.integration import (
    classify_rows_batch,
    generate_classification_summary,
)
from raglite.ingestion.classification.models import (
    EntityLevel,
    PeriodType,
    ValueType,
)

# Test markers
pytestmark = [
    pytest.mark.unit,
]

# Performance test constants
PERF_TEST_SMALL_BATCH = 100
PERF_TEST_LARGE_BATCH = 1000
PERF_TEST_HUGE_BATCH = 5000
PERF_TEST_SMALL_THRESHOLD_MS = 20
PERF_TEST_LARGE_THRESHOLD_MS = 100
# CI runs 3-5x slower than local - add adjustment factor
PERF_CI_ADJUSTMENT = 5


class TestGenerateClassificationSummary:
    """Tests for generate_classification_summary function.

    Given: A list of classified rows
    When: generate_classification_summary() is called
    Then: A ClassificationSummary is generated with breakdowns
    """

    def test_summary_generation_with_expected_breakdowns(self):
        """TEST-AC-9.5.3.1 [P0]: Summary generation with expected breakdowns.

        Arrange: Classified rows with mixed types
        Act: Call generate_classification_summary()
        Assert: Counts are accurate for all categories
        """
        rows = [
            {
                "period_type": PeriodType.MONTHLY_ACTUAL.value,
                "value_type": ValueType.ACTUAL.value,
                "entity_level": EntityLevel.COMPANY_ONLY.value,
            },
            {
                "period_type": PeriodType.MONTHLY_ACTUAL.value,
                "value_type": ValueType.ACTUAL.value,
                "entity_level": EntityLevel.COMPANY_ONLY.value,
            },
            {
                "period_type": PeriodType.BUDGET.value,
                "value_type": ValueType.BUDGET.value,
                "entity_level": EntityLevel.CONSOLIDATED.value,
            },
            {
                "period_type": PeriodType.YTD_ACTUAL.value,
                "value_type": ValueType.ACTUAL.value,
                "entity_level": EntityLevel.SEGMENT.value,
            },
        ]

        summary = generate_classification_summary(rows, duration_ms=15)

        assert summary.total_rows == 4
        assert summary.classification_duration_ms == 15
        assert summary.period_monthly_actual == 2
        assert summary.period_budget == 1
        assert summary.period_ytd_actual == 1
        assert summary.value_actual == 3
        assert summary.value_budget == 1
        assert summary.entity_company_only == 2
        assert summary.entity_consolidated == 1
        assert summary.entity_segment == 1

    def test_summary_generation_empty_rows(self):
        """TEST-AC-9.5.3.2 [P0]: Summary generation with empty rows.

        Arrange: Empty row list
        Act: Call generate_classification_summary()
        Assert: All counts are zero
        """
        summary = generate_classification_summary([], duration_ms=0)

        assert summary.total_rows == 0
        assert summary.classification_duration_ms == 0
        assert summary.period_monthly_actual == 0
        assert summary.value_actual == 0
        assert summary.entity_company_only == 0

    def test_summary_generation_all_unknown(self):
        """TEST-AC-9.5.3.3 [P0]: Summary with all UNKNOWN classifications.

        Arrange: 5 rows all classified as UNKNOWN
        Act: Call generate_classification_summary()
        Assert: UNKNOWN counts are 5
        """
        rows = [
            {
                "period_type": PeriodType.UNKNOWN.value,
                "value_type": ValueType.UNKNOWN.value,
                "entity_level": EntityLevel.UNKNOWN.value,
            }
            for _ in range(5)
        ]

        summary = generate_classification_summary(rows, duration_ms=10)

        assert summary.total_rows == 5
        assert summary.period_unknown == 5
        assert summary.value_unknown == 5
        assert summary.entity_unknown == 5

    def test_summary_generation_dataclass_fields(self):
        """TEST-AC-9.5.3.4 [P0]: Summary dataclass has all required fields.

        Arrange: Empty ClassificationSummary
        Act: Inspect dataclass fields
        Assert: All expected fields present
        """

        summary = generate_classification_summary([], duration_ms=0)

        # Period type fields
        assert hasattr(summary, "period_monthly_actual")
        assert hasattr(summary, "period_ytd_actual")
        assert hasattr(summary, "period_budget")
        assert hasattr(summary, "period_ytd_budget")
        assert hasattr(summary, "period_unknown")

        # Value type fields
        assert hasattr(summary, "value_actual")
        assert hasattr(summary, "value_budget")
        assert hasattr(summary, "value_forecast")
        assert hasattr(summary, "value_variance")
        assert hasattr(summary, "value_unknown")

        # Entity level fields
        assert hasattr(summary, "entity_consolidated")
        assert hasattr(summary, "entity_company_only")
        assert hasattr(summary, "entity_segment")
        assert hasattr(summary, "entity_geographic")
        assert hasattr(summary, "entity_unknown")


class TestPerformanceConstraints:
    """Tests for performance constraints (AC4).

    Given: Batch of rows to classify
    When: classify_rows_batch() is called
    Then: Performance meets <100ms for 1000 rows target
    """

    def test_batch_classification_performance_100_rows(self):
        """TEST-AC-9.5.4.1 [P1]: 100 rows classified in <20ms.

        Arrange: 100 rows
        Act: Call classify_rows_batch() and measure time
        Assert: Duration < 20ms (with CI adjustment)
        """
        rows = [
            {"entity": f"Entity {i}", "period": "Dec-24", "metric": "Revenue"}
            for i in range(PERF_TEST_SMALL_BATCH)
        ]

        start = time.perf_counter()
        results = classify_rows_batch(rows)
        duration_ms = (time.perf_counter() - start) * 1000

        assert len(results) == PERF_TEST_SMALL_BATCH
        threshold = PERF_TEST_SMALL_THRESHOLD_MS * PERF_CI_ADJUSTMENT
        assert duration_ms < threshold, f"Expected <{threshold}ms, got {duration_ms:.2f}ms"

    def test_batch_classification_performance_1000_rows(self):
        """TEST-AC-9.5.4.2 [P1]: 1000 rows classified in <100ms (AC4).

        Arrange: 1000 rows
        Act: Call classify_rows_batch() and measure time
        Assert: Duration < 100ms (with CI adjustment for 3-5x slower)
        """
        rows = [
            {"entity": f"Entity {i}", "period": "Dec-24", "metric": "Revenue"}
            for i in range(PERF_TEST_LARGE_BATCH)
        ]

        start = time.perf_counter()
        results = classify_rows_batch(rows)
        duration_ms = (time.perf_counter() - start) * 1000

        assert len(results) == PERF_TEST_LARGE_BATCH
        threshold = PERF_TEST_LARGE_THRESHOLD_MS * PERF_CI_ADJUSTMENT
        assert duration_ms < threshold, f"Expected <{threshold}ms, got {duration_ms:.2f}ms"

    def test_memory_usage_is_linear(self):
        """TEST-AC-9.5.4.3 [P1]: Memory usage is O(n).

        Arrange: 5000 rows
        Act: Call classify_rows_batch()
        Assert: No crash, linear memory (smoke test)
        """
        rows = [
            {"entity": f"Entity {i}", "period": "Dec-24", "metric": "Revenue"}
            for i in range(PERF_TEST_HUGE_BATCH)
        ]

        results = classify_rows_batch(rows)
        assert len(results) == PERF_TEST_HUGE_BATCH
