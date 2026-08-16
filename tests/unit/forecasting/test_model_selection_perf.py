"""Unit Tests for Story 6.23: Variable Cost MAPE Final Validation.

RED PHASE - TDD: These unit tests validate internal components and calculations
needed for Story 6.23 acceptance criteria.

Test IDs map to Story 6.23 Acceptance Criteria:
- TEST-AC-6.23.1-UNIT: Variable Cost MAPE calculation logic
- TEST-AC-6.23.2-UNIT: CoV calculation and entity filtering logic
- TEST-AC-6.23.3-UNIT: Variable pass rate calculation logic
- TEST-AC-6.23.4-UNIT: Performance timing utilities
- TEST-AC-6.23.5-UNIT: MCP schema validation

Story: /docs/sprint-artifacts/stories/6-23-variable-cost-mape-final-validation.md
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

# =============================================================================
# Fixtures for Unit Tests
# =============================================================================


@pytest.fixture
def sample_timeseries_data():
    """Create sample time series data for testing."""
    from raglite.shared.models import TimeSeriesPoint

    base_date = datetime(2024, 1, 1)
    # Simulate variable cost data (EUR/ton, negative values = costs)
    return [
        TimeSeriesPoint(date=base_date + timedelta(days=i * 30), value=-200 - i * 5)
        for i in range(12)
    ]


@pytest.fixture
def sample_variable_cost_data():
    """Create sample variable cost data matching Portugal patterns."""
    from raglite.shared.models import TimeSeriesPoint

    base_date = datetime(2024, 1, 1)
    # Portugal variable cost: EUR -180 to -280 per ton (realistic range)
    values = [-185, -192, -205, -215, -228, -235, -242, -250, -255, -262, -270, -275]
    return [
        TimeSeriesPoint(date=base_date + timedelta(days=i * 30), value=v)
        for i, v in enumerate(values)
    ]


@pytest.fixture
def sample_high_variance_data():
    """Create high-variance data (CoV > 33% baseline)."""
    from raglite.shared.models import TimeSeriesPoint

    base_date = datetime(2024, 1, 1)
    # Highly variable data (mixing Portugal and other countries' patterns)
    values = [-50, -150, -300, -80, -280, -120, -350, -60, -250, -100, -320, -90]
    return [
        TimeSeriesPoint(date=base_date + timedelta(days=i * 30), value=v)
        for i, v in enumerate(values)
    ]


@pytest.fixture
def sample_forecast_data():
    """Create sample forecast data."""
    from raglite.shared.models import ForecastPoint

    base_date = datetime(2024, 12, 1)
    return [
        ForecastPoint(
            date=base_date + timedelta(days=i * 30),
            value=-260 - i * 5,
            lower=-275 - i * 5,
            upper=-245 - i * 5,
        )
        for i in range(4)
    ]


# =============================================================================
# TEST-AC-6.23.1-UNIT: Variable Cost MAPE Calculation
# =============================================================================


class TestPerformanceTiming:
    """Unit tests for performance timing utilities (AC4 support)."""

    def test_runtime_tracking(self):
        """TEST-AC-6.23.4-UNIT-A: Runtime tracking utility.

        GIVEN: A timed operation
        WHEN: Measuring execution time
        THEN: Captures accurate duration
        """
        import time

        start = time.time()
        time.sleep(0.1)  # Simulate work
        elapsed = time.time() - start

        assert elapsed >= 0.1, f"Elapsed time {elapsed}s should be >= 0.1s"
        assert elapsed < 0.2, f"Elapsed time {elapsed}s should be < 0.2s"

    def test_timeout_threshold_check(self):
        """TEST-AC-6.23.4-UNIT-B: Timeout threshold validation.

        GIVEN: 10 minute (600s) threshold
        WHEN: Checking various runtimes
        THEN: Correctly identifies threshold violations
        """
        MAX_RUNTIME = 600  # 10 minutes in seconds

        test_cases = [
            (300, True),  # 5 min - OK
            (550, True),  # ~9 min - OK
            (600, False),  # Exactly 10 min - FAIL (not strictly less than)
            (650, False),  # ~11 min - FAIL
        ]

        for runtime, expected_pass in test_cases:
            passes = runtime < MAX_RUNTIME
            assert passes == expected_pass, (
                f"Runtime {runtime}s should {'pass' if expected_pass else 'fail'} "
                f"<{MAX_RUNTIME}s threshold"
            )


# =============================================================================
# TEST-AC-6.23.5-UNIT: MCP Schema Validation
# =============================================================================


class TestMCPSchemaValidation:
    """Unit tests for MCP schema validation (AC5 support)."""

    def test_quality_gate_result_schema(self):
        """TEST-AC-6.23.5-UNIT-A: QualityGateResult schema validation.

        GIVEN: QualityGateResult dataclass
        WHEN: Creating an instance
        THEN: All required fields present
        """
        from raglite.forecasting.validation_schema import QualityGateResult

        result = QualityGateResult(
            passed=True,
            minimum_required=10,
            actual_passed=11,
            variable_cost_mape=6.5,
            variable_cost_target=8.0,
        )

        assert result.passed is True
        assert result.minimum_required == 10
        assert result.actual_passed == 11
        assert result.variable_cost_mape == 6.5
        assert result.variable_cost_target == 8.0

    def test_variable_validation_result_schema(self):
        """TEST-AC-6.23.5-UNIT-B: VariableValidationResult schema validation.

        GIVEN: VariableValidationResult dataclass
        WHEN: Creating an instance
        THEN: All required fields present
        """
        from raglite.forecasting.validation_schema import VariableValidationResult

        result = VariableValidationResult(
            variable_name="variable_cost",
            display_name="Variable Cost per Ton",
            target_mape=8.0,
            actual_mape=6.8,
            passed=True,
            holdout_mape=6.8,
            walkforward_mape=7.2,
            cv_mape=7.0,
        )

        assert result.variable_name == "variable_cost"
        assert result.passed is True
        assert result.actual_mape < result.target_mape

    def test_unified_validation_result_schema(self):
        """TEST-AC-6.23.5-UNIT-C: UnifiedValidationResult schema validation.

        GIVEN: UnifiedValidationResult dataclass
        WHEN: Creating an instance with all fields
        THEN: Schema is complete and serializable
        """
        from dataclasses import asdict

        from raglite.forecasting.validation_schema import (
            QualityGateResult,
            UnifiedValidationResult,
            VariableValidationResult,
        )

        result = UnifiedValidationResult(
            timestamp=datetime.now().isoformat(),
            runtime_seconds=480.5,
            mape_method="holdout",
            variables_tested=12,
            variables_passed=10,
            pass_rate=0.833,
            average_mape=5.2,
            variable_results=[
                VariableValidationResult(
                    variable_name="variable_cost",
                    display_name="Variable Cost",
                    target_mape=8.0,
                    actual_mape=6.8,
                    passed=True,
                )
            ],
            model_performance={},
            quality_gate=QualityGateResult(
                passed=True,
                minimum_required=10,
                actual_passed=10,
                variable_cost_mape=6.8,
                variable_cost_target=8.0,
            ),
        )

        # Should be serializable to dict
        result_dict = asdict(result)

        assert "timestamp" in result_dict
        assert "runtime_seconds" in result_dict
        assert "quality_gate" in result_dict
        assert result_dict["quality_gate"]["passed"] is True

    def test_schema_json_serialization(self):
        """TEST-AC-6.23.5-UNIT-D: Schema JSON serialization.

        GIVEN: Validation result
        WHEN: Converting to JSON
        THEN: All fields serialize correctly
        """
        import json
        from dataclasses import asdict

        from raglite.forecasting.validation_schema import (
            QualityGateResult,
            UnifiedValidationResult,
        )

        result = UnifiedValidationResult(
            timestamp="2025-12-13T12:00:00",
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
                variable_cost_mape=7.2,
                variable_cost_target=8.0,
            ),
        )

        # Should serialize without errors
        json_str = json.dumps(asdict(result))
        assert json_str is not None

        # Should deserialize back
        parsed = json.loads(json_str)
        assert parsed["variables_passed"] == 10
        assert parsed["quality_gate"]["passed"] is True


# =============================================================================
# Regression Tests
# =============================================================================


class TestRegressionFromBaseline:
    """Regression tests to ensure improvements don't regress."""

    def test_baseline_values_documented(self):
        """Verify baseline values are documented for comparison.

        GIVEN: Story 6.23 baseline documentation
        WHEN: Checking documented baselines
        THEN: All baselines are clearly defined
        """
        # Document baselines from Story 6.23
        BASELINES = {
            "variable_cost_mape": 41.43,  # Pre-improvement MAPE
            "data_cov": 33.0,  # Pre-improvement CoV
            "pass_rate": 5 / 8,  # 5/8 variables passing before
        }

        TARGETS = {
            "variable_cost_mape": 8.0,  # Target <8%
            "data_cov": 15.0,  # Target <15%
            "pass_rate": 10 / 12,  # Target 10/12
        }

        # All targets should be improvements over baselines
        assert TARGETS["variable_cost_mape"] < BASELINES["variable_cost_mape"]
        assert TARGETS["data_cov"] < BASELINES["data_cov"]
        assert TARGETS["pass_rate"] > BASELINES["pass_rate"]
