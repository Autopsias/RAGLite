# Story 4.8: Strategic Recommendation Engine

Status: ready-for-dev

## Story

As a **system**,
I want **to generate actionable recommendations based on financial data analysis**,
so that **users receive strategic guidance on where to focus attention**.

## Acceptance Criteria

| AC | Criterion | Validation Method |
|----|-----------|-------------------|
| AC1 | Recommendation engine analyzes insights and generates actionable next steps (FR25) | Unit test: `generate_recommendations()` accepts List[Insight] and returns List[Recommendation] with actionable steps |
| AC2 | Recommendations prioritized by potential impact | Unit test: `Recommendation` model contains impact_score (1-10), results sorted by impact descending |
| AC3 | Recommendations include rationale with supporting data | Unit test: `Recommendation` model contains rationale string and supporting_evidence dict fields |
| AC4 | Recommendation quality validated: align with human expert analysis 80%+ of time | Integration test: validate recommendations against expert-labeled dataset (>=80% alignment) |
| AC5 | Example tested: "Focus on reducing cloud infrastructure costs - trending 40% over budget with minimal usage increase" | Integration test: synthetic test case with cloud cost anomaly generates expected recommendation |

## Tasks / Subtasks

### Task 1: Design Recommendation data models (AC: 2, 3)
- [ ] 1.1 Define `RecommendationCategory` enum in `raglite/shared/models.py` with values: COST_REDUCTION, REVENUE_GROWTH, RISK_MITIGATION, OPERATIONAL_EFFICIENCY, STRATEGIC_INVESTMENT
- [ ] 1.2 Define `Recommendation` model with fields: category, impact_score (1-10), title, description, rationale, supporting_evidence (Dict), action_steps (List[str]), urgency (high/medium/low), sources, created_at
- [ ] 1.3 Define `RecommendationResult` model with fields: recommendations (List[Recommendation]), total_generated, generation_method, insights_analyzed

### Task 2: Implement `generate_recommendations()` function (AC: 1, 2)
- [ ] 2.1 Create `raglite/insights/recommendations.py` module (~80-120 lines per target)
- [ ] 2.2 Implement signature: `async def generate_recommendations(insights: List[Insight], context: Optional[str] = None) -> RecommendationResult`
- [ ] 2.3 Implement recommendation categorization logic based on insight type (RISK insight -> RISK_MITIGATION, OPPORTUNITY -> REVENUE_GROWTH or COST_REDUCTION)
- [ ] 2.4 Implement impact scoring (1=low impact, 10=high impact) based on insight priority, magnitude, and affected metrics

### Task 3: Implement LLM-powered recommendation synthesis (AC: 1, 3)
- [ ] 3.1 Implement `synthesize_recommendation()` helper using Mistral Large for strategic reasoning
- [ ] 3.2 Generate rationale explaining why this recommendation matters
- [ ] 3.3 Generate concrete action steps (3-5 steps per recommendation)
- [ ] 3.4 Include supporting evidence citations from source insights
- [ ] 3.5 Determine urgency level based on insight priority and category

### Task 4: Implement recommendation prioritization and filtering (AC: 2, 4)
- [ ] 4.1 Implement impact scoring algorithm: insight priority + magnitude + strategic alignment
- [ ] 4.2 Implement deduplication (avoid redundant recommendations from similar insights)
- [ ] 4.3 Implement `filter_recommendations()` to limit results by category, impact threshold, or count
- [ ] 4.4 Sort results by impact score descending (10=highest impact first)

### Task 5: Structured logging and context (AC: 1)
- [ ] 5.1 Add structured logging with `extra={}` context for each generated recommendation
- [ ] 5.2 Log fields: category, impact_score, urgency, sources_count, generation_time_ms
- [ ] 5.3 Add timing metrics for recommendation generation performance

