#!/usr/bin/env python3
"""
Pytest Marker Validation Script

Validates pytest marker syntax to prevent common errors like:
- Missing quotes: @pytest.mark.priority(P0) instead of @pytest.mark.priority("P0")
- Unknown markers
- Invalid marker values

This prevents CI failures from marker syntax errors by catching them early.
"""

import ast
import re
import sys
from pathlib import Path

# Valid marker values (from pytest.ini configuration)
# None = boolean marker (no value expected)
# "any" = function marker (requires arguments, but any value is valid)
# Set = enum marker (specific string values required)
VALID_MARKERS = {
    # Custom markers from pytest.ini
    "priority": {"P0", "P1", "P2", "P3"},
    "unit": None,
    "integration": None,
    "e2e": None,
    "slow": None,
    "asyncio": None,
    # Built-in pytest markers (don't warn about these)
    "parametrize": "any",  # Built-in parameterization (requires args)
    "skip": None,  # Built-in skip marker
    "skipif": "any",  # Built-in conditional skip (requires args)
    "xfail": "any",  # Built-in expected failure (requires args)
    "reruns": "any",  # pytest-rerunfailures plugin (requires args)
    "reruns_delay": "any",  # pytest-rerunfailures plugin (requires args)
    "timeout": "any",  # pytest-timeout plugin (requires args)
    "usefixtures": "any",  # Built-in fixture marker (requires args)
    "preserve_collection": None,  # Custom fixture marker
    "manages_collection_state": None,  # Custom fixture marker
    "acceptance": None,  # Custom acceptance test marker
    "uat": None,  # User acceptance testing marker
    "validation": None,  # Validation test marker
}

# Regex pattern to detect @pytest.mark.X decorators
PYTEST_MARK_PATTERN = re.compile(r"@pytest\.mark\.(\w+)(?:\(([^)]*)\))?")


class MarkerValidator(ast.NodeVisitor):
    """AST visitor to validate pytest marker decorators."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function decorators for pytest markers."""
        self._check_decorators(node.decorator_list)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function decorators for pytest markers."""
        self._check_decorators(node.decorator_list)
        self.generic_visit(node)

    def _check_decorators(self, decorators: list[ast.expr]) -> None:
        """Validate pytest marker decorators."""
        for decorator in decorators:
            # Get source line for accurate error messages
            if hasattr(decorator, "lineno"):
                line_num = decorator.lineno
            else:
                line_num = 0

            # Check if it's a pytest.mark decorator
            if isinstance(decorator, ast.Call):
                # Handle @pytest.mark.marker_name(...)
                if self._is_pytest_mark_call(decorator):
                    marker_name = self._get_marker_name(decorator)
                    if marker_name:
                        self._validate_marker(marker_name, decorator, line_num)
            elif isinstance(decorator, ast.Attribute):
                # Handle @pytest.mark.marker_name (no args)
                if self._is_pytest_mark_attr(decorator):
                    marker_name = decorator.attr
                    self._validate_marker(marker_name, decorator, line_num)

    def _is_pytest_mark_call(self, node: ast.Call) -> bool:
        """Check if node is a pytest.mark.X() call."""
        if isinstance(node.func, ast.Attribute):
            return (
                isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "mark"
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == "pytest"
            )
        return False

    def _is_pytest_mark_attr(self, node: ast.Attribute) -> bool:
        """Check if node is a pytest.mark.X attribute."""
        return (
            node.attr == "mark" and isinstance(node.value, ast.Name) and node.value.id == "pytest"
        ) or (
            isinstance(node.value, ast.Attribute)
            and node.value.attr == "mark"
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "pytest"
        )

    def _get_marker_name(self, node: ast.Call) -> str | None:
        """Extract marker name from pytest.mark.X(...) call."""
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _validate_marker(self, marker_name: str, node: ast.expr, line_num: int) -> None:
        """Validate marker name and arguments."""
        # Check if marker is known
        if marker_name not in VALID_MARKERS and marker_name != "mark":
            self.warnings.append(
                f"{self.file_path}:{line_num}: Unknown marker '{marker_name}' "
                f"(not defined in pytest.ini)"
            )
            return

        marker_spec = VALID_MARKERS.get(marker_name)

        # For boolean markers (None), no arguments expected
        if marker_spec is None:
            if isinstance(node, ast.Call) and node.args:
                self.errors.append(
                    f"{self.file_path}:{line_num}: Marker '{marker_name}' is boolean "
                    f"(should be @{marker_name}, not @{marker_name}(...))"
                )
            return

        # For "any" markers, arguments are required but no validation
        if marker_spec == "any":
            # These markers require arguments, but we don't validate the content
            return

        # For enum markers (Set), check argument syntax and values
        if isinstance(marker_spec, set):
            if isinstance(node, ast.Call) and node.args:
                # Check if argument is a string literal
                arg = node.args[0]
                if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                    self.errors.append(
                        f"{self.file_path}:{line_num}: Marker '{marker_name}' requires "
                        f'string literal (e.g., @pytest.mark.{marker_name}("P0"))'
                    )
                    return

                # Check if value is valid
                value = arg.value
                if value not in marker_spec:
                    self.errors.append(
                        f"{self.file_path}:{line_num}: Invalid marker value '{value}' "
                        f"for '{marker_name}' (valid: {', '.join(sorted(marker_spec))})"
                    )


def validate_file(file_path: Path) -> tuple[list[str], list[str]]:
    """Validate a single Python file for pytest marker issues."""
    errors = []
    warnings = []

    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        # Parse AST
        tree = ast.parse(source, filename=str(file_path))

        # Validate markers
        validator = MarkerValidator(file_path)
        validator.visit(tree)

        errors.extend(validator.errors)
        warnings.extend(validator.warnings)

    except SyntaxError as e:
        errors.append(f"{file_path}:{e.lineno}: Syntax error: {e.msg}")
    except Exception as e:
        errors.append(f"{file_path}: Failed to parse: {e}")

    return errors, warnings


def main() -> int:
    """Main validation entry point."""
    # Find all test files
    tests_dir = Path(__file__).parent.parent / "tests"
    if not tests_dir.exists():
        print(f"ERROR: Tests directory not found: {tests_dir}")
        return 1

    test_files = list(tests_dir.rglob("test_*.py"))

    if not test_files:
        print("WARNING: No test files found")
        return 0

    print(f"Validating pytest markers in {len(test_files)} test files...")

    total_errors = []
    total_warnings = []

    for test_file in test_files:
        errors, warnings = validate_file(test_file)
        total_errors.extend(errors)
        total_warnings.extend(warnings)

    # Print results
    if total_warnings:
        print("\nWARNINGS:")
        for warning in total_warnings:
            print(f"  {warning}")

    if total_errors:
        print("\nERRORS:")
        for error in total_errors:
            print(f"  {error}")
        print(f"\nFound {len(total_errors)} marker syntax error(s)")
        return 1

    print("✓ All pytest markers validated successfully")
    if total_warnings:
        print(f"  ({len(total_warnings)} warning(s))")

    return 0


if __name__ == "__main__":
    sys.exit(main())
