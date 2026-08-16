# Story 9.2: Classification Module - Period Type Classification + LLM API Resilience

Status: done

## Story

As a data engineer,
I want the ingestion pipeline to classify period types during extraction,
so that downstream forecasting queries can filter by period_type without complex normalization logic.

## Acceptance Criteria (BDD Format)

### AC1: Period Classifier Module Creation

```gherkin
Given the existing period classification logic in raglite/forecasting/timeseries/period_classification.py
When Story 9.2 is implemented
Then a new module exists at raglite/ingestion/classification/period_classifier.py
And it exports PeriodType, ClassifiedPeriod, classify_period, and ClassificationReport
And all functions maintain 100% backward compatibility with existing behavior
```

### AC2: Classification Accuracy Target

```gherkin
Given a ground truth dataset of 50+ period strings from production PDFs
When the period classifier processes all strings
Then it achieves 95%+ classification accuracy
And monthly actual periods (e.g., "Dec-21") are correctly classified
And YTD actual periods (e.g., "YTD Dec-21") are correctly classified
And budget periods (e.g., "B Dec-21") are correctly excluded
And unknown formats are properly flagged
```

### AC3: LLM API Resilience for Ambiguous Periods

```gherkin
Given a period string that cannot be classified by regex patterns
When LLM-based classification is attempted
Then the classifier uses exponential backoff on API failures (1s, 2s, 4s)
And a maximum of 3 retries are attempted before fallback
And fallback returns PeriodType.UNKNOWN with is_usable=False
And all failures are logged with structured logging
```

### AC4: Batch Classification with Caching

```gherkin
Given a list of 100+ period strings to classify
When classify_periods_batch() is called
Then classification results are cached by normalized input
And duplicate periods are only classified once
And a ClassificationReport is generated summarizing the batch
And batch processing completes in <500ms for 1000 periods
```

### AC5: Integration with Database Schema

```gherkin
Given the period_type column exists in financial_tables (Story 9.1)
When a period is classified
Then the period_type value matches the VARCHAR(50) column constraint
And valid values are: "monthly_actual", "ytd_actual", "budget", "ytd_budget", "unknown"
And the normalized period string is available for storage
```

### AC6: Portuguese Month Support

```gherkin
Given period strings with Portuguese month abbreviations
When classification is performed
Then "Dez-21" is classified as MONTHLY_ACTUAL with normalized="Dec-21"
And "Fev-24" is classified as MONTHLY_ACTUAL with normalized="Feb-24"
And "YTD Out-19" is classified as YTD_ACTUAL with normalized="Oct-19"
And Portuguese-English translation is applied consistently
```

## Tasks / Subtasks

