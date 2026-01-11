"""Expert-labeled test scenarios for recommendation validation.

Story 4.10 Task 3.2: Expert-labeled ground truth for recommendation testing.
"""

from raglite.shared.models import Insight, InsightCategory, RecommendationCategory

from .models import RecommendationTestScenario

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
