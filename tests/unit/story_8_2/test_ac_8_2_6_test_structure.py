"""AC-8.2.6 ATDD Tests: Test File Structure Mirrors Production.

Story 8.2: External Data Client Refactoring

Given the production module structure after refactoring
When the test refactoring is complete
Then test file structure mirrors production module structure

Verification:
- Each production module has a corresponding test module
- Tests are organized in same directory structure
- Easy to locate tests for any production module
- Shared fixtures in conftest.py files
"""

from __future__ import annotations

import pytest

from tests.unit.story_8_2.conftest import (
    BASEGOV_PACKAGE,
    CLIENTS_DIR,
    ECB_PACKAGE,
    EUROSTAT_PACKAGE,
    EXTERNAL_DATA_TESTS_DIR,
    STORAGE_PACKAGE,
    get_python_files_recursive,
)

pytestmark = [pytest.mark.unit]


class TestAC826ProductionToTestMapping:
    """[AC-8.2.6] Verify 1:1 mapping between production and test modules."""

    def test_ac_8_2_6_storage_core_has_test(self) -> None:
        """[TEST-AC-8.2.6-A] storage/core.py should have corresponding test.

        Given storage/core.py exists
        When we check test directory
        Then tests/unit/external_data/storage/test_core.py exists
        """
        prod_file = STORAGE_PACKAGE / "core.py"
        test_file = EXTERNAL_DATA_TESTS_DIR / "storage" / "test_core.py"

        if not prod_file.exists():
            pytest.skip("Production file not yet created")

        assert test_file.exists(), f"Missing test file for {prod_file.name}. Expected: {test_file}"

    def test_ac_8_2_6_storage_freshness_has_test(self) -> None:
        """[TEST-AC-8.2.6-B] storage/freshness.py should have corresponding test."""
        prod_file = STORAGE_PACKAGE / "freshness.py"
        test_file = EXTERNAL_DATA_TESTS_DIR / "storage" / "test_freshness.py"

        if not prod_file.exists():
            pytest.skip("Production file not yet created")

        assert test_file.exists(), f"Missing test file for {prod_file.name}. Expected: {test_file}"

    def test_ac_8_2_6_storage_tier2_has_test(self) -> None:
        """[TEST-AC-8.2.6-C] storage/tier2.py should have corresponding test."""
        prod_file = STORAGE_PACKAGE / "tier2.py"
        test_file = EXTERNAL_DATA_TESTS_DIR / "storage" / "test_tier2.py"

        if not prod_file.exists():
            pytest.skip("Production file not yet created")

        assert test_file.exists(), f"Missing test file for {prod_file.name}. Expected: {test_file}"

    def test_ac_8_2_6_storage_model_weights_has_test(self) -> None:
        """[TEST-AC-8.2.6-D] storage/model_weights.py should have test."""
        prod_file = STORAGE_PACKAGE / "model_weights.py"
        test_file = EXTERNAL_DATA_TESTS_DIR / "storage" / "test_model_weights.py"

        if not prod_file.exists():
            pytest.skip("Production file not yet created")

        assert test_file.exists(), f"Missing test file for {prod_file.name}. Expected: {test_file}"

    def test_ac_8_2_6_storage_model_selection_has_test(self) -> None:
        """[TEST-AC-8.2.6-E] storage/model_selection.py should have test."""
        prod_file = STORAGE_PACKAGE / "model_selection.py"
        test_file = EXTERNAL_DATA_TESTS_DIR / "storage" / "test_model_selection.py"

        if not prod_file.exists():
            pytest.skip("Production file not yet created")

        assert test_file.exists(), f"Missing test file for {prod_file.name}. Expected: {test_file}"

    def test_ac_8_2_6_base_client_has_test(self) -> None:
        """[TEST-AC-8.2.6-F] clients/base.py should have corresponding test."""
        prod_file = CLIENTS_DIR / "base.py"
        test_file = EXTERNAL_DATA_TESTS_DIR / "clients" / "test_base.py"

        if not prod_file.exists():
            pytest.skip("Production file not yet created")

        assert test_file.exists(), f"Missing test file for {prod_file.name}. Expected: {test_file}"

    def test_ac_8_2_6_basegov_client_has_test(self) -> None:
        """[TEST-AC-8.2.6-G] basegov/client.py should have corresponding test."""
        prod_file = BASEGOV_PACKAGE / "client.py"
        test_file = EXTERNAL_DATA_TESTS_DIR / "clients" / "basegov" / "test_client.py"

        if not prod_file.exists():
            pytest.skip("Production file not yet created")

        assert test_file.exists(), f"Missing test file for {prod_file.name}. Expected: {test_file}"

    def test_ac_8_2_6_ecb_client_has_test(self) -> None:
        """[TEST-AC-8.2.6-H] ecb/client.py should have corresponding test."""
        prod_file = ECB_PACKAGE / "client.py"
        test_file = EXTERNAL_DATA_TESTS_DIR / "clients" / "ecb" / "test_client.py"

        if not prod_file.exists():
            pytest.skip("Production file not yet created")

        assert test_file.exists(), f"Missing test file for {prod_file.name}. Expected: {test_file}"

    def test_ac_8_2_6_eurostat_client_has_test(self) -> None:
        """[TEST-AC-8.2.6-I] eurostat/client.py should have corresponding test."""
        prod_file = EUROSTAT_PACKAGE / "client.py"
        test_file = EXTERNAL_DATA_TESTS_DIR / "clients" / "eurostat" / "test_client.py"

        if not prod_file.exists():
            pytest.skip("Production file not yet created")

        assert test_file.exists(), f"Missing test file for {prod_file.name}. Expected: {test_file}"


