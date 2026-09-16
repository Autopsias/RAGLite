"""Unit tests for recommendation helper functions.

Tests for:
- calculate_impact_score()
- categorize_recommendation()
- determine_urgency()
- filter_recommendations()

Target: 25 tests covering score calculation, categorization logic, urgency determination, and filtering.
"""

from datetime import UTC, datetime

import pytest

from raglite.shared.models import Insight, InsightCategory, Recommendation, RecommendationCategory

# =============================================================================
# calculate_impact_score() Tests
# =============================================================================


class TestCalculateImpactScore:
    """Tests for calculate_impact_score() function."""

    def test_critical_risk_insight_high_impact(self):
        """AC2: Critical RISK insight (priority 1) gets high impact score."""
        from raglite.insights.recommendations import calculate_impact_score

        insight = Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Marketing spend increased 30% YoY with no revenue increase",
            created_at=datetime.now(UTC),
        )
        score = calculate_impact_score(insight)
        # Priority 1 -> base 9, RISK boost +2 = 10 (capped)
        assert score == 10

    def test_opportunity_insight_medium_impact(self):
        """AC2: OPPORTUNITY insight (priority 2) gets boosted impact."""
        from raglite.insights.recommendations import calculate_impact_score

        insight = Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Revenue growth trending 15% above forecast",
            created_at=datetime.now(UTC),
        )
        score = calculate_impact_score(insight)
        # Priority 2 -> base 7, OPPORTUNITY boost +1 = 8
        assert score == 8

    def test_anomaly_insight_medium_impact(self):
        """AC2: ANOMALY insight (priority 3) gets medium impact."""
        from raglite.insights.recommendations import calculate_impact_score

        insight = Insight(
            category=InsightCategory.ANOMALY,
            priority=3,
            summary="Unusual spike in cloud costs detected",
            created_at=datetime.now(UTC),
        )
        score = calculate_impact_score(insight)
        # Priority 3 -> base 5, no category boost = 5
        assert score == 5

    def test_trend_insight_lower_impact(self):
        """AC2: TREND insight (priority 4) gets lower impact."""
        from raglite.insights.recommendations import calculate_impact_score

        insight = Insight(
            category=InsightCategory.TREND,
            priority=4,
            summary="Operating expenses showing stable pattern",
            created_at=datetime.now(UTC),
        )
        score = calculate_impact_score(insight)
        # Priority 4 -> base 3, no category boost = 3
        assert score == 3

    def test_strategic_priority_insight_boosted(self):
        """AC2: STRATEGIC_PRIORITY insight gets +1 boost."""
        from raglite.insights.recommendations import calculate_impact_score

        insight = Insight(
            category=InsightCategory.STRATEGIC_PRIORITY,
            priority=2,
            summary="Capital expenditure planning needed for next fiscal year",
            created_at=datetime.now(UTC),
        )
        score = calculate_impact_score(insight)
        # Priority 2 -> base 7, STRATEGIC_PRIORITY boost +1 = 8
        assert score == 8

    def test_priority_5_minimum_score(self):
        """AC2: Priority 5 insight gets minimum impact score."""
        from raglite.insights.recommendations import calculate_impact_score

        insight = Insight(
            category=InsightCategory.TREND,
            priority=5,
            summary="Low priority trend",
            created_at=datetime.now(UTC),
        )
        score = calculate_impact_score(insight)
        # Priority 5 -> 11 - 10 = 1
        assert score == 1


# =============================================================================
# categorize_recommendation() Tests
# =============================================================================


class TestCategorizeRecommendation:
    """Tests for categorize_recommendation() function."""

    def test_risk_insight_to_risk_mitigation(self):
        """AC1: RISK insight maps to RISK_MITIGATION."""
        from raglite.insights.recommendations import categorize_recommendation

        insight = Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Marketing spend increased 30% YoY with no revenue increase",
            created_at=datetime.now(UTC),
        )
        category = categorize_recommendation(insight)
        assert category == RecommendationCategory.RISK_MITIGATION

    def test_opportunity_insight_to_revenue_growth(self):
        """AC1: OPPORTUNITY insight maps to REVENUE_GROWTH."""
        from raglite.insights.recommendations import categorize_recommendation

        insight = Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Revenue growth trending 15% above forecast",
            created_at=datetime.now(UTC),
        )
        category = categorize_recommendation(insight)
        assert category == RecommendationCategory.REVENUE_GROWTH

    def test_opportunity_with_cost_to_cost_reduction(self, cost_opportunity_insight: Insight):
        """AC1: OPPORTUNITY insight with 'cost' keyword maps to COST_REDUCTION."""
        from raglite.insights.recommendations import categorize_recommendation

        category = categorize_recommendation(cost_opportunity_insight)
        assert category == RecommendationCategory.COST_REDUCTION

    def test_anomaly_insight_to_operational_efficiency(self):
        """AC1: ANOMALY insight maps to OPERATIONAL_EFFICIENCY."""
        from raglite.insights.recommendations import categorize_recommendation

        insight = Insight(
            category=InsightCategory.ANOMALY,
            priority=3,
            summary="Unusual spike in cloud costs detected",
            created_at=datetime.now(UTC),
        )
        category = categorize_recommendation(insight)
        assert category == RecommendationCategory.OPERATIONAL_EFFICIENCY

    def test_trend_insight_to_operational_efficiency(self):
        """AC1: TREND insight maps to OPERATIONAL_EFFICIENCY."""
        from raglite.insights.recommendations import categorize_recommendation

        insight = Insight(
            category=InsightCategory.TREND,
            priority=4,
            summary="Operating expenses showing stable pattern",
            created_at=datetime.now(UTC),
        )
        category = categorize_recommendation(insight)
        assert category == RecommendationCategory.OPERATIONAL_EFFICIENCY

    def test_strategic_priority_to_strategic_investment(self):
        """AC1: STRATEGIC_PRIORITY insight maps to STRATEGIC_INVESTMENT."""
        from raglite.insights.recommendations import categorize_recommendation

        insight = Insight(
            category=InsightCategory.STRATEGIC_PRIORITY,
            priority=2,
            summary="Capital expenditure planning needed for next fiscal year",
            created_at=datetime.now(UTC),
        )
        category = categorize_recommendation(insight)
        assert category == RecommendationCategory.STRATEGIC_INVESTMENT


