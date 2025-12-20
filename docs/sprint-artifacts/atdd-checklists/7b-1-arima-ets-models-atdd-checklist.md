# ATDD Checklist: Story 7B.1 - Add ARIMA/ETS Model Wrappers

**Epic:** 7B - Intelligent Model Selection Framework
**Story:** 7b-1-add-arima-ets-model-wrappers
**TDD Phase:** RED (Tests Created, All Failing)
**Test File:** `tests/unit/test_arima_ets_models.py`
**Total Tests:** 57

---

## Status Summary

| Phase | Status | Tests Passing | Tests Failing |
|-------|--------|---------------|---------------|
| RED   | COMPLETE | 0 | 57 |
| GREEN | PENDING | - | - |
| REFACTOR | PENDING | - | - |

---

## Acceptance Criteria Coverage

### AC1: fit_arima() Implementation (10 tests)

| Test ID | Description | Status |
|---------|-------------|--------|
| TEST-AC-1.1 | Use pmdarima's auto_arima for automatic (p,d,q) selection | FAILING |
| TEST-AC-1.2 | Accept y_train: pd.Series as primary input | FAILING |
| TEST-AC-1.3 | Accept optional X_train: pd.DataFrame for exogenous regressors (ARIMAX) | FAILING |
| TEST-AC-1.4 | Accept forecast_horizon: int parameter | FAILING |
| TEST-AC-1.5 | Accept frequency: str parameter ("M" for monthly) | FAILING |
| TEST-AC-1.6 | Accept frequency: str parameter ("Q" for quarterly) | FAILING |
| TEST-AC-1.7 | Return tuple: (model, metrics_dict, predictions, confidence_intervals) | FAILING |
| TEST-AC-1.8 | Metrics dict includes: aic | FAILING |
| TEST-AC-1.9 | Metrics dict includes: order | FAILING |
| TEST-AC-1.10 | Metrics dict includes: seasonal_order | FAILING |

### AC2: fit_ets() Implementation (13 tests)

| Test ID | Description | Status |
|---------|-------------|--------|
| TEST-AC-2.1 | Use statsmodels ExponentialSmoothing | FAILING |
| TEST-AC-2.2 | Accept y_train: pd.Series as primary input | FAILING |
| TEST-AC-2.3 | Accept forecast_horizon: int parameter | FAILING |
| TEST-AC-2.4 | Accept frequency: str parameter ("M" for monthly) | FAILING |
| TEST-AC-2.5 | Accept frequency: str parameter ("Q" for quarterly) | FAILING |
| TEST-AC-2.6 | Support trend options: add | FAILING |
| TEST-AC-2.7 | Support trend options: mul | FAILING |
| TEST-AC-2.8 | Support trend options: None | FAILING |
| TEST-AC-2.9 | Support seasonal options: add | FAILING |
| TEST-AC-2.10 | Support seasonal options: mul | FAILING |
| TEST-AC-2.11 | Support seasonal options: None | FAILING |
| TEST-AC-2.12 | Support damped trend option | FAILING |
| TEST-AC-2.13 | Return tuple: (model, metrics_dict, predictions, confidence_intervals) | FAILING |

### AC3: Exogenous Variable Support (5 tests)

| Test ID | Description | Status |
|---------|-------------|--------|
| TEST-AC-3.1 | fit_arima() accepts X_train: pd.DataFrame for training | FAILING |
| TEST-AC-3.2 | fit_arima() accepts X_future: pd.DataFrame for prediction | FAILING |
| TEST-AC-3.3 | Validate regressor dimensions match forecast horizon | FAILING |
| TEST-AC-3.4 | Handle missing regressors gracefully (fall back to pure ARIMA) | FAILING |
| TEST-AC-3.5 | X_train defaults to None when not provided | FAILING |

### AC4: Frequency Handling (4 tests)

| Test ID | Description | Status |
|---------|-------------|--------|
| TEST-AC-4.1 | Monthly frequency ("M"): seasonal_periods=12 | FAILING |
| TEST-AC-4.2 | Quarterly frequency ("Q"): seasonal_periods=4 | FAILING |
| TEST-AC-4.3 | Auto-detect frequency from Series index if not provided | FAILING |
| TEST-AC-4.4 | Handle frequency conversion gracefully | FAILING |

### AC5: Return ForecastPoint Compatible Output (4 tests)

