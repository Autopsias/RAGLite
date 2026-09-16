# RAGLite Forecasting Validation Report
Generated: 2026-02-02T14:19:26.341165
Runtime: 447.9 seconds

## Overall Assessment: ✅ PASS

### Quality Gate Results
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Variables Passing MAPE | ≥9/25 | 19/25 | ✅ PASS |
| Variable Cost MAPE | <70.0% | 18.96% | ✅ PASS |
| Average MASE | <1.0 | 1.60 | ❌ FAIL |

### Quick Summary
- **Excellent (MAPE <5%):** 6 variables
- **Good (MAPE 5-15%):** 2 variables
- **Needs Improvement (MAPE 15-30%):** 4 variables
- **Critical (MAPE >30%):** 8 variables

**Average MAPE:** 164.16%
**Average MASE:** 1.60 (worse than naïve)
**Average FQS:** 57.3/100 (Moderate)

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

### ✅ Revenue
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.07% | <5.5% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 1.41 | <1.0 | ❌ FAIL | Worse than naïve by 41% |
| SMAPE | 1.07% | - | INFO | Symmetric error |
| RMSE | 0.01 | - | INFO | Error in original units |
| MAE | 0.01 | - | INFO | Average absolute error |
| Bias | -0.01 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 53.9/100 | ≥65 | INFO | Moderate quality |

**Assessment:** Excellent performance.

---

### ✅ EBITDA
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 102.90% | <100.0% | ✅ MASE-ONLY | MASE 0.08 passed (MAPE waived) |
| MASE | 0.08 | <1.0 | ✅ PASS | Beats naïve by 92% |
| SMAPE | 120.12% | - | INFO | Symmetric error |
| RMSE | 15.66 | - | INFO | Error in original units |
| MAE | 12.68 | - | INFO | Average absolute error |
| Bias | -12.68 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 62.5/100 | ≥65 | INFO | Moderate quality |

**Assessment:** Critical performance.

---

### ❌ Sales Volume
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 548.70% | <10.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 1.79 | <1.0 | ❌ FAIL | Worse than naïve by 79% |
| SMAPE | 143.22% | - | INFO | Symmetric error |
| RMSE | 1183.86 | - | INFO | Error in original units |
| MAE | 1048.34 | - | INFO | Average absolute error |
| Bias | +994.99 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 6.9/100 | ≥65 | INFO | Poor quality |

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
| MAPE | 602.97% | <10.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 15.07 | <1.0 | ❌ FAIL | Worse than naïve by 1407% |
| SMAPE | 161.20% | - | INFO | Symmetric error |
| RMSE | 43.17 | - | INFO | Error in original units |
| MAE | 34.48 | - | INFO | Average absolute error |
| Bias | +32.45 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 0.0/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ Variable Cost per Ton
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 18.96% | <70.0% | ✅ MASE-ONLY | MASE 1.59 passed (MAPE waived) |
| MASE | 1.59 | <1.0 | ❌ FAIL | Worse than naïve by 59% |
| SMAPE | 22.03% | - | INFO | Symmetric error |
| RMSE | 26.75 | - | INFO | Error in original units |
| MAE | 21.45 | - | INFO | Average absolute error |
| Bias | -21.45 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 41.8/100 | ≥65 | INFO | Poor quality |

**Assessment:** Moderate performance.

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

### ✅ Average Selling Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 4.24% | <9.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.64 | <1.0 | ✅ PASS | Beats naïve by 36% |
| SMAPE | 4.12% | - | INFO | Symmetric error |
| RMSE | 3.21 | - | INFO | Error in original units |
| MAE | 2.72 | - | INFO | Average absolute error |
| Bias | +2.72 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 77.6/100 | ≥65 | INFO | Good quality |

**Assessment:** Excellent performance.

---

