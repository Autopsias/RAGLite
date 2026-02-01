"""Tests for impact score calculation logic."""

from raglite.insights.recommendations import calculate_impact_score
from raglite.shared.models import Insight, InsightCategory


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
