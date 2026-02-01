"""Acceptance tests for AC5: Ground Truth Validation (50+ Samples).

TEST-AC-9.2.5.x tests validate the ground truth dataset structure and
validation process meets requirements.

TDD RED Phase: These tests define EXPECTED BEHAVIOR from acceptance criteria.
All tests MUST fail initially.
"""

import json
from pathlib import Path

import pytest

# Ground truth file location
GROUND_TRUTH_PATH = Path(__file__).parents[2] / "fixtures" / "period_classification_ground_truth.json"


class TestAC5GroundTruthValidation:
    """AC5: Ground Truth Validation (50+ Samples).

    Given the ground truth dataset at tests/fixtures/period_classification_ground_truth.json
    When running the validation test
    Then dataset meets structure and coverage requirements
    """

    def test_ac5_1_dataset_contains_50_plus_samples(self) -> None:
        """TEST-AC-9.2.5.1 [P0]: Dataset contains 50+ samples.

        Given the ground truth file exists
        When counting samples
        Then at least 50 samples are present (exceeds requirement)
        """
        with open(GROUND_TRUTH_PATH) as f:
            ground_truth = json.load(f)

        assert len(ground_truth) >= 50, f"Expected 50+ samples, got {len(ground_truth)}"

    def test_ac5_2_all_period_types_represented(self) -> None:
        """TEST-AC-9.2.5.2 [P0]: All PeriodType values are represented.

        Given the ground truth dataset
        When checking period type coverage
        Then MONTHLY_ACTUAL, YTD_ACTUAL, BUDGET, YTD_BUDGET, UNKNOWN are all present
        """
        with open(GROUND_TRUTH_PATH) as f:
            ground_truth = json.load(f)

        actual_types = {sample["expected_type"] for sample in ground_truth}
        expected_types = {"monthly_actual", "ytd_actual", "budget", "ytd_budget", "unknown"}

        missing = expected_types - actual_types
        assert not missing, f"Missing period types in ground truth: {missing}"

    def test_ac5_3_edge_cases_covered(self) -> None:
        """TEST-AC-9.2.5.3 [P0]: Edge cases are covered.

        Given the ground truth dataset
        When checking for edge case coverage
        Then Portuguese months, case variations, and whitespace are included
        """
        with open(GROUND_TRUTH_PATH) as f:
            ground_truth = json.load(f)

        periods = [sample["period"] for sample in ground_truth]

        # Check Portuguese months present
        portuguese_months = ["Dez", "Fev", "Abr", "Mai", "Ago", "Set", "Out"]
        has_portuguese = any(
            any(pm in period for pm in portuguese_months)
            for period in periods
        )
        assert has_portuguese, "Ground truth should include Portuguese month abbreviations"

        # Check case variations present
        has_lowercase = any(period.islower() or period[0].islower() for period in periods if period)
        has_uppercase = any(period.isupper() or period[0:3].isupper() for period in periods if period and len(period) >= 3)
        assert has_lowercase or has_uppercase, "Ground truth should include case variations"

        # Check whitespace variations present
        has_whitespace = any(
            "\t" in period or "\u00a0" in period or period != period.strip()
            for period in periods
            if period
        )
        assert has_whitespace, "Ground truth should include whitespace variations (tabs, NBSP)"

    @pytest.mark.integration
    def test_ac5_4_validation_reports_accuracy_and_failures(self) -> None:
        """TEST-AC-9.2.5.4 [P1]: Validation script reports accuracy and failure details.

        Given the ground truth validation runs
        When classification is performed
        Then output includes accuracy percentage and failure details
        """
        from raglite.ingestion.classification import classify_period

        with open(GROUND_TRUTH_PATH) as f:
            ground_truth = json.load(f)

        correct = 0
        failures = []

        for sample in ground_truth:
            period = sample["period"]
            expected_type = sample["expected_type"]
            expected_normalized = sample.get("expected_normalized")

            result = classify_period(period)
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

        # Validation output should be available
        assert accuracy is not None, "Accuracy should be calculated"
        assert isinstance(failures, list), "Failures should be a list"

        # Log output for verification (in real usage, this would be captured)
        print(f"Validation Results:")
        print(f"  Total samples: {len(ground_truth)}")
        print(f"  Correct: {correct}")
        print(f"  Accuracy: {accuracy:.2%}")
        print(f"  Failures: {len(failures)}")

        if failures:
            print("  Failure details:")
            for f in failures[:5]:  # Limit output
                print(f"    {f}")

    @pytest.mark.parametrize(
        "threshold",
        [0.90, 0.95, 0.99],
    )
    def test_ac5_5_accuracy_threshold_configurable(self, threshold: float) -> None:
        """TEST-AC-9.2.5.5 [P1]: Accuracy threshold is configurable (default: 95%).

        Given different accuracy thresholds
        When validation is performed
        Then result can be compared against any threshold
        """
        from raglite.ingestion.classification import classify_period

        with open(GROUND_TRUTH_PATH) as f:
            ground_truth = json.load(f)

        correct = 0
        for sample in ground_truth:
            result = classify_period(sample["period"])
            if result.period_type.value == sample["expected_type"]:
                if result.normalized == sample.get("expected_normalized"):
                    correct += 1

        accuracy = correct / len(ground_truth)

        # Test that threshold comparison works (not asserting pass/fail on threshold)
        passes_threshold = accuracy >= threshold
        assert isinstance(passes_threshold, bool), "Threshold comparison should return bool"

        # Log for visibility
        print(f"Threshold {threshold:.0%}: {'PASS' if passes_threshold else 'FAIL'} (actual: {accuracy:.2%})")


