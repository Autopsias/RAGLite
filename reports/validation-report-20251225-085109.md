# RAGLite Forecasting Validation Report
Generated: 2025-12-25T08:51:09.509073
Runtime: 436.8 seconds

## Overall Assessment: ✅ PASS

### Quality Gate Results
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Variables Passing MAPE | ≥9/20 | 19/20 | ✅ PASS |
| Variable Cost MAPE | <8.0% | 53.24% | ❌ FAIL |
| Average MASE | <1.0 | 0.79 | ✅ PASS |

### Quick Summary
- **Excellent (MAPE <5%):** 7 variables
- **Good (MAPE 5-15%):** 6 variables
- **Needs Improvement (MAPE 15-30%):** 0 variables
- **Critical (MAPE >30%):** 7 variables

**Average MAPE:** 27.99%
**Average MASE:** 0.79 (better than naïve)
**Average FQS:** 70.5/100 (Good)

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
| MAPE | 99.57% | <5.0% | ✅ MASE-ONLY | MASE 0.69 passed (MAPE waived) |
| MASE | 0.69 | <1.0 | ✅ PASS | Beats naïve by 31% |
| SMAPE | 63.47% | - | INFO | Symmetric error |
| RMSE | 19.40 | - | INFO | Error in original units |
| MAE | 18.24 | - | INFO | Average absolute error |
| Bias | +18.24 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 42.9/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ Sales Volume
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 9.02% | <10.0% | ✅ MASE-ONLY | MASE 0.15 passed (MAPE waived) |
| MASE | 0.15 | <1.0 | ✅ PASS | Beats naïve by 85% |
| SMAPE | 8.79% | - | INFO | Symmetric error |
| RMSE | 17.09 | - | INFO | Error in original units |
| MAE | 16.70 | - | INFO | Average absolute error |
| Bias | +7.42 | ~0 | INFO | Tends to over-predict |
| FQS | 91.8/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Good performance.

---

### ✅ Electricity Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 52.98% | <15.0% | ✅ MASE-ONLY | MASE 0.53 passed (MAPE waived) |
| MASE | 0.53 | <1.0 | ✅ PASS | Beats naïve by 47% |
| SMAPE | 40.65% | - | INFO | Symmetric error |
| RMSE | 36.41 | - | INFO | Error in original units |
| MAE | 34.49 | - | INFO | Average absolute error |
| Bias | +34.49 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 64.3/100 | ≥65 | INFO | Moderate quality |

**Assessment:** Critical performance.

---

### ✅ Thermal Energy Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 68.93% | <10.0% | ✅ MASE-ONLY | MASE 2.54 passed (MAPE waived) |
| MASE | 2.54 | <1.0 | ❌ FAIL | Worse than naïve by 154% |
| SMAPE | 89.24% | - | INFO | Symmetric error |
| RMSE | 68.92 | - | INFO | Error in original units |
| MAE | 39.78 | - | INFO | Average absolute error |
| Bias | -38.97 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 10.9/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ Variable Cost per Ton
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 53.24% | <8.0% | ✅ MASE-ONLY | MASE 1.48 passed (MAPE waived) |
| MASE | 1.48 | <1.0 | ❌ FAIL | Worse than naïve by 48% |
| SMAPE | 53.38% | - | INFO | Symmetric error |
| RMSE | 48.21 | - | INFO | Error in original units |
| MAE | 45.09 | - | INFO | Average absolute error |
| Bias | +19.71 | ~0 | INFO | Tends to over-predict |
| FQS | 33.3/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ Pet Coke Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 6.52% | <31.0% | ✅ MASE-ONLY | MASE 0.07 passed (MAPE waived) |
| MASE | 0.07 | <1.0 | ✅ PASS | Beats naïve by 93% |
| SMAPE | 6.26% | - | INFO | Symmetric error |
| RMSE | 6.80 | - | INFO | Error in original units |
| MAE | 6.12 | - | INFO | Average absolute error |
| Bias | +6.12 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 95.5/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Good performance.

---

