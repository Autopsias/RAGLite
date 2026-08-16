# Story 9.3: Classification Module - Value Type Classification

**Epic:** 9 - Data Quality at Ingestion
**Status:** done
**Estimate:** 0.5 days
**Dependencies:** Story 9.1 (Schema Migration) - DONE, Story 9.2 (Period Type Classification) - DONE

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

---

## Prerequisites

- **Story 9.1 (Schema Migration):** DONE. Classification columns exist in PostgreSQL (period_type, value_type, entity_level).
- **Story 9.2 (Period Type Classification):** DONE. Period classifier module with regex patterns and LLM fallback.

---

## Story

As a data engineer,
I want to classify financial values into value types (actual, budget, forecast, variance, unknown) using regex patterns with period_type integration,
so that the ingestion pipeline can store semantically-classified value data that enables simplified forecasting queries to distinguish between actual historical values and budget/forecast projections.

---

## Context

### Problem Statement

Financial tables contain mixed value types (actual, budget, forecast, variance) that are difficult to distinguish without semantic classification. The forecasting module (Epic 4) requires filtering to actual values only, but currently has no reliable way to identify them. Without classification at ingestion:
- Budget values contaminate forecasting models
- Variance calculations are misinterpreted as actual data
- Forecasts are double-counted or confused with actuals

### Foundation Code (Existing Implementation)

The value type classifier exists at `raglite/ingestion/classification/value_type_classifier.py` (328 LOC) with:
- `ValueType` enum: ACTUAL, BUDGET, FORECAST, VARIANCE, UNKNOWN
- `ClassifiedValueType` dataclass with original, value_type, source fields
- `classify_value_type()` function with regex patterns and header integration
- `classify_value_types_batch()` with LRU caching (10,000 entries)
- `ValueTypeReport` dataclass for reporting

### Classification Hierarchy

The existing implementation uses a priority hierarchy:
0. Empty/whitespace/unknown patterns -> UNKNOWN
1. PeriodType (if provided): BUDGET/YTD_BUDGET -> BUDGET, MONTHLY_ACTUAL/YTD_ACTUAL -> ACTUAL
2. Period prefix/keywords: "B ", "Budget", "F ", "Forecast", "Var", "Variance", etc.
3. Column header (secondary): "Budget", "Forecast", "Variance", "Actual"
4. Default: ACTUAL (no modifiers present)

### Ground Truth Dataset

`tests/fixtures/value_type_ground_truth.json` contains 51 test cases covering:
- Actual values (8 samples): Plain periods (Dec-21, Jan-25), "Actual" keyword, Portuguese "Real" keyword
- Budget values (10 samples): "B " prefix, "Budget" keyword, Portuguese "Orcamento/Plano", trailing "B"
- Forecast values (10 samples): "F " prefix, "Forecast" keyword, Portuguese "Previsao", "Projected"
- Variance values (10 samples): "Var", "%Var", "Delta", "Variance", Portuguese "Variacao", "Diff"
- Unknown values (5 samples): Empty, N/A, invalid, year-only, None literal
- Edge cases (8 samples): Header conflicts, whitespace, case variations

### Risk Mitigation

Per Test Design (`docs/test-design-epic-9.md`):
- **R-001 (Score: 6):** LLM classification accuracy <95% on edge cases
  - Mitigation: Ground truth validation, regex-only classification (no LLM needed for value_type)

---

## Acceptance Criteria

### AC1: Value Type Classification with 90%+ Accuracy

**Given** a list of period strings and optional headers from financial tables
**When** classifying value types using `classify_value_type()` or `classify_value_types_batch()`
**Then**:
- [ ] AC1.1: Returns correct ValueType for 90%+ of ground truth samples (51 samples, need 46+)
- [ ] AC1.2: Classifies Portuguese keywords correctly (Orcamento, Previsao, Variacao, Real)
- [ ] AC1.3: Handles budget prefix/suffix patterns (B Dec-21, Dec-21 B)
- [ ] AC1.4: Handles forecast prefix patterns (F Dec-21, Forecast Dec-21)
- [ ] AC1.5: Handles variance patterns (%Var, Delta, Diff)
- [ ] AC1.6: Defaults to ACTUAL for plain periods without modifiers

**BDD Scenarios:**

```gherkin
Scenario: Classify plain period as actual
  Given the period string "Dec-21"
  And no header provided
  When classify_value_type() is called
  Then value_type is ACTUAL
  And source is "default"

Scenario: Classify budget prefix period
  Given the period string "B Dec-21"
  When classify_value_type() is called
  Then value_type is BUDGET
  And source is "period_prefix"

Scenario: Classify Portuguese budget keyword
  Given the period string "Orcamento Mar-25"
  When classify_value_type() is called
  Then value_type is BUDGET
  And source is "period_prefix"

Scenario: Classify forecast prefix period
  Given the period string "F Jun-24"
  When classify_value_type() is called
  Then value_type is FORECAST
  And source is "period_prefix"

Scenario: Classify variance pattern
  Given the period string "Var Dec-21"
  When classify_value_type() is called
  Then value_type is VARIANCE
  And source is "period_prefix"

Scenario: Ground truth validation passes at 90%+
  Given the ground truth dataset with 51 samples
  When validating classification accuracy
  Then at least 46 samples are correctly classified (90%+)
```

