# Story 9.2: Classification Module - Period Type Classification + LLM API Resilience

**Epic:** 9 - Data Quality at Ingestion
**Status:** done
**Estimate:** 1.5 days
**Dependencies:** Story 9.1 (Schema Migration) - DONE

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

---

## Prerequisites

- **Story 9.1 (Schema Migration):** DONE. Classification columns exist in PostgreSQL (period_type, value_type, entity_level).

---

## Story

As a data engineer,
I want to classify period strings into period types (monthly_actual, ytd_actual, budget, ytd_budget, unknown) using regex patterns with LLM fallback,
so that the ingestion pipeline can store semantically-classified period data that enables simplified forecasting queries without complex normalization logic.

---

## Context

### Problem Statement

The forecasting module (Epic 4) is blocked by data quality issues. Period strings in financial tables come in 30+ format variants (Portuguese months, 4-digit years, YTD prefixes, budget indicators). Without classification at ingestion, forecasting queries require complex normalization logic, leading to:
- 99.3% data loss in GROUP EBITDA extraction (2/292 records usable)
- 50+ LOC of period normalization in forecasting module
- Inconsistent handling of budget vs actual data

### Foundation Code (Commit 58fbc9e)

The following exists in `raglite/ingestion/classification/`:
- `PeriodType` enum with 5 values: MONTHLY_ACTUAL, YTD_ACTUAL, BUDGET, YTD_BUDGET, UNKNOWN
- `ClassifiedPeriod` dataclass with original, period_type, normalized, is_usable fields
- `classify_period()` function with regex patterns for known formats
- `_classify_with_llm()` function with exponential backoff (1s, 2s, 4s)
- `classify_periods_batch()` with LRU caching (10,000 entries)
- `ClassificationReport` dataclass for reporting

### Ground Truth Dataset

`tests/fixtures/period_classification_ground_truth.json` contains 67 test cases covering:
- English months (Dec-21, Jan-25)
- Portuguese months (Dez-21, Fev-24, Abr-23, Mai-22, Ago-21, Set-20, Out-19)
- 4-digit years (Dec-2017, Jan-2025, Dez-2021)
- YTD prefixes (YTD Dec-21, YTD Sep-25)
- Budget prefixes (B Dec-21, Dec-21 B, Jan B 25)
- YTD Budget (YTD B Dec-21)
- Unknown formats (empty, N/A, 2017 P, Q1 2021, FY2021)
- Case variations (dec-21, DeC-21, FEV-24)
- Whitespace handling (trailing tabs, leading tabs, NBSP)

### Risk Mitigation

Per Test Design (`docs/test-design-epic-9.md`):
- **R-001 (Score: 6):** LLM classification accuracy <95% on edge cases
  - Mitigation: Ground truth validation, regex fallbacks, iterative prompt tuning
- **R-007 (Score: 6):** LLM API unavailable/rate-limited blocks ingestion
  - Mitigation: **Fail-fast regex fallback within 5s**, no retries during batch, AC2.4 validation

---

## Acceptance Criteria

### AC1: Period Type Classification with 95%+ Accuracy

**Given** a list of period strings from financial tables
**When** classifying periods using `classify_period()` or `classify_periods_batch()`
**Then**:
- [ ] AC1.1: Returns correct PeriodType for 95%+ of ground truth samples (67 samples)
- [ ] AC1.2: Classifies Portuguese month abbreviations correctly (Dez, Fev, Abr, Mai, Ago, Set, Out)
- [ ] AC1.3: Handles 4-digit year formats (2024 -> 24, Dec-2017 -> Dec-17)
- [ ] AC1.4: Extracts normalized period (Mon-YY format) for usable types
- [ ] AC1.5: Sets `is_usable=True` only for MONTHLY_ACTUAL and YTD_ACTUAL

**BDD Scenarios:**

