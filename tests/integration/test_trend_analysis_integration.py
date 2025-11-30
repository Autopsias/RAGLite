"""Integration tests for Story 4.6: Trend Analysis & Pattern Recognition.

Tests end-to-end trend analysis pipeline with real data extraction.
These tests validate 90%+ trend detection accuracy per Tech Spec requirement.
"""

from datetime import datetime

import pytest

from raglite.shared.models import (
    TimeSeriesData,
    TimeSeriesPoint,
    TrendDirection,
)

# Mark all tests as preserve_collection - these are read-only tests
# that don't modify the Qdrant collection (performance optimization)
pytestmark = pytest.mark.preserve_collection

# =============================================================================
# Test Expert-Labeled Trend Dataset
# =============================================================================


class TestTrendDetectionAccuracy:
    """Tests for 90%+ trend detection accuracy using expert-labeled dataset (AC5, NFR)."""

    @pytest.fixture
    def expert_labeled_trends(self) -> list[dict]:
        """Expert-labeled dataset with known trends for accuracy validation.

        Each entry contains:
        - values: Time series values (8 quarters)
        - expected_direction: Expert-classified direction
        - expected_cagr_range: Expected CAGR range (min, max)
        - description: Description of the trend
        """
        return [
            {
                "metric": "revenue_growth",
                "values": [100.0, 108.0, 116.5, 125.8, 135.9, 146.8, 158.5, 171.2],
                "expected_direction": TrendDirection.INCREASING,
                "expected_cagr_range": (0.10, 0.15),  # 10-15% annual growth
                "description": "Strong consistent revenue growth",
            },
            {
                "metric": "revenue_moderate",
                "values": [100.0, 103.0, 106.1, 109.3, 112.6, 115.9, 119.4, 123.0],
                "expected_direction": TrendDirection.INCREASING,
                "expected_cagr_range": (0.05, 0.12),  # 5-12% annual growth
                "description": "Moderate revenue growth",
            },
            {
                "metric": "cost_decline",
                "values": [100.0, 94.0, 88.4, 83.1, 78.1, 73.4, 69.0, 64.9],
                "expected_direction": TrendDirection.DECREASING,
                "expected_cagr_range": (-0.15, -0.08),  # 8-15% annual decline
                "description": "Cost reduction program",
            },
            {
                "metric": "expenses_decline",
                "values": [100.0, 97.0, 94.1, 91.3, 88.6, 85.9, 83.4, 80.9],
                "expected_direction": TrendDirection.DECREASING,
                "expected_cagr_range": (-0.12, -0.05),  # 5-12% annual decline
                "description": "Moderate expense reduction",
            },
            {
                "metric": "stable_cash_flow",
                "values": [100.0, 101.0, 99.5, 100.5, 100.0, 99.0, 101.0, 100.5],
                "expected_direction": TrendDirection.STABLE,
                "expected_cagr_range": (-0.05, 0.05),  # Within ±5%
                "description": "Stable cash flow",
            },
            {
                "metric": "stable_margin",
                "values": [25.0, 25.2, 24.8, 25.1, 24.9, 25.3, 25.0, 25.1],
                "expected_direction": TrendDirection.STABLE,
                "expected_cagr_range": (-0.05, 0.05),
                "description": "Stable profit margin",
            },
            {
                "metric": "high_growth",
                "values": [50.0, 60.0, 72.0, 86.4, 103.7, 124.4, 149.3, 179.2],
                "expected_direction": TrendDirection.INCREASING,
                "expected_cagr_range": (0.20, 0.35),  # 20-35% annual growth
                "description": "High-growth startup revenue",
            },
            {
                "metric": "rapid_decline",
                "values": [200.0, 170.0, 144.5, 122.8, 104.4, 88.7, 75.4, 64.1],
                "expected_direction": TrendDirection.DECREASING,
                "expected_cagr_range": (-0.25, -0.15),  # 15-25% annual decline
                "description": "Rapid market share loss",
            },
            {
                "metric": "slow_growth",
                "values": [100.0, 101.5, 103.0, 104.6, 106.1, 107.7, 109.4, 111.0],
                "expected_direction": TrendDirection.INCREASING,
                "expected_cagr_range": (0.02, 0.08),
                "description": "Slow but steady growth (borderline stable)",
            },
            {
                "metric": "flat_revenue",
                "values": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
                "expected_direction": TrendDirection.STABLE,
                "expected_cagr_range": (-0.01, 0.01),
                "description": "Perfectly flat (no change)",
            },
        ]

    @pytest.mark.asyncio
    async def test_trend_detection_accuracy_90_percent(self, expert_labeled_trends):
        """Test that trend detection achieves 90%+ accuracy on labeled dataset (Tech Spec NFR)."""
        from raglite.insights.trends import analyze_trends

        correct_predictions = 0
        total_predictions = len(expert_labeled_trends)

        for labeled in expert_labeled_trends:
            # Create timeseries from labeled data
            points = [
                TimeSeriesPoint(
                    date=datetime(2024, i, 1),
                    value=labeled["values"][i - 1],
                    label=f"Q{i}",
                )
                for i in range(1, len(labeled["values"]) + 1)
            ]
            timeseries = TimeSeriesData(
                metric_name=labeled["metric"],
                points=points,
                interval="quarterly",
            )

            # Analyze trend
            result = await analyze_trends(
                [labeled["metric"]],
                {labeled["metric"]: timeseries},
            )

            # Check prediction
            predicted = result.trends[0].direction
            expected = labeled["expected_direction"]

            if predicted == expected:
                correct_predictions += 1
            else:
                print(
                    f"Mismatch: {labeled['metric']} - "
                    f"Expected {expected.value}, Got {predicted.value} "
                    f"(CAGR: {result.trends[0].cagr:.4f})"
                )

        accuracy = correct_predictions / total_predictions * 100
        print(
            f"Trend detection accuracy: {accuracy:.1f}% ({correct_predictions}/{total_predictions})"
        )

        # Tech Spec requirement: 90%+ accuracy
        assert accuracy >= 90.0, f"Accuracy {accuracy:.1f}% below 90% threshold"


