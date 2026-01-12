#!/usr/bin/env python3
"""Validate mock coverage for get_mistral_client imports.

This script prevents CI failures caused by modules importing get_mistral_client
but not being covered by mock fixtures.

Strategic Context:
- Root cause from ci-strategy-analyst: 17+ modules import get_mistral_client
- Only 5 locations are patched in mock fixtures
- New modules like enrichment.py bypass mock coverage
- 80% CI fix rate reflects reactive patching without structural prevention

Prevention:
- Scan all raglite/ modules for get_mistral_client imports
- Parse mock fixtures to extract patched locations
- Report any unpatched import locations
- Exit with error code if gaps found (blocks commit)

Usage:
    python scripts/validate-mock-coverage.py
    python scripts/validate-mock-coverage.py --verbose
"""

import argparse
import ast
import sys
from pathlib import Path


def find_mistral_imports(project_root: Path) -> set[str]:
    """Find all modules that import get_mistral_client.

    Args:
        project_root: Root directory of the project

    Returns:
        Set of module paths like 'raglite.retrieval.search.enrichment'
    """
    raglite_dir = project_root / "raglite"
    imports = set()

    for py_file in raglite_dir.rglob("*.py"):
        # Skip __pycache__ and test files
        if "__pycache__" in str(py_file) or "test_" in py_file.name:
            continue

        try:
            with open(py_file, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))

            for node in ast.walk(tree):
                # Check for: from raglite.shared.clients import get_mistral_client
                if isinstance(node, ast.ImportFrom):
                    if node.module == "raglite.shared.clients":
                        for alias in node.names:
                            if alias.name == "get_mistral_client":
                                # Convert file path to module path
                                relative = py_file.relative_to(project_root)
                                module_path = str(relative.with_suffix("")).replace("/", ".")
                                imports.add(module_path)

        except SyntaxError:
            # Skip files with syntax errors
            continue

    return imports


def find_patched_locations(project_root: Path) -> set[str]:
    """Find all locations patched in mock fixtures.

    Args:
        project_root: Root directory of the project

    Returns:
        Set of patched module paths like 'raglite.retrieval.search.enrichment'
    """
    mock_fixtures = project_root / "tests" / "fixtures" / "mock_clients.py"
    patched = set()

    try:
        with open(mock_fixtures, encoding="utf-8") as f:
            content = f.read()

        # Parse AST to find patch() calls
        tree = ast.parse(content, filename=str(mock_fixtures))

        for node in ast.walk(tree):
            # Look for patch("raglite.module.path.get_mistral_client")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "patch":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        patch_target = node.args[0].value
                        # Extract module path (remove .get_mistral_client suffix)
                        if patch_target.endswith(".get_mistral_client"):
                            module_path = patch_target.rsplit(".", 1)[0]
                            patched.add(module_path)

    except FileNotFoundError:
        print(f"ERROR: Mock fixtures not found at {mock_fixtures}", file=sys.stderr)
        sys.exit(1)

    return patched


def main():
    parser = argparse.ArgumentParser(description="Validate mock coverage for get_mistral_client")
    parser.add_argument("--verbose", action="store_true", help="Show all imports and patches")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.resolve()

    # Find all imports
    imports = find_mistral_imports(project_root)

    # Find all patched locations
    patched = find_patched_locations(project_root)

    # Find gaps (imports not covered by patches)
    gaps = imports - patched

    if args.verbose:
        print("=" * 80)
        print(f"Modules importing get_mistral_client: {len(imports)}")
        print("=" * 80)
        for module in sorted(imports):
            print(f"  - {module}")

        print()
        print("=" * 80)
        print(f"Locations patched in mock fixtures: {len(patched)}")
        print("=" * 80)
        for module in sorted(patched):
            print(f"  - {module}")

        print()

    # Report results
    if gaps:
        print("=" * 80)
        print("ERROR: Mock coverage gaps detected!")
        print("=" * 80)
        print()
        print(f"Found {len(gaps)} module(s) importing get_mistral_client without mock coverage:")
        print()
        for module in sorted(gaps):
            print(f"  ❌ {module}.get_mistral_client")
        print()
        print("=" * 80)
        print("Fix: Add patches to tests/fixtures/mock_clients.py")
        print("=" * 80)
        print()
        print("In mock_mistral_api_globally fixture, add:")
        for module in sorted(gaps):
            print(f'        patch("{module}.get_mistral_client") as mock_{module.split(".")[-1]},')
        print()
        print("Then assign:")
        for module in sorted(gaps):
            print(f"        mock_{module.split('.')[-1]}.return_value = mock_client_instance")
        print()
        sys.exit(1)
    else:
        print("=" * 80)
        print("✅ Mock coverage validation PASSED")
        print("=" * 80)
        print(f"  - {len(imports)} module(s) import get_mistral_client")
        print(f"  - {len(patched)} location(s) patched in mock fixtures")
        print("  - 0 gaps (100% coverage)")
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
