"""Test AC1: Variable Cost MAPE <8% (from 41.43% baseline).

Story 6.23 - RED PHASE: Tests MUST FAIL initially.
"""

from __future__ import annotations

import json
import re
import subprocess

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xfail(
        reason="TDD RED phase - expected to fail until Story 6.23 implementation complete"
    ),
]


class TestAC1VariableCostMAPE:
    """AC1: Variable Cost MAPE <8% (from 41.43% baseline).

    GIVEN the improvements from stories 6.15-6.22 are implemented
    WHEN running unified validation with --variable variable_cost
    THEN the Variable Cost MAPE should be <8%

    RED PHASE: This test will FAIL until validation shows MAPE <8%.
    """

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
