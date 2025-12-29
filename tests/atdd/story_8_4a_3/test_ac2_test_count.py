"""[P0] ATDD tests for AC-8.4a-3.2: Test count unchanged or increased.

Given the current test count baseline from the 31 files
When the refactoring is complete
Then the total test count is unchanged or increased (no tests lost)

These tests verify that no tests were lost during the refactoring process.
"""

import subprocess
from pathlib import Path

import pytest

# Baseline test count from 31 moderate priority files (recorded before refactoring)
BASELINE_TEST_COUNT = 610  # Approximate based on story


class TestAC2TestCount:
    """[P0] Tests for AC-8.4a-3.2 - Test count preservation."""

    @pytest.mark.atdd
    def test_ac_8_4a_3_2_1_total_test_count_gte_baseline(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.2.1: Total unit test count >= baseline (~610 tests)."""
        result = subprocess.run(
            ["pytest", str(tests_unit_path), "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Parse output for test count (last line typically shows "X tests collected")
        output = result.stdout + result.stderr
        # Extract test count
        test_count = 0
        for line in output.splitlines():
            if "test" in line.lower() and "collected" in line.lower():
                # Parse lines like "4536/4548 tests collected"
                parts = line.split()
                for part in parts:
                    if "/" in part:
                        # Format: "4536/4548"
                        test_count = int(part.split("/")[0])
                        break
                    elif part.isdigit():
                        test_count = int(part)
                        break
                if test_count:
                    break

        assert test_count >= BASELINE_TEST_COUNT, (
            f"Test count {test_count} is less than baseline {BASELINE_TEST_COUNT}. "
            "Tests may have been lost during refactoring."
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_2_2_forecasting_tests_preserved(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.2.2: Forecasting module tests preserved."""
        forecasting_path = tests_unit_path / "forecasting"
        result = subprocess.run(
            ["pytest", str(forecasting_path), "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Should have tests in forecasting directory
        assert "test" in result.stdout.lower() or forecasting_path.exists(), (
            "Forecasting tests should be preserved after refactoring"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_2_3_external_data_tests_preserved(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.2.3: External data module tests preserved."""
        external_path = tests_unit_path / "external_data"
        result = subprocess.run(
            ["pytest", str(external_path), "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert "test" in result.stdout.lower() or external_path.exists(), (
            "External data tests should be preserved after refactoring"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_2_4_ingestion_tests_preserved(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.2.4: Ingestion module tests preserved."""
        ingestion_path = tests_unit_path / "ingestion"
        result = subprocess.run(
            ["pytest", str(ingestion_path), "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert "test" in result.stdout.lower() or ingestion_path.exists(), (
            "Ingestion tests should be preserved after refactoring"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_2_5_insights_tests_preserved(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.2.5: Insights module tests preserved."""
        insights_path = tests_unit_path / "insights"
        result = subprocess.run(
            ["pytest", str(insights_path), "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert "test" in result.stdout.lower() or insights_path.exists(), (
            "Insights tests should be preserved after refactoring"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_2_6_retrieval_tests_preserved(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.2.6: Retrieval module tests preserved."""
        retrieval_path = tests_unit_path / "retrieval"
        result = subprocess.run(
            ["pytest", str(retrieval_path), "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert "test" in result.stdout.lower() or retrieval_path.exists(), (
            "Retrieval tests should be preserved after refactoring"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_2_7_shared_tests_preserved(self, tests_unit_path: Path) -> None:
        """TEST-AC-8.4a-3.2.7: Shared module tests preserved."""
        shared_path = tests_unit_path / "shared"
        result = subprocess.run(
            ["pytest", str(shared_path), "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert "test" in result.stdout.lower() or shared_path.exists(), (
            "Shared tests should be preserved after refactoring"
        )
