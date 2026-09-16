# RAGLite Forecasting Validation Report
Generated: 2026-02-02T10:25:51.629084
Runtime: 273.3 seconds

## Overall Assessment: ❌ FAIL

### Quality Gate Results
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Variables Passing MAPE | ≥9/20 | 12/20 | ✅ PASS |
| Variable Cost MAPE | <70.0% | 624095.28% | ❌ FAIL |
| Average MASE | <1.0 | 4361.90 | ❌ FAIL |

### Quick Summary
- **Excellent (MAPE <5%):** 4 variables
- **Good (MAPE 5-15%):** 1 variables
- **Needs Improvement (MAPE 15-30%):** 3 variables
- **Critical (MAPE >30%):** 7 variables

**Average MAPE:** 41702.38%
**Average MASE:** 4361.90 (worse than naïve)
**Average FQS:** 50.5/100 (Moderate)

## Understanding the Metrics

### MAPE (Mean Absolute Percentage Error)
**What it measures:** Average percentage deviation from actual values
**Target:** Variable-specific (see table below)
**Interpretation:**
- <5%: Excellent - suitable for financial reporting
- 5-10%: Good - acceptable for planning
- 10-20%: Moderate - use with caution
- >20%: Poor - investigate root cause

### MASE (Mean Absolute Scaled Error)
**What it measures:** Forecast accuracy relative to a naïve baseline (previous period's value)
**Target:** <1.0 (beating the naïve forecast)
**Interpretation:**
- <0.5: Excellent - model provides significant value over naïve baseline
- 0.5-0.8: Good - model outperforms naïve substantially
- 0.8-1.0: Marginal - model barely beats naïve
- >1.0: Poor - naïve forecast would be better

### SMAPE (Symmetric MAPE)
**What it measures:** Percentage error bounded 0-200%, treats over/under equally
**When to use:** Volatile metrics where MAPE skews results
**Interpretation:** Similar to MAPE but more stable for commodities

### RMSE (Root Mean Square Error)
**What it measures:** Average error in original units, penalizes large errors
**When to use:** When large errors are especially costly (risk management)
**Interpretation:** Lower is better; compare only within same variable

### MAE (Mean Absolute Error)
**What it measures:** Simple average of absolute errors in original units
**When to use:** When you want interpretable error in data units
**Interpretation:** Lower is better; more robust to outliers than RMSE

### Bias (Mean Error)
**What it measures:** Systematic over-prediction (positive) or under-prediction (negative)
**Target:** Close to 0
**Interpretation:**
- Positive: Model tends to over-predict (conservative)
- Negative: Model tends to under-predict (optimistic)
- Near 0: Model is well-calibrated

### FQS (Forecast Quality Score)
**What it measures:** Composite quality metric combining MAPE and MASE (0-100 scale)
**Target:** ≥65 (Good), ≥80 (Excellent)
**Formula:** FQS = 100 × [0.35 × A_MAPE + 0.65 × A_MASE]
**Interpretation:**
- ≥80: Excellent - high confidence in forecast quality
- 65-79: Good - acceptable for planning decisions
- 50-64: Moderate - use with caution
- <50: Poor - forecast needs investigation
**Note:** MASE-weighted (65%) per Hyndman (2006) recommendation for cross-series comparability


## Detailed Variable Analysis

### ❌ Revenue
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

---

### ❌ EBITDA
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 23.15% | <100.0% | ❌ FAIL | Poor - needs investigation |
| MASE | 2.80 | <1.0 | ❌ FAIL | Worse than naïve by 180% |
| SMAPE | 26.83% | - | INFO | Symmetric error |
| RMSE | 59.41 | - | INFO | Error in original units |
| MAE | 52.39 | - | INFO | Average absolute error |
| Bias | -52.39 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 26.9/100 | ≥65 | INFO | Poor quality |

**Assessment:** Poor performance.

---

### ❌ Sales Volume
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 100.00% | <10.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 2.48 | <1.0 | ❌ FAIL | Worse than naïve by 148% |
| SMAPE | 200.00% | - | INFO | Symmetric error |
| RMSE | 572.23 | - | INFO | Error in original units |
| MAE | 565.50 | - | INFO | Average absolute error |
| Bias | -565.50 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 0.0/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ Electricity Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 641.23% | <25.0% | ✅ MASE-ONLY | MASE 0.43 passed (MAPE waived) |
| MASE | 0.43 | <1.0 | ✅ PASS | Beats naïve by 57% |
| SMAPE | 58.34% | - | INFO | Symmetric error |
| RMSE | 36.58 | - | INFO | Error in original units |
| MAE | 26.20 | - | INFO | Average absolute error |
| Bias | +25.04 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 51.1/100 | ≥65 | INFO | Moderate quality |

**Assessment:** Critical performance.

---

### ❌ Thermal Energy Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 142.13% | <10.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 5.83 | <1.0 | ❌ FAIL | Worse than naïve by 483% |
| SMAPE | 66.10% | - | INFO | Symmetric error |
| RMSE | 41.40 | - | INFO | Error in original units |
| MAE | 31.00 | - | INFO | Average absolute error |
| Bias | +27.43 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 0.0/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ❌ Variable Cost per Ton
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 624095.28% | <70.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 65403.39 | <1.0 | ❌ FAIL | Worse than naïve by 6540239% |
| SMAPE | 199.94% | - | INFO | Symmetric error |
| RMSE | 618529.24 | - | INFO | Error in original units |
| MAE | 618529.24 | - | INFO | Average absolute error |
| Bias | +618529.24 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 0.0/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ Pet Coke Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

---

### ✅ Natural Gas Price (TTF)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

---

### ❌ Average Selling Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 103.04% | <9.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 9.07 | <1.0 | ❌ FAIL | Worse than naïve by 807% |
| SMAPE | 170.35% | - | INFO | Symmetric error |
| RMSE | 69.45 | - | INFO | Error in original units |
| MAE | 68.78 | - | INFO | Average absolute error |
| Bias | -68.78 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 0.0/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ Capacity Utilization
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 316.82% | <50.0% | ✅ MASE-ONLY | MASE 1.16 passed (MAPE waived) |
| MASE | 1.16 | <1.0 | ❌ FAIL | Worse than naïve by 16% |
| SMAPE | 122.60% | - | INFO | Symmetric error |
| RMSE | 9.06 | - | INFO | Error in original units |
| MAE | 9.06 | - | INFO | Average absolute error |
| Bias | +9.06 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 27.1/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ CO2 EUA Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

---

### ❌ 3-Month EURIBOR Rate
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 24.77% | <23.0% | ❌ FAIL | Poor - needs investigation |
| MASE | 0.33 | <1.0 | ✅ PASS | Beats naïve by 67% |
| SMAPE | 28.93% | - | INFO | Symmetric error |
| RMSE | 0.54 | - | INFO | Error in original units |
| MAE | 0.50 | - | INFO | Average absolute error |
| Bias | -0.50 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 80.7/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Poor performance.

---

### ✅ Portugal GDP Growth (YoY)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 27.65% | <55.0% | ✅ MASE-ONLY | MASE 0.33 passed (MAPE waived) |
| MASE | 0.33 | <1.0 | ✅ PASS | Beats naïve by 67% |
| SMAPE | 31.93% | - | INFO | Symmetric error |
| RMSE | 0.67 | - | INFO | Error in original units |
| MAE | 0.63 | - | INFO | Average absolute error |
| Bias | -0.49 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 79.4/100 | ≥65 | INFO | Good quality |

**Assessment:** Poor performance.

---

### ✅ Portugal HICP Inflation
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.22% | <20.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.05 | <1.0 | ✅ PASS | Beats naïve by 95% |
| SMAPE | 0.22% | - | INFO | Symmetric error |
| RMSE | 0.29 | - | INFO | Error in original units |
| MAE | 0.28 | - | INFO | Average absolute error |
| Bias | -0.06 | ~0 | INFO | Tends to under-predict |
| FQS | 98.2/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Diesel Price (EU)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.88% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.30 | <1.0 | ✅ PASS | Beats naïve by 70% |
| SMAPE | 1.89% | - | INFO | Symmetric error |
| RMSE | 0.03 | - | INFO | Error in original units |
| MAE | 0.03 | - | INFO | Average absolute error |
| Bias | -0.02 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 89.7/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Construction Output Index
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.15% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.39 | <1.0 | ✅ PASS | Beats naïve by 61% |
| SMAPE | 1.16% | - | INFO | Symmetric error |
| RMSE | 1.67 | - | INFO | Error in original units |
| MAE | 1.33 | - | INFO | Average absolute error |
| Bias | -1.33 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 87.0/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Industrial Production Index
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.68% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.60 | <1.0 | ✅ PASS | Beats naïve by 40% |
| SMAPE | 1.69% | - | INFO | Symmetric error |
| RMSE | 1.83 | - | INFO | Error in original units |
| MAE | 1.65 | - | INFO | Average absolute error |
| Bias | -0.49 | ~0 | INFO | Tends to under-predict |
| FQS | 79.9/100 | ≥65 | INFO | Good quality |

**Assessment:** Excellent performance.

---

### ✅ Building Permits (Portugal)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 12.16% | <25.0% | ✅ PASS (MAPE) | Moderate for FP&A reporting |
| MASE | 1.00 | <1.0 | ❌ FAIL | Worse than naïve by 0% |
| SMAPE | 11.14% | - | INFO | Symmetric error |
| RMSE | 1114.90 | - | INFO | Error in original units |
| MAE | 920.66 | - | INFO | Average absolute error |
| Bias | +920.66 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 63.2/100 | ≥65 | INFO | Moderate quality |

**Assessment:** Moderate performance.

---

### ✅ Construction Confidence Indicator
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 44.50% | <63.0% | ✅ MASE-ONLY | MASE 0.30 passed (MAPE waived) |
| MASE | 0.30 | <1.0 | ✅ PASS | Beats naïve by 70% |
| SMAPE | 50.25% | - | INFO | Symmetric error |
| RMSE | 1.52 | - | INFO | Error in original units |
| MAE | 1.38 | - | INFO | Average absolute error |
| Bias | -0.53 | ~0 | INFO | Tends to under-predict |
| FQS | 74.8/100 | ≥65 | INFO | Good quality |

**Assessment:** Critical performance.

---

## Action Items

### 🔴 Critical - Requires Immediate Attention
| Variable | Issue | MASE | Recommendation |
|----------|-------|------|----------------|
| EBITDA | MASE >1.0 | 2.80 | Evaluate model configuration |
| Sales Volume | MASE >1.0 | 2.48 | Evaluate model configuration |
| Thermal Energy Cost | MASE >1.0 | 5.83 | Evaluate model configuration |
| Variable Cost per Ton | MASE >1.0 | 65403.39 | Evaluate model configuration |
| Average Selling Price | MASE >1.0 | 9.07 | Evaluate model configuration |
| Capacity Utilization | MASE >1.0 | 1.16 | Evaluate model configuration |
| Building Permits (Portugal) | MASE >1.0 | 1.00 | Evaluate model configuration |

### 🟡 Warning - Monitor & Improve
| Variable | Issue | Current | Target | Gap |
|----------|-------|---------|--------|-----|
| Electricity Cost | Exceeds target | 641.23% | 25.0% | +616.23% |
| 3-Month EURIBOR Rate | Exceeds target | 24.77% | 23.0% | +1.77% |

### 🟢 Good Performance - No Action Required
Portugal GDP Growth (YoY), Portugal HICP Inflation, Diesel Price (EU), Construction Output Index, Industrial Production Index, Construction Confidence Indicator


## Actionable Guidance

### ✅ Acceptable (No Action Required)

| Variable | MAPE | MASE | Status |
|----------|------|------|--------|
| Electricity Cost | 641.2% | 0.43 | MASE-only |
| Pet Coke Price | N/A | N/A | Primary |
| Natural Gas Price (TTF) | N/A | N/A | Primary |
| Capacity Utilization | 316.8% | 1.16 | MASE-only |
| CO2 EUA Price | N/A | N/A | Primary |
| Portugal GDP Growth (YoY) | 27.7% | 0.33 | MASE-only |
| Portugal HICP Inflation | 0.2% | 0.05 | Primary |
| Diesel Price (EU) | 1.9% | 0.30 | Primary |
| Construction Output Index | 1.1% | 0.39 | Primary |
| Industrial Production Index | 1.7% | 0.60 | Primary |
| Building Permits (Portugal) | 12.2% | 1.00 | Primary |
| Construction Confidence Indicator | 44.5% | 0.30 | MASE-only |


### 🔧 Needs Data Fix (Requires Reingestion)

**Sales Volume** - MAPE 100.0% and MASE 2.48 both poor
- **Root Cause:** Likely data quality issue (entity mixing, wrong aliases, scale mismatch)
- **Fix:** 1) Check db_metric_aliases for incorrect mappings
2) Verify entity filter (GROUP vs individual entities)
3) Check for scale mismatches (thousands vs units)
- **Expected Improvement:** 50-90% reduction in MAPE after data fix