### AC2: PeriodType Integration

**Given** a period string with a corresponding PeriodType from period_classifier
**When** classifying value types with period_type parameter
**Then**:
- [ ] AC2.1: PeriodType.BUDGET or PeriodType.YTD_BUDGET maps to ValueType.BUDGET
- [ ] AC2.2: PeriodType.MONTHLY_ACTUAL or PeriodType.YTD_ACTUAL maps to ValueType.ACTUAL
- [ ] AC2.3: PeriodType.UNKNOWN does not force ValueType (falls through to other rules)
- [ ] AC2.4: PeriodType takes precedence over period prefix when both present

**BDD Scenarios:**

```gherkin
Scenario: PeriodType.BUDGET overrides period analysis
  Given the period string "Dec-21"
  And period_type is PeriodType.BUDGET
  When classify_value_type() is called
  Then value_type is BUDGET
  And source is "period_type"

Scenario: PeriodType takes precedence over conflicting prefix
  Given the period string "F Dec-21" (forecast prefix)
  And period_type is PeriodType.BUDGET
  When classify_value_type() is called
  Then value_type is BUDGET
  And source is "period_type"
```

### AC3: Column Header Context

**Given** a period string with a column header for context
**When** classifying value types with header parameter
**Then**:
- [ ] AC3.1: Header "Forecast" classifies as FORECAST when no period prefix
- [ ] AC3.2: Header "Budget" classifies as BUDGET when no period prefix
- [ ] AC3.3: Period prefix overrides conflicting header (B Dec-21 + "Forecast" header = BUDGET)
- [ ] AC3.4: Portuguese header keywords work (Orcamento, Previsao)

**BDD Scenarios:**

```gherkin
Scenario: Header provides context when period is plain
  Given the period string "Dec-21"
  And header is "Forecast"
  When classify_value_type() is called
  Then value_type is FORECAST
  And source is "column_header"

Scenario: Period prefix overrides conflicting header
  Given the period string "B Dec-21"
  And header is "Forecast"
  When classify_value_type() is called
  Then value_type is BUDGET
  And source is "period_prefix"
```

### AC4: Unknown Value Handling

**Given** period strings that cannot be classified
**When** classifying invalid or empty inputs
**Then**:
- [ ] AC4.1: Empty strings return UNKNOWN with source "empty"
- [ ] AC4.2: "N/A", "None", "null" markers return UNKNOWN with source "unknown_marker"
- [ ] AC4.3: Invalid formats (year-only like "2021") return UNKNOWN with source "invalid_format"
- [ ] AC4.4: Classification never raises exceptions for malformed inputs

**BDD Scenarios:**

```gherkin
Scenario: Empty string returns unknown
  Given the period string ""
  When classify_value_type() is called
  Then value_type is UNKNOWN
  And source is "empty"

Scenario: N/A marker returns unknown
  Given the period string "N/A"
  When classify_value_type() is called
  Then value_type is UNKNOWN
  And source is "unknown_marker"

Scenario: Year-only format returns unknown
  Given the period string "2021"
  When classify_value_type() is called
  Then value_type is UNKNOWN
  And source is "invalid_format"
```

### AC5: Batch Processing Performance

**Given** a batch of period strings to classify
**When** using classify_value_types_batch()
**Then**:
- [ ] AC5.1: Returns list of ClassifiedValueType matching input order
- [ ] AC5.2: Returns ValueTypeReport with accurate counts
- [ ] AC5.3: LRU cache provides <100ms for 1000 duplicate periods
- [ ] AC5.4: Handles None headers and period_types gracefully

**BDD Scenarios:**

```gherkin
Scenario: Batch classification with report
  Given a list of 100 periods ["Dec-21", "B Jan-22", "F Mar-23", ...]
  When classify_value_types_batch() is called
  Then results list has 100 ClassifiedValueType entries
  And report.total_records equals 100
  And report.value_type_breakdown sums to 100

Scenario: Cached batch performance
  Given a list of 1000 identical periods ["Dec-21", "Dec-21", ...]
  When classify_value_types_batch() is called
  Then classification completes in <100ms
```

---

## Tasks / Subtasks

### Task 1: Validate Existing Implementation Against Ground Truth (AC1) - 0.15 day