```gherkin
Scenario: Classify English monthly actual period
  Given the period string "Dec-21"
  When classify_period() is called
  Then period_type is MONTHLY_ACTUAL
  And normalized is "Dec-21"
  And is_usable is True

Scenario: Classify Portuguese monthly actual period
  Given the period string "Dez-21"
  When classify_period() is called
  Then period_type is MONTHLY_ACTUAL
  And normalized is "Dec-21"
  And is_usable is True

Scenario: Classify 4-digit year format
  Given the period string "Dec-2017"
  When classify_period() is called
  Then period_type is MONTHLY_ACTUAL
  And normalized is "Dec-17"
  And is_usable is True

Scenario: Classify YTD actual period
  Given the period string "YTD Dec-21"
  When classify_period() is called
  Then period_type is YTD_ACTUAL
  And normalized is "Dec-21"
  And is_usable is True

Scenario: Classify budget period with prefix
  Given the period string "B Dec-21"
  When classify_period() is called
  Then period_type is BUDGET
  And normalized is None
  And is_usable is False

Scenario: Classify budget period with suffix
  Given the period string "Dec-21 B"
  When classify_period() is called
  Then period_type is BUDGET
  And normalized is None
  And is_usable is False

Scenario: Ground truth validation passes at 95%+
  Given the ground truth dataset with 67 samples
  When validating classification accuracy
  Then at least 64 samples are correctly classified (95.5%+)
```

### AC2: Regex Pattern Matching for Known Formats

**Given** the need for deterministic classification without LLM dependency
**When** classifying periods with known formats
**Then**:
- [ ] AC2.1: Regex patterns match BEFORE LLM fallback is attempted
- [ ] AC2.2: Patterns handle: Mon-YY, Mon-YYYY, YTD Mon-YY, B Mon-YY, YTD B Mon-YY, Mon-YY B
- [ ] AC2.3: Patterns are case-insensitive for month abbreviations
- [ ] AC2.4: Classification completes within 5s even when LLM API is unavailable (R-007 mitigation)

**BDD Scenarios:**

```gherkin
Scenario: Regex matches before LLM for known format
  Given a period string "Dec-21" that matches regex pattern
  When classify_period() is called
  Then the result is returned without calling the LLM API
  And classification time is <100ms

Scenario: Case-insensitive month matching
  Given the period strings ["dec-21", "DEC-21", "DeC-21"]
  When classify_period() is called on each
  Then all return period_type MONTHLY_ACTUAL
  And all return normalized "Dec-21"

Scenario: Whitespace handling
  Given period strings with trailing tabs, leading tabs, or NBSP
  When classify_period() is called
  Then classification succeeds with correct type
  And whitespace is stripped from normalized output
```

### AC3: LLM Fallback for Unknown Formats

**Given** a period string that does not match any regex pattern
**When** the LLM fallback is invoked
**Then**:
- [ ] AC3.1: Uses Mistral Small model for classification
- [ ] AC3.2: Implements exponential backoff (1s, 2s) on API errors
- [ ] AC3.3: Returns UNKNOWN after 2 failed retries (reduced from 3 for 5s timeout compliance)
- [ ] AC3.4: Logs warnings for each retry attempt with period and error
- [ ] AC3.5: Logs error after all retries exhausted

**BDD Scenarios:**

```gherkin
Scenario: LLM fallback for ambiguous format
  Given a period string "Q1 2021" that does not match regex
  When classify_period() is called
  Then the LLM fallback is invoked
  And the result reflects LLM classification (likely UNKNOWN)

Scenario: LLM retry with exponential backoff
  Given the LLM API returns 429 rate limit error
  When classify_period() is called
  Then retry 1 occurs after 1s delay
  And retry 2 occurs after 2s delay
  And UNKNOWN is returned after 2 retries fail (5s timeout compliance)
```

### AC4: API Resilience (5s Timeout, Fail-Fast to Regex)

**Given** the LLM API is unavailable (429, 503, timeout)
**When** classifying periods in batch
**Then**:
- [ ] AC4.1: Total classification time for any single period is <5s
- [ ] AC4.2: Regex-matchable periods classify correctly regardless of API status
- [ ] AC4.3: Non-regex periods return UNKNOWN (not hang or raise exception)
- [ ] AC4.4: Structured logging captures API failures with context
- [ ] AC4.5: Ingestion pipeline continues (not blocked by API failures)

**BDD Scenarios:**

