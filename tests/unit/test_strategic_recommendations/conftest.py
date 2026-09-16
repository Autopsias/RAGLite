"""Pytest configuration for strategic recommendation tests.

Imports shared fixtures from test_recommendations_fixtures.py.
"""

from .test_recommendations_fixtures import (
    cost_opportunity_insight,
    sample_anomaly_insight,
    sample_opportunity_insight,
    sample_risk_insight,
    sample_strategic_priority_insight,
    sample_trend_insight,
)

__all__ = [
    "sample_risk_insight",
    "sample_opportunity_insight",
    "sample_anomaly_insight",
    "sample_trend_insight",
    "sample_strategic_priority_insight",
    "cost_opportunity_insight",
]
