# Validation Report

**Document:** `/docs/stories/6.3-prophet-multi-variate-forecasting.md`
**Checklist:** `/bmad/bmm/workflows/4-implementation/create-story/checklist.md`
**Date:** 2025-12-05T10:30:00

---

## Summary

- **Overall:** 11/20 passed (55%)
- **Critical Issues:** 6
- **Enhancements:** 4
- **LLM Optimizations:** 3

---

## Section Results

### Story Structure & Metadata
**Pass Rate:** 5/5 (100%)

| Mark | Item | Evidence |
|------|------|----------|
| ✓ PASS | Epic reference | Line 3: `**Epic:** Epic 6 - Advanced Forecasting with External Data` |
| ✓ PASS | Priority specified | Line 4: `**Priority:** P0` |
| ✓ PASS | Status defined | Line 6: `**Status:** 🟡 READY TO START` |
| ✓ PASS | User story format | Lines 10-12: "As a system, I want to..." |
| ✓ PASS | Dependencies listed | Lines 315-317: Story 6.1 and 6.2 referenced |

---

### Acceptance Criteria Completeness
**Pass Rate:** 4/7 (57%)

| Mark | Item | Evidence |
|------|------|----------|
| ✓ PASS | AC1: Function signature defined | Lines 18-45: `generate_forecast()` with `external_regressors` parameter |
| ✓ PASS | AC2: Regressor selection | Lines 56-88: `select_regressors()` with correlation analysis |
| ✓ PASS | AC3: Missing data handling | Lines 94-135: `prepare_regressors()` with interpolation |
| ✗ FAIL | AC4: Accuracy validation | Lines 142-159: `ForecastResult` model shows new fields, but **current model in `models.py:405-438` lacks these fields** |
| ⚠ PARTIAL | AC5: Backward compatibility | Lines 161-165: Stated but function signature change breaks compatibility (see Critical Issues) |
| ✓ PASS | AC6: Unit tests | Lines 167-186: Test scenarios listed |
| ⚠ PARTIAL | AC7: Integration tests | Lines 188-211: Tests defined but reference `fetch_ine_building_permits()` which doesn't exist |

**Impact:** Developer will encounter undefined functions and missing model fields during implementation.

---

### Technical Specification Completeness
**Pass Rate:** 2/8 (25%)

| Mark | Item | Evidence |
|------|------|----------|
| ✗ FAIL | Missing function: `fetch_historical_metric()` | Line 234: Referenced but never defined. Is this a PostgreSQL query? Qdrant query? Story 4.2 MCP tool? |
| ✗ FAIL | Missing function: `calculate_accuracy()` | Line 294: Referenced but implementation not provided |
| ✗ FAIL | Missing function: `get_baseline_rmse()` | Line 297: Referenced but no guidance on where Epic 4 RMSE is stored or how to retrieve |
| ✗ FAIL | `ForecastResult` model incompatible | Current model (models.py:405-438) lacks: `model_type`, `accuracy_metrics`, `regressors_used`, `improvement_vs_baseline` |
| ⚠ PARTIAL | Future regressor values | Lines 285-288: "Assume constant" is naive. Better: extrapolate trend or use Prophet forecast for regressors |
| ✓ PASS | Prophet `add_regressor()` usage | Lines 255-256: Correct API usage documented |
| ✗ FAIL | Breaking API change not addressed | Current `generate_forecast()` takes `historical_data: TimeSeriesData`. Story 6.3 changes this to fetch internally via `metric` string |
| ✓ PASS | Import statements | Line 223: Correct imports from approved tech stack |

**Impact:** Developer cannot implement without inventing 3+ functions and modifying Pydantic models.

---

### Previous Story Context
**Pass Rate:** 0/2 (0%)

| Mark | Item | Evidence |
|------|------|----------|
| ✗ FAIL | Story 6.2 completion status | Story 6.2 is "READY TO START" (not complete). Story 6.3 depends on `ExternalDataStorage` class from 6.2 which doesn't exist yet |
| ✗ FAIL | Story 6.1 patterns not referenced | Story 6.1 defines Pydantic models in `raglite/external_data/models.py`. Story 6.3 should reference fetching data from these clients |

**Impact:** Developer may attempt Story 6.3 before dependencies are complete, causing wasted effort.

