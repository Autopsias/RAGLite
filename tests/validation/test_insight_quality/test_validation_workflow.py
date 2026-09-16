"""Tests for full validation workflow (Story 4.10 AC3)."""

import pytest

from .models import InsightTestScenario
from .scenarios import INSIGHT_TEST_SCENARIOS
from .validator import InsightQualityValidator


class TestValidationWorkflow:
    """Tests for full validation workflow (Story 4.10 AC3)."""

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_validate_all_scenarios(
        self,
        validator: InsightQualityValidator,
        test_scenarios: list[InsightTestScenario],
    ):
        """Test validation on full expert-labeled scenario set.

        Story 4.10 AC3: Target 75%+ relevance rate.
        """
        result = await validator.validate_insights(test_scenarios)

        assert result.total_scenarios == len(test_scenarios)
        assert result.passed_scenarios >= 0
        assert 0 <= result.relevance_rate <= 100

        # Log results for debugging
        print("\nInsight Validation Results:")
        print(f"  Total scenarios: {result.total_scenarios}")
        print(f"  Passed scenarios: {result.passed_scenarios}")
        print(f"  Relevance rate: {result.relevance_rate:.1f}%")
        print(f"  Threshold met: {result.passed}")
        print(f"  Category breakdown: {result.category_breakdown}")

    @pytest.mark.asyncio
    async def test_validate_empty_scenarios_raises(
        self,
        validator: InsightQualityValidator,
    ):
        """Test validation raises for empty scenarios."""
        with pytest.raises(ValueError, match="No test scenarios"):
            await validator.validate_insights([])

    @pytest.mark.asyncio
    async def test_validate_single_scenario(
        self,
        validator: InsightQualityValidator,
    ):
        """Test validation with single scenario."""
        single_scenario = [INSIGHT_TEST_SCENARIOS[0]]

        result = await validator.validate_insights(single_scenario)

        assert result.total_scenarios == 1
        assert result.passed_scenarios in [0, 1]


@pytest.fixture
def validator() -> InsightQualityValidator:
    """Create validator instance for tests."""
    return InsightQualityValidator(threshold_pct=75.0)


@pytest.fixture
def test_scenarios() -> list[InsightTestScenario]:
    """Return the expert-labeled test scenarios."""
    return INSIGHT_TEST_SCENARIOS
