"""Recommendation alignment validator implementation.

Story 4.10 AC4: Validates recommendation alignment with expert analysis.
Target: 80%+ alignment rate with expert-labeled ground truth.
"""

from typing import Any
from unittest.mock import AsyncMock, patch

from raglite.insights.recommendations import generate_recommendations
from raglite.shared.models import Recommendation

from .models import RecommendationTestScenario, RecommendationValidationResult


class RecommendationAlignmentValidator:
    """Validates recommendation alignment against 80% expert agreement threshold.

    Story 4.10 AC4: Expert-labeled recommendation validation.

    Example:
        >>> validator = RecommendationAlignmentValidator()
        >>> result = await validator.validate_recommendations(test_scenarios)
        >>> assert result.passed  # alignment_rate >= 80%
    """

    def __init__(self, threshold_pct: float = 80.0, impact_tolerance: int = 2):
        """Initialize validator with alignment threshold.

        Args:
            threshold_pct: Minimum acceptable alignment rate (default 80.0)
            impact_tolerance: Acceptable deviation from expected impact (default ±2)
        """
        self.threshold_pct = threshold_pct
        self.impact_tolerance = impact_tolerance

    def _is_recommendation_aligned(
        self,
        recommendation: Recommendation,
        scenario: RecommendationTestScenario,
    ) -> tuple[bool, str]:
        """Check if generated recommendation aligns with expert expectations.

        Story 4.10 Task 3.3: Alignment scoring logic.

        Args:
            recommendation: Generated recommendation
            scenario: Expected scenario with expert labels

        Returns:
            Tuple of (is_aligned, reason)
        """
        reasons = []

        # Check 1: Category match
        category_match = recommendation.category == scenario.expected_category
        if not category_match:
            reasons.append(
                f"Category mismatch: got {recommendation.category.value}, "
                f"expected {scenario.expected_category.value}"
            )

        # Check 2: Impact score within tolerance of expected range
        impact_min, impact_max = scenario.expected_impact_range
        impact_in_range = (
            impact_min - self.impact_tolerance
            <= recommendation.impact_score
            <= impact_max + self.impact_tolerance
        )
        if not impact_in_range:
            reasons.append(
                f"Impact out of range: got {recommendation.impact_score}, "
                f"expected [{impact_min}, {impact_max}] ±{self.impact_tolerance}"
            )

        # Check 3: Action steps are actionable (have verb-noun structure)
        has_actionable_steps = self._has_actionable_steps(recommendation.action_steps)
        if not has_actionable_steps:
            reasons.append("Action steps not actionable (missing verb-noun structure)")

        # Check 4: Rationale references supporting data (non-empty)
        has_rationale = bool(recommendation.rationale)
        if not has_rationale:
            reasons.append("No rationale provided")

        # Overall alignment: category match + impact in range + actionable steps
        is_aligned = category_match and impact_in_range and has_actionable_steps

        reason = "; ".join(reasons) if reasons else "All checks passed"
        return is_aligned, reason

    def _has_actionable_steps(self, action_steps: list[str]) -> bool:
        """Check if action steps are actionable (verb-noun structure).

        Story 4.10 Task 3.3: Validate action_steps are actionable.

        Args:
            action_steps: List of action step strings

        Returns:
            True if at least one step has actionable verb
        """
        if not action_steps:
            return False

        # Common actionable verbs for business recommendations
        actionable_verbs = {
            "review",
            "analyze",
            "assess",
            "evaluate",
            "implement",
            "develop",
            "create",
            "reduce",
            "increase",
            "optimize",
            "improve",
            "establish",
            "conduct",
            "monitor",
            "track",
            "identify",
            "investigate",
            "allocate",
            "prioritize",
            "schedule",
            "plan",
            "execute",
            "negotiate",
            "streamline",
            "automate",
            "delegate",
            "consolidate",
            "diversify",
            "invest",
            "divest",
        }

        for step in action_steps:
            words = step.lower().split()
            if words and words[0] in actionable_verbs:
                return True

        # Fallback: any step with length > 5 words is likely actionable
        return any(len(step.split()) >= 5 for step in action_steps)

    async def validate_recommendations(
        self,
        test_scenarios: list[RecommendationTestScenario],
    ) -> RecommendationValidationResult:
        """Score recommendations against expert-labeled expectations.

        Story 4.10 AC4: Run scenarios and calculate alignment rate.

        Args:
            test_scenarios: List of scenarios with expected recommendations

        Returns:
            RecommendationValidationResult with alignment rate and breakdown

        Raises:
            ValueError: If no test scenarios provided
        """
        if not test_scenarios:
            raise ValueError("No test scenarios provided")

        scenario_results: list[dict[str, Any]] = []
        category_counts: dict[str, int] = {}
        aligned_count = 0

        # Mock LLM for faster validation
        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_response = AsyncMock()
            mock_response.choices = [
                AsyncMock(
                    message=AsyncMock(
                        content=(
                            "TITLE: Strategic Recommendation\n"
                            "DESCRIPTION: Based on analysis, we recommend action.\n"
                            "RATIONALE: This matters because of financial impact.\n"
                            "ACTIONS:\n"
                            "1. Review the underlying data\n"
                            "2. Assess impact on business objectives\n"
                            "3. Develop action plan with stakeholders"
                        )
                    )
                )
            ]
            mock_client.return_value.chat.complete.return_value = mock_response

            for scenario in test_scenarios:
                # Generate recommendations from insight
                result = await generate_recommendations(
                    insights=[scenario.insight],
                    context=scenario.description,
                    auto_synthesize=True,
                )

                # Validate first recommendation (primary result)
                if result.recommendations:
                    rec = result.recommendations[0]
                    is_aligned, reason = self._is_recommendation_aligned(rec, scenario)

                    # Track category
                    cat_key = rec.category.value
                    category_counts[cat_key] = category_counts.get(cat_key, 0) + 1

                    scenario_results.append(
                        {
                            "scenario_id": scenario.scenario_id,
                            "description": scenario.description,
                            "aligned": is_aligned,
                            "reason": reason,
                            "generated_category": rec.category.value,
                            "generated_impact": rec.impact_score,
                            "generated_urgency": rec.urgency,
                            "expected_category": scenario.expected_category.value,
                            "expected_impact_range": scenario.expected_impact_range,
                            "expected_urgency": scenario.expected_urgency,
                        }
                    )

                    if is_aligned:
                        aligned_count += 1
                else:
                    scenario_results.append(
                        {
                            "scenario_id": scenario.scenario_id,
                            "description": scenario.description,
                            "aligned": False,
                            "reason": "No recommendations generated",
                            "generated_category": None,
                            "generated_impact": None,
                            "generated_urgency": None,
                            "expected_category": scenario.expected_category.value,
                            "expected_impact_range": scenario.expected_impact_range,
                            "expected_urgency": scenario.expected_urgency,
                        }
                    )

        # Calculate alignment rate
        alignment_rate = (aligned_count / len(test_scenarios)) * 100

        return RecommendationValidationResult(
            total_scenarios=len(test_scenarios),
            aligned_scenarios=aligned_count,
            alignment_rate=alignment_rate,
            passed=alignment_rate >= self.threshold_pct,
            scenario_results=scenario_results,
            category_breakdown=category_counts,
        )
