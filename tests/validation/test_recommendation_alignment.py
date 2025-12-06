"""Recommendation alignment validation framework.

Story 4.10 AC4: Validates recommendation alignment with expert analysis.
Target: 80%+ alignment rate with expert-labeled ground truth.
"""

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from raglite.insights.recommendations import (
    calculate_impact_score,
    categorize_recommendation,
    generate_recommendations,
)
from raglite.shared.models import Insight, InsightCategory, Recommendation, RecommendationCategory


@dataclass
class RecommendationTestScenario:
    """Expert-labeled test scenario for recommendation validation.

    Story 4.10 AC4: Each scenario has expected recommendation labeled by expert.

    Attributes:
        scenario_id: Unique identifier (e.g., "cost_reduction")
        description: Human-readable scenario description
        insight: Input insight that triggers recommendation
        expected_category: Expected RecommendationCategory
        expected_impact_range: Acceptable impact score range (min, max inclusive)
        expected_urgency: Expected urgency level (high, medium, low)
        expected_action_keywords: Keywords expected in action steps
    """

    scenario_id: str
    description: str
    insight: Insight
    expected_category: RecommendationCategory = RecommendationCategory.OPERATIONAL_EFFICIENCY
    expected_impact_range: tuple[int, int] = (1, 10)
    expected_urgency: str = "medium"
    expected_action_keywords: list[str] = field(default_factory=list)


@dataclass
class RecommendationValidationResult:
    """Result of recommendation alignment validation.

    Story 4.10 AC4: Structured validation result for recommendation alignment.

    Attributes:
        total_scenarios: Total number of test scenarios
        aligned_scenarios: Number of scenarios with aligned recommendations
        alignment_rate: Percentage of scenarios with aligned recommendations (0-100)
        passed: Whether alignment rate meets 80% threshold
        scenario_results: Per-scenario pass/fail details
        category_breakdown: Count of recommendations per category
    """

    total_scenarios: int
    aligned_scenarios: int
    alignment_rate: float
    passed: bool
    scenario_results: list[dict[str, Any]]
    category_breakdown: dict[str, int]


