"""Shared fixtures for insights module tests.

Provides common test data fixtures for Anomaly, Trend, Insight, ForecastResult models.

Available Fixtures:
    sample_anomalies: List[Anomaly] - Marketing spend anomaly (moderate severity)
    sample_trends: List[Trend] - Revenue stable trend (2% magnitude)
    sample_forecasts: List[ForecastResult] - Cash flow forecast (Q1 2025)
    sample_risk_insight: Insight - RISK category (priority 1)
    sample_opportunity_insight: Insight - OPPORTUNITY category (priority 2)
    sample_anomaly_insight: Insight - ANOMALY category (priority 3)
    sample_trend_insight: Insight - TREND category (priority 4)
    sample_strategic_priority_insight: Insight - STRATEGIC_PRIORITY category (priority 2)
    cost_opportunity_insight: Insight - OPPORTUNITY with cost reduction potential
    sample_insights: List[Insight] - Collection of 5 diverse insights for filtering tests
    mock_mistral_response: MagicMock - Mock Mistral API response for recommendation generation

Usage:
    @pytest.mark.asyncio
    async def test_my_feature(sample_risk_insight: Insight):
        result = await analyze_insight(sample_risk_insight)
        assert result.priority == 1
"""

from datetime import UTC, datetime

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    ForecastPoint,
    ForecastResult,
    Insight,
    InsightCategory,
    Trend,
    TrendDirection,
)


@pytest.fixture
def sample_anomalies() -> list[Anomaly]:
    """Create sample anomalies for testing."""
    return [
        Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=2.5,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=30.0,
        ),
    ]


@pytest.fixture
def sample_trends() -> list[Trend]:
    """Create sample trends for testing."""
    return [
        Trend(
            metric="revenue",
            direction=TrendDirection.STABLE,
            magnitude=2.0,
            confidence=0.9,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.02,
            qoq_growth=0.5,
        ),
    ]


@pytest.fixture
def sample_forecasts() -> list[ForecastResult]:
    """Create sample forecasts for testing."""
    return [
        ForecastResult(
            metric_name="cash_flow",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=1100000,
                    lower=1000000,
                    upper=1200000,
                )
            ],
            periods_ahead=4,
        ),
    ]


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
    """Create an OPPORTUNITY insight with cost reduction potential."""
    return Insight(
        category=InsightCategory.OPPORTUNITY,
        priority=2,
        summary="Cloud infrastructure optimization can reduce costs 25%",
        supporting_data={
            "current_spend": 4000000,
            "potential_savings": 1000000,
            "optimization_type": "cost_reduction",
        },
        rationale="Unused cloud resources identified",
        sources=["cloud_costs"],
        recommended_action="Optimize cloud infrastructure",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_insights() -> list[Insight]:
    """Create sample insights for filtering tests.

    Returns 5 insights with varying categories and priorities:
    - RISK (priority 1): Critical risk
    - OPPORTUNITY (priority 2): Growth opportunity
    - RISK (priority 3): Medium risk
    - ANOMALY (priority 4): Minor anomaly
    - TREND (priority 5): Stable trend
    """
    return [
        Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Critical risk",
        ),
        Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Growth opportunity",
        ),
        Insight(
            category=InsightCategory.RISK,
            priority=3,
            summary="Medium risk",
        ),
        Insight(
            category=InsightCategory.ANOMALY,
            priority=4,
            summary="Minor anomaly",
        ),
        Insight(
            category=InsightCategory.TREND,
            priority=5,
            summary="Stable trend",
        ),
    ]


@pytest.fixture
def mock_mistral_response():
    """Create a mock Mistral response for recommendation generation.

    Returns a MagicMock with properly structured response containing:
    - TITLE: Optimize Marketing ROI
    - DESCRIPTION: Review and optimize marketing spend allocation
    - RATIONALE: Marketing efficiency has declined significantly
    - ACTIONS: 4-step action plan
    """
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """TITLE: Optimize Marketing ROI
DESCRIPTION: Review and optimize marketing spend allocation to improve return on investment.
RATIONALE: Marketing efficiency has declined significantly, requiring immediate attention to prevent further resource waste.
ACTIONS:
1. Conduct marketing channel audit
2. Implement ROI tracking for all campaigns
3. Reallocate budget to high-performing channels
4. Set quarterly review checkpoints"""
    return mock_response
