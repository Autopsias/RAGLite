"""Unit tests for proactive insight synthesis.

Tests the synthesize_insight() function which generates natural language
summaries, rationales, and actions using the Mistral LLM. Corresponds to AC1, AC5.
"""

from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    Trend,
    TrendDirection,
)


class TestSynthesizeInsight:
    """Tests for the synthesize_insight() function."""

    @pytest.fixture
    def sample_anomaly(self) -> Anomaly:
        """Create sample anomaly for synthesis tests."""
        return Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=2.5,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=30.0,
        )

    @pytest.fixture
    def sample_trend(self) -> Trend:
        """Create sample trend for synthesis tests."""
        return Trend(
            metric="revenue",
            direction=TrendDirection.STABLE,
            magnitude=2.0,
            confidence=0.9,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.02,
            qoq_growth=0.5,
        )

    @pytest.mark.asyncio
    async def test_synthesize_anomaly_with_mocked_mistral(self, sample_anomaly):
        """Test synthesize_insight with mocked Mistral client."""
        from raglite.insights.proactive import synthesize_insight

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
    async def test_synthesize_trend_with_mocked_mistral(self, sample_trend):
        """Test synthesize_insight with trend and mocked Mistral."""
        from raglite.insights.proactive import synthesize_insight

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
    async def test_synthesize_fallback_on_error(self, sample_anomaly):
        """Test that synthesize_insight returns fallback on API error."""
        from raglite.insights.proactive import synthesize_insight

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
    async def test_synthesize_prompt_contains_context(self, sample_anomaly, sample_trend):
        """Test that the LLM prompt contains all context."""
        from raglite.insights.proactive import synthesize_insight

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
