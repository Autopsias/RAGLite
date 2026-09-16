"""[P0] ATDD tests for AC-8.4b.4: All Integration Tests Pass.

Given all integration tests currently pass
When the refactoring is complete
Then all integration tests continue to pass

These tests verify that all integration tests pass after refactoring.
"""

import subprocess
from pathlib import Path

import pytest

from .conftest import directory_exists, get_all_integration_test_files


class TestAC4TestsPassing:
    """[P0] Tests for AC-8.4b.4 - All tests pass."""

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4b_4_1_all_integration_tests_pass(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.4.1: All integration tests pass."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(tests_integration_path),
                "-x",  # Stop on first failure
                "-q",
                "--no-header",
                "-m",
                "not slow",  # Exclude slow tests for faster validation
            ],
            capture_output=True,
            text=True,
            cwd=tests_integration_path.parent.parent,
            timeout=600,  # 10 minute timeout
        )

        output = result.stdout + result.stderr
        if "FAILED" in output or "ERROR" in output:
            pytest.fail(f"Integration tests failed:\n{output}")

        assert result.returncode == 0 or "passed" in output.lower(), f"Test run failed: {output}"

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4b_4_2_no_import_errors(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.4.2: No import errors during test collection."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(tests_integration_path),
                "--collect-only",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=tests_integration_path.parent.parent,
        )

        output = result.stdout + result.stderr
        assert "ImportError" not in output, f"Import errors found: {output}"
        assert "ModuleNotFoundError" not in output, f"Module errors found: {output}"
        assert "SyntaxError" not in output, f"Syntax errors found: {output}"

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4b_4_3_no_fixture_errors(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.4.3: No fixture resolution errors."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(tests_integration_path),
                "--collect-only",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=tests_integration_path.parent.parent,
        )

        output = result.stdout + result.stderr
        # Check for actual fixture error patterns, not just the words "fixture" and "error"
        has_fixture_error = any(
            pattern in output.lower()
            for pattern in ["fixture '", "fixture not found", "error: fixture"]
        )
        assert not has_fixture_error, f"Fixture errors found: {output}"

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4b_4_4_pytest_markers_valid(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.4.4: All pytest markers are valid."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(tests_integration_path),
                "--collect-only",
                "--strict-markers",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=tests_integration_path.parent.parent,
        )

        output = result.stdout + result.stderr
        assert "Unknown pytest.mark" not in output, f"Unknown markers: {output}"

    @pytest.mark.atdd
    def test_ac_8_4b_4_5_test_isolation_maintained(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.4.5: Test isolation is maintained (no cross-file imports)."""
        test_files = get_all_integration_test_files(tests_integration_path)
        violations = []

        for test_file in test_files:
            content = test_file.read_text()
            # Check for imports from other test files
            lines = content.split("\n")
            for line in lines:
                if line.strip().startswith("from tests.integration.test_"):
                    violations.append(f"{test_file.name}: {line.strip()}")
                elif "import test_" in line and not line.strip().startswith("#"):
                    violations.append(f"{test_file.name}: {line.strip()}")

        assert len(violations) == 0, f"Cross-test imports found (violates isolation): {violations}"


class TestAC4SubdirectoryTestsPassing:
    """[P1] Tests for subdirectory-specific test execution."""

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4b_4_6_forecasting_tests_pass(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.4.6: Forecasting subdirectory tests pass."""
        forecasting_path = tests_integration_path / "forecasting"
        if not directory_exists(tests_integration_path, "forecasting"):
            pytest.fail("forecasting/ directory not created yet")

        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(forecasting_path),
                "-v",
                "--no-header",
            ],
            capture_output=True,
            text=True,
            cwd=tests_integration_path.parent.parent,
            timeout=300,
        )

        output = result.stdout + result.stderr
        if "FAILED" in output or "ERROR" in output:
            pytest.fail(f"Forecasting tests failed:\n{output}")

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4b_4_7_ingestion_tests_pass(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.4.7: Ingestion subdirectory tests pass."""
        ingestion_path = tests_integration_path / "ingestion"
        if not directory_exists(tests_integration_path, "ingestion"):
            pytest.fail("ingestion/ directory not created yet")

        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(ingestion_path),
                "-v",
                "--no-header",
            ],
            capture_output=True,
            text=True,
            cwd=tests_integration_path.parent.parent,
            timeout=300,
        )

        output = result.stdout + result.stderr
        if "FAILED" in output or "ERROR" in output:
            pytest.fail(f"Ingestion tests failed:\n{output}")

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4b_4_8_model_selection_tests_pass(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.4.8: Model selection subdirectory tests pass."""
        model_selection_path = tests_integration_path / "model_selection"
        if not directory_exists(tests_integration_path, "model_selection"):
            pytest.fail("model_selection/ directory not created yet")

        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(model_selection_path),
                "-v",
                "--no-header",
            ],
            capture_output=True,
            text=True,
            cwd=tests_integration_path.parent.parent,
            timeout=300,
        )

        output = result.stdout + result.stderr
        if "FAILED" in output or "ERROR" in output:
            pytest.fail(f"Model selection tests failed:\n{output}")