```gherkin
Scenario: Fail-fast when LLM API unavailable (R-007)
  Given the LLM API is returning 503 Service Unavailable
  And a batch of 100 periods with 90 regex-matchable and 10 ambiguous
  When classify_periods_batch() is called
  Then 90 periods are classified correctly via regex
  And 10 periods return UNKNOWN within 5s each
  And total batch time is <60s (not 10 * full retry timeout)

Scenario: Timeout protection per period
  Given an ambiguous period "ambiguous-format-xyz"
  And the LLM API times out on every call
  When classify_period() is called
  Then the function returns within 15s maximum (3 retries * 4s + overhead)
  And result is UNKNOWN
  And warning logs are emitted

Scenario: Regex bypass protects throughput
  Given a batch of 1000 periods with 990 regex-matchable
  When classify_periods_batch() is called
  Then batch completes in <500ms (per caching target)
  And no LLM calls are made for regex-matchable periods
```

### AC5: Ground Truth Validation (50+ Samples)

**Given** the ground truth dataset at `tests/fixtures/period_classification_ground_truth.json`
**When** running the validation test
**Then**:
- [ ] AC5.1: Dataset contains 67 samples (exceeds 50+ requirement)
- [ ] AC5.2: All PeriodType values are represented (MONTHLY_ACTUAL, YTD_ACTUAL, BUDGET, YTD_BUDGET, UNKNOWN)
- [ ] AC5.3: Edge cases are covered (Portuguese months, case variations, whitespace)
- [ ] AC5.4: Validation script reports accuracy percentage and failure details
- [ ] AC5.5: Accuracy threshold is configurable (default: 95%)

**BDD Scenarios:**

```gherkin
Scenario: Ground truth validation passes
  Given the ground truth dataset with 67 samples
  When running pytest tests/integration/test_classification_integration.py
  Then the test passes with 95%+ accuracy
  And failure details (if any) are logged with period, expected, and actual

Scenario: Validation script output
  Given the ground truth validation runs
  When the script completes
  Then output includes:
    | Metric | Value |
    | Total samples | 67 |
    | Correct | >= 64 |
    | Accuracy | >= 95.5% |
    | Failures | Listed with details |
```

---

## Tasks / Subtasks

### Task 1: Enhance Regex Patterns (AC2) - 0.5 day

- [ ] 1.1: Add regex pattern for Mon-YYYY format (AC2.2)
- [ ] 1.2: Add regex pattern for " B " mid-string budget indicator (AC2.2)
- [ ] 1.3: Verify case-insensitivity with explicit tests (AC2.3)
- [ ] 1.4: Add NBSP and tab whitespace handling in normalization (AC2.2)
- [ ] 1.5: Document all regex patterns with examples in docstrings

### Task 2: Implement API Resilience (AC4) - 0.5 day

- [ ] 2.1: Add 5s per-call timeout to LLM client (AC4.1)
- [ ] 2.2: Reduce max_retries to 2 (total time: 1s + 2s + 5s = 8s max) (AC4.1)
- [ ] 2.3: Add structured logging for API failures with context (AC4.4)
- [ ] 2.4: Ensure exceptions are caught and UNKNOWN returned (AC4.3)
- [ ] 2.5: Add timeout logging with period context

### Task 3: Add Unit Tests for Patterns (AC1, AC2) - 0.25 day

- [ ] 3.1: Create/update `tests/unit/ingestion/classification/test_period_classifier.py`
- [ ] 3.2: Test all Portuguese month abbreviations (AC1.2)
- [ ] 3.3: Test 4-digit year conversion (AC1.3)
- [ ] 3.4: Test case-insensitive matching (AC2.3)
- [ ] 3.5: Test whitespace normalization (AC2.4)
- [ ] 3.6: Test budget prefix/suffix variations (AC1.5)
- [ ] 3.7: Ensure 80%+ test coverage for period_classifier.py

### Task 4: Add Integration Tests for API Resilience (AC3, AC4) - 0.25 day

- [ ] 4.1: Create/update `tests/integration/ingestion/test_classification_integration.py`
- [ ] 4.2: Test LLM fallback invocation (mock LLM, verify call) (AC3.1)
- [ ] 4.3: Test exponential backoff timing (AC3.2)
- [ ] 4.4: Test 5s timeout enforcement (AC4.1)
- [ ] 4.5: Test batch processing with mixed API failures (AC4.5)
- [ ] 4.6: Mark slow tests with `@pytest.mark.slow` per test guidelines

