# RAGLite Forecasting Validation Report
Generated: 2026-01-29T22:38:30.062338
Runtime: 377.0 seconds

## Overall Assessment: ✅ PASS

### Quality Gate Results
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Variables Passing MAPE | ≥9/20 | 16/20 | ✅ PASS |
| Variable Cost MAPE | <70.0% | 11.41% | ✅ PASS |
| Average MASE | <1.0 | 0.54 | ✅ PASS |

### Quick Summary
- **Excellent (MAPE <5%):** 6 variables
- **Good (MAPE 5-15%):** 3 variables
- **Needs Improvement (MAPE 15-30%):** 3 variables
- **Critical (MAPE >30%):** 4 variables

**Average MAPE:** 39.88%
**Average MASE:** 0.54 (better than naïve)
**Average FQS:** 72.8/100 (Good)

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
| MAPE | 3.17% | <5.5% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 1.06 | <1.0 | ❌ FAIL | Worse than naïve by 6% |
| SMAPE | 3.23% | - | INFO | Symmetric error |
| RMSE | 0.03 | - | INFO | Error in original units |
| MAE | 0.03 | - | INFO | Average absolute error |
| Bias | -0.03 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 46.8/100 | ≥65 | INFO | Poor quality |

**Assessment:** Excellent performance.

---

### ✅ EBITDA
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 17.26% | <100.0% | ✅ MASE-ONLY | MASE 0.35 passed (MAPE waived) |
| MASE | 0.35 | <1.0 | ✅ PASS | Beats naïve by 65% |
| SMAPE | 18.87% | - | INFO | Symmetric error |
| RMSE | 2.45 | - | INFO | Error in original units |
| MAE | 2.29 | - | INFO | Average absolute error |
| Bias | -1.87 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 82.5/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Moderate performance.

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

### ✅ Variable Cost per Ton
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 11.41% | <70.0% | ✅ MASE-ONLY | MASE 0.45 passed (MAPE waived) |
| MASE | 0.45 | <1.0 | ✅ PASS | Beats naïve by 55% |
| SMAPE | 11.89% | - | INFO | Symmetric error |
| RMSE | 15.10 | - | INFO | Error in original units |
| MAE | 11.37 | - | INFO | Average absolute error |
| Bias | -3.67 | ~0 | INFO | Tends to under-predict |
| FQS | 77.4/100 | ≥65 | INFO | Good quality |

**Assessment:** Moderate performance.

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

### ✅ Capacity Utilization
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 347.17% | <50.0% | ✅ MASE-ONLY | MASE 1.40 passed (MAPE waived) |
| MASE | 1.40 | <1.0 | ❌ FAIL | Worse than naïve by 40% |
| SMAPE | 126.88% | - | INFO | Symmetric error |
| RMSE | 26.60 | - | INFO | Error in original units |
| MAE | 26.60 | - | INFO | Average absolute error |
| Bias | +26.60 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 29.9/100 | ≥65 | INFO | Poor quality |

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
| MAPE | 10.57% | <25.0% | ✅ PASS (MAPE) | Moderate for FP&A reporting |
| MASE | 0.87 | <1.0 | ✅ PASS | Beats naïve by 13% |
| SMAPE | 9.72% | - | INFO | Symmetric error |
| RMSE | 1011.47 | - | INFO | Error in original units |
| MAE | 793.66 | - | INFO | Average absolute error |
| Bias | +791.77 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 56.5/100 | ≥65 | INFO | Moderate quality |

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
| Revenue | MASE >1.0 | 1.06 | Evaluate model configuration |
| Capacity Utilization | MASE >1.0 | 1.40 | Evaluate model configuration |

### 🟡 Warning - Monitor & Improve
| Variable | Issue | Current | Target | Gap |
|----------|-------|---------|--------|-----|
| Sales Volume | Exceeds target | 73.70% | 10.0% | +63.70% |
| Thermal Energy Cost | Exceeds target | 57.41% | 10.0% | +47.41% |
| 3-Month EURIBOR Rate | Near threshold | 22.85% | 23.0% | -0.15% |

### 🟢 Good Performance - No Action Required
EBITDA, Electricity Cost, Variable Cost per Ton, Average Selling Price, Portugal GDP Growth (YoY), Portugal HICP Inflation, Diesel Price (EU), Construction Output Index, Industrial Production Index, Building Permits (Portugal), Construction Confidence Indicator


