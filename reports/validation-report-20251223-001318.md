# RAGLite Forecasting Validation Report
Generated: 2025-12-23T00:13:18.172191
Runtime: 383.8 seconds

## Overall Assessment: ⚠️ WARNING

### Quality Gate Results
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Variables Passing MAPE | ≥9/20 | 16/20 | ✅ PASS |
| Variable Cost MAPE | <8.0% | 173.12% | ❌ FAIL |
| Average MASE | <1.0 | 0.88 | ✅ PASS |

### Quick Summary
- **Excellent (MAPE <5%):** 6 variables
- **Good (MAPE 5-15%):** 2 variables
- **Needs Improvement (MAPE 15-30%):** 4 variables
- **Critical (MAPE >30%):** 8 variables

**Average MAPE:** 37.91%
**Average MASE:** 0.88 (better than naïve)
**Average FQS:** 65.7/100 (Good)

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
| MAPE | 3.87% | <5.5% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 1.28 | <1.0 | ❌ FAIL | Worse than naïve by 28% |
| SMAPE | 3.95% | - | INFO | Symmetric error |
| RMSE | 35.03 | - | INFO | Error in original units |
| MAE | 33.83 | - | INFO | Average absolute error |
| Bias | -33.83 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 57.2/100 | ≥65 | INFO | Moderate quality |

**Assessment:** Excellent performance.

---

### ✅ EBITDA
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 87.41% | <5.0% | ✅ MASE-ONLY | MASE 0.60 passed (MAPE waived) |
| MASE | 0.60 | <1.0 | ✅ PASS | Beats naïve by 40% |
| SMAPE | 57.54% | - | INFO | Symmetric error |
| RMSE | 17.29 | - | INFO | Error in original units |
| MAE | 15.97 | - | INFO | Average absolute error |
| Bias | +15.97 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 49.9/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ❌ Sales Volume
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 28.60% | <10.0% | ❌ FAIL | Poor - needs investigation |
| MASE | 0.51 | <1.0 | ✅ PASS | Beats naïve by 49% |
| SMAPE | 33.50% | - | INFO | Symmetric error |
| RMSE | 56.27 | - | INFO | Error in original units |
| MAE | 54.92 | - | INFO | Average absolute error |
| Bias | -54.92 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 73.6/100 | ≥65 | INFO | Good quality |

**Assessment:** Poor performance.

---

### ✅ Electricity Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 16.18% | <15.0% | ✅ MASE-ONLY | MASE 0.16 passed (MAPE waived) |
| MASE | 0.16 | <1.0 | ✅ PASS | Beats naïve by 84% |
| SMAPE | 14.51% | - | INFO | Symmetric error |
| RMSE | 12.05 | - | INFO | Error in original units |
| MAE | 10.32 | - | INFO | Average absolute error |
| Bias | +9.39 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 89.2/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Moderate performance.

---

### ❌ Thermal Energy Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 68.93% | <10.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 2.54 | <1.0 | ❌ FAIL | Worse than naïve by 154% |
| SMAPE | 89.24% | - | INFO | Symmetric error |
| RMSE | 68.92 | - | INFO | Error in original units |
| MAE | 39.78 | - | INFO | Average absolute error |
| Bias | -38.97 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 10.9/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ❌ Variable Cost per Ton
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 173.12% | <8.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 5.02 | <1.0 | ❌ FAIL | Worse than naïve by 402% |
| SMAPE | 75.14% | - | INFO | Symmetric error |
| RMSE | 268.76 | - | INFO | Error in original units |
| MAE | 153.04 | - | INFO | Average absolute error |
| Bias | -133.38 | ~0 | INFO | Tends to under-predict |
| FQS | 0.0/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ Pet Coke Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 30.05% | <31.0% | ✅ MASE-ONLY | MASE 0.32 passed (MAPE waived) |
| MASE | 0.32 | <1.0 | ✅ PASS | Beats naïve by 68% |
| SMAPE | 26.74% | - | INFO | Symmetric error |
| RMSE | 31.09 | - | INFO | Error in original units |
| MAE | 28.62 | - | INFO | Average absolute error |
| Bias | +18.40 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 79.2/100 | ≥65 | INFO | Good quality |

**Assessment:** Critical performance.

---

### ✅ Natural Gas Price (TTF)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 32.34% | <45.0% | ✅ MASE-ONLY | MASE 0.29 passed (MAPE waived) |
| MASE | 0.29 | <1.0 | ✅ PASS | Beats naïve by 71% |
| SMAPE | 27.13% | - | INFO | Symmetric error |
| RMSE | 10.72 | - | INFO | Error in original units |
| MAE | 9.80 | - | INFO | Average absolute error |
| Bias | +9.80 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 79.4/100 | ≥65 | INFO | Good quality |

