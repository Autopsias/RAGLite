"""[P0] ATDD tests for AC-8.4b.3: Coverage Maintained at 80%+.

Given the current coverage baseline for integration tests
When the refactoring is complete
Then test coverage remains at or above 80%

These tests verify coverage is maintained after refactoring.
"""

import subprocess
from pathlib import Path

import pytest


class TestAC3CoverageMaintenance:
    """[P0] Tests for AC-8.4b.3 - Coverage maintenance."""

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4b_3_1_coverage_above_80_percent(
        self, tests_integration_path: Path, coverage_threshold: float
    ) -> None:
        """TEST-AC-8.4b.3.1: Integration test coverage >= 80%."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(tests_integration_path),
                "--cov=raglite",
                f"--cov-fail-under={int(coverage_threshold)}",
                "-q",
                "--no-header",
            ],
            capture_output=True,
            text=True,
            cwd=tests_integration_path.parent.parent,
            timeout=600,  # 10 minute timeout for coverage run
        )

        # Check for coverage failure
        output = result.stdout + result.stderr
        if "FAIL Required test coverage" in output:
            pytest.fail(
                f"Coverage below {coverage_threshold}% threshold. "
                "Run: pytest tests/integration/ --cov=raglite"
            )

        # Also check exit code (cov-fail-under returns non-zero on failure)
        assert result.returncode == 0 or "passed" in output.lower(), (
            f"Coverage check failed: {output}"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_3_2_no_coverage_regression_in_new_files(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.3.2: New split files have actual test coverage."""
        subdirs = ["forecasting", "ingestion", "model_selection"]
        uncovered_files = []

        for subdir in subdirs:
            subdir_path = tests_integration_path / subdir
            if subdir_path.exists():
                for test_file in subdir_path.glob("test_*.py"):
                    content = test_file.read_text()
                    # Check file has actual assertions (not just pass/skip)
                    has_assertions = (
                        "assert " in content
                        or "pytest.raises" in content
                        or "pytest.fail" in content
                    )
                    if not has_assertions:
                        uncovered_files.append(test_file.name)

        assert len(uncovered_files) == 0, f"Files without assertions: {uncovered_files}"

    @pytest.mark.atdd
    def test_ac_8_4b_3_3_test_coverage_includes_split_modules(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.3.3: Split modules are included in coverage."""
        subdirs = ["forecasting", "ingestion", "model_selection"]
        modules_with_tests = []

        for subdir in subdirs:
            subdir_path = tests_integration_path / subdir
            if subdir_path.exists():
                test_files = list(subdir_path.glob("test_*.py"))
                if test_files:
                    modules_with_tests.append(subdir)

        # After refactoring, all 3 subdirectories should have tests
        expected_modules = {"forecasting", "ingestion", "model_selection"}
        found_modules = set(modules_with_tests)

        missing = expected_modules - found_modules
        assert len(missing) == 0, f"Missing test coverage in modules: {missing}"

    @pytest.mark.atdd
    def test_ac_8_4b_3_4_no_duplicate_fixtures(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.3.4: No duplicate fixture definitions across conftest files."""
        conftest_files = list(tests_integration_path.rglob("conftest.py"))
        fixture_locations = {}
        duplicates = []

        for conftest in conftest_files:
            content = conftest.read_text()
            # Find fixture definitions
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "@pytest.fixture" in line or "@pytest.fixture(" in line:
                    # Get the function name from the next non-decorator line
                    for j in range(i + 1, min(i + 5, len(lines))):
                        next_line = lines[j].strip()
                        if next_line.startswith("def ") or next_line.startswith("async def "):
                            func_name = (
                                next_line.split("(")[0]
                                .replace("def ", "")
                                .replace("async ", "")
                                .strip()
                            )
                            if func_name in fixture_locations:
                                duplicates.append(
                                    f"{func_name}: {fixture_locations[func_name]} and {conftest}"
                                )
                            else:
                                fixture_locations[func_name] = str(conftest)
                            break

        # Some fixtures may legitimately be duplicated for isolation - filter common ones
        legitimate_duplicates = {"setup", "teardown", "session_scope"}
        real_duplicates = [
            d for d in duplicates if not any(ld in d for ld in legitimate_duplicates)
        ]

        assert len(real_duplicates) == 0, f"Duplicate fixtures found: {real_duplicates}"


class TestAC3SubdirectoryCoverage:
    """[P1] Tests for subdirectory-specific coverage validation."""

    @pytest.mark.atdd
    def test_ac_8_4b_3_5_forecasting_tests_have_assertions(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.3.5: Forecasting tests have proper assertions."""
        forecasting_path = tests_integration_path / "forecasting"
        if not forecasting_path.exists():
            pytest.fail("forecasting/ directory not created yet")

        for test_file in forecasting_path.glob("test_*.py"):
            content = test_file.read_text()
            assert_count = content.count("assert ")
            assert assert_count >= 3, f"{test_file.name} has only {assert_count} assertions"

    @pytest.mark.atdd
    def test_ac_8_4b_3_6_ingestion_tests_have_assertions(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.3.6: Ingestion tests have proper assertions."""
        ingestion_path = tests_integration_path / "ingestion"
        if not ingestion_path.exists():
            pytest.fail("ingestion/ directory not created yet")

        for test_file in ingestion_path.glob("test_*.py"):
            content = test_file.read_text()
            assert_count = content.count("assert ")
            assert assert_count >= 3, f"{test_file.name} has only {assert_count} assertions"

    @pytest.mark.atdd
    def test_ac_8_4b_3_7_model_selection_tests_have_assertions(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.3.7: Model selection tests have proper assertions."""
        model_selection_path = tests_integration_path / "model_selection"
        if not model_selection_path.exists():
            pytest.fail("model_selection/ directory not created yet")

        for test_file in model_selection_path.glob("test_*.py"):
            content = test_file.read_text()
            assert_count = content.count("assert ")
            assert assert_count >= 3, f"{test_file.name} has only {assert_count} assertions"
