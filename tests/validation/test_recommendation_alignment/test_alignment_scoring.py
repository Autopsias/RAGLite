"""Tests for alignment scoring logic (Story 4.10 Task 3.3)."""

from raglite.shared.models import Insight, InsightCategory, Recommendation, RecommendationCategory
from tests.validation.test_recommendation_alignment import (
    RecommendationAlignmentValidator,
    RecommendationTestScenario,
)


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
