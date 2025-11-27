# Story 4.6: Trend Analysis & Pattern Recognition

Status: ready-for-dev

## Story

As a **system**,
I want **to identify trends and patterns in financial data**,
so that **strategic insights can be generated proactively**.

## Acceptance Criteria

| AC | Criterion | Validation Method |
|----|-----------|-------------------|
| AC1 | Trend analysis identifies: growth patterns, cyclical trends, correlations between metrics | Unit test: `analyze_trends()` callable with metrics list and timeseries data, returns List[Trend] |
| AC2 | Pattern recognition uses statistical analysis and/or LLM reasoning per Tech Spec | Unit test: CAGR calculation, QoQ growth rate, correlation detection via scipy.stats.pearsonr |
| AC3 | Trends characterized with direction (increasing/decreasing) and magnitude | Unit test: Trend model contains direction enum and magnitude float fields |
| AC4 | Trend analysis runs automatically on document ingestion or on-demand | Integration test: trigger on new document or via MCP query |
| AC5 | Unit tests validate trend detection logic | Unit test: synthetic data with known trends correctly identified |

## Tasks / Subtasks

### Task 1: Design Trend data models (AC: 1, 3)
- [ ] 1.1 Define `TrendDirection` enum in `raglite/shared/models.py` with values: INCREASING, DECREASING, STABLE, CYCLICAL
- [ ] 1.2 Define `Trend` model with fields: metric, direction, magnitude, confidence, start_date, end_date, description
- [ ] 1.3 Define `TrendAnalysisResult` model with trends list and metadata (metrics_analyzed, correlation_pairs, analysis_method)
- [ ] 1.4 Define `CorrelationResult` model with fields: metric_a, metric_b, correlation_coefficient, p_value, interpretation

### Task 2: Implement `analyze_trends()` function (AC: 1, 2, 3)
- [ ] 2.1 Create `raglite/insights/trends.py` module (~50-80 lines per Tech Spec)
- [ ] 2.2 Implement CAGR (Compound Annual Growth Rate) calculation
- [ ] 2.3 Implement QoQ (Quarter-over-Quarter) growth rate calculation
- [ ] 2.4 Implement direction detection (INCREASING if growth > 5%, DECREASING if < -5%, STABLE otherwise)
- [ ] 2.5 Implement magnitude calculation (percentage change normalized)

### Task 3: Implement correlation detection (AC: 1, 2)
- [ ] 3.1 Implement `detect_correlations()` helper using scipy.stats.pearsonr
- [ ] 3.2 Identify significant correlations (|r| > 0.7, p-value < 0.05)
- [ ] 3.3 Generate correlation interpretation (positive/negative, strong/moderate/weak)

### Task 4: Add LLM-powered trend explanation (AC: 2)
- [ ] 4.1 Implement `explain_trend()` helper function using Mistral Large
- [ ] 4.2 Generate contextual reasoning for trend significance
- [ ] 4.3 Include supporting data in explanation (CAGR value, correlation coefficient, time period)

### Task 5: Structured logging and context (AC: 4)
- [ ] 5.1 Add structured logging with `extra={}` context for each detected trend
- [ ] 5.2 Log fields: metric, direction, magnitude, start_date, end_date, analysis_method
- [ ] 5.3 Add timing metrics for analysis performance

### Task 6: Unit tests (AC: 1, 2, 3, 5)
- [ ] 6.1 Create `tests/unit/test_trend_analysis.py`
- [ ] 6.2 Test `Trend` and `TrendAnalysisResult` models (validation, serialization)
- [ ] 6.3 Test `analyze_trends()` with synthetic data containing known trends
- [ ] 6.4 Test CAGR calculation accuracy (±0.1% tolerance)
- [ ] 6.5 Test QoQ growth rate calculation
- [ ] 6.6 Test direction classification thresholds (INCREASING, DECREASING, STABLE)
- [ ] 6.7 Test `detect_correlations()` with known correlated/uncorrelated data
- [ ] 6.8 Test `explain_trend()` with mocked Mistral client
- [ ] 6.9 Test edge cases: empty data, single point, all identical values, insufficient data
- [ ] 6.10 Achieve >=80% coverage on new code