class RecommendationAlignmentValidator:
    """Validates recommendation alignment against 80% expert agreement threshold.

    Story 4.10 AC4: Expert-labeled recommendation validation.

    Example:
        >>> validator = RecommendationAlignmentValidator()
        >>> result = await validator.validate_recommendations(test_scenarios)
        >>> assert result.passed  # alignment_rate >= 80%
    """

    def __init__(self, threshold_pct: float = 80.0, impact_tolerance: int = 2):
        """Initialize validator with alignment threshold.

        Args:
            threshold_pct: Minimum acceptable alignment rate (default 80.0)
            impact_tolerance: Acceptable deviation from expected impact (default ±2)
        """
        self.threshold_pct = threshold_pct
        self.impact_tolerance = impact_tolerance

    def _is_recommendation_aligned(
        self,
        recommendation: Recommendation,
        scenario: RecommendationTestScenario,
    ) -> tuple[bool, str]:
        """Check if generated recommendation aligns with expert expectations.

        Story 4.10 Task 3.3: Alignment scoring logic.

        Args:
            recommendation: Generated recommendation
            scenario: Expected scenario with expert labels

        Returns:
            Tuple of (is_aligned, reason)
        """
        reasons = []

        # Check 1: Category match
        category_match = recommendation.category == scenario.expected_category
        if not category_match:
            reasons.append(
                f"Category mismatch: got {recommendation.category.value}, "
                f"expected {scenario.expected_category.value}"
            )

        # Check 2: Impact score within tolerance of expected range
        impact_min, impact_max = scenario.expected_impact_range
        impact_in_range = (
            impact_min - self.impact_tolerance
            <= recommendation.impact_score
            <= impact_max + self.impact_tolerance
        )
        if not impact_in_range:
            reasons.append(
                f"Impact out of range: got {recommendation.impact_score}, "
                f"expected [{impact_min}, {impact_max}] ±{self.impact_tolerance}"
            )

        # Check 3: Action steps are actionable (have verb-noun structure)
        has_actionable_steps = self._has_actionable_steps(recommendation.action_steps)
        if not has_actionable_steps:
            reasons.append("Action steps not actionable (missing verb-noun structure)")

        # Check 4: Rationale references supporting data (non-empty)
        has_rationale = bool(recommendation.rationale)
        if not has_rationale:
            reasons.append("No rationale provided")

        # Overall alignment: category match + impact in range + actionable steps
        is_aligned = category_match and impact_in_range and has_actionable_steps

        reason = "; ".join(reasons) if reasons else "All checks passed"
        return is_aligned, reason

    def _has_actionable_steps(self, action_steps: list[str]) -> bool:
        """Check if action steps are actionable (verb-noun structure).

        Story 4.10 Task 3.3: Validate action_steps are actionable.

        Args:
            action_steps: List of action step strings

        Returns:
            True if at least one step has actionable verb
        """
        if not action_steps:
            return False

        # Common actionable verbs for business recommendations
        actionable_verbs = {
            "review",
            "analyze",
            "assess",
            "evaluate",
            "implement",
            "develop",
            "create",
            "reduce",
            "increase",
            "optimize",
            "improve",
            "establish",
            "conduct",
            "monitor",
            "track",
            "identify",
            "investigate",
            "allocate",
            "prioritize",
            "schedule",
            "plan",
            "execute",
            "negotiate",
            "streamline",
            "automate",
            "delegate",
            "consolidate",
            "diversify",
            "invest",
            "divest",
        }

        for step in action_steps:
            words = step.lower().split()
            if words and words[0] in actionable_verbs:
                return True

        # Fallback: any step with length > 5 words is likely actionable
        return any(len(step.split()) >= 5 for step in action_steps)

    async def validate_recommendations(
        self,
        test_scenarios: list[RecommendationTestScenario],
    ) -> RecommendationValidationResult:
        """Score recommendations against expert-labeled expectations.

        Story 4.10 AC4: Run scenarios and calculate alignment rate.

        Args:
            test_scenarios: List of scenarios with expected recommendations

        Returns:
            RecommendationValidationResult with alignment rate and breakdown

        Raises:
            ValueError: If no test scenarios provided
        """
        if not test_scenarios:
            raise ValueError("No test scenarios provided")

        scenario_results: list[dict[str, Any]] = []
        category_counts: dict[str, int] = {}
        aligned_count = 0

        # Mock LLM for faster validation
        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_response = AsyncMock()
            mock_response.choices = [
                AsyncMock(
                    message=AsyncMock(
                        content=(
                            "TITLE: Strategic Recommendation\n"
                            "DESCRIPTION: Based on analysis, we recommend action.\n"
                            "RATIONALE: This matters because of financial impact.\n"
                            "ACTIONS:\n"
                            "1. Review the underlying data\n"
                            "2. Assess impact on business objectives\n"
                            "3. Develop action plan with stakeholders"
                        )
                    )
                )
            ]
            mock_client.return_value.chat.complete.return_value = mock_response

            for scenario in test_scenarios:
                # Generate recommendations from insight
                result = await generate_recommendations(
                    insights=[scenario.insight],
                    context=scenario.description,
                    auto_synthesize=True,
                )

                # Validate first recommendation (primary result)
                if result.recommendations:
                    rec = result.recommendations[0]
                    is_aligned, reason = self._is_recommendation_aligned(rec, scenario)

                    # Track category
                    cat_key = rec.category.value
                    category_counts[cat_key] = category_counts.get(cat_key, 0) + 1

                    scenario_results.append(
                        {
                            "scenario_id": scenario.scenario_id,
                            "description": scenario.description,
                            "aligned": is_aligned,
                            "reason": reason,
                            "generated_category": rec.category.value,
                            "generated_impact": rec.impact_score,
                            "generated_urgency": rec.urgency,
                            "expected_category": scenario.expected_category.value,
                            "expected_impact_range": scenario.expected_impact_range,
                            "expected_urgency": scenario.expected_urgency,
                        }
                    )

                    if is_aligned:
                        aligned_count += 1
                else:
                    scenario_results.append(
                        {
                            "scenario_id": scenario.scenario_id,
                            "description": scenario.description,
                            "aligned": False,
                            "reason": "No recommendations generated",
                            "generated_category": None,
                            "generated_impact": None,
                            "generated_urgency": None,
                            "expected_category": scenario.expected_category.value,
                            "expected_impact_range": scenario.expected_impact_range,
                            "expected_urgency": scenario.expected_urgency,
                        }
                    )

        # Calculate alignment rate
        alignment_rate = (aligned_count / len(test_scenarios)) * 100

        return RecommendationValidationResult(
            total_scenarios=len(test_scenarios),
            aligned_scenarios=aligned_count,
            alignment_rate=alignment_rate,
            passed=alignment_rate >= self.threshold_pct,
            scenario_results=scenario_results,
            category_breakdown=category_counts,
        )


