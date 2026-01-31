# RAGLite Forecasting Validation Report
Generated: 2026-01-29T11:59:54.474100
Runtime: 317.4 seconds

## Overall Assessment: ❌ FAIL

### Quality Gate Results
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Variables Passing MAPE | ≥9/20 | 12/20 | ✅ PASS |
| Variable Cost MAPE | <8.0% | 132.94% | ❌ FAIL |
| Average MASE | <1.0 | 1.03 | ❌ FAIL |

### Quick Summary
- **Excellent (MAPE <5%):** 5 variables
- **Good (MAPE 5-15%):** 1 variables
- **Needs Improvement (MAPE 15-30%):** 3 variables
- **Critical (MAPE >30%):** 7 variables

**Average MAPE:** 48.81%
**Average MASE:** 1.03 (worse than naïve)
**Average FQS:** 60.2/100 (Moderate)

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
| MAPE | 84.13% | <5.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 1.17 | <1.0 | ❌ FAIL | Worse than naïve by 17% |
| SMAPE | 123.79% | - | INFO | Symmetric error |
| RMSE | 11.27 | - | INFO | Error in original units |
| MAE | 10.49 | - | INFO | Average absolute error |
| Bias | -1.48 | ~0 | INFO | Tends to under-predict |
| FQS | 41.7/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ Sales Volume
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 73.70% | <10.0% | ✅ MASE-ONLY | MASE 0.77 passed (MAPE waived) |
| MASE | 0.77 | <1.0 | ✅ PASS | Beats naïve by 23% |
| SMAPE | 79.47% | - | INFO | Symmetric error |
| RMSE | 201.72 | - | INFO | Error in original units |
| MAE | 147.23 | - | INFO | Average absolute error |
| Bias | +46.07 | ~0 | INFO | Tends to over-predict |
| FQS | 61.5/100 | ≥65 | INFO | Moderate quality |

**Assessment:** Critical performance.

---

### ❌ Electricity Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 78.96% | <15.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 3.01 | <1.0 | ❌ FAIL | Worse than naïve by 201% |
| SMAPE | 83.03% | - | INFO | Symmetric error |
| RMSE | 6.37 | - | INFO | Error in original units |
| MAE | 5.54 | - | INFO | Average absolute error |
| Bias | +1.60 | ~0 | INFO | Tends to over-predict |
| FQS | 0.0/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ Thermal Energy Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 57.41% | <10.0% | ✅ MASE-ONLY | MASE 0.77 passed (MAPE waived) |
| MASE | 0.77 | <1.0 | ✅ PASS | Beats naïve by 23% |
| SMAPE | 40.92% | - | INFO | Symmetric error |
| RMSE | 11.78 | - | INFO | Error in original units |
| MAE | 9.18 | - | INFO | Average absolute error |
| Bias | +4.77 | ~0 | INFO | Tends to over-predict |
| FQS | 61.7/100 | ≥65 | INFO | Moderate quality |

**Assessment:** Critical performance.

---

### ❌ Variable Cost per Ton
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 132.94% | <8.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 4.68 | <1.0 | ❌ FAIL | Worse than naïve by 368% |
| SMAPE | 111.55% | - | INFO | Symmetric error |
| RMSE | 171.74 | - | INFO | Error in original units |
| MAE | 117.63 | - | INFO | Average absolute error |
| Bias | -101.36 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 0.0/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ❌ Pet Coke Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

---

### ❌ Natural Gas Price (TTF)
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
| FQS | 67.8/100 | ≥65 | INFO | Good quality |

**Assessment:** Excellent performance.

---

### ❌ Capacity Utilization
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 227.98% | <10.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 1.07 | <1.0 | ❌ FAIL | Worse than naïve by 7% |
| SMAPE | 86.91% | - | INFO | Symmetric error |
| RMSE | 23.52 | - | INFO | Error in original units |
| MAE | 20.40 | - | INFO | Average absolute error |
| Bias | +20.40 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 46.3/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ❌ CO2 EUA Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

---

