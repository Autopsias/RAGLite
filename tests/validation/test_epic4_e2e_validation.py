"""End-to-end validation pipeline for Epic 4 forecasting and insights.

Story 4.10 AC1-AC4: Comprehensive validation of forecast accuracy, insight quality,
and recommendation alignment against MVP success criteria.

Targets:
- Forecast accuracy: MAPE ≤15% (NFR10)
- Insight relevance: ≥75%
- Recommendation alignment: ≥80%
"""

from dataclasses import dataclass
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from tests.validation.test_forecast_accuracy import (
    ForecastAccuracyValidator,
    ForecastValidationResult,
    create_growth_data,
    create_seasonal_data,
    create_volatile_data,
)
from tests.validation.test_insight_quality import (
    INSIGHT_TEST_SCENARIOS,
    InsightQualityValidator,
    InsightTestScenario,
    InsightValidationResult,
)
from tests.validation.test_recommendation_alignment import (
    RECOMMENDATION_TEST_SCENARIOS,
    RecommendationAlignmentValidator,
    RecommendationTestScenario,
    RecommendationValidationResult,
)


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


class Epic4ValidationOrchestrator:
    """Orchestrates end-to-end validation of Epic 4 forecasting and insights.

    Story 4.10 Task 4.3: Validation orchestrator for all MVP criteria.

    Example:
        >>> orchestrator = Epic4ValidationOrchestrator()
        >>> result = await orchestrator.run_full_validation()
        >>> assert result.overall_passed
    """

    def __init__(
        self,
        forecast_threshold: float = 15.0,
        insight_threshold: float = 75.0,
        recommendation_threshold: float = 80.0,
    ):
        """Initialize orchestrator with thresholds.

        Args:
            forecast_threshold: Max acceptable MAPE for forecasts (default 15.0)
            insight_threshold: Min acceptable insight relevance rate (default 75.0)
            recommendation_threshold: Min acceptable recommendation alignment (default 80.0)
        """
        self.forecast_validator = ForecastAccuracyValidator(threshold_pct=forecast_threshold)
        self.insight_validator = InsightQualityValidator(threshold_pct=insight_threshold)
        self.recommendation_validator = RecommendationAlignmentValidator(
            threshold_pct=recommendation_threshold
        )

    async def validate_forecasts(
        self,
        test_data: dict[str, pd.DataFrame],
    ) -> list[ForecastValidationResult]:
        """Run forecast validation on provided test data.

        Args:
            test_data: Dict of metric_name -> DataFrame with 'ds' and 'y' columns

        Returns:
            List of ForecastValidationResult for each metric
        """
        results = []
        for metric_name, df in test_data.items():
            try:
                result = await self.forecast_validator.validate_forecasts(
                    historical_data=df,
                    metric_name=metric_name,
                    train_ratio=0.8,
                )
                results.append(result)
            except Exception:
                # Create failed result
                results.append(
                    ForecastValidationResult(
                        metric_name=metric_name,
                        mape=100.0,  # Max error for failed validation
                        passed=False,
                        data_points_train=0,
                        data_points_test=0,
                        actuals=[],
                        predictions=[],
                        per_period_errors=[],
                    )
                )
        return results

    async def validate_insights(
        self,
        test_scenarios: list[InsightTestScenario] | None = None,
    ) -> InsightValidationResult:
        """Run insight quality validation.

        Args:
            test_scenarios: Optional custom scenarios (defaults to expert-labeled set)

        Returns:
            InsightValidationResult with relevance rate
        """
        scenarios = test_scenarios or INSIGHT_TEST_SCENARIOS
        return await self.insight_validator.validate_insights(scenarios)

    async def validate_recommendations(
        self,
        test_scenarios: list[RecommendationTestScenario] | None = None,
    ) -> RecommendationValidationResult:
        """Run recommendation alignment validation.

        Args:
            test_scenarios: Optional custom scenarios (defaults to expert-labeled set)

        Returns:
            RecommendationValidationResult with alignment rate
        """
        scenarios = test_scenarios or RECOMMENDATION_TEST_SCENARIOS
        return await self.recommendation_validator.validate_recommendations(scenarios)

    def _generate_improvement_recommendations(
        self,
        forecast_results: list[ForecastValidationResult],
        insight_result: InsightValidationResult,
        recommendation_result: RecommendationValidationResult,
    ) -> list[str]:
        """Generate actionable improvement recommendations based on results.

        Story 4.10 AC5: Improvement recommendations for failed criteria.

        Args:
            forecast_results: List of forecast validation results
            insight_result: Insight validation result
            recommendation_result: Recommendation validation result

        Returns:
            List of improvement recommendation strings
        """
        recommendations = []

        # Forecast improvements
        failed_forecasts = [r for r in forecast_results if not r.passed]
        if failed_forecasts:
            avg_mape = sum(r.mape for r in failed_forecasts) / len(failed_forecasts)
            if avg_mape > 25:
                recommendations.append(
                    "FORECAST: MAPE significantly exceeds threshold. Consider: "
                    "(1) Increase historical data coverage (24+ months), "
                    "(2) Tune Prophet hyperparameters (changepoint_prior_scale), "
                    "(3) Add external regressors for anomalous periods."
                )
            else:
                recommendations.append(
                    "FORECAST: MAPE slightly above threshold. Consider: "
                    "(1) Review data quality for outliers, "
                    "(2) Test alternative seasonality settings."
                )

        # Insight improvements
        if not insight_result.passed:
            if insight_result.relevance_rate < 50:
                recommendations.append(
                    "INSIGHT: Relevance rate critically low. Consider: "
                    "(1) Review categorization logic in categorize_insight(), "
                    "(2) Adjust priority thresholds in calculate_insight_priority(), "
                    "(3) Improve LLM synthesis prompts for better summarization."
                )
            else:
                recommendations.append(
                    "INSIGHT: Relevance rate below target. Consider: "
                    "(1) Fine-tune category boundaries for edge cases, "
                    "(2) Expand expert-labeled training scenarios."
                )

        # Recommendation improvements
        if not recommendation_result.passed:
            if recommendation_result.alignment_rate < 60:
                recommendations.append(
                    "RECOMMENDATION: Alignment rate critically low. Consider: "
                    "(1) Review categorize_recommendation() mapping logic, "
                    "(2) Adjust impact score calculation in calculate_impact_score(), "
                    "(3) Improve action step generation prompts."
                )
            else:
                recommendations.append(
                    "RECOMMENDATION: Alignment rate below target. Consider: "
                    "(1) Expand impact score tolerance range, "
                    "(2) Review urgency determination logic."
                )

        if not recommendations:
            recommendations.append(
                "All validation criteria met! Consider: "
                "(1) Adding edge case scenarios for robustness, "
                "(2) Expanding test data coverage to additional metrics."
            )

        return recommendations

    def _generate_summary(
        self,
        forecast_results: list[ForecastValidationResult],
        insight_result: InsightValidationResult,
        recommendation_result: RecommendationValidationResult,
    ) -> str:
        """Generate executive summary of validation results.

        Args:
            forecast_results: List of forecast validation results
            insight_result: Insight validation result
            recommendation_result: Recommendation validation result

        Returns:
            Executive summary string
        """
        # Forecast summary
        passed_forecasts = sum(1 for r in forecast_results if r.passed)
        avg_mape = (
            sum(r.mape for r in forecast_results) / len(forecast_results) if forecast_results else 0
        )
        forecast_status = "PASS" if all(r.passed for r in forecast_results) else "FAIL"

        # Insight summary
        insight_status = "PASS" if insight_result.passed else "FAIL"

        # Recommendation summary
        rec_status = "PASS" if recommendation_result.passed else "FAIL"

        # Overall
        overall_status = (
            "PASS"
            if (forecast_status == "PASS" and insight_status == "PASS" and rec_status == "PASS")
            else "FAIL"
        )

        summary = f"""
Epic 4 Validation Summary
========================

Overall Status: {overall_status}

1. Forecast Accuracy (Target: MAPE ≤15%)
   Status: {forecast_status}
   Metrics validated: {len(forecast_results)}
   Metrics passed: {passed_forecasts}/{len(forecast_results)}
   Average MAPE: {avg_mape:.1f}%

2. Insight Quality (Target: ≥75% relevance)
   Status: {insight_status}
   Scenarios tested: {insight_result.total_scenarios}
   Scenarios passed: {insight_result.passed_scenarios}
   Relevance rate: {insight_result.relevance_rate:.1f}%

3. Recommendation Alignment (Target: ≥80%)
   Status: {rec_status}
   Scenarios tested: {recommendation_result.total_scenarios}
   Scenarios aligned: {recommendation_result.aligned_scenarios}
   Alignment rate: {recommendation_result.alignment_rate:.1f}%
"""
        return summary.strip()

    async def run_full_validation(
        self,
        forecast_data: dict[str, pd.DataFrame] | None = None,
        insight_scenarios: list[InsightTestScenario] | None = None,
        recommendation_scenarios: list[RecommendationTestScenario] | None = None,
    ) -> Epic4ValidationResult:
        """Run complete Epic 4 validation pipeline.

        Story 4.10 Task 4.3: End-to-end validation orchestration.

        Args:
            forecast_data: Optional forecast test data (defaults to synthetic data)
            insight_scenarios: Optional insight scenarios (defaults to expert-labeled)
            recommendation_scenarios: Optional recommendation scenarios (defaults to expert-labeled)

        Returns:
            Epic4ValidationResult with all validation results and summary
        """
        # Default forecast data if not provided
        if forecast_data is None:
            start_date = datetime(2021, 1, 1)
            forecast_data = {
                "revenue": create_growth_data(start_date, periods=12, growth_rate=0.05),
                "expenses": create_seasonal_data(start_date, periods=12),
                "cash_flow": create_volatile_data(start_date, periods=12, volatility=0.10),
            }

        # Run all validations
        forecast_results = await self.validate_forecasts(forecast_data)
        insight_result = await self.validate_insights(insight_scenarios)
        recommendation_result = await self.validate_recommendations(recommendation_scenarios)

        # Generate summary and recommendations
        summary = self._generate_summary(forecast_results, insight_result, recommendation_result)
        improvement_recommendations = self._generate_improvement_recommendations(
            forecast_results, insight_result, recommendation_result
        )

        # Determine overall pass/fail
        overall_passed = (
            all(r.passed for r in forecast_results)
            and insight_result.passed
            and recommendation_result.passed
        )

        return Epic4ValidationResult(
            overall_passed=overall_passed,
            forecast_results=forecast_results,
            insight_result=insight_result,
            recommendation_result=recommendation_result,
            summary=summary,
            improvement_recommendations=improvement_recommendations,
        )


