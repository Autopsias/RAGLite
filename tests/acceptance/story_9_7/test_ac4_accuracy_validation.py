"""ATDD tests for Story 9.7 AC4 - Classification Accuracy Validation.

TDD RED Phase: All tests MUST fail initially because:
- validate-classification-accuracy.py script does not exist
- tests/fixtures/classification_ground_truth.json does not exist

Test IDs follow pattern: TEST-AC-9.7.4.{test}

BDD Acceptance Criteria:
Given a ground truth dataset exists with expected classifications:
  - tests/fixtures/classification_ground_truth.json (50+ manually verified rows)
When comparing re-ingested data against ground truth
Then period_type accuracy is >= 95% (per Epic 9 AC1)
And value_type accuracy is >= 90%
And entity_level accuracy is >= 90%
And misclassifications are logged for review
And accuracy report is generated with:
  | Metric       | Expected | Actual | Status |
  |--------------|----------|--------|--------|
  | period_type  | >= 95%   | X%     | PASS/FAIL |
  | value_type   | >= 90%   | X%     | PASS/FAIL |
  | entity_level | >= 90%   | X%     | PASS/FAIL |
"""

import pytest

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.story_9_7,
    pytest.mark.atdd,
]


class TestAC4ClassificationAccuracyValidation:
    """AC4: Classification Accuracy Validation.

    Given ground truth exists
    When comparing classifications
    Then accuracy meets Epic 9 targets (95%/90%/90%)
    """

    def test_ac_4_1_1_ground_truth_file_exists(self) -> None:
        """TEST-AC-9.7.4.1 [P0]: Ground truth JSON file exists.

        Given the test fixtures directory exists
        When we check for classification_ground_truth.json
        Then the file exists with 50+ entries
        """
        # Arrange: Expected file path
        from pathlib import Path

        gt_path = Path("tests/fixtures/classification_ground_truth.json")

        # Assert: File exists
        # RED STATE: File does not exist yet
        assert gt_path.exists(), f"Ground truth file not found at {gt_path}"

    def test_ac_4_1_2_ground_truth_has_50_entries(self) -> None:
        """TEST-AC-9.7.4.2 [P0]: Ground truth has at least 50 entries.

        Given the ground truth file exists
        When we load and examine it
        Then it contains at least 50 verified entries
        """
        # Arrange: Load ground truth
        import json
        from pathlib import Path

        gt_path = Path("tests/fixtures/classification_ground_truth.json")

        # RED STATE: File does not exist
        assert gt_path.exists(), "Ground truth file not found"

        with open(gt_path) as f:
            ground_truth = json.load(f)

        # Assert: At least 50 entries
        assert len(ground_truth.get("entries", [])) >= 50, (
            f"Expected 50+ entries, found {len(ground_truth.get('entries', []))}"
        )

    def test_ac_4_1_3_ground_truth_has_required_fields(self) -> None:
        """TEST-AC-9.7.4.3 [P0]: Ground truth entries have required fields.

        Given the ground truth file exists
        When we examine entry structure
        Then each entry has document, table_index, row_index, expected classifications
        """
        # Arrange: Load ground truth
        import json
        from pathlib import Path

        gt_path = Path("tests/fixtures/classification_ground_truth.json")

        # RED STATE: File does not exist
        assert gt_path.exists(), "Ground truth file not found"

        with open(gt_path) as f:
            ground_truth = json.load(f)

        # Assert: Required fields are present
        required_fields = [
            "document",
            "table_index",
            "row_index",
            "expected_period_type",
            "expected_value_type",
            "expected_entity_level",
        ]

        for entry in ground_truth.get("entries", [])[:5]:  # Check first 5 entries
            for field in required_fields:
                assert field in entry, f"Entry missing required field: {field}"

    def test_ac_4_1_4_accuracy_validation_script_exists(self) -> None:
        """TEST-AC-9.7.4.4 [P0]: Accuracy validation script exists.

        Given the scripts directory exists
        When we check for validate-classification-accuracy.py
        Then the script exists
        """
        # Arrange: Expected script path
        from pathlib import Path

        script_path = Path("scripts/validate-classification-accuracy.py")

        # Assert: Script exists
        # RED STATE: Script does not exist yet
        assert script_path.exists(), f"Script not found at {script_path}"

    def test_ac_4_1_5_accuracy_script_loads_ground_truth(self) -> None:
        """TEST-AC-9.7.4.5 [P0]: Script loads ground truth file.

        Given the accuracy validation script exists
        When we examine its logic
        Then it loads tests/fixtures/classification_ground_truth.json
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-accuracy.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Ground truth loading is present
        assert "classification_ground_truth" in source_code, (
            "Script should load classification_ground_truth.json"
        )

    def test_ac_4_1_6_accuracy_script_queries_database(self) -> None:
        """TEST-AC-9.7.4.6 [P0]: Script queries database for comparison.

        Given the accuracy validation script exists
        When we examine its logic
        Then it queries PostgreSQL to get actual classifications
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-accuracy.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Database query is present
        assert "SELECT" in source_code.upper() or "query" in source_code.lower(), (
            "Script should query database for actual classifications"
        )
        assert "financial_tables" in source_code, "Script should query financial_tables table"

    def test_ac_4_1_7_accuracy_script_calculates_period_type_accuracy(self) -> None:
        """TEST-AC-9.7.4.7 [P0]: Script calculates period_type accuracy.

        Given the accuracy validation script exists
        When we examine its logic
        Then it calculates period_type accuracy percentage
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-accuracy.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: period_type accuracy calculation is present
        assert "period_type" in source_code, "Script should calculate period_type accuracy"
        assert "accuracy" in source_code.lower() or "%" in source_code, (
            "Script should calculate accuracy percentage"
        )

    def test_ac_4_1_8_accuracy_script_validates_95_percent_target(self) -> None:
        """TEST-AC-9.7.4.8 [P0]: Script validates 95% period_type target.

        Given the accuracy validation script exists
        When we examine its logic
        Then it validates period_type accuracy >= 95%
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-accuracy.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: 95% threshold is present
        assert "95" in source_code, "Script should validate against 95% period_type target"

    def test_ac_4_1_9_accuracy_script_validates_90_percent_value_type(self) -> None:
        """TEST-AC-9.7.4.9 [P0]: Script validates 90% value_type target.

        Given the accuracy validation script exists
        When we examine its logic
        Then it validates value_type accuracy >= 90%
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-accuracy.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: 90% threshold is present for value_type
        assert "value_type" in source_code, "Script should validate value_type accuracy"
        assert "90" in source_code, "Script should validate against 90% value_type target"

    def test_ac_4_1_10_accuracy_script_logs_misclassifications(self) -> None:
        """TEST-AC-9.7.4.10 [P0]: Script logs misclassifications.

        Given the accuracy validation script exists
        When misclassifications are found
        Then they are logged for review
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-accuracy.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Misclassification logging is present
        assert "misclass" in source_code.lower() or "mismatch" in source_code.lower(), (
            "Script should log misclassifications"
        )

    def test_ac_4_1_11_accuracy_script_generates_report(self) -> None:
        """TEST-AC-9.7.4.11 [P0]: Script generates accuracy report.

        Given the accuracy validation script exists
        When validation completes
        Then report is saved to docs/sprint-artifacts/classification-accuracy-report.md
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-accuracy.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Report generation is present
        assert "accuracy-report" in source_code or "accuracy_report" in source_code, (
            "Script should generate accuracy report file"
        )

    def test_ac_4_1_12_accuracy_report_structure(self, sample_accuracy_report: dict) -> None:
        """TEST-AC-9.7.4.12 [P0]: Accuracy report has expected structure.

        Given a valid accuracy report
        When examining its structure
        Then it contains metrics for all three classification types with PASS/FAIL status
        """
        # Arrange: Use sample accuracy report fixture
        report = sample_accuracy_report

        # Assert: Report has expected structure
        assert "metrics" in report, "Report should have metrics section"
        assert "period_type" in report["metrics"], "Report should have period_type metric"
        assert "value_type" in report["metrics"], "Report should have value_type metric"
        assert "entity_level" in report["metrics"], "Report should have entity_level metric"

        # Check each metric has expected fields
        for metric_name in ["period_type", "value_type", "entity_level"]:
            metric = report["metrics"][metric_name]
            assert "expected" in metric, f"{metric_name} should have expected threshold"
            assert "actual" in metric, f"{metric_name} should have actual value"
            assert "status" in metric, f"{metric_name} should have PASS/FAIL status"
            assert metric["status"] in ["PASS", "FAIL"], (
                f"{metric_name} status should be PASS or FAIL"
            )