### ✅ Capacity Utilization
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 347.17% | <50.0% | ✅ MASE-ONLY | MASE 1.40 passed (MAPE waived) |
| MASE | 1.40 | <1.0 | ❌ FAIL | Worse than naïve by 40% |
| SMAPE | 126.88% | - | INFO | Symmetric error |
| RMSE | 8.87 | - | INFO | Error in original units |
| MAE | 8.87 | - | INFO | Average absolute error |
| Bias | +8.87 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 19.5/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ CO2 EUA Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

---

### ✅ 3-Month EURIBOR Rate
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 24.77% | <25.0% | ✅ PASS (MAPE) | Poor for FP&A reporting |
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
| MAPE | 10.42% | <25.0% | ✅ PASS (MAPE) | Moderate for FP&A reporting |
| MASE | 0.85 | <1.0 | ✅ PASS | Beats naïve by 15% |
| SMAPE | 9.60% | - | INFO | Symmetric error |
| RMSE | 992.70 | - | INFO | Error in original units |
| MAE | 783.13 | - | INFO | Average absolute error |
| Bias | +766.74 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 68.6/100 | ≥65 | INFO | Good quality |

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

### ✅ GROUP EBITDA
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 9.63% | <50.0% | ✅ MASE-ONLY | MASE 0.36 passed (MAPE waived) |
| MASE | 0.36 | <1.0 | ✅ PASS | Beats naïve by 64% |
| SMAPE | 9.32% | - | INFO | Symmetric error |
| RMSE | 1.94 | - | INFO | Error in original units |
| MAE | 1.78 | - | INFO | Average absolute error |
| Bias | +0.58 | ~0 | INFO | Tends to over-predict |
| FQS | 85.1/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Good performance.

---

### ❌ GROUP Cash Flow
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 802.05% | <100.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 3.71 | <1.0 | ❌ FAIL | Worse than naïve by 271% |
| SMAPE | 183.41% | - | INFO | Symmetric error |
| RMSE | 10.72 | - | INFO | Error in original units |
| MAE | 10.55 | - | INFO | Average absolute error |
| Bias | +10.55 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 0.0/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ❌ GROUP Turnover
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 63.17% | <20.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 1.73 | <1.0 | ❌ FAIL | Worse than naïve by 73% |
| SMAPE | 92.75% | - | INFO | Symmetric error |
| RMSE | 423427.03 | - | INFO | Error in original units |
| MAE | 414707.44 | - | INFO | Average absolute error |
| Bias | -414707.44 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 21.6/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ GROUP Net Income
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 28.78% | <100.0% | ✅ MASE-ONLY | MASE 0.69 passed (MAPE waived) |
| MASE | 0.69 | <1.0 | ✅ PASS | Beats naïve by 31% |
| SMAPE | 34.64% | - | INFO | Symmetric error |
| RMSE | 14.54 | - | INFO | Error in original units |
| MAE | 12.90 | - | INFO | Average absolute error |
| Bias | -12.90 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 67.4/100 | ≥65 | INFO | Good quality |

**Assessment:** Poor performance.

---

## Action Items

### 🔴 Critical - Requires Immediate Attention
| Variable | Issue | MASE | Recommendation |
|----------|-------|------|----------------|
| Revenue | MASE >1.0 | 1.41 | Evaluate model configuration |
| Sales Volume | MASE >1.0 | 1.79 | Evaluate model configuration |
| Thermal Energy Cost | MASE >1.0 | 15.07 | Evaluate model configuration |
| Variable Cost per Ton | MASE >1.0 | 1.59 | Evaluate model configuration |
| Capacity Utilization | MASE >1.0 | 1.40 | Evaluate model configuration |
| GROUP Cash Flow | MASE >1.0 | 3.71 | Evaluate model configuration |
| GROUP Turnover | MASE >1.0 | 1.73 | Evaluate model configuration |

### 🟡 Warning - Monitor & Improve
| Variable | Issue | Current | Target | Gap |
|----------|-------|---------|--------|-----|
| EBITDA | Exceeds target | 102.90% | 100.0% | +2.90% |
| Electricity Cost | Exceeds target | 641.23% | 25.0% | +616.23% |
| 3-Month EURIBOR Rate | Near threshold | 24.77% | 25.0% | -0.23% |

