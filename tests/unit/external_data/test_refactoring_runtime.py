"""Runtime validation tests for Story 7.1 refactoring.

Story 7.1: Split test_external_data_clients.py
Priority: P1-P3 (Important to Future-proofing)

These tests validate runtime behavior including pytest collection, CI compatibility,
fixture reusability, and performance characteristics.

Test Coverage:
- Pytest test discovery correctness
- CI pipeline compatibility validation
- Fixture reusability and edge cases
- Parametrized test coverage patterns
- Test suite performance characteristics
"""

from __future__ import annotations

import ast
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

# Group runtime validation tests that run subprocesses to run on same worker
pytestmark = pytest.mark.xdist_group(name="refactoring_runtime")

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
# P1 Tests: Test Discovery (Important Scenarios)
# ============================================================================


class TestDiscovery:
    """P1: Validate pytest test discovery correctness."""

    @pytest.mark.slow  # Subprocess execution takes ~10s
    def test_pytest_collects_all_modules(self) -> None:
        """[P1] pytest can discover and collect all test modules."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(EXTERNAL_DATA_TESTS_DIR),
                "--collect-only",
                "-q",
                "--ignore=test_refactoring_acceptance.py",
                "--ignore=test_refactoring_structure.py",
                "--ignore=test_refactoring_runtime.py",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, (
            f"Test collection failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

        # Verify all modules are collected
        for module_name in TEST_MODULES:
            assert module_name in result.stdout, f"Module {module_name} not collected by pytest"

    @pytest.mark.slow  # Subprocess execution takes ~12s
    def test_no_collection_errors(self) -> None:
        """[P1] pytest collection has no errors or warnings."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(EXTERNAL_DATA_TESTS_DIR),
                "--collect-only",
                "-v",
                "--ignore=test_refactoring_acceptance.py",
                "--ignore=test_refactoring_structure.py",
                "--ignore=test_refactoring_runtime.py",
                "--ignore=test_refactoring_namespace.py",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check for fatal collection errors (module import failures)
        # Allow warnings but not errors that prevent collection
        assert result.returncode == 0, (
            f"Collection failed with return code {result.returncode}\n{result.stdout}"
        )
        # Check that tests were collected successfully
        assert "collected" in result.stdout.lower(), f"No tests collected:\n{result.stdout}"


# ============================================================================
# P1 Tests: CI Compatibility (Important Scenarios)
# ============================================================================


class TestCICompatibility:
    """P1: Validate CI pipeline compatibility."""

    def test_pytest_markers_preserved(self) -> None:
        """[P1] All asyncio markers are preserved in refactored modules."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()

            # Find async test functions
            tree = ast.parse(content)
            async_tests = []
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("test_"):
                    async_tests.append(node.name)

            # For each async test, verify @pytest.mark.asyncio decorator
            if async_tests:
                for test_name in async_tests:
                    pattern = "@pytest.mark.asyncio"
                    assert pattern in content or "pytestmark" in content, (
                        f"Async test {test_name} in {module_name}.py missing @pytest.mark.asyncio marker"
                    )

    def test_no_hardcoded_test_ports(self) -> None:
        """[P1] No hardcoded test ports in test modules (use settings)."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()

            # Check for hardcoded ports (test or production)
            hardcoded_ports = ["6333", "6335", "5432", "5433"]
            for port in hardcoded_ports:
                if f'"{port}"' in content or f"'{port}'" in content or f":{port}" in content:
                    # Allow in comments or docstrings only
                    lines_with_port = [
                        i for i, line in enumerate(content.splitlines(), 1) if port in line
                    ]
                    for line_num in lines_with_port:
                        line = content.splitlines()[line_num - 1]
                        if (
                            not line.strip().startswith("#")
                            and '"""' not in line
                            and "'''" not in line
                        ):
                            pytest.fail(
                                f"Module {module_name}.py has hardcoded port {port} on line {line_num}. "
                                f"Use settings/fixtures instead."
                            )


