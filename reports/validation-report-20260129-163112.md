# RAGLite Forecasting Validation Report
Generated: 2026-01-29T16:31:12.657922
Runtime: 167.9 seconds

## Overall Assessment: ❌ FAIL

### Quality Gate Results
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Variables Passing MAPE | ≥9/20 | 10/20 | ✅ PASS |
| Average MASE | <1.0 | 0.54 | ✅ PASS |

### Quick Summary
- **Excellent (MAPE <5%):** 4 variables
- **Good (MAPE 5-15%):** 1 variables
- **Needs Improvement (MAPE 15-30%):** 3 variables
- **Critical (MAPE >30%):** 2 variables

**Average MAPE:** 58.79%
**Average MASE:** 0.54 (better than naïve)
**Average FQS:** 73.1/100 (Good)

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
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

---

### ❌ Sales Volume
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

---

### ✅ Electricity Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 13.27% | <25.0% | ✅ MASE-ONLY | MASE 0.14 passed (MAPE waived) |
| MASE | 0.14 | <1.0 | ✅ PASS | Beats naïve by 86% |
| SMAPE | 11.95% | - | INFO | Symmetric error |
| RMSE | 11.20 | - | INFO | Error in original units |
| MAE | 8.83 | - | INFO | Average absolute error |
| Bias | +6.48 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 92.9/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Moderate performance.

---

### ❌ Thermal Energy Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

---

### ❌ Variable Cost per Ton
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

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

### ❌ Average Selling Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

---

### ✅ Capacity Utilization
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 459.58% | <50.0% | ✅ MASE-ONLY | MASE 1.69 passed (MAPE waived) |
| MASE | 1.69 | <1.0 | ❌ FAIL | Worse than naïve by 69% |
| SMAPE | 139.36% | - | INFO | Symmetric error |
| RMSE | 13.14 | - | INFO | Error in original units |
| MAE | 13.14 | - | INFO | Average absolute error |
| Bias | +13.14 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 15.5/100 | ≥65 | INFO | Poor quality |

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
| Capacity Utilization | MASE >1.0 | 1.69 | Evaluate model configuration |
| Building Permits (Portugal) | MASE >1.0 | 1.29 | Evaluate model configuration |

### 🟡 Warning - Monitor & Improve
| Variable | Issue | Current | Target | Gap |
|----------|-------|---------|--------|-----|
| 3-Month EURIBOR Rate | Near threshold | 22.85% | 23.0% | -0.15% |

### 🟢 Good Performance - No Action Required
Electricity Cost, Portugal GDP Growth (YoY), Portugal HICP Inflation, Diesel Price (EU), Construction Output Index, Industrial Production Index, Construction Confidence Indicator


## Actionable Guidance

### ✅ Acceptable (No Action Required)

| Variable | MAPE | MASE | Status |
|----------|------|------|--------|
| Electricity Cost | 13.3% | 0.14 | MASE-only |
| Capacity Utilization | 459.6% | 1.69 | MASE-only |
| 3-Month EURIBOR Rate | 22.8% | 0.31 | Primary |
| Portugal GDP Growth (YoY) | 27.7% | 0.33 | MASE-only |
| Portugal HICP Inflation | 0.2% | 0.05 | Primary |
| Diesel Price (EU) | 1.9% | 0.31 | Primary |
| Construction Output Index | 1.2% | 0.40 | Primary |
| Industrial Production Index | 1.6% | 0.57 | Primary |
| Building Permits (Portugal) | 15.3% | 1.29 | Primary |
| Construction Confidence Indicator | 44.4% | 0.28 | MASE-only |


### ⚙️ Consider Threshold Adjustment (No Reingestion)

**Revenue** - MAPE 0.0% exceeds threshold 5.5%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**EBITDA** - MAPE 0.0% exceeds threshold 100.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Sales Volume** - MAPE 0.0% exceeds threshold 10.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Thermal Energy Cost** - MAPE 0.0% exceeds threshold 10.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Variable Cost per Ton** - MAPE 0.0% exceeds threshold 70.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Pet Coke Price** - MAPE 0.0% exceeds threshold 31.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Natural Gas Price (TTF)** - MAPE 0.0% exceeds threshold 45.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Average Selling Price** - MAPE 0.0% exceeds threshold 9.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**CO2 EUA Price** - MAPE 0.0% exceeds threshold 25.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable


### ⚠️ Bias Alerts

| Variable | Bias | Alert |
|----------|------|-------|
| Capacity Utilization | 13.14 | Systematic over-prediction detected (bias=13.14) |
| 3-Month EURIBOR Rate | -0.47 | Systematic under-prediction detected (bias=-0.47) |
| Portugal GDP Growth (YoY) | -0.49 | Systematic under-prediction detected (bias=-0.49) |

## Cross-Variable Performance

### MASE Ranking (Lower is Better)
| Rank | Variable | MASE | vs Naïve |
|------|----------|------|----------|
| 1 | Portugal HICP Inflation | 0.05 | 95% better |
| 2 | Electricity Cost | 0.14 | 86% better |
| 3 | Construction Confidence Indicator | 0.28 | 72% better |
| 4 | 3-Month EURIBOR Rate | 0.31 | 69% better |
| 5 | Diesel Price (EU) | 0.31 | 69% better |
| 6 | Portugal GDP Growth (YoY) | 0.33 | 67% better |
| 7 | Construction Output Index | 0.40 | 60% better |
| 8 | Industrial Production Index | 0.57 | 43% better |
| 9 | Building Permits (Portugal) | 1.29 | 29% worse |
| 10 | Capacity Utilization | 1.69 | 69% worse |

### Variables Where Model Adds Most Value
1. **Portugal HICP Inflation** - MASE 0.05 (95% better than naïve)
2. **Electricity Cost** - MASE 0.14 (86% better than naïve)
3. **Construction Confidence Indicator** - MASE 0.28 (72% better than naïve)

### Variables Where Model Needs Work
1. **Building Permits (Portugal)** - MASE 1.29 (29% worse than naïve)
2. **Capacity Utilization** - MASE 1.69 (69% worse than naïve)

### FQS Ranking (Higher is Better)
| Rank | Variable | FQS | Rating |
|------|----------|-----|--------|
| 1 | Portugal HICP Inflation | 97.6 | Excellent |
| 2 | Electricity Cost | 92.9 | Excellent |
| 3 | Construction Confidence Indicator | 86.2 | Excellent |
| 4 | 3-Month EURIBOR Rate | 84.7 | Excellent |
| 5 | Diesel Price (EU) | 84.5 | Excellent |
| 6 | Portugal GDP Growth (YoY) | 83.3 | Excellent |
| 7 | Construction Output Index | 79.9 | Good |
| 8 | Industrial Production Index | 71.4 | Good |
| 9 | Building Permits (Portugal) | 35.3 | Poor |
| 10 | Capacity Utilization | 15.5 | Poor |
