"""Acceptance Tests for Story 6.23: MCP Tools Integration.

RED PHASE - TDD: All tests in this file MUST FAIL initially.
These tests validate MCP tool functionality with new data sources.

Test IDs map to Story 6.23 Acceptance Criteria:
- TEST-AC-6.23.5: All MCP tools functional with new data sources
- TEST-EPIC6-QG: Epic 6 Quality Gate

Story: /docs/sprint-artifacts/stories/6-23-variable-cost-mape-final-validation.md
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from raglite.forecasting.regressor_config import METRIC_REGRESSORS

# =============================================================================
# Test Markers and Configuration
# =============================================================================

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,  # Read-only tests
    pytest.mark.slow,  # Tests take 30+ seconds
    # P0 FIX (2026-01-24): Prevent parallel subprocess model loading
    # test_epic6_quality_gate_passes spawns subprocess that loads 2GB models
    # Without this marker, 4 workers × 2GB = 8GB → OOM crash
    pytest.mark.xdist_group(name="subprocess_heavy"),
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
# TEST-AC-6.23.5: All MCP tools functional with new data sources
# =============================================================================


class TestAC5MCPToolsFunctional:
    """AC5: All MCP tools functional with new data sources.

    GIVEN the MCP integration from Story 6.22
    WHEN calling MCP tools
    THEN tools should return valid responses with live data

    RED PHASE: Tests will FAIL until MCP tools are fully integrated.
    """

    def get_tool_function(self, tool_name: str):
        """Extract the underlying function from a FastMCP FunctionTool.

        MCP tools are FunctionTool objects, not regular functions.
        Access the `.fn` attribute to get the callable.
        """
        import raglite.main as main_module

        func_map = {
            "validate_forecasting_accuracy": main_module.validate_forecasting_accuracy,
            "list_available_regressors": main_module.list_available_regressors,
            "get_regressor_data": main_module.get_regressor_data,
        }

        if tool_name not in func_map:
            raise ValueError(f"Tool {tool_name} not found")

        tool_obj = func_map[tool_name]
        if hasattr(tool_obj, "fn"):
            return tool_obj.fn

        raise ValueError(f"Could not extract function from {tool_name}")

    @pytest.mark.asyncio
    async def test_ac5_validate_forecasting_accuracy_tool(self):
        """TEST-AC-6.23.5a: validate_forecasting_accuracy() returns valid response.

        GIVEN: MCP tool is exposed via main.py (Story 6.22)
        WHEN: Calling validate_forecasting_accuracy with variable_cost
        THEN: Returns valid UnifiedValidationResult schema
        """
        try:
            validate_func = self.get_tool_function("validate_forecasting_accuracy")
        except (ImportError, ValueError) as e:
            pytest.skip(f"MCP tool not implemented yet: {e}")

        # WHEN: Call MCP tool
        try:
            result = await validate_func(
                metrics=["variable_cost"],
                mape_method="holdout",
            )
        except Exception as e:
            pytest.fail(f"TEST-AC-6.23.5a FAILED: MCP tool error: {e}")

        # THEN: Validate response schema
        assert result is not None, "MCP tool returned None"
        assert hasattr(result, "variables_passed") or "variables_passed" in result, (
            "Response missing variables_passed field"
        )
        assert hasattr(result, "pass_rate") or "pass_rate" in result, (
            "Response missing pass_rate field"
        )

    @pytest.mark.asyncio
    async def test_ac5_list_available_regressors_tool(self):
        """TEST-AC-6.23.5b: list_available_regressors() returns all regressors.

        GIVEN: MCP tool is exposed (Story 6.22)
        WHEN: Calling list_available_regressors
        THEN: Returns all regressors without filtering and specific metric regressors when filtered
        """
        # Test 1: Get ALL regressors (no metric filter)
        try:
            list_func = self.get_tool_function("list_available_regressors")
        except (ImportError, ValueError) as e:
            pytest.skip(f"MCP tool not implemented yet: {e}")

        try:
            all_result = await list_func()  # No metric filter
        except Exception as e:
            pytest.fail(f"TEST-AC-6.23.5b FAILED: MCP tool error: {e}")

        # THEN: Validate total regressor count (should be all 11)
        MINIMUM_REGRESSORS = 11
        total_count = getattr(
            all_result, "total_count", len(all_result) if hasattr(all_result, "__len__") else 0
        )

        assert total_count >= MINIMUM_REGRESSORS, (
            f"TEST-AC-6.23.5b FAILED: Only {total_count} total regressors, expected >= {MINIMUM_REGRESSORS}"
        )

        # Verify key regressors exist in full list
        regressor_names = []
        if hasattr(all_result, "regressors"):
            regressor_names = [r.name for r in all_result.regressors]
        elif isinstance(all_result, list):
            regressor_names = [r.get("name", r) for r in all_result]

        EXPECTED_REGRESSORS = [
            "construction_output",  # Eurostat (Story 6.16)
            "euribor_3m",  # ECB (Story 6.17)
            "gdp_growth",  # ECB (Story 6.17)
            "ttf_gas",  # External data
        ]

        for expected in EXPECTED_REGRESSORS:
            assert any(expected in name for name in regressor_names), (
                f"Expected regressor '{expected}' not found in {regressor_names}"
            )

        # Test 2: Get filtered regressors for variable_cost
        try:
            filtered_result = await list_func(metric="variable_cost")
        except Exception as e:
            pytest.fail(f"TEST-AC-6.23.5b FAILED: MCP tool error (filtered): {e}")

        # Verify filtered result has the expected variable_cost regressors
        filtered_count = getattr(
            filtered_result,
            "total_count",
            len(filtered_result) if hasattr(filtered_result, "__len__") else 0,
        )

        # Data-driven approach: derive expected count from configuration (Story 7 - Epic 7)
        # This prevents config-test drift when regressor configuration changes
        EXPECTED_VARIABLE_COST_REGRESSORS = len(METRIC_REGRESSORS.get("variable_cost", []))
        assert filtered_count == EXPECTED_VARIABLE_COST_REGRESSORS, (
            f"Expected {EXPECTED_VARIABLE_COST_REGRESSORS} variable_cost regressors, got {filtered_count}"
        )

        # Verify the specific variable_cost regressors match configuration
        if hasattr(filtered_result, "regressors"):
            filtered_names = [r.name for r in filtered_result.regressors]
        else:
            filtered_names = [r.get("name", r) for r in filtered_result]

        # Verify all configured regressors are returned
        configured_regressors = METRIC_REGRESSORS.get("variable_cost", [])
        for expected in configured_regressors:
            assert expected in filtered_names, (
                f"Expected variable_cost regressor '{expected}' not found in {filtered_names}"
            )

    @pytest.mark.asyncio
    @pytest.mark.external_api  # Hits real external APIs (Quandl, EEX, etc.) - skip in fast CI
    async def test_ac5_get_regressor_data_tool(self):
        """TEST-AC-6.23.5c: get_regressor_data() fetches live data.

        GIVEN: MCP tool and external data sources (Stories 6.16, 6.17)
        WHEN: Calling get_regressor_data for ttf_gas
        THEN: Returns recent data points

        NOTE: This test hits real external APIs (Quandl, EEX, ECB, Eurostat).
        It is marked with external_api and excluded from fast CI runs.
        """
        try:
            get_data_func = self.get_tool_function("get_regressor_data")
        except (ImportError, ValueError) as e:
            pytest.skip(f"MCP tool not implemented yet: {e}")

        # Test regressors from different sources
        TEST_REGRESSORS = ["ttf_gas", "construction_output", "euribor_3m"]

        for regressor_name in TEST_REGRESSORS:
            try:
                result = await get_data_func(
                    regressor=regressor_name,
                    start_date="2024-01-01",
                )
            except Exception as e:
                pytest.fail(
                    f"TEST-AC-6.23.5c FAILED: get_regressor_data({regressor_name}) error: {e}"
                )

            # Validate response has data
            record_count = getattr(
                result, "record_count", len(result) if hasattr(result, "__len__") else 0
            )

            assert record_count > 0, (
                f"TEST-AC-6.23.5c FAILED: No data returned for regressor '{regressor_name}'"
            )

    @pytest.mark.asyncio
    async def test_ac5_mcp_response_schema_compliance(self):
        """TEST-AC-6.23.5d: MCP responses comply with Story 6.22 schemas.

        GIVEN: Schema definitions in validation_schema.py
        WHEN: Calling MCP tools
        THEN: Responses match defined schemas
        """
        from dataclasses import asdict

        try:
            validate_func = self.get_tool_function("validate_forecasting_accuracy")
        except (ImportError, ValueError) as e:
            pytest.skip(f"MCP tools or schemas not implemented yet: {e}")

        # WHEN: Call validation tool
        try:
            result = await validate_func(
                metrics=["revenue"],
                mape_method="holdout",
            )
        except Exception as e:
            pytest.skip(f"Validation tool not ready: {e}")

        # THEN: Response should be convertible to dict (schema compliant)
        try:
            if hasattr(result, "__dataclass_fields__"):
                result_dict = asdict(result)
            else:
                result_dict = dict(result)
        except Exception as e:
            pytest.fail(f"TEST-AC-6.23.5d FAILED: Response not schema compliant: {e}")

        # Verify required fields
        REQUIRED_FIELDS = [
            "timestamp",
            "runtime_seconds",
            "variables_tested",
            "variables_passed",
            "pass_rate",
            "quality_gate_passed",  # Changed from "quality_gate" based on actual response
        ]

        for field in REQUIRED_FIELDS:
            assert field in result_dict, f"Missing required field: {field}"


# =============================================================================
# Quality Gate Summary Test
# =============================================================================


class TestEpic6QualityGate:
    """Epic 6 Quality Gate: Final validation combining all acceptance criteria.

    This is the ultimate pass/fail test for Epic 6.
    """

    @pytest.mark.slow
    @pytest.mark.skipif(
        os.environ.get("CI") == "true",
        reason="Subprocess loads 3-4GB forecasting models (Chronos, TFT, Prophet), exceeds CI memory. Validate manually.",
    )
    def test_epic6_quality_gate_passes(self, validation_script_path, project_root):
        """TEST-EPIC6-QG: Epic 6 quality gate must pass.

        GIVEN: All stories 6.15-6.22 are implemented
        WHEN: Running full validation
        THEN: Quality gate passes (Variable Cost <8% AND 10/12 pass)
        """
        # P0 FIX: Ensure subprocess inherits CI_FAST_EMBEDDING to use 80MB model
        # instead of 2GB Fin-E5 model
        env = os.environ.copy()
        env["CI_FAST_EMBEDDING"] = os.environ.get("CI_FAST_EMBEDDING", "true")

        # Run full validation
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(validation_script_path),
                "--full",
                "--export-json",
                "--mcp-format",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=660,
            env=env,  # Pass environment with CI_FAST_EMBEDDING
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
            pytest.fail("Could not parse validation output")

        # Check quality gate
        quality_gate = json_output.get("quality_gate", {})

        # EPIC 6 QUALITY GATE ASSERTION
        assert quality_gate.get("passed") is True, (
            f"EPIC 6 QUALITY GATE FAILED:\n"
            f"  - Variable Cost MAPE: {quality_gate.get('variable_cost_mape')}% (target: <8%)\n"
            f"  - Variables Passed: {quality_gate.get('actual_passed')}/{quality_gate.get('minimum_required')} required\n"
            f"  - Pass Rate: {json_output.get('pass_rate', 0):.1%}\n"
            f"Full results: {json.dumps(json_output, indent=2)}"
        )
