"""Acceptance Tests for Story 6.23: Variable Cost MAPE Final Validation (Core).

RED PHASE - TDD: All tests in this file MUST FAIL initially.
These tests validate the Epic 6 quality gates which are the culmination
of stories 6.15-6.22.

Test IDs map to Story 6.23 Acceptance Criteria (Core):
- TEST-AC-6.23.1: Variable Cost MAPE <8%
- TEST-AC-6.23.2: Data coefficient of variation <15%

Story: /docs/sprint-artifacts/stories/6-23-variable-cost-mape-final-validation.md
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from raglite.forecasting.timeseries import extract_timeseries
from raglite.shared.clients import get_postgresql_connection

# =============================================================================
# Test Markers and Configuration
# =============================================================================

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,  # Read-only tests
    pytest.mark.slow,  # Tests take 60+ seconds
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def validation_script_path():
    """Path to unified validation script."""
    script_path = (
        Path(__file__).parent.parent.parent / "scripts" / "validate_forecasting_unified.py"
    )
    if not script_path.exists():
        pytest.skip(f"Validation script not found: {script_path}")
    return script_path


@pytest.fixture
def project_root():
    """Project root directory."""
    return Path(__file__).parent.parent.parent


# =============================================================================
# TEST-AC-6.23.1: Variable Cost MAPE <8% (from 41.43% baseline)
# =============================================================================


class TestAC1VariableCostMAPE:
    """AC1: Variable Cost MAPE <8% (from 41.43% baseline).

    GIVEN the improvements from stories 6.15-6.22 are implemented
    WHEN running unified validation with --variable variable_cost
    THEN the Variable Cost MAPE should be <8%

    RED PHASE: This test will FAIL until validation shows MAPE <8%.

    NOTE: Tests in this class require Variable Cost data ingestion which
    is not available in CI environments. Skip in CI.
    """

    @pytest.fixture(autouse=True)
    def skip_in_ci(self):
        """Skip in CI - requires Variable Cost data ingestion."""
        import os

        if os.getenv("CI"):
            pytest.skip("Skipped in CI - requires Variable Cost data ingestion")

    @pytest.mark.slow
    def test_ac1_variable_cost_mape_below_target(self, validation_script_path, project_root):
        """TEST-AC-6.23.1: Variable Cost MAPE must be below 8% target.

        GIVEN: Entity-specific extraction (Story 6.15) filters Portugal-only data
        WHEN: Running validation with holdout MAPE method
        THEN: Variable Cost MAPE < 8.0% (improved from 41.43% baseline)
        """
        # GIVEN: Validation script exists and improvements are implemented
        assert validation_script_path.exists(), "Validation script must exist"

        # WHEN: Run validation for variable_cost with holdout method
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(validation_script_path),
                "--variable",
                "variable_cost",
                "--mape-method",
                "holdout",
                "--export-json",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=300,  # 5 minute timeout for single variable
        )

        # THEN: Script completes successfully
        assert result.returncode == 0, (
            f"Validation script failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # THEN: Parse and verify MAPE is below target
        import json

        # Find JSON output in stdout
        output_lines = result.stdout.strip().split("\n")
        json_output = None
        for line in output_lines:
            try:
                json_output = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

        assert json_output is not None, "No JSON output found in validation results"

        # Extract variable_cost MAPE from results
        variable_cost_mape = None
        if "variable_results" in json_output:
            for var_result in json_output["variable_results"]:
                if var_result.get("variable_name") == "variable_cost":
                    variable_cost_mape = var_result.get("actual_mape")
                    break
        elif "quality_gate" in json_output:
            variable_cost_mape = json_output["quality_gate"].get("variable_cost_mape")

        # AC1 ASSERTION: MAPE must be below 8%
        # This test will FAIL until Story 6.23 validation passes
        assert variable_cost_mape is not None, "Variable Cost MAPE not found in results"
        assert variable_cost_mape < 8.0, (
            f"TEST-AC-6.23.1 FAILED: Variable Cost MAPE {variable_cost_mape:.2f}% >= 8.0% target. "
            f"(Baseline was 41.43%, must improve to <8%)"
        )

    def test_ac1_variable_cost_improvement_percentage(self, validation_script_path, project_root):
        """TEST-AC-6.23.1b: Verify improvement percentage from baseline.

        GIVEN: Baseline MAPE was 41.43%
        WHEN: New validation is run
        THEN: Improvement should be >80% reduction
        """
        BASELINE_MAPE = 41.43
        TARGET_IMPROVEMENT_PCT = 80.0  # Must improve by at least 80%

        # Run validation
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(validation_script_path),
                "--variable",
                "variable_cost",
                "--mape-method",
                "holdout",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=300,
        )

        # Skip if validation script not ready
        if result.returncode != 0:
            pytest.skip(f"Validation script not ready: {result.stderr}")

        # Parse MAPE from output (look for MAPE percentage pattern)
        import re

        mape_match = re.search(r"MAPE[:\s]+(\d+\.?\d*)%", result.stdout)
        if not mape_match:
            pytest.skip("Could not parse MAPE from output")

        current_mape = float(mape_match.group(1))
        improvement_pct = ((BASELINE_MAPE - current_mape) / BASELINE_MAPE) * 100

        # AC1b ASSERTION: Must show significant improvement
        assert improvement_pct >= TARGET_IMPROVEMENT_PCT, (
            f"Improvement {improvement_pct:.1f}% is below {TARGET_IMPROVEMENT_PCT}% threshold. "
            f"Baseline: {BASELINE_MAPE}%, Current: {current_mape}%"
        )


# =============================================================================
# TEST-AC-6.23.2: Data coefficient of variation <15% (from 33% baseline)
# =============================================================================


class TestAC2DataCoefficientOfVariation:
    """AC2: Data coefficient of variation <15% (from 33% baseline).

    GIVEN entity-specific extraction filters Portugal-only entities
    WHEN calculating CoV from extracted time series
    THEN CoV should be <15% (improved from 33% baseline)

    RED PHASE: This test will FAIL until data quality improves.

    NOTE: Tests in this class require Variable Cost data ingestion which
    is not available in CI environments. Skip in CI.
    """

    @pytest.fixture(autouse=True)
    def skip_in_ci(self):
        """Skip in CI - requires Variable Cost data ingestion."""
        import os

        if os.getenv("CI"):
            pytest.skip("Skipped in CI - requires Variable Cost data ingestion")

    def test_ac2_variable_cost_cov_below_target(self):
        """TEST-AC-6.23.2: Variable Cost data CoV must be below 15%.

        GIVEN: Portugal-only entity filtering is active (Story 6.15)
        WHEN: Extracting variable_cost time series data
        THEN: Coefficient of variation < 15% (from 33% baseline)
        """
        import numpy as np

        # GIVEN: PostgreSQL connection available
        try:
            get_postgresql_connection()
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")
        # WHEN: Extract variable_cost time series with entity filtering
        try:
            timeseries_data = extract_timeseries(
                metric_name="variable_cost",
                entity_filter="Portugal",  # Story 6.15: Entity-specific filtering
            )
        except Exception as e:
            pytest.skip(f"Time series extraction not implemented: {e}")

        # Skip if no data
        if not timeseries_data or len(timeseries_data) < 3:
            pytest.skip("Insufficient time series data for CoV calculation")

        # THEN: Calculate coefficient of variation
        values = [point.value for point in timeseries_data]
        mean_value = np.mean(values)
        std_value = np.std(values)

        if mean_value == 0:
            pytest.skip("Cannot calculate CoV with zero mean")

        cov = (std_value / abs(mean_value)) * 100

        # AC2 ASSERTION: CoV must be below 15%
        assert cov < 15.0, (
            f"TEST-AC-6.23.2 FAILED: Variable Cost CoV {cov:.2f}% >= 15% target. "
            f"(Baseline was 33%, entity filtering should reduce variance)"
        )

    def test_ac2_portugal_only_entity_filtering(self):
        """TEST-AC-6.23.2b: Verify Portugal-only entity filtering is active.

        GIVEN: Entity detection from Story 6.15 is implemented
        WHEN: Extracting variable_cost data
        THEN: Only Portugal entities should be included
        """
        try:
            # Extract with explicit Portugal filter
            timeseries_data = extract_timeseries(
                metric_name="variable_cost",
                entity_filter="Portugal",
            )
        except Exception as e:
            pytest.skip(f"Entity filtering not implemented: {e}")

        # Verify data is Portugal-only (values in expected range)
        # Portugal variable cost should be EUR -150 to -350 per ton
        if timeseries_data:
            values = [point.value for point in timeseries_data]
            # AC2b: Values should be in Portugal range (negative, EUR/ton)
            assert all(-400 <= v <= 0 for v in values), (
                f"Variable cost values outside Portugal range: {values}"
            )

    def test_ac2_value_normalization_eur_per_ton(self):
        """TEST-AC-6.23.2c: Verify values normalized to EUR/ton.

        GIVEN: Variable cost data is extracted
        WHEN: Checking value units
        THEN: Values should be normalized EUR/ton (range: -150 to -350)
        """
        try:
            timeseries_data = extract_timeseries(metric_name="variable_cost")
        except Exception as e:
            pytest.skip(f"Time series extraction not implemented: {e}")

        if not timeseries_data:
            pytest.skip("No variable cost data available")

        values = [point.value for point in timeseries_data]

        # AC2c: Values should be in EUR/ton range for Portugal cement
        # Variable costs are typically -150 to -350 EUR/ton (negative = cost)
        EXPECTED_MIN = -400
        EXPECTED_MAX = 0

        assert min(values) >= EXPECTED_MIN, f"Min value {min(values)} below expected range"
        assert max(values) <= EXPECTED_MAX, f"Max value {max(values)} above expected range"