### Task 6: Unit tests (AC: 1, 2, 3)
- [ ] 6.1 Create `tests/unit/test_strategic_recommendations.py`
- [ ] 6.2 Test `RecommendationCategory` enum and `Recommendation` model (validation, serialization)
- [ ] 6.3 Test `generate_recommendations()` with mock insights
- [ ] 6.4 Test impact scoring algorithm (critical RISK insight -> high impact score)
- [ ] 6.5 Test recommendation categorization logic (RISK -> RISK_MITIGATION, OPPORTUNITY -> REVENUE_GROWTH)
- [ ] 6.6 Test `synthesize_recommendation()` with mocked Mistral client
- [ ] 6.7 Test deduplication logic (similar insights = consolidated recommendation)
- [ ] 6.8 Test edge cases: empty insights, single insight, conflicting recommendations
- [ ] 6.9 Achieve >=80% coverage on new code

### Task 7: Integration tests (AC: 4, 5)
- [ ] 7.1 Create `tests/integration/test_strategic_recommendations_integration.py`
- [ ] 7.2 Create expert-labeled test dataset with expected recommendations
- [ ] 7.3 Validate 80%+ recommendation alignment on test dataset
- [ ] 7.4 Test cloud cost example: "Focus on reducing cloud infrastructure costs - trending 40% over budget"
- [ ] 7.5 Test end-to-end: insight generation -> recommendation engine
- [ ] 7.6 Test processing time <3s for typical input (5-10 insights)

### Task 8: Documentation and cleanup (AC: All)
- [ ] 8.1 Add Google-style docstrings to all public functions
- [ ] 8.2 Update story file with Dev Agent Record
- [ ] 8.3 Verify all linting passes (`uv run ruff check .`)
- [ ] 8.4 Update `raglite/insights/__init__.py` with new exports

## Dev Notes

### Architecture Patterns

**File Locations (per Tech Spec Section 3.5):**
- Recommendations: `raglite/insights/recommendations.py` (~80-120 lines)
- Models: `raglite/shared/models.py` (add RecommendationCategory, Recommendation, RecommendationResult)
- Tests: `tests/unit/test_strategic_recommendations.py`, `tests/integration/test_strategic_recommendations_integration.py`

**Estimated Lines:** ~80-120 lines in recommendations.py, ~40 lines in models.py

**Key Function Signatures:**
```python
# In raglite/insights/recommendations.py
async def generate_recommendations(
    insights: List[Insight],
    context: Optional[str] = None
) -> RecommendationResult:
    """Generate strategic recommendations from analyzed insights.

    Story 4.8 AC1-AC5: Strategic recommendation engine with LLM synthesis.

    Args:
        insights: List of proactive insights from Story 4.7
        context: Optional additional context (company strategy, constraints)

    Returns:
        RecommendationResult containing:
          - recommendations: List of Recommendation objects sorted by impact
          - total_generated: Count before filtering
          - generation_method: "LLM synthesis (Mistral Large)"
          - insights_analyzed: Number of insights processed

    Raises:
        ValueError: If insights list is empty

    Example:
        >>> from raglite.insights.proactive import Insight, InsightCategory
        >>> insights = [Insight(category=InsightCategory.RISK, priority=1, ...)]
        >>> result = await generate_recommendations(insights)
        >>> print(result.recommendations[0])
        Recommendation(category="RISK_MITIGATION", impact_score=9, ...)
    """
```

