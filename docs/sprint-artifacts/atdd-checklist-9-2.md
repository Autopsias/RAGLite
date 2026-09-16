# ATDD Checklist - Story 9.2: Period Type Classification + LLM API Resilience

**Story:** 9-2-classification-module-period-type-classification
**Phase:** TDD RED (tests written, some failing as expected)
**Created:** 2026-01-31
**Updated:** 2026-01-31

## Summary

| Metric | Value |
|--------|-------|
| Total Tests Created | 67 |
| Tests Passing | 62 |
| Tests Failing (RED) | 5 |
| ACs Covered | AC1, AC2, AC3, AC4, AC5 |
| Status | **red** (AC4 API resilience tests failing as expected) |

## Test Files

| File | Test Count | ACs Covered | Status |
|------|------------|-------------|--------|
| `tests/acceptance/story_9_2/test_ac1_period_classification_accuracy.py` | 19 | AC1 | PASS |
| `tests/acceptance/story_9_2/test_ac2_regex_pattern_matching.py` | 25 | AC2 | 1 FAIL |
| `tests/acceptance/story_9_2/test_ac3_llm_fallback.py` | 5 | AC3 | PASS |
| `tests/acceptance/story_9_2/test_ac4_api_resilience.py` | 7 | AC4 | 4 FAIL |
| `tests/acceptance/story_9_2/test_ac5_ground_truth_validation.py` | 11 | AC5 | PASS |

**Total Tests:** 67 (57 fast + 10 slow/integration)

## AC Coverage Matrix

### AC1: Period Type Classification with 95%+ Accuracy

| Test ID | Test Name | Priority | Status |
|---------|-----------|----------|--------|
| TEST-AC-9.2.1.1 | `test_ac1_1_ground_truth_accuracy_exceeds_95_percent` | P0 | PASS |
| TEST-AC-9.2.1.2 | `test_ac1_2_portuguese_month_abbreviations[*]` (7 params) | P0 | PASS |
| TEST-AC-9.2.1.3 | `test_ac1_3_four_digit_year_formats[*]` (3 params) | P0 | PASS |
| TEST-AC-9.2.1.4 | `test_ac1_4_normalized_period_extraction[*]` (2 params) | P0 | PASS |
| TEST-AC-9.2.1.5 | `test_ac1_5_is_usable_only_for_actual_types[*]` (6 params) | P0 | PASS |

### AC2: Regex Pattern Matching for Known Formats

| Test ID | Test Name | Priority | Status |
|---------|-----------|----------|--------|
| TEST-AC-9.2.2.1 | `test_ac2_1_regex_matches_before_llm_for_known_format` | P0 | PASS |
| TEST-AC-9.2.2.2 | `test_ac2_2_patterns_handle_all_formats[*]` (12 params) | P0 | PASS |
| TEST-AC-9.2.2.3 | `test_ac2_3_case_insensitive_month_matching[*]` (7 params) | P0 | PASS |
| TEST-AC-9.2.2.4 | `test_ac2_4_classification_within_5s_even_without_llm` | P0 | **RED** |
| TEST-AC-9.2.2.5 | `test_ac2_5_whitespace_handling[*]` (4 params) | P1 | PASS |

### AC3: LLM Fallback for Unknown Formats

| Test ID | Test Name | Priority | Status |
|---------|-----------|----------|--------|
| TEST-AC-9.2.3.1 | `test_ac3_1_uses_mistral_small_model` | P0 | PASS |
| TEST-AC-9.2.3.2 | `test_ac3_2_exponential_backoff_on_api_errors` | P0 | PASS |
| TEST-AC-9.2.3.3 | `test_ac3_3_returns_unknown_after_retries_exhausted` | P0 | PASS |
| TEST-AC-9.2.3.4 | `test_ac3_4_warnings_logged_for_each_retry` | P1 | PASS |
| TEST-AC-9.2.3.5 | `test_ac3_5_error_logged_after_all_retries_exhausted` | P1 | PASS |

### AC4: API Resilience (5s Timeout, Fail-Fast)

| Test ID | Test Name | Priority | Status |
|---------|-----------|----------|--------|
| TEST-AC-9.2.4.1 | `test_ac4_1_single_period_classification_under_5s` | P0 | **RED** |
| TEST-AC-9.2.4.2 | `test_ac4_2_regex_periods_classify_correctly_despite_api_status` | P0 | PASS |
| TEST-AC-9.2.4.3 | `test_ac4_3_non_regex_periods_return_unknown_not_exception` | P0 | PASS |
| TEST-AC-9.2.4.4 | `test_ac4_4_structured_logging_captures_api_failures` | P1 | **RED** |
| TEST-AC-9.2.4.5 | `test_ac4_5_batch_processing_not_blocked_by_api_failures` | P0 | **RED** |
| TEST-AC-9.2.4.6 | `test_ac4_6_timeout_per_period_enforced` | P0 | **RED** |
| TEST-AC-9.2.4.7 | `test_ac4_7_regex_bypass_for_throughput` | P1 | PASS |

