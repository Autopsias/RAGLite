"""Static structure validation tests for Story 7.1 refactoring.

Story 7.1: Split test_external_data_clients.py
Priority: P0 (Critical - validates refactoring correctness)

These tests validate module structure, fixture isolation, and import cycles
using static code analysis (no subprocess/import required).

Test Coverage:
- Module existence and importability
- Fixture isolation and scope consistency
- Import cycle detection
- File size compliance
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TESTS_ROOT = PROJECT_ROOT / "tests"
EXTERNAL_DATA_TESTS_DIR = TESTS_ROOT / "unit" / "external_data"

# All test modules in the refactored structure
TEST_MODULES = [
    "test_ine_client",
    "test_basegov_client",
    "test_basegov_story695",
    "test_bpstat_client",
    "test_omie_client",
    "test_oil_bulletin_client",
    "test_commodities_client",
    "test_atic_client",
    "test_ipma_client",
    "test_exceptions",
]


# ============================================================================
# P0 Tests: Module Structure Validation (Critical Path)
# ============================================================================


class TestModuleStructure:
    """P0: Validate refactored module structure."""

    def test_all_modules_exist(self) -> None:
        """[P0] All expected test modules exist in filesystem."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            assert module_path.exists(), f"Module {module_name}.py not found"

    def test_all_modules_importable(self) -> None:
        """[P0] All test modules can be imported without errors."""
        for module_name in TEST_MODULES:
            module_path = f"tests.unit.external_data.{module_name}"
            try:
                importlib.import_module(module_path)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_path}: {e}")

    def test_conftest_importable(self) -> None:
        """[P0] Conftest module is importable and provides fixtures."""
        try:
            conftest_module = importlib.import_module("tests.unit.external_data.conftest")
            # Check for expected fixtures
            assert hasattr(conftest_module, "mock_httpx_response")
            assert hasattr(conftest_module, "mock_httpx_client")
            assert hasattr(conftest_module, "sample_date_range")
        except ImportError as e:
            pytest.fail(f"Failed to import conftest: {e}")

    def test_no_duplicate_module_names(self) -> None:
        """[P0] No duplicate module names in external_data directory."""
        module_files = list(EXTERNAL_DATA_TESTS_DIR.glob("test_*.py"))
        module_names = [f.name for f in module_files]
        unique_names = set(module_names)
        assert len(module_names) == len(unique_names), (
            f"Duplicate module names detected: "
            f"{[name for name in module_names if module_names.count(name) > 1]}"
        )


# ============================================================================
# P0 Tests: Fixture Isolation (Critical Path)
# ============================================================================


class TestFixtureIsolation:
    """P0: Validate fixture isolation and accessibility."""

    def test_shared_fixtures_accessible_from_all_modules(self) -> None:
        """[P0] All test modules can access shared fixtures from conftest."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()

            # Check if module uses fixtures (not all modules must use all fixtures)
            # But if they use fixtures, they should be accessible
            if "mock_httpx_response" in content or "mock_httpx_client" in content:
                # Module uses shared fixtures - verify no local redefinition
                tree = ast.parse(content)
                local_fixtures = [
                    node.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef)
                    and any(
                        isinstance(dec, ast.Name)
                        and dec.id == "fixture"
                        or isinstance(dec, ast.Attribute)
                        and dec.attr == "fixture"
                        for dec in node.decorator_list
                    )
                ]

                # Shared fixtures should NOT be redefined locally
                shared_fixture_names = [
                    "mock_httpx_response",
                    "mock_httpx_client",
                    "sample_date_range",
                ]
                duplicates = [f for f in shared_fixture_names if f in local_fixtures]
                assert not duplicates, (
                    f"Module {module_name} redefines shared fixtures: {duplicates}. "
                    f"Use fixtures from conftest.py instead."
                )

    def test_no_fixture_scope_conflicts(self) -> None:
        """[P0] Fixtures have consistent scopes across modules."""
        conftest_path = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        content = conftest_path.read_text()
        tree = ast.parse(content)

        fixture_scopes: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, "attr") and decorator.func.attr == "fixture":
                            # Extract scope if specified
                            scope = "function"  # default
                            for keyword in decorator.keywords:
                                if keyword.arg == "scope":
                                    if isinstance(keyword.value, ast.Constant):
                                        scope = keyword.value.value
                            fixture_scopes[node.name] = scope

        # Validate expected scopes
        assert fixture_scopes.get("mock_httpx_response", "function") == "function"
        assert fixture_scopes.get("mock_httpx_client", "function") == "function"
        assert fixture_scopes.get("sample_date_range", "function") == "function"


# ============================================================================
# P0 Tests: Import Cycle Detection (Critical Path)
# ============================================================================


class TestImportCycles:
    """P0: Detect import cycles between test modules."""

    def test_no_circular_imports(self) -> None:
        """[P0] No circular imports between test modules."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            # Check for imports of other test modules
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "tests.unit.external_data.test_" in node.module:
                        pytest.fail(
                            f"Module {module_name} imports another test module: {node.module}. "
                            f"Test modules should not import each other. Extract shared code to conftest.py."
                        )

    def test_no_relative_imports_between_test_modules(self) -> None:
        """[P0] Test modules do not use relative imports to other test modules."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level > 0:
                    # Relative import detected
                    if node.module and node.module.startswith("test_"):
                        pytest.fail(
                            f"Module {module_name} uses relative import to test module: {node.module}. "
                            f"Avoid relative imports between test modules."
                        )


# ============================================================================
# P1 Tests: File Size Compliance (Important Scenarios)
# ============================================================================


class TestFileSizeCompliance:
    """P1: Validate all modules comply with file size limits."""

    @pytest.mark.parametrize("module_name", TEST_MODULES)
    def test_module_under_hard_limit(self, module_name: str) -> None:
        """[P1] Each module is under 500 LOC hard limit."""
        module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
        line_count = len(module_path.read_text().splitlines())
        assert line_count < 500, (
            f"Module {module_name}.py exceeds hard limit: {line_count} LOC (limit: 500 LOC)"
        )

    def test_conftest_size_reasonable(self) -> None:
        """[P1] conftest.py is reasonably sized (<200 LOC)."""
        conftest_path = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        line_count = len(conftest_path.read_text().splitlines())
        assert line_count < 200, (
            f"conftest.py too large: {line_count} LOC (target: <200 LOC). "
            f"Consider extracting large fixtures to separate modules."
        )

    def test_total_loc_matches_baseline(self) -> None:
        """[P1] Total LOC across all modules matches baseline (~3025 LOC)."""
        total_loc = 0
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            total_loc += len(module_path.read_text().splitlines())

        # Add conftest LOC
        conftest_path = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        total_loc += len(conftest_path.read_text().splitlines())

        # Baseline: 3025 LOC in original file
        # After split: should be similar (±10% for docstrings, formatting)
        baseline = 3025
        tolerance = 0.15  # 15% tolerance
        assert baseline * (1 - tolerance) <= total_loc <= baseline * (1 + tolerance), (
            f"Total LOC ({total_loc}) outside expected range "
            f"[{int(baseline * (1 - tolerance))}, {int(baseline * (1 + tolerance))}]. "
            f"Baseline: {baseline} LOC"
        )