- [ ] 1.1: Create `tests/integration/test_value_type_classification_accuracy.py`
- [ ] 1.2: Load ground truth from `tests/fixtures/value_type_ground_truth.json`
- [ ] 1.3: Run classification on all 51 samples
- [ ] 1.4: Assert 90%+ accuracy (46+ correct)
- [ ] 1.5: Output detailed failure report for any misclassifications
- [ ] 1.6: Mark as P0 test (critical path per test design)

### Task 2: Add Unit Tests for Value Type Patterns (AC1, AC2, AC3, AC4) - 0.15 day

- [ ] 2.1: Create/update `tests/unit/ingestion/classification/test_value_type_classifier.py`
- [ ] 2.2: Test Portuguese keyword mapping (Orcamento, Previsao, Variacao)
- [ ] 2.3: Test budget prefix/suffix patterns (B Dec-21, Dec-21 B)
- [ ] 2.4: Test forecast patterns (F Dec-21, Forecast Dec-21, Projected)
- [ ] 2.5: Test variance patterns (%Var, Delta, Diff, Variance)
- [ ] 2.6: Test PeriodType integration (AC2)
- [ ] 2.7: Test header context (AC3)
- [ ] 2.8: Test unknown handling (AC4)
- [ ] 2.9: Ensure 80%+ test coverage for value_type_classifier.py

### Task 3: Add Batch Processing Tests (AC5) - 0.1 day

- [ ] 3.1: Test batch classification with mixed value types
- [ ] 3.2: Test ValueTypeReport accuracy
- [ ] 3.3: Test cache performance (<100ms for 1000 duplicates)
- [ ] 3.4: Test input validation (mismatched list lengths)
- [ ] 3.5: Test None handling for headers and period_types

### Task 4: Fix Any Failing Tests (if needed) - 0.05 day

- [ ] 4.1: Analyze any ground truth failures
- [ ] 4.2: Adjust regex patterns if accuracy <90%
- [ ] 4.3: Add missing edge case handling
- [ ] 4.4: Re-run validation to confirm 90%+ accuracy

### Task 5: Documentation and Finalization - 0.05 day

- [ ] 5.1: Verify docstrings with examples for public functions
- [ ] 5.2: Update `raglite/ingestion/classification/__init__.py` exports if needed
- [ ] 5.3: Run full test suite: `pytest tests/ -v --tb=short`
- [ ] 5.4: Verify all acceptance criteria are met
- [ ] 5.5: Update story status to "done" in sprint-status.yaml

---

## Technical Design

### File Structure

```
raglite/ingestion/classification/
  __init__.py                     # Exports (update if needed)
  models.py                       # ValueType, ClassifiedValueType, etc. (existing)
  period_classifier.py            # Story 9.2 (existing)
  value_type_classifier.py        # classify_value_type(), classify_value_types_batch() (existing, 328 LOC)

tests/unit/ingestion/classification/
  test_value_type_classifier.py   # Unit tests (create)

tests/integration/
  test_value_type_classification_accuracy.py  # Ground truth validation (create)

tests/fixtures/
  value_type_ground_truth.json    # 51 samples (existing)
```

### Existing classify_value_type() Function

```python
def classify_value_type(
    period: str,
    header: str | None = None,
    period_type: PeriodType | None = None,
) -> ClassifiedValueType:
    """Classify a period string into its value type.

    Classification hierarchy (checked first to last):
    0. Empty/whitespace/unknown patterns -> UNKNOWN
    1. period_type (if provided): BUDGET/YTD_BUDGET -> BUDGET, MONTHLY_ACTUAL/YTD_ACTUAL -> ACTUAL
    2. Period prefix/keywords: "B ", "Budget", "F ", "Forecast", "Var", "Variance", etc.
    3. Column header (secondary): "Budget", "Forecast", "Variance", "Actual"
    4. Default: ACTUAL (no modifiers present)
    """
```

### Ground Truth Validation Test

```python
# tests/integration/test_value_type_classification_accuracy.py
import json
import pytest
from raglite.ingestion.classification import classify_value_type

GROUND_TRUTH_PATH = "tests/fixtures/value_type_ground_truth.json"
ACCURACY_THRESHOLD = 0.90

@pytest.mark.integration
def test_value_type_classification_accuracy():
    """Validate value type classification against ground truth (AC1, P0)."""
    with open(GROUND_TRUTH_PATH) as f:
        ground_truth = json.load(f)

    correct = 0
    failures = []

    for sample in ground_truth:
        period = sample["period"]
        header = sample.get("header")
        expected_type = sample["expected_value_type"]

        result = classify_value_type(period, header=header)

        if result.value_type.value == expected_type:
            correct += 1
        else:
            failures.append({
                "period": period,
                "header": header,
                "expected": expected_type,
                "actual": result.value_type.value,
                "source": result.source,
            })

    accuracy = correct / len(ground_truth)

    # Log failures for debugging
    if failures:
        for f in failures:
            print(f"FAIL: {f}")

    assert accuracy >= ACCURACY_THRESHOLD, (
        f"Accuracy {accuracy:.2%} below threshold {ACCURACY_THRESHOLD:.0%}. "
        f"Failures: {len(failures)}/{len(ground_truth)}"
    )
```