### AC5: Ground Truth Validation (50+ Samples)

| Test ID | Test Name | Priority | Status |
|---------|-----------|----------|--------|
| TEST-AC-9.2.5.1 | `test_ac5_1_dataset_contains_50_plus_samples` | P0 | PASS |
| TEST-AC-9.2.5.2 | `test_ac5_2_all_period_types_represented` | P0 | PASS |
| TEST-AC-9.2.5.3 | `test_ac5_3_edge_cases_covered` | P0 | PASS |
| TEST-AC-9.2.5.4 | `test_ac5_4_validation_reports_accuracy_and_failures` | P1 | PASS |
| TEST-AC-9.2.5.5 | `test_ac5_5_accuracy_threshold_configurable[*]` (3 params) | P1 | PASS |
| TEST-AC-9.2.5.6 | `test_all_samples_have_required_fields` | P0 | PASS |
| TEST-AC-9.2.5.7 | `test_expected_types_are_valid_enum_values` | P0 | PASS |
| TEST-AC-9.2.5.8 | `test_normalized_is_null_for_excluded_types` | P1 | PASS |
| TEST-AC-9.2.5.9 | `test_normalized_is_present_for_actual_types` | P1 | PASS |

## Failing Tests Analysis (RED State)

### Root Cause: Exception Propagation in classify_period()

The 5 failing tests all relate to **AC4: API Resilience**. The current implementation in `classify_period()` calls `_classify_with_llm()` but does NOT catch exceptions when LLM fails. This causes:

1. `TimeoutError` and other exceptions to propagate up to the caller
2. Instead of graceful fallback to `UNKNOWN`
3. Blocking the ingestion pipeline on API failures

### Required Fix (for dev-story phase)

In `raglite/ingestion/classification/period_classifier.py`, line ~235:

```python
# Current (broken for AC4):
llm_result = _classify_with_llm(period)

# Required fix:
try:
    llm_result = _classify_with_llm(period)
except Exception as e:
    logger.warning("LLM classification failed", extra={"period": period, "error": str(e)})
    llm_result = PeriodType.UNKNOWN
```

### Test File Locations

All failing tests are in:
- `/Users/ricardocarvalho/DeveloperFolder/RAGLite/tests/acceptance/story_9_2/test_ac2_regex_pattern_matching.py`
- `/Users/ricardocarvalho/DeveloperFolder/RAGLite/tests/acceptance/story_9_2/test_ac4_api_resilience.py`

## Ground Truth Fixture

**File:** `tests/fixtures/period_classification_ground_truth.json`
**Samples:** 65 (exceeds 50+ requirement)

| Period Type | Count |
|-------------|-------|
| monthly_actual | 23 |
| ytd_actual | 11 |
| budget | 7 |
| ytd_budget | 5 |
| unknown | 10 |
| edge cases (case/whitespace) | 9 |

## Run Commands

```bash
# Run fast tests only (will PASS - implementation exists)
uv run pytest tests/acceptance/story_9_2/ -q

# Run ALL tests including slow/integration (5 will FAIL - RED state)
uv run pytest tests/acceptance/story_9_2/ -m "slow or integration" -q

# Run all tests with no marker filtering
uv run pytest tests/acceptance/story_9_2/ -m "" -q --tb=short

# Run specific failing test
uv run pytest tests/acceptance/story_9_2/test_ac4_api_resilience.py -v
```

## Implementation Module Path

Tests expect implementation at:
- `raglite/ingestion/classification/__init__.py` (exports)
- `raglite/ingestion/classification/models.py` (PeriodType, ClassifiedPeriod, ClassificationReport)
- `raglite/ingestion/classification/period_classifier.py` (classify_period, classify_periods_batch, _classify_with_llm)

## Notes

- **Status: RED** - 5 tests failing as expected for TDD RED phase
- Failing tests validate AC4 (API Resilience) which requires exception handling improvement
- AC1, AC2 (partial), AC3, AC5 tests all PASS - implementation mostly complete
- Ground truth accuracy: 95%+ achieved (AC1.1 passes)
- Portuguese months, 4-digit years, whitespace handling all working
- LLM fallback with exponential backoff implemented (AC3 passes)

## Next Steps (dev-story phase)

1. Add try/catch in `classify_period()` to handle `_classify_with_llm()` failures
2. Return `UNKNOWN` on exception instead of propagating
3. Add structured logging for failed classifications
4. Verify all 5 failing tests turn GREEN
5. Update story status to "done" in sprint-status.yaml