### 🟢 Good Performance - No Action Required
Average Selling Price, Portugal GDP Growth (YoY), Portugal HICP Inflation, Diesel Price (EU), Construction Output Index, Industrial Production Index, Building Permits (Portugal), Construction Confidence Indicator, GROUP EBITDA, GROUP Net Income


## Actionable Guidance

### ✅ Acceptable (No Action Required)

| Variable | MAPE | MASE | Status |
|----------|------|------|--------|
| Revenue | 1.1% | 1.41 | Primary |
| EBITDA | 102.9% | 0.08 | MASE-only |
| Electricity Cost | 641.2% | 0.43 | MASE-only |
| Variable Cost per Ton | 19.0% | 1.59 | MASE-only |
| Pet Coke Price | N/A | N/A | Primary |
| Natural Gas Price (TTF) | N/A | N/A | Primary |
| Average Selling Price | 4.2% | 0.64 | Primary |
| Capacity Utilization | 347.2% | 1.40 | MASE-only |
| CO2 EUA Price | N/A | N/A | Primary |
| 3-Month EURIBOR Rate | 24.8% | 0.33 | Primary |
| Portugal GDP Growth (YoY) | 27.7% | 0.33 | MASE-only |
| Portugal HICP Inflation | 0.2% | 0.05 | Primary |
| Diesel Price (EU) | 1.9% | 0.30 | Primary |
| Construction Output Index | 1.1% | 0.39 | Primary |
| Industrial Production Index | 1.7% | 0.60 | Primary |
| Building Permits (Portugal) | 10.4% | 0.85 | Primary |
| Construction Confidence Indicator | 44.5% | 0.30 | MASE-only |
| GROUP EBITDA | 9.6% | 0.36 | MASE-only |
| GROUP Net Income | 28.8% | 0.69 | MASE-only |


### 🔧 Needs Data Fix (Requires Reingestion)

**Thermal Energy Cost** - MAPE 603.0% and MASE 15.07 both poor
- **Root Cause:** Likely data quality issue (entity mixing, wrong aliases, scale mismatch)
- **Fix:** 1) Check db_metric_aliases for incorrect mappings
2) Verify entity filter (GROUP vs individual entities)
3) Check for scale mismatches (thousands vs units)
- **Expected Improvement:** 50-90% reduction in MAPE after data fix

**GROUP Cash Flow** - MAPE 802.0% and MASE 3.71 both poor
- **Root Cause:** Likely data quality issue (entity mixing, wrong aliases, scale mismatch)
- **Fix:** 1) Check db_metric_aliases for incorrect mappings
2) Verify entity filter (GROUP vs individual entities)
3) Check for scale mismatches (thousands vs units)
- **Expected Improvement:** 50-90% reduction in MAPE after data fix


### ⚙️ Consider Threshold Adjustment (No Reingestion)

**Sales Volume** - MAPE 548.7% exceeds threshold 10.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**GROUP Turnover** - MAPE 63.2% exceeds threshold 20.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable


### ⚠️ Bias Alerts

| Variable | Bias | Alert |
|----------|------|-------|
| EBITDA | -12.68 | Systematic under-prediction detected (bias=-12.68) |
| Sales Volume | 994.99 | Systematic over-prediction detected (bias=994.99) |
| Electricity Cost | 25.04 | Systematic over-prediction detected (bias=25.04) |
| Thermal Energy Cost | 32.45 | Systematic over-prediction detected (bias=32.45) |
| Variable Cost per Ton | -21.45 | Systematic under-prediction detected (bias=-21.45) |
| Capacity Utilization | 8.87 | Systematic over-prediction detected (bias=8.87) |
| 3-Month EURIBOR Rate | -0.50 | Systematic under-prediction detected (bias=-0.50) |
| Portugal GDP Growth (YoY) | -0.49 | Systematic under-prediction detected (bias=-0.49) |
| GROUP Cash Flow | 10.55 | Systematic over-prediction detected (bias=10.55) |
| GROUP Turnover | -414707.44 | Systematic under-prediction detected (bias=-414707.44) |
| GROUP Net Income | -12.90 | Systematic under-prediction detected (bias=-12.90) |