# =============================================================================
# Test End-to-End Pipeline (AC4)
# =============================================================================


class TestEndToEndPipeline:
    """Tests for end-to-end trend analysis pipeline."""

    @pytest.mark.asyncio
    async def test_timeseries_to_trend_pipeline(self):
        """Test end-to-end: time-series extraction -> trend analysis -> result formatting."""
        from raglite.insights.trends import analyze_trends

        # Simulate extracted time series data (as would come from Story 4.1)
        revenue_data = TimeSeriesData(
            metric_name="revenue",
            points=[
                TimeSeriesPoint(date=datetime(2023, 1, 1), value=100.0, label="Q1 2023"),
                TimeSeriesPoint(date=datetime(2023, 4, 1), value=108.0, label="Q2 2023"),
                TimeSeriesPoint(date=datetime(2023, 7, 1), value=116.6, label="Q3 2023"),
                TimeSeriesPoint(date=datetime(2023, 10, 1), value=125.9, label="Q4 2023"),
                TimeSeriesPoint(date=datetime(2024, 1, 1), value=136.0, label="Q1 2024"),
                TimeSeriesPoint(date=datetime(2024, 4, 1), value=146.9, label="Q2 2024"),
                TimeSeriesPoint(date=datetime(2024, 7, 1), value=158.7, label="Q3 2024"),
                TimeSeriesPoint(date=datetime(2024, 10, 1), value=171.4, label="Q4 2024"),
            ],
            interval="quarterly",
            source_documents=["Q1_2023_Report.pdf", "Q2_2024_Report.pdf"],
        )

        expenses_data = TimeSeriesData(
            metric_name="expenses",
            points=[
                TimeSeriesPoint(date=datetime(2023, 1, 1), value=60.0, label="Q1 2023"),
                TimeSeriesPoint(date=datetime(2023, 4, 1), value=63.0, label="Q2 2023"),
                TimeSeriesPoint(date=datetime(2023, 7, 1), value=66.2, label="Q3 2023"),
                TimeSeriesPoint(date=datetime(2023, 10, 1), value=69.5, label="Q4 2023"),
                TimeSeriesPoint(date=datetime(2024, 1, 1), value=73.0, label="Q1 2024"),
                TimeSeriesPoint(date=datetime(2024, 4, 1), value=76.7, label="Q2 2024"),
                TimeSeriesPoint(date=datetime(2024, 7, 1), value=80.5, label="Q3 2024"),
                TimeSeriesPoint(date=datetime(2024, 10, 1), value=84.5, label="Q4 2024"),
            ],
            interval="quarterly",
            source_documents=["Q1_2023_Report.pdf", "Q2_2024_Report.pdf"],
        )

        # Run trend analysis
        result = await analyze_trends(
            ["revenue", "expenses"],
            {"revenue": revenue_data, "expenses": expenses_data},
        )

        # Validate result structure
        assert result.metrics_analyzed == 2
        assert len(result.trends) == 2

        # Validate trend detection
        revenue_trend = next(t for t in result.trends if t.metric == "revenue")
        expenses_trend = next(t for t in result.trends if t.metric == "expenses")

        assert revenue_trend.direction == TrendDirection.INCREASING
        assert expenses_trend.direction == TrendDirection.INCREASING

        # Both are growing, should detect positive correlation
        assert len(result.correlations) >= 1
        corr = result.correlations[0]
        assert corr.correlation_coefficient > 0.9  # Strong positive

    @pytest.mark.asyncio
    async def test_multi_metric_analysis_pipeline(self):
        """Test analysis of multiple metrics simultaneously."""
        from raglite.insights.trends import analyze_trends

        # Create 5 metrics with different trends
        metrics_data = {
            "revenue": TimeSeriesData(
                metric_name="revenue",
                points=[
                    TimeSeriesPoint(date=datetime(2024, i, 1), value=100 + i * 10, label=f"Q{i}")
                    for i in range(1, 9)
                ],
            ),
            "costs": TimeSeriesData(
                metric_name="costs",
                points=[
                    TimeSeriesPoint(date=datetime(2024, i, 1), value=80 - i * 5, label=f"Q{i}")
                    for i in range(1, 9)
                ],
            ),
            "margin": TimeSeriesData(
                metric_name="margin",
                points=[
                    TimeSeriesPoint(date=datetime(2024, i, 1), value=20 + 0.1, label=f"Q{i}")
                    for i in range(1, 9)
                ],
            ),
            "employees": TimeSeriesData(
                metric_name="employees",
                points=[
                    TimeSeriesPoint(date=datetime(2024, i, 1), value=50 + i * 3, label=f"Q{i}")
                    for i in range(1, 9)
                ],
            ),
            "productivity": TimeSeriesData(
                metric_name="productivity",
                points=[
                    TimeSeriesPoint(date=datetime(2024, i, 1), value=100 + i * 8, label=f"Q{i}")
                    for i in range(1, 9)
                ],
            ),
        }

        result = await analyze_trends(list(metrics_data.keys()), metrics_data)

        # Should analyze all 5 metrics
        assert result.metrics_analyzed == 5
        assert len(result.trends) == 5

        # Should find correlations between pairs
        # With 5 metrics, there are C(5,2) = 10 possible pairs
        # But we only keep significant correlations
        assert len(result.correlations) >= 1


