# Story 7b-3: Per-Variable Model Selection via Cross-Validation

Status: Drafted

## Story Header

- **Epic:** 7b - Intelligent Model Selection Framework
- **Priority:** P0
- **Effort:** 2.5 days
- **Status:** drafted
- **Dependencies:** 7b-1 (ARIMA/ETS wrappers) - DONE, 7b-2 (Data characteristics analyzer) - DONE

## User Story

As a forecasting system,
I want to cross-validate ALL 9 available models per variable and automatically select the optimal model,
so that each financial metric uses the most accurate forecasting model based on empirical holdout performance.

## Background

Currently, Prophet is used for all variables regardless of data characteristics, resulting in poor accuracy for some metrics (e.g., EBITDA: 84.77% MAPE). With 9 models now available (ARIMA, ETS, Prophet, XGBoost, LightGBM, CatBoost, Chronos-2, TFT, Linear), this story implements a cross-validation framework to select the best model per variable.

## Acceptance Criteria

### AC-7b.3.1: TimeSeriesSplit Cross-Validation Implementation

**Given** a historical time series for a financial variable with at least 12 data points
**When** `select_best_model()` is called with the variable data
**Then** the function performs time-series aware cross-validation using `sklearn.model_selection.TimeSeriesSplit` with configurable folds (default: 5)

**Verification:**
- TimeSeriesSplit is used instead of random k-fold (respects temporal order)
- Default 5-fold CV with minimum 12 observations enforced
- Each fold maintains proper train/test split without data leakage

### AC-7b.3.2: All 9 Models Tested

**Given** the model selection framework is initialized
**When** cross-validation runs for a variable
**Then** ALL 9 available models are tested:
  - ARIMA (from Story 7b-1)
  - ETS (from Story 7b-1)
  - Prophet (existing)
  - XGBoost (existing)
  - LightGBM (existing)
  - CatBoost (existing)
  - Chronos-2 (existing, zero-shot)
  - TFT (existing, requires training)
  - Linear/Ridge/Lasso (existing)

**Verification:**
- `CANDIDATE_MODELS` list contains all 9 models
- Each model is attempted during CV (unless filtered by pre-selection logic)
- TFT training is handled on-demand with checkpoint caching

### AC-7b.3.3: Regressor Comparison

**Given** external regressors are available for a variable
**When** model selection runs
**Then** each model is tested BOTH with and without regressors, resulting in up to 18 configurations per variable (9 models x 2 regressor modes)

**Verification:**
- Two runs per model: `{model}_False` and `{model}_True`
- Only regressor-capable models use regressors (skip for Chronos-2 in regressor mode)
- Best configuration includes `best_with_regressors` and `best_regressor_set` in result

### AC-7b.3.4: MAPE/MASE Selection Criteria

**Given** cross-validation results for all model configurations
**When** selecting the best model
**Then** selection is based on:
  1. Primary: Holdout MAPE (lower is better)
  2. Secondary: MASE (lower is better, used as tiebreaker)

**Verification:**
- Best model selected by `min(mape)` first, then `min(mase)` for ties
- Both metrics stored in `ModelSelectionResult.best_mape` and `ModelSelectionResult.best_mase`
- Selection criteria documented in result metadata

### AC-7b.3.5: Graceful Model Failure Handling

**Given** a model fails during cross-validation (fitting error, convergence failure, etc.)
**When** the failure occurs
**Then** the model is skipped with a warning log, and selection continues with remaining models

**Verification:**
- `try/except` around each model evaluation
- Warning logged with model name and error message
- At least one model must succeed or raise `ModelSelectionError`
- Failed models excluded from `candidate_results` or marked with `error` status

### AC-7b.3.6: ModelSelectionResult Output

**Given** model selection completes successfully
**When** results are returned
**Then** a `ModelSelectionResult` dataclass is returned containing:
  - `variable_name`: str
  - `best_model`: str (e.g., "arima", "prophet")
  - `best_mape`: float
  - `best_mase`: float
  - `best_with_regressors`: bool
  - `best_regressor_set`: list[str]
  - `candidate_results`: dict[str, dict] (all tested configurations)
  - `data_characteristics`: DataCharacteristics (from Story 7b-2)
  - `cv_folds`: int
  - `runtime_seconds`: float

**Verification:**
- All fields populated with valid values
- `candidate_results` contains entries for all tested models
- Serializable to JSON for caching (Story 7b-4)

### AC-7b.3.7: Runtime Performance