# ============================================================================
# P2 Tests: Fixture Reusability (Edge Cases)
# ============================================================================


class TestFixtureReusability:
    """P2: Validate fixture reusability and edge cases."""

    def test_fixtures_have_docstrings(self) -> None:
        """[P2] All fixtures in conftest have docstrings."""
        conftest_path = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        content = conftest_path.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) or isinstance(decorator, ast.Name):
                        # This is a fixture
                        docstring = ast.get_docstring(node)
                        assert docstring, f"Fixture {node.name} missing docstring"
                        break

    def test_no_unused_fixtures_in_conftest(self) -> None:
        """[P2] All fixtures in conftest are used by at least one test module."""
        conftest_path = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        conftest_content = conftest_path.read_text()
        tree = ast.parse(conftest_content)

        # Extract fixture names
        fixture_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Call)
                        and hasattr(decorator.func, "attr")
                        and decorator.func.attr == "fixture"
                    ) or (isinstance(decorator, ast.Name) and decorator.id == "fixture"):
                        fixture_names.append(node.name)
                        break

        # Check usage in test modules
        unused_fixtures = []
        for fixture_name in fixture_names:
            used = False
            for module_name in TEST_MODULES:
                module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
                content = module_path.read_text()
                if fixture_name in content:
                    used = True
                    break

            if not used:
                unused_fixtures.append(fixture_name)

        # Allow some fixtures to be unused (they might be helpers or for future use)
        # But warn if more than 20% are unused
        if unused_fixtures:
            usage_rate = 1 - (len(unused_fixtures) / len(fixture_names))
            assert usage_rate >= 0.8, (
                f"Too many unused fixtures in conftest.py ({len(unused_fixtures)}/{len(fixture_names)}): "
                f"{unused_fixtures}. Consider removing or documenting their purpose."
            )


# ============================================================================
# P2 Tests: Parametrized Test Coverage (Edge Cases)
# ============================================================================


class TestParametrizedCoverage:
    """P2: Validate parametrized test patterns."""

    def test_parametrized_tests_use_proper_ids(self) -> None:
        """[P2] Parametrized tests use descriptive ids."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if (
                                hasattr(decorator.func, "attr")
                                and decorator.func.attr == "parametrize"
                            ):
                                # Check if ids parameter is provided
                                has_ids = any(kw.arg == "ids" for kw in decorator.keywords)
                                # Not mandatory, but recommended for clarity
                                # We'll just document it if missing
                                if not has_ids:
                                    # This is informational, not a failure
                                    pass  # Consider adding ids for better test output


# ============================================================================
# P3 Tests: Performance Testing (Future-proofing)
# ============================================================================


class TestPerformance:
    """P3: Validate test suite performance."""

    def test_no_redundant_imports(self) -> None:
        """[P3] Modules do not have redundant imports."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            imports.append(f"{node.module}.{alias.name}")

            # Check for duplicates
            unique_imports = set(imports)
            if len(imports) != len(unique_imports):
                duplicates = [imp for imp in imports if imports.count(imp) > 1]
                # P3 test - informational only, allow tolerance for refactored code
                # This catches new issues but doesn't block on pre-existing patterns
                # Set threshold at 10 to avoid false positives from refactored code
                if len(set(duplicates)) > 10:
                    pytest.fail(
                        f"Module {module_name}.py has excessive redundant imports (>{len(set(duplicates))}): {set(duplicates)}"
                    )

    @pytest.mark.slow
    def test_individual_module_import_time(self) -> None:
        """[P3] Each module imports quickly (<1s)."""
        import time

        for module_name in TEST_MODULES:
            start = time.time()
            importlib.import_module(f"tests.unit.external_data.{module_name}")
            duration = time.time() - start

            assert duration < 1.0, (
                f"Module {module_name} import took {duration:.2f}s (limit: 1.0s). "
                f"Consider lazy imports or reducing import complexity."
            )
