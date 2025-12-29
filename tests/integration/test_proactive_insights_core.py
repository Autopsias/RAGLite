"""Integration tests for Story 4.7: Proactive Insight Generation.

Tests end-to-end insight generation combining anomaly detection, trend analysis,
and forecast integration. Validates 75%+ insight usefulness (AC4) and
processes the marketing spend example (AC6).
"""

import time
from datetime import datetime

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    ForecastPoint,
    ForecastResult,
    InsightCategory,
    InsightGenerationResult,
    Trend,
    TrendDirection,
)

# Mark all tests as preserve_collection - these are read-only tests
# that don't modify the Qdrant collection (performance optimization)
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]

# =============================================================================
# Expert-Labeled Test Scenarios (AC4)
# =============================================================================

# Expert-labeled insights for validation testing
# Each scenario has inputs and expected insight characteristics
TEST_SCENARIOS = {
    "marketing_anomaly_risk": {
        "description": "Marketing spend 30% YoY increase with stable revenue -> RISK",
        "anomalies": [
            Anomaly(
                date="2024-Q3",
                metric="marketing_spend",
                value=2600000,
                expected_value=2000000,
                z_score=2.5,
                severity=AnomalySeverity.MODERATE,
                magnitude_pct=30.0,
            ),
        ],
        "trends": [
            Trend(
                metric="revenue",
                direction=TrendDirection.STABLE,
                magnitude=2.0,
                confidence=0.9,
                start_date="2024-Q1",
                end_date="2024-Q4",
                cagr=0.02,
                qoq_growth=0.5,
            ),
        ],
        "forecasts": [],
        "expected_categories": [InsightCategory.ANOMALY, InsightCategory.TREND],
        "expected_priority_range": (2, 4),  # (min, max)
        "expected_summary_keywords": ["marketing", "spend"],
    },
    "revenue_growth_opportunity": {
        "description": "Strong revenue growth trend -> OPPORTUNITY",
        "anomalies": [],
        "trends": [
            Trend(
                metric="revenue",
                direction=TrendDirection.INCREASING,
                magnitude=15.0,
                confidence=0.95,
                start_date="2024-Q1",
                end_date="2024-Q4",
                cagr=0.15,
                qoq_growth=3.8,
            ),
        ],
        "forecasts": [],
        "expected_categories": [InsightCategory.OPPORTUNITY],
        "expected_priority_range": (2, 3),
        "expected_summary_keywords": ["revenue"],
    },
    "critical_expense_anomaly": {
        "description": "Critical expense spike -> RISK with priority 1",
        "anomalies": [
            Anomaly(
                date="2024-Q3",
                metric="operating_expenses",
                value=5000000,
                expected_value=3000000,
                z_score=4.0,
                severity=AnomalySeverity.CRITICAL,
                magnitude_pct=66.7,
            ),
        ],
        "trends": [],
        "forecasts": [],
        "expected_categories": [InsightCategory.RISK],
        "expected_priority_range": (1, 1),  # Must be priority 1
        "expected_summary_keywords": ["operating", "expenses"],
    },
    "declining_revenue_risk": {
        "description": "Declining revenue trend -> RISK",
        "anomalies": [],
        "trends": [
            Trend(
                metric="revenue",
                direction=TrendDirection.DECREASING,
                magnitude=12.0,
                confidence=0.85,
                start_date="2024-Q1",
                end_date="2024-Q4",
                cagr=-0.12,
                qoq_growth=-3.0,
            ),
        ],
        "forecasts": [],
        "expected_categories": [InsightCategory.RISK],
        "expected_priority_range": (2, 3),
        "expected_summary_keywords": ["revenue"],
    },
    "forecast_uncertainty": {
        "description": "Forecast with low confidence -> STRATEGIC_PRIORITY",
        "anomalies": [],
        "trends": [],
        "forecasts": [
            ForecastResult(
                metric_name="cash_flow",
                forecast=[
                    ForecastPoint(
                        date=datetime(2025, 1, 1),
                        value=1100000,
                        lower=700000,
                        upper=1500000,
                    ),
                ],
                periods_ahead=4,
                accuracy_estimate="±20%",
            ),
        ],
        "expected_categories": [InsightCategory.STRATEGIC_PRIORITY],
        "expected_priority_range": (3, 4),
        "expected_summary_keywords": ["cash_flow", "forecast"],
    },
    "multi_signal_scenario": {
        "description": "Multiple anomalies and trends -> Multiple insights sorted by priority",
        "anomalies": [
            Anomaly(
                date="2024-Q3",
                metric="revenue",
                value=1500000,
                expected_value=1000000,
                z_score=3.5,
                severity=AnomalySeverity.CRITICAL,
                magnitude_pct=50.0,
            ),
            Anomaly(
                date="2024-Q2",
                metric="expenses",
                value=550000,
                expected_value=500000,
                z_score=2.0,
                severity=AnomalySeverity.MODERATE,
                magnitude_pct=10.0,
            ),
        ],
        "trends": [
            Trend(
                metric="cash_flow",
                direction=TrendDirection.INCREASING,
                magnitude=8.0,
                confidence=0.8,
                start_date="2024-Q1",
                end_date="2024-Q4",
                cagr=0.08,
                qoq_growth=2.0,
            ),
        ],
        "forecasts": [],
        "expected_categories": [
            InsightCategory.RISK,
            InsightCategory.ANOMALY,
            InsightCategory.TREND,
        ],
        "expected_priority_range": (1, 4),
        "expected_summary_keywords": ["revenue", "expenses", "cash_flow"],
    },
}