- [ ] Task 1: Create classification module structure (AC: #1)
  - [ ] 1.1: Create `raglite/ingestion/classification/__init__.py` (AC: #1)
  - [ ] 1.2: Create `raglite/ingestion/classification/models.py` with PeriodType enum and ClassifiedPeriod dataclass (AC: #1, #5)
  - [ ] 1.3: Create `raglite/ingestion/classification/period_classifier.py` adapting logic from forecasting module (AC: #1, #6)
  - [ ] 1.4: Export all public symbols from `__init__.py` (AC: #1)

- [ ] Task 2: Implement batch classification with caching (AC: #4)
  - [ ] 2.1: Add `classify_periods_batch()` function with LRU cache (AC: #4)
  - [ ] 2.2: Implement `ClassificationReport` generation for batch results (AC: #4)
  - [ ] 2.3: Add performance validation ensuring <500ms for 1000 periods (AC: #4)

- [ ] Task 3: Implement LLM fallback with resilience (AC: #3)
  - [ ] 3.1: Create `_classify_with_llm()` for ambiguous periods (AC: #3)
  - [ ] 3.2: Implement exponential backoff retry logic (1s, 2s, 4s) (AC: #3)
  - [ ] 3.3: Add structured logging for all LLM interactions and failures (AC: #3)
  - [ ] 3.4: Implement fallback to UNKNOWN on exhausted retries (AC: #3)

- [ ] Task 4: Create ground truth dataset and accuracy validation (AC: #2)
  - [ ] 4.1: Create `tests/fixtures/period_classification_ground_truth.json` with 50+ examples (AC: #2)
  - [ ] 4.2: Add validation script to verify 95%+ accuracy (AC: #2)
  - [ ] 4.3: Include edge cases: Portuguese months, 4-digit years, double spaces (AC: #2, #6)

- [ ] Task 5: Unit tests (AC: #1, #2, #3, #4, #6)
  - [ ] 5.1: Create `tests/unit/ingestion/classification/test_period_classifier.py` (AC: #1)
  - [ ] 5.2: Test all PeriodType classifications (MONTHLY_ACTUAL, YTD_ACTUAL, BUDGET, YTD_BUDGET, UNKNOWN) (AC: #2)
  - [ ] 5.3: Test Portuguese month translation (AC: #6)
  - [ ] 5.4: Test batch classification and caching behavior (AC: #4)
  - [ ] 5.5: Test LLM retry logic with mocked API failures (AC: #3)
  - [ ] 5.6: Ensure test coverage meets 95%+ threshold per Epic 9 requirements

- [ ] Task 6: Integration tests (AC: #2, #5)
  - [ ] 6.1: Add integration test validating period_type values against database constraints (AC: #5)
  - [ ] 6.2: Add ground truth accuracy validation test (AC: #2)
  - [ ] 6.3: Add performance benchmark test for batch processing (AC: #4)

## Dev Notes

### Foundation Code Available

From commit `58fbc9e` (merged to main), the following exists in `raglite/forecasting/timeseries/period_classification.py`:

```python
class PeriodType(Enum):
    MONTHLY_ACTUAL = "monthly_actual"
    YTD_ACTUAL = "ytd_actual"
    BUDGET = "budget"
    YTD_BUDGET = "ytd_budget"
    UNKNOWN = "unknown"

@dataclass
class ClassifiedPeriod:
    original: str
    period_type: PeriodType
    normalized: str | None
    is_usable: bool

def classify_period(period: str | None) -> ClassifiedPeriod:
    # Regex-based classification logic (lines 88-191)
    ...

@dataclass
class ClassificationReport:
    # Summary statistics (lines 213-239)
    ...
```

### LLM API Resilience Pattern

Follow the pattern from `raglite/ingestion/adaptive_table/unit_inference/llm_inference.py`:

```python
def _call_mistral_for_unit_inference(...) -> str | None:
    try:
        from mistralai.models import SystemMessage, UserMessage
        from raglite.shared.clients import get_mistral_client

        client = get_mistral_client()
        response = client.chat.complete(...)
        return response.choices[0].message.content
    except Exception as e:
        logger.warning("Mistral API call failed", extra={"error": str(e)})
        return None
```

Add exponential backoff:

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)
def _classify_with_llm_retry(period: str) -> PeriodType:
    ...
```

### Database Schema Constraint

The `period_type` column (from Story 9.1) is VARCHAR(50). Valid values must match:

| PeriodType Enum | Database Value |
|-----------------|----------------|
| MONTHLY_ACTUAL | "monthly_actual" |
| YTD_ACTUAL | "ytd_actual" |
| BUDGET | "budget" |
| YTD_BUDGET | "ytd_budget" |
| UNKNOWN | "unknown" |

### Portuguese Month Mapping

From existing implementation:

```python
PORTUGUESE_MONTH_MAP: dict[str, str] = {
    "Fev": "Feb",
    "Abr": "Apr",
    "Mai": "May",
    "Ago": "Aug",
    "Set": "Sep",
    "Out": "Oct",
    "Dez": "Dec",
}
```

### Module Structure

```
raglite/ingestion/classification/
  __init__.py                    # Public exports
  models.py                       # PeriodType, ClassifiedPeriod, ClassificationReport
  period_classifier.py            # classify_period(), classify_periods_batch()
```

### Test Organization

- Unit tests: `tests/unit/ingestion/classification/test_period_classifier.py`
- Integration tests: `tests/integration/ingestion/test_classification_integration.py`
- Ground truth: `tests/fixtures/period_classification_ground_truth.json`

### Performance Requirements

- Single period classification: <1ms (regex-based)
- Batch classification (1000 periods): <500ms
- LLM fallback: 1-3s per call (with retries)

### File Size Constraints

Per `.claude/rules/file-size-limits.md`:
- Target: 100-250 LOC per file
- Hard limit: 500 LOC
- Split `models.py` and `period_classifier.py` accordingly

### References

- [Source: raglite/forecasting/timeseries/period_classification.py] - Foundation code to adapt
- [Source: tests/unit/forecasting/timeseries/test_period_classification.py] - Test patterns to follow
- [Source: raglite/ingestion/adaptive_table/unit_inference/llm_inference.py] - LLM API pattern
- [Source: docs/epics/epic-9-tracking.md] - Epic requirements (95% accuracy target)
- [Source: migrations/007_add_classification_columns.sql] - Database schema (Story 9.1)
- [Source: .claude/rules/testing.md] - Test marker requirements

## Dev Agent Record

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

### File List