### ✅ 3-Month EURIBOR Rate
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 22.85% | <23.0% | ✅ PASS (MAPE) | Poor for FP&A reporting |
| MASE | 0.31 | <1.0 | ✅ PASS | Beats naïve by 69% |
| SMAPE | 26.63% | - | INFO | Symmetric error |
| RMSE | 0.52 | - | INFO | Error in original units |
| MAE | 0.47 | - | INFO | Average absolute error |
| Bias | -0.47 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 84.7/100 | ≥65 | INFO | Excellent quality |

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
| FQS | 83.3/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Poor performance.

---

### ✅ Portugal HICP Inflation
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.20% | <20.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.05 | <1.0 | ✅ PASS | Beats naïve by 95% |
| SMAPE | 0.20% | - | INFO | Symmetric error |
| RMSE | 0.26 | - | INFO | Error in original units |
| MAE | 0.25 | - | INFO | Average absolute error |
| Bias | +0.10 | ~0 | INFO | Tends to over-predict |
| FQS | 97.6/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Diesel Price (EU)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.94% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.31 | <1.0 | ✅ PASS | Beats naïve by 69% |
| SMAPE | 1.96% | - | INFO | Symmetric error |
| RMSE | 0.03 | - | INFO | Error in original units |
| MAE | 0.03 | - | INFO | Average absolute error |
| Bias | -0.02 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 84.5/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Industrial Electricity Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 6.50% | <20.0% | ✅ PASS (MAPE) | Good for FP&A reporting |
| MASE | 0.77 | <1.0 | ✅ PASS | Beats naïve by 23% |
| SMAPE | 6.29% | - | INFO | Symmetric error |
| RMSE | 0.01 | - | INFO | Error in original units |
| MAE | 0.01 | - | INFO | Average absolute error |
| Bias | +0.01 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 61.3/100 | ≥65 | INFO | Moderate quality |

**Assessment:** Good performance.

---

### ✅ Construction Output Index
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.18% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.40 | <1.0 | ✅ PASS | Beats naïve by 60% |
| SMAPE | 1.19% | - | INFO | Symmetric error |
| RMSE | 1.70 | - | INFO | Error in original units |
| MAE | 1.37 | - | INFO | Average absolute error |
| Bias | -1.37 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 79.9/100 | ≥65 | INFO | Good quality |

**Assessment:** Excellent performance.

---

### ✅ Industrial Production Index
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.61% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.57 | <1.0 | ✅ PASS | Beats naïve by 43% |
| SMAPE | 1.61% | - | INFO | Symmetric error |
| RMSE | 1.79 | - | INFO | Error in original units |
| MAE | 1.58 | - | INFO | Average absolute error |
| Bias | -0.35 | ~0 | INFO | Tends to under-predict |
| FQS | 71.4/100 | ≥65 | INFO | Good quality |

**Assessment:** Excellent performance.

---

### ✅ Building Permits (Portugal)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 15.28% | <25.0% | ✅ PASS (MAPE) | Moderate for FP&A reporting |
| MASE | 1.29 | <1.0 | ❌ FAIL | Worse than naïve by 29% |
| SMAPE | 13.91% | - | INFO | Symmetric error |
| RMSE | 1319.12 | - | INFO | Error in original units |
| MAE | 1181.47 | - | INFO | Average absolute error |
| Bias | +1181.47 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 35.3/100 | ≥65 | INFO | Poor quality |

**Assessment:** Moderate performance.

---

### ✅ Construction Confidence Indicator
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 44.37% | <63.0% | ✅ MASE-ONLY | MASE 0.28 passed (MAPE waived) |
| MASE | 0.28 | <1.0 | ✅ PASS | Beats naïve by 72% |
| SMAPE | 46.01% | - | INFO | Symmetric error |
| RMSE | 1.42 | - | INFO | Error in original units |
| MAE | 1.32 | - | INFO | Average absolute error |
| Bias | -0.54 | ~0 | INFO | Tends to under-predict |
| FQS | 86.2/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Critical performance.

---

## Action Items