### Task 7: Integration tests (AC: 4, 5)
- [ ] 7.1 Create `tests/integration/test_trend_analysis_integration.py`
- [ ] 7.2 Create test dataset with expert-labeled trends
- [ ] 7.3 Validate 90%+ trend detection accuracy (Tech Spec requirement)
- [ ] 7.4 Test end-to-end: time-series extraction -> trend analysis -> result formatting
- [ ] 7.5 Test correlation detection on multi-metric dataset

### Task 8: Documentation and cleanup (AC: All)
- [ ] 8.1 Add Google-style docstrings to all public functions
- [ ] 8.2 Update story file with Dev Agent Record
- [ ] 8.3 Verify all linting passes (`uv run ruff check .`)
- [ ] 8.4 Update `raglite/insights/__init__.py` with new exports

## Dev Notes

### Architecture Patterns

**File Locations (per Tech Spec Section 3.4):**
- Trend analysis: `raglite/insights/trends.py` (~50-80 lines)
- Models: `raglite/shared/models.py` (add TrendDirection, Trend, TrendAnalysisResult, CorrelationResult)
- Tests: `tests/unit/test_trend_analysis.py`, `tests/integration/test_trend_analysis_integration.py`

**Estimated Lines:** ~50-80 lines in trends.py, ~50 lines in models.py

**Key Function Signatures (from Tech Spec Section 3.4):**
```python
# In raglite/insights/trends.py
async def analyze_trends(
    metrics: List[str],
    timeseries_data: Dict[str, TimeSeriesData]
) -> TrendAnalysisResult:
    """Analyze trends and patterns in financial data.

    Story 4.6 AC1-AC5: Statistical trend analysis with growth patterns and correlations.

    Args:
        metrics: List of metric names to analyze (e.g., ["revenue", "expenses", "cash_flow"])
        timeseries_data: Dict mapping metric names to their TimeSeriesData

    Returns:
        TrendAnalysisResult containing:
          - trends: List of detected Trend objects
          - correlations: List of CorrelationResult objects
          - metrics_analyzed: Number of metrics processed
          - analysis_method: "Statistical analysis (CAGR, QoQ, Pearson correlation)"

    Raises:
        ValueError: If timeseries has fewer than 3 data points for any metric

    Example:
        >>> from raglite.forecasting.timeseries_extract import TimeSeriesData
        >>> revenue = TimeSeriesData(metric="revenue", points=[...])
        >>> expenses = TimeSeriesData(metric="expenses", points=[...])
        >>> result = await analyze_trends(
        ...     ["revenue", "expenses"],
        ...     {"revenue": revenue, "expenses": expenses}
        ... )
        >>> print(result.trends[0])
        Trend(metric="revenue", direction=INCREASING, magnitude=15.2, confidence=0.95)
    """
```

**Data Models (add to `shared/models.py`):**
```python
from enum import Enum

class TrendDirection(str, Enum):
    """Direction of detected trend.

    Story 4.6 AC3: Trend direction characterization.
    """
    INCREASING = "increasing"  # Growth > 5%
    DECREASING = "decreasing"  # Growth < -5%
    STABLE = "stable"          # -5% <= growth <= 5%
    CYCLICAL = "cyclical"      # Seasonal pattern detected


class Trend(BaseModel):
    """Detected trend in financial time-series data.

    Story 4.6 AC1/AC3: Trend with direction and magnitude.
    """
    metric: str = Field(..., description="Metric name")
    direction: TrendDirection = Field(..., description="Trend direction")
    magnitude: float = Field(..., description="Magnitude as percentage (e.g., 15.2 for 15.2% CAGR)")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Statistical confidence")
    start_date: str = Field(..., description="Start of trend period")
    end_date: str = Field(..., description="End of trend period")
    description: str = Field(default="", description="LLM-generated trend explanation")
    cagr: float = Field(default=0.0, description="Compound Annual Growth Rate")
    qoq_growth: float = Field(default=0.0, description="Quarter-over-Quarter average growth")


class CorrelationResult(BaseModel):
    """Correlation between two financial metrics.

    Story 4.6 AC1: Correlation detection between metrics.
    """
    metric_a: str = Field(..., description="First metric name")
    metric_b: str = Field(..., description="Second metric name")
    correlation_coefficient: float = Field(
        ..., ge=-1.0, le=1.0,
        description="Pearson correlation coefficient"
    )
    p_value: float = Field(..., description="Statistical significance")
    interpretation: str = Field(
        default="",
        description="Human-readable interpretation (e.g., 'Strong positive correlation')"
    )


class TrendAnalysisResult(BaseModel):
    """Result of trend analysis across multiple metrics.

    Story 4.6 AC1: Complete trend analysis result with metadata.
    """
    trends: list[Trend] = Field(
        default_factory=list,
        description="List of detected trends"
    )
    correlations: list[CorrelationResult] = Field(
        default_factory=list,
        description="List of detected correlations"
    )
    metrics_analyzed: int = Field(..., description="Number of metrics processed")
    analysis_method: str = Field(
        default="Statistical analysis (CAGR, QoQ, Pearson correlation)",
        description="Methods used for analysis"
    )
```

