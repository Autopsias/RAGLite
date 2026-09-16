"""Pytest fixtures for recommendation alignment tests."""

import pytest

from . import (
    RECOMMENDATION_TEST_SCENARIOS,
    RecommendationAlignmentValidator,
    RecommendationTestScenario,
)


@pytest.fixture
def validator() -> RecommendationAlignmentValidator:
    """Create validator instance for tests."""
    return RecommendationAlignmentValidator(threshold_pct=80.0)


@pytest.fixture
def test_scenarios() -> list[RecommendationTestScenario]:
    """Return the expert-labeled test scenarios."""
    return RECOMMENDATION_TEST_SCENARIOS
