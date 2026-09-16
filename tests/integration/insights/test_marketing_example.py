"""Tests for AC6: Marketing spend example."""

from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    InsightCategory,
    Trend,
    TrendDirection,
)

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestMarketingSpendAnomalyExample:
    """Tests for AC6: Marketing spend example."""

    @pytest.mark.asyncio
    async def test_marketing_spend_30_percent_increase_stable_revenue(self):
        """AC6: Q3 marketing spend increased 30% YoY with no revenue increase -> RISK insight."""
        from raglite.insights.proactive import generate_insights

        # Marketing spend anomaly
        marketing_anomaly = Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=2.5,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=30.0,
            reason="Q3 marketing spend increased 30% YoY with no corresponding revenue increase",
        )

        # Revenue stable (no corresponding increase)
        revenue_trend = Trend(
            metric="revenue",
            direction=TrendDirection.STABLE,
            magnitude=2.0,
            confidence=0.9,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.02,
            qoq_growth=0.5,
            description="Revenue remained stable despite increased marketing investment",
        )

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""SUMMARY: Q3 marketing spend increased 30% YoY with no corresponding revenue increase - potential inefficiency.
RATIONALE: The 30% increase in marketing spend without a proportional revenue increase suggests potential campaign inefficiency or ROI issues that warrant investigation.
ACTION: Conduct marketing ROI analysis and review campaign effectiveness metrics."""
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights(
                [marketing_anomaly],
                [revenue_trend],
                [],
                auto_synthesize=True,
            )

        # Should generate insights
        assert result.total_generated == 2
        assert result.metrics_analyzed == 2

        # Find marketing insight
        marketing_insight = next(
            (
                i
                for i in result.insights
                if "marketing" in i.sources or "marketing" in i.supporting_data.get("metric", "")
            ),
            None,
        )
        assert marketing_insight is not None

        # Validate the insight matches AC6 example
        assert marketing_insight.category in [
            InsightCategory.ANOMALY,
            InsightCategory.RISK,
        ]
        assert marketing_insight.priority <= 3  # Should be moderate to high priority
        assert marketing_insight.supporting_data.get("magnitude_pct") == 30.0
        assert (
            "marketing" in marketing_insight.summary.lower() or "30%" in marketing_insight.summary
        )

    @pytest.mark.asyncio
    async def test_marketing_spend_with_llm_synthesis(self):
        """Test that LLM synthesis produces meaningful insights for marketing example."""
        from raglite.insights.proactive import generate_insights

        marketing_anomaly = Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=2.5,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=30.0,
        )

        revenue_trend = Trend(
            metric="revenue",
            direction=TrendDirection.STABLE,
            magnitude=2.0,
            confidence=0.9,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.02,
            qoq_growth=0.5,
        )

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""SUMMARY: Marketing spend increased 30% with no revenue increase - potential inefficiency.
RATIONALE: The significant increase in marketing expenditure without corresponding revenue growth indicates potential issues with marketing effectiveness or ROI.
ACTION: Review marketing campaign performance and reallocate budget to higher-performing channels."""
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights(
                [marketing_anomaly],
                [revenue_trend],
                [],
                auto_synthesize=True,
            )

        # Find marketing insight
        marketing_insight = next(
            (
                i
                for i in result.insights
                if "marketing" in i.sources or "marketing" in i.supporting_data.get("metric", "")
            ),
            None,
        )

        # Validate LLM-generated fields are populated
        assert marketing_insight.summary != ""
        assert marketing_insight.rationale != ""
        assert marketing_insight.recommended_action != ""
