"""Data models for Epic 4 E2E validation."""

from dataclasses import dataclass

from tests.validation.forecast_accuracy import ForecastValidationResult
from tests.validation.test_insight_quality import InsightValidationResult
from tests.validation.test_recommendation_alignment import RecommendationValidationResult


@dataclass
class Epic4ValidationResult:
    """Complete validation result for Epic 4 MVP criteria.

    Story 4.10 AC1-AC4: Aggregated results from all validation frameworks.

    Attributes:
        overall_passed: True if all criteria met
        forecast_results: Per-metric MAPE results
        insight_result: Insight relevance validation result
        recommendation_result: Recommendation alignment validation result
        summary: Executive summary of validation results
        improvement_recommendations: List of improvement suggestions
    """

    overall_passed: bool
    forecast_results: list[ForecastValidationResult]
    insight_result: InsightValidationResult
    recommendation_result: RecommendationValidationResult
    summary: str
    improvement_recommendations: list[str]

    @property
    def forecast_passed(self) -> bool:
        """Check if all forecasts passed MAPE threshold."""
        return all(r.passed for r in self.forecast_results)

    @property
    def insight_passed(self) -> bool:
        """Check if insight relevance met threshold."""
        return self.insight_result.passed

    @property
    def recommendation_passed(self) -> bool:
        """Check if recommendation alignment met threshold."""
        return self.recommendation_result.passed

    @property
    def average_mape(self) -> float:
        """Calculate average MAPE across all metrics."""
        if not self.forecast_results:
            return 0.0
        return sum(r.mape for r in self.forecast_results) / len(self.forecast_results)
