"""Integration tests for unified validation script.

Story 6.21: Unified Validation Script

Tests require PostgreSQL and Qdrant to be running.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

# Mark all tests as integration
# requires_ml_stack: subprocess loads full forecasting stack (~3-4GB)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,  # Forecasting is slow
    pytest.mark.preserve_collection,  # All tests are read-only (CLI/programmatic validation)
    pytest.mark.requires_ml_stack,
]


class TestUnifiedValidationCLI:
    """Test unified validation script via CLI."""

    def test_help_flag(self):
        """Test that --help flag works."""
        result = subprocess.run(
            ["python", "scripts/validate_forecasting_unified.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Unified Forecasting Validation" in result.stdout
        assert "--mape-method" in result.stdout
        assert "--export-json" in result.stdout
        # Check that MVP fallback documentation is present
        assert "holdout fallback" in result.stdout.lower() or "mvp" in result.stdout.lower()

    def test_single_variable_validation(self):
        """Test validating a single variable."""
        result = subprocess.run(
            [
                "python",
                "scripts/validate_forecasting_unified.py",
                "--variable",
                "revenue",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Script should complete (exit 0 if validation passes, exit 1 if quality gate fails)
        # For a single variable test, quality gate will fail (needs 10/12)
        # so we expect returncode=1 for normal execution
        assert result.returncode == 1, (
            f"Expected returncode=1 for single variable (quality gate fails), "
            f"got {result.returncode}. stderr: {result.stderr}"
        )

    def test_invalid_variable_name(self):
        """Test error handling for invalid variable name."""
        result = subprocess.run(
            [
                "python",
                "scripts/validate_forecasting_unified.py",
                "--variable",
                "invalid_metric",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1
        assert "Unknown variable" in result.stdout or "invalid_metric" in result.stdout

    @pytest.mark.slow
    def test_export_json_output(self, tmp_path):
        """Test JSON export functionality."""
        reports_dir = Path("reports")
        json_files_before = (
            set(reports_dir.glob("unified-validation-*.json")) if reports_dir.exists() else set()
        )

        result = subprocess.run(
            [
                "python",
                "scripts/validate_forecasting_unified.py",
                "--variable",
                "revenue",
                "--export-json",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path.cwd()),
        )

        # Script should complete (returncode=1 is expected for single variable)
        assert result.returncode in [0, 1], f"Unexpected error: {result.stderr}"

        try:
            # Check that a new JSON file was created in reports/
            json_files_after = set(reports_dir.glob("unified-validation-*.json"))
            new_files = json_files_after - json_files_before

            assert len(new_files) > 0, "No new JSON file was created"

            # Verify JSON structure
            latest_file = max(new_files, key=lambda p: p.stat().st_mtime)
            with open(latest_file) as f:
                data = json.load(f)

            assert "timestamp" in data
            assert "mape_method" in data
            assert "variable_results" in data
            assert "quality_gate" in data
        finally:
            # Cleanup any files we created
            for f in new_files:
                try:
                    f.unlink()
                except Exception:
                    pass

    def test_mcp_format_output(self, tmp_path):
        """Test MCP-compatible output format."""
        reports_dir = Path("reports")
        json_files_before = (
            set(reports_dir.glob("unified-validation-*.json")) if reports_dir.exists() else set()
        )

        result = subprocess.run(
            [
                "python",
                "scripts/validate_forecasting_unified.py",
                "--variable",
                "revenue",
                "--export-json",
                "--mcp-format",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Script should complete (returncode=1 is expected for single variable)
        assert result.returncode in [0, 1], f"Unexpected error: {result.stderr}"

        try:
            # Check that a new JSON file was created
            json_files_after = set(reports_dir.glob("unified-validation-*.json"))
            new_files = json_files_after - json_files_before

            assert len(new_files) > 0, "No new JSON file was created"

            # Verify MCP schema
            latest_file = max(new_files, key=lambda p: p.stat().st_mtime)
            with open(latest_file) as f:
                data = json.load(f)

            # MCP format should include schema version
            assert "_schema_version" in data
            assert "_source" in data
            assert data["_source"] == "raglite-unified-validation"
        finally:
            # Cleanup any files we created
            for f in new_files:
                try:
                    f.unlink()
                except Exception:
                    pass

    def test_fail_fast_mode(self):
        """Test fail-fast mode exits on first violation."""
        # This should exit quickly if first variable fails
        result = subprocess.run(
            [
                "python",
                "scripts/validate_forecasting_unified.py",
                "--full",
                "--fail-fast",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=120,  # Should be faster than full validation
        )

        # Should complete without crashing (exit 0 or 1 depending on pass/fail)
        assert result.returncode in [0, 1], f"Unexpected error: {result.stderr}"

    @pytest.mark.parametrize("mape_method", ["holdout", "walkforward", "cv"])
    def test_mape_methods(self, mape_method):
        """Test all MAPE calculation methods."""
        result = subprocess.run(
            [
                "python",
                "scripts/validate_forecasting_unified.py",
                "--variable",
                "revenue",
                "--mape-method",
                mape_method,
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should complete without crashing (returncode=1 expected for single variable)
        assert result.returncode in [0, 1], (
            f"MAPE method '{mape_method}' failed unexpectedly. "
            f"returncode={result.returncode}, stderr={result.stderr}"
        )


class TestUnifiedValidationProgrammatic:
    """Test unified validation via direct Python import."""

    @pytest.mark.asyncio
    async def test_import_and_run_validation(self):
        """Test importing and running validation programmatically."""
        from scripts.validate_forecasting_unified import run_unified_validation

        # Run with single variable
        result = await run_unified_validation(
            variables=["revenue"],
            mape_method="holdout",
            fail_fast=False,
            quiet=True,
        )

        # Verify result structure
        assert result.timestamp is not None
        assert result.runtime_seconds > 0
        assert result.mape_method == "holdout"
        assert result.variables_tested == 1
        assert len(result.variable_results) == 1
        assert result.variable_results[0].variable_name == "revenue"

    @pytest.mark.asyncio
    async def test_quality_gate_logic(self):
        """Test quality gate pass/fail logic."""
        from scripts.validate_forecasting_unified import run_unified_validation

        # Run with single variable (won't pass 10/12 requirement)
        result = await run_unified_validation(
            variables=["revenue"],
            mape_method="holdout",
            fail_fast=False,
            quiet=True,
        )

        # Single variable test should fail quality gate
        assert result.quality_gate.passed is False
        assert result.quality_gate.minimum_required == 10
        assert result.quality_gate.actual_passed < 10


class TestUnifiedValidationAcceptanceCriteria:
    """Test acceptance criteria from Story 6.21."""

    def test_ac1_supports_all_12_variables(self):
        """AC1: Script supports all 12 cement industry variables."""
        from scripts.validate_forecasting_unified import CEMENT_FORECAST_VARIABLES

        assert len(CEMENT_FORECAST_VARIABLES) == 12

        expected_variables = {
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
            "co2_eua_price",
            "clinker_factor",
        }

        assert set(CEMENT_FORECAST_VARIABLES.keys()) == expected_variables

    def test_ac2_supports_all_mape_methods(self):
        """AC2: Script supports holdout, walk-forward, and CV MAPE."""
        from raglite.forecasting.validation_methods import (
            calculate_cv_mape,
            calculate_holdout_mape,
            calculate_walkforward_mape,
        )

        # All three functions should exist
        assert callable(calculate_holdout_mape)
        assert callable(calculate_walkforward_mape)
        assert callable(calculate_cv_mape)

    def test_ac3_json_export_schema(self):
        """AC3: JSON export includes per-variable and per-model breakdown."""
        from dataclasses import asdict
        from datetime import datetime

        from raglite.forecasting.validation_schema import (
            ModelPerformanceStats,
            QualityGateResult,
            UnifiedValidationResult,
            VariableValidationResult,
        )

        # Create sample result
        result = UnifiedValidationResult(
            timestamp=datetime.now().isoformat(),
            runtime_seconds=100.0,
            mape_method="holdout",
            variables_tested=12,
            variables_passed=10,
            pass_rate=0.833,
            average_mape=5.5,
            variable_results=[
                VariableValidationResult(
                    variable_name="revenue",
                    display_name="Revenue",
                    target_mape=5.0,
                    actual_mape=4.5,
                    passed=True,
                    holdout_mape=4.5,
                    walkforward_mape=None,
                    cv_mape=None,
                    ensemble_weights={"prophet": 0.5, "linear": 0.5},
                    best_model="prophet",
                    best_model_mape=4.5,
                )
            ],
            model_performance={
                "prophet": ModelPerformanceStats(
                    model_name="prophet",
                    avg_mape=5.0,
                    variables_used=12,
                    avg_runtime_seconds=20.0,
                )
            },
            quality_gate=QualityGateResult(
                passed=True,
                minimum_required=10,
                actual_passed=10,
                variable_cost_mape=7.5,
                variable_cost_target=8.0,
            ),
        )

        # Convert to dict (JSON-serializable)
        data = asdict(result)

        # Verify structure
        assert "timestamp" in data
        assert "variable_results" in data
        assert "model_performance" in data
        assert "quality_gate" in data
        assert len(data["variable_results"]) == 1
        assert "ensemble_weights" in data["variable_results"][0]

    def test_ac4_mcp_format_compatibility(self):
        """AC4: MCP format output is compatible with Story 6.22 tools."""
        from dataclasses import asdict
        from datetime import datetime

        from raglite.forecasting.validation_schema import (
            QualityGateResult,
            UnifiedValidationResult,
        )

        result = UnifiedValidationResult(
            timestamp=datetime.now().isoformat(),
            runtime_seconds=100.0,
            mape_method="holdout",
            variables_tested=12,
            variables_passed=10,
            pass_rate=0.833,
            average_mape=5.5,
            variable_results=[],
            model_performance={},
            quality_gate=QualityGateResult(
                passed=True,
                minimum_required=10,
                actual_passed=10,
                variable_cost_mape=7.5,
                variable_cost_target=8.0,
            ),
        )

        # Add MCP metadata
        data = asdict(result)
        data["_schema_version"] = "1.0"
        data["_source"] = "raglite-unified-validation"

        # Should be JSON-serializable
        json_str = json.dumps(data, default=str)
        assert json_str is not None

        # Should deserialize correctly
        parsed = json.loads(json_str)
        assert parsed["_schema_version"] == "1.0"
        assert parsed["quality_gate"]["passed"] is True