**Given** model selection is running for a single variable
**When** all 9 models are cross-validated with 5 folds
**Then** total runtime is less than 10 minutes per variable

**Verification:**
- Performance test with timeout assertion
- TFT training uses reduced epochs (50) and early stopping (5 epochs)
- Parallel model evaluation where possible
- Chronos-2 uses efficient zero-shot inference

## Technical Specification

### File: raglite/forecasting/model_selection.py (Create - ~500 lines)

```python
"""Model selection via cross-validation for per-variable optimal model choice."""

from dataclasses import dataclass, field
from typing import Any
import time
import logging
import asyncio

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit

from raglite.forecasting.data_analyzer import (
    analyze_data_characteristics,
    DataCharacteristics,
)

logger = logging.getLogger(__name__)

# All 9 available models
CANDIDATE_MODELS = [
    "arima",      # NEW - Story 7b-1
    "ets",        # NEW - Story 7b-1
    "prophet",    # Existing
    "xgboost",    # Existing
    "lightgbm",   # Existing
    "catboost",   # Existing
    "chronos",    # Existing (Chronos-2)
    "tft",        # Existing (if trained)
    "linear",     # Existing (Linear/Ridge/Lasso)
]


@dataclass
class ModelSelectionResult:
    """Result of model selection cross-validation."""

    variable_name: str
    best_model: str
    best_mape: float
    best_mase: float
    best_with_regressors: bool
    best_regressor_set: list[str] = field(default_factory=list)
    candidate_results: dict[str, dict] = field(default_factory=dict)
    data_characteristics: DataCharacteristics | None = None
    cv_folds: int = 5
    runtime_seconds: float = 0.0


async def select_best_model(
    variable_name: str,
    historical_data: pd.Series,
    external_regressors: dict[str, pd.Series] | None = None,
    cv_folds: int = 5,
    force_refresh: bool = False,
) -> ModelSelectionResult:
    """Select best model for variable via cross-validation.

    Args:
        variable_name: Name of the financial variable
        historical_data: Time series data (pandas Series with DatetimeIndex)
        external_regressors: Optional dict of regressor name -> Series
        cv_folds: Number of CV folds (default: 5)
        force_refresh: Ignore any cached results

    Returns:
        ModelSelectionResult with best model and all candidate results

    Raises:
        ValueError: If historical_data has fewer than 12 points
        ModelSelectionError: If all models fail
    """
    start_time = time.time()

    # Validate minimum data points
    if len(historical_data) < 12:
        raise ValueError(
            f"Variable {variable_name} has only {len(historical_data)} points, "
            "minimum 12 required for cross-validation"
        )

    # 1. Analyze data characteristics (Story 7b-2)
    data_chars = analyze_data_characteristics(historical_data)

    # 2. Pre-filter models based on data characteristics
    candidate_models = _filter_candidates(data_chars, CANDIDATE_MODELS)

    # 3. Cross-validate each model
    tscv = TimeSeriesSplit(n_splits=cv_folds)
    results: dict[str, dict] = {}

    for model_name in candidate_models:
        for use_regs in [False, True]:
            # Skip regressor mode for models that don't support it
            if use_regs and model_name == "chronos":
                continue

            config_key = f"{model_name}_{use_regs}"

            try:
                cv_metrics = await _cv_evaluate(
                    model_name,
                    historical_data,
                    external_regressors if use_regs else None,
                    tscv,
                    variable_name,
                )
                results[config_key] = cv_metrics
                logger.info(
                    f"Model {config_key} CV complete",
                    extra={
                        "variable": variable_name,
                        "mape": cv_metrics["mape"],
                        "mase": cv_metrics["mase"],
                    },
                )
            except Exception as e:
                logger.warning(
                    f"Model {model_name} failed for {variable_name}: {e}",
                    extra={"model": model_name, "error": str(e)},
                )
                results[config_key] = {"error": str(e), "mape": float("inf"), "mase": float("inf")}

    # 4. Ensure at least one model succeeded
    valid_results = {k: v for k, v in results.items() if "error" not in v}
    if not valid_results:
        raise ModelSelectionError(
            f"All models failed for variable {variable_name}. "
            f"Errors: {results}"
        )

    # 5. Select best by MAPE (primary), then MASE (secondary)
    best_key = min(
        valid_results.items(),
        key=lambda x: (x[1]["mape"], x[1]["mase"])
    )[0]

    # Parse best configuration
    best_model, use_regs_str = best_key.rsplit("_", 1)
    best_with_regressors = use_regs_str == "True"
    best_metrics = valid_results[best_key]

    runtime = time.time() - start_time

    return ModelSelectionResult(
        variable_name=variable_name,
        best_model=best_model,
        best_mape=best_metrics["mape"],
        best_mase=best_metrics["mase"],
        best_with_regressors=best_with_regressors,
        best_regressor_set=list(external_regressors.keys()) if best_with_regressors and external_regressors else [],
        candidate_results=results,
        data_characteristics=data_chars,
        cv_folds=cv_folds,
        runtime_seconds=runtime,
    )


class ModelSelectionError(Exception):
    """Raised when model selection fails completely."""
    pass
```

