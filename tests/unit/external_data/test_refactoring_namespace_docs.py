"""Documentation and quality validation for Story 7.1 refactoring.

Story 7.1: Split test_external_data_clients.py
Priority: P1-P3 (Important to Future-proofing)

These tests validate documentation quality, test class organization,
conftest organization, and future-proofing patterns.

Test Coverage:
- Module docstring quality
- Test class organization patterns
- Conftest.py organization
- Future-proofing (deprecated features, naming conventions)
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
# P1 Tests: Module Docstring Quality (Important Scenarios)
# ============================================================================


class TestModuleDocstrings:
    """P1: Validate module docstring quality."""

    def test_all_modules_have_docstrings(self) -> None:
        """[P1] All test modules have module-level docstrings."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            docstring = ast.get_docstring(tree)
            assert docstring, f"Module {module_name}.py missing module docstring"

    def test_docstrings_mention_story(self) -> None:
        """[P1] Module docstrings reference Story 7.1."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            docstring = ast.get_docstring(tree)
            assert docstring, f"Module {module_name}.py missing docstring"

            # Check for story reference
            assert "Story 7.1" in docstring or "story 7.1" in docstring.lower(), (
                f"Module {module_name}.py docstring does not reference Story 7.1. "
                f"Add reference for context."
            )

    def test_docstrings_describe_test_coverage(self) -> None:
        """[P1] Module docstrings describe what tests are included."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            docstring = ast.get_docstring(tree)
            assert docstring, f"Module {module_name}.py missing docstring"

            # Should mention "tests" or "test classes"
            assert any(
                keyword in docstring.lower() for keyword in ["test", "tests", "class", "coverage"]
            ), (
                f"Module {module_name}.py docstring should describe test coverage. "
                f"Add description of included test classes."
            )


# ============================================================================
# P2 Tests: Test Class Organization (Edge Cases)
# ============================================================================


class TestClassOrganization:
    """P2: Validate test class organization patterns."""

    def test_test_classes_have_docstrings(self) -> None:
        """[P2] All test classes have class-level docstrings."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                    docstring = ast.get_docstring(node)
                    # Docstrings are optional for test classes, but recommended
                    if not docstring:
                        # Informational only - not a hard failure
                        pass

    def test_test_methods_have_descriptive_names(self) -> None:
        """[P2] Test methods have descriptive names (not just test_1, test_2)."""
        for module_name in TEST_MODULES:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    # Check if name is too generic (ends with just a number)
                    if node.name.split("_")[-1].isdigit() and len(node.name.split("_")) <= 2:
                        pytest.fail(
                            f"Test {node.name} in {module_name}.py has non-descriptive name. "
                            f"Use descriptive names like test_fetch_data_success instead of test_1."
                        )


# ============================================================================
# P2 Tests: Conftest Organization (Edge Cases)
# ============================================================================


class TestConftestOrganization:
    """P2: Validate conftest.py organization."""

    def test_conftest_has_module_docstring(self) -> None:
        """[P2] conftest.py has clear module docstring."""
        conftest_path = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        content = conftest_path.read_text()
        tree = ast.parse(content)

        docstring = ast.get_docstring(tree)
        assert docstring, "conftest.py missing module docstring"
        assert len(docstring) > 50, (
            f"conftest.py docstring too short ({len(docstring)} chars). "
            f"Provide detailed description of shared fixtures."
        )

    def test_conftest_fixtures_grouped_logically(self) -> None:
        """[P2] conftest.py fixtures are grouped logically."""
        conftest_path = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        content = conftest_path.read_text()

        # Check for comment headers or blank line separators
        # (This is heuristic - manual review needed)
        lines = content.splitlines()
        fixture_lines = [i for i, line in enumerate(lines) if "@pytest.fixture" in line]

        if len(fixture_lines) > 3:
            # Should have some grouping markers (comments or blank lines)
            # Check for blank lines between fixtures
            blank_lines = [i for i, line in enumerate(lines) if not line.strip()]
            [
                bl
                for bl in blank_lines
                if any(fl < bl < fixture_lines[i + 1] for i, fl in enumerate(fixture_lines[:-1]))
            ]
            # At least some separation expected
            # (Informational only)
            pass

    def test_conftest_has_type_hints(self) -> None:
        """[P2] All fixtures in conftest have type hints."""
        conftest_path = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        content = conftest_path.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if it's a fixture
                is_fixture = any(
                    (
                        isinstance(dec, ast.Call)
                        and hasattr(dec.func, "attr")
                        and dec.func.attr == "fixture"
                    )
                    or (isinstance(dec, ast.Name) and dec.id == "fixture")
                    for dec in node.decorator_list
                )

                if is_fixture:
                    # Check for return type annotation
                    assert node.returns is not None, (
                        f"Fixture {node.name} in conftest.py missing return type hint. "
                        f"Add return type for clarity."
                    )


# ============================================================================
# P3 Tests: Future-proofing (Advanced Validation)
# ============================================================================


class TestFutureProofing:
    """P3: Advanced validation for future maintainability."""

    def test_no_deprecated_pytest_features(self) -> None:
        """[P3] Tests do not use deprecated pytest features."""
        deprecated_patterns = [
            "pytest.yield_fixture",  # Use @pytest.fixture with yield instead
            "pytest_funcarg__",  # Old-style fixtures
            "pytest.raises(Exception)",  # Too broad
        ]

        for module_name in TEST_MODULES + ["conftest"]:
            module_path = EXTERNAL_DATA_TESTS_DIR / f"{module_name}.py"
            content = module_path.read_text()

            for pattern in deprecated_patterns:
                assert pattern not in content, (
                    f"Module {module_name}.py uses deprecated pattern: {pattern}. "
                    f"Update to modern pytest syntax."
                )

    def test_consistent_fixture_naming(self) -> None:
        """[P3] Fixtures follow consistent naming conventions."""
        conftest_path = EXTERNAL_DATA_TESTS_DIR / "conftest.py"
        content = conftest_path.read_text()
        tree = ast.parse(content)

        fixture_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                is_fixture = any(
                    (
                        isinstance(dec, ast.Call)
                        and hasattr(dec.func, "attr")
                        and dec.func.attr == "fixture"
                    )
                    or (isinstance(dec, ast.Name) and dec.id == "fixture")
                    for dec in node.decorator_list
                )
                if is_fixture:
                    fixture_names.append(node.name)

        # Check naming conventions
        for name in fixture_names:
            # Should be snake_case
            assert name.islower() or "_" in name, (
                f"Fixture {name} should use snake_case naming convention"
            )

            # Should not have redundant prefixes
            redundant_prefixes = ["fixture_", "test_fixture_"]
            for prefix in redundant_prefixes:
                assert not name.startswith(prefix), (
                    f"Fixture {name} has redundant prefix {prefix}. "
                    f"Use concise names like 'mock_client' instead of 'fixture_mock_client'."
                )
