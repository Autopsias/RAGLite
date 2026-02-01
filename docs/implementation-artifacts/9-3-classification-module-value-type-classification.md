# Story 9.3: Classification Module - Value Type Classification

Status: ready-for-dev

## Story

As a data engineer,
I want the ingestion pipeline to classify value types (actual, budget, forecast, variance) during extraction,
so that downstream forecasting queries can filter by value_type without complex inference logic.

## Acceptance Criteria (BDD Format)

### AC1: Value Type Classifier Module Creation

```gherkin
Given the period classification module exists at raglite/ingestion/classification/
When Story 9.3 is implemented
Then a new module exists at raglite/ingestion/classification/value_type_classifier.py
And it exports ValueType enum and classify_value_type function
And the module follows the same patterns as period_classifier.py
```

### AC2: ValueType Enum Definition

```gherkin
Given the value_type column in financial_tables is VARCHAR(50)
When the ValueType enum is defined
Then it includes: ACTUAL, BUDGET, FORECAST, VARIANCE, UNKNOWN
And enum values map to database strings: "actual", "budget", "forecast", "variance", "unknown"
And the enum is exported from raglite/ingestion/classification/__init__.py
```

### AC3: Classification Accuracy Target

```gherkin
Given a ground truth dataset of 50+ value type examples from production PDFs
When the value type classifier processes all examples
Then it achieves 90%+ classification accuracy
And actual values (no modifier) are correctly classified as ACTUAL
And budget indicators ("B ", "Budget", "Orcamento") are classified as BUDGET
And forecast indicators ("F ", "Forecast", "Previsao") are classified as FORECAST
And variance indicators ("Var", "Delta", "%Var") are classified as VARIANCE
And unknown formats are properly flagged as UNKNOWN
```

### AC4: Context-Based Classification

```gherkin
Given a period string and optional column header context
When classify_value_type() is called
Then it uses period prefixes (e.g., "B Dec-21" -> BUDGET) as primary signal
And column headers (e.g., "Budget", "Actual", "Forecast") as secondary signal
And returns ACTUAL as default when no modifiers are present
And handles Portuguese equivalents (Orcamento, Previsao, Real)
```

### AC5: Integration with Period Classification

```gherkin
Given period_type classification already identifies BUDGET and YTD_BUDGET
When value_type classification runs
Then BUDGET period types are automatically marked as value_type=BUDGET
And YTD_BUDGET period types are automatically marked as value_type=BUDGET
And MONTHLY_ACTUAL and YTD_ACTUAL default to value_type=ACTUAL
And this prevents classification inconsistencies
```

### AC6: Batch Classification Support

```gherkin
Given a list of period strings and optional headers to classify
When classify_value_types_batch() is called
Then all items are classified efficiently
And a ClassificationReport is generated with value_type breakdown
And batch processing completes in <100ms for 1000 items
```

## Tasks / Subtasks

