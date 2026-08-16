"""Unit tests for Story 4.6: Core Trend Analysis Functions.

Tests analyze_trends, explain_trend, and integration scenarios.
Split from test_trend_analysis.py as part of Story 8.4a-2.
"""

import os
from datetime import datetime

import pytest

from raglite.shared.models import (
    TimeSeriesData,
    TimeSeriesPoint,
    TrendDirection,
)

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests use scipy which interacts with torch type checking - mocked torch breaks this
pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        os.environ.get("LIGHTWEIGHT_TESTS") == "true",
        reason="Trend analysis tests use scipy which breaks with mocked torch",
    ),
]


# =============================================================================
# Test analyze_trends() Function (AC1-AC5)
# =============================================================================


class TestAnalyzeTrends:
    """Tests for the analyze_trends() function."""

    @pytest.fixture
    def increasing_timeseries(self) -> TimeSeriesData:
        """Create timeseries with known increasing trend."""
        # ~9% annual growth: 100 -> 142 over 8 quarters (2 years)
        values = [100.0, 105.0, 110.0, 116.0, 122.0, 128.0, 135.0, 142.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        return TimeSeriesData(
            metric_name="revenue",
            points=points,
            interval="quarterly",
        )

    @pytest.fixture
    def decreasing_timeseries(self) -> TimeSeriesData:
        """Create timeseries with known decreasing trend."""
        values = [100.0, 95.0, 90.0, 86.0, 82.0, 78.0, 74.0, 70.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        return TimeSeriesData(
            metric_name="expenses",
            points=points,
            interval="quarterly",
        )

    @pytest.fixture
    def stable_timeseries(self) -> TimeSeriesData:
        """Create timeseries with stable (no significant trend)."""
        values = [100.0, 101.0, 99.0, 100.5, 100.0, 99.5, 101.0, 100.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        return TimeSeriesData(
            metric_name="cash_flow",
            points=points,
            interval="quarterly",
        )

    @pytest.mark.asyncio
    async def test_analyze_trends_returns_result(self, increasing_timeseries):
        """Test that analyze_trends returns TrendAnalysisResult."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["revenue"],
            {"revenue": increasing_timeseries},
        )

        assert result.__class__.__name__ == "TrendAnalysisResult"
        assert result.metrics_analyzed == 1

    @pytest.mark.asyncio
    async def test_analyze_trends_detects_increasing(self, increasing_timeseries):
        """Test that increasing trend is correctly identified (AC1, AC3)."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["revenue"],
            {"revenue": increasing_timeseries},
        )

        assert len(result.trends) == 1
        trend = result.trends[0]
        assert trend.metric == "revenue"
        assert trend.direction == TrendDirection.INCREASING
        assert trend.magnitude > 0
        assert trend.cagr > 0.05  # > 5% threshold

    @pytest.mark.asyncio
    async def test_analyze_trends_detects_decreasing(self, decreasing_timeseries):
        """Test that decreasing trend is correctly identified (AC1, AC3)."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["expenses"],
            {"expenses": decreasing_timeseries},
        )

        assert len(result.trends) == 1
        trend = result.trends[0]
        assert trend.direction == TrendDirection.DECREASING
        assert trend.cagr < -0.05  # < -5% threshold

    @pytest.mark.asyncio
    async def test_analyze_trends_detects_stable(self, stable_timeseries):
        """Test that stable trend is correctly identified (AC3)."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["cash_flow"],
            {"cash_flow": stable_timeseries},
        )

        assert len(result.trends) == 1
        trend = result.trends[0]
        assert trend.direction == TrendDirection.STABLE
        assert -0.05 <= trend.cagr <= 0.05

    @pytest.mark.asyncio
    async def test_analyze_trends_multiple_metrics(
        self, increasing_timeseries, decreasing_timeseries, stable_timeseries
    ):
        """Test analyzing multiple metrics at once."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["revenue", "expenses", "cash_flow"],
            {
                "revenue": increasing_timeseries,
                "expenses": decreasing_timeseries,
                "cash_flow": stable_timeseries,
            },
        )

        assert result.metrics_analyzed == 3
        assert len(result.trends) == 3

        # Find each trend
        directions = {t.metric: t.direction for t in result.trends}
        assert directions["revenue"] == TrendDirection.INCREASING
        assert directions["expenses"] == TrendDirection.DECREASING
        assert directions["cash_flow"] == TrendDirection.STABLE

    @pytest.mark.asyncio
    async def test_analyze_trends_detects_correlations(
        self, increasing_timeseries, decreasing_timeseries
    ):
        """Test that correlations are detected between metrics (AC1)."""
        from raglite.insights.trends import analyze_trends

        # Create positively correlated data
        values_a = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0]
        values_b = [50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0]

        ts_a = TimeSeriesData(
            metric_name="revenue",
            points=[
                TimeSeriesPoint(date=datetime(2024, i, 1), value=values_a[i - 1], label=f"Q{i}")
                for i in range(1, 9)
            ],
        )
        ts_b = TimeSeriesData(
            metric_name="marketing",
            points=[
                TimeSeriesPoint(date=datetime(2024, i, 1), value=values_b[i - 1], label=f"Q{i}")
                for i in range(1, 9)
            ],
        )

        result = await analyze_trends(
            ["revenue", "marketing"],
            {"revenue": ts_a, "marketing": ts_b},
        )

        # Should detect strong positive correlation
        assert len(result.correlations) >= 1
        corr = result.correlations[0]
        assert corr.correlation_coefficient > 0.9

    @pytest.mark.asyncio
    async def test_analyze_trends_insufficient_data(self):
        """Test that analyze_trends raises ValueError with < 3 data points."""
        from raglite.insights.trends import analyze_trends

        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0, label="Q1"),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=110.0, label="Q2"),
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        with pytest.raises(ValueError, match="Insufficient data"):
            await analyze_trends(["revenue"], {"revenue": timeseries})

    @pytest.mark.asyncio
    async def test_analyze_trends_missing_metric(self, increasing_timeseries):
        """Test handling of missing metric in data dict."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["revenue", "nonexistent"],
            {"revenue": increasing_timeseries},
        )

        # Should analyze available metrics only
        assert result.metrics_analyzed == 1

    @pytest.mark.asyncio
    async def test_trend_has_required_fields(self, increasing_timeseries):
        """Test that each detected trend has all required fields (AC3)."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["revenue"],
            {"revenue": increasing_timeseries},
        )

        for trend in result.trends:
            assert trend.metric is not None
            assert trend.direction.name in ["INCREASING", "DECREASING", "STABLE"]
            assert trend.magnitude is not None
            assert trend.start_date is not None
            assert trend.end_date is not None
            assert 0.0 <= trend.confidence <= 1.0


# =============================================================================
# Test explain_trend() Function (AC2)
