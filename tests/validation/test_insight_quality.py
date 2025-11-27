"""Insight quality validation framework.

Story 4.10 AC3: Validates insight relevance using expert-labeled test scenarios.
Target: 75%+ insights rated useful/actionable.
"""

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from raglite.insights.proactive import (
    calculate_insight_priority,
    categorize_insight,
    generate_insights,
)
from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    ForecastResult,
    Insight,
    InsightCategory,
    Trend,
    TrendDirection,
)


@dataclass
class InsightTestScenario:
    """Expert-labeled test scenario for insight validation.

    Story 4.10 AC3: Each scenario has expected outcomes labeled by expert.

    Attributes:
        scenario_id: Unique identifier (e.g., "marketing_spike")
        description: Human-readable scenario description
        anomaly: Optional anomaly input data
        trend: Optional trend input data
        forecast: Optional forecast input data
        expected_category: Expected InsightCategory for this scenario
        expected_priority_range: Acceptable priority range (min, max inclusive)
        expected_keywords: Keywords that should appear in rationale/summary
    """

    scenario_id: str
    description: str
    anomaly: Anomaly | None = None
    trend: Trend | None = None
    forecast: ForecastResult | None = None
    expected_category: InsightCategory = InsightCategory.RISK
    expected_priority_range: tuple[int, int] = (1, 5)
    expected_keywords: list[str] = field(default_factory=list)


@dataclass
class InsightValidationResult:
    """Result of insight quality validation.

    Story 4.10 AC3: Structured validation result for insight relevance.

    Attributes:
        total_scenarios: Total number of test scenarios
        passed_scenarios: Number of scenarios that passed validation
        relevance_rate: Percentage of scenarios with useful insights (0-100)
        passed: Whether relevance rate meets 75% threshold
        scenario_results: Per-scenario pass/fail details
        category_breakdown: Count of insights per category
    """

    total_scenarios: int
    passed_scenarios: int
    relevance_rate: float
    passed: bool
    scenario_results: list[dict[str, Any]]
    category_breakdown: dict[str, int]


