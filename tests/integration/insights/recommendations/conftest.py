"""Shared fixtures for strategic recommendations tests."""

from datetime import UTC, datetime

import pytest

from raglite.shared.models import (
    Insight,
    InsightCategory,
    RecommendationCategory,
)

# =============================================================================
# Expert-Labeled Test Scenarios
# =============================================================================

EXPERT_LABELED_SCENARIOS = {
    "cloud_cost_over_budget": {
        "insight": Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Cloud infrastructure costs trending 40% over budget with minimal usage increase",
            supporting_data={
                "cloud_budget": 5000000,
                "cloud_actual": 7000000,
                "budget_variance": 0.40,
                "usage_increase": 0.05,
            },
            rationale="Cloud spending has significantly exceeded budget without corresponding usage increase",
            sources=["cloud_costs", "infrastructure_budget"],
            recommended_action="Focus on reducing cloud infrastructure costs",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.RISK_MITIGATION,
        "expected_impact_min": 8,
        "expected_urgency": "high",
        "expected_title_keywords": ["cloud", "cost", "infrastructure", "reduce"],
    },
    "marketing_inefficiency_risk": {
        "insight": Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Marketing spend increased 30% YoY with no corresponding revenue increase",
            supporting_data={
                "marketing_spend_yoy_change": 0.30,
                "revenue_yoy_change": 0.02,
            },
            rationale="Marketing ROI has declined significantly",
            sources=["marketing_spend", "revenue"],
            recommended_action="Review marketing channel effectiveness",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.RISK_MITIGATION,
        "expected_impact_min": 8,
        "expected_urgency": "high",
        "expected_title_keywords": ["marketing", "roi", "efficiency"],
    },
    "revenue_growth_opportunity": {
        "insight": Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Revenue growth trending 25% above forecast in emerging markets",
            supporting_data={
                "revenue_growth": 0.25,
                "forecast_variance": 0.25,
                "market": "emerging",
            },
            rationale="Strong market expansion opportunity",
            sources=["revenue", "market_analysis"],
            recommended_action="Accelerate emerging market investment",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.REVENUE_GROWTH,
        "expected_impact_min": 6,
        "expected_urgency_in": ["high", "medium"],
        "expected_title_keywords": ["revenue", "growth", "market", "expand"],
    },
    "cost_savings_opportunity": {
        "insight": Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Vendor consolidation could reduce procurement costs by 20%",
            supporting_data={
                "cost_savings_potential": 0.20,
                "vendor_count": 45,
                "category": "procurement",
            },
            rationale="Opportunity to reduce expenses through vendor consolidation",
            sources=["procurement_costs", "vendor_analysis"],
            recommended_action="Initiate vendor consolidation program",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.COST_REDUCTION,
        "expected_impact_min": 6,
        "expected_title_keywords": ["cost", "vendor", "consolidat", "procure"],
    },
    "operational_anomaly": {
        "insight": Insight(
            category=InsightCategory.ANOMALY,
            priority=3,
            summary="Unusual spike in overtime hours across production departments",
            supporting_data={
                "overtime_hours": 15000,
                "baseline_hours": 8000,
                "z_score": 2.8,
            },
            rationale="Production capacity may be constrained",
            sources=["hr_data", "production_metrics"],
            recommended_action="Investigate production capacity constraints",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.OPERATIONAL_EFFICIENCY,
        "expected_impact_min": 4,
        "expected_title_keywords": ["operation", "production", "capacity", "overtime"],
    },
    "strategic_investment_needed": {
        "insight": Insight(
            category=InsightCategory.STRATEGIC_PRIORITY,
            priority=2,
            summary="Capital expenditure planning required for manufacturing expansion",
            supporting_data={
                "capex_need": 50000000,
                "capacity_utilization": 0.92,
                "growth_forecast": 0.15,
            },
            rationale="Current manufacturing capacity nearing limits",
            sources=["capex_planning", "manufacturing_capacity"],
            recommended_action="Approve capex for manufacturing expansion",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.STRATEGIC_INVESTMENT,
        "expected_impact_min": 6,
        "expected_title_keywords": ["invest", "capex", "expansion", "manufactur"],
    },
}


@pytest.fixture
def all_expert_scenarios() -> dict:
    """Return all expert-labeled scenarios."""
    return EXPERT_LABELED_SCENARIOS


@pytest.fixture
def cloud_cost_scenario() -> dict:
    """Return the cloud cost over budget scenario (AC5)."""
    return EXPERT_LABELED_SCENARIOS["cloud_cost_over_budget"]
