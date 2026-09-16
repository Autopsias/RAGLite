"""ATDD Acceptance Tests - AC1: File Size Reduction.

Story: 7-1-split-test-external-data-clients
Epic: 7 - Technical Debt & Code Quality

Verifies:
- Original test_external_data_clients.py is removed
- All new modules are under 500 LOC
- Ideal target of 250-400 LOC per module
"""

from pathlib import Path

import pytest

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TESTS_ROOT = PROJECT_ROOT / "tests"
EXTERNAL_DATA_TESTS_DIR = TESTS_ROOT / "unit" / "external_data"
ORIGINAL_TEST_FILE = TESTS_ROOT / "unit" / "test_external_data_clients.py"

# Expected modules after refactoring
EXPECTED_MODULES = [
    "test_ine_client.py",
    "test_basegov_client.py",
    "test_basegov_story695.py",
    "test_bpstat_client.py",
    "test_omie_client.py",
    "test_oil_bulletin_client.py",
    "test_commodities_client.py",
    "test_atic_client.py",
    "test_ipma_client.py",
    "test_exceptions.py",
]

# File size limits
HARD_LIMIT_LOC = 500
IDEAL_MAX_LOC = 400


class TestAC1FileSizeReduction:
    """TEST-AC-1: File Size Reduction acceptance criteria tests."""

    @pytest.mark.acceptance
    def test_ac1_1_original_file_removed(self) -> None:
        """TEST-AC-1.1: Original test_external_data_clients.py should not exist."""
        assert not ORIGINAL_TEST_FILE.exists(), (
            f"Original file {ORIGINAL_TEST_FILE} should be removed after refactoring. "
            "The file still exists with 3,025 LOC."
        )

    @pytest.mark.acceptance
    @pytest.mark.parametrize("module_name", EXPECTED_MODULES)
    def test_ac1_2_module_under_hard_limit(self, module_name: str) -> None:
        """TEST-AC-1.2: Each new module must be under 500 LOC hard limit."""
        module_path = EXTERNAL_DATA_TESTS_DIR / module_name

        assert module_path.exists(), (
            f"Expected module {module_name} does not exist at {module_path}. "
            "Module needs to be created during refactoring."
        )

        line_count = len(module_path.read_text().splitlines())
        assert line_count <= HARD_LIMIT_LOC, (
            f"Module {module_name} has {line_count} LOC, exceeds hard limit of {HARD_LIMIT_LOC}. "
            "Consider splitting further."
        )

    @pytest.mark.acceptance
    @pytest.mark.parametrize("module_name", EXPECTED_MODULES)
    def test_ac1_3_module_under_ideal_limit(self, module_name: str) -> None:
        """TEST-AC-1.3: Each new module should ideally be under 400 LOC."""
        module_path = EXTERNAL_DATA_TESTS_DIR / module_name

        if not module_path.exists():
            pytest.skip(f"Module {module_name} does not exist yet (RED phase)")

        line_count = len(module_path.read_text().splitlines())
        # This is a soft limit - warn but don't fail
        if line_count > IDEAL_MAX_LOC:
            pytest.xfail(
                f"Module {module_name} has {line_count} LOC, "
                f"above ideal limit of {IDEAL_MAX_LOC}. "
                "Consider splitting if feasible."
            )