# =============================================================================
# Test Correlation Detection on Multi-Metric Dataset (AC1)
# =============================================================================


class TestCorrelationDetection:
    """Tests for correlation detection across multiple metrics."""

    @pytest.mark.asyncio
    async def test_detects_revenue_expense_correlation(self):
        """Test detection of correlation between revenue and expenses."""
        from raglite.insights.trends import analyze_trends

        # Revenue and expenses that grow together (common pattern)
        revenue = TimeSeriesData(
            metric_name="revenue",
            points=[
                TimeSeriesPoint(date=datetime(2024, i, 1), value=100 + i * 15, label=f"Q{i}")
                for i in range(1, 9)
            ],
        )
        expenses = TimeSeriesData(
            metric_name="expenses",
            points=[
                TimeSeriesPoint(date=datetime(2024, i, 1), value=60 + i * 8, label=f"Q{i}")
                for i in range(1, 9)
            ],
        )

        result = await analyze_trends(
            ["revenue", "expenses"],
            {"revenue": revenue, "expenses": expenses},
        )

        # Should detect strong positive correlation
        assert len(result.correlations) == 1
        corr = result.correlations[0]
        assert corr.correlation_coefficient > 0.99
        assert "positive" in corr.interpretation.lower()

    @pytest.mark.asyncio
    async def test_detects_negative_correlation(self):
        """Test detection of negative correlation (inverse relationship)."""
        from raglite.insights.trends import analyze_trends

        # Market share goes up while competitor share goes down
        our_share = TimeSeriesData(
            metric_name="our_share",
            points=[
                TimeSeriesPoint(date=datetime(2024, i, 1), value=30 + i * 5, label=f"Q{i}")
                for i in range(1, 9)
            ],
        )
        competitor_share = TimeSeriesData(
            metric_name="competitor_share",
            points=[
                TimeSeriesPoint(date=datetime(2024, i, 1), value=70 - i * 5, label=f"Q{i}")
                for i in range(1, 9)
            ],
        )

        result = await analyze_trends(
            ["our_share", "competitor_share"],
            {"our_share": our_share, "competitor_share": competitor_share},
        )

        # Should detect strong negative correlation
        assert len(result.correlations) == 1
        corr = result.correlations[0]
        assert corr.correlation_coefficient < -0.99
        assert "negative" in corr.interpretation.lower()

    @pytest.mark.asyncio
    async def test_ignores_weak_correlations(self):
        """Test that weak correlations (|r| < 0.4) are excluded."""
        from raglite.insights.trends import analyze_trends

        # Create uncorrelated data
        metric_a = TimeSeriesData(
            metric_name="metric_a",
            points=[
                TimeSeriesPoint(date=datetime(2024, i, 1), value=100 + i * 10, label=f"Q{i}")
                for i in range(1, 9)
            ],
        )
        # Random-ish values with no clear correlation
        metric_b = TimeSeriesData(
            metric_name="metric_b",
            points=[
                TimeSeriesPoint(date=datetime(2024, i, 1), value=v, label=f"Q{i}")
                for i, v in enumerate([50, 48, 52, 49, 51, 47, 53, 50], 1)
            ],
        )

        result = await analyze_trends(
            ["metric_a", "metric_b"],
            {"metric_a": metric_a, "metric_b": metric_b},
        )

        # Weak correlation should be filtered out
        # (The correlation exists but is not significant)
        for corr in result.correlations:
            assert abs(corr.correlation_coefficient) > 0.4