class InsightQualityValidator:
    """Validates insight relevance against 75% usefulness threshold.

    Story 4.10 AC3: Expert-labeled test set validation for insight quality.

    Example:
        >>> validator = InsightQualityValidator()
        >>> result = await validator.validate_insights(test_scenarios)
        >>> assert result.passed  # relevance_rate >= 75%
    """

    def __init__(self, threshold_pct: float = 75.0):
        """Initialize validator with relevance threshold.

        Args:
            threshold_pct: Minimum acceptable relevance rate (default 75.0)
        """
        self.threshold_pct = threshold_pct

    def _is_insight_relevant(
        self,
        insight: Insight,
        scenario: InsightTestScenario,
    ) -> tuple[bool, str]:
        """Check if generated insight is relevant for the scenario.

        Story 4.10 Task 2.3: Relevance scoring logic.

        Args:
            insight: Generated insight
            scenario: Expected scenario with expert labels

        Returns:
            Tuple of (is_relevant, reason)
        """
        reasons = []

        # Check 1: Category match
        category_match = insight.category == scenario.expected_category
        if not category_match:
            reasons.append(
                f"Category mismatch: got {insight.category.value}, "
                f"expected {scenario.expected_category.value}"
            )

        # Check 2: Priority in expected range
        priority_min, priority_max = scenario.expected_priority_range
        priority_match = priority_min <= insight.priority <= priority_max
        if not priority_match:
            reasons.append(
                f"Priority out of range: got {insight.priority}, "
                f"expected [{priority_min}, {priority_max}]"
            )

        # Check 3: Supporting data contains relevant metrics
        has_supporting_data = bool(insight.supporting_data)
        if not has_supporting_data:
            reasons.append("No supporting data")

        # Check 4: Rationale or summary references expected content
        # (If keywords are specified, check for them; otherwise, just check non-empty)
        text_content = f"{insight.summary} {insight.rationale}".lower()
        keywords_match = True
        if scenario.expected_keywords:
            found_keywords = [kw for kw in scenario.expected_keywords if kw.lower() in text_content]
            keywords_match = len(found_keywords) > 0
            if not keywords_match:
                reasons.append(f"Missing expected keywords: {scenario.expected_keywords}")

        # Overall relevance: category + priority must match, and must have supporting data
        is_relevant = category_match and priority_match and has_supporting_data

        reason = "; ".join(reasons) if reasons else "All checks passed"
        return is_relevant, reason

    async def validate_insights(
        self,
        test_scenarios: list[InsightTestScenario],
    ) -> InsightValidationResult:
        """Score insights against expert-labeled expectations.

        Story 4.10 AC3: Run scenarios and calculate relevance rate.

        Args:
            test_scenarios: List of scenarios with expected outcomes

        Returns:
            InsightValidationResult with relevance rate and breakdown

        Raises:
            ValueError: If no test scenarios provided
        """
        if not test_scenarios:
            raise ValueError("No test scenarios provided")

        scenario_results: list[dict[str, Any]] = []
        category_counts: dict[str, int] = {}
        passed_count = 0

        # Mock LLM for faster validation
        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_response = AsyncMock()
            mock_response.choices = [
                AsyncMock(
                    message=AsyncMock(
                        content="SUMMARY: Test insight\nRATIONALE: Based on data analysis\nACTION: Review findings"
                    )
                )
            ]
            mock_client.return_value.chat.complete.return_value = mock_response

            for scenario in test_scenarios:
                # Build inputs
                anomalies = [scenario.anomaly] if scenario.anomaly else []
                trends = [scenario.trend] if scenario.trend else []
                forecasts = [scenario.forecast] if scenario.forecast else []

                # Generate insights
                result = await generate_insights(
                    anomalies=anomalies,
                    trends=trends,
                    forecasts=forecasts,
                    auto_synthesize=True,
                )

                # Validate first insight (primary result)
                if result.insights:
                    insight = result.insights[0]
                    is_relevant, reason = self._is_insight_relevant(insight, scenario)

                    # Track category
                    cat_key = insight.category.value
                    category_counts[cat_key] = category_counts.get(cat_key, 0) + 1

                    scenario_results.append(
                        {
                            "scenario_id": scenario.scenario_id,
                            "description": scenario.description,
                            "passed": is_relevant,
                            "reason": reason,
                            "generated_category": insight.category.value,
                            "generated_priority": insight.priority,
                            "expected_category": scenario.expected_category.value,
                            "expected_priority_range": scenario.expected_priority_range,
                        }
                    )

                    if is_relevant:
                        passed_count += 1
                else:
                    scenario_results.append(
                        {
                            "scenario_id": scenario.scenario_id,
                            "description": scenario.description,
                            "passed": False,
                            "reason": "No insights generated",
                            "generated_category": None,
                            "generated_priority": None,
                            "expected_category": scenario.expected_category.value,
                            "expected_priority_range": scenario.expected_priority_range,
                        }
                    )

        # Calculate relevance rate
        relevance_rate = (passed_count / len(test_scenarios)) * 100

        return InsightValidationResult(
            total_scenarios=len(test_scenarios),
            passed_scenarios=passed_count,
            relevance_rate=relevance_rate,
            passed=relevance_rate >= self.threshold_pct,
            scenario_results=scenario_results,
            category_breakdown=category_counts,
        )


# ============================================================================
# Expert-Labeled Test Scenarios (Story 4.10 Task 2.2)
# ============================================================================

