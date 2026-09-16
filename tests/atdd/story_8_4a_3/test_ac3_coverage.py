"""[P0] ATDD tests for AC-8.4a-3.3: Coverage maintained at 80%+.

Given the current coverage baseline for the affected modules
When the refactoring is complete
Then test coverage remains at or above 80%

These tests verify that coverage is maintained during refactoring.
"""

import subprocess
from pathlib import Path

import pytest

COVERAGE_THRESHOLD = 80


class TestAC3Coverage:
    """[P0] Tests for AC-8.4a-3.3 - Coverage maintenance."""

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_3_1_overall_coverage_gte_80(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.3.1: Overall unit test coverage >= 80%."""
        result = subprocess.run(
            [
                "pytest",
                str(tests_unit_path),
                "--cov=raglite",
                f"--cov-fail-under={COVERAGE_THRESHOLD}",
                "-q",
                "--tb=no",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        # Coverage check is built into pytest-cov
        assert result.returncode == 0, (
            f"Coverage below {COVERAGE_THRESHOLD}%.\n"
            f"Run: pytest tests/unit/ --cov=raglite --cov-report=term-missing\n"
            f"Output: {result.stdout}\n{result.stderr}"
        )

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_3_2_forecasting_coverage(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.3.2: Forecasting module coverage >= 80%."""
        forecasting_tests = tests_unit_path / "forecasting"
        result = subprocess.run(
            [
                "pytest",
                str(forecasting_tests),
                "--cov=raglite.forecasting",
                f"--cov-fail-under={COVERAGE_THRESHOLD}",
                "-q",
                "--tb=no",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        # Allow failure if directory doesn't exist yet
        if "no tests ran" in result.stdout.lower() or not forecasting_tests.exists():
            pytest.skip("Forecasting tests not yet reorganized")
        assert result.returncode == 0, f"Forecasting coverage below {COVERAGE_THRESHOLD}%"

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_3_3_external_data_coverage(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.3.3: External data module coverage >= 80%."""
        external_tests = tests_unit_path / "external_data"
        result = subprocess.run(
            [
                "pytest",
                str(external_tests),
                "--cov=raglite.external_data",
                f"--cov-fail-under={COVERAGE_THRESHOLD}",
                "-q",
                "--tb=no",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if "no tests ran" in result.stdout.lower() or not external_tests.exists():
            pytest.skip("External data tests not yet reorganized")
        assert result.returncode == 0, f"External data coverage below {COVERAGE_THRESHOLD}%"

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_3_4_ingestion_coverage(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.3.4: Ingestion module coverage >= 80%."""
        ingestion_tests = tests_unit_path / "ingestion"
        result = subprocess.run(
            [
                "pytest",
                str(ingestion_tests),
                "--cov=raglite.ingestion",
                f"--cov-fail-under={COVERAGE_THRESHOLD}",
                "-q",
                "--tb=no",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if "no tests ran" in result.stdout.lower() or not ingestion_tests.exists():
            pytest.skip("Ingestion tests not yet reorganized")
        assert result.returncode == 0, f"Ingestion coverage below {COVERAGE_THRESHOLD}%"

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_3_5_insights_coverage(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.3.5: Insights module coverage >= 80%."""
        insights_tests = tests_unit_path / "insights"
        result = subprocess.run(
            [
                "pytest",
                str(insights_tests),
                "--cov=raglite.insights",
                f"--cov-fail-under={COVERAGE_THRESHOLD}",
                "-q",
                "--tb=no",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if "no tests ran" in result.stdout.lower() or not insights_tests.exists():
            pytest.skip("Insights tests not yet reorganized")
        assert result.returncode == 0, f"Insights coverage below {COVERAGE_THRESHOLD}%"

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_3_6_retrieval_coverage(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.3.6: Retrieval module coverage >= 80%."""
        retrieval_tests = tests_unit_path / "retrieval"
        result = subprocess.run(
            [
                "pytest",
                str(retrieval_tests),
                "--cov=raglite.retrieval",
                f"--cov-fail-under={COVERAGE_THRESHOLD}",
                "-q",
                "--tb=no",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if "no tests ran" in result.stdout.lower() or not retrieval_tests.exists():
            pytest.skip("Retrieval tests not yet reorganized")
        assert result.returncode == 0, f"Retrieval coverage below {COVERAGE_THRESHOLD}%"
