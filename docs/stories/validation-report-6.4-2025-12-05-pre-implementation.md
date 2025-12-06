# Validation Report

**Document:** `docs/stories/6.4-model-ensemble-framework.md`
**Checklist:** `.bmad/bmm/workflows/4-implementation/create-story/checklist.md`
**Date:** 2025-12-05

## Summary

- **Overall:** 7/20 passed (35%)
- **Critical Issues:** 8
- **Enhancement Opportunities:** 5
- **LLM Optimization Issues:** 3

---

## Section Results

### 1. Story Structure & Metadata
**Pass Rate:** 4/5 (80%)

✓ **PASS** - User story format present (lines 10-12)
> Evidence: "As a system, I want to use diverse predictive models beyond Prophet..."

✓ **PASS** - Epic reference correct (line 3)
> Evidence: "**Epic:** Epic 6 - Advanced Forecasting with External Data"

✓ **PASS** - Priority and effort specified (lines 4-5)
> Evidence: "**Priority:** P1", "**Estimated Effort:** 3-4 days"

✓ **PASS** - Dependencies listed (lines 69-72)
> Evidence: "Story 6.3 (multi-variate Prophet as baseline)"

✗ **FAIL** - Missing status update guidance
> **Impact:** Story shows "🟡 READY TO START" but no instructions for updating status through implementation lifecycle.

---

### 2. Technical Requirements
**Pass Rate:** 1/6 (17%)

✗ **FAIL** - **CRITICAL: Dependencies NOT in pyproject.toml**
> **Impact:** scikit-learn and XGBoost are NOT installed. Current pyproject.toml (lines 31-53) does NOT include:
> - `scikit-learn>=1.5`
> - `xgboost>=2.1`
> Developer will get ImportError immediately. This is a BLOCKER.
> **Evidence:** pyproject.toml dependencies end at line 53 with no scikit-learn/xgboost entries.

✗ **FAIL** - Missing file locations and action types
> **Impact:** Story lists components (Prophet, Linear, XGBoost) but doesn't specify:
> - Which files to modify (`raglite/forecasting/hybrid.py` or new `raglite/forecasting/ensemble.py`?)
> - Import statements needed
> - Function signatures
> **Evidence:** AC1 (lines 18-24) has no file paths or code examples.

✗ **FAIL** - Missing ForecastResult model extension
> **Impact:** Story mentions ensemble voting but doesn't specify new fields for ForecastResult:
> - `ensemble_models`: list of model names
> - `individual_predictions`: dict of model -> value
> - `ensemble_weights`: dict of model -> weight
> **Evidence:** Current ForecastResult (models.py lines 405-461) only has multi-variate fields from 6.3, not ensemble fields.

✓ **PASS** - Environment variable configuration documented
> Evidence: "Environment variable: `FORECASTING_MODELS=prophet,linear,xgboost`" (line 27)

✗ **FAIL** - Missing TimeSeriesSplit import guidance
> **Impact:** AC3 mentions "5-fold time-series split" but doesn't provide import or usage pattern.
> Developer might use wrong CV approach. `sklearn.model_selection.TimeSeriesSplit` is correct but not stated.

✗ **FAIL** - Missing parallel execution architecture
> **Impact:** NFR states "3 models in parallel" (<15s p95) but no guidance on:
> - `asyncio.gather()` vs `ThreadPoolExecutor`
> - Whether Prophet supports parallel prediction
> - Memory implications of 3 simultaneous models

---

### 3. Integration with Story 6.3
**Pass Rate:** 1/4 (25%)

✓ **PASS** - Story 6.3 dependency correctly stated
> Evidence: Line 72: "Story 6.3 (multi-variate Prophet as baseline)"

✗ **FAIL** - Missing code reuse guidance
> **Impact:** Story 6.3 (`hybrid.py`) already has:
> - `select_regressors()` (lines 79-125)
> - `prepare_regressors()` (lines 128-179)
> - `calculate_accuracy()` (lines 182-229)
> - `generate_forecast()` with multi-variate support (lines 393-704)
> Story 6.4 should EXTEND these, not recreate. No guidance provided.
> **Evidence:** hybrid.py has 787 lines of forecasting code, none mentioned in story.

✗ **FAIL** - Missing backward compatibility requirements
> **Impact:** Story doesn't specify:
> - Should `generate_forecast()` accept `model_type` parameter?
> - How to preserve existing Prophet-only behavior?
> - Deprecation strategy for callers not wanting ensemble?

✗ **FAIL** - Missing integration with `explain_forecast()`
> **Impact:** Story 6.3's LLM explanation (hybrid.py lines 707-787) should include ensemble-specific reasoning.
> No guidance on how to explain "3 models agree/disagree".

---

### 4. Acceptance Criteria Completeness
**Pass Rate:** 1/7 (14%)

