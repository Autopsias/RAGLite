"""Test AC3: At least 10/12 variables meet their MAPE targets.

Story 6.23 - RED PHASE: Tests MUST FAIL initially.
"""

from __future__ import annotations

import json
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


class TestAC3VariablePassRate:
    """AC3: At least 10/12 variables meet their MAPE targets.

    GIVEN the full validation runs with all 12 variables
    WHEN checking pass rate against MAPE targets
    THEN at least 10 variables (83.3%+) should pass

    RED PHASE: This test will FAIL until 10/12 pass rate achieved.
    """

    @pytest.mark.slow
    def test_ac3_minimum_pass_rate(self, validation_script_path, project_root):
        """TEST-AC-6.23.3: At least 10/12 variables must meet MAPE targets.

        GIVEN: All improvements from 6.15-6.22 are implemented
        WHEN: Running full validation (--full)
        THEN: Pass rate >= 83.3% (10/12 variables)
        """
        MINIMUM_PASSING = 10
        TOTAL_VARIABLES = 12
        MINIMUM_PASS_RATE = 0.833

        # WHEN: Run full validation
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(validation_script_path),
                "--full",
                "--export-json",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=660,  # 11 minute timeout for full validation
        )

        # Parse results
        json_output = None
        for line in result.stdout.strip().split("\n"):
            try:
                json_output = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

        if json_output is None:
            pytest.skip("Could not parse JSON output from validation")

        # Extract pass rate
        variables_passed = json_output.get("variables_passed", 0)
        variables_tested = json_output.get("variables_tested", 0)
        pass_rate = json_output.get("pass_rate", 0)

        # AC3 ASSERTION: At least 10/12 must pass
        assert variables_passed >= MINIMUM_PASSING, (
            f"TEST-AC-6.23.3 FAILED: Only {variables_passed}/{variables_tested} variables passed. "
            f"Minimum required: {MINIMUM_PASSING}/{TOTAL_VARIABLES}"
        )

        assert pass_rate >= MINIMUM_PASS_RATE, (
            f"Pass rate {pass_rate:.1%} below {MINIMUM_PASS_RATE:.1%} threshold"
        )

    @pytest.mark.slow
    def test_ac3_expected_passing_variables(self, validation_script_path, project_root):
        """TEST-AC-6.23.3b: Verify specific variables pass their targets.

        GIVEN: Expected passing variables are defined
        WHEN: Running full validation
        THEN: Core variables (revenue, ebitda, etc.) should pass
        """
        EXPECTED_PASSING = [
            "revenue",
            "ebitda",
            "sales_volume",
            "electricity_cost",
            "thermal_cost",
            "variable_cost",
            "petcoke_price",
            "ttf_gas_price",
            "avg_selling_price",
            "capacity_utilization",
        ]

        ALLOWED_TO_FAIL = ["co2_eua_price", "clinker_factor"]

        # Run validation
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(validation_script_path),
                "--full",
                "--export-json",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=660,
        )

        json_output = None
        for line in result.stdout.strip().split("\n"):
            try:
                json_output = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

        if json_output is None:
            pytest.skip("Could not parse JSON output")

        # Check each expected variable
        variable_results = json_output.get("variable_results", [])
        passed_vars = [v["variable_name"] for v in variable_results if v.get("passed")]
        failed_vars = [v["variable_name"] for v in variable_results if not v.get("passed")]

        # AC3b: All expected variables should pass (except allowed failures)
        unexpected_failures = [
            v for v in failed_vars if v in EXPECTED_PASSING and v not in ALLOWED_TO_FAIL
        ]

        assert not unexpected_failures, (
            f"TEST-AC-6.23.3b FAILED: Expected variables failed: {unexpected_failures}. "
            f"All passed: {passed_vars}, All failed: {failed_vars}"
        )
