#!/usr/bin/env python3
"""CI Test Discovery Validation Script

Validates that all tests are discoverable and properly configured for CI pipeline.
This script ensures:
1. All test files can be discovered by pytest
2. Test markers are properly configured
3. Test organization follows project structure
4. JUnit XML output is generated correctly
"""

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def run_command(cmd, capture_output=True):
    """Run command and return result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture_output, text=True, timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"


def validate_test_discovery():
    """Validate that pytest can discover all expected tests."""
    print("🔍 Validating test discovery...")

    # Check total test collection
    success, output, _ = run_command("python -m pytest --collect-only -q")
    if not success:
        print("❌ Test collection failed")
        return False

    # Extract test count from output
    if "tests collected" in output:
        # Get the last line with collection summary
        lines = output.strip().split("\n")
        for line in reversed(lines):
            if "tests collected" in line:
                print(f"✅ {line.strip()}")
                break
    else:
        print("❌ Could not find test collection summary")
        return False

    return True


def validate_test_organization():
    """Validate test organization follows expected structure."""
    print("\n📁 Validating test organization...")

    expected_structure = {
        "tests/unit/": "Unit tests (no external dependencies)",
        "tests/integration/": "Integration tests (require Qdrant)",
        "tests/e2e/": "End-to-end tests (full system)",
    }

    all_good = True
    for path, description in expected_structure.items():
        if Path(path).exists():
            test_files = list(Path(path).glob("test_*.py"))
            print(f"✅ {path}: {len(test_files)} test files - {description}")
        else:
            print(f"❌ {path}: Directory missing - {description}")
            all_good = False

    return all_good


def validate_marker_configuration():
    """Validate that test markers are properly configured."""
    print("\n🏷️  Validating marker configuration...")

    # Check that pytest.ini has required markers
    pytest_ini = Path("pytest.ini")
    if not pytest_ini.exists():
        print("❌ pytest.ini not found")
        return False

    content = pytest_ini.read_text()
    required_markers = ["slow:", "unit:", "integration:", "e2e:", "smoke:", "p0:"]

    all_good = True
    for marker in required_markers:
        if marker in content:
            print(f"✅ Marker {marker.strip(':')} configured")
        else:
            print(f"❌ Marker {marker.strip(':')} missing from pytest.ini")
            all_good = False

    return all_good


def validate_junit_xml_output():
    """Validate JUnit XML output for CI integration."""
    print("\n📊 Validating JUnit XML output...")

    # Ensure test-results directory exists
    results_dir = Path("test-results/pytest")
    results_dir.mkdir(parents=True, exist_ok=True)

    # Run a simple test to generate XML
    success, _, _ = run_command(
        "python -m pytest tests/unit/test_shared_config.py::test_settings_load_from_env -q"
    )

    if not success:
        print("❌ Failed to run test for XML validation")
        return False

    # Check XML file exists and is valid
    junit_file = results_dir / "junit.xml"
    if not junit_file.exists():
        print("❌ JUnit XML file not generated")
        return False

    try:
        tree = ET.parse(junit_file)
        root = tree.getroot()

        # Check basic XML structure
        testsuites = root.findall("testsuite")
        if testsuites:
            total_tests = sum(int(ts.get("tests", 0)) for ts in testsuites)
            print(f"✅ JUnit XML valid: {total_tests} tests reported")
            return True
        else:
            print("❌ JUnit XML missing testsuite elements")
            return False

    except ET.ParseError as e:
        print(f"❌ JUnit XML parsing failed: {e}")
        return False


def validate_python_imports():
    """Validate that critical modules can be imported."""
    print("\n🐍 Validating Python imports...")

    test_imports = [
        ("import raglite", "raglite module"),
        ("from raglite.main import mcp", "MCP server"),
        ("from tests.conftest import *", "test fixtures"),
    ]

    all_good = True
    for import_cmd, description in test_imports:
        success, _, error = run_command(f'python -c "{import_cmd}"')
        if success:
            print(f"✅ {description} imports successfully")
        else:
            print(f"❌ {description} import failed")
            all_good = False

    return all_good


def main():
    """Run all CI test discovery validations."""
    print("🚀 CI Test Discovery Validation\n")

    validations = [
        ("Test Discovery", validate_test_discovery),
        ("Test Organization", validate_test_organization),
        ("Marker Configuration", validate_marker_configuration),
        ("JUnit XML Output", validate_junit_xml_output),
        ("Python Imports", validate_python_imports),
    ]

    results = {}
    for name, validator in validations:
        try:
            results[name] = validator()
        except Exception as e:
            print(f"❌ {name} validation failed with error: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<8} {name}")

    print(f"\nOverall: {passed}/{total} validations passed")

    if passed == total:
        print("🎉 All test discovery validations passed!")
        return 0
    else:
        print("💥 Some validations failed - CI may have issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
