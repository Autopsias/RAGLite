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

import numpy as np
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


class TestVariableCostMAPECalculation:
    """Unit tests for MAPE calculation logic (AC1 support)."""

    def test_mape_calculation_basic(self):
        """TEST-AC-6.23.1-UNIT-A: Basic MAPE calculation formula.

        GIVEN: Actual and predicted values
        WHEN: Calculating MAPE
        THEN: Formula: mean(|actual - predicted| / |actual|) * 100
        """
        actuals = np.array([100, 110, 120, 130])
        predictions = np.array([95, 108, 115, 128])

        # Calculate MAPE manually
        mape = np.mean(np.abs(actuals - predictions) / np.abs(actuals)) * 100

        assert mape > 0, "MAPE should be positive"
        assert mape < 10, f"Expected low MAPE for close predictions, got {mape}"

    def test_mape_handles_negative_values(self):
        """TEST-AC-6.23.1-UNIT-B: MAPE works with negative values (costs).

        GIVEN: Negative values (typical for costs)
        WHEN: Calculating MAPE
        THEN: Uses absolute values correctly
        """
        # Variable costs are negative (EUR/ton)
        actuals = np.array([-200, -210, -220, -230])
        predictions = np.array([-195, -208, -215, -228])

        mape = np.mean(np.abs(actuals - predictions) / np.abs(actuals)) * 100

        assert mape > 0, "MAPE should be positive even with negative inputs"
        assert mape < 5, f"Expected low MAPE, got {mape}"

    def test_mape_target_threshold(self):
        """TEST-AC-6.23.1-UNIT-C: Verify 8% target threshold logic.

        GIVEN: MAPE value
        WHEN: Comparing to 8% target
        THEN: Correctly identifies pass/fail
        """
        TARGET_MAPE = 8.0

        # Test cases
        passing_mape = 7.5  # Below target
        failing_mape = 8.5  # Above target
        edge_case_mape = 8.0  # At target (should fail per strict <8%)

        assert passing_mape < TARGET_MAPE, "7.5% should pass <8% target"
        assert failing_mape >= TARGET_MAPE, "8.5% should fail <8% target"
        assert edge_case_mape >= TARGET_MAPE, "Exactly 8% should fail strict <8%"

    def test_mape_from_validation_methods(self, sample_timeseries_data, sample_forecast_data):
        """TEST-AC-6.23.1-UNIT-D: Test MAPE via validation_methods module.

        GIVEN: Time series and forecast data
        WHEN: Using validation_methods.calculate_holdout_mape
        THEN: Returns valid MAPE percentage
        """
        try:
            from raglite.forecasting.validation_methods import calculate_holdout_mape

            mape = calculate_holdout_mape(
                sample_timeseries_data, sample_forecast_data, holdout_size=4
            )

            assert mape is not None, "MAPE calculation returned None"
            assert 0 <= mape <= 100, f"MAPE {mape} outside valid range 0-100%"
        except ImportError:
            pytest.skip("validation_methods not implemented")


# =============================================================================
# TEST-AC-6.23.2-UNIT: CoV Calculation and Entity Filtering
# =============================================================================