### 🔴 Critical - Requires Immediate Attention
| Variable | Issue | MASE | Recommendation |
|----------|-------|------|----------------|
| EBITDA | MASE >1.0 | 1.17 | Evaluate model configuration |
| Electricity Cost | MASE >1.0 | 3.01 | Evaluate model configuration |
| Variable Cost per Ton | MASE >1.0 | 4.68 | Evaluate model configuration |
| Capacity Utilization | MASE >1.0 | 1.07 | Evaluate model configuration |
| Building Permits (Portugal) | MASE >1.0 | 1.29 | Evaluate model configuration |

### 🟡 Warning - Monitor & Improve
| Variable | Issue | Current | Target | Gap |
|----------|-------|---------|--------|-----|
| Sales Volume | Exceeds target | 73.70% | 10.0% | +63.70% |
| Thermal Energy Cost | Exceeds target | 57.41% | 10.0% | +47.41% |
| 3-Month EURIBOR Rate | Near threshold | 22.85% | 23.0% | -0.15% |

### 🟢 Good Performance - No Action Required
Average Selling Price, Portugal GDP Growth (YoY), Portugal HICP Inflation, Diesel Price (EU), Industrial Electricity Price, Construction Output Index, Industrial Production Index, Construction Confidence Indicator


## Actionable Guidance

### ✅ Acceptable (No Action Required)

| Variable | MAPE | MASE | Status |
|----------|------|------|--------|
| Sales Volume | 73.7% | 0.77 | MASE-only |
| Thermal Energy Cost | 57.4% | 0.77 | MASE-only |
| Average Selling Price | 4.2% | 0.64 | Primary |
| 3-Month EURIBOR Rate | 22.8% | 0.31 | Primary |
| Portugal GDP Growth (YoY) | 27.7% | 0.33 | MASE-only |
| Portugal HICP Inflation | 0.2% | 0.05 | Primary |
| Diesel Price (EU) | 1.9% | 0.31 | Primary |
| Industrial Electricity Price | 6.5% | 0.77 | Primary |
| Construction Output Index | 1.2% | 0.40 | Primary |
| Industrial Production Index | 1.6% | 0.57 | Primary |
| Building Permits (Portugal) | 15.3% | 1.29 | Primary |
| Construction Confidence Indicator | 44.4% | 0.28 | MASE-only |


### 🔧 Needs Data Fix (Requires Reingestion)

**Electricity Cost** - MAPE 79.0% and MASE 3.01 both poor
- **Root Cause:** Likely data quality issue (entity mixing, wrong aliases, scale mismatch)
- **Fix:** 1) Check db_metric_aliases for incorrect mappings
2) Verify entity filter (GROUP vs individual entities)
3) Check for scale mismatches (thousands vs units)
- **Expected Improvement:** 50-90% reduction in MAPE after data fix

**Variable Cost per Ton** - MAPE 132.9% and MASE 4.68 both poor
- **Root Cause:** Likely data quality issue (entity mixing, wrong aliases, scale mismatch)
- **Fix:** 1) Check db_metric_aliases for incorrect mappings
2) Verify entity filter (GROUP vs individual entities)
3) Check for scale mismatches (thousands vs units)
- **Expected Improvement:** 50-90% reduction in MAPE after data fix


### ⚙️ Consider Threshold Adjustment (No Reingestion)

**Revenue** - MAPE 0.0% exceeds threshold 5.5%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**EBITDA** - MAPE 84.1% exceeds threshold, MASE 1.17 is borderline
- **Analysis:** Model performs close to naive baseline
- **Recommendation:** Consider: 1) Adding predictive regressors, 2) Adjusting threshold to 92%

**Pet Coke Price** - MAPE 0.0% exceeds threshold 31.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Natural Gas Price (TTF)** - MAPE 0.0% exceeds threshold 45.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Capacity Utilization** - MAPE 228.0% exceeds threshold, MASE 1.07 is borderline
- **Analysis:** Model performs close to naive baseline
- **Recommendation:** Consider: 1) Adding predictive regressors, 2) Adjusting threshold to 250%

**CO2 EUA Price** - MAPE 0.0% exceeds threshold 25.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable


