"""[P0] ATDD tests for AC-8.4b.2: Test Count Unchanged or Increased.

Given the current test count baseline from pytest tests/integration/ --collect-only
When the refactoring is complete
Then the total test count is unchanged or increased (no tests lost)

These tests verify that all integration tests are preserved after refactoring.
"""

import subprocess
from pathlib import Path

import pytest

from .conftest import (
    EXPECTED_FORECASTING_FILES,
    EXPECTED_INGESTION_FILES,
    EXPECTED_MODEL_SELECTION_FILES,
    directory_exists,
    get_all_integration_test_files,
)


class TestAC2TestCountPreservation:
    """[P0] Tests for AC-8.4b.2 - Test count preservation."""

    @pytest.mark.atdd
    @pytest.mark.slow
    @pytest.mark.timeout(0)  # Disable timeout - subprocess has own timeout
    def test_ac_8_4b_2_1_test_count_meets_baseline(
        self, tests_integration_path: Path, test_count_baseline: int
    ) -> None:
        """TEST-AC-8.4b.2.1: Integration test count >= 282 baseline."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(tests_integration_path),
                "--collect-only",
                "-q",
                "-m",
                "",  # Include all markers (slow tests excluded by default)
            ],
            capture_output=True,
            text=True,
            cwd=tests_integration_path.parent.parent,
            timeout=180,  # 3 min subprocess timeout
        )

        # Parse test count from output
        output = result.stdout + result.stderr
        lines = output.strip().split("\n")
        test_count = 0

        for line in lines:
            if "test" in line.lower() and "collected" in line.lower():
                # Parse "N tests collected" or "N/M tests collected"
                parts = line.split()
                for _i, part in enumerate(parts):
                    if part.isdigit():
                        test_count = int(part)
                        break
                    elif "/" in part:
                        test_count = int(part.split("/")[0])
                        break

        assert test_count >= test_count_baseline, (
            f"Test count {test_count} < baseline {test_count_baseline} - tests lost during refactoring"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_2_2_no_empty_test_files(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.2.2: No test files are empty (all have tests)."""
        test_files = get_all_integration_test_files(tests_integration_path)
        empty_files = []

        for test_file in test_files:
            content = test_file.read_text()
            # Check for at least one test function or class
            has_tests = (
                "def test_" in content or "async def test_" in content or "class Test" in content
            )
            if not has_tests:
                empty_files.append(test_file.name)

        assert len(empty_files) == 0, f"Empty test files found: {empty_files}"

    @pytest.mark.atdd
    @pytest.mark.slow
    @pytest.mark.timeout(0)  # Disable timeout - subprocess has own timeout
    def test_ac_8_4b_2_3_all_test_modules_importable(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.2.3: All test modules are importable without errors."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(tests_integration_path),
                "--collect-only",
                "-q",
                "--ignore-glob=**/conftest.py",
            ],
            capture_output=True,
            text=True,
            cwd=tests_integration_path.parent.parent,
            timeout=180,  # 3 min subprocess timeout
        )

        # Check for import errors
        output = result.stdout + result.stderr
        assert "ImportError" not in output, f"Import errors found: {output}"
        assert "ModuleNotFoundError" not in output, f"Module errors found: {output}"

    @pytest.mark.atdd
    def test_ac_8_4b_2_4_subdirectory_conftest_valid_syntax(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.2.4: All subdirectory conftest.py files have valid syntax."""
        subdirs = ["forecasting", "ingestion", "model_selection"]
        invalid_conftest = []

        for subdir in subdirs:
            conftest_path = tests_integration_path / subdir / "conftest.py"
            if conftest_path.exists():
                try:
                    compile(conftest_path.read_text(), str(conftest_path), "exec")
                except SyntaxError as e:
                    invalid_conftest.append(f"{subdir}/conftest.py: {e}")

        assert len(invalid_conftest) == 0, f"Invalid conftest files: {invalid_conftest}"

    @pytest.mark.atdd
    def test_ac_8_4b_2_5_forecasting_tests_exist(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.2.5: Forecasting subdirectory contains expected test files."""
        if not directory_exists(tests_integration_path, "forecasting"):
            pytest.fail("forecasting/ subdirectory not yet created")

        forecasting_path = tests_integration_path / "forecasting"
        missing_files = []

        for expected in EXPECTED_FORECASTING_FILES:
            if not (forecasting_path / expected).exists():
                missing_files.append(expected)

        assert len(missing_files) == 0, f"Missing forecasting test files: {missing_files}"

    @pytest.mark.atdd
    def test_ac_8_4b_2_6_ingestion_tests_exist(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.2.6: Ingestion subdirectory contains expected test files."""
        if not directory_exists(tests_integration_path, "ingestion"):
            pytest.fail("ingestion/ subdirectory not yet created")

        ingestion_path = tests_integration_path / "ingestion"
        missing_files = []

        for expected in EXPECTED_INGESTION_FILES:
            if not (ingestion_path / expected).exists():
                missing_files.append(expected)

        assert len(missing_files) == 0, f"Missing ingestion test files: {missing_files}"

    @pytest.mark.atdd
    def test_ac_8_4b_2_7_model_selection_tests_exist(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.2.7: Model selection subdirectory contains expected test files."""
        if not directory_exists(tests_integration_path, "model_selection"):
            pytest.fail("model_selection/ subdirectory not yet created")

        model_selection_path = tests_integration_path / "model_selection"
        missing_files = []

        for expected in EXPECTED_MODEL_SELECTION_FILES:
            if not (model_selection_path / expected).exists():
                missing_files.append(expected)

        assert len(missing_files) == 0, f"Missing model_selection test files: {missing_files}"


class TestAC2TestFunctionPreservation:
    """[P1] Tests for preservation of specific test functions."""

    @pytest.mark.atdd
    def test_ac_8_4b_2_8_forecast_query_tests_preserved(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.2.8: Original forecast query tests are preserved in split files."""
        forecasting_path = tests_integration_path / "forecasting"
        if not forecasting_path.exists():
            pytest.fail("forecasting/ directory not created yet")

        # Check that split files contain test functions
        test_functions_found = 0
        for test_file in forecasting_path.glob("test_*.py"):
            content = test_file.read_text()
            test_functions_found += content.count("def test_")
            test_functions_found += content.count("async def test_")

        # Original file has ~20+ tests, expect similar count across split files
        assert test_functions_found >= 15, (
            f"Expected at least 15 test functions in forecasting/, found {test_functions_found}"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_2_9_ingestion_tests_preserved(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.2.9: Original ingestion tests are preserved in split files."""
        ingestion_path = tests_integration_path / "ingestion"
        if not ingestion_path.exists():
            pytest.fail("ingestion/ directory not created yet")

        # Check that split files contain test functions
        test_functions_found = 0
        for test_file in ingestion_path.glob("test_*.py"):
            content = test_file.read_text()
            test_functions_found += content.count("def test_")
            test_functions_found += content.count("async def test_")

        assert test_functions_found >= 15, (
            f"Expected at least 15 test functions in ingestion/, found {test_functions_found}"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_2_10_model_selection_tests_preserved(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.2.10: Original model selection tests are preserved in split files."""
        model_selection_path = tests_integration_path / "model_selection"
        if not model_selection_path.exists():
            pytest.fail("model_selection/ directory not created yet")

        # Check that split files contain test functions
        test_functions_found = 0
        for test_file in model_selection_path.glob("test_*.py"):
            content = test_file.read_text()
            test_functions_found += content.count("def test_")
            test_functions_found += content.count("async def test_")

        assert test_functions_found >= 15, (
            f"Expected at least 15 test functions in model_selection/, found {test_functions_found}"
        )
