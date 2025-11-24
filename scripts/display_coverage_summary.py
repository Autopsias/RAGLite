#!/usr/bin/env python3
"""Display coverage summary from JSON file."""

import json
import sys


def main() -> None:
    """Display coverage summary from JSON file."""
    if len(sys.argv) < 2:
        print("Usage: display_coverage_summary.py <coverage.json>")
        sys.exit(1)

    coverage_file = sys.argv[1]

    with open(coverage_file) as f:
        data = json.load(f)
        total = data["totals"]
        covered = total["covered_lines"]
        statements = total["num_statements"]
        missing = statements - covered
        pct = total["percent_covered"]
        print(f"Overall Coverage: {pct:.2f}%")
        print(f"Covered Lines: {covered}/{statements}")
        print(f"Missing Lines: {missing}")


if __name__ == "__main__":
    main()
