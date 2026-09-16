"""Unit tests for recommendation synthesis.

Tests for synthesize_recommendation() with mocked LLM.

Target: 5 tests covering LLM synthesis, fallback handling.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import Insight, InsightCategory, RecommendationCategory

# =============================================================================
# synthesize_recommendation() Tests
# =============================================================================


class TestSynthesizeRecommendation:
    """Tests for synthesize_recommendation() with mocked Mistral client."""

    @pytest.fixture
    def mock_mistral_response(self):
        """Create a mock Mistral response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """TITLE: Optimize Marketing ROI
DESCRIPTION: Review and optimize marketing spend allocation to improve return on investment.
RATIONALE: Marketing efficiency has declined significantly, requiring immediate attention to prevent further resource waste.
ACTIONS:
1. Conduct marketing channel audit
2. Implement ROI tracking for all campaigns
3. Reallocate budget to high-performing channels
4. Set quarterly review checkpoints"""
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