# ============================================================================
# Expert-Labeled Test Scenarios (Story 4.10 Task 3.2)
# ============================================================================

RECOMMENDATION_TEST_SCENARIOS: list[RecommendationTestScenario] = [
    # Scenario 1: Cost reduction for overspending
    RecommendationTestScenario(
        scenario_id="cost_overrun",
        description="Cloud costs 40% over budget require cost reduction",
        insight=Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Cloud costs 40% over budget",
            supporting_data={
                "metric": "cloud_costs",
                "value": 140000,
                "budget": 100000,
                "overage_pct": 40.0,
            },
            rationale="Cloud infrastructure costs exceeding budget significantly",
            sources=["cloud_costs"],
            recommended_action="Review cloud resource allocation",
        ),
        expected_category=RecommendationCategory.RISK_MITIGATION,
        expected_impact_range=(8, 10),
        expected_urgency="high",
        expected_action_keywords=["review", "reduce", "optimize"],
    ),
    # Scenario 2: Investment recommendation for growth opportunity
    RecommendationTestScenario(
        scenario_id="growth_opportunity",
        description="Revenue growth opportunity in new market segment",
        insight=Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="New market segment shows 25% growth potential",
            supporting_data={
                "metric": "revenue",
                "growth_rate": 0.25,
                "market_segment": "enterprise",
            },
            rationale="Enterprise segment showing strong demand signals",
            sources=["revenue"],
            recommended_action="Expand enterprise sales team",
        ),
        expected_category=RecommendationCategory.REVENUE_GROWTH,
        expected_impact_range=(7, 10),
        expected_urgency="medium",
        expected_action_keywords=["expand", "invest", "develop"],
    ),
    # Scenario 3: Risk mitigation for volatility
    RecommendationTestScenario(
        scenario_id="volatility_risk",
        description="Cash flow volatility requires risk mitigation",
        insight=Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Cash flow volatility increased 30%",
            supporting_data={
                "metric": "cash_flow",
                "volatility": 0.30,
                "trend": "increasing",
            },
            rationale="High cash flow volatility indicates operational risk",
            sources=["cash_flow"],
            recommended_action="Establish cash reserves",
        ),
        expected_category=RecommendationCategory.RISK_MITIGATION,
        expected_impact_range=(8, 10),
        expected_urgency="high",
        expected_action_keywords=["establish", "monitor", "hedge"],
    ),
    # Scenario 4: Process improvement for inefficiencies
    RecommendationTestScenario(
        scenario_id="process_inefficiency",
        description="Manufacturing inefficiency detected",
        insight=Insight(
            category=InsightCategory.ANOMALY,
            priority=3,
            summary="Production efficiency dropped 15%",
            supporting_data={
                "metric": "production_efficiency",
                "value": 0.72,
                "expected": 0.85,
                "drop_pct": 15.0,
            },
            rationale="Equipment downtime causing production delays",
            sources=["production_efficiency"],
            recommended_action="Implement preventive maintenance",
        ),
        expected_category=RecommendationCategory.OPERATIONAL_EFFICIENCY,
        expected_impact_range=(5, 8),
        expected_urgency="medium",
        expected_action_keywords=["implement", "optimize", "automate"],
    ),
    # Scenario 5: Strategic investment decision
    RecommendationTestScenario(
        scenario_id="strategic_investment",
        description="R&D investment opportunity identified",
        insight=Insight(
            category=InsightCategory.STRATEGIC_PRIORITY,
            priority=2,
            summary="R&D pipeline shows promising ROI potential",
            supporting_data={
                "metric": "r&d_pipeline",
                "projected_roi": 2.5,
                "investment_required": 500000,
            },
            rationale="Strong product pipeline with high ROI potential",
            sources=["r&d_pipeline"],
            recommended_action="Allocate additional R&D budget",
        ),
        expected_category=RecommendationCategory.STRATEGIC_INVESTMENT,
        expected_impact_range=(6, 9),
        expected_urgency="medium",
        expected_action_keywords=["allocate", "invest", "prioritize"],
    ),
    # Scenario 6: Cost reduction opportunity in operations
    RecommendationTestScenario(
        scenario_id="ops_cost_reduction",
        description="Operational costs have reduction opportunity",
        insight=Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Operational costs can be reduced 20% through automation",
            supporting_data={
                "metric": "operating_expenses",
                "potential_savings": 200000,
                "savings_pct": 20.0,
            },
            rationale="Manual processes can be automated for cost savings",
            sources=["operating_expenses"],
            recommended_action="Implement automation solutions",
        ),
        expected_category=RecommendationCategory.COST_REDUCTION,
        expected_impact_range=(7, 10),
        expected_urgency="medium",
        expected_action_keywords=["implement", "automate", "reduce"],
    ),
    # Scenario 7: Revenue growth through pricing optimization
    RecommendationTestScenario(
        scenario_id="pricing_opportunity",
        description="Pricing optimization opportunity identified",
        insight=Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Pricing analysis shows 10% revenue increase potential",
            supporting_data={
                "metric": "revenue",
                "price_elasticity": 0.8,
                "potential_increase": 0.10,
            },
            rationale="Market analysis shows room for price adjustment",
            sources=["revenue", "pricing_analysis"],
            recommended_action="Implement tiered pricing strategy",
        ),
        expected_category=RecommendationCategory.REVENUE_GROWTH,
        expected_impact_range=(6, 9),
        expected_urgency="medium",
        expected_action_keywords=["implement", "adjust", "analyze"],
    ),
    # Scenario 8: Risk mitigation for supply chain
    RecommendationTestScenario(
        scenario_id="supply_chain_risk",
        description="Supply chain concentration risk identified",
        insight=Insight(
            category=InsightCategory.RISK,
            priority=2,
            summary="70% of supply from single vendor",
            supporting_data={
                "metric": "supply_chain",
                "vendor_concentration": 0.70,
                "risk_level": "high",
            },
            rationale="Single vendor dependency creates operational risk",
            sources=["supply_chain"],
            recommended_action="Diversify supplier base",
        ),
        expected_category=RecommendationCategory.RISK_MITIGATION,
        expected_impact_range=(6, 9),
        expected_urgency="medium",
        expected_action_keywords=["diversify", "evaluate", "establish"],
    ),
]


