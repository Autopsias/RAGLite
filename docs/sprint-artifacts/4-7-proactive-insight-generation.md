# Story 4.7: Proactive Insight Generation

Status: done

## Story

As a **system**,
I want **to autonomously generate insights highlighting risks, opportunities, and areas requiring attention**,
so that **users learn what they should know without asking**.

## Acceptance Criteria

| AC | Criterion | Validation Method |
|----|-----------|-------------------|
| AC1 | Insight generation combines anomaly detection, trend analysis, and contextual reasoning (FR22, FR23) | Unit test: `generate_insights()` accepts anomalies, trends, forecasts and returns List[Insight] |
| AC2 | Insights categorized: risks, opportunities, anomalies, trends, strategic priorities | Unit test: `InsightCategory` enum with RISK, OPPORTUNITY, ANOMALY, TREND, STRATEGIC_PRIORITY values |
| AC3 | Insights ranked by priority/impact (FR24) | Unit test: `Insight` model contains priority field (1-5), results sorted by priority ascending |
| AC4 | Insight quality validated: 75%+ rated useful/actionable by user testing | Integration test: validate sample insights against expert-labeled dataset (>=75% accuracy) |
| AC5 | Insights include supporting data and rationale (FR25) | Unit test: `Insight` model contains supporting_data dict and rationale string fields |
| AC6 | Example insights tested: "Q3 marketing spend increased 30% YoY with no corresponding revenue increase - potential inefficiency" | Integration test: synthetic test case with known marketing/revenue anomaly generates expected insight |

## Tasks / Subtasks

### Task 1: Design Insight data models (AC: 2, 3, 5)
- [x] 1.1 Define `InsightCategory` enum in `raglite/shared/models.py` with values: RISK, OPPORTUNITY, ANOMALY, TREND, STRATEGIC_PRIORITY
- [x] 1.2 Define `Insight` model with fields: category, priority (1-5), summary, supporting_data (Dict), rationale, sources, recommended_action, created_at
- [x] 1.3 Define `InsightGenerationResult` model with fields: insights (List[Insight]), total_generated, generation_method, metrics_analyzed

### Task 2: Implement `generate_insights()` function (AC: 1, 2, 3)
- [x] 2.1 Create `raglite/insights/proactive.py` module (~50-80 lines per Tech Spec)
- [x] 2.2 Implement signature: `async def generate_insights(anomalies: List[Anomaly], trends: List[Trend], forecasts: List[ForecastResult]) -> InsightGenerationResult`
- [x] 2.3 Implement insight categorization logic based on input type (anomaly -> ANOMALY/RISK, trend -> TREND/OPPORTUNITY, forecast -> RISK/OPPORTUNITY)
- [x] 2.4 Implement priority scoring (1=critical, 5=low) based on severity, magnitude, and confidence

### Task 3: Implement LLM-powered insight synthesis (AC: 1, 5)
- [x] 3.1 Implement `synthesize_insight()` helper using Mistral Large for contextual reasoning
- [x] 3.2 Generate rationale combining anomalies, trends, and forecasts into coherent narrative
- [x] 3.3 Generate recommended actions based on insight category
- [x] 3.4 Include supporting data citations from source anomalies/trends/forecasts

### Task 4: Implement insight ranking and filtering (AC: 3, 4)
- [x] 4.1 Implement priority scoring algorithm: anomaly severity + trend magnitude + forecast confidence
- [x] 4.2 Implement deduplication (avoid redundant insights from same underlying data)
- [x] 4.3 Implement `filter_insights()` to limit results by category, priority, or count
- [x] 4.4 Sort results by priority (ascending: 1=most critical first)

### Task 5: Structured logging and context (AC: 1)
- [x] 5.1 Add structured logging with `extra={}` context for each generated insight
- [x] 5.2 Log fields: category, priority, sources_count, generation_time_ms
- [x] 5.3 Add timing metrics for insight generation performance

