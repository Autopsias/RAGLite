#!/usr/bin/env python3
"""Check file size limits - prevent large file proliferation.

Validates Python file line counts against thresholds and manages
grandfathered exceptions for existing large files.

Research-backed thresholds (AI comprehension optimization):
- Ideal: 100-250 LOC (~1,000-2,500 tokens)
- Warning: 400 LOC (~4,000 tokens)
- Hard Limit: 500 LOC (~5,000 tokens)

Usage:
    # In CI/CD (GitHub Actions)
    python scripts/check_file_sizes.py

    # Generate baseline for current violations
    python scripts/check_file_sizes.py --generate-baseline

    # Local check with verbose output
    python scripts/check_file_sizes.py --verbose

    # Strict mode (fail on ALL violations, ignore exceptions)
    python scripts/check_file_sizes.py --strict

Exit codes:
    0 - All checks passed
    1 - Violations found or error
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Research-backed thresholds
WARNING_THRESHOLD = 400
HARD_LIMIT = 500

# Directory configuration
# Production code: strict enforcement (CI fails on new violations)
# Test code: soft enforcement (warnings only, no CI failure)
DIRECTORIES: dict[str, dict[str, Any]] = {
    "raglite/": {"mode": "strict", "fail_on_new": True},
    "tests/": {"mode": "warn", "fail_on_new": False},
}

EXCLUDE_PATTERNS = ["__pycache__", ".venv", "venv", "build", "dist", ".git"]


def count_lines(file_path: Path) -> int:
    """Count total lines in a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        Total line count
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            return len(f.readlines())
    except Exception:
        return 0


def load_exceptions(exceptions_file: Path) -> dict[str, Any]:
    """Load grandfathered exceptions from JSON file.

    Args:
        exceptions_file: Path to .file-size-exceptions

    Returns:
        Dictionary with version, baseline_date, and exceptions
    """
    if not exceptions_file.exists():
        return {"version": 1, "exceptions": {}, "baseline_date": None}

    with open(exceptions_file) as f:
        return json.load(f)


def scan_files(directories: dict[str, dict[str, Any]], base_path: Path) -> list[dict[str, Any]]:
    """Scan directories for Python files and their line counts.

    Args:
        directories: Dictionary of directory paths and their config
        base_path: Project root path

    Returns:
        List of file info dicts sorted by line count descending
    """
    results = []

    for directory, config in directories.items():
        dir_path = base_path / directory
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            # Skip excluded patterns
            if any(pattern in str(py_file) for pattern in EXCLUDE_PATTERNS):
                continue

            line_count = count_lines(py_file)
            relative_path = str(py_file.relative_to(base_path))

            results.append(
                {
                    "path": relative_path,
                    "lines": line_count,
                    "directory": directory,
                    "mode": config["mode"],
                    "fail_on_new": config["fail_on_new"],
                    "exceeds_warning": line_count > WARNING_THRESHOLD,
                    "exceeds_limit": line_count > HARD_LIMIT,
                }
            )

    return sorted(results, key=lambda x: x["lines"], reverse=True)


def check_file_sizes(
    files: list[dict[str, Any]],
    exceptions: dict[str, Any],
    check_new_only: bool = True,
) -> tuple[bool, dict[str, Any]]:
    """Check file sizes against limits and exceptions.

    Args:
        files: List of file info dicts from scan_files
        exceptions: Loaded exceptions from .file-size-exceptions
        check_new_only: If True, only fail on NEW violations (not grandfathered)

    Returns:
        Tuple of (passed, results_dict)
    """
    violations = []
    warnings = []
    new_violations = []
    exception_paths = set(exceptions.get("exceptions", {}).keys())

    for file_info in files:
        path = file_info["path"]

        if file_info["exceeds_limit"]:
            if path in exception_paths:
                # Grandfathered - track but don't fail
                violations.append({**file_info, "grandfathered": True})
            else:
                # New violation
                if file_info["fail_on_new"]:
                    new_violations.append(file_info)
                violations.append({**file_info, "grandfathered": False})
        elif file_info["exceeds_warning"]:
            warnings.append(file_info)

    # Pass if no NEW violations in strict directories
    passed = len(new_violations) == 0 if check_new_only else len(violations) == 0

    return passed, {
        "violations": violations,
        "new_violations": new_violations,
        "warnings": warnings,
        "total_files_checked": len(files),
        "passed": passed,
    }


