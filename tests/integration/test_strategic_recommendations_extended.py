"""Integration tests for strategic recommendation engine - Extended Tests.

Story 4.8 AC4/AC5: Processing time, pipeline integration, and data integrity tests.
"""

import time
from datetime import UTC, datetime

import pytest

from raglite.shared.models import (
    Insight,
    InsightCategory,
)
from tests.integration.conftest import EXPERT_LABELED_SCENARIOS

# Mark all tests as preserve_collection - these are read-only tests
# that don't modify the Qdrant collection (performance optimization)
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def all_expert_scenarios() -> dict:
    """Return all expert-labeled scenarios."""
    return EXPERT_LABELED_SCENARIOS


# =============================================================================
# Processing Time Performance Tests
# =============================================================================


class TestProcessingTimePerformance:
    """Tests for processing time requirements."""

    @pytest.mark.asyncio
    async def test_processing_time_under_3s_for_5_insights(self, all_expert_scenarios: dict):
        """Performance: Processing time < 3s for 5 insights (without LLM)."""
        from raglite.insights.recommendations import generate_recommendations

        # Take first 5 scenarios
        insights = [scenario["insight"] for scenario in list(all_expert_scenarios.values())[:5]]

        start_time = time.time()
        result = await generate_recommendations(insights, auto_synthesize=False)
        elapsed_time = time.time() - start_time

        assert elapsed_time < 3.0, f"Processing took {elapsed_time:.2f}s (> 3s)"
        assert result.total_generated == 5

    @pytest.mark.asyncio
    async def test_processing_time_under_3s_for_10_insights(self):
        """Performance: Processing time < 3s for 10 insights (without LLM)."""
        from raglite.insights.recommendations import generate_recommendations

        # Generate 10 insights
        insights = [
            Insight(
                category=list(InsightCategory)[i % len(InsightCategory)],
                priority=(i % 5) + 1,
                summary=f"Test insight {i}",
                supporting_data={"index": i},
                sources=[f"source_{i}"],
                created_at=datetime.now(UTC),
            )
            for i in range(10)
        ]

        start_time = time.time()
        result = await generate_recommendations(insights, auto_synthesize=False)
        elapsed_time = time.time() - start_time

        assert elapsed_time < 3.0, f"Processing took {elapsed_time:.2f}s (> 3s)"
        assert result.total_generated == 10


# =============================================================================
# Pipeline Integration Tests
# =============================================================================


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


# =============================================================================
# Data Integrity Tests
# =============================================================================


class TestDataIntegrity:
    """Tests for data integrity through recommendation pipeline."""

    @pytest.fixture
    def cloud_cost_scenario(self) -> dict:
        """Return the cloud cost over budget scenario (AC5)."""
        return EXPERT_LABELED_SCENARIOS["cloud_cost_over_budget"]

    @pytest.mark.asyncio
    async def test_sources_preserved(self, cloud_cost_scenario: dict):
        """Data integrity: Sources from insight preserved in recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.sources == cloud_cost_scenario["insight"].sources

    @pytest.mark.asyncio
    async def test_supporting_data_preserved(self, cloud_cost_scenario: dict):
        """Data integrity: Supporting data from insight preserved as evidence."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.supporting_evidence == cloud_cost_scenario["insight"].supporting_data

    @pytest.mark.asyncio
    async def test_timestamp_is_set(self, cloud_cost_scenario: dict):
        """Data integrity: Recommendation has valid timestamp."""
        from raglite.insights.recommendations import generate_recommendations

        before = datetime.now(UTC)
        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        after = datetime.now(UTC)

        rec = result.recommendations[0]
        assert before <= rec.created_at <= after