### Task 6: Unit tests (AC: 1, 2, 3, 5)
- [x] 6.1 Create `tests/unit/test_proactive_insights.py`
- [x] 6.2 Test `InsightCategory` enum and `Insight` model (validation, serialization)
- [x] 6.3 Test `generate_insights()` with mock anomalies, trends, forecasts
- [x] 6.4 Test priority scoring algorithm (higher severity = lower priority number)
- [x] 6.5 Test insight categorization logic (anomaly -> RISK/ANOMALY, positive trend -> OPPORTUNITY)
- [x] 6.6 Test `synthesize_insight()` with mocked Mistral client
- [x] 6.7 Test deduplication logic (same underlying metric = merged insight)
- [x] 6.8 Test edge cases: empty inputs, single anomaly, no trends, conflicting signals
- [x] 6.9 Achieve >=80% coverage on new code

### Task 7: Integration tests (AC: 4, 6)
- [x] 7.1 Create `tests/integration/test_proactive_insights_integration.py`
- [x] 7.2 Create expert-labeled test dataset with expected insights
- [x] 7.3 Validate 75%+ insight usefulness on test dataset
- [x] 7.4 Test marketing spend anomaly example: "Q3 marketing spend increased 30% YoY with no corresponding revenue increase"
- [x] 7.5 Test end-to-end: anomaly detection -> trend analysis -> insight generation
- [x] 7.6 Test processing time <5s for typical input (10 anomalies, 5 trends, 3 forecasts)

### Task 8: Documentation and cleanup (AC: All)
- [x] 8.1 Add Google-style docstrings to all public functions
- [x] 8.2 Update story file with Dev Agent Record
- [x] 8.3 Verify all linting passes (`uv run ruff check .`)
- [x] 8.4 Update `raglite/insights/__init__.py` with new exports

## Dev Notes

### Architecture Patterns

**File Locations (per Tech Spec Section 3.5):**
- Proactive insights: `raglite/insights/proactive.py` (~50-80 lines)
- Models: `raglite/shared/models.py` (add InsightCategory, Insight, InsightGenerationResult)
- Tests: `tests/unit/test_proactive_insights.py`, `tests/integration/test_proactive_insights_integration.py`

**Estimated Lines:** ~50-80 lines in proactive.py, ~30 lines in models.py

**Key Function Signatures (from Tech Spec Section 3.5):**
```python
# In raglite/insights/proactive.py
async def generate_insights(
    anomalies: List[Anomaly],
    trends: List[Trend],
    forecasts: List[ForecastResult]
) -> InsightGenerationResult:
    """Generate prioritized insights from anomalies, trends, and forecasts.

    Story 4.7 AC1-AC6: Proactive insight generation with LLM synthesis.

    Args:
        anomalies: List of detected anomalies from Story 4.5
        trends: List of identified trends from Story 4.6
        forecasts: List of forecast results from Story 4.2

    Returns:
        InsightGenerationResult containing:
          - insights: List of Insight objects sorted by priority
          - total_generated: Count before filtering
          - generation_method: "LLM synthesis (Mistral Large)"
          - metrics_analyzed: Number of unique metrics processed

    Raises:
        ValueError: If all inputs are empty (nothing to analyze)

    Example:
        >>> from raglite.insights.anomalies import Anomaly
        >>> from raglite.insights.trends import Trend
        >>> from raglite.forecasting.hybrid import ForecastResult
        >>> anomalies = [Anomaly(metric="marketing_spend", severity="critical", ...)]
        >>> trends = [Trend(metric="revenue", direction="stable", ...)]
        >>> result = await generate_insights(anomalies, trends, [])
        >>> print(result.insights[0])
        Insight(category="RISK", priority=1, summary="Marketing spend anomaly...")
    """
```

