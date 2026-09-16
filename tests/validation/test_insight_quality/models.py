"""Data models for insight quality validation.

Story 4.10 AC3: Test scenario and validation result models.
"""

from dataclasses import dataclass, field
from typing import Any

from raglite.shared.models import (
    Anomaly,
    ForecastResult,
    InsightCategory,
    Trend,
)


@dataclass
class InsightTestScenario:
    """Expert-labeled test scenario for insight validation.

    Story 4.10 AC3: Each scenario has expected outcomes labeled by expert.

    Attributes:
        scenario_id: Unique identifier (e.g., "marketing_spike")
        description: Human-readable scenario description
        anomaly: Optional anomaly input data
        trend: Optional trend input data
        forecast: Optional forecast input data
        expected_category: Expected InsightCategory for this scenario
        expected_priority_range: Acceptable priority range (min, max inclusive)
        expected_keywords: Keywords that should appear in rationale/summary
    """

    scenario_id: str
    description: str
    anomaly: Anomaly | None = None
    trend: Trend | None = None
    forecast: ForecastResult | None = None
    expected_category: InsightCategory = InsightCategory.RISK
    expected_priority_range: tuple[int, int] = (1, 5)
    expected_keywords: list[str] = field(default_factory=list)


@dataclass
class InsightValidationResult:
    """Result of insight quality validation.

    Story 4.10 AC3: Structured validation result for insight relevance.

    Attributes:
        total_scenarios: Total number of test scenarios
        passed_scenarios: Number of scenarios that passed validation
        relevance_rate: Percentage of scenarios with useful insights (0-100)
        passed: Whether relevance rate meets 75% threshold
        scenario_results: Per-scenario pass/fail details
        category_breakdown: Count of insights per category
    """

    total_scenarios: int
    passed_scenarios: int
    relevance_rate: float
    passed: bool
    scenario_results: list[dict[str, Any]]
    category_breakdown: dict[str, int]
