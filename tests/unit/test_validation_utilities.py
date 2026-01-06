"""Unit tests for validation utility functions.

Story 4.10 Task 6: Tests for edge cases and utility functions
used by the validation framework.
"""

from datetime import datetime

import numpy as np
import pytest

from tests.validation.forecast_accuracy.test_data import (
    create_growth_data,
    create_seasonal_data,
    create_volatile_data,
)
from tests.validation.forecast_accuracy.validator import ForecastAccuracyValidator
from tests.validation.test_insight_quality.models import (
    InsightTestScenario,
    InsightValidationResult,
)
from tests.validation.test_insight_quality.validator import InsightQualityValidator
from tests.validation.test_recommendation_alignment.models import (
    RecommendationTestScenario,
    RecommendationValidationResult,
)
from tests.validation.test_recommendation_alignment.validator import (
    RecommendationAlignmentValidator,
)

# For backward compatibility
ForecastValidationResult = InsightValidationResult  # Alias


class TestMAPEEdgeCases:
    """Edge case tests for MAPE calculation."""

    @pytest.fixture
    def validator(self) -> ForecastAccuracyValidator:
        return ForecastAccuracyValidator(threshold_pct=15.0)

    def test_mape_with_negative_values(self, validator: ForecastAccuracyValidator):
        """MAPE should handle negative actual values (e.g., net losses)."""
        actuals = [-100.0, -50.0, -75.0]
        predictions = [-90.0, -55.0, -70.0]

        # MAPE uses absolute percentage error
        mape = validator.calculate_mape(actuals, predictions)

        # Expected: abs((-100 - -90) / -100) + ... / 3 * 100
        # = (10/100 + 5/50 + 5/75) / 3 * 100
        expected = (10 / 100 + 5 / 50 + 5 / 75) / 3 * 100
        assert abs(mape - expected) < 0.01

    def test_mape_with_very_large_values(self, validator: ForecastAccuracyValidator):
        """MAPE should handle very large values without overflow."""
        actuals = [1e12, 2e12, 3e12]
        predictions = [1.1e12, 2.1e12, 3.1e12]

        mape = validator.calculate_mape(actuals, predictions)

        # All errors are 10%, ~5%, ~3.33%
        assert 0 < mape < 20

    def test_mape_with_very_small_values(self, validator: ForecastAccuracyValidator):
        """MAPE should handle very small values without precision issues."""
        actuals = [0.001, 0.002, 0.003]
        predictions = [0.0011, 0.0021, 0.0031]

        mape = validator.calculate_mape(actuals, predictions)

        # All errors are 10%, 5%, ~3.33%
        assert 0 < mape < 20

    def test_mape_with_mixed_positive_negative(self, validator: ForecastAccuracyValidator):
        """MAPE should handle mix of positive and negative values."""
        actuals = [100.0, -50.0, 75.0, -25.0]
        predictions = [110.0, -45.0, 80.0, -30.0]

        mape = validator.calculate_mape(actuals, predictions)

        assert mape > 0
        assert mape < 100

    def test_mape_single_zero_prediction(self, validator: ForecastAccuracyValidator):
        """MAPE should handle when prediction is zero but actual is non-zero."""
        actuals = [100.0, 200.0]
        predictions = [0.0, 200.0]

        mape = validator.calculate_mape(actuals, predictions)

        # First prediction error is 100%
        assert mape == pytest.approx(50.0)  # Average of 100% and 0%


class TestSMAPEFallback:
    """Tests for SMAPE fallback when MAPE is undefined."""

    @pytest.fixture
    def validator(self) -> ForecastAccuracyValidator:
        return ForecastAccuracyValidator()

    def test_smape_basic_calculation(self, validator: ForecastAccuracyValidator):
        """SMAPE formula: 2 * |actual - predicted| / (|actual| + |predicted|) * 100."""
        actuals = np.array([0.0, 0.0, 0.0])
        predictions = np.array([10.0, 20.0, 30.0])

        smape = validator._calculate_smape(actuals, predictions)

        # SMAPE = 2 * |0 - p| / (0 + |p|) = 2 for all, * 100 = 200%
        assert smape == pytest.approx(200.0)

    def test_smape_with_both_zeros(self, validator: ForecastAccuracyValidator):
        """SMAPE should return 0 when both arrays are all zeros."""
        actuals = np.array([0.0, 0.0, 0.0])
        predictions = np.array([0.0, 0.0, 0.0])

        smape = validator._calculate_smape(actuals, predictions)

        assert smape == 0.0

    def test_smape_symmetric(self, validator: ForecastAccuracyValidator):
        """SMAPE should give same result regardless of which is actual/predicted."""
        arr1 = np.array([100.0, 200.0])
        arr2 = np.array([120.0, 180.0])

        smape1 = validator._calculate_smape(arr1, arr2)
        smape2 = validator._calculate_smape(arr2, arr1)

        assert smape1 == pytest.approx(smape2)