def generate_baseline(files: list[dict[str, Any]], output_path: Path) -> None:
    """Generate baseline exceptions file from current violations.

    Args:
        files: List of file info dicts from scan_files
        output_path: Path to write .file-size-exceptions
    """
    exceptions: dict[str, Any] = {
        "version": 1,
        "baseline_date": datetime.now().isoformat(),
        "description": "Grandfathered file size violations - reduce gradually",
        "thresholds": {
            "warning": WARNING_THRESHOLD,
            "hard_limit": HARD_LIMIT,
        },
        "exceptions": {},
    }

    for file_info in files:
        if file_info["exceeds_limit"]:
            exceptions["exceptions"][file_info["path"]] = {
                "lines": file_info["lines"],
                "reason": "Baseline: existing at time of enforcement",
                "target_lines": HARD_LIMIT,
                "directory": file_info["directory"],
            }

    with open(output_path, "w") as f:
        json.dump(exceptions, f, indent=2)

    print(f"Generated baseline with {len(exceptions['exceptions'])} exceptions")
    print(f"Written to: {output_path}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check Python file size limits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--generate-baseline",
        action="store_true",
        help="Generate baseline exceptions file from current violations",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output including all files",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on ANY violation (ignore exceptions)",
    )
    parser.add_argument(
        "--exceptions-file",
        type=Path,
        default=Path(".file-size-exceptions"),
        help="Path to exceptions file (default: .file-size-exceptions)",
    )

    args = parser.parse_args()
    base_path = Path.cwd()

    print("=" * 80)
    print("FILE SIZE CHECK")
    print("=" * 80)
    print(f"Warning threshold: {WARNING_THRESHOLD} LOC")
    print(f"Hard limit: {HARD_LIMIT} LOC")
    print()

    # Scan files
    files = scan_files(DIRECTORIES, base_path)
    strict_files = [f for f in files if f["fail_on_new"]]
    warn_files = [f for f in files if not f["fail_on_new"]]

    print(f"Scanned {len(files)} Python files")
    print(f"  - Production (strict): {len(strict_files)} files")
    print(f"  - Tests (warn only): {len(warn_files)} files")
    print()

    # Generate baseline mode
    if args.generate_baseline:
        generate_baseline(files, args.exceptions_file)
        return

    # Load exceptions
    exceptions = load_exceptions(args.exceptions_file)
    exception_count = len(exceptions.get("exceptions", {}))
    print(f"Loaded {exception_count} grandfathered exceptions")
    print()

    # Check sizes
    passed, results = check_file_sizes(files, exceptions, check_new_only=not args.strict)

    # Print new violations (always show these)
    if results["new_violations"]:
        print("NEW VIOLATIONS (must fix):")
        print("-" * 80)
        for v in results["new_violations"]:
            print(f"  {v['path']}: {v['lines']} LOC (limit: {HARD_LIMIT})")
        print()

    # Print grandfathered violations (verbose only)
    if args.verbose:
        grandfathered = [v for v in results["violations"] if v.get("grandfathered")]
        if grandfathered:
            print(f"GRANDFATHERED VIOLATIONS ({len(grandfathered)} files):")
            print("-" * 80)
            for v in sorted(grandfathered, key=lambda x: x["lines"], reverse=True):
                print(f"  {v['path']}: {v['lines']} LOC")
            print()

    # Print warnings (verbose only)
    if args.verbose and results["warnings"]:
        print(f"WARNINGS ({len(results['warnings'])} files near limit):")
        print("-" * 80)
        for w in sorted(results["warnings"], key=lambda x: x["lines"], reverse=True):
            print(f"  {w['path']}: {w['lines']} LOC")
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files checked: {results['total_files_checked']}")
    print(f"New violations (strict): {len(results['new_violations'])}")
    grandfathered_count = len([v for v in results["violations"] if v.get("grandfathered")])
    print(f"Grandfathered violations: {grandfathered_count}")
    print(f"Warnings (near limit): {len(results['warnings'])}")
    print()

    if passed:
        print("PASSED - No new file size violations")
        sys.exit(0)
    else:
        print("FAILED - New file size violations detected")
        print("\nTo fix:")
        print("  1. Refactor large files into smaller modules (<500 LOC each)")
        print("  2. Extract related functionality into separate files")
        print("  3. See docs/analysis/file-size-refactoring-briefing.md for guidance")
        print("  4. If truly necessary, add to .file-size-exceptions with justification")
        sys.exit(1)


if __name__ == "__main__":
    main()