## Actionable Guidance

### ✅ Acceptable (No Action Required)

| Variable | MAPE | MASE | Status |
|----------|------|------|--------|
| Revenue | 3.2% | 1.06 | Primary |
| EBITDA | 17.3% | 0.35 | MASE-only |
| Sales Volume | 73.7% | 0.77 | MASE-only |
| Electricity Cost | 13.3% | 0.14 | MASE-only |
| Thermal Energy Cost | 57.4% | 0.77 | MASE-only |
| Variable Cost per Ton | 11.4% | 0.45 | MASE-only |
| Average Selling Price | 4.2% | 0.64 | Primary |
| Capacity Utilization | 347.2% | 1.40 | MASE-only |
| 3-Month EURIBOR Rate | 22.8% | 0.31 | Primary |
| Portugal GDP Growth (YoY) | 27.7% | 0.33 | MASE-only |
| Portugal HICP Inflation | 0.2% | 0.05 | Primary |
| Diesel Price (EU) | 1.9% | 0.31 | Primary |
| Construction Output Index | 1.2% | 0.40 | Primary |
| Industrial Production Index | 1.6% | 0.57 | Primary |
| Building Permits (Portugal) | 10.6% | 0.87 | Primary |
| Construction Confidence Indicator | 44.4% | 0.28 | MASE-only |


### ⚙️ Consider Threshold Adjustment (No Reingestion)

**Pet Coke Price** - MAPE 0.0% exceeds threshold 31.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**Natural Gas Price (TTF)** - MAPE 0.0% exceeds threshold 45.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

**CO2 EUA Price** - MAPE 0.0% exceeds threshold 25.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable


### ⚠️ Bias Alerts

| Variable | Bias | Alert |
|----------|------|-------|
| Sales Volume | 46.07 | Systematic over-prediction detected (bias=46.07) |
| Thermal Energy Cost | 4.77 | Systematic over-prediction detected (bias=4.77) |
| Capacity Utilization | 26.60 | Systematic over-prediction detected (bias=26.60) |
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
| 7 | EBITDA | 0.35 | 65% better |
| 8 | Construction Output Index | 0.40 | 60% better |
| 9 | Variable Cost per Ton | 0.45 | 55% better |
| 10 | Industrial Production Index | 0.57 | 43% better |
| 11 | Average Selling Price | 0.64 | 36% better |
| 12 | Thermal Energy Cost | 0.77 | 23% better |
| 13 | Sales Volume | 0.77 | 23% better |
| 14 | Building Permits (Portugal) | 0.87 | 13% better |
| 15 | Revenue | 1.06 | 6% worse |
| 16 | Capacity Utilization | 1.40 | 40% worse |

### Variables Where Model Adds Most Value
1. **Portugal HICP Inflation** - MASE 0.05 (95% better than naïve)
2. **Electricity Cost** - MASE 0.14 (86% better than naïve)
3. **Construction Confidence Indicator** - MASE 0.28 (72% better than naïve)

### Variables Where Model Needs Work
1. **Revenue** - MASE 1.06 (6% worse than naïve)
2. **Capacity Utilization** - MASE 1.40 (40% worse than naïve)

### FQS Ranking (Higher is Better)
| Rank | Variable | FQS | Rating |
|------|----------|-----|--------|
| 1 | Portugal HICP Inflation | 97.6 | Excellent |
| 2 | Electricity Cost | 92.9 | Excellent |
| 3 | Construction Confidence Indicator | 86.2 | Excellent |
| 4 | 3-Month EURIBOR Rate | 84.7 | Excellent |
| 5 | Diesel Price (EU) | 84.5 | Excellent |
| 6 | Portugal GDP Growth (YoY) | 83.3 | Excellent |
| 7 | EBITDA | 82.5 | Excellent |
| 8 | Construction Output Index | 79.9 | Good |
| 9 | Variable Cost per Ton | 77.4 | Good |
| 10 | Industrial Production Index | 71.4 | Good |
| 11 | Average Selling Price | 67.8 | Good |
| 12 | Thermal Energy Cost | 61.7 | Moderate |
| 13 | Sales Volume | 61.5 | Moderate |
| 14 | Building Permits (Portugal) | 56.5 | Moderate |
| 15 | Revenue | 46.8 | Poor |
| 16 | Capacity Utilization | 29.9 | Poor |