**Thermal Energy Cost** - MAPE 142.1% and MASE 5.83 both poor
- **Root Cause:** Likely data quality issue (entity mixing, wrong aliases, scale mismatch)
- **Fix:** 1) Check db_metric_aliases for incorrect mappings
2) Verify entity filter (GROUP vs individual entities)
3) Check for scale mismatches (thousands vs units)
- **Expected Improvement:** 50-90% reduction in MAPE after data fix

**Variable Cost per Ton** - MAPE 624095.3% and MASE 65403.39 both poor
- **Root Cause:** Likely data quality issue (entity mixing, wrong aliases, scale mismatch)
- **Fix:** 1) Check db_metric_aliases for incorrect mappings
2) Verify entity filter (GROUP vs individual entities)
3) Check for scale mismatches (thousands vs units)
- **Expected Improvement:** 50-90% reduction in MAPE after data fix

**Average Selling Price** - MAPE 103.0% and MASE 9.07 both poor
- **Root Cause:** Likely data quality issue (entity mixing, wrong aliases, scale mismatch)
- **Fix:** 1) Check db_metric_aliases for incorrect mappings
2) Verify entity filter (GROUP vs individual entities)
3) Check for scale mismatches (thousands vs units)
- **Expected Improvement:** 50-90% reduction in MAPE after data fix


