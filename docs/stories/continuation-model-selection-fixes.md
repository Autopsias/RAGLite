# Continuation Prompt: Model Selection Fixes for Chronos & TFT

## Context

We completed a deep analysis of why the model selection system is underperforming. Two major issues were identified:

1. **Regressors are NEVER being passed** to model selection - all 20 variables tested without external regressors
2. **TFT model is failing** for most variables due to multiple bugs

The model selection batch run showed Chronos winning 7/20 variables, but with very high MAPEs for many variables (e.g., ebitda: 19443%, variable_cost: 1305%). These could potentially improve dramatically with regressors.

---

## Issue 1: Regressors Never Passed to Model Selection

### Root Cause
In `raglite/forecasting/model_selection_job.py`, both `run_batch_model_selection()` and `run_single_variable_selection()` call `select_best_model()` WITHOUT the `external_regressors` parameter.

### Affected Code Locations

**File: `raglite/forecasting/model_selection_job.py`**

Line 256-258 (batch function):
```python
result = await select_best_model(
    var_name, historical_data=historical_data, force_refresh=force_refresh
)
# MISSING: external_regressors parameter!
```

Line 325-327 (single variable function):
```python
result = await select_best_model(
    variable, historical_data=historical_data, force_refresh=force_refresh
)
# MISSING: external_regressors parameter!
```

### What Exists But Is Unused
- `raglite/forecasting/regressor_config.py` has complete regressor mappings in `METRIC_REGRESSORS`
- `get_default_regressors(metric)` function returns appropriate regressors per variable
- The regressor data fetching infrastructure exists

### Configured Regressors (Currently Unused)
```python
capacity_utilization: ['euribor_3m', 'diesel', 'ttf_gas', 'industrial_production', 'construction_output']
revenue: ['construction_output', 'gdp_growth', 'euribor_3m', 'building_permits']
ebitda: ['euribor_3m', 'ttf_gas', 'diesel', 'api2_coal']
sales_volume: ['construction_output', 'building_permits', 'construction_confidence', 'euribor_3m', 'industrial_production']
electricity_cost: ['ren_electricity', 'ttf_gas']
thermal_cost: ['api2_coal', 'ttf_gas', 'industrial_production']
variable_cost: ['api2_coal', 'ttf_gas', 'industrial_production']
```

### Fix Required
1. Import `get_default_regressors` from `regressor_config.py`
2. For each variable, get the regressor names: `regressor_names = get_default_regressors(var_name)`
3. Fetch the regressor time series data (check how `hybrid.py` does this)
4. Pass `external_regressors=regressor_dict` to `select_best_model()`

---

## Issue 2: TFT Excluded from Regressor Testing

### Root Cause
In `raglite/forecasting/model_selection.py` line 160-161:
```python
# Test with regressors if provided (skip chronos, ets, tft - they don't support regressors)
if external_regressors and model_name not in ("chronos", "ets", "tft"):
```

### Problem
TFT is incorrectly excluded! TFT actually DOES support regressors via the `external_regressors` parameter in `fit_and_forecast_tft()`.

### Fix Required
Change line 161 to:
```python
if external_regressors and model_name not in ("chronos", "ets"):
```

---

## Issue 3: TFT Regressors Hardcoded to None in Subprocess

### Root Cause
In `raglite/forecasting/model_selection_utils.py` line 242-246:
```python
def _run_tft_inference(dates, values, horizon):
    return fit_and_forecast_tft(
        y=y,
        periods_ahead=horizon,
        external_regressors=None,  # HARDCODED TO NONE!
    )
```

Even if we pass regressors to `fit_tft()`, they never reach `fit_and_forecast_tft()`.

### Fix Required
1. Modify `fit_tft()` to accept `external_regressors` parameter
2. Modify `_run_tft_inference()` to accept and pass regressors
3. Serialize regressors for subprocess (convert DataFrame to dict/list)

---

## Issue 4: TFT Minimum Data Requirement Mismatch

### Root Cause
Inconsistent minimum data checks:
- `model_selection_utils.py:200`: `min_required = encoder_length + horizon` (e.g., 12+3=15)
- `tft_model.py:207`: `min_required = encoder_length + horizon + 1` (e.g., 12+3+1=16)

The preprocessing check passes but actual inference fails.

### Fix Required
In `model_selection_utils.py` line 200, change:
```python
min_required = min_encoder_length + horizon
```
To:
```python
min_required = min_encoder_length + horizon + 1
```

---

## Issue 5: Data Availability for TFT

### Current Data Points Per Variable
```
capacity_utilization: 18 points (CV fold: ~14) - TFT FAILS
revenue: 21 points (CV fold: ~16) - TFT borderline
ebitda: 40 points (CV fold: ~32) - TFT OK
sales_volume: 34 points (CV fold: ~27) - TFT OK
gdp_growth: 48 points (CV fold: ~38) - TFT OK
industrial_production: 59 points (CV fold: ~47) - TFT OK
```

TFT needs 16+ points per CV fold. Most variables should work, but some with <20 total points will fail.

### Consideration
For variables with insufficient data, TFT will gracefully return NaN (current behavior is correct). No fix needed, just awareness.

---

## Database Results Location

Model selection results are cached in PostgreSQL:
```sql
SELECT variable_name, best_model, best_mape, use_regressors, regressor_list
FROM model_selection
ORDER BY variable_name;
```

Candidate results (all models tested) are in `candidate_results` JSONB column.

---

## Files to Modify

1. **`raglite/forecasting/model_selection_job.py`**
   - Lines 256-258: Add regressor fetching and passing for batch
   - Lines 325-327: Add regressor fetching and passing for single

2. **`raglite/forecasting/model_selection.py`**
   - Line 161: Remove "tft" from exclusion list

3. **`raglite/forecasting/model_selection_utils.py`**
   - Line 200: Fix minimum data check (+1)
   - Line 179: Add `external_regressors` parameter to `fit_tft()`
   - Lines 231-246: Add regressor passing to `_run_tft_inference()`

---

## Expected Improvements After Fixes

Based on Story 6.25 validation results:
- **ebitda**: Could improve from 19443% to <5% MAPE with regressors
- **variable_cost**: Could improve significantly with energy regressors
- **thermal_cost**: Energy regressors (api2_coal, ttf_gas) should help
- **electricity_cost**: ren_electricity + ttf_gas regressors available

---

## Testing After Fixes

Run model selection for a single variable to verify:
```bash
uv run python3 -c "
import asyncio
from raglite.forecasting.model_selection_job import run_single_variable_selection
asyncio.run(run_single_variable_selection('ebitda'))
"
```

Check that:
1. Candidate results include `*_True` entries (with regressors)
2. TFT produces valid MAPE (not null/nan) for variables with 20+ data points
3. Best model selection considers regressor variants

---

## Git Status Note

There are uncommitted changes from the session that fixed:
- TFT checkpoint loading (ProcessPoolExecutor)
- TFT minimum data check in `tft_model.py`
- Partial fix in `model_selection_utils.py`

Review with `git diff` before continuing.