---

### Code Reuse & Anti-Pattern Prevention
**Pass Rate:** 0/3 (0%)

| Mark | Item | Evidence |
|------|------|----------|
| ✗ FAIL | No reference to existing `hybrid.py` structure | Current file is 320 lines. Story doesn't indicate WHERE to add new code or how to preserve existing function signature |
| ✗ FAIL | No guidance on model field additions | Must update `raglite/shared/models.py` `ForecastResult` class but not documented |
| ⚠ PARTIAL | Duplicate test data pattern | Test examples use 4 data points - Prophet requires 6+ (per existing MIN_DATA_POINTS constant) |

**Impact:** Developer may break existing functionality or write incompatible code.

---

## Failed Items (✗)

### 1. Missing `ForecastResult` Model Updates
**Location:** AC4 (Lines 147-155)
**Current State:** `ForecastResult` in `models.py:405-438` has:
- `metric_name`, `historical_data`, `forecast`, `confidence_reasoning`, `basis`, `accuracy_estimate`, `periods_ahead`

**Required Additions:**
```python
model_type: str = Field(default="prophet_univariate")  # "prophet_univariate" | "prophet_multivariate"
accuracy_metrics: dict[str, float] = Field(default_factory=dict)  # {"rmse": X, "mae": Y, "mape": Z}
regressors_used: list[str] = Field(default_factory=list)  # ["building_permits", "electricity_price"]
improvement_vs_baseline: float | None = Field(default=None)  # % improvement vs Epic 4
```

**Recommendation:** Add "Update `raglite/shared/models.py` ForecastResult class" as subtask AC4.1

---

### 2. Missing `fetch_historical_metric()` Implementation
**Location:** Technical Design (Line 234)
**Problem:** Function is called but never defined.
**Options:**
- Option A: Query PostgreSQL `external_data_points` table via `ExternalDataStorage`
- Option B: Query Qdrant for historical metrics from ingested documents (Epic 4 pattern)
- Option C: Accept `historical_data` parameter (preserve backward compatibility)

**Recommendation:** Define function explicitly or clarify it comes from Story 6.2 `ExternalDataStorage` class

---

### 3. Missing `calculate_accuracy()` and `get_baseline_rmse()` Functions
**Location:** Lines 294-299
**Problem:** These are called but implementation is undefined.
**Required Implementation:**
```python
def calculate_accuracy(model: Prophet, historical: pd.Series) -> dict[str, float]:
    """Cross-validation accuracy metrics using Prophet diagnostics."""
    from prophet.diagnostics import cross_validation, performance_metrics
    cv = cross_validation(model, initial='365 days', period='90 days', horizon='90 days')
    metrics = performance_metrics(cv)
    return {"rmse": metrics["rmse"].mean(), "mae": metrics["mae"].mean(), "mape": metrics["mape"].mean()}
```

**Recommendation:** Add helper function definitions or reference Prophet diagnostics documentation

---

### 4. Breaking API Change to `generate_forecast()`
**Location:** AC1 (Lines 22-46)
**Current Signature (hybrid.py:62-66):**
```python
async def generate_forecast(
    metric: str,
    historical_data: TimeSeriesData,  # <-- PASSED AS PARAMETER
    periods_ahead: int = 4,
) -> ForecastResult:
```

**Proposed Signature (Story 6.3):**
```python
async def generate_forecast(
    metric: str,
    periods_ahead: int = 12,
    external_regressors: Optional[Dict[str, pd.Series]] = None,
    frequency: str = 'M'
) -> ForecastResult:  # historical_data fetched internally
```

**Problem:** Removes `historical_data` parameter, breaking all existing callers.

**Recommendation:**
1. Keep `historical_data: TimeSeriesData | None = None` as optional parameter
2. If `None`, fetch from PostgreSQL
3. Add deprecation warning for callers passing `historical_data`

---

### 5. Story 6.2 Dependency Not Complete
**Location:** Dependencies (Line 317)
**Problem:** Story 6.2 defines `ExternalDataStorage` class which Story 6.3 imports. Story 6.2 status is "READY TO START" (not complete).
**Risk:** Developer attempts implementation before PostgreSQL schema exists.

**Recommendation:** Add explicit prerequisite check: "Verify Story 6.2 implementation exists before starting"

