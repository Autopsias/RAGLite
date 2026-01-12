#!/usr/bin/env python3
"""Validate xdist_group markers on embedding-dependent tests.

This script ensures all integration tests that use the embedding model
have the @pytest.mark.xdist_group(name="embedding_model") marker.

Without this marker, tests scatter across workers and each worker loads
the 2GB Fin-E5 model independently (60s × workers = massive overhead).

Usage:
    python scripts/validate-xdist-markers.py [--fix-suggestions]

Exit codes:
    0: All markers present
    1: Missing markers found (CI should fail)
"""

import argparse
import re
import sys
from pathlib import Path

# Patterns indicating embedding model usage
EMBEDDING_PATTERNS = [
    r"get_embedding_model",
    r"session_ingested_collection",
    r"warmup_embedding_model",
    r"SentenceTransformer",
    r"from raglite\.shared\.clients import.*embedding",
]

# Patterns indicating xdist_group marker
XDIST_GROUP_PATTERN = r'xdist_group\s*\(\s*name\s*=\s*["\']embedding_model["\']\s*\)'


def find_test_files(integration_dir: Path) -> list[Path]:
    """Find all test_*.py files in integration tests."""
    return list(integration_dir.glob("**/test_*.py"))


def uses_embedding(file_path: Path) -> bool:
    """Check if file uses embedding model."""
    content = file_path.read_text()
    for pattern in EMBEDDING_PATTERNS:
        if re.search(pattern, content):
            return True
    return False


def has_xdist_marker(file_path: Path) -> bool:
    """Check if file has xdist_group(name='embedding_model') marker."""
    content = file_path.read_text()
    return bool(re.search(XDIST_GROUP_PATTERN, content))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--fix-suggestions", action="store_true", help="Show how to fix missing markers"
    )
    args = parser.parse_args()

    integration_dir = Path("tests/integration")
    if not integration_dir.exists():
        print(f"ERROR: Directory not found: {integration_dir}")
        sys.exit(1)

    test_files = find_test_files(integration_dir)
    if not test_files:
        print(f"WARNING: No test files found in {integration_dir}")
        sys.exit(0)

    missing = []
    for f in test_files:
        if uses_embedding(f) and not has_xdist_marker(f):
            missing.append(f)

    if missing:
        print(f"ERROR: {len(missing)} files use embedding but missing xdist_group marker:")
        for f in missing:
            print(f"  - {f}")

        if args.fix_suggestions:
            print("\nTo fix, add to each file's pytestmark:")
            print("  pytest.mark.xdist_group(name='embedding_model'),")
            print("\nExample:")
            print("  pytestmark = [")
            print("      pytest.mark.integration,")
            print("      pytest.mark.xdist_group(name='embedding_model'),")
            print("  ]")

        sys.exit(1)
    else:
        total = len([f for f in test_files if uses_embedding(f)])
        print(f"OK: All {total} embedding-dependent integration test files have correct markers")
        sys.exit(0)


if __name__ == "__main__":
    main()
