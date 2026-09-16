"""Tests for Epic4ValidationResult properties."""

import pytest

from tests.validation.forecast_accuracy import ForecastValidationResult
from tests.validation.test_epic4_e2e_validation.models import Epic4ValidationResult
from tests.validation.test_insight_quality import InsightValidationResult
from tests.validation.test_recommendation_alignment import RecommendationValidationResult


class TestValidationResult:
    """Tests for Epic4ValidationResult properties."""

    def test_overall_passed_property(self):
        """Test overall_passed property."""
        # Create mock results
        forecast_result = ForecastValidationResult(
            metric_name="revenue",
            mape=10.0,
            passed=True,
            data_points_train=8,
            data_points_test=2,
            actuals=[100, 110],
            predictions=[105, 115],
            per_period_errors=[5, 4.5],
        )
        insight_result = InsightValidationResult(
            total_scenarios=10,
            passed_scenarios=8,
            relevance_rate=80.0,
            passed=True,
            scenario_results=[],
            category_breakdown={},
        )
        recommendation_result = RecommendationValidationResult(
            total_scenarios=8,
            aligned_scenarios=7,
            alignment_rate=87.5,
            passed=True,
            scenario_results=[],
            category_breakdown={},
        )

        result = Epic4ValidationResult(
            overall_passed=True,
            forecast_results=[forecast_result],
            insight_result=insight_result,
            recommendation_result=recommendation_result,
            summary="Test summary",
            improvement_recommendations=["All good"],
        )

        assert result.forecast_passed
        assert result.insight_passed
        assert result.recommendation_passed
        assert result.average_mape == 10.0

    def test_average_mape_multiple_metrics(self):
        """Test average MAPE calculation with multiple metrics."""
        results = [
            ForecastValidationResult(
                metric_name="revenue",
                mape=10.0,
                passed=True,
                data_points_train=8,
                data_points_test=2,
                actuals=[],
                predictions=[],
                per_period_errors=[],
            ),
            ForecastValidationResult(
                metric_name="expenses",
                mape=14.0,
                passed=True,
                data_points_train=8,
                data_points_test=2,
                actuals=[],
                predictions=[],
                per_period_errors=[],
            ),
            ForecastValidationResult(
                metric_name="cash_flow",
                mape=12.0,
                passed=True,
                data_points_train=8,
                data_points_test=2,
                actuals=[],
                predictions=[],
                per_period_errors=[],
            ),
        ]

        insight_result = InsightValidationResult(
            total_scenarios=0,
            passed_scenarios=0,
            relevance_rate=0,
            passed=False,
            scenario_results=[],
            category_breakdown={},
        )
        recommendation_result = RecommendationValidationResult(
            total_scenarios=0,
            aligned_scenarios=0,
            alignment_rate=0,
            passed=False,
            scenario_results=[],
            category_breakdown={},
        )

        result = Epic4ValidationResult(
            overall_passed=False,
            forecast_results=results,
            insight_result=insight_result,
            recommendation_result=recommendation_result,
            summary="",
            improvement_recommendations=[],
        )

        assert result.average_mape == pytest.approx(12.0)  # (10 + 14 + 12) / 3