### Task 5: Ground Truth Validation Tests (AC5) - 0.25 day

- [ ] 5.1: Create `tests/integration/test_period_classification_accuracy.py`
- [ ] 5.2: Load ground truth from `tests/fixtures/period_classification_ground_truth.json`
- [ ] 5.3: Run classification on all samples (AC5.1)
- [ ] 5.4: Assert 95%+ accuracy (AC5.5)
- [ ] 5.5: Output detailed failure report (AC5.4)
- [ ] 5.6: Mark as P0 test (critical path per test design)

### Task 6: Documentation and Finalization - 0.25 day

- [ ] 6.1: Update `raglite/ingestion/classification/__init__.py` exports if needed
- [ ] 6.2: Add docstrings with examples for public functions
- [ ] 6.3: Verify all acceptance criteria are met
- [ ] 6.4: Run full test suite: `pytest tests/ -v --tb=short`
- [ ] 6.5: Update story status to "done" in sprint-status.yaml

---

## Technical Design

### File Structure

```
raglite/ingestion/classification/
  __init__.py               # Exports (existing)
  models.py                 # PeriodType, ClassifiedPeriod, etc. (existing)
  period_classifier.py      # classify_period(), classify_periods_batch() (enhance)
  value_type_classifier.py  # Story 9.3

tests/unit/ingestion/classification/
  test_period_classifier.py # Unit tests (create/enhance)

tests/integration/ingestion/
  test_classification_integration.py  # LLM fallback tests (existing, enhance)
  test_period_classification_accuracy.py  # Ground truth validation (create)

tests/fixtures/
  period_classification_ground_truth.json  # 67 samples (existing)
```

### API Resilience Changes

Current implementation (`period_classifier.py`):
```python
def _classify_with_llm(period: str) -> PeriodType:
    max_retries = 3
    delays = [1, 2, 4]  # Total worst case: 7s
```

Updated implementation:
```python
def _classify_with_llm(period: str, timeout: float = 5.0) -> PeriodType:
    max_retries = 2  # Reduced from 3
    delays = [1, 2]  # Total worst case: 3s + 5s timeout = 8s max

    for attempt in range(max_retries):
        try:
            client = get_mistral_client()
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[...],
                temperature=0.0,
                timeout=timeout,  # Add timeout
            )
            # ... rest of implementation
        except TimeoutError:
            logger.warning("LLM timeout", extra={"period": period, "timeout": timeout})
```

### Ground Truth Validation Test

