"""Unit tests for proactive insights edge cases and integration scenarios.

Tests edge cases, conflicting signals, and structured logging.
"""

import logging
from datetime import datetime

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    ForecastPoint,
    ForecastResult,
    InsightCategory,
    Trend,
    TrendDirection,
)


class TestEdgeCases:
    """Tests for edge cases in insight generation."""

    @pytest.mark.asyncio
    async def test_single_anomaly_no_trends_no_forecasts(self):
        """Test with single anomaly only."""
        from raglite.insights.proactive import generate_insights

        anomaly = Anomaly(
            date="2024-Q3",
            metric="revenue",
            value=1500000,
            expected_value=1000000,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=50.0,
        )

        result = await generate_insights([anomaly], [], [], auto_synthesize=False)

        assert result.total_generated == 1
        assert result.insights[0].category == InsightCategory.RISK
        assert result.insights[0].priority == 1

    @pytest.mark.asyncio
    async def test_only_trends(self):
        """Test with trends only."""
        from raglite.insights.proactive import generate_insights

        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=25.0,
            confidence=0.95,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.25,
            qoq_growth=6.0,
        )

        result = await generate_insights([], [trend], [], auto_synthesize=False)

        assert result.total_generated == 1
        assert result.insights[0].category == InsightCategory.OPPORTUNITY

    @pytest.mark.asyncio
    async def test_only_forecasts(self):
        """Test with forecasts only."""
        from raglite.insights.proactive import generate_insights

        forecast = ForecastResult(
            metric_name="revenue",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=1100000,
                    lower=900000,
                    upper=1300000,
                )
            ],
            periods_ahead=4,
        )

        result = await generate_insights([], [], [forecast], auto_synthesize=False)

        assert result.total_generated == 1
        assert result.insights[0].category == InsightCategory.STRATEGIC_PRIORITY

    @pytest.mark.asyncio
    async def test_conflicting_signals(self):
        """Test handling of conflicting signals (anomaly + positive trend)."""
        from raglite.insights.proactive import generate_insights

        # Critical anomaly (negative signal)
        anomaly = Anomaly(
            date="2024-Q3",
            metric="expenses",
            value=5000000,
            expected_value=3000000,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=66.7,
        )

        # Positive trend (different metric)
        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=20.0,
            confidence=0.9,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.20,
            qoq_growth=5.0,
        )

        result = await generate_insights([anomaly], [trend], [], auto_synthesize=False)

        # Should generate both insights
        assert result.total_generated == 2

        # Find the risk insight
        risk_insights = [i for i in result.insights if i.category == InsightCategory.RISK]
        assert len(risk_insights) >= 1

        # Find the opportunity insight
        opp_insights = [i for i in result.insights if i.category == InsightCategory.OPPORTUNITY]
        assert len(opp_insights) >= 1


class TestStructuredLogging:
    """Tests for structured logging in insight generation."""

    @pytest.mark.asyncio
    async def test_logging_on_insight_generation(self, caplog):
        """Test that insight generation logs with structured context."""
        from raglite.insights.proactive import generate_insights

        caplog.set_level(logging.INFO)

        anomaly = Anomaly(
            date="2024-Q3",
            metric="revenue",
            value=1500000,
            expected_value=1000000,
            z_score=2.5,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=50.0,
        )

        await generate_insights([anomaly], [], [], auto_synthesize=False)

        # Check that logs were emitted
        assert len(caplog.records) > 0

        # Check for key log messages
        log_messages = [r.message for r in caplog.records]
        assert any(
            "insight generation" in msg.lower() or "insight generated" in msg.lower()
            for msg in log_messages
        )

    @pytest.mark.asyncio
    async def test_logging_includes_insight_details(self, caplog):
        """Test that log entries include insight details."""
        from raglite.insights.proactive import generate_insights

        caplog.set_level(logging.INFO)

        anomaly = Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=2.5,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=30.0,
        )

        await generate_insights([anomaly], [], [], auto_synthesize=False)

        # Check for category in log records
        found_category_log = False
        for record in caplog.records:
            if hasattr(record, "category") or "anomaly" in str(record.message).lower():
                found_category_log = True
                break
        assert found_category_log
