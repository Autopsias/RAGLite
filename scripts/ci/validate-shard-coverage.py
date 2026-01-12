#!/usr/bin/env python3
"""Validate that test shards cover all integration tests exactly once.

This script ensures that the shard configuration doesn't miss tests
or run the same test in multiple shards.
"""

import argparse
import subprocess
import sys

# Shard definitions - must match ci.yml matrix configuration
# Uses directory-based sharding (not marker-based) for reliable test distribution
SHARDS = {
    "postgresql": {
        "pytest_args": [
            "tests/integration/forecasting/",
            "tests/integration/model_selection/",
            "tests/integration/external_data/",
            "tests/integration/insights/",
            "-m",
            "not health_check",
            "--collect-only",
            "-qq",
        ],
        "description": "PostgreSQL-focused tests (forecasting, model_selection, external_data, insights)",
    },
    "other": {
        "pytest_args": [
            "tests/integration/",
            "--ignore=tests/integration/forecasting/",
            "--ignore=tests/integration/model_selection/",
            "--ignore=tests/integration/external_data/",
            "--ignore=tests/integration/insights/",
            "-m",
            "not health_check",
            "--collect-only",
            "-qq",
        ],
        "description": "Remaining integration tests (ingestion, retrieval, MCP, etc.)",
    },
}


def collect_tests(pytest_args: list[str]) -> set[str]:
    """Run pytest --collect-only and return set of test IDs."""
    cmd = ["pytest"] + pytest_args
    result = subprocess.run(cmd, capture_output=True, text=True)

    tests = set()
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        # Test IDs look like: tests/integration/path/test_file.py::test_function
        if line.startswith("tests/") and "::" in line:
            tests.add(line)

    return tests


def validate_shards(verbose: bool = False) -> tuple[bool, dict]:
    """Validate that shards cover all tests exactly once.

    Returns:
        (success, stats) tuple
    """
    # Collect tests for each shard
    shard_tests = {}
    for name, config in SHARDS.items():
        tests = collect_tests(config["pytest_args"])
        shard_tests[name] = tests
        if verbose:
            print(f"Shard '{name}': {len(tests)} tests")

    # Collect ALL integration tests
    all_tests = collect_tests(
        ["tests/integration/", "-m", "not health_check", "--collect-only", "-qq"]
    )
    if verbose:
        print(f"\nTotal integration tests: {len(all_tests)}")

    # Check for coverage
    covered = set()
    for tests in shard_tests.values():
        covered.update(tests)

    missing = all_tests - covered

    # Check for duplicates
    duplicates = set()
    seen = set()
    for _name, tests in shard_tests.items():
        for test in tests:
            if test in seen:
                duplicates.add(test)
            seen.add(test)

    # Report findings
    success = True
    stats = {
        "total": len(all_tests),
        "covered": len(covered),
        "missing": len(missing),
        "duplicates": len(duplicates),
        "shards": {name: len(tests) for name, tests in shard_tests.items()},
    }

    if missing:
        success = False
        print(f"\n❌ MISSING: {len(missing)} tests not in any shard:")
        if verbose:
            for test in sorted(missing)[:20]:
                print(f"   - {test}")
            if len(missing) > 20:
                print(f"   ... and {len(missing) - 20} more")

    if duplicates:
        success = False
        print(f"\n❌ DUPLICATES: {len(duplicates)} tests in multiple shards:")
        if verbose:
            for test in sorted(duplicates)[:10]:
                print(f"   - {test}")

    if success:
        print("\n✅ Shard validation PASSED")
        print(f"   Total tests: {len(all_tests)}")
        print(f"   Shards: {len(SHARDS)}")
        for name, count in stats["shards"].items():
            print(f"     - {name}: {count} tests")

    return success, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate test shard coverage")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed test lists",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output stats as JSON",
    )
    args = parser.parse_args()

    success, stats = validate_shards(verbose=args.verbose)

    if args.json:
        import json

        print(json.dumps(stats, indent=2))

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
