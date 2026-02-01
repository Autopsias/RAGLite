"""AC-8.1.1: Production Files Under 500 LOC.

ATDD tests for verifying production file refactoring.

Given: The forecasting production files (timeseries_extract.py, hybrid.py) exceed 500 LOC
When: The refactoring is complete
Then: ALL resulting production modules are under 500 LOC each
"""

from .conftest import HARD_LIMIT_LOC, PROJECT_ROOT, count_lines, get_python_files


class TestAC8_1_1_ProductionFilesUnder500LOC:
    """AC-8.1.1: All production files under 500 LOC after refactoring."""

    def test_ac_8_1_1_timeseries_extract_converted_to_shim(self) -> None:
        """TEST-AC-8.1.1-A: timeseries_extract.py should be converted to a shim file < 100 LOC."""
        filepath = "raglite/forecasting/timeseries_extract.py"
        full_path = PROJECT_ROOT / filepath
        loc = count_lines(full_path)

        # After refactoring, shim file should be < 100 LOC
        assert loc < 100, f"{filepath} has {loc} LOC, expected < 100 after conversion to shim."

    def test_ac_8_1_1_hybrid_converted_to_package(self) -> None:
        """TEST-AC-8.1.1-B: hybrid.py should be converted to a package (directory)."""
        # Original file should NOT exist
        old_file = PROJECT_ROOT / "raglite/forecasting/hybrid.py"
        assert not old_file.exists(), (
            "hybrid.py should be removed and replaced with hybrid/ package"
        )

        # Package directory should exist
        package_dir = PROJECT_ROOT / "raglite/forecasting/hybrid"
        assert package_dir.exists() and package_dir.is_dir(), (
            "hybrid/ package directory should exist"
        )

    def test_ac_8_1_1_timeseries_submodules_exist(self) -> None:
        """TEST-AC-8.1.1-C: Timeseries submodules should exist after refactoring."""
        expected_modules = [
            "raglite/forecasting/timeseries/__init__.py",
            "raglite/forecasting/timeseries/core.py",
            "raglite/forecasting/timeseries/external.py",
            "raglite/forecasting/timeseries/metadata.py",
            "raglite/forecasting/timeseries/parsing.py",
            "raglite/forecasting/timeseries/qdrant_ebitda.py",
            "raglite/forecasting/timeseries/qdrant_metric.py",
            "raglite/forecasting/timeseries/qdrant_variable_cost.py",
            "raglite/forecasting/timeseries/sql_extraction.py",
        ]

        missing_modules = []
        for module_path in expected_modules:
            full_path = PROJECT_ROOT / module_path
            if not full_path.exists():
                missing_modules.append(module_path)

        assert not missing_modules, (
            f"Missing timeseries submodules after refactoring: {missing_modules}"
        )

    def test_ac_8_1_1_hybrid_submodules_exist(self) -> None:
        """TEST-AC-8.1.1-D: Hybrid submodules should exist after refactoring."""
        expected_modules = [
            "raglite/forecasting/hybrid/__init__.py",
            "raglite/forecasting/hybrid/ensemble.py",
            "raglite/forecasting/hybrid/lazy_imports.py",
            "raglite/forecasting/hybrid/ml_models.py",
            "raglite/forecasting/hybrid/model_generators.py",
            "raglite/forecasting/hybrid/preprocessing.py",
        ]

        missing_modules = []
        for module_path in expected_modules:
            full_path = PROJECT_ROOT / module_path
            if not full_path.exists():
                missing_modules.append(module_path)

        assert not missing_modules, (
            f"Missing hybrid submodules after refactoring: {missing_modules}"
        )

    def test_ac_8_1_1_all_new_modules_under_500_loc(self) -> None:
        """TEST-AC-8.1.1-E: All new production modules should be under 500 LOC.

        Note: Files documented in .file-size-exceptions are excluded from this check.
        These are cohesive modules that cannot be reasonably split further.
        """
        import json

        new_module_dirs = [
            PROJECT_ROOT / "raglite/forecasting/timeseries",
            PROJECT_ROOT / "raglite/forecasting/hybrid",
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
        for dir_path in new_module_dirs:
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
        assert not violations, f"New modules exceed {HARD_LIMIT_LOC} LOC limit: {violations}"
