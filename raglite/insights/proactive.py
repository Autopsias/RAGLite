"""Proactive insight generation from financial analysis.

Story 4.7: Combines anomaly detection, trend analysis, and contextual reasoning
to generate prioritized actionable insights.

This module is a facade that re-exports the modularized insight generation
functionality from proactive_modules package.
"""

# Re-export all public API from modularized components
from raglite.insights.proactive_modules import (
    calculate_insight_priority,
    categorize_insight,
    filter_insights,
    generate_insights,
    synthesize_insight,
)

__all__ = [
    "calculate_insight_priority",
    "categorize_insight",
    "filter_insights",
    "generate_insights",
    "synthesize_insight",
]