**Trend Analysis Logic (from Tech Spec Section 3.4):**
```python
import numpy as np
from scipy.stats import pearsonr

def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """Calculate Compound Annual Growth Rate.

    Story 4.6 AC2: CAGR calculation for growth patterns.
    """
    if start_value <= 0 or years <= 0:
        return 0.0
    return ((end_value / start_value) ** (1 / years)) - 1


def calculate_qoq_growth(values: list[float]) -> float:
    """Calculate average Quarter-over-Quarter growth rate.

    Story 4.6 AC2: QoQ growth rate calculation.
    """
    if len(values) < 2:
        return 0.0
    growths = [(values[i] - values[i-1]) / values[i-1] * 100
               for i in range(1, len(values)) if values[i-1] != 0]
    return np.mean(growths) if growths else 0.0


def classify_direction(cagr: float, threshold: float = 0.05) -> TrendDirection:
    """Classify trend direction based on CAGR.

    Story 4.6 AC3: Direction classification.
    """
    if cagr > threshold:
        return TrendDirection.INCREASING
    elif cagr < -threshold:
        return TrendDirection.DECREASING
    return TrendDirection.STABLE


def detect_correlation(values_a: list[float], values_b: list[float]) -> CorrelationResult:
    """Detect correlation between two metrics using Pearson correlation.

    Story 4.6 AC1/AC2: Correlation detection.
    """
    if len(values_a) != len(values_b) or len(values_a) < 3:
        raise ValueError("Need at least 3 matching data points for correlation")

    r, p_value = pearsonr(values_a, values_b)

    # Generate interpretation
    strength = "strong" if abs(r) > 0.7 else "moderate" if abs(r) > 0.4 else "weak"
    direction = "positive" if r > 0 else "negative"
    interpretation = f"{strength.capitalize()} {direction} correlation"

    return CorrelationResult(
        metric_a="",  # Set by caller
        metric_b="",  # Set by caller
        correlation_coefficient=round(r, 3),
        p_value=round(p_value, 4),
        interpretation=interpretation
    )
```

### Existing Module Reuse

**From Story 4.1 (Time-Series Extraction):**
- `raglite/forecasting/timeseries_extract.py`:
  - `TimeSeriesData` model with `points` and `metric` fields
  - Data already normalized to consistent time intervals

**From Story 4.2 (Forecasting Engine):**
- `raglite/shared/clients.py`:
  - `get_mistral_client()` for LLM reasoning (trend explanation)

**From Story 4.5 (Anomaly Detection):**
- `raglite/insights/__init__.py` module already exists
- Similar pattern for `explain_trend()` as `explain_anomaly()`
- Same logging patterns with structured `extra={}` context
- Use existing model patterns (Anomaly, AnomalyDetectionResult)

### NFR Requirements

- **Tech Spec Section 3.4:** Trend detection accuracy 90%+ (expert validation)
- **Tech Spec Section 3.4:** Processing time <10s for 5 metrics
- **FR22/FR23:** Insight generation combines anomaly detection with trend analysis
- **Story 4.7 dependency:** Proactive insight generation requires trend analysis output

### Testing Strategy

Per `docs/process/definition-of-done.md` and `docs/architecture/testing-strategy.md`:
- New code must have >=80% test coverage
- Unit tests mock external dependencies (Mistral client, scipy stats)
- Integration tests use test database (port 6335/5433 per Story 4.0.5)
- Synthetic test data with known trends for accuracy validation