class TestAC826DirectoryStructure:
    """[AC-8.2.6] Verify test directory structure matches production."""

    def test_ac_8_2_6_storage_test_dir_exists(self) -> None:
        """[TEST-AC-8.2.6-J] tests/unit/external_data/storage/ should exist.

        Given storage/ package exists in production
        When we check test directory
        Then corresponding test directory exists
        """
        storage_test_dir = EXTERNAL_DATA_TESTS_DIR / "storage"
        assert storage_test_dir.exists(), f"Storage test directory not found at {storage_test_dir}"

    def test_ac_8_2_6_clients_test_dir_exists(self) -> None:
        """[TEST-AC-8.2.6-K] tests/unit/external_data/clients/ should exist.

        Given clients/ package exists in production
        When we check test directory
        Then corresponding test directory exists
        """
        clients_test_dir = EXTERNAL_DATA_TESTS_DIR / "clients"
        assert clients_test_dir.exists(), f"Clients test directory not found at {clients_test_dir}"

    def test_ac_8_2_6_basegov_test_dir_exists(self) -> None:
        """[TEST-AC-8.2.6-L] tests/.../clients/basegov/ should exist."""
        basegov_test_dir = EXTERNAL_DATA_TESTS_DIR / "clients" / "basegov"
        assert basegov_test_dir.exists(), f"Basegov test directory not found at {basegov_test_dir}"

    def test_ac_8_2_6_ecb_test_dir_exists(self) -> None:
        """[TEST-AC-8.2.6-M] tests/.../clients/ecb/ should exist."""
        ecb_test_dir = EXTERNAL_DATA_TESTS_DIR / "clients" / "ecb"
        assert ecb_test_dir.exists(), f"ECB test directory not found at {ecb_test_dir}"

    def test_ac_8_2_6_eurostat_test_dir_exists(self) -> None:
        """[TEST-AC-8.2.6-N] tests/.../clients/eurostat/ should exist."""
        eurostat_test_dir = EXTERNAL_DATA_TESTS_DIR / "clients" / "eurostat"
        assert eurostat_test_dir.exists(), (
            f"Eurostat test directory not found at {eurostat_test_dir}"
        )


class TestAC826SharedFixtures:
    """[AC-8.2.6] Verify shared fixtures in conftest.py files."""

    def test_ac_8_2_6_external_data_conftest_exists(self) -> None:
        """[TEST-AC-8.2.6-O] Main conftest.py should exist.

        Expected: tests/unit/external_data/conftest.py
        """
        conftest = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        assert conftest.exists(), f"Main conftest not found at {conftest}"

    def test_ac_8_2_6_storage_conftest_exists(self) -> None:
        """[TEST-AC-8.2.6-P] Storage conftest.py should exist.

        Expected: tests/unit/external_data/storage/conftest.py
        """
        conftest = EXTERNAL_DATA_TESTS_DIR / "storage" / "conftest.py"
        assert conftest.exists(), f"Storage conftest not found at {conftest}"

    def test_ac_8_2_6_clients_conftest_exists(self) -> None:
        """[TEST-AC-8.2.6-Q] Clients conftest.py should exist.

        Expected: tests/unit/external_data/clients/conftest.py
        """
        conftest = EXTERNAL_DATA_TESTS_DIR / "clients" / "conftest.py"
        assert conftest.exists(), f"Clients conftest not found at {conftest}"

    def test_ac_8_2_6_conftest_provides_mock_fixtures(self) -> None:
        """[TEST-AC-8.2.6-R] Main conftest should provide mock fixtures.

        Expected fixtures: mock_httpx_response, mock_httpx_client
        """
        conftest = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        if not conftest.exists():
            pytest.fail(f"Main conftest not found at {conftest}")

        content = conftest.read_text()
        expected_fixtures = ["mock_httpx_response", "mock_httpx_client"]

        for fixture in expected_fixtures:
            assert fixture in content, f"Expected fixture '{fixture}' not found in conftest.py"


class TestAC826TestDiscoverability:
    """[AC-8.2.6] Verify tests are discoverable by pytest."""

    def test_ac_8_2_6_all_test_dirs_have_init(self) -> None:
        """[TEST-AC-8.2.6-S] All test directories should have __init__.py.

        This ensures pytest can discover all test modules.
        """
        expected_dirs = [
            EXTERNAL_DATA_TESTS_DIR,
            EXTERNAL_DATA_TESTS_DIR / "storage",
            EXTERNAL_DATA_TESTS_DIR / "clients",
            EXTERNAL_DATA_TESTS_DIR / "clients" / "basegov",
            EXTERNAL_DATA_TESTS_DIR / "clients" / "ecb",
            EXTERNAL_DATA_TESTS_DIR / "clients" / "eurostat",
        ]

        for test_dir in expected_dirs:
            if test_dir.exists():
                init_file = test_dir / "__init__.py"
                assert init_file.exists(), f"Missing __init__.py in {test_dir}"

    def test_ac_8_2_6_test_files_follow_naming(self) -> None:
        """[TEST-AC-8.2.6-T] Test files should follow test_*.py naming.

        This ensures pytest can discover all tests.
        """
        all_test_files = get_python_files_recursive(EXTERNAL_DATA_TESTS_DIR)

        violations = []
        for f in all_test_files:
            # Skip conftest and __init__ files
            if f.name in ("conftest.py", "__init__.py"):
                continue
            # Skip __pycache__
            if "__pycache__" in str(f):
                continue

            if not f.name.startswith("test_"):
                violations.append(f.name)

        assert not violations, f"Test files not following test_*.py naming: {violations}"
