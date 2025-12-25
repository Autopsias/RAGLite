# Story 7B.1: Add ARIMA/ETS Model Wrappers

**Epic:** 7B - Intelligent Model Selection Framework
**Status:** drafted

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

---

## Prerequisites

- **Story 7.5 (Epic 7 Tech Debt):** Refactor hybrid.py into models package - ✅ COMPLETE. The new models package structure and patterns are in place.

---

## Story

As a developer,
I want `fit_arima()` and `fit_ets()` functions implemented matching existing model patterns,
so that the model selection framework can leverage statistical models for stationary financial data alongside existing ML models.

---

## Context

Currently, Prophet is used for all variables regardless of data characteristics, resulting in poor accuracy for some metrics (EBITDA: 84.77% MAPE). The existing hybrid.py forecasting module has 9 models (Prophet, XGBoost, LightGBM, CatBoost, Chronos-2, TFT, Linear/Ridge/Lasso), but lacks classical statistical models that excel at stationary financial data.

### Why ARIMA/ETS?

Per Epic 7: Intelligent Model Selection Framework (`docs/prd/epic-7-intelligent-model-selection.md`):

1. **ARIMA (AutoRegressive Integrated Moving Average)** - Best for stationary and difference-stationary financial data
2. **ETS (Exponential Smoothing State Space Model)** - Best for trend + seasonality patterns
3. **Both support exogenous variables** - ARIMAX/ETSX variants for regressor inclusion

### Current Model Inventory Gap

| Model | Status | Best For |
|-------|--------|----------|
| Prophet | Existing | Regime changes, seasonality |
| XGBoost | Existing | High-dimensional features |
| LightGBM | Existing | Fast gradient boosting |
| CatBoost | Existing | Categorical variables |
| Chronos-2 | Existing | Cold-start, zero-shot |
| TFT | Existing | Complex multivariate |
| Linear/Ridge/Lasso | Existing | Simple trends |
| **ARIMA/SARIMA** | **MISSING** | Stationary financial data |
| **ETS** | **MISSING** | Trend + seasonality |

### Expected Impact

After model selection (Story 7.3), these models are expected to improve:

| Variable | Current Model | Expected Best Model | Current MAPE | Target MAPE |
|----------|---------------|---------------------|--------------|-------------|
| EBITDA | Prophet | ARIMA(1,1,1) | 84.77% | <15% |
| Variable Cost | Prophet | ARIMA or Linear | High | <8% |
| TTF Gas | Prophet | ARIMA | - | - |
| Euribor 3M | Prophet | ARIMA | - | - |

---

## Acceptance Criteria

### AC1: fit_arima() Implementation
**Given** the need for ARIMA model forecasting
**When** implementing the `fit_arima()` function
**Then**:
- [ ] Use pmdarima's `auto_arima` for automatic (p,d,q) selection
- [ ] Accept `y_train: pd.Series` as primary input
- [ ] Accept optional `X_train: pd.DataFrame` for exogenous regressors (ARIMAX)
- [ ] Accept `forecast_horizon: int` parameter
- [ ] Accept `frequency: str` parameter ("M" for monthly, "Q" for quarterly)
- [ ] Return tuple: `(model, metrics_dict, predictions, confidence_intervals)`
- [ ] Metrics dict includes: `aic`, `order`, `seasonal_order`

### AC2: fit_ets() Implementation
**Given** the need for ETS model forecasting
**When** implementing the `fit_ets()` function
**Then**:
- [ ] Use statsmodels `ExponentialSmoothing`
- [ ] Accept `y_train: pd.Series` as primary input
- [ ] Accept `forecast_horizon: int` parameter
- [ ] Accept `frequency: str` parameter ("M" for monthly, "Q" for quarterly)
- [ ] Support trend options: add, mul, None
- [ ] Support seasonal options: add, mul, None
- [ ] Support damped trend option
- [ ] Return tuple: `(model, metrics_dict, predictions, confidence_intervals)`

### AC3: Exogenous Variable Support
**Given** external regressors improve forecast accuracy
**When** using ARIMAX with exogenous variables
**Then**:
- [ ] `fit_arima()` accepts `X_train: pd.DataFrame | None` for training
- [ ] `fit_arima()` accepts `X_future: pd.DataFrame | None` for prediction
- [ ] Validate regressor dimensions match forecast horizon
- [ ] Handle missing regressors gracefully (fall back to pure ARIMA)

