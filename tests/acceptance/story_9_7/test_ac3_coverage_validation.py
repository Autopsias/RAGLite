"""ATDD tests for Story 9.7 AC3 - Classification Coverage Validation.

TDD RED Phase: All tests MUST fail initially because the validate-classification-coverage.py
script does not exist yet.

Test IDs follow pattern: TEST-AC-9.7.3.{test}

BDD Acceptance Criteria:
Given re-ingestion is complete for all 33 documents
When validating classification coverage
Then 100% of rows have period_type populated (no NULLs)
And 100% of rows have value_type populated (no NULLs)
And 100% of rows have entity_level populated (no NULLs)
And validation query confirms: SELECT COUNT(*) FROM financial_tables WHERE period_type IS NULL = 0
And classification breakdown is generated:
  | Classification | Count | Percentage |
  |----------------|-------|------------|
  | monthly_actual | X     | Y%         |
  | ytd_actual     | X     | Y%         |
  | budget         | X     | Y%         |
  | unknown        | X     | Y%         |
And coverage report is saved to docs/sprint-artifacts/classification-coverage-report.md
"""

import pytest

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.story_9_7,
    pytest.mark.atdd,
]


class TestAC3ClassificationCoverageValidation:
    """AC3: Classification Coverage Validation.

    Given re-ingestion is complete
    When validating coverage
    Then 100% of rows have classification fields populated
    """

    def test_ac_3_1_1_coverage_validation_script_exists(self) -> None:
        """TEST-AC-9.7.3.1 [P0]: Coverage validation script exists.

        Given the scripts directory exists
        When we check for validate-classification-coverage.py
        Then the script exists
        """
        # Arrange: Expected script path
        from pathlib import Path

        script_path = Path("scripts/validate-classification-coverage.py")

        # Assert: Script exists
        # RED STATE: Script does not exist yet
        assert script_path.exists(), f"Script not found at {script_path}"

    def test_ac_3_1_2_coverage_script_checks_period_type_nulls(self) -> None:
        """TEST-AC-9.7.3.2 [P0]: Script checks period_type NULL count.

        Given the coverage validation script exists
        When we examine its logic
        Then it queries for period_type IS NULL rows
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-coverage.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: period_type NULL check is present
        assert "period_type" in source_code, "Script should check period_type column for NULLs"
        assert "NULL" in source_code.upper() or "null" in source_code, (
            "Script should query for NULL values"
        )

    def test_ac_3_1_3_coverage_script_checks_value_type_nulls(self) -> None:
        """TEST-AC-9.7.3.3 [P0]: Script checks value_type NULL count.

        Given the coverage validation script exists
        When we examine its logic
        Then it queries for value_type IS NULL rows
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-coverage.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: value_type NULL check is present
        assert "value_type" in source_code, "Script should check value_type column for NULLs"

    def test_ac_3_1_4_coverage_script_checks_entity_level_nulls(self) -> None:
        """TEST-AC-9.7.3.4 [P0]: Script checks entity_level NULL count.

        Given the coverage validation script exists
        When we examine its logic
        Then it queries for entity_level IS NULL rows
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-coverage.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: entity_level NULL check is present
        assert "entity_level" in source_code, "Script should check entity_level column for NULLs"

    def test_ac_3_1_5_coverage_script_generates_breakdown(self) -> None:
        """TEST-AC-9.7.3.5 [P0]: Script generates classification breakdown.

        Given the coverage validation script exists
        When we examine its output logic
        Then it generates count and percentage by classification type
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-coverage.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Breakdown logic is present
        assert "breakdown" in source_code.lower() or "GROUP BY" in source_code.upper(), (
            "Script should generate classification breakdown with GROUP BY"
        )
        assert "percentage" in source_code.lower() or "%" in source_code, (
            "Script should calculate percentages for breakdown"
        )

    def test_ac_3_1_6_coverage_script_saves_report(self) -> None:
        """TEST-AC-9.7.3.6 [P0]: Script saves coverage report to file.

        Given the coverage validation script exists
        When coverage validation completes
        Then report is saved to docs/sprint-artifacts/classification-coverage-report.md
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-coverage.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Report file output is present
        assert (
            "classification-coverage-report" in source_code or "coverage_report" in source_code
        ), "Script should save report to coverage report file"
        assert "docs/sprint-artifacts" in source_code or "write" in source_code.lower(), (
            "Script should write report to docs/sprint-artifacts/"
        )

    def test_ac_3_1_7_coverage_script_returns_exit_code(self) -> None:
        """TEST-AC-9.7.3.7 [P0]: Script returns appropriate exit code.

        Given the coverage validation script exists
        When coverage validation completes
        Then exit code 0 if 100% coverage, 1 otherwise
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/validate-classification-coverage.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Exit code logic is present
        assert "exit" in source_code.lower() or "sys.exit" in source_code, (
            "Script should return exit code based on coverage status"
        )

    def test_ac_3_1_8_coverage_100_percent_period_type(self, sample_coverage_report: dict) -> None:
        """TEST-AC-9.7.3.8 [P0]: Coverage report shows 100% period_type.

        Given a valid coverage report
        When examining period_type coverage
        Then NULL count is 0 (100% coverage)
        """
        # Arrange: Use sample coverage report fixture
        report = sample_coverage_report

        # Assert: period_type has no NULLs
        # RED STATE: This validates the expected report structure
        assert report["period_type_nulls"] == 0, (
            "period_type should have 0 NULL values (100% coverage)"
        )

    def test_ac_3_1_9_coverage_100_percent_value_type(self, sample_coverage_report: dict) -> None:
        """TEST-AC-9.7.3.9 [P0]: Coverage report shows 100% value_type.

        Given a valid coverage report
        When examining value_type coverage
        Then NULL count is 0 (100% coverage)
        """
        # Arrange: Use sample coverage report fixture
        report = sample_coverage_report

        # Assert: value_type has no NULLs
        assert report["value_type_nulls"] == 0, (
            "value_type should have 0 NULL values (100% coverage)"
        )

    def test_ac_3_1_10_coverage_100_percent_entity_level(
        self, sample_coverage_report: dict
    ) -> None:
        """TEST-AC-9.7.3.10 [P0]: Coverage report shows 100% entity_level.

        Given a valid coverage report
        When examining entity_level coverage
        Then NULL count is 0 (100% coverage)
        """
        # Arrange: Use sample coverage report fixture
        report = sample_coverage_report

        # Assert: entity_level has no NULLs
        assert report["entity_level_nulls"] == 0, (
            "entity_level should have 0 NULL values (100% coverage)"
        )
