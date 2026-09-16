"""Tests for insight categorization logic."""

from raglite.insights.proactive import categorize_insight
from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    InsightCategory,
    Trend,
    TrendDirection,
)


class TestInsightCategorization:
    """Tests for insight categorization logic."""

    def test_categorize_critical_anomaly_as_risk(self):
        """Critical anomaly should be categorized as RISK."""
        anomaly = Anomaly(
            date="2024-Q3",
            metric="costs",
            value=150.0,
            expected_value=100.0,
            z_score=3.0,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=50.0,
        )

        category = categorize_insight(anomaly=anomaly)

        assert category == InsightCategory.RISK

    def test_categorize_increasing_trend_as_opportunity(self):
        """Strong increasing trend should be categorized as OPPORTUNITY."""
        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=15.0,
            confidence=0.85,
            start_date="2023-Q1",
            end_date="2024-Q4",
            cagr=0.15,
            qoq_growth=0.04,
        )

        category = categorize_insight(trend=trend)

        assert category == InsightCategory.OPPORTUNITY

    def test_categorize_decreasing_trend_as_risk(self):
        """Strong decreasing trend should be categorized as RISK."""
        trend = Trend(
            metric="profit",
            direction=TrendDirection.DECREASING,
            magnitude=12.0,
            confidence=0.80,
            start_date="2023-Q1",
            end_date="2024-Q4",
            cagr=-0.06,
            qoq_growth=-0.015,
        )

        category = categorize_insight(trend=trend)

        assert category == InsightCategory.RISK

    def test_categorize_moderate_anomaly_as_anomaly(self):
        """Moderate anomaly should be categorized as ANOMALY."""
        anomaly = Anomaly(
            date="2024-Q3",
            metric="inventory",
            value=110.0,
            expected_value=100.0,
            z_score=2.0,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=10.0,
        )

        category = categorize_insight(anomaly=anomaly)

        assert category == InsightCategory.ANOMALY
