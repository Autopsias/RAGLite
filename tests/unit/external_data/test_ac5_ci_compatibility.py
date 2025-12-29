"""ATDD Acceptance Tests - AC5: CI Compatibility.

Story: 7-1-split-test-external-data-clients
Epic: 7 - Technical Debt & Code Quality

Verifies:
- All tests discoverable by pytest
- No changes to test markers
- Proper module structure for test discovery
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TESTS_ROOT = PROJECT_ROOT / "tests"
EXTERNAL_DATA_TESTS_DIR = TESTS_ROOT / "unit" / "external_data"
ORIGINAL_TEST_FILE = TESTS_ROOT / "unit" / "test_external_data_clients.py"

# Expected modules
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


class TestAC5CICompatibility:
    """TEST-AC-5: CI Compatibility acceptance criteria tests."""

    @pytest.mark.acceptance
    def test_ac5_1_tests_discoverable(self) -> None:
        """TEST-AC-5.1: All tests must be discoverable by pytest."""
        # If original file still exists, skip (RED phase before refactoring)
        if ORIGINAL_TEST_FILE.exists():
            pytest.skip(
                "Original file still exists - cannot verify test discovery. "
                "This test will pass after refactoring is complete."
            )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(EXTERNAL_DATA_TESTS_DIR),
                "--collect-only",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode == 0, (
            f"pytest --collect-only failed. Tests may not be discoverable.\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.acceptance
    @pytest.mark.parametrize("module_name", EXPECTED_MODULES)
    def test_ac5_2_module_has_asyncio_markers(self, module_name: str) -> None:
        """TEST-AC-5.2: Modules must preserve @pytest.mark.asyncio markers."""
        module_path = EXTERNAL_DATA_TESTS_DIR / module_name

        if not module_path.exists():
            pytest.skip(f"Module {module_name} does not exist yet (RED phase)")

        content = module_path.read_text()

        # Check for async tests - they need asyncio marker
        if "async def test_" in content:
            assert "@pytest.mark.asyncio" in content or "pytestmark" in content, (
                f"Module {module_name} has async tests but missing @pytest.mark.asyncio markers. "
                "Ensure all async tests are properly marked."
            )

    @pytest.mark.acceptance
    def test_ac5_3_no_duplicate_test_names(self) -> None:
        """TEST-AC-5.3: No duplicate test function names across modules.

        Note: Within the same module, test classes can have same-named methods.
        This test checks for duplicates across DIFFERENT modules only.
        """
        # If original file still exists, skip (RED phase before refactoring)
        if ORIGINAL_TEST_FILE.exists():
            pytest.skip(
                "Original file still exists - cannot verify duplicates. "
                "This test will pass after refactoring is complete."
            )

        # Track test names with module path as key
        test_names_by_module: dict[str, set[str]] = {}
        duplicates: list[str] = []

        for module_path in EXTERNAL_DATA_TESTS_DIR.glob("test_*.py"):
            if module_path.name.startswith("test_ac"):
                continue  # Skip acceptance test files

            content = module_path.read_text()
            module_test_names = set()

            for line in content.splitlines():
                if "def test_" in line or "async def test_" in line:
                    # Extract function name
                    name = line.split("def ")[1].split("(")[0].strip()
                    module_test_names.add(name)

            test_names_by_module[module_path.name] = module_test_names

        # Check for duplicates across different modules
        checked_pairs = set()
        for module1, tests1 in test_names_by_module.items():
            for module2, tests2 in test_names_by_module.items():
                if module1 >= module2:  # Skip self-comparison and duplicate pairs
                    continue

                pair_key = tuple(sorted([module1, module2]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                # Find intersection (tests in both modules)
                common_tests = tests1 & tests2
                if common_tests:
                    for test_name in common_tests:
                        duplicates.append(f"{test_name} in {module1} and {module2}")

        assert not duplicates, (
            f"Found duplicate test function names across modules: {duplicates}. "
            "Each test function name should be unique across different modules."
        )