class TestDataCreationUtilities:
    """Tests for synthetic data creation utilities."""

    def test_growth_data_has_correct_shape(self):
        """Growth data should have correct number of periods."""
        df = create_growth_data(datetime(2021, 1, 1), periods=12)

        assert len(df) == 12
        assert "ds" in df.columns
        assert "y" in df.columns

    def test_growth_data_increases(self):
        """Growth data should show overall upward trend."""
        df = create_growth_data(
            datetime(2021, 1, 1),
            periods=12,
            growth_rate=0.05,
            noise_pct=0.0,  # No noise for deterministic test
        )

        # Each period should be ~5% higher than previous
        values = df["y"].tolist()
        for i in range(1, len(values)):
            ratio = values[i] / values[i - 1]
            assert 1.04 <= ratio <= 1.06  # Allow for rounding

    def test_seasonal_data_has_pattern(self):
        """Seasonal data should show quarterly pattern."""
        df = create_seasonal_data(
            datetime(2021, 1, 1),
            periods=8,  # 2 years
            seasonal_amplitude=0.2,
            noise_pct=0.0,
        )

        values = df["y"].tolist()

        # Q4 (indices 3, 7) should be highest
        # Q2 (indices 1, 5) should be lowest
        assert values[3] > values[1]  # Q4 > Q2 in year 1
        assert values[7] > values[5]  # Q4 > Q2 in year 2

    def test_volatile_data_has_variation(self):
        """Volatile data should have significant variation."""
        df = create_volatile_data(
            datetime(2021, 1, 1),
            periods=12,
            volatility=0.15,
        )

        values = df["y"].tolist()
        std_dev = np.std(values)
        mean_val = np.mean(values)

        # Coefficient of variation should be significant
        cv = std_dev / mean_val
        assert cv > 0.05  # At least 5% coefficient of variation

    def test_growth_data_reproducibility(self):
        """Growth data should be reproducible with same seed."""
        df1 = create_growth_data(datetime(2021, 1, 1), periods=8, noise_pct=0.05)
        df2 = create_growth_data(datetime(2021, 1, 1), periods=8, noise_pct=0.05)

        # Both should be identical due to fixed seed
        assert df1["y"].tolist() == df2["y"].tolist()


class TestValidationResultStructures:
    """Tests for validation result dataclass structures."""

    def test_forecast_validation_result_fields(self):
        """ForecastValidationResult should have all required fields."""
        result = ForecastValidationResult(
            metric_name="revenue",
            mape=12.5,
            passed=True,
            data_points_train=8,
            data_points_test=2,
            actuals=[100, 110],
            predictions=[105, 115],
            per_period_errors=[5.0, 4.5],
        )

        assert result.metric_name == "revenue"
        assert result.mape == 12.5
        assert result.passed is True
        assert result.data_points_train == 8
        assert result.data_points_test == 2
        assert len(result.actuals) == 2
        assert len(result.predictions) == 2
        assert len(result.per_period_errors) == 2

    def test_insight_validation_result_fields(self):
        """InsightValidationResult should have all required fields."""
        result = InsightValidationResult(
            total_scenarios=10,
            passed_scenarios=8,
            relevance_rate=80.0,
            passed=True,
            scenario_results=[{"id": "test", "passed": True}],
            category_breakdown={"risk": 3, "opportunity": 2},
        )

        assert result.total_scenarios == 10
        assert result.passed_scenarios == 8
        assert result.relevance_rate == 80.0
        assert result.passed is True
        assert len(result.scenario_results) == 1
        assert len(result.category_breakdown) == 2

    def test_recommendation_validation_result_fields(self):
        """RecommendationValidationResult should have all required fields."""
        result = RecommendationValidationResult(
            total_scenarios=8,
            aligned_scenarios=7,
            alignment_rate=87.5,
            passed=True,
            scenario_results=[{"id": "test", "aligned": True}],
            category_breakdown={"risk_mitigation": 3},
        )

        assert result.total_scenarios == 8
        assert result.aligned_scenarios == 7
        assert result.alignment_rate == 87.5
        assert result.passed is True


class TestThresholdValidation:
    """Tests for threshold validation logic."""

    def test_forecast_threshold_boundary_pass(self):
        """Exactly at threshold should pass."""
        validator = ForecastAccuracyValidator(threshold_pct=15.0)
        mape = 15.0

        # At boundary should pass
        passed = mape <= validator.threshold_pct
        assert passed is True

    def test_forecast_threshold_boundary_fail(self):
        """Just above threshold should fail."""
        validator = ForecastAccuracyValidator(threshold_pct=15.0)
        mape = 15.01

        passed = mape <= validator.threshold_pct
        assert passed is False

    def test_insight_threshold_boundary_pass(self):
        """Exactly at insight threshold should pass."""
        validator = InsightQualityValidator(threshold_pct=75.0)
        relevance_rate = 75.0

        passed = relevance_rate >= validator.threshold_pct
        assert passed is True

    def test_recommendation_threshold_boundary_pass(self):
        """Exactly at recommendation threshold should pass."""
        validator = RecommendationAlignmentValidator(threshold_pct=80.0)
        alignment_rate = 80.0

        passed = alignment_rate >= validator.threshold_pct
        assert passed is True


