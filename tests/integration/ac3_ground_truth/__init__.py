"""AC3 Ground Truth Validation Test Suite.

This package contains tests for Story 2.5 acceptance criteria:
- AC1: Full ground truth execution (50 queries)
- AC2: Decision gate validation (≥70% retrieval accuracy)
- AC3: Attribution accuracy validation (≥95% attribution accuracy)
"""

from tests.integration.ac3_ground_truth.models import AccuracyMetrics, QueryValidationResult

__all__ = ["AccuracyMetrics", "QueryValidationResult"]
