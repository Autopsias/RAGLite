"""ATDD Acceptance Tests - AC2: New Module Structure.

Story: 7-1-split-test-external-data-clients
Epic: 7 - Technical Debt & Code Quality

Verifies:
- tests/unit/external_data/ directory exists
- All expected modules exist
- conftest.py exists with shared fixtures
- __init__.py exists
"""

from pathlib import Path

import pytest

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TESTS_ROOT = PROJECT_ROOT / "tests"
EXTERNAL_DATA_TESTS_DIR = TESTS_ROOT / "unit" / "external_data"

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

# Expected test classes per module
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
        "TestBaseGovStory695",
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

CONFTEST_MAX_LOC = 200


class TestAC2NewModuleStructure:
    """TEST-AC-2: New Module Structure acceptance criteria tests."""

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