class TestPerPeriodErrorCalculation:
    """Tests for per-period error calculation."""

    @pytest.fixture
    def validator(self) -> ForecastAccuracyValidator:
        return ForecastAccuracyValidator()

    def test_per_period_errors_basic(self, validator: ForecastAccuracyValidator):
        """Basic per-period error calculation."""
        actuals = [100.0, 200.0, 300.0]
        predictions = [110.0, 190.0, 300.0]

        errors = validator.get_per_period_errors(actuals, predictions)

        assert len(errors) == 3
        assert errors[0] == pytest.approx(10.0)  # |100-110|/100 * 100
        assert errors[1] == pytest.approx(5.0)  # |200-190|/200 * 100
        assert errors[2] == pytest.approx(0.0)  # |300-300|/300 * 100

    def test_per_period_errors_with_zero_actual(self, validator: ForecastAccuracyValidator):
        """Per-period errors should handle zero actuals."""
        actuals = [0.0, 100.0]
        predictions = [10.0, 100.0]

        errors = validator.get_per_period_errors(actuals, predictions)

        assert len(errors) == 2
        # First error uses absolute prediction as percentage
        assert errors[0] == 1000.0  # |10| * 100
        assert errors[1] == 0.0


class TestActionableStepsValidation:
    """Tests for actionable steps validation in recommendations."""

    @pytest.fixture
    def validator(self) -> RecommendationAlignmentValidator:
        return RecommendationAlignmentValidator()

    def test_actionable_steps_with_verbs(self, validator: RecommendationAlignmentValidator):
        """Steps starting with action verbs should be actionable."""
        steps = [
            "Review the quarterly reports",
            "Analyze cost trends",
            "Implement automation",
        ]

        assert validator._has_actionable_steps(steps) is True

    def test_actionable_steps_no_verbs(self, validator: RecommendationAlignmentValidator):
        """Steps without action verbs may still be actionable if long enough."""
        steps = [
            "The quarterly reports show trends that need attention",  # 8 words
        ]

        assert validator._has_actionable_steps(steps) is True

    def test_actionable_steps_short_no_verbs(self, validator: RecommendationAlignmentValidator):
        """Short steps without action verbs should not be actionable."""
        steps = [
            "Cost report",
            "Data file",
        ]

        assert validator._has_actionable_steps(steps) is False

    def test_actionable_steps_empty(self, validator: RecommendationAlignmentValidator):
        """Empty steps list should not be actionable."""
        assert validator._has_actionable_steps([]) is False

    def test_actionable_verbs_coverage(self, validator: RecommendationAlignmentValidator):
        """Test various actionable verbs are recognized."""
        verbs_to_test = [
            "Review",
            "Analyze",
            "Assess",
            "Evaluate",
            "Implement",
            "Develop",
            "Create",
            "Reduce",
            "Increase",
            "Optimize",
        ]

        for verb in verbs_to_test:
            steps = [f"{verb} the business process"]
            assert validator._has_actionable_steps(steps) is True, f"Verb '{verb}' not recognized"


class TestScenarioValidation:
    """Tests for scenario validation edge cases."""

    def test_insight_scenario_with_minimal_data(self):
        """InsightTestScenario should work with minimal required data."""
        from raglite.shared.models import Anomaly, AnomalySeverity

        scenario = InsightTestScenario(
            scenario_id="minimal",
            description="Minimal test",
            anomaly=Anomaly(
                date="2024-Q1",
                metric="test",
                value=100.0,
                expected_value=80.0,
                z_score=2.0,
                severity=AnomalySeverity.MODERATE,
                magnitude_pct=25.0,
            ),
        )

        assert scenario.scenario_id == "minimal"
        assert scenario.anomaly is not None
        assert scenario.trend is None
        assert scenario.forecast is None

    def test_recommendation_scenario_with_custom_ranges(self):
        """RecommendationTestScenario should accept custom impact ranges."""
        from raglite.shared.models import Insight, InsightCategory

        scenario = RecommendationTestScenario(
            scenario_id="custom_range",
            description="Custom range test",
            insight=Insight(
                category=InsightCategory.RISK,
                priority=2,
                summary="Test",
                supporting_data={},
                sources=[],
            ),
            expected_impact_range=(3, 7),  # Custom range
        )

        assert scenario.expected_impact_range == (3, 7)
