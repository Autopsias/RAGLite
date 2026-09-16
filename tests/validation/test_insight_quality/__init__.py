"""Insight quality validation framework.

Story 4.10 AC3: Validates insight relevance using expert-labeled test scenarios.
Target: 75%+ insights rated useful/actionable.

This package tests insight quality validation through:
- Test scenario data models
- Validation workflow logic
- Relevance scoring tests
- Categorization and priority tests
"""

# Export models and scenarios for backward compatibility
from .models import InsightTestScenario, InsightValidationResult
from .scenarios import INSIGHT_TEST_SCENARIOS

# Export all test classes for backward compatibility
from .test_categorization import TestInsightCategorization
from .test_priority import TestPriorityCalculation
from .test_relevance_scoring import TestRelevanceScoring
from .test_threshold import TestThresholdConfiguration
from .test_validation_workflow import TestValidationWorkflow
from .validator import InsightQualityValidator

__all__ = [
    "InsightTestScenario",
    "InsightValidationResult",
    "INSIGHT_TEST_SCENARIOS",
    "InsightQualityValidator",
    "TestInsightCategorization",
    "TestPriorityCalculation",
    "TestRelevanceScoring",
    "TestThresholdConfiguration",
    "TestValidationWorkflow",
]