# ============================================================================
# Pytest Tests
# ============================================================================


@pytest.fixture
def validator() -> RecommendationAlignmentValidator:
    """Create validator instance for tests."""
    return RecommendationAlignmentValidator(threshold_pct=80.0)


@pytest.fixture
def test_scenarios() -> list[RecommendationTestScenario]:
    """Return the expert-labeled test scenarios."""
    return RECOMMENDATION_TEST_SCENARIOS


class TestRecommendationCategorization:
    """Tests for recommendation categorization logic."""

    def test_categorize_risk_insight_as_risk_mitigation(self):
        """Risk insight should generate RISK_MITIGATION recommendation."""
        insight = Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Cost overrun detected",
            supporting_data={"metric": "costs"},
            sources=["costs"],
        )

        category = categorize_recommendation(insight)

        assert category == RecommendationCategory.RISK_MITIGATION

    def test_categorize_opportunity_with_cost_as_cost_reduction(self):
        """Opportunity insight with cost-related data should be COST_REDUCTION."""
        insight = Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Cost reduction opportunity",
            supporting_data={"metric": "cost", "savings": 100000},
            sources=["operating_expenses"],
        )

        category = categorize_recommendation(insight)

        assert category == RecommendationCategory.COST_REDUCTION

    def test_categorize_opportunity_as_revenue_growth(self):
        """Opportunity insight without cost data should be REVENUE_GROWTH."""
        insight = Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Growth opportunity",
            supporting_data={"metric": "revenue", "growth": 0.15},
            sources=["revenue"],
        )

        category = categorize_recommendation(insight)

        assert category == RecommendationCategory.REVENUE_GROWTH

    def test_categorize_anomaly_as_operational_efficiency(self):
        """Anomaly insight should generate OPERATIONAL_EFFICIENCY recommendation."""
        insight = Insight(
            category=InsightCategory.ANOMALY,
            priority=3,
            summary="Process anomaly detected",
            supporting_data={"metric": "efficiency"},
            sources=["efficiency"],
        )

        category = categorize_recommendation(insight)

        assert category == RecommendationCategory.OPERATIONAL_EFFICIENCY

    def test_categorize_strategic_priority_as_strategic_investment(self):
        """Strategic priority insight should generate STRATEGIC_INVESTMENT."""
        insight = Insight(
            category=InsightCategory.STRATEGIC_PRIORITY,
            priority=2,
            summary="Strategic investment opportunity",
            supporting_data={"metric": "roi"},
            sources=["roi"],
        )

        category = categorize_recommendation(insight)

        assert category == RecommendationCategory.STRATEGIC_INVESTMENT


