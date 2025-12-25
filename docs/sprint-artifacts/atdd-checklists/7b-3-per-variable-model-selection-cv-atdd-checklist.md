# ATDD Checklist: Story 7b-3 - Per-Variable Model Selection via Cross-Validation

**Story ID:** 7b-3
**Status:** RED (Tests Created - Awaiting Implementation)
**Test File:** `tests/integration/test_model_selection.py`
**Implementation File:** `raglite/forecasting/model_selection.py` (TO BE CREATED)

---

## Summary

| Acceptance Criteria | Test Count | Status |
|---------------------|------------|--------|
| AC-7b.3.1: TimeSeriesSplit CV | 7* | RED |
| AC-7b.3.2: All 9 Models Tested | 4 | RED |
| AC-7b.3.3: Regressor Comparison | 5 | RED |
| AC-7b.3.4: MAPE/MASE Selection | 4 | RED |
| AC-7b.3.5: Graceful Failure Handling | 5 | RED |
| AC-7b.3.6: ModelSelectionResult Output | 8 | RED |
| AC-7b.3.7: Runtime Performance | 2 | RED |
| Additional: Module Exports | 4 | RED |
| Additional: Edge Cases | 2 | RED |
| **TOTAL** | **41** | **RED** |

*Note: AC-7b.3.1 includes parametrized test with 3 values (cv_folds=[3,5,7]), expanding to 7 test cases.*

---

## Acceptance Criteria Details

### AC-7b.3.1: TimeSeriesSplit Cross-Validation Implementation [P0]

**Given** a historical time series for a financial variable with at least 12 data points
**When** `select_best_model()` is called with the variable data
**Then** the function performs time-series aware cross-validation using `sklearn.model_selection.TimeSeriesSplit` with configurable folds (default: 5)

| Test ID | Test Name | Description | Status |
|---------|-----------|-------------|--------|
| TEST-AC-7b.3.1.1 | `test_ac_7b_3_1_1_select_best_model_uses_time_series_split` | Verifies TimeSeriesSplit usage | RED |
| TEST-AC-7b.3.1.2 | `test_ac_7b_3_1_2_configurable_cv_folds` | cv_folds parameter accepts 3, 5, 7 | RED |
| TEST-AC-7b.3.1.3 | `test_ac_7b_3_1_3_default_five_folds` | Default 5 folds when not specified | RED |
| TEST-AC-7b.3.1.4 | `test_ac_7b_3_1_4_minimum_12_observations_required` | ValueError for <12 points | RED |
| TEST-AC-7b.3.1.5 | `test_ac_7b_3_1_5_exactly_12_points_accepted` | Exactly 12 points is valid | RED |

---

### AC-7b.3.2: All 9 Models Tested [P0]

**Given** the model selection framework is initialized
**When** cross-validation runs for a variable
**Then** ALL 9 available models are tested: ARIMA, ETS, Prophet, XGBoost, LightGBM, CatBoost, Chronos-2, TFT, Linear

| Test ID | Test Name | Description | Status |
|---------|-----------|-------------|--------|
| TEST-AC-7b.3.2.1 | `test_ac_7b_3_2_1_candidate_models_contains_all_nine` | CANDIDATE_MODELS has 9 models | RED |
| TEST-AC-7b.3.2.2 | `test_ac_7b_3_2_2_candidate_models_is_list` | CANDIDATE_MODELS is ordered list | RED |
| TEST-AC-7b.3.2.3 | `test_ac_7b_3_2_3_all_models_attempted_during_selection` | Each model tested during selection | RED |
| TEST-AC-7b.3.2.4 | `test_ac_7b_3_2_4_tft_included_when_available` | TFT is in candidate results | RED |

---

### AC-7b.3.3: Regressor Comparison [P0]

**Given** external regressors are available for a variable
**When** model selection runs
**Then** each model is tested BOTH with and without regressors, resulting in up to 18 configurations per variable

| Test ID | Test Name | Description | Status |
|---------|-----------|-------------|--------|
| TEST-AC-7b.3.3.1 | `test_ac_7b_3_3_1_models_tested_with_and_without_regressors` | Both _False and _True configs | RED |
| TEST-AC-7b.3.3.2 | `test_ac_7b_3_3_2_chronos_skipped_for_regressor_mode` | chronos_True not in results | RED |
| TEST-AC-7b.3.3.3 | `test_ac_7b_3_3_3_best_with_regressors_flag_set` | best_with_regressors is bool | RED |
| TEST-AC-7b.3.3.4 | `test_ac_7b_3_3_4_best_regressor_set_populated` | best_regressor_set matches input | RED |
| TEST-AC-7b.3.3.5 | `test_ac_7b_3_3_5_no_regressors_provided` | Works with None regressors | RED |

---

### AC-7b.3.4: MAPE/MASE Selection Criteria [P0]

**Given** cross-validation results for all model configurations
**When** selecting the best model
**Then** selection is based on: Primary: MAPE (lower is better), Secondary: MASE (tiebreaker)

| Test ID | Test Name | Description | Status |
|---------|-----------|-------------|--------|
| TEST-AC-7b.3.4.1 | `test_ac_7b_3_4_1_best_model_selected_by_lowest_mape` | Lowest MAPE wins | RED |
| TEST-AC-7b.3.4.2 | `test_ac_7b_3_4_2_mase_used_as_tiebreaker` | MASE breaks ties | RED |
| TEST-AC-7b.3.4.3 | `test_ac_7b_3_4_3_best_mape_populated` | best_mape is float >= 0 | RED |
| TEST-AC-7b.3.4.4 | `test_ac_7b_3_4_4_best_mase_populated` | best_mase is float >= 0 | RED |

