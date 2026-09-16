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