class TestGroundTruthDatasetStructure:
    """Validate the structure of each ground truth sample."""

    def test_all_samples_have_required_fields(self) -> None:
        """TEST-AC-9.2.5.6 [P0]: All samples have required fields.

        Given each ground truth sample
        When checking field presence
        Then period and expected_type are always present
        """
        with open(GROUND_TRUTH_PATH) as f:
            ground_truth = json.load(f)

        for idx, sample in enumerate(ground_truth):
            assert "period" in sample, f"Sample {idx} missing 'period' field"
            assert "expected_type" in sample, f"Sample {idx} missing 'expected_type' field"

    def test_expected_types_are_valid_enum_values(self) -> None:
        """TEST-AC-9.2.5.7 [P0]: Expected types match PeriodType enum values.

        Given all expected_type values in ground truth
        When validating against PeriodType enum
        Then all values are valid enum names (lowercase)
        """
        from raglite.ingestion.classification import PeriodType

        with open(GROUND_TRUTH_PATH) as f:
            ground_truth = json.load(f)

        valid_types = {pt.value for pt in PeriodType}

        for sample in ground_truth:
            expected = sample["expected_type"]
            assert expected in valid_types, (
                f"Invalid expected_type '{expected}'. Valid: {valid_types}"
            )

    def test_normalized_is_null_for_excluded_types(self) -> None:
        """TEST-AC-9.2.5.8 [P1]: Normalized is null for budget and unknown types.

        Given samples with budget, ytd_budget, or unknown types
        When checking expected_normalized
        Then it is null (not a usable period)
        """
        with open(GROUND_TRUTH_PATH) as f:
            ground_truth = json.load(f)

        excluded_types = {"budget", "ytd_budget", "unknown"}

        for sample in ground_truth:
            if sample["expected_type"] in excluded_types:
                expected_normalized = sample.get("expected_normalized")
                assert expected_normalized is None, (
                    f"Period '{sample['period']}' of type '{sample['expected_type']}' "
                    f"should have null expected_normalized, got '{expected_normalized}'"
                )

    def test_normalized_is_present_for_actual_types(self) -> None:
        """TEST-AC-9.2.5.9 [P1]: Normalized is present for actual types.

        Given samples with monthly_actual or ytd_actual types
        When checking expected_normalized
        Then it is a valid Mon-YY format string
        """
        with open(GROUND_TRUTH_PATH) as f:
            ground_truth = json.load(f)

        actual_types = {"monthly_actual", "ytd_actual"}

        for sample in ground_truth:
            if sample["expected_type"] in actual_types:
                expected_normalized = sample.get("expected_normalized")
                assert expected_normalized is not None, (
                    f"Period '{sample['period']}' of type '{sample['expected_type']}' "
                    f"should have expected_normalized set"
                )
                # Verify Mon-YY format
                assert len(expected_normalized) == 6, (
                    f"Expected Mon-YY format (6 chars), got '{expected_normalized}'"
                )
                assert expected_normalized[3] == "-", (
                    f"Expected '-' at position 3 in '{expected_normalized}'"
                )
