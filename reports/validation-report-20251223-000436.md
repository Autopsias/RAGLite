# RAGLite Forecasting Validation Report
Generated: 2025-12-23T00:04:36.916626
Runtime: 178.2 seconds

## Overall Assessment: ❌ FAIL

### Quality Gate Results
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Variables Passing MAPE | ≥9/20 | 10/20 | ✅ PASS |
| Average MASE | <1.0 | 0.50 | ✅ PASS |

### Quick Summary
- **Excellent (MAPE <5%):** 4 variables
- **Good (MAPE 5-15%):** 2 variables
- **Needs Improvement (MAPE 15-30%):** 2 variables
- **Critical (MAPE >30%):** 3 variables

**Average MAPE:** 157.39%
**Average MASE:** 0.50 (better than naïve)
**Average FQS:** 74.7/100 (Good)

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
| MAPE | 1552.25% | <5.5% | ❌ FAIL | Critical - needs investigation |
| MASE | 0.95 | <1.0 | ✅ PASS | Beats naïve by 5% |
| SMAPE | 95.18% | - | INFO | Symmetric error |
| RMSE | 307568.45 | - | INFO | Error in original units |
| MAE | 262352.88 | - | INFO | Average absolute error |
| Bias | +151567.95 | ~0 | INFO | Tends to over-predict |
| FQS | 34.3/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

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

### ❌ Capacity Utilization
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | N/A | - | ⚠️ N/A | No data available |

**Assessment:** Unknown performance.

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

### 🟡 Warning - Monitor & Improve
| Variable | Issue | Current | Target | Gap |
|----------|-------|---------|--------|-----|
| Revenue | Exceeds target | 1552.25% | 5.5% | +1546.75% |
| Electricity Cost | Exceeds target | 16.18% | 15.0% | +1.18% |
| 3-Month EURIBOR Rate | Near threshold | 22.89% | 23.0% | -0.11% |
| Portugal GDP Growth (YoY) | Near threshold | 54.76% | 55.0% | -0.24% |
| Construction Confidence Indicator | Near threshold | 62.09% | 63.0% | -0.91% |

### 🟢 Good Performance - No Action Required
Portugal HICP Inflation, Diesel Price (EU), Industrial Electricity Price, Construction Output Index, Industrial Production Index, Building Permits (Portugal)


## Actionable Guidance

### ✅ Acceptable (No Action Required)

| Variable | MAPE | MASE | Status |
|----------|------|------|--------|
| Electricity Cost | 16.2% | 0.16 | MASE-only |
| 3-Month EURIBOR Rate | 22.9% | 0.31 | Primary |
| Portugal GDP Growth (YoY) | 54.8% | 0.64 | MASE-only |
| Portugal HICP Inflation | 0.3% | 0.08 | Primary |
| Diesel Price (EU) | 3.9% | 0.63 | Primary |
| Industrial Electricity Price | 6.5% | 0.77 | Primary |
| Construction Output Index | 0.9% | 0.32 | Primary |
| Industrial Production Index | 1.2% | 0.44 | Primary |
| Building Permits (Portugal) | 10.3% | 0.91 | Primary |
| Construction Confidence Indicator | 62.1% | 0.35 | MASE-only |


### ⚙️ Consider Threshold Adjustment (No Reingestion)

**Revenue** - MAPE 1552.3% exceeds threshold but MASE 0.95 is excellent
- **Analysis:** Forecasts follow correct trend but may have systematic bias
- **Recommendation:** Consider enabling MASE-only pass for this variable

**EBITDA** - MAPE 0.0% exceeds threshold 5.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Sales Volume** - MAPE 0.0% exceeds threshold 10.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Thermal Energy Cost** - MAPE 0.0% exceeds threshold 10.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Variable Cost per Ton** - MAPE 0.0% exceeds threshold 8.0%
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

**Capacity Utilization** - MAPE 0.0% exceeds threshold 10.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**CO2 EUA Price** - MAPE 0.0% exceeds threshold 25.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable


### ⚠️ Bias Alerts

| Variable | Bias | Alert |
|----------|------|-------|
| Revenue | 151567.95 | Systematic over-prediction detected (bias=151567.95) |
| 3-Month EURIBOR Rate | -0.47 | Systematic under-prediction detected (bias=-0.47) |
| Portugal GDP Growth (YoY) | -1.29 | Systematic under-prediction detected (bias=-1.29) |
| Construction Confidence Indicator | -1.78 | Systematic under-prediction detected (bias=-1.78) |

## Cross-Variable Performance

### MASE Ranking (Lower is Better)
| Rank | Variable | MASE | vs Naïve |
|------|----------|------|----------|
| 1 | Portugal HICP Inflation | 0.08 | 92% better |
| 2 | Electricity Cost | 0.16 | 84% better |
| 3 | 3-Month EURIBOR Rate | 0.31 | 69% better |
| 4 | Construction Output Index | 0.32 | 68% better |
| 5 | Construction Confidence Indicator | 0.35 | 65% better |
| 6 | Industrial Production Index | 0.44 | 56% better |
| 7 | Diesel Price (EU) | 0.63 | 37% better |
| 8 | Portugal GDP Growth (YoY) | 0.64 | 36% better |
| 9 | Industrial Electricity Price | 0.77 | 23% better |
| 10 | Building Permits (Portugal) | 0.91 | 9% better |
| 11 | Revenue | 0.95 | 5% better |

### Variables Where Model Adds Most Value
1. **Portugal HICP Inflation** - MASE 0.08 (92% better than naïve)
2. **Electricity Cost** - MASE 0.16 (84% better than naïve)
3. **3-Month EURIBOR Rate** - MASE 0.31 (69% better than naïve)

### FQS Ranking (Higher is Better)
| Rank | Variable | FQS | Rating |
|------|----------|-----|--------|
| 1 | Portugal HICP Inflation | 97.4 | Excellent |
| 2 | Construction Output Index | 89.4 | Excellent |
| 3 | Electricity Cost | 89.2 | Excellent |
| 4 | Industrial Production Index | 85.2 | Excellent |
| 5 | 3-Month EURIBOR Rate | 82.0 | Excellent |
| 6 | Diesel Price (EU) | 78.2 | Good |
| 7 | Industrial Electricity Price | 72.5 | Good |
| 8 | Building Permits (Portugal) | 66.9 | Good |
| 9 | Construction Confidence Indicator | 66.8 | Good |
| 10 | Portugal GDP Growth (YoY) | 59.9 | Moderate |
| 11 | Revenue | 34.3 | Poor |
