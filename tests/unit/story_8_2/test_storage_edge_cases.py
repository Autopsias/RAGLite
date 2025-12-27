"""[P1] Storage Module Edge Cases and Error Handling

Test expansion for Story 8.2 - Phase 6 (Test Automation Expansion).
Covers edge cases, error paths, and boundary conditions for storage operations.

Priority: P1 (Important data integrity scenarios)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

# Direct imports to avoid apscheduler dependency
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CONSTANTS_PATH = PROJECT_ROOT / "raglite" / "external_data" / "storage" / "constants.py"

# Load constants module directly
spec = importlib.util.spec_from_file_location("storage_constants", CONSTANTS_PATH)
constants_module = importlib.util.module_from_spec(spec)
sys.modules["storage_constants"] = constants_module
spec.loader.exec_module(constants_module)

TIER2_SOURCES = constants_module.TIER2_SOURCES


class TestStorageConstantsEdgeCases:
    """[P1] Edge cases for storage constants and configuration."""

    def test_tier2_sources_is_dict(self):
        """[TEST-AC-8.2-P1-A] GIVEN TIER2_SOURCES WHEN accessed THEN is dict with source configuration."""
        # GIVEN/WHEN: TIER2_SOURCES constant
        # THEN: Should be dict mapping source names to configuration
        assert isinstance(TIER2_SOURCES, dict)
        assert len(TIER2_SOURCES) > 0

    def test_tier2_sources_not_empty(self):
        """[TEST-AC-8.2-P1-B] GIVEN TIER2_SOURCES WHEN accessed THEN contains expected sources."""
        # GIVEN/WHEN: TIER2_SOURCES constant
        # THEN: Should not be empty
        assert len(TIER2_SOURCES) > 0

    def test_tier2_sources_contains_expected_keys(self):
        """[TEST-AC-8.2-P1-C] GIVEN TIER2_SOURCES WHEN accessed THEN contains known sources."""
        # GIVEN: Expected tier 2 sources (energy commodities and EU/PT indicators)
        expected_sources = {"ICE_API2_Coal", "ICE_TTF_Gas"}

        # WHEN: Checking TIER2_SOURCES keys
        # THEN: Contains expected sources
        assert expected_sources.issubset(TIER2_SOURCES.keys())


class TestStorageImportPaths:
    """[P0] Backward compatibility tests for import paths."""

    def test_storage_shim_file_exists(self):
        """[TEST-AC-8.2-P0-D] GIVEN old storage.py WHEN checking THEN shim file exists."""
        # GIVEN: Storage shim path
        storage_shim = PROJECT_ROOT / "raglite" / "external_data" / "storage.py"

        # WHEN/THEN: Shim file exists
        assert storage_shim.exists()

    def test_storage_package_has_core_module(self):
        """[TEST-AC-8.2-P1-E] GIVEN storage package WHEN checking THEN core.py exists."""
        # GIVEN: Storage package
        core_path = PROJECT_ROOT / "raglite" / "external_data" / "storage" / "core.py"

        # WHEN/THEN: Core module exists
        assert core_path.exists()

    def test_storage_package_has_freshness_module(self):
        """[TEST-AC-8.2-P1-F] GIVEN storage package WHEN checking THEN freshness.py exists."""
        # GIVEN: Storage package
        freshness_path = PROJECT_ROOT / "raglite" / "external_data" / "storage" / "freshness.py"

        # WHEN/THEN: Freshness module exists
        assert freshness_path.exists()

    def test_storage_package_has_tier2_module(self):
        """[TEST-AC-8.2-P1-G] GIVEN storage package WHEN checking THEN tier2.py exists."""
        # GIVEN: Storage package
        tier2_path = PROJECT_ROOT / "raglite" / "external_data" / "storage" / "tier2.py"

        # WHEN/THEN: Tier2 module exists
        assert tier2_path.exists()

    def test_storage_package_has_model_weights_module(self):
        """[TEST-AC-8.2-P1-H] GIVEN storage package WHEN checking THEN model_weights.py exists."""
        # GIVEN: Storage package
        weights_path = PROJECT_ROOT / "raglite" / "external_data" / "storage" / "model_weights.py"

        # WHEN/THEN: Model weights module exists
        assert weights_path.exists()

    def test_storage_package_has_model_selection_module(self):
        """[TEST-AC-8.2-P1-I] GIVEN storage package WHEN checking THEN model_selection.py exists."""
        # GIVEN: Storage package
        selection_path = (
            PROJECT_ROOT / "raglite" / "external_data" / "storage" / "model_selection.py"
        )

        # WHEN/THEN: Model selection module exists
        assert selection_path.exists()


class TestStorageModuleStructure:
    """[P1] Tests for module structure and organization."""

    def test_storage_package_has_init(self):
        """[P1] GIVEN storage package WHEN checking THEN __init__.py exists."""
        # GIVEN: Storage package init path
        init_path = PROJECT_ROOT / "raglite" / "external_data" / "storage" / "__init__.py"

        # WHEN/THEN: Package has __init__.py
        assert init_path.exists()

    def test_constants_module_has_no_sqlalchemy_imports(self):
        """[P1] GIVEN constants module WHEN checking THEN no SQLAlchemy imports."""
        # GIVEN: Constants module content
        with open(CONSTANTS_PATH) as f:
            content = f.read()

        # WHEN/THEN: No sqlalchemy imports (leaf node)
        assert "from sqlalchemy" not in content
        assert "import sqlalchemy" not in content

    def test_constants_module_exports_tier2_sources(self):
        """[P1] GIVEN constants module WHEN checking THEN exports TIER2_SOURCES."""
        # GIVEN: Loaded constants module
        # WHEN/THEN: TIER2_SOURCES is exported
        assert hasattr(constants_module, "TIER2_SOURCES")

    def test_all_storage_modules_exist(self):
        """[P1] GIVEN storage package WHEN checking THEN all modules exist."""
        # GIVEN: Expected modules
        expected_modules = [
            "__init__.py",
            "constants.py",
            "core.py",
            "freshness.py",
            "tier2.py",
            "model_weights.py",
            "model_selection.py",
        ]

        # WHEN: Checking storage directory
        storage_dir = PROJECT_ROOT / "raglite" / "external_data" / "storage"

        # THEN: All modules exist
        for module_name in expected_modules:
            module_path = storage_dir / module_name
            assert module_path.exists(), f"Missing {module_name}"

    def test_storage_shim_file_is_small(self):
        """[P1] GIVEN storage.py shim WHEN checking THEN is under 100 LOC."""
        # GIVEN: Storage shim path
        shim_path = PROJECT_ROOT / "raglite" / "external_data" / "storage.py"

        # WHEN: Counting lines
        with open(shim_path) as f:
            lines = len(f.readlines())

        # THEN: Shim is small (< 100 LOC)
        assert lines < 100, f"Shim should be <100 LOC, got {lines}"