**Assessment:** Critical performance.

---

### ✅ Average Selling Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.83% | <9.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.28 | <1.0 | ✅ PASS | Beats naïve by 72% |
| SMAPE | 1.83% | - | INFO | Symmetric error |
| RMSE | 1.27 | - | INFO | Error in original units |
| MAE | 1.22 | - | INFO | Average absolute error |
| Bias | +0.34 | ~0 | INFO | Tends to over-predict |
| FQS | 90.3/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Capacity Utilization
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 136.19% | <10.0% | ✅ MASE-ONLY | MASE 0.65 passed (MAPE waived) |
| MASE | 0.65 | <1.0 | ✅ PASS | Beats naïve by 35% |
| SMAPE | 73.62% | - | INFO | Symmetric error |
| RMSE | 27.62 | - | INFO | Error in original units |
| MAE | 25.71 | - | INFO | Average absolute error |
| Bias | +1.77 | ~0 | INFO | Tends to over-predict |
| FQS | 43.8/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ❌ CO2 EUA Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 16.87% | <25.0% | ❌ FAIL | Moderate - needs investigation |
| MASE | 1.57 | <1.0 | ❌ FAIL | Worse than naïve by 57% |
| SMAPE | 17.74% | - | INFO | Symmetric error |
| RMSE | 14.94 | - | INFO | Error in original units |
| MAE | 12.49 | - | INFO | Average absolute error |
| Bias | -6.01 | ~0 | INFO | Tends to under-predict |
| FQS | 43.0/100 | ≥65 | INFO | Poor quality |

**Assessment:** Moderate performance.

---

### ✅ 3-Month EURIBOR Rate
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 22.89% | <23.0% | ✅ PASS (MAPE) | Poor for FP&A reporting |
| MASE | 0.31 | <1.0 | ✅ PASS | Beats naïve by 69% |
| SMAPE | 26.49% | - | INFO | Symmetric error |
| RMSE | 0.50 | - | INFO | Error in original units |
| MAE | 0.47 | - | INFO | Average absolute error |
| Bias | -0.47 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 82.0/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Poor performance.

---

### ✅ Portugal GDP Growth (YoY)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 54.76% | <55.0% | ✅ MASE-ONLY | MASE 0.64 passed (MAPE waived) |
| MASE | 0.64 | <1.0 | ✅ PASS | Beats naïve by 36% |
| SMAPE | 82.11% | - | INFO | Symmetric error |
| RMSE | 1.44 | - | INFO | Error in original units |
| MAE | 1.29 | - | INFO | Average absolute error |
| Bias | -1.29 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 59.9/100 | ≥65 | INFO | Moderate quality |

**Assessment:** Critical performance.

---

### ✅ Portugal HICP Inflation
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.31% | <20.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.08 | <1.0 | ✅ PASS | Beats naïve by 92% |
| SMAPE | 0.31% | - | INFO | Symmetric error |
| RMSE | 0.46 | - | INFO | Error in original units |
| MAE | 0.39 | - | INFO | Average absolute error |
| Bias | +0.39 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 97.4/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Diesel Price (EU)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 3.90% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.63 | <1.0 | ✅ PASS | Beats naïve by 37% |
| SMAPE | 4.00% | - | INFO | Symmetric error |
| RMSE | 0.07 | - | INFO | Error in original units |
| MAE | 0.06 | - | INFO | Average absolute error |
| Bias | -0.06 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 78.2/100 | ≥65 | INFO | Good quality |

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
| FQS | 72.5/100 | ≥65 | INFO | Good quality |

**Assessment:** Good performance.

---

### ✅ Construction Output Index
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.92% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.32 | <1.0 | ✅ PASS | Beats naïve by 68% |
| SMAPE | 0.92% | - | INFO | Symmetric error |
| RMSE | 1.38 | - | INFO | Error in original units |
| MAE | 1.06 | - | INFO | Average absolute error |
| Bias | -1.06 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 89.4/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Industrial Production Index
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.24% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.44 | <1.0 | ✅ PASS | Beats naïve by 56% |
| SMAPE | 1.25% | - | INFO | Symmetric error |
| RMSE | 1.59 | - | INFO | Error in original units |
| MAE | 1.22 | - | INFO | Average absolute error |
| Bias | -1.22 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 85.2/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Building Permits (Portugal)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 10.30% | <25.0% | ✅ PASS (MAPE) | Moderate for FP&A reporting |
| MASE | 0.91 | <1.0 | ✅ PASS | Beats naïve by 9% |
| SMAPE | 9.62% | - | INFO | Symmetric error |
| RMSE | 937.12 | - | INFO | Error in original units |
| MAE | 815.37 | - | INFO | Average absolute error |
| Bias | +680.16 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 66.9/100 | ≥65 | INFO | Good quality |