- [ ] Task 1: Create value type classifier module (AC: #1, #2)
  - [ ] 1.1: Create `raglite/ingestion/classification/value_type_classifier.py` (AC: #1)
  - [ ] 1.2: Define `ValueType` enum with 5 values matching database constraints (AC: #2)
  - [ ] 1.3: Define `ClassifiedValueType` dataclass mirroring ClassifiedPeriod pattern (AC: #1)
  - [ ] 1.4: Export new symbols from `__init__.py` (AC: #1, #2)

- [ ] Task 2: Implement classification logic (AC: #3, #4, #5)
  - [ ] 2.1: Implement `classify_value_type(period: str, header: str | None = None) -> ClassifiedValueType` (AC: #4)
  - [ ] 2.2: Add regex patterns for budget indicators ("B ", "Budget", "Orcamento") (AC: #3)
  - [ ] 2.3: Add regex patterns for forecast indicators ("F ", "Forecast", "Previsao") (AC: #3)
  - [ ] 2.4: Add regex patterns for variance indicators ("Var", "Delta", "%Var") (AC: #3)
  - [ ] 2.5: Implement period_type-aware classification (BUDGET period_type -> BUDGET value_type) (AC: #5)
  - [ ] 2.6: Add Portuguese language support (Real, Orcamento, Previsao) (AC: #4)

- [ ] Task 3: Implement batch classification (AC: #6)
  - [ ] 3.1: Implement `classify_value_types_batch()` function (AC: #6)
  - [ ] 3.2: Add `ValueTypeReport` dataclass for batch statistics (AC: #6)
  - [ ] 3.3: Add performance validation ensuring <100ms for 1000 items (AC: #6)

- [ ] Task 4: Create ground truth dataset (AC: #3)
  - [ ] 4.1: Create `tests/fixtures/value_type_ground_truth.json` with 50+ examples (AC: #3)
  - [ ] 4.2: Include examples from all categories (actual, budget, forecast, variance) (AC: #3)
  - [ ] 4.3: Include Portuguese language examples (AC: #3)
  - [ ] 4.4: Add edge cases: mixed case, extra spaces, partial matches (AC: #3)

- [ ] Task 5: Unit tests (AC: #1, #2, #3, #4, #5, #6)
  - [ ] 5.1: Create `tests/unit/ingestion/classification/test_value_type_classifier.py` (AC: #1)
  - [ ] 5.2: Test all ValueType classifications (ACTUAL, BUDGET, FORECAST, VARIANCE, UNKNOWN) (AC: #2)
  - [ ] 5.3: Test period_type integration (BUDGET period -> BUDGET value) (AC: #5)
  - [ ] 5.4: Test Portuguese language support (AC: #4)
  - [ ] 5.5: Test batch classification and report generation (AC: #6)
  - [ ] 5.6: Ensure test coverage meets 95%+ threshold per Epic 9 requirements

- [ ] Task 6: Integration tests (AC: #3, #5)
  - [ ] 6.1: Add ground truth accuracy validation test (AC: #3)
  - [ ] 6.2: Add integration test with period_classifier coordination (AC: #5)
  - [ ] 6.3: Add performance benchmark test for batch processing (AC: #6)

## Dev Notes

### ValueType Enum Design

Following the pattern from `raglite/ingestion/classification/models.py`:

```python
class ValueType(Enum):
    """Classification of value types in financial data.

    Used to filter actual vs budget vs forecast data for analysis.
    """

    ACTUAL = "actual"       # Realized/historical values
    BUDGET = "budget"       # Planned/budgeted values
    FORECAST = "forecast"   # Predicted/projected values
    VARIANCE = "variance"   # Difference calculations
    UNKNOWN = "unknown"     # Cannot determine type
```

### Classification Patterns

**Budget Indicators (case-insensitive):**
- Period prefix: "B Dec-21", "B Jun-24"
- Header/column: "Budget", "Orcamento", "Plano"
- Label: "Budget YTD", "Budget Monthly"

**Forecast Indicators (case-insensitive):**
- Period prefix: "F Dec-21", "F Jun-24"
- Header/column: "Forecast", "Previsao", "Projected"
- Label: "Forecast YTD", "Projected"

**Variance Indicators (case-insensitive):**
- Period prefix: "Var", "%Var", "Delta"
- Header/column: "Variance", "Variacao", "Diff"
- Format: "Var vs Budget", "% Var"

**Actual (default):**
- No modifier present
- Header/column: "Actual", "Real"
- Standard period format: "Dec-21" without B/F prefix

### Integration with PeriodType

From `raglite/ingestion/classification/models.py`, PeriodType already distinguishes:
- `BUDGET = "budget"` - "B Dec-21", "Dec-21 B"
- `YTD_BUDGET = "ytd_budget"` - "YTD B Dec-21"

The value_type classifier should leverage this:

```python
def classify_value_type(
    period: str,
    header: str | None = None,
    period_type: PeriodType | None = None
) -> ClassifiedValueType:
    # If period_type is BUDGET or YTD_BUDGET, value_type is BUDGET
    if period_type in (PeriodType.BUDGET, PeriodType.YTD_BUDGET):
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.BUDGET,
            source="period_type"
        )
    ...
```

### Portuguese Language Mapping

```python
PORTUGUESE_VALUE_TYPE_MAP: dict[str, ValueType] = {
    "real": ValueType.ACTUAL,
    "actual": ValueType.ACTUAL,
    "orcamento": ValueType.BUDGET,
    "budget": ValueType.BUDGET,
    "plano": ValueType.BUDGET,
    "previsao": ValueType.FORECAST,
    "forecast": ValueType.FORECAST,
    "variacao": ValueType.VARIANCE,
    "variance": ValueType.VARIANCE,
}
```

### Module Structure

```
raglite/ingestion/classification/
  __init__.py                    # Add ValueType, ClassifiedValueType exports
  models.py                      # Add ValueType enum, ClassifiedValueType dataclass
  period_classifier.py           # Existing (unchanged)
  value_type_classifier.py       # NEW - Story 9.3
```

### Test Organization

- Unit tests: `tests/unit/ingestion/classification/test_value_type_classifier.py`
- Integration tests: `tests/integration/ingestion/test_classification_integration.py` (extend existing)
- Ground truth: `tests/fixtures/value_type_ground_truth.json`

### Performance Requirements

- Single value classification: <0.1ms (simple regex/lookup)
- Batch classification (1000 items): <100ms
- Memory: O(n) where n is batch size

### File Size Constraints

Per `.claude/rules/file-size-limits.md`:
- Target: 100-250 LOC per file
- Hard limit: 500 LOC
- `value_type_classifier.py` should be ~150 LOC

### Database Schema Constraint

The `value_type` column (from Story 9.1) is VARCHAR(50). Valid values must match:

| ValueType Enum | Database Value |
|----------------|----------------|
| ACTUAL | "actual" |
| BUDGET | "budget" |
| FORECAST | "forecast" |
| VARIANCE | "variance" |
| UNKNOWN | "unknown" |

### References

- [Source: raglite/ingestion/classification/period_classifier.py] - Pattern to follow
- [Source: raglite/ingestion/classification/models.py] - PeriodType enum pattern
- [Source: migrations/007_add_classification_columns.sql] - Database schema (Story 9.1)
- [Source: docs/epics/epic-9-tracking.md] - Epic requirements (90% accuracy target)
- [Source: .claude/rules/testing.md] - Test marker requirements

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
