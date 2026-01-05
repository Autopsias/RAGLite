"""Shared pytest fixtures for strategic recommendation tests.

These fixtures are imported by all test modules in this package.
"""

from datetime import UTC, datetime

import pytest

from raglite.shared.models import Insight, InsightCategory


@pytest.fixture
def sample_risk_insight() -> Insight:
    """Create a sample RISK insight (priority 1)."""
    return Insight(
        category=InsightCategory.RISK,
        priority=1,
        summary="Marketing spend increased 30% YoY with no revenue increase",
        supporting_data={
            "marketing_spend_yoy_change": 0.30,
            "revenue_yoy_change": 0.02,
            "metric": "marketing_spend",
        },
        rationale="Potential marketing inefficiency detected",
        sources=["marketing_spend", "revenue"],
        recommended_action="Review marketing ROI",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_opportunity_insight() -> Insight:
    """Create a sample OPPORTUNITY insight (priority 2)."""
    return Insight(
        category=InsightCategory.OPPORTUNITY,
        priority=2,
        summary="Revenue growth trending 15% above forecast",
        supporting_data={
            "revenue_growth": 0.15,
            "forecast_variance": 0.15,
            "metric": "revenue",
        },
        rationale="Strong sales performance in Q3",
        sources=["revenue"],
        recommended_action="Accelerate growth initiatives",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_anomaly_insight() -> Insight:
    """Create a sample ANOMALY insight (priority 3)."""
    return Insight(
        category=InsightCategory.ANOMALY,
        priority=3,
        summary="Unusual spike in cloud costs detected",
        supporting_data={
            "cloud_costs": 3000000,
            "expected_costs": 2000000,
            "z_score": 2.5,
        },
        rationale="Cloud costs 50% above baseline",
        sources=["cloud_costs"],
        recommended_action="Investigate cloud usage",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_trend_insight() -> Insight:
    """Create a sample TREND insight (priority 4)."""
    return Insight(
        category=InsightCategory.TREND,
        priority=4,
        summary="Operating expenses showing stable pattern",
        supporting_data={
            "metric": "operating_expenses",
            "direction": "stable",
            "magnitude": 2.5,
        },
        rationale="Expenses remain within budget",
        sources=["operating_expenses"],
        recommended_action="Continue monitoring",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_strategic_priority_insight() -> Insight:
    """Create a sample STRATEGIC_PRIORITY insight (priority 2)."""
    return Insight(
        category=InsightCategory.STRATEGIC_PRIORITY,
        priority=2,
        summary="Capital expenditure planning needed for next fiscal year",
        supporting_data={
            "capex_budget": 10000000,
            "utilization_rate": 0.85,
        },
        rationale="Current assets nearing capacity",
        sources=["capex", "utilization"],
        recommended_action="Initiate capex planning",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def cost_opportunity_insight() -> Insight:
    """Create an OPPORTUNITY insight about cost reduction."""
    return Insight(
        category=InsightCategory.OPPORTUNITY,
        priority=2,
        summary="Cloud infrastructure costs trending 40% under budget",
        supporting_data={
            "cloud_budget": 5000000,
            "cloud_actual": 3000000,
            "cost_savings": 2000000,
        },
        rationale="Significant cost savings opportunity",
        sources=["cloud_costs"],
        recommended_action="Reallocate budget savings",
        created_at=datetime.now(UTC),
    )