**Assessment:** Moderate performance.

---

### ✅ Construction Confidence Indicator
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 62.09% | <63.0% | ✅ MASE-ONLY | MASE 0.35 passed (MAPE waived) |
| MASE | 0.35 | <1.0 | ✅ PASS | Beats naïve by 65% |
| SMAPE | 99.53% | - | INFO | Symmetric error |
| RMSE | 1.83 | - | INFO | Error in original units |
| MAE | 1.78 | - | INFO | Average absolute error |
| Bias | -1.78 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 66.8/100 | ≥65 | INFO | Good quality |

**Assessment:** Critical performance.

---

## Action Items

### 🔴 Critical - Requires Immediate Attention
| Variable | Issue | MASE | Recommendation |
|----------|-------|------|----------------|
| Revenue | MASE >1.0 | 1.28 | Evaluate model configuration |
| Thermal Energy Cost | MASE >1.0 | 2.54 | Evaluate model configuration |
| Variable Cost per Ton | MASE >1.0 | 5.02 | Evaluate model configuration |
| CO2 EUA Price | MASE >1.0 | 1.57 | Evaluate model configuration |

### 🟡 Warning - Monitor & Improve
| Variable | Issue | Current | Target | Gap |
|----------|-------|---------|--------|-----|
| EBITDA | Exceeds target | 87.41% | 5.0% | +82.41% |
| Sales Volume | Exceeds target | 28.60% | 10.0% | +18.60% |
| Electricity Cost | Exceeds target | 16.18% | 15.0% | +1.18% |
| Pet Coke Price | Near threshold | 30.05% | 31.0% | -0.95% |
| Capacity Utilization | Exceeds target | 136.19% | 10.0% | +126.19% |
| 3-Month EURIBOR Rate | Near threshold | 22.89% | 23.0% | -0.11% |
| Portugal GDP Growth (YoY) | Near threshold | 54.76% | 55.0% | -0.24% |
| Construction Confidence Indicator | Near threshold | 62.09% | 63.0% | -0.91% |

### 🟢 Good Performance - No Action Required
Natural Gas Price (TTF), Average Selling Price, Portugal HICP Inflation, Diesel Price (EU), Industrial Electricity Price, Construction Output Index, Industrial Production Index, Building Permits (Portugal)


## Actionable Guidance

### ✅ Acceptable (No Action Required)

| Variable | MAPE | MASE | Status |
|----------|------|------|--------|
| Revenue | 3.9% | 1.28 | Primary |
| EBITDA | 87.4% | 0.60 | MASE-only |
| Electricity Cost | 16.2% | 0.16 | MASE-only |
| Pet Coke Price | 30.1% | 0.32 | MASE-only |
| Natural Gas Price (TTF) | 32.3% | 0.29 | MASE-only |
| Average Selling Price | 1.8% | 0.28 | Primary |
| Capacity Utilization | 136.2% | 0.65 | MASE-only |
| 3-Month EURIBOR Rate | 22.9% | 0.31 | Primary |
| Portugal GDP Growth (YoY) | 54.8% | 0.64 | MASE-only |
| Portugal HICP Inflation | 0.3% | 0.08 | Primary |
| Diesel Price (EU) | 3.9% | 0.63 | Primary |
| Industrial Electricity Price | 6.5% | 0.77 | Primary |
| Construction Output Index | 0.9% | 0.32 | Primary |
| Industrial Production Index | 1.2% | 0.44 | Primary |
| Building Permits (Portugal) | 10.3% | 0.91 | Primary |
| Construction Confidence Indicator | 62.1% | 0.35 | MASE-only |


### 🔧 Needs Data Fix (Requires Reingestion)

**Thermal Energy Cost** - MAPE 68.9% and MASE 2.54 both poor
- **Root Cause:** Likely data quality issue (entity mixing, wrong aliases, scale mismatch)
- **Fix:** 1) Check db_metric_aliases for incorrect mappings
2) Verify entity filter (GROUP vs individual entities)
3) Check for scale mismatches (thousands vs units)
- **Expected Improvement:** 50-90% reduction in MAPE after data fix

**Variable Cost per Ton** - MAPE 173.1% and MASE 5.02 both poor
- **Root Cause:** Likely data quality issue (entity mixing, wrong aliases, scale mismatch)
- **Fix:** 1) Check db_metric_aliases for incorrect mappings
2) Verify entity filter (GROUP vs individual entities)
3) Check for scale mismatches (thousands vs units)
- **Expected Improvement:** 50-90% reduction in MAPE after data fix


### ⚙️ Consider Threshold Adjustment (No Reingestion)

