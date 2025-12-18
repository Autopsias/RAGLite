#!/usr/bin/env python3
"""
CI Infrastructure Validation Script

Validates that the CI infrastructure fixes are properly configured and working.
This script checks for:
1. Sequential execution in integration tests (-n 0)
2. Aggressive port cleanup in PostgreSQL containers
3. Proper error handling and timeouts
4. Consistent database configurations

Usage: python scripts/validate-ci-infrastructure.py
"""

import re
import sys
from pathlib import Path


def validate_integration_test_sequential_execution():
    """Validate that integration tests use sequential execution to avoid pytest-xdist issues."""
    ci_workflow_path = Path(".github/workflows/ci.yml")

    if not ci_workflow_path.exists():
        return False, "CI workflow file not found"

    content = ci_workflow_path.read_text()

    # Look for the integration test execution section
    integration_test_pattern = r"pytest tests/integration/.*-n (\d+)"
    matches = re.findall(integration_test_pattern, content, re.MULTILINE | re.DOTALL)

    if not matches:
        return False, "No pytest integration test execution found"

    # Check if using sequential execution (-n 0)
    using_sequential = any(match == "0" for match in matches)

    if not using_sequential:
        return (
            False,
            f"Integration tests still using parallel execution (-n {matches[-1]}), should be -n 0",
        )

    return True, "Integration tests properly configured for sequential execution"


def validate_aggressive_port_cleanup():
    """Validate that PostgreSQL containers use aggressive port cleanup."""
    ci_workflow_path = Path(".github/workflows/ci.yml")

    if not ci_workflow_path.exists():
        return False, "CI workflow file not found"

    content = ci_workflow_path.read_text()

    # Check for aggressive cleanup patterns
    required_patterns = [
        r"lsof -ti:\$.*PORT.*xargs -r kill -9",  # lsof port cleanup
        r"sleep 3.*# Increased wait time",  # Increased wait times
        r"Aggressively cleaning containers",  # Comment indicating aggressive cleanup
    ]

    missing_patterns = []
    for pattern in required_patterns:
        if not re.search(pattern, content, re.MULTILINE):
            missing_patterns.append(pattern)

    if missing_patterns:
        return False, f"Missing aggressive cleanup patterns: {missing_patterns}"

    return True, "PostgreSQL containers properly configured with aggressive port cleanup"


def validate_error_handling():
    """Validate enhanced error handling in CI workflow."""
    ci_workflow_path = Path(".github/workflows/ci.yml")

    if not ci_workflow_path.exists():
        return False, "CI workflow file not found"

    content = ci_workflow_path.read_text()

    # Check for enhanced error handling patterns
    required_patterns = [
        r"--tb=short",  # Short traceback format
        r"--maxfail=3",  # Max failures before stopping
        r"MAX_RETRIES=45",  # Increased retry count
        r"Container logs for debugging:",  # Debug logging on failure
    ]

    missing_patterns = []
    for pattern in required_patterns:
        if not re.search(pattern, content, re.MULTILINE):
            missing_patterns.append(pattern)

    if missing_patterns:
        return False, f"Missing error handling patterns: {missing_patterns}"

    return True, "Enhanced error handling properly configured"


def validate_database_configuration():
    """Validate consistent database configuration across all jobs."""
    ci_workflow_path = Path(".github/workflows/ci.yml")

    if not ci_workflow_path.exists():
        return False, "CI workflow file not found"

    content = ci_workflow_path.read_text()

    # Check for consistent raglite_ci database configuration
    required_patterns = [
        r"POSTGRES_DB=raglite_ci",
        r"POSTGRES_USER=raglite_ci",
        r"POSTGRES_PASSWORD=raglite_ci",
    ]

    missing_patterns = []
    for pattern in required_patterns:
        if not re.search(pattern, content):
            missing_patterns.append(pattern)

    if missing_patterns:
        return False, f"Missing database configuration patterns: {missing_patterns}"

    return True, "Database configuration is consistent"


def validate_pytest_xdist_avoidance():
    """Validate that pytest-xdist is avoided in scenarios with shared state."""
    ci_workflow_path = Path(".github/workflows/ci.yml")

    if not ci_workflow_path.exists():
        return False, "CI workflow file not found"

    content = ci_workflow_path.read_text()

    # Check for explanatory comments about pytest-xdist avoidance
    explanatory_comments = [
        "pytest-xdist worker controller has internal errors",
        "shared Qdrant collection state",
        "Integration tests share session fixtures",
    ]

    found_comments = sum(1 for comment in explanatory_comments if comment in content)

    if found_comments < 2:  # Require at least 2 of the 3 comments
        return (
            False,
            f"Insufficient explanatory comments about pytest-xdist avoidance ({found_comments}/3)",
        )

    return True, "Proper pytest-xdist avoidance documentation found"


def main():
    """Run all validation checks and report results."""
    print("🔍 CI Infrastructure Validation")
    print("=" * 50)

    validations = [
        ("Integration Test Sequential Execution", validate_integration_test_sequential_execution),
        ("Aggressive Port Cleanup", validate_aggressive_port_cleanup),
        ("Enhanced Error Handling", validate_error_handling),
        ("Database Configuration", validate_database_configuration),
        ("pytest-xdist Avoidance", validate_pytest_xdist_avoidance),
    ]

    all_passed = True
    results = []

    for name, validator in validations:
        try:
            passed, message = validator()
            results.append((name, passed, message))
            if not passed:
                all_passed = False
        except Exception as e:
            results.append((name, False, f"Validation error: {e}"))
            all_passed = False

    # Print results
    print("\n📊 Validation Results:")
    print("-" * 50)

    for name, passed, message in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {name}")
        if not passed:
            print(f"   → {message}")

    print("\n" + "=" * 50)

    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED")
        print("CI infrastructure is properly configured!")
        return 0
    else:
        print("❌ SOME VALIDATIONS FAILED")
        print("Please review and fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
