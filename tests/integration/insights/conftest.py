"""Shared fixtures for insights integration tests."""

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

# =============================================================================
# Expert-Labeled Test Scenarios (AC4)
# =============================================================================

# Expert-labeled insights for validation testing
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


@pytest.fixture
def test_scenarios():
    """Return expert-labeled test scenarios."""
    return TEST_SCENARIOS


@pytest.fixture
def marketing_scenario():
    """Return marketing spend anomaly scenario."""
    return TEST_SCENARIOS["marketing_anomaly_risk"]