**Sales Volume** - MAPE 28.6% exceeds threshold but MASE 0.51 is excellent
- **Analysis:** Forecasts follow correct trend but may have systematic bias
- **Recommendation:** Consider enabling MASE-only pass for this variable

**CO2 EUA Price** - MAPE 16.9% exceeds threshold 25.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable


### ⚠️ Bias Alerts

| Variable | Bias | Alert |
|----------|------|-------|
| EBITDA | 15.97 | Systematic over-prediction detected (bias=15.97) |
| Sales Volume | -54.92 | Systematic under-prediction detected (bias=-54.92) |
| Thermal Energy Cost | -38.97 | Systematic under-prediction detected (bias=-38.97) |
| Variable Cost per Ton | -133.38 | Systematic under-prediction detected (bias=-133.38) |
| Natural Gas Price (TTF) | 9.80 | Systematic over-prediction detected (bias=9.80) |
| 3-Month EURIBOR Rate | -0.47 | Systematic under-prediction detected (bias=-0.47) |
| Portugal GDP Growth (YoY) | -1.29 | Systematic under-prediction detected (bias=-1.29) |
| Construction Confidence Indicator | -1.78 | Systematic under-prediction detected (bias=-1.78) |

## Cross-Variable Performance

### MASE Ranking (Lower is Better)
| Rank | Variable | MASE | vs Naïve |
|------|----------|------|----------|
| 1 | Portugal HICP Inflation | 0.08 | 92% better |
| 2 | Electricity Cost | 0.16 | 84% better |
| 3 | Average Selling Price | 0.28 | 72% better |
| 4 | Natural Gas Price (TTF) | 0.29 | 71% better |
| 5 | 3-Month EURIBOR Rate | 0.31 | 69% better |
| 6 | Construction Output Index | 0.32 | 68% better |
| 7 | Pet Coke Price | 0.32 | 68% better |
| 8 | Construction Confidence Indicator | 0.35 | 65% better |
| 9 | Industrial Production Index | 0.44 | 56% better |
| 10 | Sales Volume | 0.51 | 49% better |
| 11 | EBITDA | 0.60 | 40% better |
| 12 | Diesel Price (EU) | 0.63 | 37% better |
| 13 | Portugal GDP Growth (YoY) | 0.64 | 36% better |
| 14 | Capacity Utilization | 0.65 | 35% better |
| 15 | Industrial Electricity Price | 0.77 | 23% better |
| 16 | Building Permits (Portugal) | 0.91 | 9% better |
| 17 | Revenue | 1.28 | 28% worse |
| 18 | CO2 EUA Price | 1.57 | 57% worse |
| 19 | Thermal Energy Cost | 2.54 | 154% worse |
| 20 | Variable Cost per Ton | 5.02 | 402% worse |

### Variables Where Model Adds Most Value
1. **Portugal HICP Inflation** - MASE 0.08 (92% better than naïve)
2. **Electricity Cost** - MASE 0.16 (84% better than naïve)
3. **Average Selling Price** - MASE 0.28 (72% better than naïve)

### Variables Where Model Needs Work
1. **Revenue** - MASE 1.28 (28% worse than naïve)
2. **CO2 EUA Price** - MASE 1.57 (57% worse than naïve)
3. **Thermal Energy Cost** - MASE 2.54 (154% worse than naïve)
4. **Variable Cost per Ton** - MASE 5.02 (402% worse than naïve)

### FQS Ranking (Higher is Better)
| Rank | Variable | FQS | Rating |
|------|----------|-----|--------|
| 1 | Portugal HICP Inflation | 97.4 | Excellent |
| 2 | Average Selling Price | 90.3 | Excellent |
| 3 | Construction Output Index | 89.4 | Excellent |
| 4 | Electricity Cost | 89.2 | Excellent |
| 5 | Industrial Production Index | 85.2 | Excellent |
| 6 | 3-Month EURIBOR Rate | 82.0 | Excellent |
| 7 | Natural Gas Price (TTF) | 79.4 | Good |
| 8 | Pet Coke Price | 79.2 | Good |
| 9 | Diesel Price (EU) | 78.2 | Good |
| 10 | Sales Volume | 73.6 | Good |
| 11 | Industrial Electricity Price | 72.5 | Good |
| 12 | Building Permits (Portugal) | 66.9 | Good |
| 13 | Construction Confidence Indicator | 66.8 | Good |
| 14 | Portugal GDP Growth (YoY) | 59.9 | Moderate |
| 15 | Revenue | 57.2 | Moderate |
| 16 | EBITDA | 49.9 | Poor |
| 17 | Capacity Utilization | 43.8 | Poor |
| 18 | CO2 EUA Price | 43.0 | Poor |
| 19 | Thermal Energy Cost | 10.9 | Poor |
| 20 | Variable Cost per Ton | 0.0 | Poor |