**Data Models (add to `shared/models.py`):**
```python
from enum import Enum
from datetime import datetime
from typing import Dict, List, Any, Optional

class RecommendationCategory(str, Enum):
    """Category of strategic recommendation.

    Story 4.8 AC1: Recommendation categorization.
    """
    COST_REDUCTION = "cost_reduction"           # Reduce expenses, improve efficiency
    REVENUE_GROWTH = "revenue_growth"           # Increase revenue, expand market
    RISK_MITIGATION = "risk_mitigation"         # Address risks, prevent losses
    OPERATIONAL_EFFICIENCY = "operational_efficiency"  # Streamline processes
    STRATEGIC_INVESTMENT = "strategic_investment"      # Capital allocation decisions


class Recommendation(BaseModel):
    """Strategic recommendation generated from financial insights.

    Story 4.8 AC2/AC3: Recommendation with impact score and rationale.
    """
    category: RecommendationCategory = Field(
        ..., description="Recommendation category"
    )
    impact_score: int = Field(
        ..., ge=1, le=10,
        description="Impact score (1=low, 10=high)"
    )
    title: str = Field(
        ..., description="Short recommendation title"
    )
    description: str = Field(
        ..., description="Detailed recommendation description"
    )
    rationale: str = Field(
        default="", description="LLM-generated explanation of why this matters"
    )
    supporting_evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Data points supporting the recommendation"
    )
    action_steps: List[str] = Field(
        default_factory=list,
        description="Concrete action steps (3-5 items)"
    )
    urgency: str = Field(
        default="medium",
        description="Urgency level: high, medium, low"
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Source insights/documents cited"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Recommendation generation timestamp"
    )


class RecommendationResult(BaseModel):
    """Result of strategic recommendation generation.

    Story 4.8 AC1: Complete recommendation result with metadata.
    """
    recommendations: List[Recommendation] = Field(
        default_factory=list,
        description="List of recommendations sorted by impact (descending)"
    )
    total_generated: int = Field(
        ..., description="Total recommendations before filtering"
    )
    generation_method: str = Field(
        default="LLM synthesis (Mistral Large)",
        description="Method used for recommendation generation"
    )
    insights_analyzed: int = Field(
        ..., description="Number of insights processed"
    )
```

**Recommendation Logic:**
```python
def calculate_impact_score(insight: Insight) -> int:
    """Calculate recommendation impact score (1-10).

    Story 4.8 AC2: Impact scoring.
    """
    # Base score from insight priority (inverted: priority 1 = high impact)
    base_score = 11 - min(insight.priority * 2, 10)  # 1->9, 2->7, 3->5, 4->3, 5->1

    # Boost for critical categories
    if insight.category == InsightCategory.RISK:
        base_score = min(base_score + 2, 10)
    elif insight.category == InsightCategory.STRATEGIC_PRIORITY:
        base_score = min(base_score + 1, 10)

    return max(1, min(base_score, 10))


def categorize_recommendation(insight: Insight) -> RecommendationCategory:
    """Determine recommendation category based on insight.

    Story 4.8 AC1: Category mapping.
    """
    if insight.category == InsightCategory.RISK:
        return RecommendationCategory.RISK_MITIGATION
    elif insight.category == InsightCategory.OPPORTUNITY:
        # Determine if cost-related or revenue-related from supporting data
        if "cost" in str(insight.supporting_data).lower():
            return RecommendationCategory.COST_REDUCTION
        return RecommendationCategory.REVENUE_GROWTH
    elif insight.category == InsightCategory.ANOMALY:
        return RecommendationCategory.OPERATIONAL_EFFICIENCY
    elif insight.category == InsightCategory.STRATEGIC_PRIORITY:
        return RecommendationCategory.STRATEGIC_INVESTMENT
    else:  # TREND
        return RecommendationCategory.OPERATIONAL_EFFICIENCY
```

### Existing Module Reuse

**From Story 4.7 (Proactive Insight Generation):**
- `raglite/insights/proactive.py`:
  - `Insight` model with category, priority, supporting_data, rationale, recommended_action
  - `InsightCategory` enum (RISK, OPPORTUNITY, ANOMALY, TREND, STRATEGIC_PRIORITY)
  - `InsightGenerationResult` model
  - `generate_insights()` function

**From Shared Modules:**
- `raglite/shared/clients.py`:
  - `get_mistral_client()` for LLM reasoning
- `raglite/shared/logging.py`:
  - `get_logger(__name__)` for structured logging

### NFR Requirements

- **Tech Spec Section 3.5:** 80%+ recommendation alignment with expert analysis
- **FR25:** Recommendations include supporting data and rationale
- **Processing time:** <3s for typical input set (5-10 insights)
- **Story 4.9 dependency:** MCP tool `get_financial_insights` will include recommendations

### Testing Strategy

