"""Baseline tests to document current state before refactoring.

These tests verify the current (pre-refactoring) state and will PASS.
They serve as documentation of what needs to be changed.
After refactoring, these baseline tests will FAIL (expected behavior).
"""

import pytest

from .conftest import HARD_LIMIT_LOC, PROJECT_ROOT, count_lines


class TestStory8_1_PreRefactoringBaseline:
    """Baseline tests to document current state before refactoring.

    NOTE: After refactoring is complete, these tests are expected to fail.
    They are marked as xfail since they verify the pre-refactoring state.
    """

    @pytest.mark.xfail(reason="Refactoring complete - file split into modules", strict=True)
    def test_baseline_timeseries_extract_exceeds_limit(self) -> None:
        """Baseline: Verify timeseries_extract.py currently exceeds 500 LOC."""
        filepath = PROJECT_ROOT / "raglite/forecasting/timeseries_extract.py"
        loc = count_lines(filepath)

        # This should PASS - documenting that the file currently exceeds limit
        assert loc > HARD_LIMIT_LOC, (
            f"timeseries_extract.py has {loc} LOC, expected > {HARD_LIMIT_LOC}. "
            "If this fails, refactoring may have started."
        )

    @pytest.mark.xfail(reason="Refactoring complete - file split into modules", strict=True)
    def test_baseline_hybrid_exceeds_limit(self) -> None:
        """Baseline: Verify hybrid.py currently exceeds 500 LOC."""
        filepath = PROJECT_ROOT / "raglite/forecasting/hybrid.py"
        loc = count_lines(filepath)

        # This should PASS - documenting that the file currently exceeds limit
        assert loc > HARD_LIMIT_LOC, (
            f"hybrid.py has {loc} LOC, expected > {HARD_LIMIT_LOC}. "
            "If this fails, refactoring may have started."
        )

    @pytest.mark.xfail(reason="Refactoring complete - test file deleted", strict=True)
    def test_baseline_test_timeseries_extract_exceeds_limit(self) -> None:
        """Baseline: Verify test_timeseries_extract.py currently exceeds 500 LOC."""
        filepath = PROJECT_ROOT / "tests/unit/test_timeseries_extract.py"
        loc = count_lines(filepath)

        # This should PASS - documenting that the file currently exceeds limit
        assert loc > HARD_LIMIT_LOC, (
            f"test_timeseries_extract.py has {loc} LOC, expected > {HARD_LIMIT_LOC}. "
            "If this fails, refactoring may have started."
        )

    @pytest.mark.xfail(reason="Refactoring complete - package created", strict=True)
    def test_baseline_timeseries_package_does_not_exist(self) -> None:
        """Baseline: Verify timeseries package does not exist yet."""
        package_path = PROJECT_ROOT / "raglite/forecasting/timeseries"

        # This should PASS - the package should NOT exist before refactoring
        assert not package_path.exists(), (
            f"timeseries package already exists at {package_path}. Refactoring may have started."
        )

    @pytest.mark.xfail(reason="Refactoring complete - package created", strict=True)
    def test_baseline_hybrid_package_does_not_exist(self) -> None:
        """Baseline: Verify hybrid package (directory) does not exist yet."""
        package_path = PROJECT_ROOT / "raglite/forecasting/hybrid"

        # Check if it's a directory (package), not just the existing hybrid.py file
        hybrid_py = PROJECT_ROOT / "raglite/forecasting/hybrid.py"

        # This should PASS - the package directory should NOT exist before refactoring
        # (hybrid.py file exists, but hybrid/ directory should not)
        assert not package_path.is_dir(), (
            f"hybrid package directory already exists at {package_path}. "
            "Refactoring may have started."
        )
        # Verify the current hybrid.py file exists
        assert hybrid_py.exists(), "hybrid.py file should exist before refactoring"
