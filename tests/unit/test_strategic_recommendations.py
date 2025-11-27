"""Unit tests for strategic recommendation engine.

Story 4.8: Tests for generate_recommendations(), synthesize_recommendation(),
calculate_impact_score(), categorize_recommendation(), filter_recommendations().

Target: 40+ unit tests covering models, functions, edge cases.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import (
    Insight,
    InsightCategory,
    Recommendation,
    RecommendationCategory,
    RecommendationResult,
)

# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_risk_insight() -> Insight:
    """Create a sample RISK insight (priority 1)."""
    return Insight(
        category=InsightCategory.RISK,
        priority=1,
        summary="Marketing spend increased 30% YoY with no revenue increase",
        supporting_data={
            "marketing_spend_yoy_change": 0.30,
            "revenue_yoy_change": 0.02,
            "metric": "marketing_spend",
        },
        rationale="Potential marketing inefficiency detected",
        sources=["marketing_spend", "revenue"],
        recommended_action="Review marketing ROI",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_opportunity_insight() -> Insight:
    """Create a sample OPPORTUNITY insight (priority 2)."""
    return Insight(
        category=InsightCategory.OPPORTUNITY,
        priority=2,
        summary="Revenue growth trending 15% above forecast",
        supporting_data={
            "revenue_growth": 0.15,
            "forecast_variance": 0.15,
            "metric": "revenue",
        },
        rationale="Strong sales performance in Q3",
        sources=["revenue"],
        recommended_action="Accelerate growth initiatives",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_anomaly_insight() -> Insight:
    """Create a sample ANOMALY insight (priority 3)."""
    return Insight(
        category=InsightCategory.ANOMALY,
        priority=3,
        summary="Unusual spike in cloud costs detected",
        supporting_data={
            "cloud_costs": 3000000,
            "expected_costs": 2000000,
            "z_score": 2.5,
        },
        rationale="Cloud costs 50% above baseline",
        sources=["cloud_costs"],
        recommended_action="Investigate cloud usage",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_trend_insight() -> Insight:
    """Create a sample TREND insight (priority 4)."""
    return Insight(
        category=InsightCategory.TREND,
        priority=4,
        summary="Operating expenses showing stable pattern",
        supporting_data={
            "metric": "operating_expenses",
            "direction": "stable",
            "magnitude": 2.5,
        },
        rationale="Expenses remain within budget",
        sources=["operating_expenses"],
        recommended_action="Continue monitoring",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_strategic_priority_insight() -> Insight:
    """Create a sample STRATEGIC_PRIORITY insight (priority 2)."""
    return Insight(
        category=InsightCategory.STRATEGIC_PRIORITY,
        priority=2,
        summary="Capital expenditure planning needed for next fiscal year",
        supporting_data={
            "capex_budget": 10000000,
            "utilization_rate": 0.85,
        },
        rationale="Current assets nearing capacity",
        sources=["capex", "utilization"],
        recommended_action="Initiate capex planning",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def cost_opportunity_insight() -> Insight:
    """Create an OPPORTUNITY insight about cost reduction."""
    return Insight(
        category=InsightCategory.OPPORTUNITY,
        priority=2,
        summary="Cloud infrastructure costs trending 40% under budget",
        supporting_data={
            "cloud_budget": 5000000,
            "cloud_actual": 3000000,
            "cost_savings": 2000000,
        },
        rationale="Significant cost savings opportunity",
        sources=["cloud_costs"],
        recommended_action="Reallocate budget savings",
        created_at=datetime.now(UTC),
    )


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


class TestCalculateImpactScore:
    """Tests for calculate_impact_score() function."""

    def test_critical_risk_insight_high_impact(self, sample_risk_insight: Insight):
        """AC2: Critical RISK insight (priority 1) gets high impact score."""
        from raglite.insights.recommendations import calculate_impact_score

        score = calculate_impact_score(sample_risk_insight)
        # Priority 1 -> base 9, RISK boost +2 = 10 (capped)
        assert score == 10

    def test_opportunity_insight_medium_impact(self, sample_opportunity_insight: Insight):
        """AC2: OPPORTUNITY insight (priority 2) gets boosted impact."""
        from raglite.insights.recommendations import calculate_impact_score

        score = calculate_impact_score(sample_opportunity_insight)
        # Priority 2 -> base 7, OPPORTUNITY boost +1 = 8
        assert score == 8

    def test_anomaly_insight_medium_impact(self, sample_anomaly_insight: Insight):
        """AC2: ANOMALY insight (priority 3) gets medium impact."""
        from raglite.insights.recommendations import calculate_impact_score

        score = calculate_impact_score(sample_anomaly_insight)
        # Priority 3 -> base 5, no category boost = 5
        assert score == 5

    def test_trend_insight_lower_impact(self, sample_trend_insight: Insight):
        """AC2: TREND insight (priority 4) gets lower impact."""
        from raglite.insights.recommendations import calculate_impact_score

        score = calculate_impact_score(sample_trend_insight)
        # Priority 4 -> base 3, no category boost = 3
        assert score == 3

    def test_strategic_priority_insight_boosted(self, sample_strategic_priority_insight: Insight):
        """AC2: STRATEGIC_PRIORITY insight gets +1 boost."""
        from raglite.insights.recommendations import calculate_impact_score

        score = calculate_impact_score(sample_strategic_priority_insight)
        # Priority 2 -> base 7, STRATEGIC_PRIORITY boost +1 = 8
        assert score == 8

    def test_priority_5_minimum_score(self):
        """AC2: Priority 5 insight gets minimum impact score."""
        from raglite.insights.recommendations import calculate_impact_score

        insight = Insight(
            category=InsightCategory.TREND,
            priority=5,
            summary="Low priority trend",
            created_at=datetime.now(UTC),
        )
        score = calculate_impact_score(insight)
        # Priority 5 -> 11 - 10 = 1
        assert score == 1


# =============================================================================
# categorize_recommendation() Tests
# =============================================================================


class TestCategorizeRecommendation:
    """Tests for categorize_recommendation() function."""

    def test_risk_insight_to_risk_mitigation(self, sample_risk_insight: Insight):
        """AC1: RISK insight maps to RISK_MITIGATION."""
        from raglite.insights.recommendations import categorize_recommendation

        category = categorize_recommendation(sample_risk_insight)
        assert category == RecommendationCategory.RISK_MITIGATION

    def test_opportunity_insight_to_revenue_growth(self, sample_opportunity_insight: Insight):
        """AC1: OPPORTUNITY insight maps to REVENUE_GROWTH."""
        from raglite.insights.recommendations import categorize_recommendation

        category = categorize_recommendation(sample_opportunity_insight)
        assert category == RecommendationCategory.REVENUE_GROWTH

    def test_opportunity_with_cost_to_cost_reduction(self, cost_opportunity_insight: Insight):
        """AC1: OPPORTUNITY insight with 'cost' keyword maps to COST_REDUCTION."""
        from raglite.insights.recommendations import categorize_recommendation

        category = categorize_recommendation(cost_opportunity_insight)
        assert category == RecommendationCategory.COST_REDUCTION

    def test_anomaly_insight_to_operational_efficiency(self, sample_anomaly_insight: Insight):
        """AC1: ANOMALY insight maps to OPERATIONAL_EFFICIENCY."""
        from raglite.insights.recommendations import categorize_recommendation

        category = categorize_recommendation(sample_anomaly_insight)
        assert category == RecommendationCategory.OPERATIONAL_EFFICIENCY

    def test_trend_insight_to_operational_efficiency(self, sample_trend_insight: Insight):
        """AC1: TREND insight maps to OPERATIONAL_EFFICIENCY."""
        from raglite.insights.recommendations import categorize_recommendation

        category = categorize_recommendation(sample_trend_insight)
        assert category == RecommendationCategory.OPERATIONAL_EFFICIENCY

    def test_strategic_priority_to_strategic_investment(
        self, sample_strategic_priority_insight: Insight
    ):
        """AC1: STRATEGIC_PRIORITY insight maps to STRATEGIC_INVESTMENT."""
        from raglite.insights.recommendations import categorize_recommendation

        category = categorize_recommendation(sample_strategic_priority_insight)
        assert category == RecommendationCategory.STRATEGIC_INVESTMENT


# =============================================================================
# determine_urgency() Tests
# =============================================================================


class TestDetermineUrgency:
    """Tests for determine_urgency() function."""

    def test_priority_1_is_high_urgency(self, sample_risk_insight: Insight):
        """Priority 1 insight results in high urgency."""
        from raglite.insights.recommendations import determine_urgency

        urgency = determine_urgency(sample_risk_insight, impact_score=10)
        assert urgency == "high"

    def test_high_impact_is_high_urgency(self, sample_opportunity_insight: Insight):
        """Impact score >= 8 results in high urgency."""
        from raglite.insights.recommendations import determine_urgency

        urgency = determine_urgency(sample_opportunity_insight, impact_score=8)
        assert urgency == "high"

    def test_low_priority_low_impact_is_low_urgency(self):
        """Priority >= 4 with impact <= 4 results in low urgency."""
        from raglite.insights.recommendations import determine_urgency

        insight = Insight(
            category=InsightCategory.TREND,
            priority=4,
            summary="Low priority",
            created_at=datetime.now(UTC),
        )
        urgency = determine_urgency(insight, impact_score=3)
        assert urgency == "low"

    def test_medium_priority_medium_impact_is_medium_urgency(self, sample_anomaly_insight: Insight):
        """Medium priority and impact results in medium urgency."""
        from raglite.insights.recommendations import determine_urgency

        urgency = determine_urgency(sample_anomaly_insight, impact_score=5)
        assert urgency == "medium"


# =============================================================================
# filter_recommendations() Tests
# =============================================================================


class TestFilterRecommendations:
    """Tests for filter_recommendations() function."""

    @pytest.fixture
    def sample_recommendations(self) -> list[Recommendation]:
        """Create a sample list of recommendations for filtering."""
        return [
            Recommendation(
                category=RecommendationCategory.RISK_MITIGATION,
                impact_score=9,
                title="Risk 1",
                description="High impact risk",
            ),
            Recommendation(
                category=RecommendationCategory.COST_REDUCTION,
                impact_score=7,
                title="Cost 1",
                description="Medium impact cost",
            ),
            Recommendation(
                category=RecommendationCategory.REVENUE_GROWTH,
                impact_score=6,
                title="Revenue 1",
                description="Medium impact revenue",
            ),
            Recommendation(
                category=RecommendationCategory.RISK_MITIGATION,
                impact_score=4,
                title="Risk 2",
                description="Low impact risk",
            ),
            Recommendation(
                category=RecommendationCategory.OPERATIONAL_EFFICIENCY,
                impact_score=3,
                title="Ops 1",
                description="Low impact ops",
            ),
        ]

    def test_filter_by_category(self, sample_recommendations: list[Recommendation]):
        """Filter recommendations by category."""
        from raglite.insights.recommendations import filter_recommendations

        filtered = filter_recommendations(
            sample_recommendations,
            category=RecommendationCategory.RISK_MITIGATION,
        )
        assert len(filtered) == 2
        assert all(r.category == RecommendationCategory.RISK_MITIGATION for r in filtered)

    def test_filter_by_min_impact(self, sample_recommendations: list[Recommendation]):
        """Filter recommendations by minimum impact score."""
        from raglite.insights.recommendations import filter_recommendations

        filtered = filter_recommendations(
            sample_recommendations,
            min_impact=7,
        )
        assert len(filtered) == 2
        assert all(r.impact_score >= 7 for r in filtered)

    def test_filter_by_limit(self, sample_recommendations: list[Recommendation]):
        """Filter recommendations by count limit."""
        from raglite.insights.recommendations import filter_recommendations

        filtered = filter_recommendations(
            sample_recommendations,
            limit=3,
        )
        assert len(filtered) == 3

    def test_filter_combined(self, sample_recommendations: list[Recommendation]):
        """Filter with multiple criteria."""
        from raglite.insights.recommendations import filter_recommendations

        filtered = filter_recommendations(
            sample_recommendations,
            category=RecommendationCategory.RISK_MITIGATION,
            min_impact=5,
            limit=1,
        )
        assert len(filtered) == 1
        assert filtered[0].impact_score == 9

    def test_filter_no_criteria_returns_all(self, sample_recommendations: list[Recommendation]):
        """Filter with no criteria returns all recommendations."""
        from raglite.insights.recommendations import filter_recommendations

        filtered = filter_recommendations(sample_recommendations)
        assert len(filtered) == 5


# =============================================================================
# synthesize_recommendation() Tests
# =============================================================================


class TestSynthesizeRecommendation:
    """Tests for synthesize_recommendation() with mocked Mistral client."""

    @pytest.fixture
    def mock_mistral_response(self):
        """Create a mock Mistral response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """TITLE: Optimize Marketing ROI
DESCRIPTION: Review and optimize marketing spend allocation to improve return on investment.
RATIONALE: Marketing efficiency has declined significantly, requiring immediate attention to prevent further resource waste.
ACTIONS:
1. Conduct marketing channel audit
2. Implement ROI tracking for all campaigns
3. Reallocate budget to high-performing channels
4. Set quarterly review checkpoints"""
        return mock_response

    @pytest.mark.asyncio
    async def test_synthesize_returns_title(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC3: synthesize_recommendation returns title."""
        from raglite.insights.recommendations import synthesize_recommendation

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            title, _, _, _ = await synthesize_recommendation(
                sample_risk_insight, RecommendationCategory.RISK_MITIGATION
            )
            assert "Marketing" in title or "ROI" in title

    @pytest.mark.asyncio
    async def test_synthesize_returns_description(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC3: synthesize_recommendation returns description."""
        from raglite.insights.recommendations import synthesize_recommendation

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            _, description, _, _ = await synthesize_recommendation(
                sample_risk_insight, RecommendationCategory.RISK_MITIGATION
            )
            assert len(description) > 0

    @pytest.mark.asyncio
    async def test_synthesize_returns_rationale(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC3: synthesize_recommendation returns rationale."""
        from raglite.insights.recommendations import synthesize_recommendation

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            _, _, rationale, _ = await synthesize_recommendation(
                sample_risk_insight, RecommendationCategory.RISK_MITIGATION
            )
            assert len(rationale) > 0

    @pytest.mark.asyncio
    async def test_synthesize_returns_action_steps(
        self, sample_risk_insight: Insight, mock_mistral_response
    ):
        """AC3: synthesize_recommendation returns action_steps list."""
        from raglite.insights.recommendations import synthesize_recommendation

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_response
            _, _, _, actions = await synthesize_recommendation(
                sample_risk_insight, RecommendationCategory.RISK_MITIGATION
            )
            assert len(actions) >= 3

    @pytest.mark.asyncio
    async def test_synthesize_fallback_on_llm_failure(self, sample_risk_insight: Insight):
        """AC3: synthesize_recommendation provides fallback on LLM failure."""
        from raglite.insights.recommendations import synthesize_recommendation

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.side_effect = Exception("LLM error")
            title, description, rationale, actions = await synthesize_recommendation(
                sample_risk_insight, RecommendationCategory.RISK_MITIGATION
            )
            # Should return fallback values
            assert "Recommendation" in title
            assert len(description) > 0
            assert len(actions) >= 3


# =============================================================================
# generate_recommendations() Tests
# =============================================================================


class TestGenerateRecommendations:
    """Tests for generate_recommendations() main function."""

    @pytest.fixture
    def mock_mistral_for_generation(self):
        """Create mock for Mistral during generation."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """TITLE: Test Recommendation
DESCRIPTION: Test description for the recommendation.
RATIONALE: Test rationale explaining importance.
ACTIONS:
1. Action step one
2. Action step two
3. Action step three"""
        return mock_response

    @pytest.mark.asyncio
    async def test_generate_returns_recommendation_result(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """AC1: generate_recommendations returns RecommendationResult."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations([sample_risk_insight])
            assert isinstance(result, RecommendationResult)

    @pytest.mark.asyncio
    async def test_generate_returns_recommendations_list(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """AC1: generate_recommendations returns list of Recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations([sample_risk_insight])
            assert len(result.recommendations) >= 1
            assert isinstance(result.recommendations[0], Recommendation)

    @pytest.mark.asyncio
    async def test_generate_sorted_by_impact_descending(
        self,
        sample_risk_insight: Insight,
        sample_trend_insight: Insight,
        mock_mistral_for_generation,
    ):
        """AC2: Results sorted by impact_score descending."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations(
                [sample_trend_insight, sample_risk_insight]  # Trend first, Risk second
            )
            # Should be sorted: Risk (high impact) before Trend (low impact)
            scores = [r.impact_score for r in result.recommendations]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_generate_empty_insights_raises_error(self):
        """AC1: Empty insights list raises ValueError."""
        from raglite.insights.recommendations import generate_recommendations

        with pytest.raises(ValueError, match="No insights"):
            await generate_recommendations([])

    @pytest.mark.asyncio
    async def test_generate_single_insight(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """Edge case: Single insight generates one recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations([sample_risk_insight])
            assert result.total_generated == 1
            assert result.insights_analyzed == 1

    @pytest.mark.asyncio
    async def test_generate_deduplication(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """Edge case: Duplicate insights are deduplicated."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            # Same insight twice
            result = await generate_recommendations([sample_risk_insight, sample_risk_insight])
            # Should only generate one recommendation
            assert result.total_generated == 1

    @pytest.mark.asyncio
    async def test_generate_without_synthesis(self, sample_risk_insight: Insight):
        """Edge case: auto_synthesize=False skips LLM."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations([sample_risk_insight], auto_synthesize=False)
        assert result.generation_method == "Rule-based"
        assert len(result.recommendations) == 1

    @pytest.mark.asyncio
    async def test_generate_multiple_insights(
        self,
        sample_risk_insight: Insight,
        sample_opportunity_insight: Insight,
        sample_anomaly_insight: Insight,
        mock_mistral_for_generation,
    ):
        """AC1: Multiple insights generate multiple recommendations."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations(
                [sample_risk_insight, sample_opportunity_insight, sample_anomaly_insight]
            )
            assert result.total_generated == 3
            assert result.insights_analyzed == 3

    @pytest.mark.asyncio
    async def test_generate_preserves_supporting_evidence(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """AC3: Supporting evidence from insight is preserved."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations([sample_risk_insight])
            rec = result.recommendations[0]
            assert rec.supporting_evidence == sample_risk_insight.supporting_data

    @pytest.mark.asyncio
    async def test_generate_preserves_sources(
        self, sample_risk_insight: Insight, mock_mistral_for_generation
    ):
        """AC3: Sources from insight are preserved."""
        from raglite.insights.recommendations import generate_recommendations

        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_mistral_for_generation
            result = await generate_recommendations([sample_risk_insight])
            rec = result.recommendations[0]
            assert rec.sources == sample_risk_insight.sources


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Edge case tests for recommendation generation."""

    @pytest.mark.asyncio
    async def test_insight_with_empty_supporting_data(self):
        """Edge case: Insight with empty supporting_data."""
        from raglite.insights.recommendations import generate_recommendations

        insight = Insight(
            category=InsightCategory.TREND,
            priority=3,
            summary="Test insight",
            supporting_data={},
            created_at=datetime.now(UTC),
        )
        result = await generate_recommendations([insight], auto_synthesize=False)
        assert len(result.recommendations) == 1
        assert result.recommendations[0].supporting_evidence == {}

    @pytest.mark.asyncio
    async def test_insight_with_empty_sources(self):
        """Edge case: Insight with empty sources list."""
        from raglite.insights.recommendations import generate_recommendations

        insight = Insight(
            category=InsightCategory.ANOMALY,
            priority=2,
            summary="Test anomaly",
            sources=[],
            created_at=datetime.now(UTC),
        )
        result = await generate_recommendations([insight], auto_synthesize=False)
        assert len(result.recommendations) == 1
        assert result.recommendations[0].sources == []

    @pytest.mark.asyncio
    async def test_all_categories_generate_recommendations(self):
        """All InsightCategory values generate valid recommendations."""
        from raglite.insights.recommendations import generate_recommendations

        insights = [
            Insight(
                category=cat,
                priority=2,
                summary=f"Test {cat.value}",
                created_at=datetime.now(UTC),
            )
            for cat in InsightCategory
        ]
        result = await generate_recommendations(insights, auto_synthesize=False)
        assert result.total_generated == len(InsightCategory)


# =============================================================================
# Structured Logging Tests
# =============================================================================


class TestStructuredLogging:
    """Tests for structured logging output."""

    @pytest.mark.asyncio
    async def test_generate_logs_start(self, sample_risk_insight: Insight, caplog):
        """Logging: generate_recommendations logs start message."""
        import logging

        from raglite.insights.recommendations import generate_recommendations

        with caplog.at_level(logging.INFO):
            await generate_recommendations([sample_risk_insight], auto_synthesize=False)
        assert "Starting recommendation generation" in caplog.text

    @pytest.mark.asyncio
    async def test_generate_logs_completion(self, sample_risk_insight: Insight, caplog):
        """Logging: generate_recommendations logs completion message."""
        import logging

        from raglite.insights.recommendations import generate_recommendations

        with caplog.at_level(logging.INFO):
            await generate_recommendations([sample_risk_insight], auto_synthesize=False)
        assert "Recommendation generation complete" in caplog.text