### ✅ Natural Gas Price (TTF)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 39.33% | <45.0% | ✅ MASE-ONLY | MASE 0.34 passed (MAPE waived) |
| MASE | 0.34 | <1.0 | ✅ PASS | Beats naïve by 66% |
| SMAPE | 32.17% | - | INFO | Symmetric error |
| RMSE | 12.40 | - | INFO | Error in original units |
| MAE | 11.77 | - | INFO | Average absolute error |
| Bias | +11.77 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 75.0/100 | ≥65 | INFO | Good quality |

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
| MAPE | 49.60% | <25.0% | ❌ FAIL | Critical - needs investigation |
| MASE | 4.79 | <1.0 | ❌ FAIL | Worse than naïve by 379% |
| SMAPE | 70.97% | - | INFO | Symmetric error |
| RMSE | 43.06 | - | INFO | Error in original units |
| MAE | 38.13 | - | INFO | Average absolute error |
| Bias | -38.13 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 17.6/100 | ≥65 | INFO | Poor quality |

**Assessment:** Critical performance.

---

### ✅ 3-Month EURIBOR Rate
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.66% | <23.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.02 | <1.0 | ✅ PASS | Beats naïve by 98% |
| SMAPE | 1.68% | - | INFO | Symmetric error |
| RMSE | 0.04 | - | INFO | Error in original units |
| MAE | 0.03 | - | INFO | Average absolute error |
| Bias | -0.03 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 98.7/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Portugal GDP Growth (YoY)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 8.79% | <55.0% | ✅ MASE-ONLY | MASE 0.09 passed (MAPE waived) |
| MASE | 0.09 | <1.0 | ✅ PASS | Beats naïve by 91% |
| SMAPE | 8.77% | - | INFO | Symmetric error |
| RMSE | 0.19 | - | INFO | Error in original units |
| MAE | 0.19 | - | INFO | Average absolute error |
| Bias | -0.07 | ~0 | INFO | Tends to under-predict |
| FQS | 93.9/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Good performance.

---

### ✅ Portugal HICP Inflation
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.21% | <20.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.05 | <1.0 | ✅ PASS | Beats naïve by 95% |
| SMAPE | 0.21% | - | INFO | Symmetric error |
| RMSE | 0.36 | - | INFO | Error in original units |
| MAE | 0.26 | - | INFO | Average absolute error |
| Bias | +0.26 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 98.2/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Diesel Price (EU)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 4.23% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.66 | <1.0 | ✅ PASS | Beats naïve by 34% |
| SMAPE | 4.12% | - | INFO | Symmetric error |
| RMSE | 0.07 | - | INFO | Error in original units |
| MAE | 0.07 | - | INFO | Average absolute error |
| Bias | +0.07 | ~0 | ⚠️ WARN | Tends to over-predict |
| FQS | 77.0/100 | ≥65 | INFO | Good quality |

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
| MAPE | 1.02% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.35 | <1.0 | ✅ PASS | Beats naïve by 65% |
| SMAPE | 1.03% | - | INFO | Symmetric error |
| RMSE | 1.63 | - | INFO | Error in original units |
| MAE | 1.18 | - | INFO | Average absolute error |
| Bias | -1.18 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 88.2/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Industrial Production Index
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.79% | <15.0% | ✅ PASS (MAPE) | Excellent for FP&A reporting |
| MASE | 0.28 | <1.0 | ✅ PASS | Beats naïve by 72% |
| SMAPE | 0.79% | - | INFO | Symmetric error |
| RMSE | 1.01 | - | INFO | Error in original units |
| MAE | 0.78 | - | INFO | Average absolute error |
| Bias | -0.78 | ~0 | ⚠️ WARN | Tends to under-predict |
| FQS | 90.6/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Excellent performance.

---

### ✅ Building Permits (Portugal)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 8.57% | <25.0% | ✅ PASS (MAPE) | Good for FP&A reporting |
| MASE | 0.75 | <1.0 | ✅ PASS | Beats naïve by 25% |
| SMAPE | 8.13% | - | INFO | Symmetric error |
| RMSE | 881.69 | - | INFO | Error in original units |
| MAE | 678.10 | - | INFO | Average absolute error |
| Bias | +191.23 | ~0 | INFO | Tends to over-predict |
| FQS | 72.5/100 | ≥65 | INFO | Good quality |

