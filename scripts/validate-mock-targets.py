#!/usr/bin/env python3
"""Validate mock patch targets exist in the codebase.

This script prevents stale mock targets after refactoring by:
1. Scanning test files for patch() calls
2. Extracting module.attribute paths
3. Verifying the targets actually exist

Root cause fix: Story 8 strategic analysis identified 45+ test failures
caused by mock targets pointing to moved/renamed modules after refactoring.

Usage:
    python scripts/validate-mock-targets.py [--verbose] [--fix-suggestions]
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

# Known patterns that are intentionally dynamic or mocked
SKIP_PATTERNS = [
    # External libraries - we can't validate these
    "unittest.mock",
    "asyncio.",
    "builtins.",
    # Test-only mocks that don't need validation
    "tests.",
    # Standard library imports within our modules (valid patch patterns)
    ".asyncio.",  # e.g., raglite.external_data.refresh.asyncio.sleep
    ".time.",  # e.g., raglite.shared.clients.time.sleep
]

# Known valid targets that may appear dynamic
KNOWN_VALID_TARGETS = {
    # Dynamically loaded script modules (importlib at runtime)
    "init_qdrant.create_collection",
    "init_qdrant.settings",
    "init_qdrant.logger",
    "init_qdrant.sys.exit",
    "init_qdrant.initialize_qdrant_collection",
    "init_qdrant.get_active_embedding_dimension",
    # Root-level modules (not in raglite/ package)
    "strands_poc.mock_multi_index_search",
    "strands_poc.Agent",
    "strands_poc.MistralModel",
    "strands_poc.create_orchestrator",
    # Standard library - patch in the module where it's imported
    "pathlib.Path.exists",  # Should use patch.object(Path, "exists") instead
}


class MockTargetVisitor(ast.NodeVisitor):
    """AST visitor to extract patch() call targets."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.targets: list[tuple[str, int]] = []  # (target, line_number)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to find patch() invocations."""
        # Check for patch("module.path")
        if self._is_patch_call(node) and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                self.targets.append((first_arg.value, node.lineno))

        # Check for patch.object(module, "attr")
        if self._is_patch_object_call(node) and len(node.args) >= 2:
            # patch.object targets are harder to validate statically
            # Skip for now - focus on string-based patch() calls
            pass

        self.generic_visit(node)

    def _is_patch_call(self, node: ast.Call) -> bool:
        """Check if this is a patch() or mock.patch() call."""
        if isinstance(node.func, ast.Name):
            return node.func.id == "patch"
        if isinstance(node.func, ast.Attribute):
            return node.func.attr == "patch"
        return False

    def _is_patch_object_call(self, node: ast.Call) -> bool:
        """Check if this is a patch.object() call."""
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "object":
                if isinstance(node.func.value, ast.Attribute):
                    return node.func.value.attr == "patch"
                if isinstance(node.func.value, ast.Name):
                    return node.func.value.id == "patch"
        return False


def should_skip_target(target: str) -> bool:
    """Check if target should be skipped (external libs, etc.)."""
    for pattern in SKIP_PATTERNS:
        # Patterns starting with . are checked anywhere in target
        # Other patterns are checked at the start
        if pattern.startswith("."):
            if pattern in target:
                return True
        elif target.startswith(pattern):
            return True
    return target in KNOWN_VALID_TARGETS


def validate_target(target: str) -> tuple[bool, str]:
    """Validate that a mock target exists.

    Handles both module attributes (raglite.module.func) and
    nested object attributes (raglite.module.obj.attr).

    Returns:
        (is_valid, error_message)
    """
    if should_skip_target(target):
        return True, ""

    parts = target.split(".")
    if len(parts) < 2:
        return False, f"Invalid target format: {target}"

    # Try progressively shorter module paths to find the importable module
    # e.g., for "raglite.shared.config.settings.mistral_api_key"
    # try: raglite.shared.config.settings.mistral_api_key (fail)
    #      raglite.shared.config.settings (fail)
    #      raglite.shared.config (success!) -> then check settings.mistral_api_key
    for i in range(len(parts) - 1, 0, -1):
        module_path = ".".join(parts[:i])
        attr_chain = parts[i:]

        try:
            module = importlib.import_module(module_path)

            # Walk the attribute chain
            obj = module
            for attr in attr_chain:
                if hasattr(obj, attr):
                    obj = getattr(obj, attr)
                else:
                    # Keep trying shorter module paths
                    break
            else:
                # Successfully walked entire chain
                return True, ""

        except ModuleNotFoundError:
            continue
        except ImportError as e:
            # Module exists but has import errors - might be circular imports
            # Be lenient here, actual test run will catch real issues
            return True, f"Warning: Import error (may be OK): {e}"

    # No valid module found
    module_path = ".".join(parts[:-1])
    return False, f"Module not found: {module_path}"


