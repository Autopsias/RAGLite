#!/usr/bin/env python3
"""
Identify Python files exceeding module size limits.

This script scans the raglite/ directory to identify files that exceed
the 1000-line hard limit, generating a prioritized report for refactoring.

Usage:
    python scripts/identify-oversized-files.py

Output:
    Prints report to stdout showing:
    - File path
    - Line count
    - Epic 3 relevance (HIGH/MEDIUM/LOW)
    - Priority for refactoring
"""

import sys
from pathlib import Path

# Module size constraints from architecture docs
WARNING_THRESHOLD = 800
HARD_LIMIT = 1000

# Epic 3 high-relevance modules (agentic orchestration dependencies)
HIGH_RELEVANCE_PATTERNS = [
    "retrieval/",  # Agentic retrieval agents
    "query_classifier",  # Query understanding for agents
    "search.py",  # Core search functionality
]

MEDIUM_RELEVANCE_PATTERNS = [
    "ingestion/",  # Document processing pipeline
    "structured/",  # SQL table search
]


def count_lines(file_path: Path) -> int:
    """Count non-empty lines in a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        Number of lines in the file
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0


def get_epic3_relevance(file_path: Path) -> str:
    """Determine Epic 3 relevance based on file path patterns.

    Args:
        file_path: Path to the Python file

    Returns:
        Relevance level: HIGH, MEDIUM, or LOW
    """
    path_str = str(file_path)

    for pattern in HIGH_RELEVANCE_PATTERNS:
        if pattern in path_str:
            return "HIGH"

    for pattern in MEDIUM_RELEVANCE_PATTERNS:
        if pattern in path_str:
            return "MEDIUM"

    return "LOW"


def scan_codebase() -> list[tuple[Path, int, str]]:
    """Scan raglite/ directory for Python files and their sizes.

    Returns:
        List of (file_path, line_count, epic3_relevance) tuples,
        sorted by line count (descending)
    """
    raglite_dir = Path(__file__).parent.parent / "raglite"

    if not raglite_dir.exists():
        print(f"Error: {raglite_dir} not found", file=sys.stderr)
        return []

    files = []
    for py_file in raglite_dir.rglob("*.py"):
        # Skip __pycache__ and test files
        if "__pycache__" in str(py_file) or "tests/" in str(py_file):
            continue

        line_count = count_lines(py_file)
        relevance = get_epic3_relevance(py_file)
        files.append((py_file, line_count, relevance))

    # Sort by line count (descending), then by relevance
    relevance_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    files.sort(key=lambda x: (-x[1], relevance_order[x[2]]))

    return files


def generate_report():
    """Generate and print the oversized files report."""
    files = scan_codebase()

    if not files:
        print("No Python files found in raglite/")
        return

    # Print header
    print("=" * 100)
    print("OVERSIZED FILES REPORT - Epic 3 Prep (Story 3.0.1)")
    print("=" * 100)
    print()
    print("Module Size Constraints:")
    print("  🎯 Target: 200-400 lines per module (optimal maintainability)")
    print(f"  ⚠️  Warning: {WARNING_THRESHOLD}+ lines (plan refactoring)")
    print(f"  ❌ Hard Limit: {HARD_LIMIT}+ lines (immediate refactor required)")
    print()
    print("=" * 100)
    print()

    # Separate files into categories
    critical_files = [(f, lc, rel) for f, lc, rel in files if lc > HARD_LIMIT]
    warning_files = [(f, lc, rel) for f, lc, rel in files if WARNING_THRESHOLD < lc <= HARD_LIMIT]

    # Print critical files (>1000 lines)
    if critical_files:
        print("❌ CRITICAL: Files Exceeding Hard Limit (>1000 lines)")
        print("-" * 100)
        print(f"{'File Path':<60} | {'Lines':>6} | {'Epic 3':>8} | {'Priority':>8}")
        print("-" * 100)

        for idx, (file_path, line_count, relevance) in enumerate(critical_files, start=1):
            relative_path = file_path.relative_to(file_path.parent.parent.parent)
            print(f"{str(relative_path):<60} | {line_count:>6} | {relevance:>8} | {idx:>8}")

        print("-" * 100)
        print(
            f"Total critical files: {len(critical_files)} "
            f"({sum(lc for _, lc, _ in critical_files):,} lines total)"
        )
        print()

    # Print warning files (800-1000 lines)
    if warning_files:
        print("⚠️  WARNING: Files Approaching Hard Limit (800-1000 lines)")
        print("-" * 100)
        print(f"{'File Path':<60} | {'Lines':>6} | {'Epic 3':>8} | {'Status':>8}")
        print("-" * 100)

        for file_path, line_count, relevance in warning_files:
            relative_path = file_path.relative_to(file_path.parent.parent.parent)
            status = "Monitor"
            print(f"{str(relative_path):<60} | {line_count:>6} | {relevance:>8} | {status:>8}")

        print("-" * 100)
        print(
            f"Total warning files: {len(warning_files)} "
            f"({sum(lc for _, lc, _ in warning_files):,} lines total)"
        )
        print()

    # Summary
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Critical files requiring refactoring: {len(critical_files)}")
    print(f"Files approaching limit (monitor): {len(warning_files)}")
    print(f"Total files scanned: {len(files)}")
    print()

    if critical_files:
        print("📋 NEXT STEPS:")
        print("  1. Review this report and prioritize by Epic 3 relevance")
        print("  2. Define refactoring strategy for each critical file")
        print("  3. Get Winston architecture approval")
        print("  4. Execute refactoring with test validation")
    else:
        print("✅ All files are within size limits!")

    print("=" * 100)


if __name__ == "__main__":
    generate_report()
