"""AC-8.1.7: Test Structure Mirrors Production.

ATDD tests for verifying test file structure mirrors production module structure.

Given: The production module structure after refactoring
When: The test refactoring is complete
Then: Test file structure mirrors production module structure (1:1 mapping)
"""

import pytest

from .conftest import PROJECT_ROOT


class TestAC8_1_7_TestStructureMirrorsProduction:
    """AC-8.1.7: Test file structure mirrors production module structure."""

    def test_ac_8_1_7_timeseries_test_structure_matches_production(self) -> None:
        """TEST-AC-8.1.7-A: Timeseries test structure should match production structure.

        NOTE: Some tests are deferred to future stories (metadata, qdrant_* modules).
        This test verifies that existing test files match their production counterparts.
        """
        # Modules with tests in Story 8.1
        tested_modules = [
            "core.py",
            "external.py",
            "parsing.py",
            "sql_extraction.py",
        ]

        # Additional modules exist but tests deferred (metadata, qdrant_ebitda, etc.)
        # year_filter has tests but no production module (extracted from sql_extraction)

        prod_dir = PROJECT_ROOT / "raglite/forecasting/timeseries"
        test_dir = PROJECT_ROOT / "tests/unit/forecasting/timeseries"

        # Check if production dir exists first
        if not prod_dir.exists():
            pytest.fail(
                "Production timeseries directory does not exist. "
                "Refactoring must create raglite/forecasting/timeseries/"
            )

        # Verify tested modules have both production and test files
        missing_pairs = []
        for module_name in tested_modules:
            prod_path = prod_dir / module_name
            test_path = test_dir / f"test_{module_name}"

            if not prod_path.exists():
                missing_pairs.append(f"Production file missing: {module_name}")
            if not test_path.exists():
                missing_pairs.append(f"Test file missing: test_{module_name}")

        assert not missing_pairs, f"Test/production structure mismatch: {missing_pairs}"

    def test_ac_8_1_7_hybrid_test_structure_matches_production(self) -> None:
        """TEST-AC-8.1.7-B: Hybrid production and test directories exist.

        NOTE: Hybrid tests are deferred to a future story. This test only verifies
        that both directories exist to support future test development.
        """
        prod_dir = PROJECT_ROOT / "raglite/forecasting/hybrid"
        test_dir = PROJECT_ROOT / "tests/unit/forecasting/hybrid"

        # Check if production dir exists
        assert prod_dir.exists(), (
            "Production hybrid directory does not exist. "
            "Refactoring must create raglite/forecasting/hybrid/"
        )

        # Check if test dir exists
        assert test_dir.exists(), (
            "Test hybrid directory does not exist. "
            "Should be created even if test files are deferred."
        )

    def test_ac_8_1_7_conftest_files_exist(self) -> None:
        """TEST-AC-8.1.7-C: Shared fixture conftest.py files should exist.

        NOTE: Only timeseries conftest is required for Story 8.1.
        Hybrid and parent conftest files may be added in future stories.
        """
        required_conftest_files = [
            "tests/unit/forecasting/timeseries/conftest.py",
        ]

        missing_conftest = []
        for conftest_path in required_conftest_files:
            full_path = PROJECT_ROOT / conftest_path
            if not full_path.exists():
                missing_conftest.append(conftest_path)

        assert not missing_conftest, f"Missing required conftest.py files: {missing_conftest}"
