"""Unit tests for Story 4.7: Insight Models and Enums.

Tests InsightCategory enum and Insight/InsightGenerationResult models.
Split from test_proactive_insights.py as part of Story 8.4a-2.
"""

from datetime import datetime

import pytest

from raglite.shared.models import Insight, InsightCategory, InsightGenerationResult

pytestmark = [pytest.mark.unit]


# =============================================================================
# Test InsightCategory Enum (AC2)
# =============================================================================


class TestInsightCategory:
    """Tests for the InsightCategory enum."""

    def test_category_values(self):
        """Test that InsightCategory has all 5 required values (AC2)."""
        assert InsightCategory.RISK.value == "risk"
        assert InsightCategory.OPPORTUNITY.value == "opportunity"
        assert InsightCategory.ANOMALY.value == "anomaly"
        assert InsightCategory.TREND.value == "trend"
        assert InsightCategory.STRATEGIC_PRIORITY.value == "strategic_priority"

    def test_category_is_string_enum(self):
        """Test that InsightCategory is a string enum."""
        assert isinstance(InsightCategory.RISK, str)
        assert InsightCategory.RISK == "risk"

    def test_all_category_values(self):
        """Test iterating over all category values."""
        categories = list(InsightCategory)
        assert len(categories) == 5
        assert InsightCategory.RISK in categories
        assert InsightCategory.OPPORTUNITY in categories
        assert InsightCategory.ANOMALY in categories
        assert InsightCategory.TREND in categories
        assert InsightCategory.STRATEGIC_PRIORITY in categories


# =============================================================================
# Test Insight Model (AC2, AC3, AC5)
# =============================================================================


class TestInsightModel:
    """Tests for the Insight model."""

    def test_insight_with_all_fields(self):
        """Test creating Insight with all fields populated (AC5)."""
        insight = Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Marketing spend increased 30% with no revenue increase",
            supporting_data={
                "metric": "marketing_spend",
                "value": 2600000,
                "expected_value": 2000000,
                "magnitude_pct": 30.0,
            },
            rationale="Marketing spend deviation of 30% suggests potential inefficiency.",
            sources=["marketing_spend", "revenue"],
            recommended_action="Review marketing ROI and campaign effectiveness.",
            created_at=datetime(2024, 10, 15, 12, 0, 0),
        )

        assert insight.category == InsightCategory.RISK
        assert insight.priority == 1
        assert "Marketing spend" in insight.summary
        assert insight.supporting_data["metric"] == "marketing_spend"
        assert "inefficiency" in insight.rationale.lower()
        assert "marketing_spend" in insight.sources
        assert "ROI" in insight.recommended_action

    def test_insight_default_values(self):
        """Test Insight default values for optional fields."""
        insight = Insight(
            category=InsightCategory.ANOMALY,
            priority=3,
            summary="Revenue anomaly detected",
        )

        assert insight.supporting_data == {}
        assert insight.rationale == ""
        assert insight.sources == []
        assert insight.recommended_action == ""
        assert insight.created_at is not None

    def test_insight_priority_bounds(self):
        """Test that priority is bounded 1-5 (AC3)."""
        insight = Insight(
            category=InsightCategory.TREND,
            priority=5,
            summary="Stable trend observed",
        )
        assert 1 <= insight.priority <= 5

    def test_insight_priority_validation_too_low(self):
        """Test that priority < 1 raises validation error."""
        with pytest.raises(ValueError):
            Insight(
                category=InsightCategory.RISK,
                priority=0,
                summary="Invalid priority",
            )

    def test_insight_priority_validation_too_high(self):
        """Test that priority > 5 raises validation error."""
        with pytest.raises(ValueError):
            Insight(
                category=InsightCategory.RISK,
                priority=6,
                summary="Invalid priority",
            )

    def test_insight_serialization(self):
        """Test that Insight can be serialized to dict."""
        insight = Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Growth opportunity identified",
            supporting_data={"metric": "revenue", "magnitude": 15.2},
        )

        data = insight.model_dump()
        assert data["category"] == "opportunity"
        assert data["priority"] == 2
        assert data["summary"] == "Growth opportunity identified"
        assert data["supporting_data"]["metric"] == "revenue"

    def test_insight_required_fields(self):
        """Test that required fields raise error if missing."""
        with pytest.raises(ValueError):
            Insight(
                category=InsightCategory.RISK,
                # Missing required 'summary' and 'priority'
            )


# =============================================================================
# Test InsightGenerationResult Model (AC1)
# =============================================================================


class TestInsightGenerationResultModel:
    """Tests for the InsightGenerationResult model."""

    def test_result_with_all_fields(self):
        """Test creating InsightGenerationResult with all fields."""
        insights = [
            Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Critical risk detected",
            ),
            Insight(
                category=InsightCategory.OPPORTUNITY,
                priority=3,
                summary="Growth opportunity",
            ),
        ]

        result = InsightGenerationResult(
            insights=insights,
            total_generated=2,
            generation_method="LLM synthesis (Mistral Large)",
            metrics_analyzed=3,
        )

        assert len(result.insights) == 2
        assert result.total_generated == 2
        assert "Mistral Large" in result.generation_method
        assert result.metrics_analyzed == 3

    def test_result_default_values(self):
        """Test InsightGenerationResult default values."""
        result = InsightGenerationResult(
            total_generated=0,
            metrics_analyzed=0,
        )

        assert result.insights == []
        assert "LLM synthesis" in result.generation_method
