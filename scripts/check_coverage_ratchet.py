#!/usr/bin/env python3
"""Check coverage ratchet - prevent coverage regression (Story 4.0.1 AC4).

This script ensures overall project coverage never decreases between PRs.
It compares current coverage to baseline and fails if coverage dropped.

Usage:
    # In CI/CD (GitHub Actions)
    python scripts/check_coverage_ratchet.py \\
        --baseline=.coverage-baseline.json \\
        --current=.coverage.json

    # Local testing
    python scripts/check_coverage_ratchet.py \\
        --current=.coverage.json \\
        --baseline-percent=22.5

Exit codes:
    0 - Coverage did not decrease (ratchet passed)
    1 - Coverage decreased (ratchet failed) or error
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


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


def get_overall_coverage(coverage_data: dict[str, Any]) -> float:
    """Extract overall coverage percentage from coverage data.

    Args:
        coverage_data: Coverage data from .coverage.json

    Returns:
        Overall coverage percentage (0-100)
    """
    totals = coverage_data.get("totals", {})
    percent_covered = totals.get("percent_covered", 0.0)
    return round(percent_covered, 2)


def check_coverage_ratchet(
    current_coverage_pct: float,
    baseline_coverage_pct: float,
) -> tuple[bool, float]:
    """Check if coverage decreased (ratchet violation).

    Args:
        current_coverage_pct: Current overall coverage percentage
        baseline_coverage_pct: Baseline overall coverage percentage

    Returns:
        Tuple of (passed, difference)
    """
    diff = current_coverage_pct - baseline_coverage_pct
    passed = diff >= 0  # Coverage must not decrease

    return (passed, diff)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check coverage ratchet - prevent regression",
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
        help="Path to baseline coverage JSON from main branch",
    )
    parser.add_argument(
        "--baseline-percent",
        type=float,
        help="Baseline coverage percentage (for local testing)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("COVERAGE RATCHET CHECK (AC4)")
    print("=" * 80)
    print()

    # Load current coverage
    current_coverage_data = load_coverage_data(args.current)
    current_pct = get_overall_coverage(current_coverage_data)

    # Load baseline coverage
    if args.baseline:
        baseline_coverage_data = load_coverage_data(args.baseline)
        baseline_pct = get_overall_coverage(baseline_coverage_data)
    elif args.baseline_percent is not None:
        baseline_pct = args.baseline_percent
    else:
        print("⚠️  No baseline provided - ratchet check skipped")
        print("   Use --baseline or --baseline-percent to enable ratchet")
        sys.exit(0)

    print(f"Baseline coverage: {baseline_pct:.2f}%")
    print(f"Current coverage:  {current_pct:.2f}%")
    print()

    # Check ratchet
    passed, diff = check_coverage_ratchet(current_pct, baseline_pct)

    if diff > 0:
        print(f"✅ Coverage INCREASED by {diff:.2f} percentage points")
    elif diff == 0:
        print("✅ Coverage UNCHANGED (no regression)")
    else:
        print(f"❌ Coverage DECREASED by {abs(diff):.2f} percentage points")

    print()
    print("=" * 80)

    if passed:
        print("✅ RATCHET CHECK PASSED")
        sys.exit(0)
    else:
        print("❌ RATCHET CHECK FAILED")
        print("\nCoverage regression detected!")
        print(f"Coverage dropped from {baseline_pct:.2f}% to {current_pct:.2f}%")
        print("\nTo fix:")
        print("  1. Add tests to restore coverage to at least baseline")
        print("  2. Review which code lost test coverage")
        print("  3. Ensure all new code has ≥80% coverage (see coverage diff)")
        sys.exit(1)


if __name__ == "__main__":
    main()