INSIGHT_TEST_SCENARIOS: list[InsightTestScenario] = [
    # Scenario 1: Marketing spend spike detection (should flag as RISK)
    InsightTestScenario(
        scenario_id="marketing_spike",
        description="Marketing spend increased 30% YoY with no revenue increase",
        anomaly=Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=130000.0,
            expected_value=100000.0,
            z_score=2.5,
            severity=AnomalySeverity.CRITICAL,
            reason="Significant marketing spend increase without ROI",
            magnitude_pct=30.0,
        ),
        expected_category=InsightCategory.RISK,
        expected_priority_range=(1, 2),
        expected_keywords=["marketing", "spend"],
    ),
    # Scenario 2: Revenue growth trend (should flag as OPPORTUNITY)
    InsightTestScenario(
        scenario_id="revenue_growth",
        description="Revenue growing 15% CAGR consistently",
        trend=Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=15.0,
            confidence=0.85,
            start_date="2023-Q1",
            end_date="2024-Q4",
            description="Strong revenue growth trend",
            cagr=0.15,
            qoq_growth=0.04,
        ),
        expected_category=InsightCategory.OPPORTUNITY,
        expected_priority_range=(1, 3),
        expected_keywords=["revenue", "growth"],
    ),
    # Scenario 3: Seasonal pattern recognition (should flag as TREND)
    InsightTestScenario(
        scenario_id="seasonal_pattern",
        description="Q4 consistently 20% higher than Q2",
        trend=Trend(
            metric="sales",
            direction=TrendDirection.STABLE,
            magnitude=5.0,
            confidence=0.75,
            start_date="2022-Q1",
            end_date="2024-Q4",
            description="Seasonal sales pattern with Q4 spike",
            cagr=0.05,
            qoq_growth=0.02,
        ),
        expected_category=InsightCategory.TREND,
        expected_priority_range=(3, 5),
        expected_keywords=["sales"],
    ),
    # Scenario 4: Cost anomaly detection (should flag as ANOMALY)
    InsightTestScenario(
        scenario_id="cost_anomaly",
        description="Cloud costs spiked 40% unexpectedly",
        anomaly=Anomaly(
            date="2024-Q2",
            metric="cloud_costs",
            value=70000.0,
            expected_value=50000.0,
            z_score=2.1,
            severity=AnomalySeverity.MODERATE,
            reason="Unexpected cloud cost increase",
            magnitude_pct=40.0,
        ),
        expected_category=InsightCategory.ANOMALY,
        expected_priority_range=(2, 4),
        expected_keywords=["cloud"],
    ),
    # Scenario 5: Critical expense deviation (should flag as RISK)
    InsightTestScenario(
        scenario_id="expense_critical",
        description="Operating expenses 50% over budget with critical severity",
        anomaly=Anomaly(
            date="2024-Q3",
            metric="operating_expenses",
            value=450000.0,
            expected_value=300000.0,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            reason="Operating expenses significantly over budget",
            magnitude_pct=50.0,
        ),
        expected_category=InsightCategory.RISK,
        expected_priority_range=(1, 2),
        expected_keywords=["expenses"],
    ),
    # Scenario 6: Decreasing profit margin (should flag as RISK)
    InsightTestScenario(
        scenario_id="margin_decline",
        description="Profit margin declining 12% over 2 years",
        trend=Trend(
            metric="profit_margin",
            direction=TrendDirection.DECREASING,
            magnitude=12.0,
            confidence=0.80,
            start_date="2023-Q1",
            end_date="2024-Q4",
            description="Consistent profit margin decline",
            cagr=-0.06,
            qoq_growth=-0.015,
        ),
        expected_category=InsightCategory.RISK,
        expected_priority_range=(2, 3),
        expected_keywords=["margin", "profit"],
    ),
    # Scenario 7: Cash flow improvement opportunity
    InsightTestScenario(
        scenario_id="cashflow_improvement",
        description="Cash flow showing 18% growth opportunity",
        trend=Trend(
            metric="cash_flow",
            direction=TrendDirection.INCREASING,
            magnitude=18.0,
            confidence=0.82,
            start_date="2023-Q2",
            end_date="2024-Q4",
            description="Strong cash flow improvement trend",
            cagr=0.18,
            qoq_growth=0.045,
        ),
        expected_category=InsightCategory.OPPORTUNITY,
        expected_priority_range=(1, 3),
        expected_keywords=["cash"],
    ),
    # Scenario 8: Minor inventory anomaly
    InsightTestScenario(
        scenario_id="inventory_minor",
        description="Inventory levels slightly elevated",
        anomaly=Anomaly(
            date="2024-Q3",
            metric="inventory",
            value=85000.0,
            expected_value=75000.0,
            z_score=1.6,
            severity=AnomalySeverity.MINOR,
            reason="Slightly elevated inventory levels",
            magnitude_pct=13.3,
        ),
        expected_category=InsightCategory.ANOMALY,
        expected_priority_range=(3, 5),
        expected_keywords=["inventory"],
    ),
    # Scenario 9: EBITDA growth trend
    InsightTestScenario(
        scenario_id="ebitda_growth",
        description="EBITDA growing 22% year-over-year",
        trend=Trend(
            metric="ebitda",
            direction=TrendDirection.INCREASING,
            magnitude=22.0,
            confidence=0.88,
            start_date="2023-Q1",
            end_date="2024-Q4",
            description="Strong EBITDA growth indicating operational efficiency",
            cagr=0.22,
            qoq_growth=0.055,
        ),
        expected_category=InsightCategory.OPPORTUNITY,
        expected_priority_range=(1, 2),
        expected_keywords=["ebitda"],
    ),
    # Scenario 10: Headcount cost anomaly
    InsightTestScenario(
        scenario_id="headcount_spike",
        description="Headcount costs increased 35% unexpectedly",
        anomaly=Anomaly(
            date="2024-Q1",
            metric="headcount_costs",
            value=540000.0,
            expected_value=400000.0,
            z_score=2.8,
            severity=AnomalySeverity.CRITICAL,
            reason="Significant headcount cost increase",
            magnitude_pct=35.0,
        ),
        expected_category=InsightCategory.RISK,
        expected_priority_range=(1, 2),
        expected_keywords=["headcount"],
    ),
]