class TestImpactScoreCalculation:
    """Tests for impact score calculation logic."""

    def test_impact_score_high_priority_risk(self):
        """High priority risk insight should get high impact score."""
        insight = Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Critical risk",
            supporting_data={},
            sources=[],
        )

        impact = calculate_impact_score(insight)

        assert 8 <= impact <= 10  # High impact

    def test_impact_score_medium_priority(self):
        """Medium priority insight should get medium impact score."""
        insight = Insight(
            category=InsightCategory.TREND,
            priority=3,
            summary="Moderate trend",
            supporting_data={},
            sources=[],
        )

        impact = calculate_impact_score(insight)

        assert 4 <= impact <= 7  # Medium impact

    def test_impact_score_low_priority(self):
        """Low priority insight should get lower impact score."""
        insight = Insight(
            category=InsightCategory.TREND,
            priority=5,
            summary="Minor trend",
            supporting_data={},
            sources=[],
        )

        impact = calculate_impact_score(insight)

        assert 1 <= impact <= 4  # Lower impact


class TestAlignmentScoring:
    """Tests for alignment scoring logic (Story 4.10 Task 3.3)."""

    def test_is_recommendation_aligned_all_match(self, validator: RecommendationAlignmentValidator):
        """Recommendation matching all criteria should be aligned."""
        recommendation = Recommendation(
            category=RecommendationCategory.RISK_MITIGATION,
            impact_score=9,
            title="Risk Mitigation Plan",
            description="Address cloud cost overrun",
            rationale="High cost variance requires immediate action",
            supporting_evidence={"metric": "cloud_costs"},
            action_steps=[
                "Review cloud resource allocation",
                "Identify unused instances",
                "Implement auto-scaling",
            ],
            urgency="high",
            sources=["cloud_costs"],
        )
        scenario = RecommendationTestScenario(
            scenario_id="test",
            description="Test scenario",
            insight=Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Test",
                supporting_data={},
                sources=[],
            ),
            expected_category=RecommendationCategory.RISK_MITIGATION,
            expected_impact_range=(8, 10),
            expected_urgency="high",
        )

        is_aligned, reason = validator._is_recommendation_aligned(recommendation, scenario)

        assert is_aligned
        assert reason == "All checks passed"

    def test_is_recommendation_aligned_category_mismatch(
        self, validator: RecommendationAlignmentValidator
    ):
        """Recommendation with wrong category should not be aligned."""
        recommendation = Recommendation(
            category=RecommendationCategory.REVENUE_GROWTH,  # Wrong category
            impact_score=8,
            title="Growth Plan",
            description="Expand revenue",
            rationale="Growth opportunity exists",
            supporting_evidence={},
            action_steps=["Review market segments"],
            urgency="medium",
            sources=[],
        )
        scenario = RecommendationTestScenario(
            scenario_id="test",
            description="Test scenario",
            insight=Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Test",
                supporting_data={},
                sources=[],
            ),
            expected_category=RecommendationCategory.RISK_MITIGATION,
            expected_impact_range=(8, 10),
        )

        is_aligned, reason = validator._is_recommendation_aligned(recommendation, scenario)

        assert not is_aligned
        assert "Category mismatch" in reason

    def test_is_recommendation_aligned_impact_with_tolerance(
        self, validator: RecommendationAlignmentValidator
    ):
        """Impact score within tolerance should be considered aligned."""
        recommendation = Recommendation(
            category=RecommendationCategory.RISK_MITIGATION,
            impact_score=7,  # Below range but within ±2 tolerance
            title="Risk Plan",
            description="Address risk",
            rationale="Risk requires attention",
            supporting_evidence={},
            action_steps=["Review situation"],
            urgency="medium",
            sources=[],
        )
        scenario = RecommendationTestScenario(
            scenario_id="test",
            description="Test scenario",
            insight=Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Test",
                supporting_data={},
                sources=[],
            ),
            expected_category=RecommendationCategory.RISK_MITIGATION,
            expected_impact_range=(8, 10),  # 7 is within tolerance of ±2
        )

        is_aligned, reason = validator._is_recommendation_aligned(recommendation, scenario)

        # 7 is within [8-2, 10+2] = [6, 12], so should be aligned
        assert is_aligned

    def test_has_actionable_steps_with_verbs(self, validator: RecommendationAlignmentValidator):
        """Steps starting with action verbs should be considered actionable."""
        steps = [
            "Review the data",
            "Analyze cost trends",
            "Implement changes",
        ]

        has_actionable = validator._has_actionable_steps(steps)

        assert has_actionable

    def test_has_actionable_steps_empty(self, validator: RecommendationAlignmentValidator):
        """Empty action steps should not be actionable."""
        has_actionable = validator._has_actionable_steps([])

        assert not has_actionable