def extract_mock_targets(filepath: Path) -> list[tuple[str, int]]:
    """Extract all mock patch targets from a test file."""
    try:
        source = filepath.read_text()
        tree = ast.parse(source)
        visitor = MockTargetVisitor(filepath)
        visitor.visit(tree)
        return visitor.targets
    except SyntaxError:
        # File has syntax errors - let other hooks catch this
        return []


def suggest_fix(target: str) -> str | None:
    """Suggest a fix for common stale target patterns."""
    suggestions = {
        # Story 8.2 refactoring: async -> sync
        "raglite.forecasting.hybrid.ensemble.fetch_historical_data": (
            "raglite.forecasting.model_selection_job.fetch_historical_data"
        ),
        # Story 8.3 refactoring: module -> package
        "raglite.ingestion.document_ingestion.ingest_pdf": (
            "raglite.ingestion.document_ingestion.core.ingest_pdf"
        ),
        "raglite.ingestion.document_ingestion.process_excel": (
            "raglite.ingestion.document_ingestion.excel_processing.process_excel"
        ),
        # Common hybrid -> ensemble moves
        "raglite.forecasting.hybrid.generate_ensemble_forecast": (
            "raglite.forecasting.ensemble.generate_ensemble_forecast"
        ),
    }

    # Check direct match
    if target in suggestions:
        return suggestions[target]

    # Check pattern-based suggestions
    if "hybrid.ensemble.fetch_historical_data" in target:
        return target.replace(
            "hybrid.ensemble.fetch_historical_data",
            "model_selection_job.fetch_historical_data",
        )

    if "document_ingestion.ingest_pdf" in target and ".core." not in target:
        return target.replace("document_ingestion.ingest_pdf", "document_ingestion.core.ingest_pdf")

    return None


def main() -> int:
    """Main entry point."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    show_suggestions = "--fix-suggestions" in sys.argv

    tests_dir = Path("tests")
    if not tests_dir.exists():
        print("No tests/ directory found")
        return 0

    # Find all test files
    test_files = list(tests_dir.rglob("test_*.py"))

    invalid_targets: list[tuple[Path, str, int, str]] = []
    warnings: list[tuple[Path, str, int, str]] = []
    total_targets = 0

    for filepath in test_files:
        targets = extract_mock_targets(filepath)
        total_targets += len(targets)

        for target, lineno in targets:
            is_valid, error = validate_target(target)

            if not is_valid:
                invalid_targets.append((filepath, target, lineno, error))
            elif error and verbose:
                warnings.append((filepath, target, lineno, error))

    # Report results
    if verbose:
        print(f"Scanned {len(test_files)} test files")
        print(f"Found {total_targets} mock patch targets")
        print()

    if warnings and verbose:
        print("Warnings (may be OK):")
        for filepath, target, lineno, error in warnings:
            print(f"  {filepath}:{lineno}: {target}")
            print(f"    {error}")
        print()

    if invalid_targets:
        print("Invalid mock targets found:")
        print("=" * 60)
        for filepath, target, lineno, error in invalid_targets:
            print(f"\n{filepath}:{lineno}")
            print(f"  Target: {target}")
            print(f"  Error: {error}")

            if show_suggestions:
                suggestion = suggest_fix(target)
                if suggestion:
                    print(f"  Suggested fix: {suggestion}")

        print()
        print(f"Found {len(invalid_targets)} invalid mock target(s)")
        print()
        print("How to fix:")
        print("  1. Check if the module/function was moved during refactoring")
        print("  2. Update patch() target to the new location")
        print("  3. Remember: patch where the function is USED, not where it's DEFINED")
        print()
        print("Run with --fix-suggestions for automated fix suggestions")
        return 1

    if verbose:
        print("All mock targets are valid!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
