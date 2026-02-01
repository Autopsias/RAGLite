"""Tests for priority calculation logic."""

from raglite.insights.proactive import calculate_insight_priority
from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    Trend,
    TrendDirection,
)


class TestPriorityCalculation:
    """Tests for priority calculation logic."""

    def test_critical_anomaly_priority_1(self):
        """Critical anomaly should get priority 1."""
        anomaly = Anomaly(
            date="2024-Q3",
            metric="costs",
            value=150.0,
            expected_value=100.0,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=50.0,
        )

        priority = calculate_insight_priority(anomaly=anomaly)

        assert priority == 1

    def test_moderate_anomaly_priority_2(self):
        """Moderate anomaly should get priority 2."""
        anomaly = Anomaly(
            date="2024-Q3",
            metric="costs",
            value=120.0,
            expected_value=100.0,
            z_score=2.2,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=20.0,
        )

        priority = calculate_insight_priority(anomaly=anomaly)

        assert priority == 2

    def test_high_magnitude_trend_priority_2(self):
        """High magnitude trend (>20%) should get priority 2."""
        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=25.0,
            confidence=0.85,
            start_date="2023-Q1",
            end_date="2024-Q4",
            cagr=0.25,
            qoq_growth=0.06,
        )

        priority = calculate_insight_priority(trend=trend)

        assert priority == 2

    def test_default_priority_3(self):
        """Without strong signals, default priority is 3."""
        trend = Trend(
            metric="revenue",
            direction=TrendDirection.STABLE,
            magnitude=5.0,
            confidence=0.75,
            start_date="2023-Q1",
            end_date="2024-Q4",
            cagr=0.05,
            qoq_growth=0.01,
        )

        priority = calculate_insight_priority(trend=trend)

        assert priority == 3