### ⚠️ Bias Alerts

| Variable | Bias | Alert |
|----------|------|-------|
| Sales Volume | 46.07 | Systematic over-prediction detected (bias=46.07) |
| Electricity Cost | 1.60 | Systematic over-prediction detected (bias=1.60) |
| Thermal Energy Cost | 4.77 | Systematic over-prediction detected (bias=4.77) |
| Variable Cost per Ton | -101.36 | Systematic under-prediction detected (bias=-101.36) |
| Capacity Utilization | 20.40 | Systematic over-prediction detected (bias=20.40) |
| 3-Month EURIBOR Rate | -0.47 | Systematic under-prediction detected (bias=-0.47) |
| Portugal GDP Growth (YoY) | -0.49 | Systematic under-prediction detected (bias=-0.49) |

## Cross-Variable Performance

### MASE Ranking (Lower is Better)
| Rank | Variable | MASE | vs Naïve |
|------|----------|------|----------|
| 1 | Portugal HICP Inflation | 0.05 | 95% better |
| 2 | Construction Confidence Indicator | 0.28 | 72% better |
| 3 | 3-Month EURIBOR Rate | 0.31 | 69% better |
| 4 | Diesel Price (EU) | 0.31 | 69% better |
| 5 | Portugal GDP Growth (YoY) | 0.33 | 67% better |
| 6 | Construction Output Index | 0.40 | 60% better |
| 7 | Industrial Production Index | 0.57 | 43% better |
| 8 | Average Selling Price | 0.64 | 36% better |
| 9 | Thermal Energy Cost | 0.77 | 23% better |
| 10 | Sales Volume | 0.77 | 23% better |
| 11 | Industrial Electricity Price | 0.77 | 23% better |
| 12 | Capacity Utilization | 1.07 | 7% worse |
| 13 | EBITDA | 1.17 | 17% worse |
| 14 | Building Permits (Portugal) | 1.29 | 29% worse |
| 15 | Electricity Cost | 3.01 | 201% worse |
| 16 | Variable Cost per Ton | 4.68 | 368% worse |

### Variables Where Model Adds Most Value
1. **Portugal HICP Inflation** - MASE 0.05 (95% better than naïve)
2. **Construction Confidence Indicator** - MASE 0.28 (72% better than naïve)
3. **3-Month EURIBOR Rate** - MASE 0.31 (69% better than naïve)

### Variables Where Model Needs Work
1. **Capacity Utilization** - MASE 1.07 (7% worse than naïve)
2. **EBITDA** - MASE 1.17 (17% worse than naïve)
3. **Building Permits (Portugal)** - MASE 1.29 (29% worse than naïve)
4. **Electricity Cost** - MASE 3.01 (201% worse than naïve)
5. **Variable Cost per Ton** - MASE 4.68 (368% worse than naïve)

### FQS Ranking (Higher is Better)
| Rank | Variable | FQS | Rating |
|------|----------|-----|--------|
| 1 | Portugal HICP Inflation | 97.6 | Excellent |
| 2 | Construction Confidence Indicator | 86.2 | Excellent |
| 3 | 3-Month EURIBOR Rate | 84.7 | Excellent |
| 4 | Diesel Price (EU) | 84.5 | Excellent |
| 5 | Portugal GDP Growth (YoY) | 83.3 | Excellent |
| 6 | Construction Output Index | 79.9 | Good |
| 7 | Industrial Production Index | 71.4 | Good |
| 8 | Average Selling Price | 67.8 | Good |
| 9 | Thermal Energy Cost | 61.7 | Moderate |
| 10 | Sales Volume | 61.5 | Moderate |
| 11 | Industrial Electricity Price | 61.3 | Moderate |
| 12 | Capacity Utilization | 46.3 | Poor |
| 13 | EBITDA | 41.7 | Poor |
| 14 | Building Permits (Portugal) | 35.3 | Poor |
| 15 | Electricity Cost | 0.0 | Poor |
| 16 | Variable Cost per Ton | 0.0 | Poor |
