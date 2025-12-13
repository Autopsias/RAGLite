"""Unit tests for unified validation script.

Story 6.21: Unified Validation Script

Tests cover:
- MAPE calculation methods (holdout, walk-forward, CV)
- CLI argument parsing
- MCP schema output format
- Data structures and serialization
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

import pytest

# Import from new module locations
from raglite.forecasting.validation_methods import (
    calculate_cv_mape,
    calculate_holdout_mape,
    calculate_walkforward_mape,
)
from raglite.forecasting.validation_schema import (
    ModelPerformanceStats,
    QualityGateResult,
    UnifiedValidationResult,
    VariableValidationResult,
)

# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_timeseries_points():
    """Create sample time series data for testing."""
    from datetime import timedelta

    from raglite.shared.models import TimeSeriesPoint

    base_date = datetime(2024, 1, 1)
    return [
        TimeSeriesPoint(date=base_date + timedelta(days=i * 30), value=100 + i * 5)
        for i in range(12)
    ]


@pytest.fixture
def sample_forecast_points():
    """Create sample forecast data for testing."""
    from datetime import timedelta

    from raglite.shared.models import ForecastPoint

    base_date = datetime(2024, 12, 1)
    return [
        ForecastPoint(
            date=base_date + timedelta(days=i * 30),
            value=160 + i * 3,
            lower=150 + i * 3,
            upper=170 + i * 3,
        )
        for i in range(4)
    ]


# =============================================================================
# MAPE Calculation Tests
# =============================================================================


class TestHoldoutMAPE:
    """Test holdout MAPE calculation."""

    def test_calculate_holdout_mape_basic(self, sample_timeseries_points, sample_forecast_points):
        """Test basic holdout MAPE calculation."""
        mape = calculate_holdout_mape(
            sample_timeseries_points, sample_forecast_points, holdout_size=4
        )

        assert mape is not None
        assert isinstance(mape, float)
        assert 0 <= mape <= 100  # MAPE is a percentage

    def test_calculate_holdout_mape_insufficient_data(self, sample_timeseries_points):
        """Test holdout MAPE with insufficient forecast data."""
        # Only 2 forecast points when we need 4
        short_forecast = sample_timeseries_points[:2]
        mape = calculate_holdout_mape(sample_timeseries_points, short_forecast, holdout_size=4)

        assert mape is None

    def test_calculate_holdout_mape_perfect_forecast(self):
        """Test holdout MAPE with perfect predictions."""
        from datetime import timedelta

        from raglite.shared.models import ForecastPoint, TimeSeriesPoint

        base = datetime(2024, 1, 1)
        historical = [
            TimeSeriesPoint(date=base + timedelta(days=i * 30), value=100.0) for i in range(8)
        ]
        forecast = [
            ForecastPoint(date=base + timedelta(days=i * 30), value=100.0, lower=95.0, upper=105.0)
            for i in range(4)
        ]

        mape = calculate_holdout_mape(historical, forecast, holdout_size=4)

        assert mape is not None
        assert mape < 0.1  # Near-perfect forecast


class TestWalkForwardMAPE:
    """Test walk-forward MAPE calculation."""

    def test_calculate_walkforward_mape_basic(self, sample_timeseries_points):
        """Test basic walk-forward MAPE calculation."""
        from raglite.shared.models import ForecastPoint

        # Mock forecast function
        def mock_forecast(data, periods_ahead):
            last_value = data[-1].value
            return [ForecastPoint(date=data[-1].date, value=last_value + 5, lower=0, upper=0)]

        mape = calculate_walkforward_mape(
            sample_timeseries_points, mock_forecast, test_periods=4, step_size=1
        )

        assert mape is not None
        assert isinstance(mape, float)
        assert 0 <= mape <= 100

    def test_calculate_walkforward_mape_insufficient_data(self):
        """Test walk-forward MAPE with insufficient data."""
        from raglite.shared.models import TimeSeriesPoint

        short_data = [TimeSeriesPoint(date=datetime(2024, i, 1), value=100.0) for i in range(1, 4)]

        def mock_forecast(data, periods_ahead):
            return []

        mape = calculate_walkforward_mape(short_data, mock_forecast, test_periods=4, step_size=1)

        # Should handle gracefully (return None or skip)
        assert mape is None or mape >= 0


class TestCrossValidationMAPE:
    """Test cross-validation MAPE calculation."""

    def test_calculate_cv_mape_basic(self, sample_timeseries_points):
        """Test basic CV MAPE calculation."""
        from raglite.shared.models import ForecastPoint

        def mock_forecast(data, periods_ahead):
            last_value = data[-1].value if data else 100
            return [
                ForecastPoint(date=data[-1].date, value=last_value + 5, lower=0, upper=0)
                for _ in range(periods_ahead)
            ]

        mape = calculate_cv_mape(sample_timeseries_points, mock_forecast, n_splits=3)

        assert mape is not None
        assert isinstance(mape, float)
        assert 0 <= mape <= 100

    def test_calculate_cv_mape_with_splits(self, sample_timeseries_points):
        """Test CV MAPE with different split configurations."""
        from raglite.shared.models import ForecastPoint

        def mock_forecast(data, periods_ahead):
            last_value = data[-1].value if data else 100
            return [
                ForecastPoint(date=data[-1].date, value=last_value, lower=0, upper=0)
                for _ in range(periods_ahead)
            ]

        mape_3splits = calculate_cv_mape(sample_timeseries_points, mock_forecast, n_splits=3)
        mape_5splits = calculate_cv_mape(sample_timeseries_points, mock_forecast, n_splits=5)

        assert mape_3splits is not None
        assert mape_5splits is not None
        # More splits shouldn't drastically change MAPE for consistent forecast
        assert abs(mape_3splits - mape_5splits) < 50  # Reasonable tolerance


# =============================================================================
# Data Structure Tests
# =============================================================================


class TestUnifiedValidationResult:
    """Test UnifiedValidationResult dataclass."""

    def test_create_validation_result(self):
        """Test creating a validation result."""
        result = UnifiedValidationResult(
            timestamp=datetime.now().isoformat(),
            runtime_seconds=120.5,
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

        assert result.variables_tested == 12
        assert result.variables_passed == 10
        assert result.pass_rate == pytest.approx(0.833, rel=0.01)
        assert result.quality_gate.passed is True

    def test_validation_result_to_dict(self):
        """Test converting validation result to dict for JSON export."""
        result = UnifiedValidationResult(
            timestamp=datetime.now().isoformat(),
            runtime_seconds=100.0,
            mape_method="walkforward",
            variables_tested=12,
            variables_passed=11,
            pass_rate=0.917,
            average_mape=4.8,
            variable_results=[],
            model_performance={},
            quality_gate=QualityGateResult(
                passed=True,
                minimum_required=10,
                actual_passed=11,
                variable_cost_mape=6.5,
                variable_cost_target=8.0,
            ),
        )

        result_dict = asdict(result)

        assert "timestamp" in result_dict
        assert "mape_method" in result_dict
        assert result_dict["variables_passed"] == 11
        assert result_dict["quality_gate"]["passed"] is True


class TestVariableValidationResult:
    """Test VariableValidationResult dataclass."""

    def test_create_variable_result(self):
        """Test creating a variable validation result."""
        result = VariableValidationResult(
            variable_name="revenue",
            display_name="Revenue",
            target_mape=5.0,
            actual_mape=4.2,
            passed=True,
            holdout_mape=4.2,
            walkforward_mape=4.5,
            cv_mape=4.8,
            ensemble_weights={"prophet": 0.4, "linear": 0.3, "xgboost": 0.3},
            best_model="prophet",
            best_model_mape=4.0,
        )

        assert result.variable_name == "revenue"
        assert result.passed is True
        assert result.actual_mape == 4.2
        assert "prophet" in result.ensemble_weights

    def test_variable_result_with_none_mape(self):
        """Test variable result with None MAPE (untested)."""
        result = VariableValidationResult(
            variable_name="variable_cost",
            display_name="Variable Cost per Ton",
            target_mape=8.0,
            actual_mape=None,
            passed=False,
        )

        assert result.actual_mape is None
        assert result.passed is False


class TestMCPSchema:
    """Test MCP-compatible output schema."""

    def test_mcp_format_structure(self):
        """Test that validation result conforms to MCP schema."""
        result = UnifiedValidationResult(
            timestamp=datetime.now().isoformat(),
            runtime_seconds=150.0,
            mape_method="holdout",
            variables_tested=12,
            variables_passed=10,
            pass_rate=0.833,
            average_mape=5.2,
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
                    ensemble_weights={},
                    best_model="prophet",
                    best_model_mape=4.5,
                )
            ],
            model_performance={},
            quality_gate=QualityGateResult(
                passed=True,
                minimum_required=10,
                actual_passed=10,
                variable_cost_mape=7.5,
                variable_cost_target=8.0,
            ),
        )

        # Convert to dict for MCP
        mcp_output = asdict(result)

        # Verify required MCP fields
        assert "timestamp" in mcp_output
        assert "runtime_seconds" in mcp_output
        assert "variables_tested" in mcp_output
        assert "pass_rate" in mcp_output
        assert "quality_gate" in mcp_output

        # Verify nested structures
        assert len(mcp_output["variable_results"]) == 1
        assert mcp_output["variable_results"][0]["variable_name"] == "revenue"

    def test_mcp_json_serialization(self):
        """Test that MCP output can be serialized to JSON."""
        result = UnifiedValidationResult(
            timestamp=datetime.now().isoformat(),
            runtime_seconds=100.0,
            mape_method="cv",
            variables_tested=12,
            variables_passed=11,
            pass_rate=0.917,
            average_mape=4.5,
            variable_results=[],
            model_performance={
                "prophet": ModelPerformanceStats(
                    model_name="prophet", avg_mape=5.2, variables_used=12, avg_runtime_seconds=15.0
                )
            },
            quality_gate=QualityGateResult(
                passed=True,
                minimum_required=10,
                actual_passed=11,
                variable_cost_mape=6.0,
                variable_cost_target=8.0,
            ),
        )

        # Should serialize without errors
        json_str = json.dumps(asdict(result), indent=2)

        assert json_str is not None
        assert "timestamp" in json_str
        assert "mape_method" in json_str

        # Should deserialize back
        parsed = json.loads(json_str)
        assert parsed["variables_tested"] == 12

    def test_quality_gate_with_none_variable_cost(self):
        """Test quality gate when variable_cost_mape is None."""
        result = QualityGateResult(
            passed=False,
            minimum_required=10,
            actual_passed=1,
            variable_cost_mape=None,
            variable_cost_target=8.0,
        )

        # Should serialize without errors
        result_dict = asdict(result)
        assert result_dict["variable_cost_mape"] is None

        json_str = json.dumps(result_dict)
        parsed = json.loads(json_str)
        assert parsed["variable_cost_mape"] is None