---

### AC-7b.3.5: Graceful Model Failure Handling [P0]

**Given** a model fails during cross-validation (fitting error, convergence failure, etc.)
**When** the failure occurs
**Then** the model is skipped with a warning log, and selection continues with remaining models

| Test ID | Test Name | Description | Status |
|---------|-----------|-------------|--------|
| TEST-AC-7b.3.5.1 | `test_ac_7b_3_5_1_failed_model_does_not_crash_selection` | Selection completes despite failures | RED |
| TEST-AC-7b.3.5.2 | `test_ac_7b_3_5_2_failed_models_excluded_or_marked` | Failed models have 'error' key | RED |
| TEST-AC-7b.3.5.3 | `test_ac_7b_3_5_3_warning_logged_for_failed_models` | Logger.warning called | RED |
| TEST-AC-7b.3.5.4 | `test_ac_7b_3_5_4_at_least_one_model_must_succeed` | Valid best_model returned | RED |
| TEST-AC-7b.3.5.5 | `test_ac_7b_3_5_5_all_models_fail_raises_error` | ModelSelectionError when all fail | RED |

---

### AC-7b.3.6: ModelSelectionResult Output [P0]

**Given** model selection completes successfully
**When** results are returned
**Then** a `ModelSelectionResult` dataclass is returned containing all required fields

| Test ID | Test Name | Description | Status |
|---------|-----------|-------------|--------|
| TEST-AC-7b.3.6.1 | `test_ac_7b_3_6_1_model_selection_result_exists` | Dataclass exists | RED |
| TEST-AC-7b.3.6.2 | `test_ac_7b_3_6_2_result_contains_variable_name` | variable_name field present | RED |
| TEST-AC-7b.3.6.3 | `test_ac_7b_3_6_3_result_contains_best_model` | best_model field present | RED |
| TEST-AC-7b.3.6.4 | `test_ac_7b_3_6_4_result_contains_data_characteristics` | DataCharacteristics included | RED |
| TEST-AC-7b.3.6.5 | `test_ac_7b_3_6_5_result_contains_candidate_results` | candidate_results dict present | RED |
| TEST-AC-7b.3.6.6 | `test_ac_7b_3_6_6_result_contains_runtime_seconds` | runtime_seconds tracked | RED |
| TEST-AC-7b.3.6.7 | `test_ac_7b_3_6_7_result_contains_all_required_fields` | All 10 fields present | RED |
| TEST-AC-7b.3.6.8 | `test_ac_7b_3_6_8_result_serializable_to_json` | JSON serialization works | RED |

---

### AC-7b.3.7: Runtime Performance [P0]

**Given** model selection is running for a single variable
**When** all 9 models are cross-validated with 5 folds
**Then** total runtime is less than 10 minutes per variable

| Test ID | Test Name | Description | Status |
|---------|-----------|-------------|--------|
| TEST-AC-7b.3.7.1 | `test_ac_7b_3_7_1_selection_completes_under_10_minutes` | < 600 seconds | RED |
| TEST-AC-7b.3.7.2 | `test_ac_7b_3_7_2_runtime_tracked_in_result` | runtime_seconds matches actual | RED |

---

## Additional Tests

### Module Exports

| Test ID | Test Name | Description | Status |
|---------|-----------|-------------|--------|
| - | `test_module_exports_select_best_model` | Function is callable | RED |
| - | `test_module_exports_candidate_models` | List is exported | RED |
| - | `test_module_exports_model_selection_result` | Dataclass is exported | RED |
| - | `test_module_exports_model_selection_error` | Exception is exported | RED |

### Edge Cases

| Test ID | Test Name | Description | Status |
|---------|-----------|-------------|--------|
| - | `test_force_refresh_parameter` | force_refresh parameter works | RED |
| - | `test_empty_regressors_dict` | Empty dict = None regressors | RED |

---

## Implementation Requirements

### Files to Create

1. **`raglite/forecasting/model_selection.py`** (~500 lines)
   - `CANDIDATE_MODELS` list with 9 models
   - `ModelSelectionResult` dataclass
   - `ModelSelectionError` exception class
   - `select_best_model()` async function
   - `_filter_candidates()` helper
   - `_cv_evaluate()` helper
   - Model-specific fitting functions

### Dependencies (Already in Tech Stack)

- `sklearn.model_selection.TimeSeriesSplit`
- `pandas`, `numpy`
- `raglite.forecasting.data_analyzer` (Story 7b-2)
- Existing model fitting functions from `raglite/forecasting/hybrid.py`

---

## Validation Commands

```bash
# Run all model selection tests (expected to FAIL in RED phase)
uv run pytest tests/integration/test_model_selection.py -v

# Run specific AC tests
uv run pytest tests/integration/test_model_selection.py -v -k "AC_7b_3_1"

# Count tests
uv run pytest tests/integration/test_model_selection.py --collect-only | grep "test_" | wc -l
```

---

## TDD Workflow

1. **RED Phase (Current):** All 41 tests fail because `model_selection.py` doesn't exist
2. **GREEN Phase (Next):** Implement `model_selection.py` to make all tests pass
3. **REFACTOR Phase:** Optimize code while maintaining passing tests

---

## Notes

- Tests use `@pytest.mark.asyncio` for async function testing
- Tests use `@pytest.mark.slow` for runtime performance test (>1 second)
- Fixtures provide realistic financial time series data
- Tests follow existing patterns from `test_arima_model.py` and data analyzer tests
