"""Tests for recommendation categorization logic."""

from raglite.insights.recommendations import categorize_recommendation
from raglite.shared.models import Insight, InsightCategory, RecommendationCategory


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