# =============================================================================
# determine_urgency() Tests
# =============================================================================


class TestDetermineUrgency:
    """Tests for determine_urgency() function."""

    def test_priority_1_is_high_urgency(self):
        """Priority 1 insight results in high urgency."""
        from raglite.insights.recommendations import determine_urgency

        insight = Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Marketing spend increased 30% YoY with no revenue increase",
            created_at=datetime.now(UTC),
        )
        urgency = determine_urgency(insight, impact_score=10)
        assert urgency == "high"

    def test_high_impact_is_high_urgency(self):
        """Impact score >= 8 results in high urgency."""
        from raglite.insights.recommendations import determine_urgency

        insight = Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Revenue growth trending 15% above forecast",
            created_at=datetime.now(UTC),
        )
        urgency = determine_urgency(insight, impact_score=8)
        assert urgency == "high"

    def test_low_priority_low_impact_is_low_urgency(self):
        """Priority >= 4 with impact <= 4 results in low urgency."""
        from raglite.insights.recommendations import determine_urgency

        insight = Insight(
            category=InsightCategory.TREND,
            priority=4,
            summary="Low priority",
            created_at=datetime.now(UTC),
        )
        urgency = determine_urgency(insight, impact_score=3)
        assert urgency == "low"

    def test_medium_priority_medium_impact_is_medium_urgency(self):
        """Medium priority and impact results in medium urgency."""
        from raglite.insights.recommendations import determine_urgency

        insight = Insight(
            category=InsightCategory.ANOMALY,
            priority=3,
            summary="Unusual spike in cloud costs detected",
            created_at=datetime.now(UTC),
        )
        urgency = determine_urgency(insight, impact_score=5)
        assert urgency == "medium"


# =============================================================================
# filter_recommendations() Tests
# =============================================================================


class TestFilterRecommendations:
    """Tests for filter_recommendations() function."""

    @pytest.fixture
    def sample_recommendations(self) -> list[Recommendation]:
        """Create a sample list of recommendations for filtering."""
        return [
            Recommendation(
                category=RecommendationCategory.RISK_MITIGATION,
                impact_score=9,
                title="Risk 1",
                description="High impact risk",
            ),
            Recommendation(
                category=RecommendationCategory.COST_REDUCTION,
                impact_score=7,
                title="Cost 1",
                description="Medium impact cost",
            ),
            Recommendation(
                category=RecommendationCategory.REVENUE_GROWTH,
                impact_score=6,
                title="Revenue 1",
                description="Medium impact revenue",
            ),
            Recommendation(
                category=RecommendationCategory.RISK_MITIGATION,
                impact_score=4,
                title="Risk 2",
                description="Low impact risk",
            ),
            Recommendation(
                category=RecommendationCategory.OPERATIONAL_EFFICIENCY,
                impact_score=3,
                title="Ops 1",
                description="Low impact ops",
            ),
        ]

    def test_filter_by_category(self, sample_recommendations: list[Recommendation]):
        """Filter recommendations by category."""
        from raglite.insights.recommendations import filter_recommendations

        filtered = filter_recommendations(
            sample_recommendations,
            category=RecommendationCategory.RISK_MITIGATION,
        )
        assert len(filtered) == 2
        assert all(r.category == RecommendationCategory.RISK_MITIGATION for r in filtered)

    def test_filter_by_min_impact(self, sample_recommendations: list[Recommendation]):
        """Filter recommendations by minimum impact score."""
        from raglite.insights.recommendations import filter_recommendations

        filtered = filter_recommendations(
            sample_recommendations,
            min_impact=7,
        )
        assert len(filtered) == 2
        assert all(r.impact_score >= 7 for r in filtered)

    def test_filter_by_limit(self, sample_recommendations: list[Recommendation]):
        """Filter recommendations by count limit."""
        from raglite.insights.recommendations import filter_recommendations

        filtered = filter_recommendations(
            sample_recommendations,
            limit=3,
        )
        assert len(filtered) == 3

    def test_filter_combined(self, sample_recommendations: list[Recommendation]):
        """Filter with multiple criteria."""
        from raglite.insights.recommendations import filter_recommendations

        filtered = filter_recommendations(
            sample_recommendations,
            category=RecommendationCategory.RISK_MITIGATION,
            min_impact=5,
            limit=1,
        )
        assert len(filtered) == 1
        assert filtered[0].impact_score == 9

    def test_filter_no_criteria_returns_all(self, sample_recommendations: list[Recommendation]):
        """Filter with no criteria returns all recommendations."""
        from raglite.insights.recommendations import filter_recommendations

        filtered = filter_recommendations(sample_recommendations)
        assert len(filtered) == 5