✓ **PASS** - All 7 ACs have checkmarks indicating expected validation
> Evidence: AC1-AC7 all show "✅"

✗ **FAIL** - AC1 missing implementation details
> **Impact:** "Implement Ensemble Framework" is vague. Doesn't specify:
> - New file or extend existing?
> - Class-based or function-based?
> - How to get Prophet forecast from existing code?
> **Evidence:** AC1 (lines 18-24) lacks code patterns.

✗ **FAIL** - AC3 missing Optuna vs GridSearch decision
> **Impact:** "Grid search or Optuna" - developer must choose. Neither library is installed.
> If Optuna chosen, needs `optuna>=3.0` in pyproject.toml.
> **Evidence:** AC3 (lines 31-35) has ambiguous "or" with no decision criteria.

✗ **FAIL** - AC4 missing metric calculation location
> **Impact:** Where to put RMSE/MAE/MAPE calculation? Reuse `calculate_accuracy()` from Story 6.3?
> Or new function? No guidance.

✗ **FAIL** - AC5 fallback missing implementation details
> **Impact:** "Fallback to Prophet-only" - but Prophet is one of the ensemble models.
> Does this mean:
> - Prophet-univariate (Epic 4)?
> - Prophet-multivariate (Story 6.3)?
> - Just drop Linear+XGBoost weights?

✗ **FAIL** - AC6 missing test file location
> **Impact:** Where should unit tests go?
> - `tests/unit/test_ensemble_forecasting.py` (new)?
> - `tests/unit/test_multivariate_forecasting.py` (existing from 6.3)?
> No guidance.

✗ **FAIL** - AC7 integration test missing database requirements
> **Impact:** "Real data" - from where?
> - Story 6.2 PostgreSQL schema?
> - Mock fixtures?
> - What test database setup needed?

---

### 5. NFRs and Performance
**Pass Rate:** 0/3 (0%)

✗ **FAIL** - NFR timing not validated against existing code
> **Impact:** "<15s p95 (3 models in parallel)" but:
> - Prophet alone can take 5-10s for fitting
> - No benchmark for current Story 6.3 performance
> - Is 15s even achievable?
> **Evidence:** hybrid.py has no timing benchmarks.

✗ **FAIL** - NFR accuracy target not measurable
> **Impact:** "10-15% reduction in RMSE vs Story 6.3" but:
> - What's Story 6.3's baseline RMSE?
> - Not documented in story or accuracy-tracking-log.jsonl
> - How to validate this requirement?

✗ **FAIL** - Missing memory requirements
> **Impact:** Running 3 ML models simultaneously has memory implications:
> - XGBoost can use significant RAM
> - No guidance on memory limits or fallback if OOM

---

## Failed Items (Must Fix)

### 1. **[BLOCKER] Add scikit-learn and XGBoost to pyproject.toml**
```toml
# Add to [project] dependencies:
"scikit-learn>=1.5,<2.0",  # Story 6.4: Model ensemble (Linear Regression)
"xgboost>=2.1,<3.0",       # Story 6.4: Gradient boosting ensemble
```
**Why:** Developer cannot import these libraries without installation.

### 2. **[BLOCKER] Specify file modifications table**
Add "Files to Modify" section like Story 6.3:
| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | MODIFY | Add scikit-learn, xgboost dependencies |
| `raglite/forecasting/hybrid.py` | MODIFY | Add ensemble functions |
| `raglite/shared/models.py` | MODIFY | Add ensemble fields to ForecastResult |
| `tests/unit/test_ensemble_forecasting.py` | NEW | Unit tests for ensemble |
| `tests/integration/test_ensemble_real_data.py` | NEW | Integration tests |

### 3. **Add ForecastResult ensemble fields**
```python
# Story 6.4: Ensemble forecasting fields
ensemble_models: list[str] = Field(
    default_factory=list,
    description="Models used in ensemble: ['prophet', 'linear', 'xgboost']"
)
individual_predictions: dict[str, list[float]] = Field(
    default_factory=dict,
    description="Per-model predictions: {'prophet': [1.2, 1.3], 'linear': [1.1, 1.4]}"
)
ensemble_weights: dict[str, float] = Field(
    default_factory=dict,
    description="Model weights: {'prophet': 0.4, 'linear': 0.3, 'xgboost': 0.3}"
)
```

### 4. **Add code examples for Linear Regression**
```python
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import TimeSeriesSplit

def fit_linear_regression(X: pd.DataFrame, y: pd.Series) -> LinearRegression:
    """Fit Linear Regression with external regressors."""
    model = LinearRegression()
    model.fit(X, y)
    return model
```

### 5. **Add code examples for XGBoost**
```python
from xgboost import XGBRegressor

def fit_xgboost(X: pd.DataFrame, y: pd.Series) -> XGBRegressor:
    """Fit XGBoost regressor with hyperparameter tuning."""
    model = XGBRegressor(
        n_estimators=100,  # Tunable via grid search
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42
    )
    model.fit(X, y)
    return model
```