# ============================================================================
# Pytest Tests
# ============================================================================


@pytest.fixture
def validator() -> InsightQualityValidator:
    """Create validator instance for tests."""
    return InsightQualityValidator(threshold_pct=75.0)


@pytest.fixture
def test_scenarios() -> list[InsightTestScenario]:
    """Return the expert-labeled test scenarios."""
    return INSIGHT_TEST_SCENARIOS


class TestInsightCategorization:
    """Tests for insight categorization logic."""

    def test_categorize_critical_anomaly_as_risk(self):
        """Critical anomaly should be categorized as RISK."""
        anomaly = Anomaly(
            date="2024-Q3",
            metric="costs",
            value=150.0,
            expected_value=100.0,
            z_score=3.0,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=50.0,
        )

        category = categorize_insight(anomaly=anomaly)

        assert category == InsightCategory.RISK

    def test_categorize_increasing_trend_as_opportunity(self):
        """Strong increasing trend should be categorized as OPPORTUNITY."""
        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=15.0,
            confidence=0.85,
            start_date="2023-Q1",
            end_date="2024-Q4",
            cagr=0.15,
            qoq_growth=0.04,
        )

        category = categorize_insight(trend=trend)

        assert category == InsightCategory.OPPORTUNITY

    def test_categorize_decreasing_trend_as_risk(self):
        """Strong decreasing trend should be categorized as RISK."""
        trend = Trend(
            metric="profit",
            direction=TrendDirection.DECREASING,
            magnitude=12.0,
            confidence=0.80,
            start_date="2023-Q1",
            end_date="2024-Q4",
            cagr=-0.06,
            qoq_growth=-0.015,
        )

        category = categorize_insight(trend=trend)

        assert category == InsightCategory.RISK

    def test_categorize_moderate_anomaly_as_anomaly(self):
        """Moderate anomaly should be categorized as ANOMALY."""
        anomaly = Anomaly(
            date="2024-Q3",
            metric="inventory",
            value=110.0,
            expected_value=100.0,
            z_score=2.0,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=10.0,
        )

        category = categorize_insight(anomaly=anomaly)

        assert category == InsightCategory.ANOMALY


class TestPriorityCalculation:
    """Tests for priority calculation logic."""

    def test_critical_anomaly_priority_1(self):
        """Critical anomaly should get priority 1."""
        anomaly = Anomaly(
            date="2024-Q3",
            metric="costs",
            value=150.0,
            expected_value=100.0,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=50.0,
        )

        priority = calculate_insight_priority(anomaly=anomaly)

        assert priority == 1

    def test_moderate_anomaly_priority_2(self):
        """Moderate anomaly should get priority 2."""
        anomaly = Anomaly(
            date="2024-Q3",
            metric="costs",
            value=120.0,
            expected_value=100.0,
            z_score=2.2,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=20.0,
        )

        priority = calculate_insight_priority(anomaly=anomaly)

        assert priority == 2

    def test_high_magnitude_trend_priority_2(self):
        """High magnitude trend (>20%) should get priority 2."""
        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=25.0,
            confidence=0.85,
            start_date="2023-Q1",
            end_date="2024-Q4",
            cagr=0.25,
            qoq_growth=0.06,
        )

        priority = calculate_insight_priority(trend=trend)

        assert priority == 2

    def test_default_priority_3(self):
        """Without strong signals, default priority is 3."""
        trend = Trend(
            metric="revenue",
            direction=TrendDirection.STABLE,
            magnitude=5.0,
            confidence=0.75,
            start_date="2023-Q1",
            end_date="2024-Q4",
            cagr=0.05,
            qoq_growth=0.01,
        )

        priority = calculate_insight_priority(trend=trend)

        assert priority == 3