**Data Models (add to `shared/models.py`):**
```python
from enum import Enum
from datetime import datetime

class InsightCategory(str, Enum):
    """Category of proactive insight.

    Story 4.7 AC2: Insight categorization.
    """
    RISK = "risk"                      # Negative trend, forecast downturn, critical anomaly
    OPPORTUNITY = "opportunity"         # Positive trend, growth potential
    ANOMALY = "anomaly"                # Unexplained outlier requiring investigation
    TREND = "trend"                    # Notable pattern (neutral - could be good or bad)
    STRATEGIC_PRIORITY = "strategic_priority"  # High-impact area needing attention


class Insight(BaseModel):
    """Proactive insight generated from financial analysis.

    Story 4.7 AC2/AC3/AC5: Insight with category, priority, and supporting data.
    """
    category: InsightCategory = Field(..., description="Insight category")
    priority: int = Field(
        ..., ge=1, le=5,
        description="Priority (1=critical, 5=low)"
    )
    summary: str = Field(..., description="One-sentence insight summary")
    supporting_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Data points supporting the insight"
    )
    rationale: str = Field(default="", description="LLM-generated explanation")
    sources: List[str] = Field(
        default_factory=list,
        description="Source documents/metrics cited"
    )
    recommended_action: str = Field(
        default="",
        description="Suggested next step"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Insight generation timestamp"
    )


class InsightGenerationResult(BaseModel):
    """Result of proactive insight generation.

    Story 4.7 AC1: Complete insight generation result with metadata.
    """
    insights: List[Insight] = Field(
        default_factory=list,
        description="List of generated insights sorted by priority"
    )
    total_generated: int = Field(..., description="Total insights before filtering")
    generation_method: str = Field(
        default="LLM synthesis (Mistral Large)",
        description="Method used for insight generation"
    )
    metrics_analyzed: int = Field(..., description="Number of unique metrics processed")
```

**Insight Generation Logic (from Tech Spec Section 3.5):**
```python
def calculate_insight_priority(
    anomaly: Optional[Anomaly] = None,
    trend: Optional[Trend] = None,
    forecast: Optional[ForecastResult] = None
) -> int:
    """Calculate insight priority (1=critical, 5=low).

    Story 4.7 AC3: Priority scoring.
    """
    score = 3  # Default: medium priority

    if anomaly:
        if anomaly.severity == AnomalySeverity.CRITICAL:
            score = min(score, 1)
        elif anomaly.severity == AnomalySeverity.MODERATE:
            score = min(score, 2)

    if trend:
        if abs(trend.magnitude) > 20:  # >20% change
            score = min(score, 2)
        elif abs(trend.magnitude) > 10:  # >10% change
            score = min(score, 3)

    if forecast:
        # Significant forecast deviation from trend
        if forecast.confidence < 0.5:
            score = min(score, 2)  # Low confidence = needs attention

    return score


def categorize_insight(
    anomaly: Optional[Anomaly] = None,
    trend: Optional[Trend] = None,
    forecast: Optional[ForecastResult] = None
) -> InsightCategory:
    """Determine insight category based on inputs.

    Story 4.7 AC2: Insight categorization logic.
    """
    # Anomaly-driven: check severity
    if anomaly and anomaly.severity == AnomalySeverity.CRITICAL:
        return InsightCategory.RISK

    # Trend-driven: check direction
    if trend:
        if trend.direction == TrendDirection.INCREASING and trend.magnitude > 10:
            return InsightCategory.OPPORTUNITY
        elif trend.direction == TrendDirection.DECREASING and trend.magnitude < -10:
            return InsightCategory.RISK

    # Forecast-driven: check confidence and direction
    if forecast and forecast.confidence < 0.5:
        return InsightCategory.STRATEGIC_PRIORITY

    # Default: anomaly if present, otherwise trend
    if anomaly:
        return InsightCategory.ANOMALY
    if trend:
        return InsightCategory.TREND

    return InsightCategory.STRATEGIC_PRIORITY
```

### Existing Module Reuse

**From Story 4.5 (Anomaly Detection):**
- `raglite/insights/anomalies.py`:
  - `Anomaly` model with severity, metric, z_score fields
  - `AnomalySeverity` enum (MINOR, MODERATE, CRITICAL)
  - `AnomalyDetectionResult` model

**From Story 4.6 (Trend Analysis):**
- `raglite/insights/trends.py`:
  - `Trend` model with direction, magnitude, confidence fields
  - `TrendDirection` enum (INCREASING, DECREASING, STABLE, CYCLICAL)
  - `TrendAnalysisResult` model with trends and correlations

**From Story 4.2 (Forecasting Engine):**
- `raglite/forecasting/hybrid.py`:
  - `ForecastResult` model with predictions, confidence_intervals
  - Forecast confidence scoring

