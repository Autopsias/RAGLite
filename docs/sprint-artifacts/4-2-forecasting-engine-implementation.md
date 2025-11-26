# Story 4.2: Forecasting Engine Implementation

Status: drafted

## Story

As a **system**,
I want **to forecast key financial indicators using the Architect-selected hybrid approach (Prophet + LLM)**,
so that **predictive insights are available to users with confidence intervals and contextual reasoning**.

## Acceptance Criteria

| AC | Criterion | Validation Method |
|----|-----------|-------------------|
| AC1 | Forecasting implementation uses hybrid approach (Prophet statistical + Claude LLM reasoning) | Code review verifies Prophet model + Claude API integration |
| AC2 | Key indicators supported: revenue, cash_flow, expense_categories per Project Brief (FR21) | Unit test verifies all three metric types |
| AC3 | Forecast generation produces predictions with confidence intervals (FR19) | Unit test validates `ForecastResult` contains `yhat`, `yhat_lower`, `yhat_upper` |
| AC4 | Forecast accuracy ±15% validated on historical data (NFR10) | Integration test with backtesting on 8+ quarters historical data |
| AC5 | Forecasting agent integrated into agentic framework | Integration test validates orchestrator can invoke forecasting |
| AC6 | Unit tests cover forecasting logic with ≥80% coverage | pytest-cov report on new code |
| AC7 | Integration test validates end-to-end forecast generation | Integration test: time-series extraction → forecasting → ForecastResult |

## Tasks / Subtasks

### Task 1: Create hybrid forecasting module (AC: 1, 2, 3)
- [ ] 1.1 Create `raglite/forecasting/hybrid.py` skeleton (~100 lines target)
- [ ] 1.2 Add Pydantic models: `ForecastResult`, `ForecastPoint` to `shared/models.py`
- [ ] 1.3 Implement `generate_forecast()` async function with Prophet + Claude
- [ ] 1.4 Support metrics: "revenue", "cash_flow", "expenses" via parameter

### Task 2: Implement Prophet statistical forecasting (AC: 1, 3, 4)
- [ ] 2.1 Configure Prophet model with quarterly seasonality (conservative settings)
- [ ] 2.2 Implement `_fit_prophet_model()` helper function
- [ ] 2.3 Extract predictions with confidence intervals (yhat, yhat_lower, yhat_upper)
- [ ] 2.4 Handle minimum data requirement (8 quarters) with graceful degradation

### Task 3: Implement LLM reasoning layer (AC: 1)
- [ ] 3.1 Implement `explain_forecast()` async function using Claude API
- [ ] 3.2 Generate confidence rationale based on data quality and trends
- [ ] 3.3 Identify risks/opportunities in forecast context

### Task 4: Integrate with agentic framework (AC: 5)
- [ ] 4.1 Create `ForecastingAgent` class in `raglite/agentic/agents/`
- [ ] 4.2 Register forecasting capabilities with orchestrator
- [ ] 4.3 Handle multi-step workflows (extract time-series → forecast)

### Task 5: Unit tests (AC: 6)
- [ ] 5.1 Create `tests/unit/test_hybrid_forecasting.py`
- [ ] 5.2 Test `generate_forecast()` with mocked Prophet model
- [ ] 5.3 Test `explain_forecast()` with mocked Claude responses
- [ ] 5.4 Test graceful degradation (insufficient data scenarios)
- [ ] 5.5 Achieve ≥80% coverage on new code (DoD requirement)

### Task 6: Integration tests (AC: 4, 7)
- [ ] 6.1 Create `tests/integration/test_forecasting_integration.py`
- [ ] 6.2 Implement backtesting: train on Q1-Q6, predict Q7-Q8, validate ±15%
- [ ] 6.3 Test end-to-end: time-series extraction → forecasting → result
- [ ] 6.4 Test agentic framework integration

### Task 7: Documentation and cleanup (AC: All)
- [ ] 7.1 Add Google-style docstrings to all public functions
- [ ] 7.2 Update story file with Dev Agent Record
- [ ] 7.3 Verify all linting passes (`uv run ruff check .`)

## Dev Notes

### Architecture Patterns

**File Location:** `raglite/forecasting/hybrid.py` (~100 lines target)

**Key Function Signatures:**
```python
async def generate_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int = 4
) -> ForecastResult:
    """Generate forecast for financial metric using Prophet + LLM.

    Args:
        metric: Metric name (e.g., "revenue", "cash_flow", "expenses")
        historical_data: Time-series data from Story 4.1 extraction
        periods_ahead: Number of periods to forecast (default 4 quarters)

    Returns:
        ForecastResult with predictions, confidence intervals, reasoning

    Raises:
        InsufficientDataError: If <8 data points available
    """

async def explain_forecast(
    forecast: ForecastResult,
    context: str
) -> str:
    """Use LLM to explain forecast with context.

    Args:
        forecast: Prophet forecast result
        context: Retrieved document context (trends, events)

    Returns:
        Natural language explanation with confidence rationale
    """
```