---

### 6. Test Data Size Too Small
**Location:** Unit Tests (Lines 333-366)
**Problem:** Test uses 4 data points:
```python
historical = pd.Series([100, 105, 110, 115], index=pd.date_range(..., periods=4, freq='M'))
```
**Current Constraint:** `MIN_DATA_POINTS = 6` in `hybrid.py:53`
**Impact:** Tests will fail with `InsufficientDataError`

**Recommendation:** Update test examples to use 8+ data points to match production requirements

---

## Partial Items (⚠)

### 1. AC5: Backward Compatibility Claim Conflicts with Implementation
**Problem:** Story claims "No breaking changes" but removes required `historical_data` parameter.
**Recommendation:** Either preserve parameter as optional OR document migration path for existing callers.

### 2. AC7: Integration Tests Reference Undefined Functions
**Problem:** `fetch_ine_building_permits()` referenced but this function name doesn't match Story 6.1 client pattern.
**Story 6.1 Pattern:** `INEClient().fetch_building_permits(start_date, end_date)`
**Recommendation:** Update test to use actual client class from Story 6.1

### 3. Future Regressor Values Strategy is Naive
**Problem:** "Use latest available data (assume constant)" causes accuracy degradation.
**Better Approach:**
1. Forecast each regressor forward using its own trend
2. Use linear extrapolation for simple cases
3. Accept user-provided future values as parameter

**Recommendation:** Add `future_regressor_strategy: str = "constant"` parameter with options: `constant`, `extrapolate`, `provided`

---

## Recommendations

### 1. Must Fix (Critical)

1. **Add ForecastResult model update task** - Update `raglite/shared/models.py` with new fields
2. **Define missing helper functions** - `fetch_historical_metric()`, `calculate_accuracy()`, `get_baseline_rmse()`
3. **Preserve backward compatibility** - Keep `historical_data` parameter as optional
4. **Add dependency check** - Verify Story 6.2 complete before implementation
5. **Fix test data sizes** - Use 8+ data points in test examples

### 2. Should Improve (Enhancements)

1. **Reference Story 6.1 client patterns** - Show how to use `INEClient`, `OMIEClient`, etc.
2. **Add file modification list** - Specify exactly which files change
3. **Clarify PostgreSQL vs Qdrant data source** - Document where historical metrics come from
4. **Improve future regressor strategy** - Document alternatives to "constant" assumption

### 3. Consider (LLM Optimization)

1. **Reduce duplication** - Technical Design repeats AC1-AC3 verbatim (remove ~100 lines)
2. **Reduce test verbosity** - Testing Plan repeats AC6-AC7 (remove ~50 lines)
3. **Use pseudocode** - Reference Prophet docs instead of copying full implementation
4. **Target length: 200 lines** - Current 394 lines is 2x optimal

---

## LLM Optimization Improvements

### Current Token Waste

| Section | Current Lines | Optimal Lines | Waste |
|---------|---------------|---------------|-------|
| AC1-AC7 | 170 | 120 | 50 |
| Technical Design | 95 | 30 (reference ACs) | 65 |
| Testing Plan | 37 | 10 (reference ACs) | 27 |
| Total | 394 | 250 | 144 (~36%) |

### Recommended Optimizations

1. **Technical Design Section:** Replace full implementation with:
   ```
   See AC1-AC3 for implementation details. File: `raglite/forecasting/hybrid.py`
   ```

2. **Testing Plan Section:** Replace with:
   ```
   Unit Tests: See AC6. File: `tests/unit/test_prophet_multivariate.py`
   Integration Tests: See AC7. File: `tests/integration/test_forecast_with_external.py`
   ```

3. **Remove redundant code blocks** - AC1 shows function signature, Technical Design shows same signature with implementation. Keep one.

---

## Validation Status

| Category | Count | Status |
|----------|-------|--------|
| Critical Issues | 6 | 🔴 Blocks implementation |
| Enhancements | 4 | 🟡 Improves success rate |
| Optimizations | 3 | 🟢 Reduces token usage |

**Verdict:** Story requires revision before dev agent can implement successfully.

---

**Report Generated By:** SM Agent (Bob)
**Validation Framework:** validate-workflow.xml v1.0
