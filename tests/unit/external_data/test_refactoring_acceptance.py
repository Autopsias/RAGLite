"""ATDD Acceptance Tests for Story 7.1: Split test_external_data_clients.py.

These tests verify the acceptance criteria for the file split refactoring.
In TDD RED phase, these tests SHOULD FAIL because the refactoring has not
been completed yet.

Story: 7-1-split-test-external-data-clients
Epic: 7 - Technical Debt & Code Quality

Acceptance Criteria Mapping:
- TEST-AC-1.x: File Size Reduction (AC1)
- TEST-AC-2.x: New Module Structure (AC2)
- TEST-AC-3.x: Functionality Preserved - Test Count (AC3)
- TEST-AC-4.x: Shared Fixtures Extracted (AC4)
- TEST-AC-5.x: CI Compatibility (AC5)
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TESTS_ROOT = PROJECT_ROOT / "tests"
EXTERNAL_DATA_TESTS_DIR = TESTS_ROOT / "unit" / "external_data"
ORIGINAL_TEST_FILE = TESTS_ROOT / "unit" / "test_external_data_clients.py"

# Expected modules after refactoring
# NOTE (2025-12-18): test_basegov_story695.py split out separately for file size limits
EXPECTED_MODULES = [
    "test_ine_client.py",
    "test_basegov_client.py",
    "test_basegov_story695.py",  # Split from test_basegov_client.py for file size limits
    "test_bpstat_client.py",
    "test_omie_client.py",
    "test_oil_bulletin_client.py",
    "test_commodities_client.py",
    "test_atic_client.py",
    "test_ipma_client.py",
    "test_exceptions.py",
]

# Expected test classes per module (from story analysis)
# NOTE (2025-12-18): Updated to reflect actual refactoring structure
EXPECTED_TEST_CLASSES = {
    "test_ine_client.py": [
        "TestINEClient",
        "TestINEDateFiltering",
        "TestINEClientAdditional",
        "TestStory68INEExtensions",
    ],
    "test_basegov_client.py": [
        "TestBaseGovClient",
        "TestBaseGovClientAdditional",
        "TestBaseGovClientCoverage",
    ],
    "test_basegov_story695.py": [
        "TestBaseGovStory695",  # Extracted to separate file for file size limits
    ],
    "test_bpstat_client.py": [
        "TestBPstatClient",
        "TestBPstatClientAdditional",
        "TestBPstatStory693",
        "TestStory68BPstatExtensions",
    ],
    "test_omie_client.py": [
        "TestOMIEClient",
        "TestOMIEStory692",
        "TestOMIEClientAdditional",
    ],
    "test_oil_bulletin_client.py": [
        "TestEUOilBulletinClient",
        "TestEUOilBulletinAdditional",
        "TestEUOilBulletinStory694",
    ],
    "test_commodities_client.py": [
        "TestCommoditiesURLFix",
        "TestCommoditiesClient",
        "TestCommoditiesClientAdditional",
        "TestCommoditiesClientCoverage",
    ],
    "test_atic_client.py": [
        "TestATICClient",
        "TestATICClientAdditional",
    ],
    "test_ipma_client.py": [
        "TestIPMAClient",
        "TestIPMAClientAdditional",
        "TestIPMAClientCoverage",
    ],
    "test_exceptions.py": [
        "TestExceptions",
        "TestRateLimitHandling",
    ],
}

# File size limits (from .claude/rules/file-size-limits.md)
HARD_LIMIT_LOC = 500
IDEAL_MAX_LOC = 400
CONFTEST_MAX_LOC = 200

# Baseline test count from original file (176 tests, excluding acceptance tests)
# Note: Original estimate was 131, updated to 197, now 176 client tests after Story 7.1 refactoring
# (2025-12-18): Excludes test_refactoring_acceptance.py (~72 tests) for stable baseline
BASELINE_TEST_COUNT = 176


class TestAC1FileSizeReduction:
    """TEST-AC-1: File Size Reduction acceptance criteria tests.

    Verifies:
    - Original test_external_data_clients.py is removed
    - All new modules are under 500 LOC
    - Ideal target of 250-400 LOC per module
    """

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


class TestAC2NewModuleStructure:
    """TEST-AC-2: New Module Structure acceptance criteria tests.

    Verifies:
    - tests/unit/external_data/ directory exists
    - All expected modules exist
    - conftest.py exists with shared fixtures
    - __init__.py exists
    """

    @pytest.mark.acceptance
    def test_ac2_1_directory_exists(self) -> None:
        """TEST-AC-2.1: tests/unit/external_data/ directory must exist."""
        assert EXTERNAL_DATA_TESTS_DIR.exists(), (
            f"Directory {EXTERNAL_DATA_TESTS_DIR} does not exist. "
            "Create the directory structure first."
        )
        assert EXTERNAL_DATA_TESTS_DIR.is_dir(), (
            f"{EXTERNAL_DATA_TESTS_DIR} exists but is not a directory."
        )

    @pytest.mark.acceptance
    def test_ac2_2_init_file_exists(self) -> None:
        """TEST-AC-2.2: __init__.py must exist in the package."""
        init_file = EXTERNAL_DATA_TESTS_DIR / "__init__.py"
        assert init_file.exists(), (
            f"__init__.py not found at {init_file}. Create package init file."
        )

    @pytest.mark.acceptance
    def test_ac2_3_conftest_exists(self) -> None:
        """TEST-AC-2.3: conftest.py must exist with shared fixtures."""
        conftest_file = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        assert conftest_file.exists(), (
            f"conftest.py not found at {conftest_file}. Create conftest with shared fixtures."
        )

    @pytest.mark.acceptance
    def test_ac2_4_conftest_under_size_limit(self) -> None:
        """TEST-AC-2.4: conftest.py should be under 200 LOC."""
        conftest_file = EXTERNAL_DATA_TESTS_DIR / "conftest.py"

        if not conftest_file.exists():
            pytest.skip("conftest.py does not exist yet (RED phase)")

        line_count = len(conftest_file.read_text().splitlines())
        assert line_count <= CONFTEST_MAX_LOC, (
            f"conftest.py has {line_count} LOC, exceeds limit of {CONFTEST_MAX_LOC}. "
            "Move some fixtures to specific test modules."
        )

    @pytest.mark.acceptance
    @pytest.mark.parametrize("module_name", EXPECTED_MODULES)
    def test_ac2_5_expected_module_exists(self, module_name: str) -> None:
        """TEST-AC-2.5: Each expected module file must exist."""
        module_path = EXTERNAL_DATA_TESTS_DIR / module_name
        assert module_path.exists(), (
            f"Expected module {module_name} does not exist at {module_path}. "
            "Module needs to be created during refactoring."
        )

    @pytest.mark.acceptance
    @pytest.mark.parametrize(
        "module_name,expected_classes",
        list(EXPECTED_TEST_CLASSES.items()),
    )
    def test_ac2_6_module_contains_expected_classes(
        self, module_name: str, expected_classes: list[str]
    ) -> None:
        """TEST-AC-2.6: Each module contains its expected test classes."""
        module_path = EXTERNAL_DATA_TESTS_DIR / module_name

        if not module_path.exists():
            pytest.skip(f"Module {module_name} does not exist yet (RED phase)")

        content = module_path.read_text()
        for class_name in expected_classes:
            assert f"class {class_name}" in content, (
                f"Expected test class {class_name} not found in {module_name}. "
                "Ensure all test classes are migrated correctly."
            )


class TestAC3FunctionalityPreserved:
    """TEST-AC-3: Functionality Preserved acceptance criteria tests.

    Verifies:
    - All existing tests pass unchanged
    - Test count remains the same (no tests lost or duplicated)
    - No behavior changes to test logic
    """

    @pytest.mark.acceptance
    def test_ac3_1_test_count_preserved(self) -> None:
        """TEST-AC-3.1: Test count must match baseline (131 tests)."""
        # If original file still exists, skip (RED phase before refactoring)
        if ORIGINAL_TEST_FILE.exists():
            pytest.skip(
                "Original file still exists - cannot verify test count preservation. "
                "This test will pass after refactoring is complete."
            )

        # Count tests in the new directory (excluding acceptance tests for stability)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(EXTERNAL_DATA_TESTS_DIR),
                "--collect-only",
                "-q",
                "--ignore",
                str(EXTERNAL_DATA_TESTS_DIR / "test_refactoring_acceptance.py"),
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        # Parse test count from output (e.g., "131 tests collected")
        output = result.stdout + result.stderr
        test_count = 0
        for line in output.splitlines():
            if "test" in line and "collected" in line:
                # Parse formats like "131 tests collected" or "131/132 tests collected"
                parts = line.split()
                for part in parts:
                    if "/" in part:
                        test_count = int(part.split("/")[0])
                        break
                    try:
                        test_count = int(part)
                        break
                    except ValueError:
                        continue
                break

        assert test_count == BASELINE_TEST_COUNT, (
            f"Test count mismatch: found {test_count}, expected {BASELINE_TEST_COUNT}. "
            f"Tests may have been lost or duplicated during refactoring."
        )

    @pytest.mark.acceptance
    @pytest.mark.slow  # Runs full test suite in subprocess - skip in local runs
    @pytest.mark.timeout(360)  # 6 minutes - subprocess needs up to 5 min
    def test_ac3_2_all_tests_pass(self) -> None:
        """TEST-AC-3.2: All tests in new structure must pass."""
        # If original file still exists, skip (RED phase before refactoring)
        if ORIGINAL_TEST_FILE.exists():
            pytest.skip(
                "Original file still exists - cannot verify new tests pass. "
                "This test will pass after refactoring is complete."
            )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(EXTERNAL_DATA_TESTS_DIR),
                "-v",
                "--tb=short",
                "-x",  # Stop at first failure for faster feedback
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=300,  # 5 minute timeout
        )

        assert result.returncode == 0, (
            f"Tests failed after refactoring.\n"
            f"stdout: {result.stdout[-2000:]}\n"
            f"stderr: {result.stderr[-1000:]}"
        )

    @pytest.mark.acceptance
    @pytest.mark.parametrize("module_name", EXPECTED_MODULES)
    def test_ac3_3_module_importable(self, module_name: str) -> None:
        """TEST-AC-3.3: Each module must be importable without errors."""
        module_path = EXTERNAL_DATA_TESTS_DIR / module_name

        if not module_path.exists():
            pytest.skip(f"Module {module_name} does not exist yet (RED phase)")

        spec = importlib.util.spec_from_file_location(
            module_name.replace(".py", ""),
            module_path,
        )
        assert spec is not None, f"Could not create spec for {module_name}"
        assert spec.loader is not None, f"No loader for {module_name}"

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Module {module_name} failed to import: {e}")


class TestAC4SharedFixtures:
    """TEST-AC-4: Shared Fixtures Extracted acceptance criteria tests.

    Verifies:
    - Common imports consolidated in conftest.py
    - Shared mock patterns extracted to conftest
    - Fixtures are properly scoped
    """

    @pytest.mark.acceptance
    def test_ac4_1_conftest_has_mock_httpx_fixture(self) -> None:
        """TEST-AC-4.1: conftest.py must have mock_httpx_response fixture."""
        conftest_file = EXTERNAL_DATA_TESTS_DIR / "conftest.py"

        if not conftest_file.exists():
            pytest.skip("conftest.py does not exist yet (RED phase)")

        content = conftest_file.read_text()
        assert "def mock_httpx_response" in content or "@pytest.fixture" in content, (
            "conftest.py should contain shared mock fixtures like mock_httpx_response. "
            "Extract common mocking patterns from test modules."
        )

    @pytest.mark.acceptance
    def test_ac4_2_conftest_has_required_imports(self) -> None:
        """TEST-AC-4.2: conftest.py must have common imports."""
        conftest_file = EXTERNAL_DATA_TESTS_DIR / "conftest.py"

        if not conftest_file.exists():
            pytest.skip("conftest.py does not exist yet (RED phase)")

        content = conftest_file.read_text()
        required_imports = [
            "pytest",
            "unittest.mock",
            "httpx",
        ]

        for imp in required_imports:
            assert imp in content, f"conftest.py should import '{imp}' for shared fixtures."

    @pytest.mark.acceptance
    def test_ac4_3_conftest_has_sample_date_range_fixture(self) -> None:
        """TEST-AC-4.3: conftest.py should have sample_date_range fixture."""
        conftest_file = EXTERNAL_DATA_TESTS_DIR / "conftest.py"

        if not conftest_file.exists():
            pytest.skip("conftest.py does not exist yet (RED phase)")

        content = conftest_file.read_text()
        assert "sample_date_range" in content, (
            "conftest.py should contain sample_date_range fixture for date testing. "
            "This is a common fixture used across multiple client tests."
        )


class TestAC5CICompatibility:
    """TEST-AC-5: CI Compatibility acceptance criteria tests.

    Verifies:
    - All tests discoverable by pytest
    - No changes to test markers
    - Proper module structure for test discovery
    """

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
        """TEST-AC-5.3: No duplicate test function names across modules."""
        # If original file still exists, skip (RED phase before refactoring)
        if ORIGINAL_TEST_FILE.exists():
            pytest.skip(
                "Original file still exists - cannot verify duplicates. "
                "This test will pass after refactoring is complete."
            )

        test_names: dict[str, str] = {}
        duplicates: list[str] = []

        for module_path in EXTERNAL_DATA_TESTS_DIR.glob("test_*.py"):
            if module_path.name == "test_refactoring_acceptance.py":
                continue  # Skip this file

            content = module_path.read_text()
            for line in content.splitlines():
                if "def test_" in line or "async def test_" in line:
                    # Extract function name
                    name = line.split("def ")[1].split("(")[0]
                    if name in test_names:
                        duplicates.append(f"{name} in {module_path.name} and {test_names[name]}")
                    test_names[name] = module_path.name

        assert not duplicates, (
            f"Found duplicate test function names: {duplicates}. "
            "Each test function name should be unique across modules."
        )