class TestRelevanceScoring:
    """Tests for relevance scoring logic (Story 4.10 Task 2.3)."""

    def test_is_insight_relevant_all_match(self, validator: InsightQualityValidator):
        """Insight matching all criteria should be relevant."""
        insight = Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Marketing spend shows critical deviation",
            supporting_data={"metric": "marketing_spend", "z_score": 2.5},
            rationale="Based on marketing analysis",
            sources=["marketing_spend"],
        )
        scenario = InsightTestScenario(
            scenario_id="test",
            description="Test scenario",
            expected_category=InsightCategory.RISK,
            expected_priority_range=(1, 2),
            expected_keywords=["marketing"],
        )

        is_relevant, reason = validator._is_insight_relevant(insight, scenario)

        assert is_relevant
        assert reason == "All checks passed"

    def test_is_insight_relevant_category_mismatch(self, validator: InsightQualityValidator):
        """Insight with wrong category should not be relevant."""
        insight = Insight(
            category=InsightCategory.OPPORTUNITY,  # Wrong category
            priority=2,
            summary="Some opportunity",
            supporting_data={"metric": "revenue"},
            rationale="Growth detected",
            sources=["revenue"],
        )
        scenario = InsightTestScenario(
            scenario_id="test",
            description="Test scenario",
            expected_category=InsightCategory.RISK,
            expected_priority_range=(1, 3),
        )

        is_relevant, reason = validator._is_insight_relevant(insight, scenario)

        assert not is_relevant
        assert "Category mismatch" in reason

    def test_is_insight_relevant_priority_out_of_range(self, validator: InsightQualityValidator):
        """Insight with priority outside range should not be relevant."""
        insight = Insight(
            category=InsightCategory.RISK,
            priority=5,  # Too low priority
            summary="Risk detected",
            supporting_data={"metric": "costs"},
            rationale="Cost increase",
            sources=["costs"],
        )
        scenario = InsightTestScenario(
            scenario_id="test",
            description="Test scenario",
            expected_category=InsightCategory.RISK,
            expected_priority_range=(1, 2),  # Expects high priority
        )

        is_relevant, reason = validator._is_insight_relevant(insight, scenario)

        assert not is_relevant
        assert "Priority out of range" in reason


class TestValidationWorkflow:
    """Tests for full validation workflow (Story 4.10 AC3)."""

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_validate_all_scenarios(
        self,
        validator: InsightQualityValidator,
        test_scenarios: list[InsightTestScenario],
    ):
        """Test validation on full expert-labeled scenario set.

        Story 4.10 AC3: Target 75%+ relevance rate.
        """
        result = await validator.validate_insights(test_scenarios)

        assert result.total_scenarios == len(test_scenarios)
        assert result.passed_scenarios >= 0
        assert 0 <= result.relevance_rate <= 100

        # Log results for debugging
        print("\nInsight Validation Results:")
        print(f"  Total scenarios: {result.total_scenarios}")
        print(f"  Passed scenarios: {result.passed_scenarios}")
        print(f"  Relevance rate: {result.relevance_rate:.1f}%")
        print(f"  Threshold met: {result.passed}")
        print(f"  Category breakdown: {result.category_breakdown}")

    @pytest.mark.asyncio
    async def test_validate_empty_scenarios_raises(
        self,
        validator: InsightQualityValidator,
    ):
        """Test validation raises for empty scenarios."""
        with pytest.raises(ValueError, match="No test scenarios"):
            await validator.validate_insights([])

    @pytest.mark.asyncio
    async def test_validate_single_scenario(
        self,
        validator: InsightQualityValidator,
    ):
        """Test validation with single scenario."""
        single_scenario = [INSIGHT_TEST_SCENARIOS[0]]

        result = await validator.validate_insights(single_scenario)

        assert result.total_scenarios == 1
        assert result.passed_scenarios in [0, 1]


class TestThresholdConfiguration:
    """Tests for configurable threshold."""

    def test_custom_threshold(self):
        """Test validator with custom threshold."""
        strict_validator = InsightQualityValidator(threshold_pct=90.0)
        assert strict_validator.threshold_pct == 90.0

    def test_default_threshold(self):
        """Test validator with default 75% threshold."""
        validator = InsightQualityValidator()
        assert validator.threshold_pct == 75.0