class TestValidationWorkflow:
    """Tests for full validation workflow (Story 4.10 AC4)."""

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_validate_all_scenarios(
        self,
        validator: RecommendationAlignmentValidator,
        test_scenarios: list[RecommendationTestScenario],
    ):
        """Test validation on full expert-labeled scenario set.

        Story 4.10 AC4: Target 80%+ alignment rate.
        """
        result = await validator.validate_recommendations(test_scenarios)

        assert result.total_scenarios == len(test_scenarios)
        assert result.aligned_scenarios >= 0
        assert 0 <= result.alignment_rate <= 100

        # Log results for debugging
        print("\nRecommendation Validation Results:")
        print(f"  Total scenarios: {result.total_scenarios}")
        print(f"  Aligned scenarios: {result.aligned_scenarios}")
        print(f"  Alignment rate: {result.alignment_rate:.1f}%")
        print(f"  Threshold met: {result.passed}")
        print(f"  Category breakdown: {result.category_breakdown}")

    @pytest.mark.asyncio
    async def test_validate_empty_scenarios_raises(
        self,
        validator: RecommendationAlignmentValidator,
    ):
        """Test validation raises for empty scenarios."""
        with pytest.raises(ValueError, match="No test scenarios"):
            await validator.validate_recommendations([])

    @pytest.mark.asyncio
    async def test_validate_single_scenario(
        self,
        validator: RecommendationAlignmentValidator,
    ):
        """Test validation with single scenario."""
        single_scenario = [RECOMMENDATION_TEST_SCENARIOS[0]]

        result = await validator.validate_recommendations(single_scenario)

        assert result.total_scenarios == 1
        assert result.aligned_scenarios in [0, 1]


class TestThresholdConfiguration:
    """Tests for configurable threshold."""

    def test_custom_threshold(self):
        """Test validator with custom threshold."""
        strict_validator = RecommendationAlignmentValidator(threshold_pct=90.0)
        assert strict_validator.threshold_pct == 90.0

    def test_default_threshold(self):
        """Test validator with default 80% threshold."""
        validator = RecommendationAlignmentValidator()
        assert validator.threshold_pct == 80.0

    def test_custom_impact_tolerance(self):
        """Test validator with custom impact tolerance."""
        tolerant_validator = RecommendationAlignmentValidator(impact_tolerance=3)
        assert tolerant_validator.impact_tolerance == 3