# ============================================================================
# Comprehensive Test Data Set (Story 4.10 Task 4.2)
# ============================================================================


def create_comprehensive_test_data(
    months: int = 24,
) -> dict[str, pd.DataFrame]:
    """Create comprehensive 24-month test data set for validation.

    Story 4.10 Task 4.2: Multi-year test data for robust validation.

    Args:
        months: Number of months of data (default 24 = 2 years)

    Returns:
        Dict of metric_name -> DataFrame with 'ds' and 'y' columns
    """
    start_date = datetime(2022, 1, 1)
    quarters = months // 3  # Convert to quarterly periods

    return {
        "revenue": create_growth_data(
            start_date, periods=quarters, growth_rate=0.05, noise_pct=0.02
        ),
        "expenses": create_seasonal_data(
            start_date, periods=quarters, seasonal_amplitude=0.15, noise_pct=0.02
        ),
        "cash_flow": create_growth_data(
            start_date, periods=quarters, growth_rate=0.03, noise_pct=0.05
        ),
        "ebitda": create_growth_data(
            start_date, periods=quarters, growth_rate=0.07, noise_pct=0.03
        ),
    }


# ============================================================================
# Pytest Tests
# ============================================================================


@pytest.fixture
def orchestrator() -> Epic4ValidationOrchestrator:
    """Create orchestrator instance for tests."""
    return Epic4ValidationOrchestrator()


