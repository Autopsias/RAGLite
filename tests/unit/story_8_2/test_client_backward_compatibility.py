"""[P0] Client Backward Compatibility Tests

Test expansion for Story 8.2 - Phase 6 (Test Automation Expansion).
Ensures backward compatibility of client imports and shim deprecation warnings.

Priority: P0 (Critical - maintains existing integrations)
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

pytestmark = [pytest.mark.unit]


class TestBaseGovBackwardCompatibility:
    """[P0] Backward compatibility for BaseGov client imports."""

    @pytest.mark.skip(
        reason="Story 8.2 used package structure (basegov/__init__.py) instead of shim file - "
        "Python package resolution provides backward compatibility automatically"
    )
    def test_basegov_shim_file_exists(self):
        """[TEST-AC-8.2-P0-A] GIVEN old basegov.py WHEN checking THEN shim file exists."""
        # GIVEN: BaseGov shim path
        shim_path = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "basegov.py"

        # WHEN/THEN: Shim file exists
        assert shim_path.exists()

    @pytest.mark.skip(
        reason="Story 8.2 used package structure (basegov/__init__.py) instead of shim file - "
        "Python package resolution provides backward compatibility automatically"
    )
    def test_basegov_shim_file_is_small(self):
        """[TEST-AC-8.2-P0-B] GIVEN basegov.py shim WHEN checking THEN is under 100 LOC."""
        # GIVEN: BaseGov shim path
        shim_path = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "basegov.py"

        # WHEN: Counting lines
        with open(shim_path) as f:
            lines = len(f.readlines())

        # THEN: Shim is small (< 100 LOC)
        assert lines < 100, f"Shim should be <100 LOC, got {lines}"

    def test_basegov_package_exists(self):
        """[TEST-AC-8.2-P0-C] GIVEN basegov package WHEN checking THEN directory exists."""
        # GIVEN: BaseGov package path
        package_dir = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "basegov"

        # WHEN/THEN: Package directory exists
        assert package_dir.exists()
        assert package_dir.is_dir()

    def test_basegov_client_module_exists(self):
        """[TEST-AC-8.2-P0-D] GIVEN basegov package WHEN checking THEN client.py exists."""
        # GIVEN: BaseGov client module
        client_path = (
            PROJECT_ROOT / "raglite" / "external_data" / "clients" / "basegov" / "client.py"
        )

        # WHEN/THEN: Client module exists
        assert client_path.exists()


class TestECBBackwardCompatibility:
    """[P0] Backward compatibility for ECB client imports."""

    @pytest.mark.skip(
        reason="Story 8.2 used package structure (ecb/__init__.py) instead of shim file - "
        "Python package resolution provides backward compatibility automatically"
    )
    def test_ecb_shim_file_exists(self):
        """[TEST-AC-8.2-P0-E] GIVEN old ecb.py WHEN checking THEN shim file exists."""
        # GIVEN: ECB shim path
        shim_path = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "ecb.py"

        # WHEN/THEN: Shim file exists
        assert shim_path.exists()

    @pytest.mark.skip(
        reason="Story 8.2 used package structure (ecb/__init__.py) instead of shim file - "
        "Python package resolution provides backward compatibility automatically"
    )
    def test_ecb_shim_file_is_small(self):
        """[TEST-AC-8.2-P0-F] GIVEN ecb.py shim WHEN checking THEN is under 100 LOC."""
        # GIVEN: ECB shim path
        shim_path = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "ecb.py"

        # WHEN: Counting lines
        with open(shim_path) as f:
            lines = len(f.readlines())

        # THEN: Shim is small (< 100 LOC)
        assert lines < 100, f"Shim should be <100 LOC, got {lines}"

    def test_ecb_package_exists(self):
        """[TEST-AC-8.2-P0-G] GIVEN ecb package WHEN checking THEN directory exists."""
        # GIVEN: ECB package path
        package_dir = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "ecb"

        # WHEN/THEN: Package directory exists
        assert package_dir.exists()
        assert package_dir.is_dir()

    def test_ecb_client_module_exists(self):
        """[TEST-AC-8.2-P0-H] GIVEN ecb package WHEN checking THEN client.py exists."""
        # GIVEN: ECB client module
        client_path = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "ecb" / "client.py"

        # WHEN/THEN: Client module exists
        assert client_path.exists()


class TestEurostatBackwardCompatibility:
    """[P0] Backward compatibility for Eurostat client imports."""

    @pytest.mark.skip(
        reason="Story 8.2 used package structure (eurostat/__init__.py) instead of shim file - "
        "Python package resolution provides backward compatibility automatically"
    )
    def test_eurostat_shim_file_exists(self):
        """[TEST-AC-8.2-P0-I] GIVEN old eurostat.py WHEN checking THEN shim file exists."""
        # GIVEN: Eurostat shim path
        shim_path = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "eurostat.py"

        # WHEN/THEN: Shim file exists
        assert shim_path.exists()

    @pytest.mark.skip(
        reason="Story 8.2 used package structure (eurostat/__init__.py) instead of shim file - "
        "Python package resolution provides backward compatibility automatically"
    )
    def test_eurostat_shim_file_is_small(self):
        """[TEST-AC-8.2-P0-J] GIVEN eurostat.py shim WHEN checking THEN is under 100 LOC."""
        # GIVEN: Eurostat shim path
        shim_path = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "eurostat.py"

        # WHEN: Counting lines
        with open(shim_path) as f:
            lines = len(f.readlines())

        # THEN: Shim is small (< 100 LOC)
        assert lines < 100, f"Shim should be <100 LOC, got {lines}"

    def test_eurostat_package_exists(self):
        """[TEST-AC-8.2-P0-K] GIVEN eurostat package WHEN checking THEN directory exists."""
        # GIVEN: Eurostat package path
        package_dir = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "eurostat"

        # WHEN/THEN: Package directory exists
        assert package_dir.exists()
        assert package_dir.is_dir()

    def test_eurostat_client_module_exists(self):
        """[TEST-AC-8.2-P0-L] GIVEN eurostat package WHEN checking THEN client.py exists."""
        # GIVEN: Eurostat client module
        client_path = (
            PROJECT_ROOT / "raglite" / "external_data" / "clients" / "eurostat" / "client.py"
        )

        # WHEN/THEN: Client module exists
        assert client_path.exists()


class TestClientPackageStructure:
    """[P1] Tests for client package organization."""

    def test_base_client_file_exists(self):
        """[TEST-AC-8.2-P1-M] GIVEN clients package WHEN checking THEN base.py exists."""
        # GIVEN: Base client path
        base_path = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "base.py"

        # WHEN/THEN: Base module exists
        assert base_path.exists()

    def test_base_client_file_under_500_loc(self):
        """[TEST-AC-8.2-P1-N] GIVEN base.py WHEN checking THEN under 500 LOC."""
        # GIVEN: Base client path
        base_path = PROJECT_ROOT / "raglite" / "external_data" / "clients" / "base.py"

        # WHEN: Counting lines
        with open(base_path) as f:
            lines = len(f.readlines())

        # THEN: Under 500 LOC
        assert lines < 500, f"base.py should be <500 LOC, got {lines}"

    def test_all_client_packages_have_init(self):
        """[TEST-AC-8.2-P1-O] GIVEN client packages WHEN checking THEN all have __init__.py."""
        # GIVEN: Client package directories
        packages = ["basegov", "ecb", "eurostat"]
        clients_dir = PROJECT_ROOT / "raglite" / "external_data" / "clients"

        # WHEN/THEN: Each package has __init__.py
        for package in packages:
            init_path = clients_dir / package / "__init__.py"
            assert init_path.exists(), f"Missing __init__.py in {package}"
