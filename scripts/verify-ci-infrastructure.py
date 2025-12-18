#!/usr/bin/env python3
"""Verify CI infrastructure fixes are properly configured.

This script validates the CI infrastructure changes made by the CI Specialist:
1. Priority-Based Test Execution workflow fixes
2. Database port configuration consistency
3. Test discovery validation range updates
4. Composite action availability

Usage:
    python scripts/verify-ci-infrastructure.py
"""

import os
import sys
from pathlib import Path

import yaml


def verify_priority_workflow():
    """Verify Priority-Based Test Execution workflow fixes."""
    print("🔍 Verifying Priority-Based Test Execution workflow...")

    workflow_path = Path(".github/workflows/test-priority-based.yml")
    if not workflow_path.exists():
        print("❌ Priority-Based workflow not found")
        return False

    with open(workflow_path) as f:
        content = f.read()

    # Check 1: All jobs use self-hosted raglite runners
    raglite_runner_count = content.count("runs-on: [self-hosted, raglite]")
    ubuntu_runner_count = content.count("runs-on: ubuntu-latest")

    if raglite_runner_count >= 4 and ubuntu_runner_count == 0:
        print(f"✅ All jobs use self-hosted raglite runners ({raglite_runner_count} jobs)")
    else:
        print(
            f"❌ Runner configuration issue: {raglite_runner_count} raglite, {ubuntu_runner_count} ubuntu"
        )
        return False

    # Check 2: Priority markers use correct syntax
    if "priority(P0)" in content and "priority(P1)" in content:
        print("✅ Priority markers use correct pytest syntax")
    else:
        print("❌ Priority markers not found or incorrect syntax")
        return False

    # Check 3: No old -k syntax
    if '-k "P0"' not in content and '-k "P1"' not in content:
        print("✅ No old pytest -k syntax found")
    else:
        print("❌ Old pytest -k syntax still present")
        return False

    return True


def verify_database_configuration():
    """Verify database port configuration consistency."""
    print("\n🔍 Verifying database configuration...")

    docker_path = Path("docker-compose.yml")
    if not docker_path.exists():
        print("❌ Docker Compose file not found")
        return False

    with open(docker_path) as f:
        docker_config = yaml.safe_load(f)

    # Check test PostgreSQL configuration
    test_pg = docker_config.get("services", {}).get("postgresql-test", {})
    if not test_pg:
        print("❌ postgresql-test service not found")
        return False

    # Verify port mapping
    ports = test_pg.get("ports", [])
    if "5433:5432" not in ports:
        print(f"❌ Test PostgreSQL port mapping incorrect: {ports}")
        return False

    # Verify environment variables match CI expectations
    env = test_pg.get("environment", [])
    expected_env = {
        "POSTGRES_DB": "raglite_ci",
        "POSTGRES_USER": "raglite_ci",
        "POSTGRES_PASSWORD": "raglite_ci",
    }

    for key, value in expected_env.items():
        if f"{key}={value}" not in env:
            print(f"❌ Test PostgreSQL env mismatch for {key}: expected {value}")
            return False

    print("✅ Database configuration matches CI expectations")
    return True


def verify_test_count_validation():
    """Verify test count validation range updates."""
    print("\n🔍 Verifying test count validation...")

    ci_path = Path(".github/workflows/ci.yml")
    if not ci_path.exists():
        print("❌ CI workflow not found")
        return False

    with open(ci_path) as f:
        content = f.read()

    # Check for updated test count ranges
    if "EXPECTED_MIN_TESTS=300" in content and "EXPECTED_MAX_TESTS=5000" in content:
        print("✅ Test count validation ranges updated")
    else:
        print("❌ Test count validation ranges not updated")
        return False

    # Check for range validation logic
    if "EXPECTED_MAX_TESTS" in content and "parametric explosions" in content:
        print("✅ Range validation logic updated")
    else:
        print("❌ Range validation logic not found")
        return False

    return True


def verify_composite_action():
    """Verify composite UV action was created."""
    print("\n🔍 Verifying composite UV action...")

    action_path = Path(".github/actions/setup-uv/action.yml")
    if not action_path.exists():
        print("❌ Composite UV action not found")
        return False

    with open(action_path) as f:
        content = f.read()

    # Check key components
    required_elements = [
        "name: 'Setup Python with UV'",
        "using: 'composite'",
        "network-resilient",
        "MAX_RETRIES=3",
    ]

    for element in required_elements:
        if element not in content:
            print(f"❌ Required element missing: {element}")
            return False

    print("✅ Composite UV action properly configured")
    return True


def verify_pytest_configuration():
    """Verify pytest configuration supports priority markers."""
    print("\n🔍 Verifying pytest configuration...")

    pytest_ini = Path("pytest.ini")
    if not pytest_ini.exists():
        print("❌ pytest.ini not found")
        return False

    with open(pytest_ini) as f:
        content = f.read()

    # Check for priority marker definition
    if "priority(level): test priority" in content:
        print("✅ Priority markers defined in pytest.ini")
    else:
        print("❌ Priority markers not defined in pytest.ini")
        return False

    return True


def main():
    """Run all verification checks."""
    print("🚀 Verifying CI Infrastructure Fixes")
    print("=" * 50)

    # Change to repository root if running from scripts/ directory
    if Path.cwd().name == "scripts":
        os.chdir("..")

    all_passed = True

    # Run all verification checks
    checks = [
        ("Priority-Based Workflow", verify_priority_workflow),
        ("Database Configuration", verify_database_configuration),
        ("Test Count Validation", verify_test_count_validation),
        ("Composite UV Action", verify_composite_action),
        ("Pytest Configuration", verify_pytest_configuration),
    ]

    for name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"❌ Error checking {name}: {e}")
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL VERIFICATIONS PASSED")
        print("CI infrastructure is properly configured!")
        return 0
    else:
        print("❌ SOME VERIFICATIONS FAILED")
        print("Please review the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
