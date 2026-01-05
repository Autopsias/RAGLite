"""Strategic recommendation engine from financial insights.

Story 4.8: Generates actionable recommendations based on financial data analysis.
This module provides a facade for backward compatibility.
"""

# Re-export all public items
# Data models
from raglite.shared.models import (
    Recommendation,
    RecommendationCategory,
    RecommendationResult,
)

# Filtering utilities
from .filtering import filter_recommendations

# Main generation engine
from .generation import generate_recommendations

# Scoring functions
from .scoring import (
    calculate_impact_score,
    categorize_recommendation,
    determine_urgency,
)

# LLM synthesis
from .synthesis import synthesize_recommendation

__all__ = [
    "Recommendation",
    "RecommendationCategory",
    "RecommendationResult",
    "calculate_impact_score",
    "categorize_recommendation",
    "determine_urgency",
    "filter_recommendations",
    "generate_recommendations",
    "synthesize_recommendation",
]