**From Shared Modules:**
- `raglite/shared/clients.py`:
  - `get_mistral_client()` for LLM reasoning
- `raglite/shared/logging.py`:
  - `get_logger(__name__)` for structured logging

### NFR Requirements

- **Tech Spec Section 3.5:** 75%+ insight usefulness (user testing validation)
- **Tech Spec Section 3.5:** 80%+ recommendation alignment with expert analysis
- **Processing time:** <5s for typical input set
- **FR22/FR23:** Contextual reasoning combining anomalies + trends
- **FR24:** Priority ranking for insight surfacing
- **FR25:** Supporting data and rationale included
- **Story 4.9 dependency:** MCP tool `get_financial_insights` will consume this output

### Testing Strategy

Per `docs/process/definition-of-done.md` and `docs/architecture/testing-strategy.md`:
- New code must have >=80% test coverage
- Unit tests mock external dependencies (Mistral client)
- Integration tests use test database (port 6335/5433 per Story 4.0.5)
- Expert-labeled test data for accuracy validation

**Test Data Pattern:**
```python
# Expert-labeled insights for validation testing
TEST_SCENARIOS = {
    "marketing_anomaly_risk": {
        "anomalies": [
            Anomaly(
                metric="marketing_spend",
                value=2600000,
                expected_value=2000000,
                z_score=2.5,
                severity=AnomalySeverity.MODERATE,
                description="30% YoY increase"
            )
        ],
        "trends": [
            Trend(
                metric="revenue",
                direction=TrendDirection.STABLE,
                magnitude=2.0,
                confidence=0.9
            )
        ],
        "expected_category": InsightCategory.RISK,
        "expected_priority": 2,
        "expected_summary_contains": "marketing spend"
    },
    "revenue_growth_opportunity": {
        "anomalies": [],
        "trends": [
            Trend(
                metric="revenue",
                direction=TrendDirection.INCREASING,
                magnitude=15.0,
                confidence=0.95
            )
        ],
        "expected_category": InsightCategory.OPPORTUNITY,
        "expected_priority": 3,
        "expected_summary_contains": "revenue growth"
    }
}
```

### Project Structure Notes

- New file: `raglite/insights/proactive.py`
- Module `raglite/insights/__init__.py` already exists from Story 4.5/4.6
- Models added to existing `shared/models.py`
- Story 4.9 will expose insights via MCP tool `get_financial_insights`

### Learnings from Previous Story

**From Story 4-6-trend-analysis-pattern-recognition (Status: done)**

- **Insights Module Structure**: `raglite/insights/` module already contains `__init__.py`, `anomalies.py`, `trends.py` - add `proactive.py` following same pattern
- **Model Pattern**: `TrendDirection` enum and `Trend`/`TrendAnalysisResult` models follow consistent Pydantic pattern - use same for `InsightCategory`/`Insight`/`InsightGenerationResult`
- **Test Coverage**: 69 tests (61 unit + 8 integration) achieved excellent coverage - target 40+ tests for this story
- **Structured Logging**: Comprehensive `extra={}` context logging established in trends.py - apply same pattern
- **LLM Integration**: `explain_trend()` function uses `get_mistral_client()` from `shared/clients.py` - use same for `synthesize_insight()`
- **File Size Note**: trends.py is 381 lines vs ~50 estimated - proactive.py may be similar with comprehensive docstrings
- **Correlation Pattern**: `detect_correlations()` demonstrates pattern for combining multiple metrics - use for insight synthesis
- **Review Advisory**: CYCLICAL detection reserved in enum but not implemented - similarly, some insight categories may be simpler initially

