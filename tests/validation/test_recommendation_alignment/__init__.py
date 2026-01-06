"""Recommendation alignment validation framework.

Story 4.10 AC4: Validates recommendation alignment with expert analysis.
Target: 80%+ alignment rate with expert-labeled ground truth.

This module provides backward compatibility facade for test files that import
from the original test_recommendation_alignment.py module.
"""

# Re-export all public API for backward compatibility
from .models import (
    RecommendationTestScenario,
    RecommendationValidationResult,
)
from .scenarios import RECOMMENDATION_TEST_SCENARIOS
from .validator import RecommendationAlignmentValidator

__all__ = [
    "RecommendationAlignmentValidator",
    "RecommendationTestScenario",
    "RecommendationValidationResult",
    "RECOMMENDATION_TEST_SCENARIOS",
]
