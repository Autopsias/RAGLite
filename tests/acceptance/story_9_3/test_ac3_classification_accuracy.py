"""ATDD tests for Story 9.3 AC3 - Classification Accuracy Target.

TDD RED Phase: All tests MUST fail initially because the value_type_classifier
does not exist yet and no ground truth dataset exists.

Test IDs follow pattern: TEST-AC-9.3.3.{test}

BDD Acceptance Criteria:
Given a ground truth dataset of 50+ value type examples from production PDFs
When the value type classifier processes all examples
Then it achieves 90%+ classification accuracy
And actual values (no modifier) are correctly classified as ACTUAL
And budget indicators ("B ", "Budget", "Orcamento") are classified as BUDGET
And forecast indicators ("F ", "Forecast", "Previsao") are classified as FORECAST
And variance indicators ("Var", "Delta", "%Var") are classified as VARIANCE
And unknown formats are properly flagged as UNKNOWN
"""

import json
from pathlib import Path

import pytest


class TestAC3ClassificationAccuracyTarget:
    """AC3: Classification Accuracy Target.

    Given a ground truth dataset of 50+ value type examples from production PDFs
    When the value type classifier processes all examples
    Then it achieves 90%+ classification accuracy
    """

    @pytest.fixture
    def ground_truth_data(self) -> list[dict]:
        """Load ground truth dataset for accuracy validation."""
        ground_truth_path = Path(
            "tests/fixtures/value_type_ground_truth.json"
        )

        # Ground truth file should exist for AC3 validation
        assert ground_truth_path.exists(), (
            f"Ground truth file not found: {ground_truth_path}. "
            "Task 4.1 must create this file."
        )

        with open(ground_truth_path) as f:
            data = json.load(f)

        # AC3 requires 50+ examples
        assert len(data) >= 50, f"Need 50+ examples, found {len(data)}"

        return data

    def test_ac_3_1_1_achieves_90_percent_accuracy(
        self, ground_truth_data: list[dict]
    ) -> None:
        """TEST-AC-9.3.3.1 [P0]: Achieves 90%+ classification accuracy.

        Given a ground truth dataset with 50+ examples
        When the classifier processes all examples
        Then accuracy is >= 90%
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import classify_value_type

        # Act: Classify all ground truth examples
        correct = 0
        total = len(ground_truth_data)

        for entry in ground_truth_data:
            period = entry["period"]
            expected_type = entry["expected_value_type"]

            result = classify_value_type(period)

            # Assert per entry: Check value_type classification
            if result.value_type.value == expected_type:
                correct += 1

        accuracy = (correct / total) * 100

        # Assert: Accuracy meets 90% target
        assert accuracy >= 90.0, (
            f"Accuracy {accuracy:.1f}% below 90% target. "
            f"Correct: {correct}/{total}"
        )

    def test_ac_3_2_1_actual_values_classified_correctly(self) -> None:
        """TEST-AC-9.3.3.2 [P0]: Actual values (no modifier) classified as ACTUAL.

        Given period strings without budget/forecast/variance modifiers
        When classify_value_type is called
        Then they are classified as ACTUAL
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Standard periods without modifiers should be ACTUAL
        actual_periods = [
            "Dec-21",
            "Jan-25",
            "YTD Dec-21",
            "YTD Jun-24",
            "Mar-23",
        ]

        # Act & Assert: All should be ACTUAL
        for period in actual_periods:
            result = classify_value_type(period)
            assert result.value_type == ValueType.ACTUAL, (
                f"'{period}' should be ACTUAL, got {result.value_type}"
            )

    def test_ac_3_2_2_budget_indicators_classified_correctly(self) -> None:
        """TEST-AC-9.3.3.3 [P0]: Budget indicators classified as BUDGET.

        Given periods with budget indicators ("B ", "Budget", "Orcamento")
        When classify_value_type is called
        Then they are classified as BUDGET
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Budget indicator periods
        budget_periods = [
            "B Dec-21",
            "B Jan-25",
            "Dec-21 B",
            "Budget Dec-21",
            "Orcamento Dez-21",
        ]

        # Act & Assert: All should be BUDGET
        for period in budget_periods:
            result = classify_value_type(period)
            assert result.value_type == ValueType.BUDGET, (
                f"'{period}' should be BUDGET, got {result.value_type}"
            )

    def test_ac_3_2_3_forecast_indicators_classified_correctly(self) -> None:
        """TEST-AC-9.3.3.4 [P0]: Forecast indicators classified as FORECAST.

        Given periods with forecast indicators ("F ", "Forecast", "Previsao")
        When classify_value_type is called
        Then they are classified as FORECAST
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Forecast indicator periods
        forecast_periods = [
            "F Dec-21",
            "F Jan-25",
            "Forecast Dec-21",
            "Previsao Dez-21",
            "Projected Dec-21",
        ]

        # Act & Assert: All should be FORECAST
        for period in forecast_periods:
            result = classify_value_type(period)
            assert result.value_type == ValueType.FORECAST, (
                f"'{period}' should be FORECAST, got {result.value_type}"
            )

    def test_ac_3_2_4_variance_indicators_classified_correctly(self) -> None:
        """TEST-AC-9.3.3.5 [P0]: Variance indicators classified as VARIANCE.

        Given periods with variance indicators ("Var", "Delta", "%Var")
        When classify_value_type is called
        Then they are classified as VARIANCE
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Variance indicator periods
        variance_periods = [
            "Var Dec-21",
            "%Var Dec-21",
            "Delta Dec-21",
            "Variance Dec-21",
            "Variacao Dez-21",
        ]

        # Act & Assert: All should be VARIANCE
        for period in variance_periods:
            result = classify_value_type(period)
            assert result.value_type == ValueType.VARIANCE, (
                f"'{period}' should be VARIANCE, got {result.value_type}"
            )

    def test_ac_3_2_5_unknown_formats_flagged_correctly(self) -> None:
        """TEST-AC-9.3.3.6 [P0]: Unknown formats flagged as UNKNOWN.

        Given unrecognizable period strings
        When classify_value_type is called
        Then they are classified as UNKNOWN
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Unknown format periods
        unknown_periods = [
            "",
            "   ",
            "N/A",
            "completely random text",
            "??##$$",
        ]

        # Act & Assert: All should be UNKNOWN
        for period in unknown_periods:
            result = classify_value_type(period)
            assert result.value_type == ValueType.UNKNOWN, (
                f"'{period}' should be UNKNOWN, got {result.value_type}"
            )
