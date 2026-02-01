"""Unit tests for Story 4.7: Insight Generation Core Functions.

Tests synthesize_insight, generate_insights, and integration scenarios.
Split from test_proactive_insights.py as part of Story 8.4a-2.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


# =============================================================================
# Test synthesize_insight() Function (AC1, AC5)
# =============================================================================


class TestSynthesizeInsight:
    """Tests for the synthesize_insight() function."""

    @pytest.mark.asyncio
    async def test_synthesize_anomaly_with_mocked_mistral(self, sample_anomalies):
        """Test synthesize_insight with mocked Mistral client."""
        from raglite.insights.proactive import synthesize_insight

        sample_anomaly = sample_anomalies[0]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""SUMMARY: Marketing spend increased 30% with no revenue increase.
RATIONALE: The significant deviation in marketing spend without corresponding revenue growth suggests potential inefficiency in marketing campaigns.
ACTION: Review marketing ROI and campaign effectiveness."""
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            summary, rationale, action = await synthesize_insight(anomaly=sample_anomaly)

        assert "marketing spend" in summary.lower() or "30%" in summary
        assert len(rationale) > 0
        assert len(action) > 0
        mock_client.chat.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_trend_with_mocked_mistral(self, sample_trends):
        """Test synthesize_insight with trend and mocked Mistral."""
        from raglite.insights.proactive import synthesize_insight

        sample_trend = sample_trends[0]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""SUMMARY: Revenue shows stable growth pattern.
RATIONALE: The 2% stable growth indicates consistent performance without significant volatility.
ACTION: Continue monitoring current strategies."""
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            summary, rationale, action = await synthesize_insight(trend=sample_trend)

        assert len(summary) > 0
        assert len(rationale) > 0
        assert len(action) > 0

    @pytest.mark.asyncio
    async def test_synthesize_fallback_on_error(self, sample_anomalies):
        """Test that synthesize_insight returns fallback on API error."""
        from raglite.insights.proactive import synthesize_insight

        sample_anomaly = sample_anomalies[0]

        mock_client = MagicMock()
        mock_client.chat.complete.side_effect = Exception("API error")

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            summary, rationale, action = await synthesize_insight(anomaly=sample_anomaly)

        # Should return fallback values
        assert "marketing_spend" in summary
        assert "moderate" in summary
        assert len(rationale) > 0
        assert len(action) > 0

    @pytest.mark.asyncio
    async def test_synthesize_prompt_contains_context(self, sample_anomalies, sample_trends):
        """Test that the LLM prompt contains all context."""
        from raglite.insights.proactive import synthesize_insight

        sample_anomaly = sample_anomalies[0]
        sample_trend = sample_trends[0]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="SUMMARY: Test\nRATIONALE: Test\nACTION: Test"))
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            await synthesize_insight(anomaly=sample_anomaly, trend=sample_trend)

        # Check the prompt sent to Mistral
        call_args = mock_client.chat.complete.call_args
        prompt = call_args.kwargs["messages"][0]["content"]

        assert "marketing_spend" in prompt.lower()
        assert "30" in prompt  # magnitude_pct
        assert "revenue" in prompt.lower()


# =============================================================================
# Test generate_insights() Function (AC1-AC6)
# =============================================================================