---

## Dev Notes

### Implementation Status

The value_type_classifier.py is **already implemented** (328 LOC) with:
- Full regex pattern matching for all value types
- Portuguese keyword support (Orcamento, Previsao, Variacao, Real)
- PeriodType integration (highest priority)
- Header context (secondary priority)
- LRU cache for batch performance
- ValueTypeReport for analytics

### This Story's Focus

This story focuses on **validation and testing**, not implementation:
1. Create ground truth validation tests (P0)
2. Create comprehensive unit tests
3. Verify 90%+ accuracy threshold is met
4. Fix any edge cases that fail validation

### Test Design Reference

From `docs/test-design-epic-9.md`:
- **P0 Test:** Value type classification >=90% accuracy (Integration, 1min)
- **P1 Test:** Budget vs actual detection from context clues (Unit)

### Architecture Reference

Per `docs/architecture/6-complete-reference-implementation.md`:
- Use direct SDK calls (no wrappers)
- Structured logging with `extra={}` for context
- Pydantic models for data validation (using dataclasses, acceptable)

### Testing Guidelines Reference

Per `tests/CLAUDE.md`:
- Tests >1s should have `@pytest.mark.slow`
- Integration tests need `@pytest.mark.integration`
- Keep unit tests fast (<100ms)

---

## Testing Requirements

### Unit Tests (Fast, No External Dependencies)

| Test Case | Priority | AC Link |
|-----------|----------|---------|
| Plain period defaults to ACTUAL | P1 | AC1.6 |
| Budget prefix "B " detection | P1 | AC1.3 |
| Budget suffix " B" detection | P1 | AC1.3 |
| Forecast prefix "F " detection | P1 | AC1.4 |
| Forecast keyword detection | P1 | AC1.4 |
| Variance pattern detection | P1 | AC1.5 |
| Portuguese keyword mapping | P1 | AC1.2 |
| PeriodType.BUDGET integration | P1 | AC2.1 |
| PeriodType precedence over prefix | P1 | AC2.4 |
| Header context when no prefix | P1 | AC3.1 |
| Prefix overrides conflicting header | P1 | AC3.3 |
| Empty string handling | P1 | AC4.1 |
| N/A marker handling | P1 | AC4.2 |
| Invalid format handling | P1 | AC4.3 |
| Case-insensitive matching | P1 | AC1 |
| Whitespace normalization | P1 | AC1 |

### Integration Tests

| Test Case | Priority | AC Link | Marker |
|-----------|----------|---------|--------|
| Ground truth 90%+ accuracy | P0 | AC1 | `@pytest.mark.integration` |
| Batch classification correctness | P1 | AC5.1 | `@pytest.mark.integration` |
| ValueTypeReport accuracy | P1 | AC5.2 | `@pytest.mark.integration` |

### Performance Tests

| Test Case | Priority | AC Link | Marker |
|-----------|----------|---------|--------|
| Cache performance <100ms for 1000 | P2 | AC5.3 | `@pytest.mark.slow` |

### Coverage Targets

- `value_type_classifier.py`: >80% coverage
- All public functions have docstrings
- All acceptance criteria have at least one test

---

## References

- [Epic 9 Tracking](../../epics/epic-9-tracking.md) - Parent epic
- [Story 9.1 (Schema Migration)](../../implementation-artifacts/9-1-schema-migration-add-classification-columns.md) - Dependency (DONE)
- [Story 9.2 (Period Type Classification)](./9-2-classification-module-period-type-classification.md) - Sibling story (DONE)
- [Test Design Epic 9](../../test-design-epic-9.md) - Test strategy, risk assessment
- [Ground Truth Dataset](../../../tests/fixtures/value_type_ground_truth.json) - 51 validation samples
- [Value Type Classifier Source](../../../raglite/ingestion/classification/value_type_classifier.py) - Implementation file (328 LOC)
- [Database Safety Rules](../../../.claude/rules/database-safety.md) - Production protection

---

## Dev Agent Record

### Agent Model Used

(To be filled by implementing agent)

### Debug Log References

(To be filled by implementing agent)

### Completion Notes List

(To be filled by implementing agent)

### File List

**Files to Create:**
- `tests/unit/ingestion/classification/test_value_type_classifier.py` (~200 LOC)
- `tests/integration/test_value_type_classification_accuracy.py` (~60 LOC)

**Files to Update (if tests fail):**
- `raglite/ingestion/classification/value_type_classifier.py` (~5-20 LOC fixes)

**Total New/Modified Code:** ~260-280 LOC