| Test ID | Description | Status |
|---------|-------------|--------|
| TEST-AC-5.1 | Predictions as numpy array of point forecasts | FAILING |
| TEST-AC-5.2 | Confidence intervals as 2D numpy array (lower, upper bounds) | FAILING |
| TEST-AC-5.3 | Default confidence level: 95% | FAILING |
| TEST-AC-5.4 | Output dimensions match forecast_horizon | FAILING |

### AC6: Graceful Fallback on Failure (7 tests)

| Test ID | Description | Status |
|---------|-------------|--------|
| TEST-AC-6.1 | Log warning with error details | FAILING |
| TEST-AC-6.2 | Raise specific exception (ARIMAFittingError) not generic Exception | FAILING |
| TEST-AC-6.3 | Raise specific exception (ETSFittingError) not generic Exception | FAILING |
| TEST-AC-6.4 | Caller can fall back to Prophet or other model | FAILING |
| TEST-AC-6.5 | Handle common failure: insufficient data | FAILING |
| TEST-AC-6.6 | Handle common failure: convergence issues | FAILING |
| TEST-AC-6.7 | Handle common failure: singular matrix | FAILING |

### AC7: Unit Test Coverage (8 tests)

| Test ID | Description | Status |
|---------|-------------|--------|
| TEST-AC-7.1 | arima_model.py exports fit_arima | FAILING |
| TEST-AC-7.2 | arima_model.py exports ARIMAFittingError | FAILING |
| TEST-AC-7.3 | ets_model.py exports fit_ets | FAILING |
| TEST-AC-7.4 | ets_model.py exports ETSFittingError | FAILING |
| TEST-AC-7.5 | models/__init__.py exports fit_arima | FAILING |
| TEST-AC-7.6 | models/__init__.py exports fit_ets | FAILING |
| TEST-AC-7.7 | models/__init__.py exports ARIMAFittingError | FAILING |
| TEST-AC-7.8 | models/__init__.py exports ETSFittingError | FAILING |

### Edge Cases (6 tests)

| Test ID | Description | Status |
|---------|-------------|--------|
| edge_case_empty_series | Handle empty series | FAILING |
| edge_case_all_zeros_series | Handle all-zeros series | FAILING |
| edge_case_negative_values_with_mul | Handle negative values with multiplicative | FAILING |
| edge_case_single_forecast_horizon | Forecast horizon of 1 | FAILING |
| edge_case_large_forecast_horizon | Large forecast horizon (12 months) | FAILING |
| edge_case_custom_confidence_level | Custom confidence level (90%) | FAILING |

---

## Implementation Files Required

### Files to Create

| File | Purpose | Estimated LOC |
|------|---------|---------------|
| `raglite/forecasting/models/arima_model.py` | ARIMA/SARIMA implementation | ~200 |
| `raglite/forecasting/models/ets_model.py` | ETS implementation | ~150 |

### Files to Modify

| File | Changes |
|------|---------|
| `raglite/forecasting/models/__init__.py` | Add exports for fit_arima, fit_ets, ARIMAFittingError, ETSFittingError |
| `pyproject.toml` | Add pmdarima dependency |

---

## Validation Commands

```bash
# Run all Story 7.1 tests
uv run pytest tests/unit/test_arima_ets_models.py -v

# Run with coverage
uv run pytest tests/unit/test_arima_ets_models.py --cov=raglite/forecasting/models/arima_model --cov=raglite/forecasting/models/ets_model --cov-report=term-missing

# Verify >80% coverage
uv run pytest tests/unit/test_arima_ets_models.py --cov=raglite/forecasting/models --cov-fail-under=80
```

---

## Next Steps

1. **GREEN Phase**: Implement `arima_model.py` and `ets_model.py` to make tests pass
2. **Update `__init__.py`**: Add exports for new functions and exceptions
3. **Add dependency**: Add pmdarima to pyproject.toml
4. **Run coverage**: Verify >80% coverage requirement (AC7)
5. **REFACTOR Phase**: Optimize and clean up implementation

---

## Notes

- Story 7.5 (models package refactoring) must be complete before implementing this story
- pmdarima is a new dependency that needs to be added
- statsmodels is already available via Prophet dependency
- All functions should follow the established `fit_*` pattern from existing models
- Async function signatures are used for consistency even though fitting is synchronous

---

## Created By

- **Generator:** ATDD Test Generator Agent
- **Date:** 2025-12-20
- **Story Reference:** `docs/sprint-artifacts/stories/7-1-add-arima-ets-model-wrappers.md`