### ⚙️ Consider Threshold Adjustment (No Reingestion)

**Revenue** - MAPE 0.0% exceeds threshold 5.5%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**EBITDA** - MAPE 23.2% exceeds threshold 100.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**3-Month EURIBOR Rate** - MAPE 24.8% exceeds threshold but MASE 0.33 is excellent
- **Analysis:** Forecasts follow correct trend but may have systematic bias
- **Recommendation:** Consider enabling MASE-only pass for this variable


### ⚠️ Bias Alerts

| Variable | Bias | Alert |
|----------|------|-------|
| EBITDA | -52.39 | Systematic under-prediction detected (bias=-52.39) |
| Sales Volume | -565.50 | Systematic under-prediction detected (bias=-565.50) |
| Electricity Cost | 25.04 | Systematic over-prediction detected (bias=25.04) |
| Thermal Energy Cost | 27.43 | Systematic over-prediction detected (bias=27.43) |
| Variable Cost per Ton | 618529.24 | Systematic over-prediction detected (bias=618529.24) |
| Average Selling Price | -68.78 | Systematic under-prediction detected (bias=-68.78) |
| Capacity Utilization | 9.06 | Systematic over-prediction detected (bias=9.06) |
| 3-Month EURIBOR Rate | -0.50 | Systematic under-prediction detected (bias=-0.50) |
| Portugal GDP Growth (YoY) | -0.49 | Systematic under-prediction detected (bias=-0.49) |