### AC4: Frequency Handling
**Given** financial data may be monthly or quarterly
**When** fitting ARIMA/ETS models
**Then**:
- [ ] Monthly frequency ("M"): seasonal_periods=12
- [ ] Quarterly frequency ("Q"): seasonal_periods=4
- [ ] Auto-detect frequency from Series index if not provided
- [ ] Handle frequency conversion gracefully

### AC5: Return ForecastPoint Compatible Output
**Given** the existing ForecastPoint data structure
**When** returning predictions and confidence intervals
**Then**:
- [ ] Predictions as numpy array of point forecasts
- [ ] Confidence intervals as 2D numpy array (lower, upper bounds)
- [ ] Default confidence level: 95%
- [ ] Output dimensions match forecast_horizon

### AC6: Graceful Fallback on Failure
**Given** ARIMA/ETS fitting may fail on certain data
**When** model fitting encounters errors
**Then**:
- [ ] Log warning with error details
- [ ] Return None or raise specific exception (not generic Exception)
- [ ] Caller can fall back to Prophet or other model
- [ ] Common failures handled: insufficient data, convergence issues, singular matrix

### AC7: Unit Test Coverage
**Given** the need for reliable model wrappers
**When** running the test suite
**Then**:
- [ ] Unit tests in `tests/unit/test_arima_ets_models.py`
- [ ] Coverage >80% for new functions
- [ ] Test cases: basic fit, with regressors, monthly, quarterly, edge cases
- [ ] Test fallback behavior on known failure cases
- [ ] Mock external dependencies for fast tests

---

## Technical Design

### New Dependency

```toml
# pyproject.toml
[project.dependencies]
pmdarima = ">=2.0,<3.0"  # Auto-ARIMA model selection
```

### File Structure

```
raglite/forecasting/
  models/
    arima_model.py       # NEW: ARIMA/SARIMA implementation (~200 LOC)
    ets_model.py         # NEW: ETS implementation (~150 LOC)
    __init__.py          # UPDATE: Add exports
```

### Function Signatures

```python
# raglite/forecasting/models/arima_model.py

from typing import Any
import numpy as np
import pandas as pd

async def fit_arima(
    y_train: pd.Series,
    X_train: pd.DataFrame | None = None,
    X_future: pd.DataFrame | None = None,
    forecast_horizon: int = 4,
    frequency: str = "M",
    confidence_level: float = 0.95,
) -> tuple[Any, dict, np.ndarray, np.ndarray]:
    """Fit ARIMA/SARIMA using pmdarima auto_arima.

    Args:
        y_train: Historical time series data
        X_train: Exogenous regressors for training (optional)
        X_future: Exogenous regressors for forecast period (optional)
        forecast_horizon: Number of periods to forecast
        frequency: Time frequency ("M" for monthly, "Q" for quarterly)
        confidence_level: Confidence interval level (default 0.95)

    Returns:
        Tuple of (model, metrics_dict, predictions, confidence_intervals)
        - model: Fitted ARIMA model object
        - metrics_dict: {"aic": float, "order": tuple, "seasonal_order": tuple}
        - predictions: numpy array of point forecasts
        - confidence_intervals: 2D array [[lower, upper], ...]

    Raises:
        ValueError: If data is insufficient for ARIMA fitting
        RuntimeError: If model convergence fails
    """
    import pmdarima as pm

    seasonal_period = 12 if frequency == "M" else 4

    model = pm.auto_arima(
        y_train,
        X=X_train,
        seasonal=True,
        m=seasonal_period,
        stepwise=True,
        suppress_warnings=True,
        max_p=3,
        max_q=3,
        max_d=2,
        max_P=2,
        max_Q=2,
        max_D=1,
        information_criterion='aic',
        error_action='ignore',
    )

    predictions, conf_int = model.predict(
        n_periods=forecast_horizon,
        X=X_future,
        return_conf_int=True,
        alpha=1 - confidence_level,
    )

    metrics = {
        "aic": model.aic(),
        "order": model.order,
        "seasonal_order": model.seasonal_order,
    }

    return model, metrics, predictions, conf_int
```

