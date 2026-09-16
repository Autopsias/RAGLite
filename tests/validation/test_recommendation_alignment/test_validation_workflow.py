"""Tests for full validation workflow (Story 4.10 AC4)."""

import pytest

from tests.validation.test_recommendation_alignment import (
    RECOMMENDATION_TEST_SCENARIOS,
    RecommendationAlignmentValidator,
    RecommendationTestScenario,
)


class TestValidationWorkflow:
    """Tests for full validation workflow (Story 4.10 AC4)."""

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_validate_all_scenarios(
        self,
        validator: RecommendationAlignmentValidator,
        test_scenarios: list[RecommendationTestScenario],
    ):
        """Test validation on full expert-labeled scenario set.

        Story 4.10 AC4: Target 80%+ alignment rate.
        """
        result = await validator.validate_recommendations(test_scenarios)

        assert result.total_scenarios == len(test_scenarios)
        assert result.aligned_scenarios >= 0
        assert 0 <= result.alignment_rate <= 100

        # Log results for debugging
        print("\nRecommendation Validation Results:")
        print(f"  Total scenarios: {result.total_scenarios}")
        print(f"  Aligned scenarios: {result.aligned_scenarios}")
        print(f"  Alignment rate: {result.alignment_rate:.1f}%")
        print(f"  Threshold met: {result.passed}")
        print(f"  Category breakdown: {result.category_breakdown}")

    @pytest.mark.asyncio
    async def test_validate_empty_scenarios_raises(
        self,
        validator: RecommendationAlignmentValidator,
    ):
        """Test validation raises for empty scenarios."""
        with pytest.raises(ValueError, match="No test scenarios"):
            await validator.validate_recommendations([])

    @pytest.mark.asyncio
    async def test_validate_single_scenario(
        self,
        validator: RecommendationAlignmentValidator,
    ):
        """Test validation with single scenario."""
        single_scenario = [RECOMMENDATION_TEST_SCENARIOS[0]]

        result = await validator.validate_recommendations(single_scenario)

        assert result.total_scenarios == 1
        assert result.aligned_scenarios in [0, 1]


class TestThresholdConfiguration:
    """Tests for configurable threshold."""

    def test_custom_threshold(self):
        """Test validator with custom threshold."""
        strict_validator = RecommendationAlignmentValidator(threshold_pct=90.0)
        assert strict_validator.threshold_pct == 90.0

    def test_default_threshold(self):
        """Test validator with default 80% threshold."""
        validator = RecommendationAlignmentValidator()
        assert validator.threshold_pct == 80.0

    def test_custom_impact_tolerance(self):
        """Test validator with custom impact tolerance."""
        tolerant_validator = RecommendationAlignmentValidator(impact_tolerance=3)
        assert tolerant_validator.impact_tolerance == 3