Per `docs/process/definition-of-done.md` and `docs/architecture/testing-strategy.md`:
- New code must have >=80% test coverage
- Unit tests mock external dependencies (Mistral client)
- Integration tests use test database (port 6335/5433 per Story 4.0.5)
- Expert-labeled test data for alignment validation

**Test Data Pattern:**
```python
# Expert-labeled recommendations for validation testing
TEST_SCENARIOS = {
    "cloud_cost_reduction": {
        "insights": [
            Insight(
                category=InsightCategory.OPPORTUNITY,
                priority=2,
                summary="Cloud infrastructure costs trending 40% under budget",
                supporting_data={
                    "cloud_budget": 5000000,
                    "cloud_actual": 3000000,
                    "usage_trend": "stable"
                },
                rationale="Significant cost savings opportunity"
            )
        ],
        "expected_category": RecommendationCategory.COST_REDUCTION,
        "expected_impact_min": 7,
        "expected_title_contains": "cloud",
        "expected_action_count_min": 3
    },
    "marketing_efficiency_risk": {
        "insights": [
            Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Marketing spend increased 30% YoY with no revenue increase",
                supporting_data={
                    "marketing_spend_yoy_change": 0.30,
                    "revenue_yoy_change": 0.02
                },
                rationale="Potential marketing inefficiency"
            )
        ],
        "expected_category": RecommendationCategory.RISK_MITIGATION,
        "expected_impact_min": 8,
        "expected_urgency": "high"
    }
}
```

### Project Structure Notes

- New file: `raglite/insights/recommendations.py`
- Module `raglite/insights/__init__.py` already exists from Story 4.5/4.6/4.7
- Models added to existing `shared/models.py`
- Story 4.9 will expose recommendations via MCP tool `get_financial_insights`

### Learnings from Previous Story

**From Story 4-7-proactive-insight-generation (Status: done)**

- **Insight Model Has recommended_action Field**: The `Insight` model already has a `recommended_action` field (Story 4.7 Task 1.2). Story 4.8 builds on this with a dedicated recommendation engine for more sophisticated strategic recommendations
- **LLM Synthesis Pattern**: `synthesize_insight()` uses `get_mistral_client()` with structured prompts - apply same pattern for `synthesize_recommendation()`
- **Priority Scoring Pattern**: `calculate_insight_priority()` maps severity/magnitude to 1-5 scale - adapt for impact scoring 1-10 scale
- **Test Coverage Target**: 61 tests (48 unit + 13 integration) achieved 75%+ accuracy - target 40+ tests, 80% alignment for recommendations
- **Structured Logging**: Comprehensive `extra={}` context logging established - apply same pattern
- **File Size**: proactive.py is ~495 lines - recommendations.py should be smaller (~80-120 lines) since it builds on existing infrastructure
- **Deduplication Pattern**: Story 4.7 Task 4.2 implemented deduplication - apply similar logic for recommendation consolidation

[Source: docs/sprint-artifacts/4-7-proactive-insight-generation.md#Dev-Agent-Record]

### Dependencies

- **Existing:** `raglite/insights/proactive.py` (`Insight`, `InsightCategory`, `InsightGenerationResult`, `generate_insights`)
- **Existing:** `raglite/shared/clients.py` (`get_mistral_client`)
- **Existing:** `raglite/shared/models.py` (base models)
- **Standard Library:** `datetime` for timestamps
- **No new libraries required** - all dependencies already available

### References

- [Epic 4 PRD: Story 4.8](docs/prd/epic-4-forecasting-proactive-insights.md#story-48-strategic-recommendation-engine)
- [Tech Spec Epic 4: Section 3.5](docs/archive/tech-spec-epic-4.md#35-proactive-insight-generation)
- [Definition of Done](docs/process/definition-of-done.md)
- [Coding Standards](docs/architecture/coding-standards.md)
- [Testing Strategy](docs/architecture/testing-strategy.md)
- [Previous Story: 4-7](docs/sprint-artifacts/4-7-proactive-insight-generation.md)

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/4-8-strategic-recommendation-engine.context.xml

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-11-27 | SM (Bob) | Story drafted from Epic 4 PRD and Tech Spec in YOLO mode |
