"""Unit tests for Story 4.7: Insight Generation Core Functions.

Tests synthesize_insight, generate_insights, and integration scenarios.
Split from test_proactive_insights.py as part of Story 8.4a-2.
"""

from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    InsightCategory,
    InsightGenerationResult,
    Trend,
    TrendDirection,
)

# Group insight tests that share mocked state to run on same worker
pytestmark = [pytest.mark.unit, pytest.mark.xdist_group(name="insights_workflow")]


# =============================================================================
# Test synthesize_insight() Function (AC1, AC5)
# =============================================================================


class TestGenerateInsights:
    """Tests for the generate_insights() function."""

    @pytest.mark.asyncio
    async def test_generate_insights_returns_result(
        self, sample_anomalies, sample_trends, sample_forecasts
    ):
        """Test that generate_insights returns InsightGenerationResult (AC1)."""
        from raglite.insights.proactive import generate_insights

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="SUMMARY: Test insight\nRATIONALE: Test\nACTION: Test")
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights(sample_anomalies, sample_trends, sample_forecasts)

        assert isinstance(result, InsightGenerationResult)
        assert result.total_generated == 3  # 1 anomaly + 1 trend + 1 forecast
        assert result.metrics_analyzed == 3

    @pytest.mark.asyncio
    async def test_generate_insights_empty_input_raises_error(self):
        """Test that empty inputs raise ValueError."""
        from raglite.insights.proactive import generate_insights

        with pytest.raises(ValueError, match="No data to analyze"):
            await generate_insights([], [], [])

    @pytest.mark.asyncio
    async def test_generate_insights_anomaly_only(self, sample_anomalies):
        """Test generate_insights with anomaly only."""
        from raglite.insights.proactive import generate_insights

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="SUMMARY: Anomaly detected\nRATIONALE: Test\nACTION: Test"
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights(sample_anomalies, [], [])

        assert result.total_generated == 1
        assert result.insights[0].category == InsightCategory.ANOMALY

    @pytest.mark.asyncio
    async def test_generate_insights_sorted_by_priority(
        self, sample_anomalies, sample_trends, sample_forecasts
    ):
        """Test insights are sorted by priority (AC3)."""
        from raglite.insights.proactive import generate_insights

        # Create critical anomaly
        critical_anomaly = Anomaly(
            date="2024-Q3",
            metric="critical_metric",
            value=5000000,
            expected_value=2000000,
            z_score=4.0,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=150.0,
        )

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="SUMMARY: Test\nRATIONALE: Test\nACTION: Test"))
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights(
                [critical_anomaly] + sample_anomalies,
                sample_trends,
                sample_forecasts,
            )

        # First insight should be highest priority (lowest number)
        priorities = [i.priority for i in result.insights]
        assert priorities == sorted(priorities)

    @pytest.mark.asyncio
    async def test_generate_insights_deduplication(self):
        """Test that duplicate metrics are deduplicated."""
        from raglite.insights.proactive import generate_insights

        # Same metric, different dates
        anomalies = [
            Anomaly(
                date="2024-Q3",
                metric="revenue",
                value=1000000,
                expected_value=800000,
                z_score=2.5,
                severity=AnomalySeverity.MODERATE,
                magnitude_pct=25.0,
            ),
            Anomaly(
                date="2024-Q3",  # Same date+metric = duplicate key
                metric="revenue",
                value=1100000,
                expected_value=800000,
                z_score=3.0,
                severity=AnomalySeverity.CRITICAL,
                magnitude_pct=37.5,
            ),
        ]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="SUMMARY: Test\nRATIONALE: Test\nACTION: Test"))
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights(anomalies, [], [])

        # Should be deduplicated - only 1 insight for revenue Q3
        assert result.total_generated == 1

    @pytest.mark.asyncio
    async def test_generate_insights_auto_synthesize_false(self, sample_anomalies, sample_trends):
        """Test generate_insights with auto_synthesize=False."""
        from raglite.insights.proactive import generate_insights

        result = await generate_insights(
            sample_anomalies,
            sample_trends,
            [],
            auto_synthesize=False,
        )

        # Should not call LLM
        assert result.total_generated == 2
        assert result.generation_method == "Rule-based"
        # Summaries should be simple
        for insight in result.insights:
            assert len(insight.summary) > 0
            assert insight.rationale == ""

    @pytest.mark.asyncio
    async def test_generate_insights_supporting_data_populated(self, sample_anomalies):
        """Test that supporting_data dict is populated (AC5)."""
        from raglite.insights.proactive import generate_insights

        result = await generate_insights(
            sample_anomalies,
            [],
            [],
            auto_synthesize=False,
        )

        insight = result.insights[0]
        assert "metric" in insight.supporting_data
        assert "value" in insight.supporting_data
        assert "z_score" in insight.supporting_data
        assert insight.supporting_data["metric"] == "marketing_spend"


# =============================================================================
# Test Marketing Spend Example (AC6)
# =============================================================================


class TestMarketingSpendExample:
    """Tests for the marketing spend anomaly example from AC6."""

    @pytest.mark.asyncio
    async def test_marketing_spend_anomaly_generates_risk_insight(self):
        """Test AC6: Marketing spend 30% YoY increase with stable revenue -> RISK."""
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
        )

        # Revenue stable trend
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
                    content="""SUMMARY: Q3 marketing spend increased 30% YoY with no corresponding revenue increase - potential inefficiency.
RATIONALE: Marketing spend deviation of 30% without revenue growth suggests campaigns may not be delivering expected ROI.
ACTION: Review marketing campaign effectiveness and ROI metrics."""
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights([marketing_anomaly], [revenue_trend], [])

        # Should generate insights for both
        assert result.total_generated == 2

        # Find marketing insight
        marketing_insight = next(
            (i for i in result.insights if "marketing" in i.supporting_data.get("metric", "")),
            None,
        )
        assert marketing_insight is not None
        assert marketing_insight.category == InsightCategory.ANOMALY
        assert (
            "marketing" in marketing_insight.summary.lower() or "30%" in marketing_insight.summary
        )