**Test Data Pattern:**
```python
# Synthetic data with known trends for testing
TEST_DATA = {
    "increasing_trend": {
        "values": [100.0, 105.0, 110.0, 116.0, 122.0, 128.0, 135.0, 142.0],
        "expected_direction": "increasing",
        "expected_cagr": 0.09  # ~9% annual growth
    },
    "decreasing_trend": {
        "values": [100.0, 95.0, 90.0, 86.0, 82.0, 78.0, 74.0, 70.0],
        "expected_direction": "decreasing",
        "expected_cagr": -0.08  # ~-8% annual growth
    },
    "stable_trend": {
        "values": [100.0, 101.0, 99.0, 100.5, 100.0, 99.5, 101.0, 100.0],
        "expected_direction": "stable",
        "expected_cagr": 0.0
    },
    "correlation_positive": {
        "metric_a": [100, 110, 120, 130, 140],
        "metric_b": [50, 55, 60, 65, 70],
        "expected_r": 1.0  # Perfect positive correlation
    },
    "correlation_negative": {
        "metric_a": [100, 110, 120, 130, 140],
        "metric_b": [70, 65, 60, 55, 50],
        "expected_r": -1.0  # Perfect negative correlation
    }
}
```

### Project Structure Notes

- New file: `raglite/insights/trends.py`
- Module `raglite/insights/__init__.py` already exists from Story 4.5
- Models added to existing `shared/models.py`
- Story 4.7 (Proactive Insight Generation) will consume trend analysis output
- Story 4.9 will expose trends via MCP tool `get_financial_insights`

### Learnings from Previous Story

**From Story 4-5-anomaly-detection (Status: done)**

- **Insights Module Created**: `raglite/insights/` module exists at `raglite/insights/__init__.py` - use same module for trends.py
- **Model Pattern**: `AnomalySeverity` enum and `Anomaly`/`AnomalyDetectionResult` models follow consistent pattern - use same approach for `TrendDirection`/`Trend`/`TrendAnalysisResult`
- **Test Coverage**: 43 tests (30 unit + 13 integration) achieved 97.56% coverage - target similar coverage (30+ tests)
- **Structured Logging**: Comprehensive `extra={}` context logging pattern established - apply same pattern for trend analysis
- **LLM Integration**: `explain_anomaly()` function uses `get_mistral_client()` from `shared/clients.py` - use same pattern for `explain_trend()`
- **Z-score Pattern**: Statistical analysis implementation (numpy) established - extend with scipy.stats.pearsonr for correlations
- **Edge Case Handling**: Empty data, single point, identical values handled - apply same patterns
- **File Size Note**: 195 lines vs ~50 estimated acceptable with comprehensive docstrings - expect similar for trends.py
- **Review Advisory**: Consider MINOR severity for trend-based detection - can integrate trend data with anomaly context

[Source: docs/sprint-artifacts/4-5-anomaly-detection.md#Dev-Agent-Record]

### Dependencies

- **Existing:** `raglite/forecasting/timeseries_extract.py` (`TimeSeriesData`)
- **Existing:** `raglite/shared/models.py` (base models)
- **Existing:** `raglite/shared/clients.py` (`get_mistral_client`)
- **Existing:** `raglite/insights/__init__.py` (module from Story 4.5)
- **New:** `scipy.stats` for `pearsonr` correlation (scipy already in dependencies)
- **Standard Library:** `numpy` (already in dependencies via sentence-transformers)
- **No new libraries required** - scipy already approved in Tech Spec

### References

- [Epic 4 PRD: Story 4.6](docs/prd/epic-4-forecasting-proactive-insights.md#story-46-trend-analysis--pattern-recognition)
- [Tech Spec Epic 4: Section 3.4](docs/archive/tech-spec-epic-4.md#34-trend-analysis)
- [Definition of Done](docs/process/definition-of-done.md)
- [Coding Standards](docs/architecture/coding-standards.md)
- [Testing Strategy](docs/architecture/testing-strategy.md)
- [Previous Story: 4-5](docs/sprint-artifacts/4-5-anomaly-detection.md)

## Dev Agent Record

### Context Reference

- `docs/sprint-artifacts/4-6-trend-analysis-pattern-recognition.context.xml` (generated 2025-11-27)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-11-27 | SM (Bob) | Story drafted from Epic 4 PRD and Tech Spec in YOLO mode |
