"""AC-8.1.5: No Circular Dependencies.

ATDD tests for verifying no circular dependencies exist after refactoring.

Given: The split modules have interdependencies
When: The refactoring is complete
Then: There are NO circular dependencies between modules

IMPORTANT (Epic 8 Safety):
- These tests use SUBPROCESS for isolated import testing
- NEVER use del sys.modules[...] - it corrupts class identity (R-016 risk)
- See docs/test-design-epic-8.md for full explanation
"""

import subprocess
import sys

import pytest

# Group circular dependency tests that run subprocesses to run on same worker
pytestmark = pytest.mark.xdist_group(name="circular_deps")


class TestAC8_1_5_NoCircularDependencies:
    """AC-8.1.5: No circular dependencies between modules."""

    def test_ac_8_1_5_import_raglite_succeeds(self) -> None:
        """TEST-AC-8.1.5-A: Import raglite should succeed without circular import errors.

        Uses subprocess for true import isolation (no sys.modules manipulation).
        """
        result = subprocess.run(
            [sys.executable, "-c", "import raglite; print('OK')"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Import raglite failed: {result.stderr}"
        assert "circular" not in result.stderr.lower(), f"Circular import detected: {result.stderr}"

    def test_ac_8_1_5_import_forecasting_succeeds(self) -> None:
        """TEST-AC-8.1.5-B: Import raglite.forecasting should succeed without errors.

        Uses subprocess for true import isolation (no sys.modules manipulation).
        """
        result = subprocess.run(
            [sys.executable, "-c", "import raglite.forecasting; print('OK')"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Import raglite.forecasting failed: {result.stderr}"
        assert "circular" not in result.stderr.lower(), (
            f"Circular import detected in forecasting: {result.stderr}"
        )

    def test_ac_8_1_5_each_submodule_imports_independently(self) -> None:
        """TEST-AC-8.1.5-C: Each new submodule should import independently.

        Uses subprocess for true import isolation (no sys.modules manipulation).
        """
        submodules = [
            "raglite.forecasting.timeseries",
            "raglite.forecasting.timeseries.core",
            "raglite.forecasting.timeseries.parsing",
            "raglite.forecasting.timeseries.metadata",
            "raglite.forecasting.timeseries.external",
            "raglite.forecasting.timeseries.sql_extraction",
            "raglite.forecasting.hybrid",
            "raglite.forecasting.hybrid.ensemble",
            "raglite.forecasting.hybrid.ml_models",
            "raglite.forecasting.hybrid.preprocessing",
        ]

        import_failures = []
        for module_name in submodules:
            result = subprocess.run(
                [sys.executable, "-c", f"import {module_name}; print('OK')"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                import_failures.append(f"{module_name}: {result.stderr}")

        assert not import_failures, f"Submodules failed to import independently: {import_failures}"