```python
# tests/integration/test_period_classification_accuracy.py
import json
import pytest
from raglite.ingestion.classification import classify_period

GROUND_TRUTH_PATH = "tests/fixtures/period_classification_ground_truth.json"
ACCURACY_THRESHOLD = 0.95

@pytest.mark.integration
def test_period_classification_accuracy():
    """Validate period classification against ground truth (AC5, P0)."""
    with open(GROUND_TRUTH_PATH) as f:
        ground_truth = json.load(f)

    correct = 0
    failures = []

    for sample in ground_truth:
        period = sample["period"]
        expected_type = sample["expected_type"]
        expected_normalized = sample.get("expected_normalized")

        result = classify_period(period)

        type_match = result.period_type.value == expected_type
        norm_match = result.normalized == expected_normalized

        if type_match and norm_match:
            correct += 1
        else:
            failures.append({
                "period": period,
                "expected_type": expected_type,
                "actual_type": result.period_type.value,
                "expected_normalized": expected_normalized,
                "actual_normalized": result.normalized,
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

### Foundation Code Reference

The period classifier at `raglite/ingestion/classification/period_classifier.py` (314 LOC) provides:
- `classify_period()` - Main classification function (lines 136-252)
- `_classify_with_llm()` - LLM fallback with retries (lines 61-133)
- `_classify_cached()` - LRU cache wrapper (lines 256-266)
- `classify_periods_batch()` - Batch processing with caching (lines 269-313)
- `PORTUGUESE_MONTH_MAP` - Translation dictionary (lines 22-30)

### Regex Pattern Reference

Current patterns (from period_classifier.py):
1. YTD Budget: `^YTD\s+B\s` (line 171)
2. Budget prefix: `^B\s` (line 180)
3. Budget mid-string: `\sB\s` (line 187)
4. Budget suffix: `\sB$` (line 194)
5. YTD Actual: `^YTD\s+([A-Za-z]{3})-(\d{2,4})$` (line 203)
6. Monthly Actual: `^([A-Za-z]{3})-(\d{2,4})$` (line 218)

### Test Design Reference

From `docs/test-design-epic-9.md`:
- **P0 Test:** Period type classification >=95% accuracy (Integration, 2min)
- **P1 Test:** Period normalization handles Portuguese months (Unit, part of 5min)
- **P1 Test:** Period normalization handles 4-digit years (Unit, part of 5min)
- **P1 Test:** LLM fallback triggers when regex patterns fail (Unit, 2min)
- **P0 Test (R-007):** Regex fallback within 5s when LLM API unavailable (Integration, 1min)

### Architecture Reference

Per `docs/architecture/6-complete-reference-implementation.md`:
- Use direct SDK calls (no wrappers beyond existing patterns)
- Structured logging with `extra={}` for context
- Async patterns for I/O operations (LLM calls)
- Pydantic models for data validation (already using dataclasses, acceptable)

### Testing Guidelines Reference

Per `tests/CLAUDE.md`:
- Tests >1s should have `@pytest.mark.slow`
- Integration tests need `@pytest.mark.integration`
- LLM-dependent tests should mock external calls in unit tests
- Real LLM tests in integration tests (may be slow)

---

## Testing Requirements

### Unit Tests (Fast, No External Dependencies)

| Test Case | Priority | AC Link |
|-----------|----------|---------|
| Portuguese month abbreviation mapping | P1 | AC1.2 |
| 4-digit year to 2-digit conversion | P1 | AC1.3 |
| Regex pattern: Monthly actual | P1 | AC2.2 |
| Regex pattern: YTD actual | P1 | AC2.2 |
| Regex pattern: Budget prefix | P1 | AC2.2 |
| Regex pattern: Budget suffix | P1 | AC2.2 |
| Case-insensitive matching | P1 | AC2.3 |
| Whitespace normalization | P1 | AC2.4 |
| Unknown format handling | P2 | AC1.1 |

### Integration Tests (May Use External Services)

| Test Case | Priority | AC Link | Marker |
|-----------|----------|---------|--------|
| Ground truth 95%+ accuracy | P0 | AC5 | `@pytest.mark.integration` |
| LLM fallback invocation (mocked) | P1 | AC3.1 | `@pytest.mark.integration` |
| 5s timeout enforcement | P0 | AC4.1 | `@pytest.mark.integration`, `@pytest.mark.slow` |
| Batch with API failures | P1 | AC4.5 | `@pytest.mark.integration` |

### Coverage Targets

- `period_classifier.py`: >80% coverage
- All public functions have docstrings
- All acceptance criteria have at least one test

---

## References

- [Epic 9 Tracking](../../epics/epic-9-tracking.md) - Parent epic
- [Story 9.1 (Schema Migration)](../../implementation-artifacts/9-1-schema-migration-add-classification-columns.md) - Dependency (DONE)
- [Test Design Epic 9](../../test-design-epic-9.md) - Test strategy, risk assessment
- [Ground Truth Dataset](../../../tests/fixtures/period_classification_ground_truth.json) - 67 validation samples
- [Period Classifier Source](../../../raglite/ingestion/classification/period_classifier.py) - Implementation file
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

**Files to Modify:**
- `raglite/ingestion/classification/period_classifier.py` (~20 LOC changes for timeout)

**Files to Create:**
- `tests/unit/ingestion/classification/test_period_classifier.py` (~200 LOC)
- `tests/integration/test_period_classification_accuracy.py` (~80 LOC)

**Files to Update:**
- `tests/integration/ingestion/test_classification_integration.py` (add API resilience tests)

**Total New/Modified Code:** ~300 LOC
