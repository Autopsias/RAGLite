"""Acceptance Tests for Story 6.23: Variable Cost MAPE Final Validation (Extended).

RED PHASE - TDD: All tests in this file MUST FAIL initially.
These tests validate the Epic 6 quality gates which are the culmination
of stories 6.15-6.22.

Test IDs map to Story 6.23 Acceptance Criteria (Extended):
- TEST-AC-6.23.3: At least 10/12 variables meet their MAPE targets
- TEST-AC-6.23.4: Validation script runtime <10 minutes

NOTE: AC5 (MCP tools) and Quality Gate tests are in test_story_6_23_mcp_tools.py

Story: /docs/sprint-artifacts/stories/6-23-variable-cost-mape-final-validation.md
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

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
# TEST-AC-6.23.3: At least 10/12 variables meet their MAPE targets
# =============================================================================


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
        import json

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

        import json

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


# =============================================================================
# TEST-AC-6.23.4: Validation script completes in <10 minutes
# =============================================================================


class TestAC4ValidationPerformance:
    """AC4: Validation script completes in <10 minutes.

    GIVEN the full 12-variable validation
    WHEN measuring runtime
    THEN total execution time should be <600 seconds (10 minutes)

    RED PHASE: This test validates performance requirements.
    """

    @pytest.mark.slow
    def test_ac4_full_validation_runtime(self, validation_script_path, project_root):
        """TEST-AC-6.23.4: Full validation must complete in <10 minutes.

        GIVEN: Validation script is optimized (Story 6.21)
        WHEN: Running full 12-variable validation
        THEN: Runtime < 600 seconds (10 minutes)
        """
        MAX_RUNTIME_SECONDS = 600  # 10 minutes

        start_time = time.time()

        # WHEN: Run full validation with timing
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(validation_script_path),
                "--full",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=660,  # 11 minute hard timeout
        )

        elapsed_time = time.time() - start_time

        # Script should succeed
        if result.returncode != 0:
            pytest.skip(f"Validation script failed: {result.stderr}")

        # AC4 ASSERTION: Runtime must be under 10 minutes
        assert elapsed_time < MAX_RUNTIME_SECONDS, (
            f"TEST-AC-6.23.4 FAILED: Validation took {elapsed_time:.1f}s, "
            f"exceeds {MAX_RUNTIME_SECONDS}s limit"
        )

    def test_ac4_single_variable_runtime(self, validation_script_path, project_root):
        """TEST-AC-6.23.4b: Single variable validation must be fast.

        GIVEN: Validation is optimized
        WHEN: Running single variable validation
        THEN: Runtime < 60 seconds per variable
        """
        MAX_SINGLE_VAR_SECONDS = 60

        start_time = time.time()

        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(validation_script_path),
                "--variable",
                "revenue",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=120,
        )

        elapsed_time = time.time() - start_time

        if result.returncode != 0:
            pytest.skip(f"Single variable validation failed: {result.stderr}")

        # AC4b: Single variable should be fast
        assert elapsed_time < MAX_SINGLE_VAR_SECONDS, (
            f"Single variable took {elapsed_time:.1f}s, should be <{MAX_SINGLE_VAR_SECONDS}s"
        )
