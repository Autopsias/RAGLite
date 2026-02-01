"""Unit tests for generation edge cases and logging.

Tests for:
- Edge cases and error handling
- Structured logging

Target: 5 tests covering edge cases, empty data, and logging.
"""

from datetime import UTC, datetime

import pytest

from raglite.shared.models import Insight, InsightCategory

# =============================================================================
# Edge Cases and Error Handling
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
            for cat in InsightCategory.__members__.values()
        ]
        result = await generate_recommendations(insights, auto_synthesize=False)
        assert result.total_generated == len(InsightCategory.__members__)


# =============================================================================
# Structured Logging Tests
# =============================================================================


class TestStructuredLogging:
    """Tests for structured logging output."""

    @pytest.fixture
    def sample_risk_insight(self) -> Insight:
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