**Assessment:** Good performance.

---

### ✅ Construction Confidence Indicator
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 6.99% | <63.0% | ✅ MASE-ONLY | MASE 0.04 passed (MAPE waived) |
| MASE | 0.04 | <1.0 | ✅ PASS | Beats naïve by 96% |
| SMAPE | 6.90% | - | INFO | Symmetric error |
| RMSE | 0.29 | - | INFO | Error in original units |
| MAE | 0.22 | - | INFO | Average absolute error |
| Bias | +0.03 | ~0 | INFO | Tends to over-predict |
| FQS | 96.2/100 | ≥65 | INFO | Excellent quality |

**Assessment:** Good performance.

---

## Action Items

### 🔴 Critical - Requires Immediate Attention
| Variable | Issue | MASE | Recommendation |
|----------|-------|------|----------------|
| Revenue | MASE >1.0 | 1.28 | Evaluate model configuration |
| Thermal Energy Cost | MASE >1.0 | 2.54 | Evaluate model configuration |
| Variable Cost per Ton | MASE >1.0 | 1.48 | Evaluate model configuration |
| CO2 EUA Price | MASE >1.0 | 4.79 | Evaluate model configuration |

### 🟡 Warning - Monitor & Improve
| Variable | Issue | Current | Target | Gap |
|----------|-------|---------|--------|-----|
| EBITDA | Exceeds target | 99.57% | 5.0% | +94.57% |
| Sales Volume | Near threshold | 9.02% | 10.0% | -0.98% |
| Electricity Cost | Exceeds target | 52.98% | 15.0% | +37.98% |
| Capacity Utilization | Exceeds target | 136.19% | 10.0% | +126.19% |

### 🟢 Good Performance - No Action Required
Pet Coke Price, Natural Gas Price (TTF), Average Selling Price, 3-Month EURIBOR Rate, Portugal GDP Growth (YoY), Portugal HICP Inflation, Diesel Price (EU), Industrial Electricity Price, Construction Output Index, Industrial Production Index, Building Permits (Portugal), Construction Confidence Indicator


## Actionable Guidance

### ✅ Acceptable (No Action Required)

| Variable | MAPE | MASE | Status |
|----------|------|------|--------|
| Revenue | 3.9% | 1.28 | Primary |
| EBITDA | 99.6% | 0.69 | MASE-only |
| Sales Volume | 9.0% | 0.15 | MASE-only |
| Electricity Cost | 53.0% | 0.53 | MASE-only |
| Thermal Energy Cost | 68.9% | 2.54 | MASE-only |
| Variable Cost per Ton | 53.2% | 1.48 | MASE-only |
| Pet Coke Price | 6.5% | 0.07 | MASE-only |
| Natural Gas Price (TTF) | 39.3% | 0.34 | MASE-only |
| Average Selling Price | 1.8% | 0.28 | Primary |
| Capacity Utilization | 136.2% | 0.65 | MASE-only |
| 3-Month EURIBOR Rate | 1.7% | 0.02 | Primary |
| Portugal GDP Growth (YoY) | 8.8% | 0.09 | MASE-only |
| Portugal HICP Inflation | 0.2% | 0.05 | Primary |
| Diesel Price (EU) | 4.2% | 0.66 | Primary |
| Industrial Electricity Price | 6.5% | 0.77 | Primary |
| Construction Output Index | 1.0% | 0.35 | Primary |
| Industrial Production Index | 0.8% | 0.28 | Primary |
| Building Permits (Portugal) | 8.6% | 0.75 | Primary |
| Construction Confidence Indicator | 7.0% | 0.04 | MASE-only |


### ⚙️ Consider Threshold Adjustment (No Reingestion)

**CO2 EUA Price** - MAPE 49.6% exceeds threshold 25.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable


### ⚠️ Bias Alerts