# =============================================================================
# Integration Tests
# =============================================================================


class TestInsightGenerationIntegration:
    """Integration tests for end-to-end insight generation."""

    @pytest.mark.asyncio
    async def test_end_to_end_insight_generation(self):
        """Test full pipeline: anomaly + trend + forecast -> insights."""
        from raglite.insights.proactive import generate_insights

        anomalies = [
            Anomaly(
                date="2024-Q3",
                metric="marketing_spend",
                value=2600000,
                expected_value=2000000,
                z_score=2.5,
                severity=AnomalySeverity.MODERATE,
                magnitude_pct=30.0,
            ),
        ]

        trends = [
            Trend(
                metric="revenue",
                direction=TrendDirection.STABLE,
                magnitude=2.0,
                confidence=0.9,
                start_date="2024-Q1",
                end_date="2024-Q4",
                cagr=0.02,
                qoq_growth=0.5,
            ),
        ]

        forecasts = [
            ForecastResult(
                metric_name="cash_flow",
                forecast=[
                    ForecastPoint(
                        date=datetime(2025, 1, 1),
                        value=1100000,
                        lower=1000000,
                        upper=1200000,
                    ),
                ],
                periods_ahead=4,
            ),
        ]

        # Use rule-based to avoid LLM dependency in integration test
        result = await generate_insights(
            anomalies,
            trends,
            forecasts,
            auto_synthesize=False,
        )

        assert isinstance(result, InsightGenerationResult)
        assert result.total_generated == 3
        assert result.metrics_analyzed == 3
        assert len(result.insights) == 3

        # Verify sorted by priority
        priorities = [i.priority for i in result.insights]
        assert priorities == sorted(priorities)

    @pytest.mark.asyncio
    async def test_processing_time_under_5_seconds(self):
        """Test that insight generation completes in <5s for typical input (AC4)."""
        from raglite.insights.proactive import generate_insights

        # Create typical input: 10 anomalies, 5 trends, 3 forecasts
        anomalies = [
            Anomaly(
                date=f"2024-Q{i % 4 + 1}",
                metric=f"metric_{i}",
                value=1000000 + i * 100000,
                expected_value=1000000,
                z_score=2.0 + i * 0.1,
                severity=AnomalySeverity.MODERATE,
                magnitude_pct=10.0 + i,
            )
            for i in range(10)
        ]

        trends = [
            Trend(
                metric=f"metric_{i}",
                direction=TrendDirection.INCREASING if i % 2 == 0 else TrendDirection.DECREASING,
                magnitude=10.0 + i,
                confidence=0.8,
                start_date="2024-Q1",
                end_date="2024-Q4",
                cagr=0.10 + i * 0.01,
                qoq_growth=2.5 + i * 0.5,
            )
            for i in range(5)
        ]

        forecasts = [
            ForecastResult(
                metric_name=f"metric_{i}",
                forecast=[
                    ForecastPoint(
                        date=datetime(2025, 1, 1),
                        value=1000000 + i * 50000,
                        lower=900000,
                        upper=1100000,
                    ),
                ],
                periods_ahead=4,
            )
            for i in range(3)
        ]

        start_time = time.time()
        result = await generate_insights(
            anomalies,
            trends,
            forecasts,
            auto_synthesize=False,
        )
        elapsed = time.time() - start_time

        assert elapsed < 5.0, f"Processing took {elapsed:.2f}s, expected <5s"
        assert result.total_generated == 18  # 10 + 5 + 3

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario_name", list(TEST_SCENARIOS.keys()))
    async def test_expert_labeled_scenarios(self, scenario_name):
        """Test insights against expert-labeled scenarios (AC4)."""
        from raglite.insights.proactive import generate_insights

        scenario = TEST_SCENARIOS[scenario_name]

        result = await generate_insights(
            scenario["anomalies"],
            scenario["trends"],
            scenario["forecasts"],
            auto_synthesize=False,
        )

        # Validate categories
        result_categories = {i.category for i in result.insights}
        expected_categories = set(scenario["expected_categories"])

        # At least one expected category should be present
        assert result_categories & expected_categories, (
            f"Scenario '{scenario_name}': Expected one of {expected_categories}, "
            f"got {result_categories}"
        )

        # Validate priority range
        min_priority, max_priority = scenario["expected_priority_range"]

        priorities = [i.priority for i in result.insights]
        assert any(min_priority <= p <= max_priority for p in priorities), (
            f"Scenario '{scenario_name}': Expected priority in [{min_priority}, {max_priority}], "
            f"got {priorities}"
        )


class TestExpertLabeledAccuracy:
    """Tests for validating 75%+ insight usefulness (AC4)."""

    @pytest.mark.asyncio
    async def test_75_percent_accuracy_threshold(self):
        """Validate that 75%+ of insights match expert expectations (AC4)."""
        from raglite.insights.proactive import generate_insights

        correct_classifications = 0
        total_scenarios = len(TEST_SCENARIOS)

        for _scenario_name, scenario in TEST_SCENARIOS.items():
            result = await generate_insights(
                scenario["anomalies"],
                scenario["trends"],
                scenario["forecasts"],
                auto_synthesize=False,
            )

            # Check if any expected category matches
            result_categories = {i.category for i in result.insights}
            expected_categories = set(scenario["expected_categories"])

            if result_categories & expected_categories:
                correct_classifications += 1

        accuracy = correct_classifications / total_scenarios
        assert accuracy >= 0.75, (
            f"Insight accuracy {accuracy:.1%} is below 75% threshold. "
            f"Passed {correct_classifications}/{total_scenarios} scenarios."
        )
