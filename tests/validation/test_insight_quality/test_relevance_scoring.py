"""Tests for relevance scoring logic (Story 4.10 Task 2.3)."""

import pytest

from raglite.shared.models import Insight, InsightCategory

from .models import InsightTestScenario
from .validator import InsightQualityValidator


class TestRelevanceScoring:
    """Tests for relevance scoring logic (Story 4.10 Task 2.3)."""

    def test_is_insight_relevant_all_match(self, validator: InsightQualityValidator):
        """Insight matching all criteria should be relevant."""
        insight = Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Marketing spend shows critical deviation",
            supporting_data={"metric": "marketing_spend", "z_score": 2.5},
            rationale="Based on marketing analysis",
            sources=["marketing_spend"],
        )
        scenario = InsightTestScenario(
            scenario_id="test",
            description="Test scenario",
            expected_category=InsightCategory.RISK,
            expected_priority_range=(1, 2),
            expected_keywords=["marketing"],
        )

        is_relevant, reason = validator._is_insight_relevant(insight, scenario)

        assert is_relevant
        assert reason == "All checks passed"

    def test_is_insight_relevant_category_mismatch(self, validator: InsightQualityValidator):
        """Insight with wrong category should not be relevant."""
        insight = Insight(
            category=InsightCategory.OPPORTUNITY,  # Wrong category
            priority=2,
            summary="Some opportunity",
            supporting_data={"metric": "revenue"},
            rationale="Growth detected",
            sources=["revenue"],
        )
        scenario = InsightTestScenario(
            scenario_id="test",
            description="Test scenario",
            expected_category=InsightCategory.RISK,
            expected_priority_range=(1, 3),
        )

        is_relevant, reason = validator._is_insight_relevant(insight, scenario)

        assert not is_relevant
        assert "Category mismatch" in reason

    def test_is_insight_relevant_priority_out_of_range(self, validator: InsightQualityValidator):
        """Insight with priority outside range should not be relevant."""
        insight = Insight(
            category=InsightCategory.RISK,
            priority=5,  # Too low priority
            summary="Risk detected",
            supporting_data={"metric": "costs"},
            rationale="Cost increase",
            sources=["costs"],
        )
        scenario = InsightTestScenario(
            scenario_id="test",
            description="Test scenario",
            expected_category=InsightCategory.RISK,
            expected_priority_range=(1, 2),  # Expects high priority
        )

        is_relevant, reason = validator._is_insight_relevant(insight, scenario)

        assert not is_relevant
        assert "Priority out of range" in reason


@pytest.fixture
def validator() -> InsightQualityValidator:
    """Create validator instance for tests."""
    return InsightQualityValidator(threshold_pct=75.0)
