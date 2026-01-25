#!/usr/bin/env python3
"""Validate xdist_group markers for embedding-dependent tests.

Purpose: Ensure all tests that use the 2GB embedding model have xdist_group markers
         to prevent redundant model loads across pytest-xdist workers.

Background:
- pytest-xdist session fixtures execute once PER WORKER, not once globally
- Without xdist_group: 60s load × 4 workers = 240s wasted
- With xdist_group: 60s load × 1 worker = 60s total

Usage:
    python scripts/validate-xdist-markers.py              # Check all integration tests
    python scripts/validate-xdist-markers.py --verbose    # Show detailed analysis
    python scripts/validate-xdist-markers.py --fix        # Auto-add markers (dry-run)
"""

import argparse
import re
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Validate xdist_group markers")
    parser.add_argument("--verbose", action="store_true", help="Show detailed analysis per file")
    parser.add_argument(
        "--fix", action="store_true", help="Show suggested fixes (no file modifications)"
    )
    return parser.parse_args()


def find_embedding_dependencies(file_path: Path) -> dict[str, list[int]]:
    """Find indicators that a test file uses the embedding model.

    Returns:
        Dict mapping indicator type to list of line numbers
    """
    indicators = {
        "import_embedding_utils": [],
        "get_embedding_model": [],
        "session_ingested_collection": [],
        "warmup_embedding_model": [],
        "parallel_ingestion": [],
    }

    content = file_path.read_text()
    lines = content.split("\n")

    for i, line in enumerate(lines, start=1):
        if "from raglite.shared.embedding_utils import" in line:
            indicators["import_embedding_utils"].append(i)
        if "get_embedding_model()" in line:
            indicators["get_embedding_model"].append(i)
        if "session_ingested_collection" in line and "@pytest.fixture" not in line:
            indicators["session_ingested_collection"].append(i)
        if "warmup_embedding_model" in line:
            indicators["warmup_embedding_model"].append(i)
        if "test_parallel_ingestion" in str(file_path):
            indicators["parallel_ingestion"].append(i)

    return {k: v for k, v in indicators.items() if v}


def has_xdist_group_marker(file_path: Path) -> bool:
    """Check if file has xdist_group marker for embedding tests.

    Accepts any of the embedding-related group names:
    - embedding_model (legacy)
    - embedding_model_reads (read-only tests)
    - embedding_model_writes (tests that modify collection state)

    Handles both single-line and multi-line marker formats:
    - xdist_group(name="embedding_model_reads")
    - xdist_group(\n    name="embedding_model_writes"\n)
    """
    content = file_path.read_text()
    # Match embedding_model variants with optional whitespace/newlines
    # Handles both: xdist_group(name="...") and xdist_group(\n    name="..."\n)
    pattern = r'xdist_group\s*\(\s*name\s*=\s*["\']embedding_model(?:_reads|_writes)?["\']\s*\)'
    return bool(re.search(pattern, content))


def main():
    args = parse_args()

    integration_tests = Path("tests/integration")
    if not integration_tests.exists():
        print(f"ERROR: {integration_tests} not found")
        return 1

    test_files = list(integration_tests.rglob("test_*.py"))
    print(f"Analyzing {len(test_files)} integration test files...\n")

    missing_markers: list[Path] = []
    properly_marked: list[Path] = []

    for test_file in sorted(test_files):
        indicators = find_embedding_dependencies(test_file)

        if not indicators:
            continue

        has_marker = has_xdist_group_marker(test_file)

        if has_marker:
            properly_marked.append(test_file)
        else:
            missing_markers.append(test_file)

            if args.verbose or args.fix:
                print(f"⚠️  {test_file.relative_to(integration_tests)}")
                print("    Embedding indicators found:")
                for indicator_type, line_numbers in indicators.items():
                    print(f"      - {indicator_type}: lines {', '.join(map(str, line_numbers))}")

                if args.fix:
                    print("\n    Suggested fix:")
                    print("    Add to pytestmark at top of file (after imports):")
                    print(
                        '    pytest.mark.xdist_group(name="embedding_model_reads")  # for read-only tests'
                    )
                print()

    # Summary
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  Total test files analyzed: {len(test_files)}")
    print(f"  Files with embedding dependencies: {len(missing_markers) + len(properly_marked)}")
    print(f"  ✅ Properly marked: {len(properly_marked)}")
    print(f"  ⚠️  Missing markers: {len(missing_markers)}")
    print("=" * 70)

    if missing_markers:
        print(f"\n❌ VALIDATION FAILED: {len(missing_markers)} files need xdist_group markers")
        print("\nFiles needing markers:")
        for f in missing_markers:
            print(f"  - {f.relative_to(integration_tests)}")

        print("\nTo fix, add this to pytestmark in each file:")
        print("  pytestmark = [")
        print("      pytest.mark.integration,")
        print('      pytest.mark.xdist_group(name="embedding_model_reads"),  # For read-only tests')
        print("      # OR")
        print(
            '      pytest.mark.xdist_group(name="embedding_model_writes"),  # For tests that modify state'
        )
        print("  ]")

        return 1

    print("\n✅ All embedding-dependent tests have xdist_group markers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
