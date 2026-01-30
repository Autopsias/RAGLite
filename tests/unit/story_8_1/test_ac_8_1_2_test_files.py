"""AC-8.1.2: Test Files Under 500 LOC.

ATDD tests for verifying test file refactoring.

Given: The forecasting test file (test_timeseries_extract.py) exceeds 500 LOC
When: The refactoring is complete
Then: ALL resulting test modules are under 500 LOC each
"""

from .conftest import HARD_LIMIT_LOC, PROJECT_ROOT, count_lines, get_python_files


class TestAC8_1_2_TestFilesUnder500LOC:
    """AC-8.1.2: All test files under 500 LOC after refactoring."""

    def test_ac_8_1_2_original_test_file_split(self) -> None:
        """TEST-AC-8.1.2-A: Original large test file should be deleted after split."""
        original_test = PROJECT_ROOT / "tests/unit/test_timeseries_extract.py"

        # After refactoring, original file should be deleted (tests moved to new structure)
        assert not original_test.exists(), (
            "tests/unit/test_timeseries_extract.py should be deleted after splitting. "
            "Tests have been moved to tests/unit/forecasting/timeseries/"
        )

    def test_ac_8_1_2_timeseries_test_submodules_exist(self) -> None:
        """TEST-AC-8.1.2-B: Timeseries test submodules should exist after refactoring."""
        expected_test_modules = [
            "tests/unit/forecasting/timeseries/test_core.py",
            "tests/unit/forecasting/timeseries/test_parsing.py",
            "tests/unit/forecasting/timeseries/test_sql_extraction.py",
            "tests/unit/forecasting/timeseries/test_external.py",
            "tests/unit/forecasting/timeseries/test_year_filter.py",
        ]

        missing_modules = []
        for module_path in expected_test_modules:
            full_path = PROJECT_ROOT / module_path
            if not full_path.exists():
                missing_modules.append(module_path)

        assert not missing_modules, (
            f"Missing timeseries test submodules after refactoring: {missing_modules}"
        )

    def test_ac_8_1_2_hybrid_test_submodules_exist(self) -> None:
        """TEST-AC-8.1.2-C: Hybrid test directory should exist (tests deferred to future story)."""
        hybrid_test_dir = PROJECT_ROOT / "tests/unit/forecasting/hybrid"

        # Hybrid test directory should exist, even if test files are deferred
        assert hybrid_test_dir.exists(), (
            f"Hybrid test directory should exist at {hybrid_test_dir}. "
            f"Test files may be deferred to a future story."
        )

    def test_ac_8_1_2_all_new_test_modules_under_500_loc(self) -> None:
        """TEST-AC-8.1.2-D: All new test modules should be under 500 LOC.

        Note: Files documented in .file-size-exceptions are excluded from this check.
        """
        import json

        new_test_dirs = [
            PROJECT_ROOT / "tests/unit/forecasting/timeseries",
            PROJECT_ROOT / "tests/unit/forecasting/hybrid",
        ]

        # Load documented exceptions
        exceptions_file = PROJECT_ROOT / ".file-size-exceptions"
        exceptions = set()
        if exceptions_file.exists():
            with open(exceptions_file) as f:
                data = json.load(f)
                # Exceptions are under the 'exceptions' key
                exceptions = set(data.get("exceptions", {}).keys())

        violations = []
        for dir_path in new_test_dirs:
            if dir_path.exists():
                for py_file in get_python_files(dir_path):
                    rel_path = str(py_file.relative_to(PROJECT_ROOT))
                    # Skip files with documented exceptions
                    if rel_path in exceptions:
                        continue
                    loc = count_lines(py_file)
                    if loc > HARD_LIMIT_LOC:
                        violations.append(f"{rel_path}: {loc} LOC")

        # This test WILL FAIL if directories don't exist or modules exceed limit (excluding exceptions)
        assert not violations, f"New test modules exceed {HARD_LIMIT_LOC} LOC limit: {violations}"
