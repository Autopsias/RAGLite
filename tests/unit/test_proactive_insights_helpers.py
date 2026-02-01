"""Unit tests for proactive insight helper functions.

Tests the calculate_insight_priority(), categorize_insight(), and filter_insights()
helper functions. Corresponds to AC2, AC3, AC4 from Story 4.7.
"""

from datetime import datetime

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    ForecastPoint,
    ForecastResult,
    Insight,
    InsightCategory,
    Trend,
    TrendDirection,
)


class TestCalculateInsightPriority:
    """Tests for the calculate_insight_priority() function."""

    def test_critical_anomaly_priority_1(self):
        """Test critical anomaly gets priority 1 (AC3)."""
        from raglite.insights.proactive import calculate_insight_priority

        anomaly = Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=30.0,
        )

        priority = calculate_insight_priority(anomaly=anomaly)
        assert priority == 1

    def test_moderate_anomaly_priority_2(self):
        """Test moderate anomaly gets priority 2."""
        from raglite.insights.proactive import calculate_insight_priority

        anomaly = Anomaly(
            date="2024-Q3",
            metric="expenses",
            value=550000,
            expected_value=500000,
            z_score=2.2,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=10.0,
        )

        priority = calculate_insight_priority(anomaly=anomaly)
        assert priority == 2

    def test_minor_anomaly_priority_3(self):
        """Test minor anomaly gets default priority 3."""
        from raglite.insights.proactive import calculate_insight_priority

        anomaly = Anomaly(
            date="2024-Q3",
            metric="cash_flow",
            value=105000,
            expected_value=100000,
            z_score=1.6,
            severity=AnomalySeverity.MINOR,
            magnitude_pct=5.0,
        )

        priority = calculate_insight_priority(anomaly=anomaly)
        assert priority == 3

    def test_high_magnitude_trend_priority_2(self):
        """Test trend with >20% magnitude gets priority 2."""
        from raglite.insights.proactive import calculate_insight_priority

        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=25.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        priority = calculate_insight_priority(trend=trend)
        assert priority == 2

    def test_medium_magnitude_trend_priority_3(self):
        """Test trend with 10-20% magnitude gets priority 3."""
        from raglite.insights.proactive import calculate_insight_priority

        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=15.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        priority = calculate_insight_priority(trend=trend)
        assert priority == 3

    def test_combined_critical_anomaly_and_trend(self):
        """Test combined critical anomaly and trend gets priority 1."""
        from raglite.insights.proactive import calculate_insight_priority

        anomaly = Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=30.0,
        )
        trend = Trend(
            metric="marketing_spend",
            direction=TrendDirection.INCREASING,
            magnitude=30.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        priority = calculate_insight_priority(anomaly=anomaly, trend=trend)
        assert priority == 1  # Critical anomaly takes precedence

    def test_default_priority_with_no_inputs(self):
        """Test default priority 3 with no significant inputs."""
        from raglite.insights.proactive import calculate_insight_priority

        priority = calculate_insight_priority()
        assert priority == 3


class TestCategorizeInsight:
    """Tests for the categorize_insight() function."""

    def test_critical_anomaly_categorized_as_risk(self):
        """Test critical anomaly is categorized as RISK (AC2)."""
        from raglite.insights.proactive import categorize_insight

        anomaly = Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=30.0,
        )

        category = categorize_insight(anomaly=anomaly)
        assert category == InsightCategory.RISK

    def test_increasing_high_magnitude_trend_categorized_as_opportunity(self):
        """Test increasing trend >10% is categorized as OPPORTUNITY (AC2)."""
        from raglite.insights.proactive import categorize_insight

        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=15.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        category = categorize_insight(trend=trend)
        assert category == InsightCategory.OPPORTUNITY

    def test_decreasing_high_magnitude_trend_categorized_as_risk(self):
        """Test decreasing trend >10% is categorized as RISK (AC2)."""
        from raglite.insights.proactive import categorize_insight

        trend = Trend(
            metric="revenue",
            direction=TrendDirection.DECREASING,
            magnitude=15.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        category = categorize_insight(trend=trend)
        assert category == InsightCategory.RISK

    def test_moderate_anomaly_categorized_as_anomaly(self):
        """Test moderate anomaly (not critical) is categorized as ANOMALY."""
        from raglite.insights.proactive import categorize_insight

        anomaly = Anomaly(
            date="2024-Q3",
            metric="expenses",
            value=550000,
            expected_value=500000,
            z_score=2.2,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=10.0,
        )

        category = categorize_insight(anomaly=anomaly)
        assert category == InsightCategory.ANOMALY

    def test_stable_trend_categorized_as_trend(self):
        """Test stable trend is categorized as TREND."""
        from raglite.insights.proactive import categorize_insight

        trend = Trend(
            metric="cash_flow",
            direction=TrendDirection.STABLE,
            magnitude=3.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        category = categorize_insight(trend=trend)
        assert category == InsightCategory.TREND

    def test_forecast_only_categorized_as_strategic_priority(self):
        """Test forecast without anomaly/trend is categorized as STRATEGIC_PRIORITY."""
        from raglite.insights.proactive import categorize_insight

        forecast = ForecastResult(
            metric_name="revenue",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=1100000,
                    lower=1000000,
                    upper=1200000,
                )
            ],
            periods_ahead=4,
        )

        category = categorize_insight(forecast=forecast)
        assert category == InsightCategory.STRATEGIC_PRIORITY


class TestFilterInsights:
    """Tests for the filter_insights() function."""

    @pytest.fixture
    def sample_insights(self) -> list[Insight]:
        """Create sample insights for filtering tests."""
        return [
            Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Critical risk",
            ),
            Insight(
                category=InsightCategory.OPPORTUNITY,
                priority=2,
                summary="Growth opportunity",
            ),
            Insight(
                category=InsightCategory.RISK,
                priority=3,
                summary="Medium risk",
            ),
            Insight(
                category=InsightCategory.ANOMALY,
                priority=4,
                summary="Minor anomaly",
            ),
            Insight(
                category=InsightCategory.TREND,
                priority=5,
                summary="Stable trend",
            ),
        ]

    def test_filter_by_category(self, sample_insights):
        """Test filtering insights by category."""
        from raglite.insights.proactive import filter_insights

        result = filter_insights(sample_insights, category=InsightCategory.RISK)

        assert len(result) == 2
        assert all(i.category == InsightCategory.RISK for i in result)

    def test_filter_by_max_priority(self, sample_insights):
        """Test filtering insights by max priority."""
        from raglite.insights.proactive import filter_insights

        result = filter_insights(sample_insights, max_priority=2)

        assert len(result) == 2
        assert all(i.priority <= 2 for i in result)

    def test_filter_by_limit(self, sample_insights):
        """Test limiting number of insights returned."""
        from raglite.insights.proactive import filter_insights

        result = filter_insights(sample_insights, limit=3)

        assert len(result) == 3

    def test_filter_combined(self, sample_insights):
        """Test combining multiple filters."""
        from raglite.insights.proactive import filter_insights

        result = filter_insights(
            sample_insights,
            category=InsightCategory.RISK,
            max_priority=2,
            limit=1,
        )

        assert len(result) == 1
        assert result[0].category == InsightCategory.RISK
        assert result[0].priority <= 2

    def test_filter_no_match(self, sample_insights):
        """Test filter with no matching insights."""
        from raglite.insights.proactive import filter_insights

        result = filter_insights(
            sample_insights,
            category=InsightCategory.STRATEGIC_PRIORITY,
        )

        assert len(result) == 0
