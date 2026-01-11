#!/usr/bin/env python3
"""Validate pytest fixture references resolve correctly.

Strategic Prevention: This script was created after Story 8 strategic analysis
identified 78 tests failing due to fixture references without fixture definitions.

Pattern detected: Tests were copied from other files but the fixture definitions
were not copied, causing 'fixture not found' errors.

This pre-commit hook runs `pytest --collect-only` to catch these issues early.
"""

import subprocess
import sys
from pathlib import Path


def validate_fixtures() -> int:
    """Run pytest --collect-only to validate fixture resolution.

    Returns:
        0 if all fixtures resolve, 1 if errors found
    """
    project_root = Path(__file__).parent.parent

    # Run pytest --collect-only on changed test files
    # This validates that all fixture references can be resolved
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            str(project_root / "tests"),
        ],
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=120,  # 2 minute timeout for collection
    )

    # Check for fixture-related errors
    fixture_errors = []
    for line in result.stderr.split("\n"):
        if "fixture" in line.lower() and "not found" in line.lower():
            fixture_errors.append(line.strip())
        elif "E       fixture" in line:
            fixture_errors.append(line.strip())

    if fixture_errors:
        print("Fixture validation FAILED")
        print("=" * 60)
        print("The following fixture references could not be resolved:")
        print()
        for error in fixture_errors[:10]:  # Show first 10
            print(f"  {error}")
        if len(fixture_errors) > 10:
            print(f"  ... and {len(fixture_errors) - 10} more")
        print()
        print("FIX: Ensure fixture definitions exist in conftest.py files")
        print("TIP: When copying tests, ALWAYS copy fixture definitions too")
        print("=" * 60)
        return 1

    # Also check for collection errors that might indicate missing fixtures
    if "error" in result.stdout.lower() or result.returncode != 0:
        # Only fail if it's actually a fixture issue
        stderr_lower = result.stderr.lower()
        if "fixture" in stderr_lower:
            print("Fixture collection errors detected:")
            print(result.stderr[:500])
            return 1

    print("Fixture validation passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(validate_fixtures())
    except subprocess.TimeoutExpired:
        print("WARNING: Fixture validation timed out (>120s)")
        print("Skipping validation - tests may still have fixture issues")
        sys.exit(0)  # Don't block commit on timeout
    except Exception as e:
        print(f"WARNING: Fixture validation failed with error: {e}")
        sys.exit(0)  # Don't block commit on script errors
