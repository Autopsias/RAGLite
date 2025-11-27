"""Insights module for anomaly detection, trend analysis, and proactive insights.

Story 4.5: Anomaly detection for financial time-series data.
Story 4.6: Trend analysis and pattern recognition.
Story 4.7: Proactive insight generation.
"""

from raglite.insights.anomalies import detect_anomalies, explain_anomaly
from raglite.insights.proactive import (
    calculate_insight_priority,
    categorize_insight,
    filter_insights,
    generate_insights,
    synthesize_insight,
)
from raglite.insights.trends import (
    analyze_trends,
    calculate_cagr,
    calculate_qoq_growth,
    classify_direction,
    detect_correlation,
    explain_trend,
)

__all__ = [
    # Story 4.5: Anomaly detection
    "detect_anomalies",
    "explain_anomaly",
    # Story 4.6: Trend analysis
    "analyze_trends",
    "calculate_cagr",
    "calculate_qoq_growth",
    "classify_direction",
    "detect_correlation",
    "explain_trend",
    # Story 4.7: Proactive insight generation
    "generate_insights",
    "synthesize_insight",
    "calculate_insight_priority",
    "categorize_insight",
    "filter_insights",
]