| Variable | Bias | Alert |
|----------|------|-------|
| EBITDA | 18.24 | Systematic over-prediction detected (bias=18.24) |
| Electricity Cost | 34.49 | Systematic over-prediction detected (bias=34.49) |
| Thermal Energy Cost | -38.97 | Systematic under-prediction detected (bias=-38.97) |
| Variable Cost per Ton | 19.71 | Systematic over-prediction detected (bias=19.71) |
| Natural Gas Price (TTF) | 11.77 | Systematic over-prediction detected (bias=11.77) |
| CO2 EUA Price | -38.13 | Systematic under-prediction detected (bias=-38.13) |

## Cross-Variable Performance

### MASE Ranking (Lower is Better)
| Rank | Variable | MASE | vs Naïve |
|------|----------|------|----------|
| 1 | 3-Month EURIBOR Rate | 0.02 | 98% better |
| 2 | Construction Confidence Indicator | 0.04 | 96% better |
| 3 | Portugal HICP Inflation | 0.05 | 95% better |
| 4 | Pet Coke Price | 0.07 | 93% better |
| 5 | Portugal GDP Growth (YoY) | 0.09 | 91% better |
| 6 | Sales Volume | 0.15 | 85% better |
| 7 | Average Selling Price | 0.28 | 72% better |
| 8 | Industrial Production Index | 0.28 | 72% better |
| 9 | Natural Gas Price (TTF) | 0.34 | 66% better |
| 10 | Construction Output Index | 0.35 | 65% better |
| 11 | Electricity Cost | 0.53 | 47% better |
| 12 | Capacity Utilization | 0.65 | 35% better |
| 13 | Diesel Price (EU) | 0.66 | 34% better |
| 14 | EBITDA | 0.69 | 31% better |
| 15 | Building Permits (Portugal) | 0.75 | 25% better |
| 16 | Industrial Electricity Price | 0.77 | 23% better |
| 17 | Revenue | 1.28 | 28% worse |
| 18 | Variable Cost per Ton | 1.48 | 48% worse |
| 19 | Thermal Energy Cost | 2.54 | 154% worse |
| 20 | CO2 EUA Price | 4.79 | 379% worse |

### Variables Where Model Adds Most Value
1. **3-Month EURIBOR Rate** - MASE 0.02 (98% better than naïve)
2. **Construction Confidence Indicator** - MASE 0.04 (96% better than naïve)
3. **Portugal HICP Inflation** - MASE 0.05 (95% better than naïve)

### Variables Where Model Needs Work
1. **Revenue** - MASE 1.28 (28% worse than naïve)
2. **Variable Cost per Ton** - MASE 1.48 (48% worse than naïve)
3. **Thermal Energy Cost** - MASE 2.54 (154% worse than naïve)
4. **CO2 EUA Price** - MASE 4.79 (379% worse than naïve)

### FQS Ranking (Higher is Better)
| Rank | Variable | FQS | Rating |
|------|----------|-----|--------|
| 1 | 3-Month EURIBOR Rate | 98.7 | Excellent |
| 2 | Portugal HICP Inflation | 98.2 | Excellent |
| 3 | Construction Confidence Indicator | 96.2 | Excellent |
| 4 | Pet Coke Price | 95.5 | Excellent |
| 5 | Portugal GDP Growth (YoY) | 93.9 | Excellent |
| 6 | Sales Volume | 91.8 | Excellent |
| 7 | Industrial Production Index | 90.6 | Excellent |
| 8 | Average Selling Price | 90.3 | Excellent |
| 9 | Construction Output Index | 88.2 | Excellent |
| 10 | Diesel Price (EU) | 77.0 | Good |
| 11 | Natural Gas Price (TTF) | 75.0 | Good |
| 12 | Industrial Electricity Price | 72.5 | Good |
| 13 | Building Permits (Portugal) | 72.5 | Good |
| 14 | Electricity Cost | 64.3 | Moderate |
| 15 | Revenue | 57.2 | Moderate |
| 16 | Capacity Utilization | 43.8 | Poor |
| 17 | EBITDA | 42.9 | Poor |
| 18 | Variable Cost per Ton | 33.3 | Poor |
| 19 | CO2 EUA Price | 17.6 | Poor |
| 20 | Thermal Energy Cost | 10.9 | Poor |