## Cross-Variable Performance

### MASE Ranking (Lower is Better)
| Rank | Variable | MASE | vs Naïve |
|------|----------|------|----------|
| 1 | Portugal HICP Inflation | 0.05 | 95% better |
| 2 | Construction Confidence Indicator | 0.30 | 70% better |
| 3 | Diesel Price (EU) | 0.30 | 70% better |
| 4 | 3-Month EURIBOR Rate | 0.33 | 67% better |
| 5 | Portugal GDP Growth (YoY) | 0.33 | 67% better |
| 6 | Construction Output Index | 0.39 | 61% better |
| 7 | Electricity Cost | 0.43 | 57% better |
| 8 | Industrial Production Index | 0.60 | 40% better |
| 9 | Building Permits (Portugal) | 1.00 | 0% worse |
| 10 | Capacity Utilization | 1.16 | 16% worse |
| 11 | Sales Volume | 2.48 | 148% worse |
| 12 | EBITDA | 2.80 | 180% worse |
| 13 | Thermal Energy Cost | 5.83 | 483% worse |
| 14 | Average Selling Price | 9.07 | 807% worse |
| 15 | Variable Cost per Ton | 65403.39 | 6540239% worse |

### Variables Where Model Adds Most Value
1. **Portugal HICP Inflation** - MASE 0.05 (95% better than naïve)
2. **Construction Confidence Indicator** - MASE 0.30 (70% better than naïve)
3. **Diesel Price (EU)** - MASE 0.30 (70% better than naïve)

### Variables Where Model Needs Work
1. **Building Permits (Portugal)** - MASE 1.00 (0% worse than naïve)
2. **Capacity Utilization** - MASE 1.16 (16% worse than naïve)
3. **Sales Volume** - MASE 2.48 (148% worse than naïve)
4. **EBITDA** - MASE 2.80 (180% worse than naïve)
5. **Thermal Energy Cost** - MASE 5.83 (483% worse than naïve)
6. **Average Selling Price** - MASE 9.07 (807% worse than naïve)
7. **Variable Cost per Ton** - MASE 65403.39 (6540239% worse than naïve)

### FQS Ranking (Higher is Better)
| Rank | Variable | FQS | Rating |
|------|----------|-----|--------|
| 1 | Portugal HICP Inflation | 98.2 | Excellent |
| 2 | Diesel Price (EU) | 89.7 | Excellent |
| 3 | Construction Output Index | 87.0 | Excellent |
| 4 | 3-Month EURIBOR Rate | 80.7 | Excellent |
| 5 | Industrial Production Index | 79.9 | Good |
| 6 | Portugal GDP Growth (YoY) | 79.4 | Good |
| 7 | Construction Confidence Indicator | 74.8 | Good |
| 8 | Building Permits (Portugal) | 63.2 | Moderate |
| 9 | Electricity Cost | 51.1 | Moderate |
| 10 | Capacity Utilization | 27.1 | Poor |
| 11 | EBITDA | 26.9 | Poor |
| 12 | Sales Volume | 0.0 | Poor |
| 13 | Thermal Energy Cost | 0.0 | Poor |
| 14 | Variable Cost per Ton | 0.0 | Poor |
| 15 | Average Selling Price | 0.0 | Poor |