### TFT Training Integration

```python
# TFT on-demand training within _cv_evaluate()

async def _train_tft_if_needed(
    variable_name: str,
    train_data: pd.Series,
    regressors: dict[str, pd.Series] | None,
) -> Any:
    """Train TFT model if checkpoint missing or expired.

    Args:
        variable_name: Variable name for checkpoint path
        train_data: Training data
        regressors: Optional external regressors

    Returns:
        Trained TFT model or loaded checkpoint
    """
    from pathlib import Path
    import torch

    checkpoint_dir = Path(f"models/tft/{variable_name}")
    checkpoint_path = checkpoint_dir / "best_model.ckpt"

    # Check for valid checkpoint (exists and < 7 days old)
    if checkpoint_path.exists():
        mtime = checkpoint_path.stat().st_mtime
        age_days = (time.time() - mtime) / 86400
        if age_days < 7:
            # Load existing checkpoint
            logger.info(f"Loading TFT checkpoint for {variable_name} (age: {age_days:.1f} days)")
            return _load_tft_checkpoint(checkpoint_path)

    # Train new model with reduced epochs
    logger.info(f"Training TFT for {variable_name} (max_epochs=50, early_stopping=5)")

    model = await _train_tft(
        train_data,
        regressors,
        max_epochs=50,  # Reduced from 100
        early_stopping_patience=5,
        checkpoint_dir=checkpoint_dir,
    )

    return model
```

### Files to Create

| File | Action | Lines |
|------|--------|-------|
| raglite/forecasting/model_selection.py | Create | +500 |
| tests/integration/test_model_selection.py | Create | +250 |

## Tasks

- [ ] Task 1: Create model_selection.py module structure [AC-7b.3.1, AC-7b.3.2]
  - [ ] 1.1 Create file with imports and logger setup
  - [ ] 1.2 Define CANDIDATE_MODELS list with all 9 models
  - [ ] 1.3 Implement ModelSelectionResult dataclass
  - [ ] 1.4 Implement ModelSelectionError exception class

- [ ] Task 2: Implement select_best_model() main function [AC-7b.3.1, AC-7b.3.4]
  - [ ] 2.1 Validate minimum 12 data points
  - [ ] 2.2 Call data analyzer (Story 7b-2)
  - [ ] 2.3 Set up TimeSeriesSplit with configurable folds
  - [ ] 2.4 Implement selection logic (MAPE primary, MASE secondary)
  - [ ] 2.5 Build and return ModelSelectionResult

- [ ] Task 3: Implement _filter_candidates() pre-selection [AC-7b.3.2]
  - [ ] 3.1 Filter based on stationarity (prefer ARIMA/ETS for stationary)
  - [ ] 3.2 Filter based on seasonality (prefer SARIMA/Prophet for seasonal)
  - [ ] 3.3 Filter based on data length (Chronos-2 for cold-start <12 points)
  - [ ] 3.4 Always include TFT as candidate

- [ ] Task 4: Implement _cv_evaluate() cross-validation [AC-7b.3.1, AC-7b.3.3, AC-7b.3.5]
  - [ ] 4.1 Iterate through TimeSeriesSplit folds
  - [ ] 4.2 Train model on train fold, predict on test fold
  - [ ] 4.3 Calculate MAPE and MASE for each fold
  - [ ] 4.4 Aggregate fold metrics (mean MAPE/MASE)
  - [ ] 4.5 Handle model failures with try/except and logging

