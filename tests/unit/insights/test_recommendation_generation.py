"""Unit tests for strategic recommendation engine.

Story 4.8: Tests for generate_recommendations(), synthesize_recommendation(),
calculate_impact_score(), categorize_recommendation(), filter_recommendations().

Target: 40+ unit tests covering models, functions, edge cases.
"""

from unittest.mock import patch

import pytest

from raglite.shared.models import (
    Insight,
    Recommendation,
    RecommendationCategory,
    RecommendationResult,
)

# Group recommendation tests that share mocked state to run on same worker
pytestmark = [pytest.mark.unit, pytest.mark.xdist_group(name="recommendations")]

# =============================================================================
# Test Data Fixtures
# =============================================================================


class TestSynthesizeRecommendation:
    """Tests for synthesize_recommendation() with mocked Mistral client."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_title(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC3: synthesize_recommendation returns title."""
        from raglite.insights.recommendations import synthesize_recommendation

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            title, _, _, _ = await synthesize_recommendation(
                sample_risk_insight, RecommendationCategory.RISK_MITIGATION
            )
            assert "Marketing" in title or "ROI" in title

    @pytest.mark.asyncio
    async def test_synthesize_returns_description(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC3: synthesize_recommendation returns description."""
        from raglite.insights.recommendations import synthesize_recommendation

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            _, description, _, _ = await synthesize_recommendation(
                sample_risk_insight, RecommendationCategory.RISK_MITIGATION
            )
            assert len(description) > 0

    @pytest.mark.asyncio
    async def test_synthesize_returns_rationale(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC3: synthesize_recommendation returns rationale."""
        from raglite.insights.recommendations import synthesize_recommendation

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            _, _, rationale, _ = await synthesize_recommendation(
                sample_risk_insight, RecommendationCategory.RISK_MITIGATION
            )
            assert len(rationale) > 0

    @pytest.mark.asyncio
    async def test_synthesize_returns_action_steps(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC3: synthesize_recommendation returns action_steps list."""
        from raglite.insights.recommendations import synthesize_recommendation

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            _, _, _, actions = await synthesize_recommendation(
                sample_risk_insight, RecommendationCategory.RISK_MITIGATION
            )
            assert len(actions) >= 3

    @pytest.mark.asyncio
    async def test_synthesize_fallback_on_llm_failure(self, sample_risk_insight: Insight):
        """AC3: synthesize_recommendation provides fallback on LLM failure."""
        from raglite.insights.recommendations import synthesize_recommendation

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.side_effect = Exception("LLM error")
            title, description, rationale, actions = await synthesize_recommendation(
                sample_risk_insight, RecommendationCategory.RISK_MITIGATION
            )
            # Should return fallback values
            assert "Recommendation" in title
            assert len(description) > 0
            assert len(actions) >= 3


# =============================================================================
# generate_recommendations() Tests
# =============================================================================


class TestGenerateRecommendations:
    """Tests for generate_recommendations() main function."""

    @pytest.mark.asyncio
    async def test_generate_returns_recommendation_result(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC1: generate_recommendations returns RecommendationResult."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            result = await generate_recommendations([sample_risk_insight])
            assert isinstance(result, RecommendationResult)

    @pytest.mark.asyncio
    async def test_generate_returns_recommendations_list(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC1: generate_recommendations returns list of Recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            result = await generate_recommendations([sample_risk_insight])
            assert len(result.recommendations) >= 1
            assert isinstance(result.recommendations[0], Recommendation)

    @pytest.mark.asyncio
    async def test_generate_sorted_by_impact_descending(
        self,
        sample_risk_insight: Insight,
        sample_trend_insight: Insight,
        mock_mistral_response,
    ):
        """AC2: Results sorted by impact_score descending."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
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
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """Edge case: Single insight generates one recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            result = await generate_recommendations([sample_risk_insight])
            assert result.total_generated == 1
            assert result.insights_analyzed == 1

    @pytest.mark.asyncio
    async def test_generate_deduplication(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """Edge case: Duplicate insights are deduplicated."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
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
        mock_mistral_response,
    ):
        """AC1: Multiple insights generate multiple recommendations."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
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
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC3: Supporting evidence from insight is preserved."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            result = await generate_recommendations([sample_risk_insight])
            rec = result.recommendations[0]
            assert rec.supporting_evidence == sample_risk_insight.supporting_data

    @pytest.mark.asyncio
    async def test_generate_preserves_sources(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC3: Sources from insight are preserved."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            result = await generate_recommendations([sample_risk_insight])
            rec = result.recommendations[0]
            assert rec.sources == sample_risk_insight.sources


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================
