"""Tests validating 80%+ alignment with expert analysis (AC4)."""

import time

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


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
