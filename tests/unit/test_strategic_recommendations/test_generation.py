"""Unit tests for recommendation generation orchestration.

Tests for generate_recommendations() main function.

Target: 10 tests covering generation orchestration, sorting, deduplication, data preservation.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import (
    Insight,
    InsightCategory,
)

# Note: Recommendation and RecommendationResult imported inside tests
# to avoid pytest-xdist class identity issues with isinstance checks

# =============================================================================
# generate_recommendations() Tests
# =============================================================================


class TestGenerateRecommendations:
    """Tests for generate_recommendations() main function."""

    @pytest.fixture
    def mock_mistral_for_generation(self):
        """Create mock for Mistral during generation."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """TITLE: Test Recommendation
DESCRIPTION: Test description for the recommendation.
RATIONALE: Test rationale explaining importance.
ACTIONS:
1. Action step one
2. Action step two
3. Action step three"""
        return mock_response

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

    @pytest.fixture
    def sample_trend_insight(self) -> Insight:
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
    def sample_opportunity_insight(self) -> Insight:
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
    def sample_anomaly_insight(self) -> Insight:
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

    @pytest.mark.asyncio
    async def test_generate_returns_recommendation_result(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """AC1: generate_recommendations returns RecommendationResult."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations([sample_risk_insight])
            assert result.__class__.__name__ == "RecommendationResult"

    @pytest.mark.asyncio
    async def test_generate_returns_recommendations_list(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """AC1: generate_recommendations returns list of Recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations([sample_risk_insight])
            assert len(result.recommendations) >= 1
            assert result.recommendations[0].__class__.__name__ == "Recommendation"

    @pytest.mark.asyncio
    async def test_generate_sorted_by_impact_descending(
        self,
        sample_risk_insight: Insight,
        sample_trend_insight: Insight,
        mock_mistral_for_generation,
    ):
        """AC2: Results sorted by impact_score descending."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations(
                [sample_trend_insight, sample_risk_insight]  # Trend first, Risk second
            )
            # Should be sorted: Risk (high impact) before Trend (low impact)
            scores = [r.impact_score for r in result.recommendations]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_generate_empty_insights_raises_error(self):
        """AC1: Empty insights list raises ValueError."""
        from raglite.insights.recommendations import generate_recommendations

        with pytest.raises(ValueError, match="No insights"):
            await generate_recommendations([])

    @pytest.mark.asyncio
    async def test_generate_single_insight(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """Edge case: Single insight generates one recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations([sample_risk_insight])
            assert result.total_generated == 1
            assert result.insights_analyzed == 1

    @pytest.mark.asyncio
    async def test_generate_deduplication(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """Edge case: Duplicate insights are deduplicated."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            # Same insight twice
            result = await generate_recommendations([sample_risk_insight, sample_risk_insight])
            # Should only generate one recommendation
            assert result.total_generated == 1

    @pytest.mark.asyncio
    async def test_generate_without_synthesis(self, sample_risk_insight: Insight):
        """Edge case: auto_synthesize=False skips LLM."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations([sample_risk_insight], auto_synthesize=False)
        assert result.generation_method == "Rule-based"
        assert len(result.recommendations) == 1

    @pytest.mark.asyncio
    async def test_generate_multiple_insights(
        self,
        sample_risk_insight: Insight,
        sample_opportunity_insight: Insight,
        sample_anomaly_insight: Insight,
        mock_mistral_for_generation,
    ):
        """AC1: Multiple insights generate multiple recommendations."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations(
                [
                    sample_risk_insight,
                    sample_opportunity_insight,
                    sample_anomaly_insight,
                ]
            )
            assert result.total_generated == 3
            assert result.insights_analyzed == 3

    @pytest.mark.asyncio
    async def test_generate_preserves_supporting_evidence(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """AC3: Supporting evidence from insight is preserved."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations([sample_risk_insight])
            rec = result.recommendations[0]
            assert rec.supporting_evidence == sample_risk_insight.supporting_data

    @pytest.mark.asyncio
    async def test_generate_preserves_sources(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """AC3: Sources from insight are preserved."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations([sample_risk_insight])
            rec = result.recommendations[0]
            assert rec.sources == sample_risk_insight.sources
