"""Integration tests for strategic recommendation engine.

Story 4.8 AC4/AC5: End-to-end tests with expert-labeled data and cloud cost example.

Target: 80%+ alignment with expert analysis.
"""

import time
from datetime import UTC, datetime

import pytest

from raglite.shared.models import (
    Insight,
    InsightCategory,
    RecommendationCategory,
    RecommendationResult,
)

# Mark all tests as preserve_collection - these are read-only tests
# that don't modify the Qdrant collection (performance optimization)
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]

# =============================================================================
# Expert-Labeled Test Scenarios
# =============================================================================

# These scenarios define expected recommendations based on expert analysis.
# The test validates that the system produces recommendations that align
# with expert expectations >= 80% of the time.

EXPERT_LABELED_SCENARIOS = {
    "cloud_cost_over_budget": {
        "insight": Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Cloud infrastructure costs trending 40% over budget with minimal usage increase",
            supporting_data={
                "cloud_budget": 5000000,
                "cloud_actual": 7000000,
                "budget_variance": 0.40,
                "usage_increase": 0.05,
            },
            rationale="Cloud spending has significantly exceeded budget without corresponding usage increase",
            sources=["cloud_costs", "infrastructure_budget"],
            recommended_action="Focus on reducing cloud infrastructure costs",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.RISK_MITIGATION,
        "expected_impact_min": 8,
        "expected_urgency": "high",
        "expected_title_keywords": ["cloud", "cost", "infrastructure", "reduce"],
    },
    "marketing_inefficiency_risk": {
        "insight": Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Marketing spend increased 30% YoY with no corresponding revenue increase",
            supporting_data={
                "marketing_spend_yoy_change": 0.30,
                "revenue_yoy_change": 0.02,
            },
            rationale="Marketing ROI has declined significantly",
            sources=["marketing_spend", "revenue"],
            recommended_action="Review marketing channel effectiveness",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.RISK_MITIGATION,
        "expected_impact_min": 8,
        "expected_urgency": "high",
        "expected_title_keywords": ["marketing", "roi", "efficiency"],
    },
    "revenue_growth_opportunity": {
        "insight": Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Revenue growth trending 25% above forecast in emerging markets",
            supporting_data={
                "revenue_growth": 0.25,
                "forecast_variance": 0.25,
                "market": "emerging",
            },
            rationale="Strong market expansion opportunity",
            sources=["revenue", "market_analysis"],
            recommended_action="Accelerate emerging market investment",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.REVENUE_GROWTH,
        "expected_impact_min": 6,
        "expected_urgency_in": ["high", "medium"],
        "expected_title_keywords": ["revenue", "growth", "market", "expand"],
    },
    "cost_savings_opportunity": {
        "insight": Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Vendor consolidation could reduce procurement costs by 20%",
            supporting_data={
                "cost_savings_potential": 0.20,
                "vendor_count": 45,
                "category": "procurement",
            },
            rationale="Opportunity to reduce expenses through vendor consolidation",
            sources=["procurement_costs", "vendor_analysis"],
            recommended_action="Initiate vendor consolidation program",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.COST_REDUCTION,
        "expected_impact_min": 6,
        "expected_title_keywords": ["cost", "vendor", "consolidat", "procure"],
    },
    "operational_anomaly": {
        "insight": Insight(
            category=InsightCategory.ANOMALY,
            priority=3,
            summary="Unusual spike in overtime hours across production departments",
            supporting_data={
                "overtime_hours": 15000,
                "baseline_hours": 8000,
                "z_score": 2.8,
            },
            rationale="Production capacity may be constrained",
            sources=["hr_data", "production_metrics"],
            recommended_action="Investigate production capacity constraints",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.OPERATIONAL_EFFICIENCY,
        "expected_impact_min": 4,
        "expected_title_keywords": ["operation", "production", "capacity", "overtime"],
    },
    "strategic_investment_needed": {
        "insight": Insight(
            category=InsightCategory.STRATEGIC_PRIORITY,
            priority=2,
            summary="Capital expenditure planning required for manufacturing expansion",
            supporting_data={
                "capex_need": 50000000,
                "capacity_utilization": 0.92,
                "growth_forecast": 0.15,
            },
            rationale="Current manufacturing capacity nearing limits",
            sources=["capex_planning", "manufacturing_capacity"],
            recommended_action="Approve capex for manufacturing expansion",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.STRATEGIC_INVESTMENT,
        "expected_impact_min": 6,
        "expected_title_keywords": ["invest", "capex", "expansion", "manufactur"],
    },
}


# =============================================================================
# Integration Test Fixtures
# =============================================================================


@pytest.fixture
def all_expert_scenarios() -> dict:
    """Return all expert-labeled scenarios."""
    return EXPERT_LABELED_SCENARIOS


@pytest.fixture
def cloud_cost_scenario() -> dict:
    """Return the cloud cost over budget scenario (AC5)."""
    return EXPERT_LABELED_SCENARIOS["cloud_cost_over_budget"]


# =============================================================================
# End-to-End Recommendation Generation Tests
# =============================================================================


class TestEndToEndRecommendationGeneration:
    """End-to-end integration tests for recommendation generation."""

    @pytest.mark.asyncio
    async def test_generate_single_recommendation_e2e(self, cloud_cost_scenario: dict):
        """E2E: Single insight generates complete recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )

        assert isinstance(result, RecommendationResult)
        assert len(result.recommendations) == 1

        rec = result.recommendations[0]
        assert rec.category == cloud_cost_scenario["expected_category"]
        assert rec.impact_score >= cloud_cost_scenario["expected_impact_min"]

    @pytest.mark.asyncio
    async def test_generate_multiple_recommendations_e2e(self, all_expert_scenarios: dict):
        """E2E: Multiple insights generate sorted recommendations."""
        from raglite.insights.recommendations import generate_recommendations

        insights = [scenario["insight"] for scenario in all_expert_scenarios.values()]
        result = await generate_recommendations(insights, auto_synthesize=False)

        assert len(result.recommendations) == len(insights)
        # Verify sorted by impact descending
        scores = [r.impact_score for r in result.recommendations]
        assert scores == sorted(scores, reverse=True)


# =============================================================================
# Expert Alignment Validation Tests (AC4)
# =============================================================================


class TestExpertAlignmentValidation:
    """Tests validating 80%+ alignment with expert analysis (AC4)."""

    @pytest.mark.asyncio
    async def test_category_alignment_80_percent(self, all_expert_scenarios: dict):
        """AC4: Recommendation categories align with expert labels >= 80%."""
        from raglite.insights.recommendations import generate_recommendations

        correct_count = 0
        total_count = len(all_expert_scenarios)

        for _scenario_name, scenario in all_expert_scenarios.items():
            result = await generate_recommendations([scenario["insight"]], auto_synthesize=False)
            rec = result.recommendations[0]

            if rec.category == scenario["expected_category"]:
                correct_count += 1

        alignment_rate = correct_count / total_count
        assert alignment_rate >= 0.80, (
            f"Category alignment {alignment_rate:.1%} < 80% ({correct_count}/{total_count})"
        )

    @pytest.mark.asyncio
    async def test_impact_score_alignment_80_percent(self, all_expert_scenarios: dict):
        """AC4: Impact scores meet minimum thresholds >= 80%."""
        from raglite.insights.recommendations import generate_recommendations

        correct_count = 0
        total_count = len(all_expert_scenarios)

        for _scenario_name, scenario in all_expert_scenarios.items():
            result = await generate_recommendations([scenario["insight"]], auto_synthesize=False)
            rec = result.recommendations[0]

            if rec.impact_score >= scenario["expected_impact_min"]:
                correct_count += 1

        alignment_rate = correct_count / total_count
        assert alignment_rate >= 0.80, (
            f"Impact alignment {alignment_rate:.1%} < 80% ({correct_count}/{total_count})"
        )

    @pytest.mark.asyncio
    async def test_urgency_alignment(self, all_expert_scenarios: dict):
        """AC4: Urgency levels align with expert expectations."""
        from raglite.insights.recommendations import generate_recommendations

        correct_count = 0
        total_count = 0

        for _scenario_name, scenario in all_expert_scenarios.items():
            # Only test scenarios with urgency expectations
            if "expected_urgency" not in scenario and "expected_urgency_in" not in scenario:
                continue

            total_count += 1
            result = await generate_recommendations([scenario["insight"]], auto_synthesize=False)
            rec = result.recommendations[0]

            if "expected_urgency" in scenario:
                if rec.urgency == scenario["expected_urgency"]:
                    correct_count += 1
            elif "expected_urgency_in" in scenario:
                if rec.urgency in scenario["expected_urgency_in"]:
                    correct_count += 1

        if total_count > 0:
            alignment_rate = correct_count / total_count
            # Urgency is secondary - 67% threshold
            assert alignment_rate >= 0.67, (
                f"Urgency alignment {alignment_rate:.1%} < 67% ({correct_count}/{total_count})"
            )

    @pytest.mark.asyncio
    async def test_overall_expert_alignment_80_percent(self, all_expert_scenarios: dict):
        """AC4: Overall alignment with expert analysis >= 80%."""
        from raglite.insights.recommendations import generate_recommendations

        # Score each scenario on multiple criteria
        scores: list[float] = []

        for _scenario_name, scenario in all_expert_scenarios.items():
            result = await generate_recommendations([scenario["insight"]], auto_synthesize=False)
            rec = result.recommendations[0]

            scenario_score = 0.0
            criteria_count = 0

            # Category match (40% weight)
            criteria_count += 1
            if rec.category == scenario["expected_category"]:
                scenario_score += 1.0

            # Impact score meets minimum (30% weight)
            criteria_count += 1
            if rec.impact_score >= scenario["expected_impact_min"]:
                scenario_score += 1.0

            # Urgency alignment (if specified) (30% weight)
            if "expected_urgency" in scenario:
                criteria_count += 1
                if rec.urgency == scenario["expected_urgency"]:
                    scenario_score += 1.0
            elif "expected_urgency_in" in scenario:
                criteria_count += 1
                if rec.urgency in scenario["expected_urgency_in"]:
                    scenario_score += 1.0

            scores.append(scenario_score / criteria_count)

        overall_alignment = sum(scores) / len(scores)
        assert overall_alignment >= 0.80, f"Overall alignment {overall_alignment:.1%} < 80%"


# =============================================================================
# Cloud Cost Example Test (AC5)
# =============================================================================


class TestCloudCostExample:
    """Tests for specific cloud cost example (AC5)."""

    @pytest.mark.asyncio
    async def test_cloud_cost_generates_risk_mitigation(self, cloud_cost_scenario: dict):
        """AC5: Cloud cost anomaly generates RISK_MITIGATION recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.category == RecommendationCategory.RISK_MITIGATION

    @pytest.mark.asyncio
    async def test_cloud_cost_high_impact(self, cloud_cost_scenario: dict):
        """AC5: Cloud cost recommendation has high impact score >= 8."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.impact_score >= 8

    @pytest.mark.asyncio
    async def test_cloud_cost_high_urgency(self, cloud_cost_scenario: dict):
        """AC5: Cloud cost recommendation has high urgency."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.urgency == "high"

    @pytest.mark.asyncio
    async def test_cloud_cost_preserves_evidence(self, cloud_cost_scenario: dict):
        """AC5: Cloud cost recommendation preserves supporting evidence."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.supporting_evidence == cloud_cost_scenario["insight"].supporting_data
        assert "cloud_budget" in rec.supporting_evidence
        assert "budget_variance" in rec.supporting_evidence


# =============================================================================
# Processing Time Performance Tests
# =============================================================================


class TestProcessingTimePerformance:
    """Tests for processing time requirements."""

    @pytest.mark.asyncio
    async def test_processing_time_under_3s_for_5_insights(self, all_expert_scenarios: dict):
        """Performance: Processing time < 3s for 5 insights (without LLM)."""
        from raglite.insights.recommendations import generate_recommendations

        # Take first 5 scenarios
        insights = [scenario["insight"] for scenario in list(all_expert_scenarios.values())[:5]]

        start_time = time.time()
        result = await generate_recommendations(insights, auto_synthesize=False)
        elapsed_time = time.time() - start_time

        assert elapsed_time < 3.0, f"Processing took {elapsed_time:.2f}s (> 3s)"
        assert result.total_generated == 5

    @pytest.mark.asyncio
    async def test_processing_time_under_3s_for_10_insights(self):
        """Performance: Processing time < 3s for 10 insights (without LLM)."""
        from raglite.insights.recommendations import generate_recommendations

        # Generate 10 insights
        insights = [
            Insight(
                category=list(InsightCategory)[i % len(InsightCategory)],
                priority=(i % 5) + 1,
                summary=f"Test insight {i}",
                supporting_data={"index": i},
                sources=[f"source_{i}"],
                created_at=datetime.now(UTC),
            )
            for i in range(10)
        ]

        start_time = time.time()
        result = await generate_recommendations(insights, auto_synthesize=False)
        elapsed_time = time.time() - start_time

        assert elapsed_time < 3.0, f"Processing took {elapsed_time:.2f}s (> 3s)"
        assert result.total_generated == 10


# =============================================================================
# Pipeline Integration Tests
# =============================================================================


class TestPipelineIntegration:
    """Tests for integration with insight generation pipeline."""

    @pytest.mark.asyncio
    async def test_insight_to_recommendation_pipeline(self):
        """E2E: Insight generation -> Recommendation engine pipeline."""
        from raglite.insights.recommendations import generate_recommendations

        # Create insights similar to what generate_insights() would produce
        insights = [
            Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Critical anomaly in revenue",
                supporting_data={"severity": "critical", "metric": "revenue"},
                rationale="Revenue dropped unexpectedly",
                sources=["revenue"],
                recommended_action="Investigate immediately",
                created_at=datetime.now(UTC),
            ),
            Insight(
                category=InsightCategory.OPPORTUNITY,
                priority=2,
                summary="Growth opportunity in new segment",
                supporting_data={"growth": 0.20, "segment": "new"},
                rationale="Strong demand signals",
                sources=["segment_analysis"],
                recommended_action="Expand in new segment",
                created_at=datetime.now(UTC),
            ),
        ]

        result = await generate_recommendations(insights, auto_synthesize=False)

        assert len(result.recommendations) == 2
        assert result.insights_analyzed == 2

        # Verify highest impact first
        assert result.recommendations[0].impact_score >= result.recommendations[1].impact_score

    @pytest.mark.asyncio
    async def test_recommendation_filtering_pipeline(self):
        """E2E: Generate recommendations then filter."""
        from raglite.insights.recommendations import (
            filter_recommendations,
            generate_recommendations,
        )

        insights = [
            Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="High priority risk",
                created_at=datetime.now(UTC),
            ),
            Insight(
                category=InsightCategory.TREND,
                priority=5,
                summary="Low priority trend",
                created_at=datetime.now(UTC),
            ),
        ]

        result = await generate_recommendations(insights, auto_synthesize=False)

        # Filter to only high impact
        filtered = filter_recommendations(result.recommendations, min_impact=5)

        assert len(filtered) == 1
        assert filtered[0].impact_score >= 5


# =============================================================================
# Data Integrity Tests
# =============================================================================


class TestDataIntegrity:
    """Tests for data integrity through recommendation pipeline."""

    @pytest.mark.asyncio
    async def test_sources_preserved(self, cloud_cost_scenario: dict):
        """Data integrity: Sources from insight preserved in recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.sources == cloud_cost_scenario["insight"].sources

    @pytest.mark.asyncio
    async def test_supporting_data_preserved(self, cloud_cost_scenario: dict):
        """Data integrity: Supporting data from insight preserved as evidence."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.supporting_evidence == cloud_cost_scenario["insight"].supporting_data

    @pytest.mark.asyncio
    async def test_timestamp_is_set(self, cloud_cost_scenario: dict):
        """Data integrity: Recommendation has valid timestamp."""
        from raglite.insights.recommendations import generate_recommendations

        before = datetime.now(UTC)
        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        after = datetime.now(UTC)

        rec = result.recommendations[0]
        assert before <= rec.created_at <= after
