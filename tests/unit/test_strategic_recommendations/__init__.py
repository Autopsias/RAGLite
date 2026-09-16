"""Test suite for strategic recommendation engine.

This package contains tests for the recommendation generation system:
- Models: RecommendationCategory enum, Recommendation, RecommendationResult
- Functions: calculate_impact_score, categorize_recommendation, filter_recommendations
- Generation: generate_recommendations, synthesize_recommendation

Facade for backward compatibility - re-exports all test classes from submodules.
"""

# Import from split modules (not _legacy)
from .test_generation import TestGenerateRecommendations
from .test_generation_edge_cases import TestEdgeCases, TestStructuredLogging
from .test_recommendation_functions import (
    TestCalculateImpactScore,
    TestCategorizeRecommendation,
    TestDetermineUrgency,
    TestFilterRecommendations,
)
from .test_recommendation_models import (
    TestRecommendationCategoryEnum,
    TestRecommendationModel,
    TestRecommendationResultModel,
)
from .test_synthesis import TestSynthesizeRecommendation

# Explicit public API
__all__ = [
    # Fixtures (imported by pytest from conftest or module)
    "sample_risk_insight",
    "sample_opportunity_insight",
    "sample_anomaly_insight",
    "sample_trend_insight",
    "sample_strategic_priority_insight",
    "cost_opportunity_insight",
    # Test Classes - Model Tests
    "TestRecommendationCategoryEnum",
    "TestRecommendationModel",
    "TestRecommendationResultModel",
    # Test Classes - Function Tests
    "TestCalculateImpactScore",
    "TestCategorizeRecommendation",
    "TestDetermineUrgency",
    "TestFilterRecommendations",
    # Test Classes - Generation Tests
    "TestSynthesizeRecommendation",
    "TestGenerateRecommendations",
    "TestEdgeCases",
    "TestStructuredLogging",
]
