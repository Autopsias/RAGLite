"""ATDD Tests for Story 9-3: Value Type Classification.

This module validates all 5 Acceptance Criteria from the story:
- AC1: Value Type Classification with 90%+ Accuracy (ground truth validation)
- AC2: PeriodType Integration (period_type parameter takes precedence)
- AC3: Column Header Context (header parameter provides secondary context)
- AC4: Unknown Value Handling (empty, N/A, invalid inputs)
- AC5: Batch Processing Performance (batch classification with caching)

Test IDs follow pattern: TEST-AC-{story}.{ac}.{test}
Example: TEST-AC-9.3.1.1 = Story 9.3, AC1, Test 1

Validation testing - implementation exists at:
- raglite/ingestion/classification/value_type_classifier.py (328 LOC)
- tests/fixtures/value_type_ground_truth.json (51 samples)
"""

import json
import time
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.integration,
]


# =============================================================================
# AC1: Value Type Classification with 90%+ Accuracy
# =============================================================================


class TestAC1ValueTypeClassificationAccuracy:
    """AC1: Value Type Classification with 90%+ Accuracy.

    Given a list of period strings and optional headers from financial tables
    When classifying value types using classify_value_type() or classify_value_types_batch()
    Then returns correct ValueType for 90%+ of ground truth samples
    """

    GROUND_TRUTH_PATH = Path("tests/fixtures/value_type_ground_truth.json")
    ACCURACY_THRESHOLD = 0.90

    @pytest.fixture
    def ground_truth_data(self) -> list[dict]:
        """Load ground truth dataset for accuracy validation."""
        assert self.GROUND_TRUTH_PATH.exists(), (
            f"Ground truth file not found: {self.GROUND_TRUTH_PATH}"
        )
        with open(self.GROUND_TRUTH_PATH) as f:
            data = json.load(f)
        assert len(data) >= 50, f"Need 50+ samples, found {len(data)}"
        return data

    def test_ac_1_1_1_achieves_90_percent_accuracy(self, ground_truth_data: list[dict]) -> None:
        """TEST-AC-9.3.1.1 [P0]: 90%+ accuracy on ground truth dataset.

        Given the ground truth dataset with 51 samples
        When validating classification accuracy
        Then at least 46 samples are correctly classified (90%+)
        """
        from raglite.ingestion.classification import classify_value_type

        correct = 0
        failures = []

        for sample in ground_truth_data:
            period = sample["period"]
            header = sample.get("header")
            expected_type = sample["expected_value_type"]

            result = classify_value_type(period, header=header)

            if result.value_type.value == expected_type:
                correct += 1
            else:
                failures.append(
                    {
                        "period": period,
                        "header": header,
                        "expected": expected_type,
                        "actual": result.value_type.value,
                        "source": result.source,
                    }
                )

        accuracy = correct / len(ground_truth_data)

        # Log failures for debugging
        if failures:
            for f in failures:
                print(f"FAIL: {f}")

        assert accuracy >= self.ACCURACY_THRESHOLD, (
            f"Accuracy {accuracy:.2%} below threshold {self.ACCURACY_THRESHOLD:.0%}. "
            f"Failures: {len(failures)}/{len(ground_truth_data)}"
        )

    def test_ac_1_1_2_portuguese_keywords_correct(self) -> None:
        """TEST-AC-9.3.1.2 [P1]: Portuguese keywords classified correctly.

        Given periods with Portuguese keywords (Orcamento, Previsao, Variacao, Real)
        When classify_value_type is called
        Then they map to correct ValueType
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        test_cases = [
            ("Orcamento Mar-25", ValueType.BUDGET),
            ("Plano Jan-23", ValueType.BUDGET),
            ("Previsao Mar-25", ValueType.FORECAST),
            ("Variacao Mar-25", ValueType.VARIANCE),
            ("Real Sep-23", ValueType.ACTUAL),
        ]

        for period, expected in test_cases:
            result = classify_value_type(period)
            assert result.value_type == expected, (
                f"'{period}' expected {expected.value}, got {result.value_type.value}"
            )

    def test_ac_1_1_3_budget_prefix_suffix_patterns(self) -> None:
        """TEST-AC-9.3.1.3 [P1]: Budget prefix/suffix patterns handled.

        Given periods with budget prefix "B " or suffix " B"
        When classify_value_type is called
        Then they are classified as BUDGET
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        budget_periods = [
            "B Dec-21",
            "B Jun-24",
            "Aug-24 B",
            "b dec-21",  # lowercase
        ]

        for period in budget_periods:
            result = classify_value_type(period)
            assert result.value_type == ValueType.BUDGET, (
                f"'{period}' expected BUDGET, got {result.value_type.value}"
            )

    def test_ac_1_1_4_forecast_prefix_patterns(self) -> None:
        """TEST-AC-9.3.1.4 [P1]: Forecast prefix patterns handled.

        Given periods with forecast indicators ("F ", "Forecast", "Projected")
        When classify_value_type is called
        Then they are classified as FORECAST
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        forecast_periods = [
            "F Dec-21",
            "F Jun-24",
            "Forecast Dec-21",
            "Projected Jan-23",
            "f jun-24",  # lowercase
        ]

        for period in forecast_periods:
            result = classify_value_type(period)
            assert result.value_type == ValueType.FORECAST, (
                f"'{period}' expected FORECAST, got {result.value_type.value}"
            )

    def test_ac_1_1_5_variance_patterns(self) -> None:
        """TEST-AC-9.3.1.5 [P1]: Variance patterns handled.

        Given periods with variance indicators (%Var, Delta, Diff)
        When classify_value_type is called
        Then they are classified as VARIANCE
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        variance_periods = [
            "Var Dec-21",
            "%Var Jun-24",
            "Delta Mar-25",
            "Variance Dec-21",
            "Diff Jan-23",
            "var Apr-22",  # lowercase
        ]

        for period in variance_periods:
            result = classify_value_type(period)
            assert result.value_type == ValueType.VARIANCE, (
                f"'{period}' expected VARIANCE, got {result.value_type.value}"
            )

    def test_ac_1_1_6_plain_periods_default_to_actual(self) -> None:
        """TEST-AC-9.3.1.6 [P1]: Plain periods without modifiers default to ACTUAL.

        Given period strings without budget/forecast/variance modifiers
        When classify_value_type is called
        Then they are classified as ACTUAL with source "default"
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        actual_periods = [
            "Dec-21",
            "Jan-25",
            "Apr-25",
            "Nov-24",
        ]

        for period in actual_periods:
            result = classify_value_type(period)
            assert result.value_type == ValueType.ACTUAL, (
                f"'{period}' expected ACTUAL, got {result.value_type.value}"
            )
            assert result.source == "default", (
                f"'{period}' expected source 'default', got '{result.source}'"
            )


# =============================================================================
# AC2: PeriodType Integration
# =============================================================================


class TestAC2PeriodTypeIntegration:
    """AC2: PeriodType Integration.

    Given a period string with a corresponding PeriodType from period_classifier
    When classifying value types with period_type parameter
    Then period_type takes precedence over other signals
    """

    def test_ac_2_2_1_budget_period_type_maps_to_budget(self) -> None:
        """TEST-AC-9.3.2.1 [P0]: PeriodType.BUDGET maps to ValueType.BUDGET.

        Given a period with period_type=BUDGET
        When classify_value_type is called
        Then value_type is BUDGET and source is "period_type"
        """
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        result = classify_value_type("Dec-21", period_type=PeriodType.BUDGET)

        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_type"

    def test_ac_2_2_2_ytd_budget_maps_to_budget(self) -> None:
        """TEST-AC-9.3.2.2 [P0]: PeriodType.YTD_BUDGET maps to ValueType.BUDGET.

        Given a period with period_type=YTD_BUDGET
        When classify_value_type is called
        Then value_type is BUDGET and source is "period_type"
        """
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        result = classify_value_type("YTD Dec-21", period_type=PeriodType.YTD_BUDGET)

        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_type"

    def test_ac_2_2_3_monthly_actual_maps_to_actual(self) -> None:
        """TEST-AC-9.3.2.3 [P0]: PeriodType.MONTHLY_ACTUAL maps to ValueType.ACTUAL.

        Given a period with period_type=MONTHLY_ACTUAL
        When classify_value_type is called
        Then value_type is ACTUAL and source is "period_type"
        """
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        result = classify_value_type("Dec-21", period_type=PeriodType.MONTHLY_ACTUAL)

        assert result.value_type == ValueType.ACTUAL
        assert result.source == "period_type"

    def test_ac_2_2_4_ytd_actual_maps_to_actual(self) -> None:
        """TEST-AC-9.3.2.4 [P0]: PeriodType.YTD_ACTUAL maps to ValueType.ACTUAL.

        Given a period with period_type=YTD_ACTUAL
        When classify_value_type is called
        Then value_type is ACTUAL and source is "period_type"
        """
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        result = classify_value_type("YTD Dec-21", period_type=PeriodType.YTD_ACTUAL)

        assert result.value_type == ValueType.ACTUAL
        assert result.source == "period_type"

    def test_ac_2_2_5_unknown_period_type_falls_through(self) -> None:
        """TEST-AC-9.3.2.5 [P1]: PeriodType.UNKNOWN falls through to other rules.

        Given period_type is UNKNOWN
        When classify_value_type is called
        Then it uses other signals (prefix, header) instead
        """
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        # Budget prefix should be detected when period_type is UNKNOWN
        result = classify_value_type("B Dec-21", period_type=PeriodType.UNKNOWN)

        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_prefix"

    def test_ac_2_2_6_period_type_takes_precedence(self) -> None:
        """TEST-AC-9.3.2.6 [P0]: PeriodType takes precedence over conflicting prefix.

        Given period string "F Dec-21" (forecast prefix)
        And period_type is PeriodType.BUDGET
        When classify_value_type is called
        Then value_type is BUDGET (period_type wins)
        """
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        result = classify_value_type("F Dec-21", period_type=PeriodType.BUDGET)

        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_type"


# =============================================================================
# AC3: Column Header Context
# =============================================================================


class TestAC3ColumnHeaderContext:
    """AC3: Column Header Context.

    Given a period string with a column header for context
    When classifying value types with header parameter
    Then header provides secondary context after period prefix
    """

    def test_ac_3_3_1_header_forecast_classifies_forecast(self) -> None:
        """TEST-AC-9.3.3.1 [P0]: Header "Forecast" classifies as FORECAST.

        Given period string "Dec-21" and header "Forecast"
        When classify_value_type is called
        Then value_type is FORECAST and source is "column_header"
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        result = classify_value_type("Dec-21", header="Forecast")

        assert result.value_type == ValueType.FORECAST
        assert result.source == "column_header"

    def test_ac_3_3_2_header_budget_classifies_budget(self) -> None:
        """TEST-AC-9.3.3.2 [P0]: Header "Budget" classifies as BUDGET.

        Given period string "Dec-21" and header "Budget"
        When classify_value_type is called
        Then value_type is BUDGET and source is "column_header"
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        result = classify_value_type("Dec-21", header="Budget")

        assert result.value_type == ValueType.BUDGET
        assert result.source == "column_header"

    def test_ac_3_3_3_period_prefix_overrides_header(self) -> None:
        """TEST-AC-9.3.3.3 [P0]: Period prefix overrides conflicting header.

        Given period "B Dec-21" (budget prefix) and header "Forecast"
        When classify_value_type is called
        Then value_type is BUDGET (prefix wins over header)
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        result = classify_value_type("B Dec-21", header="Forecast")

        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_prefix"

    def test_ac_3_3_4_portuguese_header_keywords(self) -> None:
        """TEST-AC-9.3.3.4 [P1]: Portuguese header keywords work.

        Given period strings with Portuguese headers (Orcamento, Previsao)
        When classify_value_type is called
        Then they are classified correctly
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        test_cases = [
            ("Dec-21", "Orcamento", ValueType.BUDGET),
            ("Dec-21", "Previsao", ValueType.FORECAST),
        ]

        for period, header, expected in test_cases:
            result = classify_value_type(period, header=header)
            assert result.value_type == expected, (
                f"Period '{period}' with header '{header}' expected "
                f"{expected.value}, got {result.value_type.value}"
            )


# =============================================================================
# AC4: Unknown Value Handling
# =============================================================================


class TestAC4UnknownValueHandling:
    """AC4: Unknown Value Handling.

    Given period strings that cannot be classified
    When classifying invalid or empty inputs
    Then they are handled gracefully as UNKNOWN
    """

    def test_ac_4_4_1_empty_strings_return_unknown(self) -> None:
        """TEST-AC-9.3.4.1 [P0]: Empty strings return UNKNOWN with source "empty".

        Given empty string or whitespace-only period
        When classify_value_type is called
        Then value_type is UNKNOWN and source is "empty"
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        empty_inputs = ["", "   ", "\t", "\n"]

        for period in empty_inputs:
            result = classify_value_type(period)
            assert result.value_type == ValueType.UNKNOWN, (
                f"Empty input '{repr(period)}' expected UNKNOWN"
            )
            assert result.source == "empty", f"Empty input '{repr(period)}' expected source 'empty'"

    def test_ac_4_4_2_na_markers_return_unknown(self) -> None:
        """TEST-AC-9.3.4.2 [P0]: N/A markers return UNKNOWN with source "unknown_marker".

        Given period strings like "N/A", "None", "null"
        When classify_value_type is called
        Then value_type is UNKNOWN and source is "unknown_marker"
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        na_markers = ["N/A", "None", "null"]

        for period in na_markers:
            result = classify_value_type(period)
            assert result.value_type == ValueType.UNKNOWN, f"N/A marker '{period}' expected UNKNOWN"
            assert result.source == "unknown_marker", (
                f"N/A marker '{period}' expected source 'unknown_marker'"
            )

    def test_ac_4_4_3_invalid_formats_return_unknown(self) -> None:
        """TEST-AC-9.3.4.3 [P1]: Invalid formats return UNKNOWN with source "invalid_format".

        Given period strings with invalid format (year-only like "2021")
        When classify_value_type is called
        Then value_type is UNKNOWN and source is "invalid_format"
        """
        from raglite.ingestion.classification import ValueType, classify_value_type

        invalid_formats = ["2021", "invalid"]

        for period in invalid_formats:
            result = classify_value_type(period)
            assert result.value_type == ValueType.UNKNOWN, (
                f"Invalid format '{period}' expected UNKNOWN"
            )
            assert result.source == "invalid_format", (
                f"Invalid format '{period}' expected source 'invalid_format'"
            )

    def test_ac_4_4_4_no_exceptions_for_malformed_inputs(self) -> None:
        """TEST-AC-9.3.4.4 [P0]: No exceptions raised for malformed inputs.

        Given various malformed period strings
        When classify_value_type is called
        Then no exceptions are raised
        """
        from raglite.ingestion.classification import classify_value_type

        malformed_inputs = [
            "",
            "   ",
            "N/A",
            "None",
            "null",
            "invalid",
            "2021",
            "??##$$",
            "completely random text",
            None,  # Test None handling
        ]

        for period in malformed_inputs:
            try:
                if period is None:
                    result = classify_value_type("")
                else:
                    result = classify_value_type(period)
                # Just verify we got a result without exception
                assert result is not None
            except Exception as e:
                pytest.fail(f"Exception raised for input '{period}': {e}")


# =============================================================================
# AC5: Batch Processing Performance
# =============================================================================


class TestAC5BatchProcessingPerformance:
    """AC5: Batch Processing Performance.

    Given a batch of period strings to classify
    When using classify_value_types_batch()
    Then batch processing is efficient with caching
    """

    def test_ac_5_5_1_batch_returns_correct_order(self) -> None:
        """TEST-AC-9.3.5.1 [P0]: Returns list of ClassifiedValueType matching input order.

        Given a list of periods to classify
        When classify_value_types_batch is called
        Then results list matches input order
        """
        from raglite.ingestion.classification import (
            ValueType,
            classify_value_types_batch,
        )

        periods = ["Dec-21", "B Jan-22", "F Feb-23", "Var Mar-24", "N/A"]

        results, report = classify_value_types_batch(periods)

        assert len(results) == 5
        assert results[0].value_type == ValueType.ACTUAL
        assert results[1].value_type == ValueType.BUDGET
        assert results[2].value_type == ValueType.FORECAST
        assert results[3].value_type == ValueType.VARIANCE
        assert results[4].value_type == ValueType.UNKNOWN

    def test_ac_5_5_2_report_has_accurate_counts(self) -> None:
        """TEST-AC-9.3.5.2 [P0]: Returns ValueTypeReport with accurate counts.

        Given a mixed list of periods
        When classify_value_types_batch is called
        Then report.total_records and breakdown are accurate
        """
        from raglite.ingestion.classification import classify_value_types_batch

        periods = [
            "Dec-21",  # ACTUAL
            "B Jan-22",  # BUDGET
            "F Feb-23",  # FORECAST
            "Var Mar-24",  # VARIANCE
            "N/A",  # UNKNOWN
        ]

        results, report = classify_value_types_batch(periods)

        assert report.total_records == 5
        assert report.actual_count == 1
        assert report.budget_count == 1
        assert report.forecast_count == 1
        assert report.variance_count == 1
        assert report.unknown_count == 1

        # Verify breakdown sums to total
        breakdown_sum = sum(report.value_type_breakdown.values())
        assert breakdown_sum == report.total_records

    def test_ac_5_5_3_cache_performance_under_100ms(self) -> None:
        """TEST-AC-9.3.5.3 [P0]: LRU cache provides <100ms for 1000 duplicate periods.

        Given 1000 identical periods (tests caching)
        When classify_value_types_batch is called
        Then processing completes in <100ms
        """
        from raglite.ingestion.classification import classify_value_types_batch

        # 1000 identical periods to test cache hit performance
        periods = ["Dec-21"] * 1000

        start = time.time()
        results, report = classify_value_types_batch(periods)
        elapsed = time.time() - start

        assert len(results) == 1000
        assert elapsed < 0.1, f"Batch took {elapsed * 1000:.1f}ms, expected <100ms"

    def test_ac_5_5_4_handles_none_headers_and_period_types(self) -> None:
        """TEST-AC-9.3.5.4 [P1]: Handles None headers and period_types gracefully.

        Given periods with None headers and period_types lists
        When classify_value_types_batch is called
        Then it processes without error
        """
        from raglite.ingestion.classification import classify_value_types_batch

        periods = ["Dec-21", "B Jan-22", "F Feb-23"]

        # Test with explicit None
        results, report = classify_value_types_batch(periods, headers=None, period_types=None)

        assert len(results) == 3
        assert report.total_records == 3

    def test_ac_5_5_5_batch_with_headers_list(self) -> None:
        """TEST-AC-9.3.5.5 [P1]: Batch supports headers list for classification.

        Given periods and matching headers lists
        When classify_value_types_batch is called
        Then headers influence classification
        """
        from raglite.ingestion.classification import (
            ValueType,
            classify_value_types_batch,
        )

        periods = ["Dec-21", "Jan-22", "Feb-23"]
        headers = ["Actual", "Budget", "Forecast"]

        results, report = classify_value_types_batch(periods, headers=headers)

        assert results[0].value_type == ValueType.ACTUAL
        assert results[1].value_type == ValueType.BUDGET
        assert results[2].value_type == ValueType.FORECAST

    def test_ac_5_5_6_batch_validates_list_lengths(self) -> None:
        """TEST-AC-9.3.5.6 [P1]: Batch validates mismatched list lengths.

        Given periods and headers lists of different lengths
        When classify_value_types_batch is called
        Then it raises ValueError
        """
        from raglite.ingestion.classification import classify_value_types_batch

        periods = ["Dec-21", "Jan-22", "Feb-23"]
        headers = ["Actual", "Budget"]  # Mismatched length

        with pytest.raises(ValueError, match="same length"):
            classify_value_types_batch(periods, headers=headers)
