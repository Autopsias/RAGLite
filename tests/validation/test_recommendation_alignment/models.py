"""Data models for recommendation alignment validation.

Story 4.10 AC4: Expert-labeled test scenarios and validation results.
"""

from dataclasses import dataclass, field
from typing import Any

from raglite.shared.models import Insight, RecommendationCategory


@dataclass
class RecommendationTestScenario:
    """Expert-labeled test scenario for recommendation validation.

    Story 4.10 AC4: Each scenario has expected recommendation labeled by expert.

    Attributes:
        scenario_id: Unique identifier (e.g., "cost_reduction")
        description: Human-readable scenario description
        insight: Input insight that triggers recommendation
        expected_category: Expected RecommendationCategory
        expected_impact_range: Acceptable impact score range (min, max inclusive)
        expected_urgency: Expected urgency level (high, medium, low)
        expected_action_keywords: Keywords expected in action steps
    """

    scenario_id: str
    description: str
    insight: Insight
    expected_category: RecommendationCategory = RecommendationCategory.OPERATIONAL_EFFICIENCY
    expected_impact_range: tuple[int, int] = (1, 10)
    expected_urgency: str = "medium"
    expected_action_keywords: list[str] = field(default_factory=list)


@dataclass
class RecommendationValidationResult:
    """Result of recommendation alignment validation.

    Story 4.10 AC4: Structured validation result for recommendation alignment.

    Attributes:
        total_scenarios: Total number of test scenarios
        aligned_scenarios: Number of scenarios with aligned recommendations
        alignment_rate: Percentage of scenarios with aligned recommendations (0-100)
        passed: Whether alignment rate meets 80% threshold
        scenario_results: Per-scenario pass/fail details
        category_breakdown: Count of recommendations per category
    """

    total_scenarios: int
    aligned_scenarios: int
    alignment_rate: float
    passed: bool
    scenario_results: list[dict[str, Any]]
    category_breakdown: dict[str, int]