- [ ] Task 5: Implement model-specific fitting functions [AC-7b.3.2]
  - [ ] 5.1 _fit_arima_cv() - use fit_arima from hybrid.py
  - [ ] 5.2 _fit_ets_cv() - use fit_ets from hybrid.py
  - [ ] 5.3 _fit_prophet_cv() - use existing Prophet fitting
  - [ ] 5.4 _fit_xgboost_cv() - use existing XGBoost fitting
  - [ ] 5.5 _fit_lightgbm_cv() - use existing LightGBM fitting
  - [ ] 5.6 _fit_catboost_cv() - use existing CatBoost fitting
  - [ ] 5.7 _fit_chronos_cv() - use existing Chronos-2 (zero-shot)
  - [ ] 5.8 _fit_tft_cv() - with on-demand training
  - [ ] 5.9 _fit_linear_cv() - use existing Linear/Ridge/Lasso

- [ ] Task 6: Implement TFT on-demand training [AC-7b.3.2, AC-7b.3.7]
  - [ ] 6.1 Create _train_tft_if_needed() function
  - [ ] 6.2 Check for existing checkpoint in models/tft/{variable}/
  - [ ] 6.3 Validate checkpoint age (<7 days TTL)
  - [ ] 6.4 Train with reduced epochs (50) and early stopping (5)
  - [ ] 6.5 Save checkpoint after training
  - [ ] 6.6 Auto-detect GPU (CUDA/MPS)

- [ ] Task 7: Implement regressor handling [AC-7b.3.3]
  - [ ] 7.1 Test each model with and without regressors
  - [ ] 7.2 Skip regressor mode for models that don't support it (Chronos-2)
  - [ ] 7.3 Align regressor data with training windows
  - [ ] 7.4 Store best_regressor_set in result

- [ ] Task 8: Implement metrics calculation [AC-7b.3.4]
  - [ ] 8.1 Implement calculate_mape() function
  - [ ] 8.2 Implement calculate_mase() function
  - [ ] 8.3 Handle edge cases (zeros, small values)
  - [ ] 8.4 Add metric validation (finite, non-negative)

- [ ] Task 9: Write integration tests [AC-7b.3.6]
  - [ ] 9.1 Create tests/integration/test_model_selection.py
  - [ ] 9.2 Test select_best_model() with real data
  - [ ] 9.3 Test all 9 models are attempted
  - [ ] 9.4 Test regressor comparison
  - [ ] 9.5 Test graceful failure handling
  - [ ] 9.6 Test ModelSelectionResult serialization

- [ ] Task 10: Performance optimization and testing [AC-7b.3.7]
  - [ ] 10.1 Add runtime measurement to select_best_model()
  - [ ] 10.2 Create performance test with <10 minute assertion
  - [ ] 10.3 Optimize parallel model evaluation where possible
  - [ ] 10.4 Verify TFT training completes within budget

- [ ] Task 11: Validation (MANDATORY)
  - [ ] 11.1 Run unit tests: `uv run pytest tests/unit/test_model_selection*.py -v`
  - [ ] 11.2 Run integration tests: `uv run pytest tests/integration/test_model_selection.py -v`
  - [ ] 11.3 Test with real variable data (e.g., EBITDA)
  - [ ] 11.4 Verify all 9 models attempted
  - [ ] 11.5 Verify runtime <10 minutes per variable

## Dev Notes

### Architecture References

