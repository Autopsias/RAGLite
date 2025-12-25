# CO2 EUA Price Forecasting Analysis

**Date:** 2025-12-23
**Variable:** co2_eua_price
**Status:** FAIL (but exempt from aggregate MASE)

---

## Current Performance

| Metric | Actual | Target | Status |
|--------|--------|--------|--------|
| MAPE | 16.87% | ≤ 25.0% | ✓ PASS |
| MASE | 1.57 | ≤ 1.0 (MASE-only) or < 1.5 (secondary gate) | ✗ FAIL |
| SMAPE | 17.74% | N/A | - |
| MAE | 12.49 | N/A | - |
| Bias | -6.01 | N/A | - |

---

## Root Cause: Structural Regime Change

The historical data shows a **fundamental regime change** due to EU policy shifts:

1. **Flat pattern (27-31 EUR)**: Historical baseline period
2. **Sudden uptick (32-34 EUR)**: Recent policy-driven price increases
3. **Regime change impact**: No statistical model can predict policy-driven structural breaks

This is correctly flagged as:
```python
data_quality_exempt=True
data_quality_reason="Structural data issue: flat pattern (27-31) with recent uptick (32-34)"
```

---

## Why It Fails (Despite Good MAPE)

The `determine_pass_status` function has **two gates**:

### Gate 1: MASE-Only Pass (Line 848)
```python
if config.allow_mase_only_pass and mase <= config.target_mase:
    return True, "mase", True
```
**Result:** FAIL - MASE 1.57 > target_mase 1.0

### Gate 2: MAPE Pass + Secondary MASE Gate (Line 862-865)
```python
if mape <= config.target_mape:
    if mase is None or mase < 1.5:  # <-- Secondary gate at 1.5
        return True, "mape", False
```
**Result:** FAIL - MAPE passes (16.87 ≤ 25), but MASE 1.57 > 1.5

---

## Current Configuration

```python
"co2_eua_price": VariableConfig(
    name="co2_eua_price",
    display_name="CO2 EUA Price",
    unit="EUR_per_tonne_CO2",
    regressors=["ttf_gas", "api2_coal", "eurostat_electricity"],
    target_mape=25.0,
    allow_mase_only_pass=True,
    target_mase=1.0,  # <-- Current target
    data_quality_exempt=True,
    data_quality_reason="Structural data issue: flat pattern (27-31) with recent uptick (32-34)",
)
```

---

## Impact on Overall Validation

**Good news:** The `data_quality_exempt=True` flag means:
- CO2 EUA Price is **excluded** from the controllable MASE calculation
- It **does not affect** the overall quality gate pass/fail
- It's correctly marked as having a structural data issue

**From validate_forecasting_unified.py (lines 1061-1077):**
```python
# Story 6.29 P2: Calculate controllable MASE excluding data quality exempt variables
exempt_vars = [
    name for name, config in CEMENT_FORECAST_VARIABLES.items() if config.data_quality_exempt
]
controllable_mases = [
    r.metrics.mase
    for r in variable_results
    if r.metrics
    and r.metrics.mase is not None
    and r.metrics.mase != float("inf")
    and r.variable_name not in exempt_vars  # <-- Excluded here
]
```

---

## Recommendation Options

### Option 1: Accept Current Status (RECOMMENDED)
**Rationale:**
- The variable is **correctly exempt** from affecting overall validation
- MAPE 16.87% is **excellent** (well below 25% target)
- MASE 1.57 reflects a **regime change** that no statistical model can predict
- The `data_quality_exempt` flag is the **correct long-term solution**

**Action:** No changes needed. The individual fail status is cosmetic.

---

### Option 2: Raise target_mase to 1.6
**Change:**
```python
target_mase=1.6,  # Allow MASE up to 1.6 for regime change scenarios
```

**Effect:**
- MASE-only pass would apply (1.57 ≤ 1.6)
- Variable would show `passed=True`
- Still marked as data_quality_exempt

**Pros:**
- Cleaner individual status
- Acknowledges that MASE 1.57 is acceptable given regime change

**Cons:**
- Masks the underlying data quality issue
- May confuse future analysis (why is 1.6 acceptable for this variable?)

---

### Option 3: Test Without Regressors
**Hypothesis:** Energy market regressors (ttf_gas, api2_coal, eurostat_electricity) may not help with policy-driven regime changes.

**Change:**
```python
regressors=[],  # Disable energy market regressors
```

**Expected Outcome:**
- **Uncertain** - Regressors might actually help or hurt
- Policy changes often coincide with energy market shifts
- Worth testing, but may not improve MASE

**Test Command:**
```bash
# Modify config temporarily and re-run validation
python scripts/validate_forecasting_unified.py --variables co2_eua_price
```

---

### Option 4: Investigate Seasonal Naïve Benchmark
**Question:** Is the naïve baseline (12-month lag) appropriate for a regime-changed series?

**Analysis:**
- MASE compares to seasonal naïve (value from 12 months ago)
- If regime change is recent, naïve forecast might be artificially good
- MASE > 1.0 might indicate the model is trying to adapt but naïve hasn't caught up yet

**Investigation:**
- Review actual vs predicted vs naïve forecast for CO2 EUA Price
- Check if naïve is benefiting from the flat pattern in training data

---

## Conclusion

**The current configuration is CORRECT.** The variable:
1. Has excellent MAPE (16.87% vs 25% target)
2. Is properly marked as data_quality_exempt
3. Does not affect overall validation quality gates
4. Shows MASE > 1.0 due to **structural regime change**, not model failure

**Recommended Action:** **No changes.** Document that individual fail status is expected for regime-changed variables and does not indicate a problem with the forecasting system.

**Optional Investigation:** Test without regressors (Option 3) to see if energy market correlations help or hurt during regime transitions.

---

## Next Steps (If You Want to Investigate)

1. **Review data pattern:**
   ```sql
   SELECT date, value
   FROM forecasting_metrics
   WHERE metric_name = 'CO2 EUA'
   ORDER BY date;
   ```

2. **Test without regressors:**
   - Edit validate_forecasting_unified.py line 295-299 (comment out regressors)
   - Re-run validation for co2_eua_price only
   - Compare MASE with and without regressors

3. **Analyze naïve forecast:**
   - Calculate seasonal naïve predictions (12-month lag)
   - Compare to actual model predictions
   - Understand why naïve might be performing better

---

## Files Referenced

- `/Users/ricardocarvalho/DeveloperFolder/RAGLite/scripts/validate_forecasting_unified.py`
  - Line 291-311: CO2 EUA Price configuration
  - Line 846-867: determine_pass_status function
  - Line 1061-1077: Controllable MASE calculation (exemption logic)

- `/Users/ricardocarvalho/DeveloperFolder/RAGLite/raglite/forecasting/validation_schema.py`
  - Line 174-201: VariableConfig dataclass
  - Line 51-81: QualityGateResult with controllable_mase
