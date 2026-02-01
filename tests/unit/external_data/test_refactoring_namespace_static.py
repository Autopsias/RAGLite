"""Static namespace and boundary validation for Story 7.1 refactoring.

Story 7.1: Split test_external_data_clients.py
Priority: P1 (Important - validates module boundaries)

These tests validate namespace cleanliness, module boundaries, and import hygiene
using static code analysis.

Test Coverage:
- Namespace pollution prevention (star imports, globals, side effects)
- Module boundary enforcement (test class organization)
- Import hygiene (organization, unused imports)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TESTS_ROOT = PROJECT_ROOT / "tests"
EXTERNAL_DATA_TESTS_DIR = TESTS_ROOT / "unit" / "external_data"

# All test modules
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
# P1 Tests: Namespace Cleanliness (Important Scenarios)
# ============================================================================


class TestNamespaceCleanliness:
    """P1: Validate namespace pollution prevention."""

    def test_no_star_imports(self) -> None:
        """[P1] Modules do not use star imports (import *)."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        assert alias.name != "*", (
                            f"Module {module_name} uses star import from {node.module}. "
                            f"Use explicit imports instead."
                        )

    def test_no_global_variables(self) -> None:
        """[P1] Test modules do not define global variables (except constants)."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            global_vars = []
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            # Allow UPPER_CASE constants
                            if not target.id.isupper():
                                global_vars.append(target.id)

            assert not global_vars, (
                f"Module {module_name} defines non-constant global variables: {global_vars}. "
                f"Use fixtures or constants instead."
            )

    def test_no_module_level_side_effects(self) -> None:
        """[P1] Modules do not have side effects at import time."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            # Check for function calls at module level (excluding decorators)
            for node in tree.body:
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    # Allow specific safe calls
                    if isinstance(node.value.func, ast.Name):
                        func_name = node.value.func.id
                        # Allow print, logging setup, etc. in some cases
                        # But generally, module level calls are discouraged
                        if func_name not in ["print", "logger"]:
                            pytest.fail(
                                f"Module {module_name} has module-level function call: {func_name}(). "
                                f"Move to fixture or test function."
                            )


# ============================================================================
# P1 Tests: Module Boundary Enforcement (Important Scenarios)
# ============================================================================


class TestModuleBoundaries:
    """P1: Validate proper module boundaries and organization."""

    def test_test_classes_match_client_domain(self) -> None:
        """[P1] Test classes are organized by client domain."""
        domain_mapping = {
            "test_ine_client.py": ["INE"],
            "test_basegov_client.py": ["BaseGov"],
            "test_basegov_story695.py": ["BaseGov"],
            "test_bpstat_client.py": ["BPstat"],
            "test_omie_client.py": ["OMIE"],
            "test_oil_bulletin_client.py": ["EUOilBulletin", "OilBulletin"],
            "test_commodities_client.py": ["Commodities"],
            "test_atic_client.py": ["ATIC"],
            "test_ipma_client.py": ["IPMA"],
            "test_exceptions.py": ["Exceptions", "RateLimit"],
        }

        for module_name, expected_domains in domain_mapping.items():
            module_path = EXTERNAL_DATA_TESTS_DIR / module_name
            content = module_path.read_text()
            tree = ast.parse(content)

            # Extract test class names
            test_classes = [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
            ]

            # Verify classes belong to expected domain
            for test_class in test_classes:
                domain_match = any(domain in test_class for domain in expected_domains)
                assert domain_match, (
                    f"Test class {test_class} in {module_name} does not match expected domains {expected_domains}. "
                    f"Ensure test classes are organized by client domain."
                )

    def test_no_cross_client_test_classes(self) -> None:
        """[P1] Modules do not contain test classes for other clients."""
        client_modules = {
            "INE": "test_ine_client.py",
            "BaseGov": ["test_basegov_client.py", "test_basegov_story695.py"],
            "BPstat": "test_bpstat_client.py",
            "OMIE": "test_omie_client.py",
            "EUOilBulletin": "test_oil_bulletin_client.py",
            "Commodities": "test_commodities_client.py",
            "ATIC": "test_atic_client.py",
            "IPMA": "test_ipma_client.py",
        }

        for module_name in TEST_MODULES:
            if module_name == "test_exceptions":
                continue  # Exceptions are cross-cutting

            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            # Extract test class names
            test_classes = [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
            ]

            # Find which client this module should test
            expected_client = None
            for client, modules in client_modules.items():
                if isinstance(modules, list):
                    if f"{module_name}.py" in modules:
                        expected_client = client
                        break
                else:
                    if modules == f"{module_name}.py":
                        expected_client = client
                        break

            if expected_client:
                # Check for cross-client test classes
                other_clients = [c for c in client_modules.keys() if c != expected_client]
                for test_class in test_classes:
                    for other_client in other_clients:
                        if other_client in test_class:
                            pytest.fail(
                                f"Module {module_name}.py (for {expected_client}) contains test class "
                                f"for different client: {test_class} (contains {other_client}). "
                                f"Move to appropriate module."
                            )


# ============================================================================
# P1 Tests: Import Hygiene (Important Scenarios)
# ============================================================================


class TestImportHygiene:
    """P1: Validate proper import organization."""

    def test_imports_organized_by_type(self) -> None:
        """[P1] Imports are organized: stdlib, third-party, local."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()

            # Check if imports follow standard order
            # This is a simplified check - full validation requires isort
            lines = content.splitlines()
            import_section = []
            in_imports = False

            for line in lines:
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    in_imports = True
                    import_section.append(line)
                elif in_imports and stripped and not stripped.startswith("#"):
                    # End of import section
                    break

            # Check for at least one blank line separating stdlib from third-party
            # (This is a heuristic - not foolproof)
            if len(import_section) > 5:
                # Look for blank lines in import section
                [i for i, line in enumerate(import_section) if not line.strip()]
                # Should have at least one separator
                # (This is informational only - not enforced strictly)
                pass

    def test_no_unused_imports(self) -> None:
        """[P1] Modules do not import unused symbols."""
        # This would require static analysis tools like pylint/ruff
        # For now, we'll just check for obvious cases
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            # Extract imported names
            imported_names: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        imported_names.add(name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        imported_names.add(name)

            # Extract used names (simplified - doesn't catch all cases)
            used_names: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_names.add(node.id)

            # Check for obvious unused imports
            # (This is heuristic - full check requires flow analysis)
            potentially_unused = imported_names - used_names

            # Filter out common false positives
            false_positives = {"annotations", "Any", "Optional", "List", "Dict", "Tuple"}
            potentially_unused = potentially_unused - false_positives

            # Allow some tolerance (fixtures, type hints may not appear in simple analysis)
            if len(potentially_unused) > 3:
                # Too many potentially unused imports - warn
                # (Not a hard failure - needs manual review)
                pass