```python
# raglite/forecasting/models/ets_model.py

from typing import Any
import numpy as np
import pandas as pd

async def fit_ets(
    y_train: pd.Series,
    forecast_horizon: int = 4,
    frequency: str = "M",
    trend: str | None = "add",
    seasonal: str | None = "add",
    damped_trend: bool = True,
    confidence_level: float = 0.95,
) -> tuple[Any, dict, np.ndarray, np.ndarray]:
    """Fit ETS using statsmodels ExponentialSmoothing.

    Args:
        y_train: Historical time series data
        forecast_horizon: Number of periods to forecast
        frequency: Time frequency ("M" for monthly, "Q" for quarterly)
        trend: Trend component type ("add", "mul", None)
        seasonal: Seasonal component type ("add", "mul", None)
        damped_trend: Whether to use damped trend
        confidence_level: Confidence interval level (default 0.95)

    Returns:
        Tuple of (model, metrics_dict, predictions, confidence_intervals)
        - model: Fitted ETS model object
        - metrics_dict: {"aic": float, "bic": float}
        - predictions: numpy array of point forecasts
        - confidence_intervals: 2D array [[lower, upper], ...]

    Raises:
        ValueError: If data is insufficient for ETS fitting
        RuntimeError: If model optimization fails
    """
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    seasonal_periods = 12 if frequency == "M" else 4

    # Ensure data length supports seasonality
    if len(y_train) < 2 * seasonal_periods:
        seasonal = None  # Disable seasonality for short series

    model = ExponentialSmoothing(
        y_train,
        trend=trend,
        seasonal=seasonal,
        damped_trend=damped_trend if trend else False,
        seasonal_periods=seasonal_periods if seasonal else None,
    ).fit(optimized=True)

    # Generate forecast
    forecast = model.get_forecast(steps=forecast_horizon)
    predictions = forecast.predicted_mean.values

    # Get confidence intervals
    conf_int = forecast.conf_int(alpha=1 - confidence_level).values

    metrics = {
        "aic": model.aic,
        "bic": model.bic,
        "sse": model.sse,
    }

    return model, metrics, predictions, conf_int
```

### Lazy Loading Pattern

Following the established pattern in hybrid.py:

```python
# raglite/forecasting/models/arima_model.py

def _get_pmdarima() -> Any:
    """Lazy load pmdarima to avoid import overhead."""
    import pmdarima as pm
    return pm
```

### Error Handling

```python
class ARIMAFittingError(Exception):
    """Raised when ARIMA fitting fails."""
    pass

class ETSFittingError(Exception):
    """Raised when ETS fitting fails."""
    pass

# Usage in fit_arima:
try:
    model = pm.auto_arima(...)
except Exception as e:
    logger.warning(f"ARIMA fitting failed: {e}")
    raise ARIMAFittingError(f"Failed to fit ARIMA: {e}") from e
```

---

## Tasks / Subtasks

### Task 1: Add pmdarima Dependency (AC1)
- [ ] Add `pmdarima>=2.0,<3.0` to pyproject.toml
- [ ] Run `uv sync` to install
- [ ] Verify import: `python -c "import pmdarima; print(pmdarima.__version__)"`

### Task 2: Create arima_model.py (AC1, AC3, AC4, AC5, AC6)
- [ ] Create `raglite/forecasting/models/arima_model.py`
- [ ] Implement `_get_pmdarima()` lazy loader
- [ ] Implement `fit_arima()` async function
- [ ] Add support for exogenous regressors (X_train, X_future)
- [ ] Handle monthly (m=12) and quarterly (m=4) frequencies
- [ ] Return (model, metrics, predictions, conf_int) tuple
- [ ] Add `ARIMAFittingError` exception class
- [ ] Add graceful fallback on fitting failures
- [ ] Add docstrings and type hints
- [ ] Verify: `python -c "from raglite.forecasting.models.arima_model import fit_arima"`

### Task 3: Create ets_model.py (AC2, AC4, AC5, AC6)
- [ ] Create `raglite/forecasting/models/ets_model.py`
- [ ] Implement `fit_ets()` async function
- [ ] Support trend options: "add", "mul", None
- [ ] Support seasonal options: "add", "mul", None
- [ ] Support damped trend option
- [ ] Handle monthly (periods=12) and quarterly (periods=4) frequencies
- [ ] Return (model, metrics, predictions, conf_int) tuple
- [ ] Add `ETSFittingError` exception class
- [ ] Add graceful fallback on fitting failures
- [ ] Add docstrings and type hints
- [ ] Verify: `python -c "from raglite.forecasting.models.ets_model import fit_ets"`

### Task 4: Update models/__init__.py (AC1, AC2)
- [ ] Add exports for `fit_arima`, `ARIMAFittingError`
- [ ] Add exports for `fit_ets`, `ETSFittingError`
- [ ] Verify: `python -c "from raglite.forecasting.models import fit_arima, fit_ets"`

