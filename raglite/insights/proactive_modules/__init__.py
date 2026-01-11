"""Proactive insight generation modules.

This package provides modular components for proactive insight generation:
- helpers: Utility functions for priority, categorization, and filtering
- synthesis: LLM-powered insight synthesis
- generation: Main insight generation orchestration
"""

from .generation import generate_insights
from .helpers import calculate_insight_priority, categorize_insight, filter_insights
from .synthesis import synthesize_insight

__all__ = [
    "calculate_insight_priority",
    "categorize_insight",
    "filter_insights",
    "synthesize_insight",
    "generate_insights",
]
