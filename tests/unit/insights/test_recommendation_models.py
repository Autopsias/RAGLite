"""Unit tests for strategic recommendation engine.

Story 4.8: Tests for generate_recommendations(), synthesize_recommendation(),
calculate_impact_score(), categorize_recommendation(), filter_recommendations().

Target: 40+ unit tests covering models, functions, edge cases.
"""

from datetime import datetime

import pytest

from raglite.shared.models import (
    Recommendation,
    RecommendationCategory,
    RecommendationResult,
)

pytestmark = [pytest.mark.unit]

# =============================================================================
# Test Data Fixtures
# =============================================================================
# Note: All sample insights are now in conftest.py


# =============================================================================
# RecommendationCategory Enum Tests
# =============================================================================


class TestRecommendationCategoryEnum:
    """Tests for RecommendationCategory enum values."""

    def test_has_cost_reduction(self):
        """AC2: Enum has COST_REDUCTION value."""
        assert RecommendationCategory.COST_REDUCTION == "cost_reduction"

    def test_has_revenue_growth(self):
        """AC2: Enum has REVENUE_GROWTH value."""
        assert RecommendationCategory.REVENUE_GROWTH == "revenue_growth"

    def test_has_risk_mitigation(self):
        """AC2: Enum has RISK_MITIGATION value."""
        assert RecommendationCategory.RISK_MITIGATION == "risk_mitigation"

    def test_has_operational_efficiency(self):
        """AC2: Enum has OPERATIONAL_EFFICIENCY value."""
        assert RecommendationCategory.OPERATIONAL_EFFICIENCY == "operational_efficiency"

    def test_has_strategic_investment(self):
        """AC2: Enum has STRATEGIC_INVESTMENT value."""
        assert RecommendationCategory.STRATEGIC_INVESTMENT == "strategic_investment"

    def test_enum_count(self):
        """AC2: Enum has exactly 5 values."""
        assert len(RecommendationCategory) == 5


# =============================================================================
# Recommendation Model Tests
# =============================================================================


class TestRecommendationModel:
    """Tests for Recommendation Pydantic model."""

    def test_recommendation_has_required_fields(self):
        """AC2/AC3: Recommendation has all required fields."""
        rec = Recommendation(
            category=RecommendationCategory.RISK_MITIGATION,
            impact_score=8,
            title="Test Recommendation",
            description="Test description",
        )
        assert rec.category == RecommendationCategory.RISK_MITIGATION
        assert rec.impact_score == 8
        assert rec.title == "Test Recommendation"
        assert rec.description == "Test description"

    def test_impact_score_range_valid(self):
        """AC2: Impact score accepts values 1-10."""
        for score in [1, 5, 10]:
            rec = Recommendation(
                category=RecommendationCategory.COST_REDUCTION,
                impact_score=score,
                title="Test",
                description="Test",
            )
            assert rec.impact_score == score

    def test_impact_score_below_minimum_fails(self):
        """AC2: Impact score rejects values < 1."""
        with pytest.raises(ValueError):
            Recommendation(
                category=RecommendationCategory.COST_REDUCTION,
                impact_score=0,
                title="Test",
                description="Test",
            )

    def test_impact_score_above_maximum_fails(self):
        """AC2: Impact score rejects values > 10."""
        with pytest.raises(ValueError):
            Recommendation(
                category=RecommendationCategory.COST_REDUCTION,
                impact_score=11,
                title="Test",
                description="Test",
            )

    def test_recommendation_has_rationale_field(self):
        """AC3: Recommendation has rationale field."""
        rec = Recommendation(
            category=RecommendationCategory.RISK_MITIGATION,
            impact_score=7,
            title="Test",
            description="Test",
            rationale="This matters because of X",
        )
        assert rec.rationale == "This matters because of X"

    def test_recommendation_has_supporting_evidence_field(self):
        """AC3: Recommendation has supporting_evidence dict field."""
        rec = Recommendation(
            category=RecommendationCategory.RISK_MITIGATION,
            impact_score=7,
            title="Test",
            description="Test",
            supporting_evidence={"metric": "revenue", "value": 1000000},
        )
        assert rec.supporting_evidence == {"metric": "revenue", "value": 1000000}

    def test_recommendation_has_action_steps_field(self):
        """AC3: Recommendation has action_steps list field."""
        rec = Recommendation(
            category=RecommendationCategory.COST_REDUCTION,
            impact_score=6,
            title="Test",
            description="Test",
            action_steps=["Step 1", "Step 2", "Step 3"],
        )
        assert len(rec.action_steps) == 3
        assert rec.action_steps[0] == "Step 1"

    def test_recommendation_has_urgency_field(self):
        """AC3: Recommendation has urgency field."""
        rec = Recommendation(
            category=RecommendationCategory.RISK_MITIGATION,
            impact_score=9,
            title="Test",
            description="Test",
            urgency="high",
        )
        assert rec.urgency == "high"

    def test_recommendation_has_sources_field(self):
        """AC3: Recommendation has sources list field."""
        rec = Recommendation(
            category=RecommendationCategory.REVENUE_GROWTH,
            impact_score=7,
            title="Test",
            description="Test",
            sources=["revenue", "sales"],
        )
        assert rec.sources == ["revenue", "sales"]

    def test_recommendation_has_created_at_field(self):
        """AC3: Recommendation has created_at timestamp field."""
        rec = Recommendation(
            category=RecommendationCategory.OPERATIONAL_EFFICIENCY,
            impact_score=5,
            title="Test",
            description="Test",
        )
        assert rec.created_at is not None
        assert isinstance(rec.created_at, datetime)

    def test_recommendation_json_serialization(self):
        """AC3: Recommendation can be serialized to JSON."""
        rec = Recommendation(
            category=RecommendationCategory.STRATEGIC_INVESTMENT,
            impact_score=8,
            title="Test",
            description="Test",
            supporting_evidence={"key": "value"},
            action_steps=["Action 1"],
        )
        json_data = rec.model_dump_json()
        assert "strategic_investment" in json_data
        assert "impact_score" in json_data


# =============================================================================
# RecommendationResult Model Tests
# =============================================================================


class TestRecommendationResultModel:
    """Tests for RecommendationResult Pydantic model."""

    def test_result_has_recommendations_list(self):
        """AC1: RecommendationResult has recommendations list."""
        result = RecommendationResult(
            recommendations=[],
            total_generated=0,
            insights_analyzed=0,
        )
        assert result.recommendations == []

    def test_result_has_total_generated(self):
        """AC1: RecommendationResult has total_generated field."""
        result = RecommendationResult(
            recommendations=[],
            total_generated=5,
            insights_analyzed=5,
        )
        assert result.total_generated == 5

    def test_result_has_generation_method(self):
        """AC1: RecommendationResult has generation_method field."""
        result = RecommendationResult(
            recommendations=[],
            total_generated=0,
            insights_analyzed=0,
        )
        assert "Mistral" in result.generation_method

    def test_result_has_insights_analyzed(self):
        """AC1: RecommendationResult has insights_analyzed field."""
        result = RecommendationResult(
            recommendations=[],
            total_generated=3,
            insights_analyzed=3,
        )
        assert result.insights_analyzed == 3


# =============================================================================
# calculate_impact_score() Tests
# =============================================================================