### 6. **Resolve AC3 ambiguity: GridSearchCV vs Optuna**
Recommend GridSearchCV (already in sklearn, no new dependency):
```python
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit

param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [3, 6, 9],
    'learning_rate': [0.01, 0.1, 0.2],
    'subsample': [0.7, 0.8, 0.9]
}

tscv = TimeSeriesSplit(n_splits=5)
grid_search = GridSearchCV(
    XGBRegressor(random_state=42),
    param_grid,
    cv=tscv,
    scoring='neg_root_mean_squared_error'
)
```

### 7. **Add parallel execution pattern**
```python
import asyncio

async def generate_ensemble_forecast(...) -> ForecastResult:
    """Generate ensemble forecast using parallel model execution."""
    # Run models in parallel
    results = await asyncio.gather(
        run_prophet_forecast(...),
        run_linear_forecast(...),  # Actually sync, wrap in executor
        run_xgboost_forecast(...),  # Actually sync, wrap in executor
        return_exceptions=True
    )
    # Handle failures...
```

### 8. **Clarify AC5 fallback behavior**
```
AC5 Clarification:
- If ALL ensemble models fail → use Story 6.3 Prophet-multivariate
- If individual model fails → continue with remaining models, adjust weights
- Log WARNING with failure details, continue with degraded ensemble
```

---

## Partial Items (Should Improve)

### 1. **Add mypy type stubs**
XGBoost and scikit-learn need type stubs for mypy. Add to pyproject.toml:
```toml
[[tool.mypy.overrides]]
module = [
    "xgboost.*",
    "sklearn.*",
]
ignore_missing_imports = true
```

### 2. **Add Settings configuration**
```python
# raglite/shared/config.py
class Settings(BaseSettings):
    forecasting_models: str = Field(
        default="prophet,linear,xgboost",
        description="Comma-separated list of models for ensemble"
    )
    ensemble_weights_prophet: float = Field(default=0.4)
    ensemble_weights_linear: float = Field(default=0.3)
    ensemble_weights_xgboost: float = Field(default=0.3)
```

### 3. **Add accuracy baseline documentation**
Reference Story 6.3's baseline RMSE for comparison. Check `docs/accuracy-tracking-log.jsonl`.

### 4. **Add test data fixtures**
Specify or reference fixtures from Story 6.3 (`tests/unit/test_multivariate_forecasting.py`).

### 5. **Add integration with MCP tool**
Story doesn't mention updating `get_financial_forecast()` MCP tool to accept `model_type` parameter.

---

## LLM Optimization Improvements

### 1. **Reduce AC verbosity**
Current ACs have repetitive structure ("✅ **Title**" then details). Consolidate for token efficiency.

### 2. **Add executable code snippets**
Replace vague requirements with copy-paste code. Developer agent needs concrete patterns.

### 3. **Create implementation checklist**
Convert ACs to step-by-step checklist:
```
[ ] 1. Add dependencies to pyproject.toml
[ ] 2. Update ForecastResult model with ensemble fields
[ ] 3. Implement fit_linear_regression() in hybrid.py
[ ] 4. Implement fit_xgboost() in hybrid.py
[ ] 5. Implement generate_ensemble_forecast()
[ ] 6. Add hyperparameter tuning with GridSearchCV
[ ] 7. Add fallback logic
[ ] 8. Add unit tests (80%+ coverage)
[ ] 9. Add integration tests
[ ] 10. Validate NFRs (<15s p95, 10-15% RMSE improvement)
```

---

## Recommendations

### Must Fix (8 Critical)
1. Add scikit-learn and xgboost to pyproject.toml
2. Add "Files to Modify" section with file paths and action types
3. Add ForecastResult ensemble fields specification
4. Add code examples for LinearRegression
5. Add code examples for XGBRegressor
6. Resolve GridSearchCV vs Optuna ambiguity (recommend GridSearchCV)
7. Add parallel execution pattern with asyncio/executor
8. Clarify AC5 fallback behavior (which Prophet mode?)

### Should Improve (5 Enhancements)
1. Add mypy type stub configuration for sklearn/xgboost
2. Add Settings configuration for ensemble weights
3. Reference Story 6.3 baseline RMSE for NFR validation
4. Reference or create test fixtures
5. Add MCP tool update guidance

### Consider (3 Optimizations)
1. Consolidate verbose ACs into implementation checklist
2. Add copy-paste code snippets throughout
3. Add Definition of Done section like Story 6.3

---

**Report Generated:** 2025-12-05
**Validator:** BMAD SM Agent (Bob)
**Story Status:** ⚠️ REQUIRES REVISION - 8 critical issues must be fixed before development
