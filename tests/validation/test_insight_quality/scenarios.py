"""Expert-labeled test scenarios for insight validation.

Story 4.10 Task 2.2: Test scenarios with expected outcomes.
"""

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    InsightCategory,
    Trend,
    TrendDirection,
)

from .models import InsightTestScenario

# ============================================================================
# Expert-Labeled Test Scenarios (Story 4.10 Task 2.2)
# ============================================================================

INSIGHT_TEST_SCENARIOS: list[InsightTestScenario] = [
    # Scenario 1: Marketing spend spike detection (should flag as RISK)
    InsightTestScenario(
        scenario_id="marketing_spike",
        description="Marketing spend increased 30% YoY with no revenue increase",
        anomaly=Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=130000.0,
            expected_value=100000.0,
            z_score=2.5,
            severity=AnomalySeverity.CRITICAL,
            reason="Significant marketing spend increase without ROI",
            magnitude_pct=30.0,
        ),
        expected_category=InsightCategory.RISK,
        expected_priority_range=(1, 2),
        expected_keywords=["marketing", "spend"],
    ),
    # Scenario 2: Revenue growth trend (should flag as OPPORTUNITY)
    InsightTestScenario(
        scenario_id="revenue_growth",
        description="Revenue growing 15% CAGR consistently",
        trend=Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=15.0,
            confidence=0.85,
            start_date="2023-Q1",
            end_date="2024-Q4",
            description="Strong revenue growth trend",
            cagr=0.15,
            qoq_growth=0.04,
        ),
        expected_category=InsightCategory.OPPORTUNITY,
        expected_priority_range=(1, 3),
        expected_keywords=["revenue", "growth"],
    ),
    # Scenario 3: Seasonal pattern recognition (should flag as TREND)
    InsightTestScenario(
        scenario_id="seasonal_pattern",
        description="Q4 consistently 20% higher than Q2",
        trend=Trend(
            metric="sales",
            direction=TrendDirection.STABLE,
            magnitude=5.0,
            confidence=0.75,
            start_date="2022-Q1",
            end_date="2024-Q4",
            description="Seasonal sales pattern with Q4 spike",
            cagr=0.05,
            qoq_growth=0.02,
        ),
        expected_category=InsightCategory.TREND,
        expected_priority_range=(3, 5),
        expected_keywords=["sales"],
    ),
    # Scenario 4: Cost anomaly detection (should flag as ANOMALY)
    InsightTestScenario(
        scenario_id="cost_anomaly",
        description="Cloud costs spiked 40% unexpectedly",
        anomaly=Anomaly(
            date="2024-Q2",
            metric="cloud_costs",
            value=70000.0,
            expected_value=50000.0,
            z_score=2.1,
            severity=AnomalySeverity.MODERATE,
            reason="Unexpected cloud cost increase",
            magnitude_pct=40.0,
        ),
        expected_category=InsightCategory.ANOMALY,
        expected_priority_range=(2, 4),
        expected_keywords=["cloud"],
    ),
    # Scenario 5: Critical expense deviation (should flag as RISK)
    InsightTestScenario(
        scenario_id="expense_critical",
        description="Operating expenses 50% over budget with critical severity",
        anomaly=Anomaly(
            date="2024-Q3",
            metric="operating_expenses",
            value=450000.0,
            expected_value=300000.0,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            reason="Operating expenses significantly over budget",
            magnitude_pct=50.0,
        ),
        expected_category=InsightCategory.RISK,
        expected_priority_range=(1, 2),
        expected_keywords=["expenses"],
    ),
    # Scenario 6: Decreasing profit margin (should flag as RISK)
    InsightTestScenario(
        scenario_id="margin_decline",
        description="Profit margin declining 12% over 2 years",
        trend=Trend(
            metric="profit_margin",
            direction=TrendDirection.DECREASING,
            magnitude=12.0,
            confidence=0.80,
            start_date="2023-Q1",
            end_date="2024-Q4",
            description="Consistent profit margin decline",
            cagr=-0.06,
            qoq_growth=-0.015,
        ),
        expected_category=InsightCategory.RISK,
        expected_priority_range=(2, 3),
        expected_keywords=["margin", "profit"],
    ),
    # Scenario 7: Cash flow improvement opportunity
    InsightTestScenario(
        scenario_id="cashflow_improvement",
        description="Cash flow showing 18% growth opportunity",
        trend=Trend(
            metric="cash_flow",
            direction=TrendDirection.INCREASING,
            magnitude=18.0,
            confidence=0.82,
            start_date="2023-Q2",
            end_date="2024-Q4",
            description="Strong cash flow improvement trend",
            cagr=0.18,
            qoq_growth=0.045,
        ),
        expected_category=InsightCategory.OPPORTUNITY,
        expected_priority_range=(1, 3),
        expected_keywords=["cash"],
    ),
    # Scenario 8: Minor inventory anomaly
    InsightTestScenario(
        scenario_id="inventory_minor",
        description="Inventory levels slightly elevated",
        anomaly=Anomaly(
            date="2024-Q3",
            metric="inventory",
            value=85000.0,
            expected_value=75000.0,
            z_score=1.6,
            severity=AnomalySeverity.MINOR,
            reason="Slightly elevated inventory levels",
            magnitude_pct=13.3,
        ),
        expected_category=InsightCategory.ANOMALY,
        expected_priority_range=(3, 5),
        expected_keywords=["inventory"],
    ),
    # Scenario 9: EBITDA growth trend
    InsightTestScenario(
        scenario_id="ebitda_growth",
        description="EBITDA growing 22% year-over-year",
        trend=Trend(
            metric="ebitda",
            direction=TrendDirection.INCREASING,
            magnitude=22.0,
            confidence=0.88,
            start_date="2023-Q1",
            end_date="2024-Q4",
            description="Strong EBITDA growth indicating operational efficiency",
            cagr=0.22,
            qoq_growth=0.055,
        ),
        expected_category=InsightCategory.OPPORTUNITY,
        expected_priority_range=(1, 2),
        expected_keywords=["ebitda"],
    ),
    # Scenario 10: Headcount cost anomaly
    InsightTestScenario(
        scenario_id="headcount_spike",
        description="Headcount costs increased 35% unexpectedly",
        anomaly=Anomaly(
            date="2024-Q1",
            metric="headcount_costs",
            value=540000.0,
            expected_value=400000.0,
            z_score=2.8,
            severity=AnomalySeverity.CRITICAL,
            reason="Significant headcount cost increase",
            magnitude_pct=35.0,
        ),
        expected_category=InsightCategory.RISK,
        expected_priority_range=(1, 2),
        expected_keywords=["headcount"],
    ),
]
