"""Baseline Tests for Story 8.2: External Data Client Refactoring.

These tests document the CURRENT state before refactoring.
They should PASS before refactoring and FAIL after refactoring is complete.

Purpose: Verify the refactoring actually changes the codebase.

NOTE: Story 8.2 refactoring is COMPLETE. These baseline tests are now skipped
as they document the pre-refactoring state, which no longer applies.
"""

from __future__ import annotations

import pytest

from tests.unit.story_8_2.conftest import (
    BASE_CLIENT_FILE,
    BASEGOV_FILE,
    BASEGOV_PACKAGE,
    ECB_FILE,
    ECB_PACKAGE,
    EUROSTAT_FILE,
    EUROSTAT_PACKAGE,
    HARD_LOC_LIMIT,
    STORAGE_FILE,
    STORAGE_PACKAGE,
    count_lines_simple,
)

# Skip all baseline tests as Story 8.2 refactoring is complete
pytestmark = pytest.mark.skip(
    reason="Story 8.2 refactoring complete - baseline tests no longer applicable"
)


class TestBaselineCurrentState:
    """Baseline tests documenting current (pre-refactoring) state."""

    def test_baseline_storage_exceeds_limit(self) -> None:
        """[BASELINE] storage.py currently exceeds 500 LOC.

        Current: 1,633 LOC
        Expected after refactoring: < 100 LOC (shim)

        This test PASSES now, FAILS after refactoring.
        """
        loc = count_lines_simple(STORAGE_FILE)
        assert loc >= HARD_LOC_LIMIT, (
            f"storage.py has {loc} LOC, expected >= {HARD_LOC_LIMIT}. "
            f"If refactoring is complete, this baseline test should FAIL."
        )

    def test_baseline_basegov_exceeds_limit(self) -> None:
        """[BASELINE] basegov.py currently exceeds 500 LOC.

        Current: 1,066 LOC
        Expected after refactoring: < 100 LOC (shim)

        This test PASSES now, FAILS after refactoring.
        """
        loc = count_lines_simple(BASEGOV_FILE)
        assert loc >= HARD_LOC_LIMIT, (
            f"basegov.py has {loc} LOC, expected >= {HARD_LOC_LIMIT}. "
            f"If refactoring is complete, this baseline test should FAIL."
        )

    def test_baseline_ecb_exceeds_limit(self) -> None:
        """[BASELINE] ecb.py currently exceeds 500 LOC.

        Current: 1,033 LOC
        Expected after refactoring: < 100 LOC (shim)

        This test PASSES now, FAILS after refactoring.
        """
        loc = count_lines_simple(ECB_FILE)
        assert loc >= HARD_LOC_LIMIT, (
            f"ecb.py has {loc} LOC, expected >= {HARD_LOC_LIMIT}. "
            f"If refactoring is complete, this baseline test should FAIL."
        )

    def test_baseline_eurostat_exceeds_limit(self) -> None:
        """[BASELINE] eurostat.py currently exceeds 500 LOC.

        Current: 957 LOC
        Expected after refactoring: < 100 LOC (shim)

        This test PASSES now, FAILS after refactoring.
        """
        loc = count_lines_simple(EUROSTAT_FILE)
        assert loc >= HARD_LOC_LIMIT, (
            f"eurostat.py has {loc} LOC, expected >= {HARD_LOC_LIMIT}. "
            f"If refactoring is complete, this baseline test should FAIL."
        )


class TestBaselinePackagesDoNotExist:
    """Baseline tests verifying new packages don't exist yet."""

    def test_baseline_storage_package_does_not_exist(self) -> None:
        """[BASELINE] storage/ package should not exist yet.

        Expected after refactoring: raglite/external_data/storage/ exists

        This test PASSES now, FAILS after refactoring.
        """
        assert not STORAGE_PACKAGE.exists(), (
            f"storage/ package exists at {STORAGE_PACKAGE}. "
            f"If refactoring is complete, this baseline test should FAIL."
        )

    def test_baseline_basegov_package_does_not_exist(self) -> None:
        """[BASELINE] basegov/ package should not exist yet.

        Expected after refactoring: clients/basegov/ exists

        This test PASSES now, FAILS after refactoring.
        """
        assert not BASEGOV_PACKAGE.exists(), (
            f"basegov/ package exists at {BASEGOV_PACKAGE}. "
            f"If refactoring is complete, this baseline test should FAIL."
        )

    def test_baseline_ecb_package_does_not_exist(self) -> None:
        """[BASELINE] ecb/ package should not exist yet.

        Expected after refactoring: clients/ecb/ exists

        This test PASSES now, FAILS after refactoring.
        """
        assert not ECB_PACKAGE.exists(), (
            f"ecb/ package exists at {ECB_PACKAGE}. "
            f"If refactoring is complete, this baseline test should FAIL."
        )

    def test_baseline_eurostat_package_does_not_exist(self) -> None:
        """[BASELINE] eurostat/ package should not exist yet.

        Expected after refactoring: clients/eurostat/ exists

        This test PASSES now, FAILS after refactoring.
        """
        assert not EUROSTAT_PACKAGE.exists(), (
            f"eurostat/ package exists at {EUROSTAT_PACKAGE}. "
            f"If refactoring is complete, this baseline test should FAIL."
        )

    def test_baseline_base_client_does_not_exist(self) -> None:
        """[BASELINE] base.py should not exist yet.

        Expected after refactoring: clients/base.py exists

        This test PASSES now, FAILS after refactoring.
        """
        assert not BASE_CLIENT_FILE.exists(), (
            f"base.py exists at {BASE_CLIENT_FILE}. "
            f"If refactoring is complete, this baseline test should FAIL."
        )


class TestBaselineImportsWork:
    """Baseline tests verifying current imports work."""

    def test_baseline_old_storage_import_works(self) -> None:
        """[BASELINE] Old storage import should work.

        Current: from raglite.external_data.storage import ExternalDataStorage
        Expected: Still works after refactoring (via shim with deprecation)
        """
        try:
            from raglite.external_data.storage import ExternalDataStorage

            assert ExternalDataStorage is not None
        except ImportError as e:
            pytest.fail(f"Baseline import failed: {e}")

    def test_baseline_old_basegov_import_works(self) -> None:
        """[BASELINE] Old basegov import should work.

        Current: from raglite.external_data.clients.basegov import BaseGovClient
        Expected: Still works after refactoring (via shim with deprecation)
        """
        try:
            from raglite.external_data.clients.basegov import BaseGovClient

            assert BaseGovClient is not None
        except ImportError as e:
            pytest.fail(f"Baseline import failed: {e}")

    def test_baseline_old_ecb_import_works(self) -> None:
        """[BASELINE] Old ecb import should work.

        Current: from raglite.external_data.clients.ecb import ECBClient
        Expected: Still works after refactoring (via shim with deprecation)
        """
        try:
            from raglite.external_data.clients.ecb import ECBClient

            assert ECBClient is not None
        except ImportError as e:
            pytest.fail(f"Baseline import failed: {e}")

    def test_baseline_old_eurostat_import_works(self) -> None:
        """[BASELINE] Old eurostat import should work.

        Current: from raglite.external_data.clients.eurostat import EurostatClient
        Expected: Still works after refactoring (via shim with deprecation)
        """
        try:
            from raglite.external_data.clients.eurostat import EurostatClient

            assert EurostatClient is not None
        except ImportError as e:
            pytest.fail(f"Baseline import failed: {e}")