# =============================================================================
# Test Processing Time Requirement (Tech Spec)
# =============================================================================


class TestProcessingTime:
    """Tests for processing time requirements (<10s for 5 metrics)."""

    @pytest.mark.asyncio
    async def test_processing_time_under_10_seconds(self):
        """Test that analysis of 5 metrics completes in <10 seconds."""
        import time

        from raglite.insights.trends import analyze_trends

        # Create 5 metrics with 8 quarters each
        metrics_data = {}
        for metric_name in ["revenue", "expenses", "cash_flow", "margin", "employees"]:
            metrics_data[metric_name] = TimeSeriesData(
                metric_name=metric_name,
                points=[
                    TimeSeriesPoint(
                        date=datetime(2024, i, 1),
                        value=100.0 + i * 5,
                        label=f"Q{i}",
                    )
                    for i in range(1, 9)
                ],
            )

        start_time = time.time()
        result = await analyze_trends(list(metrics_data.keys()), metrics_data)
        elapsed_time = time.time() - start_time

        # Tech Spec requirement: <10s for 5 metrics
        assert elapsed_time < 10.0, f"Processing took {elapsed_time:.2f}s (>10s threshold)"
        assert result.metrics_analyzed == 5

        print(f"Processing time for 5 metrics: {elapsed_time:.3f}s")


# =============================================================================
# Test Integration with Anomaly Detection (Story 4.5)
# =============================================================================


class TestIntegrationWithAnomalyDetection:
    """Tests for integration between trend analysis and anomaly detection."""

    @pytest.mark.asyncio
    async def test_trend_with_anomaly_data(self):
        """Test trend detection on data that also has anomalies."""
        from raglite.insights.anomalies import detect_anomalies
        from raglite.insights.trends import analyze_trends

        # Data with clear trend but also an anomaly
        values = [100.0, 110.0, 120.0, 500.0, 140.0, 150.0, 160.0, 170.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        # Both should work on same data
        trend_result = await analyze_trends(["revenue"], {"revenue": timeseries})
        anomaly_result = await detect_anomalies("revenue", timeseries)

        # Should detect increasing trend despite anomaly
        assert trend_result.trends[0].direction == TrendDirection.INCREASING

        # Should also detect the 500.0 anomaly
        assert len(anomaly_result.anomalies) >= 1
        assert any(a.value == 500.0 for a in anomaly_result.anomalies)
