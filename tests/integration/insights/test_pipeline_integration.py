"""Integration tests for the full pipeline: anomaly -> trend -> insight."""

from datetime import datetime

import pytest

from raglite.shared.models import (
    InsightCategory,
    TimeSeriesData,
    TimeSeriesPoint,
)

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestAnomalyTrendForecastPipeline:
    """Integration tests for the full pipeline: anomaly -> trend -> insight."""

    @pytest.mark.asyncio
    async def test_anomaly_detection_to_insight(self):
        """Test anomaly detection flowing into insight generation."""
        from raglite.insights.anomalies import detect_anomalies
        from raglite.insights.proactive import generate_insights

        # Create time series with anomaly
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=100.0 + i * 2, label=f"Q{i}")
            for i in range(1, 8)
        ]
        # Add anomaly at Q8
        points.append(TimeSeriesPoint(date=datetime(2024, 8, 1), value=200.0, label="Q8"))

        timeseries = TimeSeriesData(metric_name="revenue", points=points, interval="quarterly")

        # Detect anomalies
        anomaly_result = await detect_anomalies("revenue", timeseries)

        # Generate insights from detected anomalies
        result = await generate_insights(
            anomaly_result.anomalies,
            [],
            [],
            auto_synthesize=False,
        )

        # Verify anomalies were detected and converted to insights
        assert anomaly_result.anomalies, "No anomalies detected"
        assert result.total_generated > 0, "No insights generated from anomalies"

    @pytest.mark.asyncio
    async def test_trend_analysis_to_insight(self):
        """Test trend analysis flowing into insight generation."""
        from raglite.insights.proactive import generate_insights
        from raglite.insights.trends import analyze_trends

        # Create time series with clear increasing trend
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=100.0 * (1.05**i), label=f"Q{i}")
            for i in range(1, 9)
        ]

        timeseries = TimeSeriesData(metric_name="revenue", points=points, interval="quarterly")

        # Analyze trends
        trend_result = await analyze_trends(["revenue"], {"revenue": timeseries})

        # Generate insights from detected trends
        result = await generate_insights(
            [],
            trend_result.trends,
            [],
            auto_synthesize=False,
        )

        # Verify trends were detected and converted to insights
        assert trend_result.trends, "No trends detected"
        assert result.total_generated > 0, "No insights generated from trends"

        # The increasing trend should generate an OPPORTUNITY insight
        opportunities = [i for i in result.insights if i.category == InsightCategory.OPPORTUNITY]
        assert opportunities, "No OPPORTUNITY insight generated from increasing trend"
