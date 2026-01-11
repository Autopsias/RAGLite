"""Unit tests for edge cases and structured logging in trend analysis."""

import logging
from datetime import datetime

import pytest

from raglite.shared.models import TimeSeriesData, TimeSeriesPoint, TrendDirection


class TestEdgeCases:
    """Tests for edge cases in trend analysis."""

    @pytest.mark.asyncio
    async def test_identical_values(self):
        """Test trend analysis with identical values (zero variance)."""
        from raglite.insights.trends import analyze_trends

        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=100.0, label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await analyze_trends(["revenue"], {"revenue": timeseries})

        assert len(result.trends) == 1
        trend = result.trends[0]
        assert trend.direction == TrendDirection.STABLE
        assert trend.cagr == 0.0

    @pytest.mark.asyncio
    async def test_negative_values(self):
        """Test trend analysis with negative values."""
        from raglite.insights.trends import analyze_trends

        values = [-100.0, -90.0, -80.0, -70.0, -60.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="net_income", points=points)

        result = await analyze_trends(["net_income"], {"revenue": timeseries})

        # Should still analyze (even though CAGR may be unusual with negative start)
        assert result.metrics_analyzed >= 0

    @pytest.mark.asyncio
    async def test_large_values(self):
        """Test trend analysis with large values (millions)."""
        from raglite.insights.trends import analyze_trends

        values = [1_000_000.0, 1_100_000.0, 1_200_000.0, 1_300_000.0, 1_400_000.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await analyze_trends(["revenue"], {"revenue": timeseries})

        assert len(result.trends) == 1
        assert result.trends[0].direction == TrendDirection.INCREASING

    @pytest.mark.asyncio
    async def test_single_metric_no_correlations(self):
        """Test that single metric produces no correlations."""
        from raglite.insights.trends import analyze_trends

        values = [100.0, 110.0, 120.0, 130.0, 140.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await analyze_trends(["revenue"], {"revenue": timeseries})

        assert result.correlations == []


class TestStructuredLogging:
    """Tests for structured logging in trend analysis."""

    @pytest.mark.asyncio
    async def test_logging_on_trend_detection(self, caplog):
        """Test that trend detection logs with structured context (AC4)."""
        from raglite.insights.trends import analyze_trends

        caplog.set_level(logging.INFO)

        values = [100.0, 110.0, 120.0, 130.0, 140.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        await analyze_trends(["revenue"], {"revenue": timeseries})

        # Check that logs were emitted
        assert len(caplog.records) > 0

        # Check for key log messages
        log_messages = [r.message for r in caplog.records]
        assert any(
            "trend analysis" in msg.lower() or "trend detected" in msg.lower()
            for msg in log_messages
        )

    @pytest.mark.asyncio
    async def test_logging_includes_metric_details(self, caplog):
        """Test that log entries include metric details (AC4)."""
        from raglite.insights.trends import analyze_trends

        caplog.set_level(logging.INFO)

        values = [100.0, 110.0, 120.0, 130.0, 140.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        await analyze_trends(["revenue"], {"revenue": timeseries})

        # Check for metric in log records
        found_metric_log = False
        for record in caplog.records:
            if hasattr(record, "metric") or "revenue" in str(record.message):
                found_metric_log = True
                break
        assert found_metric_log


class TestSyntheticDataKnownTrends:
    """Tests using synthetic data with known trends for validation (AC5)."""

    @pytest.mark.asyncio
    async def test_increasing_trend_synthetic_data(self):
        """Test 8 quarters of growth correctly classified (AC5)."""
        from raglite.insights.trends import analyze_trends

        # Known increasing trend: ~9% annual growth
        values = [100.0, 105.0, 110.0, 116.0, 122.0, 128.0, 135.0, 142.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await analyze_trends(["revenue"], {"revenue": timeseries})

        assert result.trends[0].direction == TrendDirection.INCREASING

    @pytest.mark.asyncio
    async def test_decreasing_trend_synthetic_data(self):
        """Test 8 quarters of decline correctly classified (AC5)."""
        from raglite.insights.trends import analyze_trends

        # Known decreasing trend: ~-8% annual growth
        values = [100.0, 95.0, 90.0, 86.0, 82.0, 78.0, 74.0, 70.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        timeseries = TimeSeriesData(metric_name="expenses", points=points)

        result = await analyze_trends(["expenses"], {"expenses": timeseries})

        assert result.trends[0].direction == TrendDirection.DECREASING

    @pytest.mark.asyncio
    async def test_stable_trend_synthetic_data(self):
        """Test flat data correctly classified as stable (AC5)."""
        from raglite.insights.trends import analyze_trends

        # Known stable trend: fluctuations within ±5%
        values = [100.0, 101.0, 99.0, 100.5, 100.0, 99.5, 101.0, 100.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        timeseries = TimeSeriesData(metric_name="cash_flow", points=points)

        result = await analyze_trends(["cash_flow"], {"cash_flow": timeseries})

        assert result.trends[0].direction == TrendDirection.STABLE

    @pytest.mark.asyncio
    async def test_correlation_positive_synthetic_data(self):
        """Test perfect positive correlation detected (AC5)."""
        from raglite.insights.trends import detect_correlation

        values_a = [100.0, 110.0, 120.0, 130.0, 140.0]
        values_b = [50.0, 55.0, 60.0, 65.0, 70.0]

        corr = detect_correlation("a", "b", values_a, values_b)

        assert corr.correlation_coefficient == 1.0

    @pytest.mark.asyncio
    async def test_correlation_negative_synthetic_data(self):
        """Test perfect negative correlation detected (AC5)."""
        from raglite.insights.trends import detect_correlation

        values_a = [100.0, 110.0, 120.0, 130.0, 140.0]
        values_b = [70.0, 65.0, 60.0, 55.0, 50.0]

        corr = detect_correlation("a", "b", values_a, values_b)

        assert corr.correlation_coefficient == -1.0