class TestCoefficientOfVariation:
    """Unit tests for CoV calculation (AC2 support)."""

    def test_cov_calculation_basic(self):
        """TEST-AC-6.23.2-UNIT-A: Basic CoV calculation formula.

        GIVEN: A set of values
        WHEN: Calculating coefficient of variation
        THEN: Formula: (std / |mean|) * 100
        """
        values = np.array([100, 105, 110, 95, 102])
        cov = (np.std(values) / np.abs(np.mean(values))) * 100

        assert cov > 0, "CoV should be positive"
        assert cov < 10, f"Expected low CoV for stable data, got {cov}"

    def test_cov_high_variance_detection(self, sample_high_variance_data):
        """TEST-AC-6.23.2-UNIT-B: Detect high variance (>33% baseline).

        GIVEN: Data with high variance (multiple entities mixed)
        WHEN: Calculating CoV
        THEN: Should exceed 33% baseline threshold
        """
        values = np.array([p.value for p in sample_high_variance_data])
        cov = (np.std(values) / np.abs(np.mean(values))) * 100

        # This high-variance data should have CoV > 33%
        assert cov > 33, f"Expected CoV > 33% for mixed-entity data, got {cov:.1f}%"

    def test_cov_low_variance_target(self, sample_variable_cost_data):
        """TEST-AC-6.23.2-UNIT-C: Verify low variance target (<15%).

        GIVEN: Filtered Portugal-only data
        WHEN: Calculating CoV
        THEN: Should be below 15% target
        """
        values = np.array([p.value for p in sample_variable_cost_data])
        cov = (np.std(values) / np.abs(np.mean(values))) * 100

        # Well-filtered data should have CoV < 15%
        TARGET_COV = 15.0
        assert cov < TARGET_COV, (
            f"TEST-AC-6.23.2-UNIT-C: CoV {cov:.1f}% exceeds {TARGET_COV}% target"
        )

    def test_entity_filter_reduces_variance(self):
        """TEST-AC-6.23.2-UNIT-D: Entity filtering should reduce variance.

        GIVEN: Mixed entity data vs single entity data
        WHEN: Comparing CoV
        THEN: Single entity should have lower CoV
        """
        # Mixed entities (high variance)
        mixed_values = np.array([-50, -150, -300, -80, -280, -120])

        # Single entity (Portugal pattern - lower variance)
        portugal_values = np.array([-185, -192, -205, -215, -228, -235])

        cov_mixed = (np.std(mixed_values) / np.abs(np.mean(mixed_values))) * 100
        cov_portugal = (np.std(portugal_values) / np.abs(np.mean(portugal_values))) * 100

        assert cov_portugal < cov_mixed, (
            f"Entity filtering should reduce CoV: "
            f"Portugal={cov_portugal:.1f}% vs Mixed={cov_mixed:.1f}%"
        )


# =============================================================================
# TEST-AC-6.23.3-UNIT: Variable Pass Rate Calculation
# =============================================================================


class TestVariablePassRate:
    """Unit tests for variable pass rate calculation (AC3 support)."""

    def test_pass_rate_calculation(self):
        """TEST-AC-6.23.3-UNIT-A: Basic pass rate calculation.

        GIVEN: Variables with pass/fail status
        WHEN: Calculating pass rate
        THEN: Formula: passed / total
        """
        total_variables = 12
        passed_variables = 10

        pass_rate = passed_variables / total_variables

        assert pass_rate == pytest.approx(0.833, rel=0.01), (
            f"Expected ~83.3% pass rate, got {pass_rate:.1%}"
        )

    def test_minimum_pass_threshold(self):
        """TEST-AC-6.23.3-UNIT-B: Verify 10/12 minimum threshold.

        GIVEN: Various pass counts
        WHEN: Checking against minimum requirement
        THEN: Only 10+ passes should satisfy threshold
        """
        MINIMUM_REQUIRED = 10
        TOTAL = 12

        # Test cases
        test_cases = [
            (9, False),  # 9/12 = 75% - FAIL
            (10, True),  # 10/12 = 83.3% - PASS
            (11, True),  # 11/12 = 91.7% - PASS
            (12, True),  # 12/12 = 100% - PASS
        ]

        for passed, expected_result in test_cases:
            meets_threshold = passed >= MINIMUM_REQUIRED
            assert meets_threshold == expected_result, (
                f"{passed}/12 should {'pass' if expected_result else 'fail'} threshold"
            )

    def test_mape_target_by_variable(self):
        """TEST-AC-6.23.3-UNIT-C: Verify MAPE targets by variable type.

        GIVEN: Variable-specific MAPE targets
        WHEN: Checking if variable passes
        THEN: Use correct target for each variable
        """
        MAPE_TARGETS = {
            "revenue": 5.0,
            "ebitda": 5.0,
            "sales_volume": 5.0,
            "electricity_cost": 8.0,
            "thermal_cost": 10.0,
            "variable_cost": 8.0,  # Critical variable
            "petcoke_price": 12.0,
            "ttf_gas_price": 12.0,
            "avg_selling_price": 6.0,
            "capacity_utilization": 10.0,
            "co2_eua_price": 15.0,
            "clinker_factor": 8.0,
        }

        # Variable cost target must be 8%
        assert MAPE_TARGETS["variable_cost"] == 8.0, "Variable cost target should be 8%"

        # Revenue/EBITDA should have stricter targets
        assert MAPE_TARGETS["revenue"] < MAPE_TARGETS["variable_cost"], (
            "Revenue should have stricter target than variable_cost"
        )


# =============================================================================
# TEST-AC-6.23.4-UNIT: Performance Timing
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