[Source: docs/sprint-artifacts/4-6-trend-analysis-pattern-recognition.md#Dev-Agent-Record]

### Dependencies

- **Existing:** `raglite/insights/anomalies.py` (`Anomaly`, `AnomalySeverity`, `AnomalyDetectionResult`)
- **Existing:** `raglite/insights/trends.py` (`Trend`, `TrendDirection`, `TrendAnalysisResult`)
- **Existing:** `raglite/forecasting/hybrid.py` (`ForecastResult`)
- **Existing:** `raglite/shared/clients.py` (`get_mistral_client`)
- **Existing:** `raglite/shared/models.py` (base models)
- **Standard Library:** `datetime` for timestamps
- **No new libraries required** - all dependencies already available

### References

- [Epic 4 PRD: Story 4.7](docs/prd/epic-4-forecasting-proactive-insights.md#story-47-proactive-insight-generation)
- [Tech Spec Epic 4: Section 3.5](docs/archive/tech-spec-epic-4.md#35-proactive-insight-generation)
- [Definition of Done](docs/process/definition-of-done.md)
- [Coding Standards](docs/architecture/coding-standards.md)
- [Testing Strategy](docs/architecture/testing-strategy.md)
- [Previous Story: 4-6](docs/sprint-artifacts/4-6-trend-analysis-pattern-recognition.md)

## Dev Agent Record

### Context Reference

- `docs/sprint-artifacts/4-7-proactive-insight-generation.context.xml` (generated 2025-11-27)

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - Clean implementation

### Completion Notes List

1. **Data Models** (Task 1): Added `InsightCategory` enum (5 values: RISK, OPPORTUNITY, ANOMALY, TREND, STRATEGIC_PRIORITY), `Insight` model with all required fields (category, priority 1-5, summary, supporting_data dict, rationale, sources, recommended_action, created_at), and `InsightGenerationResult` model to `raglite/shared/models.py`

2. **Core Implementation** (Tasks 2-5): Created `raglite/insights/proactive.py` (~495 lines with comprehensive docstrings) containing:
   - `generate_insights()` - Main function combining anomalies, trends, forecasts into prioritized insights
   - `categorize_insight()` - Categorization logic (critical anomaly -> RISK, increasing trend >10% -> OPPORTUNITY, etc.)
   - `calculate_insight_priority()` - Priority scoring (1=critical for CRITICAL anomaly, 2 for MODERATE or >20% trend, etc.)
   - `synthesize_insight()` - LLM-powered insight synthesis using Mistral Large for rationale and recommendations
   - `filter_insights()` - Filter by category, priority, or count

3. **Unit Tests** (Task 6): Created `tests/unit/test_proactive_insights.py` with 48 tests covering:
   - InsightCategory enum values
   - Insight model validation and serialization
   - Priority calculation logic
   - Categorization logic
   - Filter functionality
   - LLM synthesis with mocked Mistral client
   - Marketing spend example (AC6)
   - Edge cases (empty inputs, single inputs, conflicting signals)

4. **Integration Tests** (Task 7): Created `tests/integration/test_proactive_insights_integration.py` with 13 tests covering:
   - End-to-end insight generation
   - Processing time <5s for typical input
   - 6 expert-labeled scenarios with expected categories/priorities
   - 75% accuracy threshold validation
   - Marketing spend anomaly example (AC6)
   - Anomaly detection -> insight pipeline
   - Trend analysis -> insight pipeline

5. **Documentation**: All public functions have Google-style docstrings with Args, Returns, Raises, and Example sections

### File List

**New Files:**
- `raglite/insights/proactive.py` (~495 lines)
- `tests/unit/test_proactive_insights.py` (~660 lines, 48 tests)
- `tests/integration/test_proactive_insights_integration.py` (~370 lines, 13 tests)

**Modified Files:**
- `raglite/shared/models.py` - Added InsightCategory, Insight, InsightGenerationResult models (~90 lines added)
- `raglite/insights/__init__.py` - Added exports for new functions
- `docs/sprint-status.yaml` - Updated 4-7 status to in-progress

### Test Results

- Unit tests: 48/48 passed (6.45s)
- Integration tests: 13/13 passed (53.35s)
- Total new tests: 61 tests

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-11-27 | SM (Bob) | Story drafted from Epic 4 PRD and Tech Spec in YOLO mode |
| 2025-11-27 | Dev (Amelia) | Implementation complete - all tasks done, 61 tests passing, ready for code review |
| 2025-11-27 | Dev (Amelia) | **Senior Dev Code Review APPROVED** - All 6 ACs verified with file:line evidence, 61/61 tests pass (48 unit + 13 integration), 75%+ expert-labeled accuracy validated, linting passes, architecture aligned |
