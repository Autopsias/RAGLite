"""End-to-end recommendation generation tests."""

from datetime import UTC, datetime

import pytest

from raglite.shared.models import (
    Insight,
    InsightCategory,
    RecommendationResult,
)

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestEndToEndRecommendationGeneration:
    """End-to-end integration tests for recommendation generation."""

    @pytest.mark.asyncio
    async def test_generate_single_recommendation_e2e(self, cloud_cost_scenario: dict):
        """E2E: Single insight generates complete recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )

        assert isinstance(result, RecommendationResult)
        assert len(result.recommendations) == 1

        rec = result.recommendations[0]
        assert rec.category == cloud_cost_scenario["expected_category"]
        assert rec.impact_score >= cloud_cost_scenario["expected_impact_min"]

    @pytest.mark.asyncio
    async def test_generate_multiple_recommendations_e2e(self, all_expert_scenarios: dict):
        """E2E: Multiple insights generate sorted recommendations."""
        from raglite.insights.recommendations import generate_recommendations

        insights = [scenario["insight"] for scenario in all_expert_scenarios.values()]
        result = await generate_recommendations(insights, auto_synthesize=False)

        assert len(result.recommendations) == len(insights)
        # Verify sorted by impact descending
        scores = [r.impact_score for r in result.recommendations]
        assert scores == sorted(scores, reverse=True)


class TestPipelineIntegration:
    """Tests for integration with insight generation pipeline."""

    @pytest.mark.asyncio
    async def test_insight_to_recommendation_pipeline(self):
        """E2E: Insight generation -> Recommendation engine pipeline."""
        from raglite.insights.recommendations import generate_recommendations

        # Create insights similar to what generate_insights() would produce
        insights = [
            Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Critical anomaly in revenue",
                supporting_data={"severity": "critical", "metric": "revenue"},
                rationale="Revenue dropped unexpectedly",
                sources=["revenue"],
                recommended_action="Investigate immediately",
                created_at=datetime.now(UTC),
            ),
            Insight(
                category=InsightCategory.OPPORTUNITY,
                priority=2,
                summary="Growth opportunity in new segment",
                supporting_data={"growth": 0.20, "segment": "new"},
                rationale="Strong demand signals",
                sources=["segment_analysis"],
                recommended_action="Expand in new segment",
                created_at=datetime.now(UTC),
            ),
        ]

        result = await generate_recommendations(insights, auto_synthesize=False)

        assert len(result.recommendations) == 2
        assert result.insights_analyzed == 2

        # Verify highest impact first
        assert result.recommendations[0].impact_score >= result.recommendations[1].impact_score

    @pytest.mark.asyncio
    async def test_recommendation_filtering_pipeline(self):
        """E2E: Generate recommendations then filter."""
        from raglite.insights.recommendations import (
            filter_recommendations,
            generate_recommendations,
        )

        insights = [
            Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="High priority risk",
                created_at=datetime.now(UTC),
            ),
            Insight(
                category=InsightCategory.TREND,
                priority=5,
                summary="Low priority trend",
                created_at=datetime.now(UTC),
            ),
        ]

        result = await generate_recommendations(insights, auto_synthesize=False)

        # Filter to only high impact
        filtered = filter_recommendations(result.recommendations, min_impact=5)

        assert len(filtered) == 1
        assert filtered[0].impact_score >= 5