### Task 5: Create Unit Tests (AC7)
- [ ] Create `tests/unit/test_arima_ets_models.py`
- [ ] Test `fit_arima()` with basic time series
- [ ] Test `fit_arima()` with exogenous regressors
- [ ] Test `fit_arima()` with monthly frequency
- [ ] Test `fit_arima()` with quarterly frequency
- [ ] Test `fit_arima()` error handling and fallback
- [ ] Test `fit_ets()` with basic time series
- [ ] Test `fit_ets()` with different trend/seasonal options
- [ ] Test `fit_ets()` error handling and fallback
- [ ] Test output format matches ForecastPoint expectations
- [ ] Run: `pytest tests/unit/test_arima_ets_models.py -v`

### Task 6: Validate Coverage (AC7)
- [ ] Run coverage: `pytest tests/unit/test_arima_ets_models.py --cov=raglite/forecasting/models/arima_model --cov=raglite/forecasting/models/ets_model --cov-report=term-missing`
- [ ] Verify >80% coverage
- [ ] Add tests for any uncovered paths

### Task 7: Integration Smoke Test
- [ ] Verify models work with real data shape
- [ ] Test with sample from existing forecast data
- [ ] Verify output dimensions match forecast_horizon
- [ ] Run: `pytest tests/unit/test_arima_ets_models.py -v`

---

## Dev Notes

### Architecture References

- **Models Package Structure:** `docs/architecture/6-complete-reference-implementation.md` (Section 11.2) defines the models package pattern with `fit_*` function signatures and return types
- **Async Patterns:** `docs/architecture/5-technology-stack-definitive.md` (async/await section) defines async function usage for all I/O and long-running operations
- **Lazy Loading Standards:** `docs/architecture/6-complete-reference-implementation.md` (Section 11.2.1) documents the `_get_library()` pattern used across all ML model imports
- **Model Interface Consistency:** See `raglite/forecasting/models/` after Story 7.5 completion for the canonical `fit_*` return signature

### statsmodels Already Available

The `statsmodels` library is already a dependency (via Prophet). No additional installation needed for ETS.

### pmdarima Installation Notes

pmdarima may have platform-specific build requirements:
- macOS: May need `libomp` for OpenMP support
- Linux: Standard pip install works
- Windows: Pre-built wheels available

### Lazy Loading Pattern

All heavy ML libraries in this codebase use lazy loading to reduce startup time. Follow the pattern from `docs/architecture/6-complete-reference-implementation.md` Section 11.2.1:

```python
def _get_pmdarima() -> Any:
    """Lazy load pmdarima."""
    import pmdarima as pm
    return pm
```

### Model Interface Consistency

All `fit_*` functions in this codebase return a consistent tuple (see `docs/architecture/6-complete-reference-implementation.md` Section 11.2):
```python
(model, metrics_dict, predictions, confidence_intervals)
```

Maintain this pattern for ARIMA/ETS to enable seamless integration with model selection (Story 7.3).

### Async Pattern

Even though ARIMA/ETS fitting is synchronous, use async function signature to match existing patterns per `docs/architecture/5-technology-stack-definitive.md`:

```python
async def fit_arima(...) -> tuple[...]:
    # Synchronous fitting wrapped in async
    ...
```

### Testing Strategy

1. Use synthetic data for basic tests (predictable behavior)
2. Use fixtures for edge cases (short series, missing data)
3. Mock pmdarima for failure scenario tests
4. Compare output shapes, not exact values

### File Size Target

- `arima_model.py`: ~200 LOC
- `ets_model.py`: ~150 LOC
- `test_arima_ets_models.py`: ~150 LOC

All well under the 500 LOC limit.

---

## References

- [Epic 7: Intelligent Model Selection](../../prd/epic-7-intelligent-model-selection.md) - Parent epic
- [pmdarima Documentation](https://alkaline-ml.com/pmdarima/) - auto_arima reference
- [statsmodels ETS](https://www.statsmodels.org/stable/generated/statsmodels.tsa.holtwinters.ExponentialSmoothing.html) - ETS reference
- [Story 7.5](./7-5-refactor-hybrid-py-forecasting-modules.md) - Models package structure reference
- [Coding Standards](../../../.claude/rules/coding-standards.md) - Code patterns

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
- `raglite/forecasting/models/arima_model.py` (~200 LOC)
- `raglite/forecasting/models/ets_model.py` (~150 LOC)
- `tests/unit/test_arima_ets_models.py` (~150 LOC)

**Files to Modify:**
- `pyproject.toml` (+1 line: pmdarima dependency)
- `raglite/forecasting/models/__init__.py` (+4 lines: exports)

**Total New Code:** ~500 LOC