@pytest.fixture
def test_data() -> dict[str, pd.DataFrame]:
    """Create test data for validation."""
    return create_comprehensive_test_data(months=24)


class TestOrchestrator:
    """Tests for validation orchestrator."""

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_run_full_validation(
        self,
        orchestrator: Epic4ValidationOrchestrator,
        test_data: dict[str, pd.DataFrame],
    ):
        """Test complete validation pipeline execution.

        Story 4.10 AC1-AC4: Full E2E validation.
        """
        # Mock LLM calls for faster validation
        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_response = AsyncMock()
            mock_response.choices = [
                AsyncMock(message=AsyncMock(content='{"summary": "Test forecast"}'))
            ]
            mock_client.return_value.chat.complete.return_value = mock_response

            result = await orchestrator.run_full_validation(forecast_data=test_data)

        # Validate result structure
        assert isinstance(result, Epic4ValidationResult)
        assert len(result.forecast_results) == 4  # revenue, expenses, cash_flow, ebitda
        assert result.insight_result is not None
        assert result.recommendation_result is not None
        assert result.summary != ""
        assert len(result.improvement_recommendations) > 0

        # Log results
        print(f"\n{result.summary}")
        print("\nImprovement Recommendations:")
        for rec in result.improvement_recommendations:
            print(f"  - {rec}")

    @pytest.mark.asyncio
    async def test_validate_forecasts_only(
        self,
        orchestrator: Epic4ValidationOrchestrator,
    ):
        """Test forecast validation in isolation."""
        test_data = {
            "revenue": create_growth_data(datetime(2021, 1, 1), periods=12),
        }

        # Mock LLM
        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock(message=AsyncMock(content='{"summary": "Test"}'))]
            mock_client.return_value.chat.complete.return_value = mock_response

            results = await orchestrator.validate_forecasts(test_data)

        assert len(results) == 1
        assert results[0].metric_name == "revenue"

    @pytest.mark.asyncio
    async def test_validate_insights_only(
        self,
        orchestrator: Epic4ValidationOrchestrator,
    ):
        """Test insight validation in isolation."""
        # Use subset of scenarios for faster test
        scenarios = INSIGHT_TEST_SCENARIOS[:3]

        result = await orchestrator.validate_insights(scenarios)

        assert result.total_scenarios == 3

    @pytest.mark.asyncio
    async def test_validate_recommendations_only(
        self,
        orchestrator: Epic4ValidationOrchestrator,
    ):
        """Test recommendation validation in isolation."""
        # Use subset of scenarios for faster test
        scenarios = RECOMMENDATION_TEST_SCENARIOS[:3]

        result = await orchestrator.validate_recommendations(scenarios)

        assert result.total_scenarios == 3


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


class TestImprovementRecommendations:
    """Tests for improvement recommendation generation."""

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


class TestCustomThresholds:
    """Tests for custom threshold configuration."""

    def test_custom_thresholds(self):
        """Test orchestrator with custom thresholds."""
        orchestrator = Epic4ValidationOrchestrator(
            forecast_threshold=10.0,  # Stricter
            insight_threshold=85.0,  # Stricter
            recommendation_threshold=90.0,  # Stricter
        )

        assert orchestrator.forecast_validator.threshold_pct == 10.0
        assert orchestrator.insight_validator.threshold_pct == 85.0
        assert orchestrator.recommendation_validator.threshold_pct == 90.0