- [Source: docs/prd/epic-7-intelligent-model-selection.md#Story 7.3]
- [Source: docs/architecture/5-technology-stack-definitive.md]
- [Source: raglite/forecasting/hybrid.py] - Existing model implementations
- [Source: raglite/forecasting/data_analyzer.py] - Story 7b-2 data characteristics

### Existing Patterns to Follow

**Model Fitting Pattern (hybrid.py):**
```python
# All existing model fitting follows this pattern
async def fit_model(
    y_train: pd.Series,
    X_train: pd.DataFrame | None = None,
    forecast_horizon: int = 4,
    frequency: str = "M",
) -> tuple[Any, dict, np.ndarray, np.ndarray]:
    """Fit model and return predictions + confidence intervals."""
    ...
```

**Cross-Validation Pattern (sklearn):**
```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)
for train_idx, test_idx in tscv.split(data):
    train, test = data.iloc[train_idx], data.iloc[test_idx]
    # Fit on train, evaluate on test
```

### Key Technical Details

1. **TimeSeriesSplit vs Random KFold:**
   - TimeSeriesSplit respects temporal order (no future data leakage)
   - Each fold uses earlier data for training, later data for testing
   - More realistic for time-series forecasting evaluation

2. **MAPE vs MASE:**
   - MAPE: Mean Absolute Percentage Error - intuitive, but undefined for zeros
   - MASE: Mean Absolute Scaled Error - scale-independent, handles zeros
   - Use MAPE as primary (business interpretable), MASE as tiebreaker

3. **Pre-filtering Logic:**
   - Stationary data -> prefer ARIMA, ETS
   - Strong seasonality -> prefer SARIMA, Prophet, ETS
   - High volatility -> prefer XGBoost, LightGBM, CatBoost
   - Cold-start (<12 points) -> Chronos-2 (zero-shot)
   - TFT always included (powerful for multivariate)

4. **TFT Training Strategy:**
   - On-demand training during CV if checkpoint missing
   - Checkpoint caching in models/tft/{variable_name}/
   - 7-day TTL aligned with model selection cache
   - Reduced epochs (50 vs 100) for faster batch processing
   - Early stopping after 5 epochs of no improvement
   - GPU auto-detection (CUDA for NVIDIA, MPS for Apple Silicon)

### Performance Budget

| Component | Target Time |
|-----------|-------------|
| Data analysis | <5 seconds |
| ARIMA CV (5 folds) | <30 seconds |
| ETS CV (5 folds) | <30 seconds |
| Prophet CV (5 folds) | <60 seconds |
| XGBoost CV (5 folds) | <30 seconds |
| LightGBM CV (5 folds) | <30 seconds |
| CatBoost CV (5 folds) | <30 seconds |
| Chronos-2 CV (5 folds) | <60 seconds |
| TFT CV (5 folds, with training) | <5 minutes |
| Linear CV (5 folds) | <10 seconds |
| **Total per variable** | **<10 minutes** |

### Project Structure

**Files to Create:**
- `raglite/forecasting/model_selection.py` - Main model selection logic (~500 lines)
- `tests/integration/test_model_selection.py` - Integration tests (~250 lines)

**Files to Reference:**
- `raglite/forecasting/hybrid.py` - Existing model fitting functions
- `raglite/forecasting/data_analyzer.py` - Story 7b-2 data analyzer
- `raglite/forecasting/adaptive_weights.py` - Story 6.12 weight calculation patterns

### Deprecation Notes

None - this is a new module.

### NFRs

- **Runtime:** <10 minutes per variable for full 9-model CV
- **TFT Training:** <5 minutes with reduced epochs
- **Memory:** Handle 500+ data points per variable
- **Test Coverage:** 80%+ for new code
- **Error Handling:** Graceful degradation when models fail

## Testing Requirements

### Unit Tests (tests/unit/test_model_selection.py)
- Test ModelSelectionResult dataclass
- Test ModelSelectionError exception
- Test _filter_candidates() logic
- Test MAPE/MASE calculation functions
- Test model fitting wrappers
- Mock external dependencies

### Integration Tests (tests/integration/test_model_selection.py)
- Test select_best_model() with real data
- Test all 9 models are evaluated
- Test regressor comparison (with/without)
- Test graceful failure handling
- Test ModelSelectionResult serialization to JSON
- Test TFT checkpoint caching
- Performance test (<10 min assertion)

### Validation Checklist

```bash
# Unit tests
uv run pytest tests/unit/test_model_selection*.py -v

# Integration tests
uv run pytest tests/integration/test_model_selection.py -v

# Performance test
uv run pytest tests/integration/test_model_selection.py -v -k "performance" --timeout=600

# Manual validation with real variable
uv run python -c "
import asyncio
import pandas as pd
from raglite.forecasting.model_selection import select_best_model

# Load real data and test
# result = asyncio.run(select_best_model('ebitda', data))
# print(result)
"
```

## Definition of Done

- [ ] All 7 acceptance criteria verified with passing tests
- [ ] Unit tests passing with 80%+ coverage on new code
- [ ] Integration tests passing
- [ ] Performance test confirms <10 min per variable
- [ ] Code follows existing hybrid.py patterns
- [ ] No new dependencies (uses existing sklearn, pandas, numpy)
- [ ] Docstrings added to all public functions
- [ ] Ready for Story 7b-4 (PostgreSQL caching)

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

(To be filled during implementation)

### Debug Log References

N/A

### Completion Notes List

(To be filled during implementation)

### File List

**To Create:**
- `raglite/forecasting/model_selection.py` - Model selection via cross-validation
- `tests/integration/test_model_selection.py` - Integration tests

**To Reference:**
- `raglite/forecasting/hybrid.py` - Existing model implementations
- `raglite/forecasting/data_analyzer.py` - Story 7b-2 data analyzer
- `raglite/forecasting/adaptive_weights.py` - Weight calculation patterns

### Change Log

- 2025-12-21: Story drafted with all 7 acceptance criteria in BDD format
