"""Acceptance tests for AC1: Period Type Classification with 95%+ Accuracy.

TEST-AC-9.2.1.x tests validate that the period classifier correctly identifies
period types from financial data with >=95% accuracy on ground truth.

TDD RED Phase: These tests define EXPECTED BEHAVIOR from acceptance criteria.
All tests MUST fail initially.
"""

import json
from pathlib import Path

import pytest

# Ground truth file location
GROUND_TRUTH_PATH = Path(__file__).parents[2] / "fixtures" / "period_classification_ground_truth.json"
ACCURACY_THRESHOLD = 0.95


class TestAC1PeriodClassificationAccuracy:
    """AC1: Period Type Classification with 95%+ Accuracy.

    Given a list of period strings from financial tables
    When classifying periods using classify_period() or classify_periods_batch()
    Then returns correct PeriodType for 95%+ of ground truth samples (67 samples)
    """

    def test_ac1_1_ground_truth_accuracy_exceeds_95_percent(self) -> None:
        """TEST-AC-9.2.1.1 [P0]: 95%+ accuracy on ground truth dataset.

        Given the ground truth dataset with 67 samples
        When classifying all periods
        Then at least 64 samples are correctly classified (95.5%+)
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        # Load ground truth
        with open(GROUND_TRUTH_PATH) as f:
            ground_truth = json.load(f)

        correct = 0
        failures = []

        for sample in ground_truth:
            period = sample["period"]
            expected_type = sample["expected_type"]
            expected_normalized = sample.get("expected_normalized")

            result = classify_period(period)

            # Map enum value to expected string format
            actual_type = result.period_type.value

            type_match = actual_type == expected_type
            norm_match = result.normalized == expected_normalized

            if type_match and norm_match:
                correct += 1
            else:
                failures.append({
                    "period": period,
                    "expected_type": expected_type,
                    "actual_type": actual_type,
                    "expected_normalized": expected_normalized,
                    "actual_normalized": result.normalized,
                })

        accuracy = correct / len(ground_truth)

        # Log failures for debugging
        if failures:
            for f in failures[:10]:  # Limit output
                print(f"FAIL: {f}")

        assert accuracy >= ACCURACY_THRESHOLD, (
            f"Accuracy {accuracy:.2%} below threshold {ACCURACY_THRESHOLD:.0%}. "
            f"Failures: {len(failures)}/{len(ground_truth)}"
        )

    @pytest.mark.parametrize(
        "portuguese_period,expected_normalized",
        [
            ("Dez-21", "Dec-21"),
            ("Fev-24", "Feb-24"),
            ("Abr-23", "Apr-23"),
            ("Mai-22", "May-22"),
            ("Ago-21", "Aug-21"),
            ("Set-20", "Sep-20"),
            ("Out-19", "Oct-19"),
        ],
    )
    def test_ac1_2_portuguese_month_abbreviations(
        self, portuguese_period: str, expected_normalized: str
    ) -> None:
        """TEST-AC-9.2.1.2 [P0]: Portuguese months classified correctly.

        Given Portuguese month abbreviations (Dez, Fev, Abr, Mai, Ago, Set, Out)
        When classify_period() is called
        Then period_type is MONTHLY_ACTUAL
        And normalized is the English equivalent
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        result = classify_period(portuguese_period)

        assert result.period_type == PeriodType.MONTHLY_ACTUAL
        assert result.normalized == expected_normalized
        assert result.is_usable is True

    @pytest.mark.parametrize(
        "four_digit_year,expected_normalized",
        [
            ("Dec-2017", "Dec-17"),
            ("Jan-2025", "Jan-25"),
            ("Dez-2021", "Dec-21"),
        ],
    )
    def test_ac1_3_four_digit_year_formats(
        self, four_digit_year: str, expected_normalized: str
    ) -> None:
        """TEST-AC-9.2.1.3 [P0]: 4-digit year formats handled correctly.

        Given period strings with 4-digit years (2024 -> 24, Dec-2017 -> Dec-17)
        When classify_period() is called
        Then normalized uses 2-digit year format
        """
        from raglite.ingestion.classification import PeriodType, classify_period

        result = classify_period(four_digit_year)

        assert result.period_type == PeriodType.MONTHLY_ACTUAL
        assert result.normalized == expected_normalized

    @pytest.mark.parametrize(
        "period,expected_type",
        [
            ("Dec-21", "MONTHLY_ACTUAL"),
            ("YTD Dec-21", "YTD_ACTUAL"),
        ],
    )
    def test_ac1_4_normalized_period_extraction(
        self, period: str, expected_type: str
    ) -> None:
        """TEST-AC-9.2.1.4 [P0]: Normalized period extracted in Mon-YY format.

        Given a usable period type (MONTHLY_ACTUAL or YTD_ACTUAL)
        When classify_period() is called
        Then normalized contains the Mon-YY format
        """
        from raglite.ingestion.classification import classify_period

        result = classify_period(period)

        assert result.period_type.name == expected_type
        assert result.normalized is not None
        # Check Mon-YY format pattern
        assert len(result.normalized) == 6  # "Dec-21" is 6 chars
        assert result.normalized[3] == "-"

    @pytest.mark.parametrize(
        "period,expected_usable",
        [
            ("Dec-21", True),       # MONTHLY_ACTUAL
            ("YTD Dec-21", True),   # YTD_ACTUAL
            ("B Dec-21", False),    # BUDGET
            ("Dec-21 B", False),    # BUDGET
            ("YTD B Dec-21", False), # YTD_BUDGET
            ("N/A", False),         # UNKNOWN
        ],
    )
    def test_ac1_5_is_usable_only_for_actual_types(
        self, period: str, expected_usable: bool
    ) -> None:
        """TEST-AC-9.2.1.5 [P0]: is_usable=True only for MONTHLY_ACTUAL and YTD_ACTUAL.

        Given various period types
        When classify_period() is called
        Then is_usable is True only for MONTHLY_ACTUAL and YTD_ACTUAL
        """
        from raglite.ingestion.classification import classify_period

        result = classify_period(period)

        assert result.is_usable is expected_usable
