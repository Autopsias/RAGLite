#!/usr/bin/env python3
"""Check coverage diff for new code in PR (Story 4.0.1 AC3).

This script calculates coverage for files changed in a PR and fails if
new code coverage is below the threshold (default: 80%).

Usage:
    # In CI/CD (GitHub Actions)
    python scripts/check_coverage_diff.py \\
        --baseline=.coverage-baseline.json \\
        --current=.coverage.json \\
        --threshold=80

    # Local testing
    python scripts/check_coverage_diff.py \\
        --current=.coverage.json \\
        --threshold=80 \\
        --changed-files="raglite/main.py,raglite/retrieval/search.py"

Exit codes:
    0 - Coverage meets threshold
    1 - Coverage below threshold or error
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def get_changed_files() -> list[str]:
    """Get list of Python files changed in current branch vs main.

    Returns:
        List of changed file paths relative to repo root
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = result.stdout.strip().split("\n")
        # Filter for Python files only
        return [f for f in files if f.endswith(".py") and f]
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting changed files: {e}", file=sys.stderr)
        sys.exit(1)


def load_coverage_data(coverage_file: Path) -> dict[str, Any]:
    """Load coverage data from JSON file.

    Args:
        coverage_file: Path to .coverage.json file

    Returns:
        Coverage data dictionary
    """
    if not coverage_file.exists():
        print(f"❌ Coverage file not found: {coverage_file}", file=sys.stderr)
        sys.exit(1)

    with open(coverage_file) as f:
        return json.load(f)


def calculate_file_coverage(
    coverage_data: dict[str, Any],
    file_path: str,
) -> tuple[int, int, float]:
    """Calculate coverage for a specific file.

    Args:
        coverage_data: Coverage data from .coverage.json
        file_path: Relative path to file

    Returns:
        Tuple of (total_statements, covered_statements, coverage_percent)
    """
    # Coverage data stores absolute paths - need to match by suffix
    files_data = coverage_data.get("files", {})

    matching_file = None
    for abs_path in files_data.keys():
        if abs_path.endswith(file_path):
            matching_file = abs_path
            break

    if not matching_file:
        # File not in coverage data (no tests executed it)
        return (0, 0, 0.0)

    file_data = files_data[matching_file]
    summary = file_data.get("summary", {})

    total_statements = summary.get("num_statements", 0)
    covered_statements = summary.get("covered_lines", 0)

    if total_statements == 0:
        return (0, 0, 0.0)

    coverage_percent = (covered_statements / total_statements) * 100
    return (total_statements, covered_statements, coverage_percent)


def check_coverage_diff(
    current_coverage: dict[str, Any],
    changed_files: list[str],
    threshold: float,
) -> tuple[bool, dict[str, Any]]:
    """Check if changed files meet coverage threshold.

    Args:
        current_coverage: Current coverage data
        changed_files: List of changed file paths
        threshold: Minimum coverage percentage required

    Returns:
        Tuple of (passed, results_dict)
    """
    results = {
        "threshold": threshold,
        "files": [],
        "overall_new_code_coverage": 0.0,
        "passed": False,
    }

    total_statements = 0
    total_covered = 0

    for file_path in changed_files:
        # Skip test files and non-code files
        if "test_" in file_path or file_path.startswith("tests/"):
            continue

        stmts, covered, coverage_pct = calculate_file_coverage(current_coverage, file_path)

        if stmts > 0:  # Only include files with statements
            total_statements += stmts
            total_covered += covered

            results["files"].append(
                {
                    "file": file_path,
                    "statements": stmts,
                    "covered": covered,
                    "coverage": round(coverage_pct, 2),
                    "passed": coverage_pct >= threshold,
                }
            )

    # Calculate overall new code coverage
    if total_statements > 0:
        overall_coverage = (total_covered / total_statements) * 100
        results["overall_new_code_coverage"] = round(overall_coverage, 2)
        results["passed"] = overall_coverage >= threshold
    else:
        # No new code statements (only test changes, docs, etc.)
        results["overall_new_code_coverage"] = 100.0
        results["passed"] = True

    return (results["passed"], results)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check coverage diff for new code in PR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to current coverage JSON file (.coverage.json)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Path to baseline coverage JSON (optional, for future comparison)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=80.0,
        help="Minimum coverage percentage for new code (default: 80)",
    )
    parser.add_argument(
        "--changed-files",
        type=str,
        help="Comma-separated list of changed files (for local testing)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("COVERAGE DIFF CHECK (AC3)")
    print("=" * 80)
    print(f"Threshold: {args.threshold}%")
    print()

    # Get changed files
    if args.changed_files:
        changed_files = args.changed_files.split(",")
        print(f"Changed files (manual): {len(changed_files)} files")
    else:
        changed_files = get_changed_files()
        print(f"Changed files (git diff): {len(changed_files)} files")

    if not changed_files:
        print("✅ No Python files changed - coverage check passed")
        sys.exit(0)

    # Load coverage data
    current_coverage = load_coverage_data(args.current)

    # Check coverage diff
    passed, results = check_coverage_diff(current_coverage, changed_files, args.threshold)

    # Print results
    print("\nCoverage by file:")
    print("-" * 80)
    for file_result in results["files"]:
        status = "✅" if file_result["passed"] else "❌"
        print(
            f"{status} {file_result['file']}: "
            f"{file_result['coverage']:.1f}% "
            f"({file_result['covered']}/{file_result['statements']} statements)"
        )

    print()
    print("=" * 80)
    print(f"Overall new code coverage: {results['overall_new_code_coverage']:.2f}%")
    print(f"Threshold: {results['threshold']}%")
    print("=" * 80)

    if passed:
        print("✅ COVERAGE CHECK PASSED")
        sys.exit(0)
    else:
        print("❌ COVERAGE CHECK FAILED")
        print(f"\nNew code coverage ({results['overall_new_code_coverage']:.2f}%) ")
        print(f"is below threshold ({results['threshold']}%)")
        sys.exit(1)


if __name__ == "__main__":
    main()
