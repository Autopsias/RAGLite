#!/usr/bin/env python3
"""Validate xdist_group markers for embedding-dependent tests.

Purpose: Ensure WRITE tests that modify embedding state have xdist_group markers
         to prevent race conditions, while allowing READ-ONLY tests to parallelize.

Background (Updated 2026-01-26):
- pytest-xdist session fixtures execute once PER WORKER, not once globally
- OLD approach: All embedding tests had xdist_group(name="embedding_model_reads")
  - Problem: 180 tests running serially on 1 worker = 30+ min CI timeout
- NEW approach: Only WRITE tests need xdist_group(name="embedding_model_writes")
  - Read-only tests can parallelize safely across workers
  - CI uses 4 workers, reducing time to ~8 min
  - Model loading overhead: 5s × 4 workers = 20s (acceptable with MiniLM in CI)

Usage:
    python scripts/validate-xdist-markers.py              # Check write test markers
    python scripts/validate-xdist-markers.py --verbose    # Show detailed analysis
    python scripts/validate-xdist-markers.py --check-legacy  # Warn about legacy read markers
"""

import argparse
import re
import sys
from pathlib import Path

# Write tests that MUST have xdist_group(name="embedding_model_writes")
# These tests modify Qdrant collection state and can't run in parallel
WRITE_TEST_FILES = {
    "test_chunking_consistency.py",
    "test_mcp_async_ingestion.py",
    "test_embedding_storage.py",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Validate xdist_group markers")
    parser.add_argument("--verbose", action="store_true", help="Show detailed analysis per file")
    parser.add_argument(
        "--check-legacy",
        action="store_true",
        help="Warn about files still using legacy embedding_model_reads markers",
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


def has_xdist_group_writes_marker(file_path: Path) -> bool:
    """Check if file has xdist_group marker for write tests.

    Only embedding_model_writes is valid for write tests.
    """
    content = file_path.read_text()
    pattern = r'xdist_group\s*\(\s*name\s*=\s*["\']embedding_model_writes["\']\s*\)'
    return bool(re.search(pattern, content))


def has_legacy_reads_marker(file_path: Path) -> bool:
    """Check if file still has legacy embedding_model_reads marker.

    These should be removed as read-only tests can now parallelize.
    """
    content = file_path.read_text()
    pattern = r'xdist_group\s*\(\s*name\s*=\s*["\']embedding_model_reads["\']\s*\)'
    return bool(re.search(pattern, content))


def main():
    args = parse_args()

    integration_tests = Path("tests/integration")
    if not integration_tests.exists():
        print(f"ERROR: {integration_tests} not found")
        return 1

    test_files = list(integration_tests.rglob("test_*.py"))
    print(f"Analyzing {len(test_files)} integration test files...\n")

    # Check write tests have proper markers
    missing_write_markers: list[Path] = []
    properly_marked_writes: list[Path] = []

    for test_file in sorted(test_files):
        if test_file.name in WRITE_TEST_FILES:
            if has_xdist_group_writes_marker(test_file):
                properly_marked_writes.append(test_file)
            else:
                missing_write_markers.append(test_file)

    # Check for legacy read markers (optional)
    legacy_markers: list[Path] = []
    if args.check_legacy:
        for test_file in sorted(test_files):
            if has_legacy_reads_marker(test_file):
                legacy_markers.append(test_file)

    # Summary
    print("=" * 70)
    print("xdist_group Marker Validation (Updated 2026-01-26)")
    print("=" * 70)
    print("\nWrite Test Markers (REQUIRED for mutation tests):")
    print(f"  Total write test files: {len(WRITE_TEST_FILES)}")
    print(f"  ✅ Properly marked: {len(properly_marked_writes)}")
    print(f"  ⚠️  Missing markers: {len(missing_write_markers)}")

    if args.verbose and properly_marked_writes:
        print("\n  Files with embedding_model_writes marker:")
        for f in properly_marked_writes:
            print(f"    ✅ {f.relative_to(integration_tests)}")

    if missing_write_markers:
        print(f"\n❌ VALIDATION FAILED: {len(missing_write_markers)} write tests need markers")
        print("\nWrite test files missing xdist_group(name='embedding_model_writes'):")
        for f in missing_write_markers:
            print(f"  ❌ {f.relative_to(integration_tests)}")

        print("\nTo fix, add this to pytestmark in each file:")
        print("  pytestmark = [")
        print("      pytest.mark.integration,")
        print('      pytest.mark.xdist_group(name="embedding_model_writes"),')
        print("  ]")
        return 1

    if args.check_legacy and legacy_markers:
        print(
            f"\n⚠️  WARNING: {len(legacy_markers)} files still have legacy embedding_model_reads markers"
        )
        print("These markers are no longer needed (read-only tests can parallelize):")
        for f in legacy_markers:
            print(f"  - {f.relative_to(integration_tests)}")

    print("\n" + "=" * 70)
    print("✅ All write tests have proper xdist_group markers")
    print("\nNote: Read-only tests do NOT need xdist_group markers.")
    print("      They can parallelize safely across workers.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
