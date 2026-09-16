"""Tests for improvement recommendation generation."""

import pytest

from tests.validation.forecast_accuracy import ForecastValidationResult
from tests.validation.test_epic4_e2e_validation.orchestrator import Epic4ValidationOrchestrator
from tests.validation.test_insight_quality import InsightValidationResult
from tests.validation.test_recommendation_alignment import RecommendationValidationResult


class TestImprovementRecommendations:
    """Tests for improvement recommendation generation."""

    @pytest.fixture
    def orchestrator(self) -> Epic4ValidationOrchestrator:
        """Create orchestrator instance for tests."""
        return Epic4ValidationOrchestrator()

    def test_recommendations_for_failed_forecast(
        self,
        orchestrator: Epic4ValidationOrchestrator,
    ):
        """Test recommendations generated for failed forecasts."""
        forecast_results = [
            ForecastValidationResult(
                metric_name="revenue",
                mape=30.0,
                passed=False,
                data_points_train=8,
                data_points_test=2,
                actuals=[],
                predictions=[],
                per_period_errors=[],
            ),
        ]
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

        recommendations = orchestrator._generate_improvement_recommendations(
            forecast_results, insight_result, recommendation_result
        )

        assert len(recommendations) > 0
        assert any("FORECAST" in r for r in recommendations)

    def test_recommendations_for_passed_all(
        self,
        orchestrator: Epic4ValidationOrchestrator,
    ):
        """Test recommendations when all criteria pass."""
        forecast_results = [
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
        ]
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

        recommendations = orchestrator._generate_improvement_recommendations(
            forecast_results, insight_result, recommendation_result
        )

        assert len(recommendations) == 1
        assert "All validation criteria met" in recommendations[0]
