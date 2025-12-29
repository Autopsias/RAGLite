"""Unit tests for strategic recommendation engine.

Story 4.8: Tests for generate_recommendations(), synthesize_recommendation(),
calculate_impact_score(), categorize_recommendation(), filter_recommendations().

Target: 40+ unit tests covering models, functions, edge cases.
"""

from datetime import UTC, datetime

import pytest

from raglite.shared.models import (
    Insight,
    InsightCategory,
)

pytestmark = [pytest.mark.unit]

# =============================================================================
# Test Data Fixtures
# =============================================================================


class TestEdgeCases:
    """Edge case tests for recommendation generation."""

    @pytest.mark.asyncio
    async def test_insight_with_empty_supporting_data(self):
        """Edge case: Insight with empty supporting_data."""
        from raglite.insights.recommendations import generate_recommendations

        insight = Insight(
            category=InsightCategory.TREND,
            priority=3,
            summary="Test insight",
            supporting_data={},
            created_at=datetime.now(UTC),
        )
        result = await generate_recommendations([insight], auto_synthesize=False)
        assert len(result.recommendations) == 1
        assert result.recommendations[0].supporting_evidence == {}

    @pytest.mark.asyncio
    async def test_insight_with_empty_sources(self):
        """Edge case: Insight with empty sources list."""
        from raglite.insights.recommendations import generate_recommendations

        insight = Insight(
            category=InsightCategory.ANOMALY,
            priority=2,
            summary="Test anomaly",
            sources=[],
            created_at=datetime.now(UTC),
        )
        result = await generate_recommendations([insight], auto_synthesize=False)
        assert len(result.recommendations) == 1
        assert result.recommendations[0].sources == []

    @pytest.mark.asyncio
    async def test_all_categories_generate_recommendations(self):
        """All InsightCategory values generate valid recommendations."""
        from raglite.insights.recommendations import generate_recommendations

        insights = [
            Insight(
                category=cat,
                priority=2,
                summary=f"Test {cat.value}",
                created_at=datetime.now(UTC),
            )
            for cat in InsightCategory
        ]
        result = await generate_recommendations(insights, auto_synthesize=False)
        assert result.total_generated == len(InsightCategory)


# =============================================================================
# Structured Logging Tests
# =============================================================================


class TestStructuredLogging:
    """Tests for structured logging output."""

    @pytest.mark.asyncio
    async def test_generate_logs_start(self, sample_risk_insight: Insight, caplog):
        """Logging: generate_recommendations logs start message."""
        import logging

        from raglite.insights.recommendations import generate_recommendations

        with caplog.at_level(logging.INFO):
            await generate_recommendations([sample_risk_insight], auto_synthesize=False)
        assert "Starting recommendation generation" in caplog.text

    @pytest.mark.asyncio
    async def test_generate_logs_completion(self, sample_risk_insight: Insight, caplog):
        """Logging: generate_recommendations logs completion message."""
        import logging

        from raglite.insights.recommendations import generate_recommendations

        with caplog.at_level(logging.INFO):
            await generate_recommendations([sample_risk_insight], auto_synthesize=False)
        assert "Recommendation generation complete" in caplog.text