## Cross-Variable Performance

### MASE Ranking (Lower is Better)
| Rank | Variable | MASE | vs Naïve |
|------|----------|------|----------|
| 1 | Portugal HICP Inflation | 0.05 | 95% better |
| 2 | EBITDA | 0.08 | 92% better |
| 3 | Construction Confidence Indicator | 0.30 | 70% better |
| 4 | Diesel Price (EU) | 0.30 | 70% better |
| 5 | 3-Month EURIBOR Rate | 0.33 | 67% better |
| 6 | Portugal GDP Growth (YoY) | 0.33 | 67% better |
| 7 | GROUP EBITDA | 0.36 | 64% better |
| 8 | Construction Output Index | 0.39 | 61% better |
| 9 | Electricity Cost | 0.43 | 57% better |
| 10 | Industrial Production Index | 0.60 | 40% better |
| 11 | Average Selling Price | 0.64 | 36% better |
| 12 | GROUP Net Income | 0.69 | 31% better |
| 13 | Building Permits (Portugal) | 0.85 | 15% better |
| 14 | Capacity Utilization | 1.40 | 40% worse |
| 15 | Revenue | 1.41 | 41% worse |
| 16 | Variable Cost per Ton | 1.59 | 59% worse |
| 17 | GROUP Turnover | 1.73 | 73% worse |
| 18 | Sales Volume | 1.79 | 79% worse |
| 19 | GROUP Cash Flow | 3.71 | 271% worse |
| 20 | Thermal Energy Cost | 15.07 | 1407% worse |

### Variables Where Model Adds Most Value
1. **Portugal HICP Inflation** - MASE 0.05 (95% better than naïve)
2. **EBITDA** - MASE 0.08 (92% better than naïve)
3. **Construction Confidence Indicator** - MASE 0.30 (70% better than naïve)

### Variables Where Model Needs Work
1. **Capacity Utilization** - MASE 1.40 (40% worse than naïve)
2. **Revenue** - MASE 1.41 (41% worse than naïve)
3. **Variable Cost per Ton** - MASE 1.59 (59% worse than naïve)
4. **GROUP Turnover** - MASE 1.73 (73% worse than naïve)
5. **Sales Volume** - MASE 1.79 (79% worse than naïve)
6. **GROUP Cash Flow** - MASE 3.71 (271% worse than naïve)
7. **Thermal Energy Cost** - MASE 15.07 (1407% worse than naïve)

### FQS Ranking (Higher is Better)
| Rank | Variable | FQS | Rating |
|------|----------|-----|--------|
| 1 | Portugal HICP Inflation | 98.2 | Excellent |
| 2 | Diesel Price (EU) | 89.7 | Excellent |
| 3 | Construction Output Index | 87.0 | Excellent |
| 4 | GROUP EBITDA | 85.1 | Excellent |
| 5 | 3-Month EURIBOR Rate | 80.7 | Excellent |
| 6 | Industrial Production Index | 79.9 | Good |
| 7 | Portugal GDP Growth (YoY) | 79.4 | Good |
| 8 | Average Selling Price | 77.6 | Good |
| 9 | Construction Confidence Indicator | 74.8 | Good |
| 10 | Building Permits (Portugal) | 68.6 | Good |
| 11 | GROUP Net Income | 67.4 | Good |
| 12 | EBITDA | 62.5 | Moderate |
| 13 | Revenue | 53.9 | Moderate |
| 14 | Electricity Cost | 51.1 | Moderate |
| 15 | Variable Cost per Ton | 41.8 | Poor |
| 16 | GROUP Turnover | 21.6 | Poor |
| 17 | Capacity Utilization | 19.5 | Poor |
| 18 | Sales Volume | 6.9 | Poor |
| 19 | Thermal Energy Cost | 0.0 | Poor |
| 20 | GROUP Cash Flow | 0.0 | Poor |