**Data Models (add to `shared/models.py`):**
```python
class ForecastPoint(BaseModel):
    """Single forecast data point with confidence interval."""
    date: datetime
    value: float  # yhat (predicted value)
    lower: float  # yhat_lower (confidence interval lower bound)
    upper: float  # yhat_upper (confidence interval upper bound)
    label: str | None = None  # e.g., "Q4 2024"

class ForecastResult(BaseModel):
    """Complete forecast result with reasoning."""
    metric_name: str
    historical_data: List[TimeSeriesPoint]
    forecast: List[ForecastPoint]
    confidence_reasoning: str
    basis: str  # e.g., "Prophet model trained on 8 quarters"
    accuracy_estimate: str  # e.g., "±15% (NFR10 target)"
    periods_ahead: int
```

### Prophet Configuration

Per Tech Spec Section 3.2:
```python
from prophet import Prophet

model = Prophet(
    yearly_seasonality=True,
    quarterly_seasonality=True,
    changepoint_prior_scale=0.05  # Conservative (prevent overfitting)
)

# Prepare DataFrame for Prophet (requires 'ds' and 'y' columns)
df = pd.DataFrame({
    'ds': [p.date for p in historical_data.points],
    'y': [p.value for p in historical_data.points]
})

# Fit and predict
model.fit(df)
future = model.make_future_dataframe(periods=periods_ahead, freq='Q')
forecast = model.predict(future)
```

### Graceful Degradation

Per Tech Spec Risk 3:
- **Minimum data requirement:** 8 quarters (2 years) for quarterly forecasts
- **If <8 data points:** Return `InsufficientDataError` with message: "Insufficient data for forecast. Minimum 8 data points required for reliable predictions."
- **Fallback:** Simple linear extrapolation if Prophet fails (not primary approach)

### Dependencies

- **Existing:** Claude API (already in tech stack), TimeSeriesData from Story 4.1
- **New:** `prophet` library (already approved in tech stack v1.2.1)
- **Story 4.1:** `extract_timeseries()` function provides input data

### NFR Requirements

- **NFR10:** ±15% forecast accuracy (validated via backtesting)
- **FR19:** Confidence intervals included in all forecasts
- **Processing time:** <30s for 4-quarter forecast

### Testing Strategy

Per `docs/process/definition-of-done.md`:
- New code must have ≥80% test coverage
- Unit tests mock Prophet model and Claude API (fast, deterministic)
- Integration tests use test database (port 6335/5433 per Story 4.0.5)
- Backtesting validates accuracy on held-out data

### Project Structure Notes

- Forecasting module exists from Story 4.1 (`raglite/forecasting/`)
- This story adds `hybrid.py` alongside existing `timeseries_extract.py`
- Story 4.3 will add automated forecast updates on document ingestion
- Story 4.4 will add MCP tool `get_financial_forecast()`

### Learnings from Previous Story

**From Story 4-1-time-series-data-extraction (Status: done)**

- **Forecasting Module Created:** `raglite/forecasting/` module exists with `__init__.py` and `timeseries_extract.py`
- **Core Functions Available:**
  - `extract_timeseries()`: Use this to get historical data for forecasting
  - `normalize_to_interval()`: Data is already normalized to consistent intervals
  - `parse_fiscal_date()`: Handles fiscal periods correctly
- **Pydantic Models Available:** `TimeSeriesPoint` and `TimeSeriesData` in `raglite/shared/models.py` (lines 306-343)
- **Test Patterns Established:**
  - Mock LLM responses for unit tests
  - Use test fixtures for integration tests
  - 88.89% coverage achieved (exceeds 80% requirement)
- **Dependencies Note:** `python-dateutil` is transitive dependency (works but not explicit)
- **Implementation Size:** Story 4.1 was 319 lines vs 50-line target - comprehensive error handling is acceptable

[Source: docs/sprint-artifacts/4-1-time-series-data-extraction.md#Dev-Agent-Record]

### References

- [Tech Spec: Epic 4 Section 3.2](docs/archive/tech-spec-epic-4.md#32-hybrid-forecasting-engine-ragliteforceastinghybridpy-100-lines)
- [Epic 4 PRD: Story 4.2](docs/prd/epic-4-forecasting-proactive-insights.md#story-42-forecasting-engine-implementation)
- [Architecture: Technology Stack](docs/architecture/5-technology-stack-definitive.md) - Prophet 1.2.1 approved
- [Definition of Done](docs/process/definition-of-done.md)
- [Previous Story: 4-1](docs/sprint-artifacts/4-1-time-series-data-extraction.md)

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-11-25 | SM (Bob) | Story drafted from Epic 4 PRD and Tech Spec in YOLO mode |
