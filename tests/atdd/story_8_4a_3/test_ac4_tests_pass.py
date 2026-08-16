"""[P0] ATDD tests for AC-8.4a-3.4: All unit tests pass.

Given all unit tests currently pass
When the refactoring is complete
Then all unit tests continue to pass

These tests verify that refactoring does not break existing tests.
"""

import subprocess
from pathlib import Path

import pytest


class TestAC4TestsPass:
    """[P0] Tests for AC-8.4a-3.4 - All tests pass."""

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_4_1_forecasting_tests_pass(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.4.1: Forecasting tests pass after refactoring."""
        forecasting_path = tests_unit_path / "forecasting"
        if not forecasting_path.exists():
            pytest.skip("Forecasting directory not yet created")

        result = subprocess.run(
            ["pytest", str(forecasting_path), "-x", "-q", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, (
            f"Forecasting tests failed:\n{result.stdout}\n{result.stderr}"
        )

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_4_2_external_data_tests_pass(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.4.2: External data tests pass after refactoring."""
        external_path = tests_unit_path / "external_data"
        if not external_path.exists():
            pytest.skip("External data directory not yet created")

        result = subprocess.run(
            ["pytest", str(external_path), "-x", "-q", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, (
            f"External data tests failed:\n{result.stdout}\n{result.stderr}"
        )

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_4_3_ingestion_tests_pass(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.4.3: Ingestion tests pass after refactoring."""
        ingestion_path = tests_unit_path / "ingestion"
        if not ingestion_path.exists():
            pytest.skip("Ingestion directory not yet created")

        result = subprocess.run(
            ["pytest", str(ingestion_path), "-x", "-q", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, f"Ingestion tests failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_4_4_insights_tests_pass(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.4.4: Insights tests pass after refactoring."""
        insights_path = tests_unit_path / "insights"
        if not insights_path.exists():
            pytest.skip("Insights directory not yet created")

        result = subprocess.run(
            ["pytest", str(insights_path), "-x", "-q", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, f"Insights tests failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_4_5_retrieval_tests_pass(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.4.5: Retrieval tests pass after refactoring."""
        retrieval_path = tests_unit_path / "retrieval"
        if not retrieval_path.exists():
            pytest.skip("Retrieval directory not yet created")

        result = subprocess.run(
            ["pytest", str(retrieval_path), "-x", "-q", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, f"Retrieval tests failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4a_3_4_6_shared_tests_pass(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.4.6: Shared tests pass after refactoring."""
        shared_path = tests_unit_path / "shared"
        if not shared_path.exists():
            pytest.skip("Shared directory not yet created")

        result = subprocess.run(
            ["pytest", str(shared_path), "-x", "-q", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, f"Shared tests failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.atdd
    def test_ac_8_4a_3_4_7_no_import_errors(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.4.7: No import errors after refactoring."""
        result = subprocess.run(
            ["pytest", str(tests_unit_path), "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Check for import errors in output
        output = result.stdout + result.stderr
        import_errors = [
            line
            for line in output.splitlines()
            if (
                "E       ImportError:" in line
                or "E       ModuleNotFoundError:" in line
                or "ModuleNotFoundError:" in line.strip()[:30]
            )
        ]
        assert not import_errors, "Import errors detected:\n" + "\n".join(import_errors)

    @pytest.mark.atdd
    def test_ac_8_4a_3_4_8_no_fixture_errors(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.4.8: No fixture errors after refactoring."""
        result = subprocess.run(
            ["pytest", str(tests_unit_path), "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Check for fixture errors
        output = result.stdout + result.stderr
        fixture_errors = [
            line
            for line in output.splitlines()
            if "fixture" in line.lower() and "error" in line.lower()
        ]
        assert not fixture_errors, "Fixture errors detected:\n" + "\n".join(fixture_errors)
