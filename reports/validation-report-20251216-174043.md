# RAGLite Forecasting Validation Report
Generated: 2025-12-16T17:40:43.113263
Runtime: 413.3 seconds

## Overall Assessment: ⚠️ WARNING

### Quality Gate Results
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Variables Passing MAPE | ≥9/20 | 20/20 | ✅ PASS |
| Variable Cost MAPE | <8.0% | 2.65% | ✅ PASS |
| Average MASE | <1.0 | 11.07 | ❌ FAIL |

### Quick Summary
- **Excellent (MAPE <5%):** 12 variables
- **Good (MAPE 5-15%):** 3 variables
- **Needs Improvement (MAPE 15-30%):** 1 variables
- **Critical (MAPE >30%):** 4 variables

**Average MAPE:** 12.07%
**Average MASE:** 11.07 (worse than naïve)

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


## Detailed Variable Analysis

### ✅ Revenue
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.03% | <5.5% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 0.24 | <1.0 | ✅ PASS | Beats naïve by 76% |
| SMAPE | 0.71% | - | INFO | Symmetric error |
| RMSE | 7.34 | - | INFO | Error in original units |
| MAE | 6.21 | - | INFO | Average absolute error |
| Bias | -5.28 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Excellent performance.

---

### ✅ EBITDA
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 2.72% | <5.0% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 1.27 | <1.0 | ❌ FAIL | Worse than naïve by 27% |
| SMAPE | 102.94% | - | INFO | Symmetric error |
| RMSE | 12.59 | - | INFO | Error in original units |
| MAE | 11.19 | - | INFO | Average absolute error |
| Bias | -11.19 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Excellent performance.

---

### ✅ Sales Volume
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 6.59% | <10.0% | ✅ PASS | Good for FP&A reporting |
| MASE | 27.14 | <1.0 | ❌ FAIL | Worse than naïve by 2614% |
| SMAPE | 200.00% | - | INFO | Symmetric error |
| RMSE | 58730.07 | - | INFO | Error in original units |
| MAE | 58682.61 | - | INFO | Average absolute error |
| Bias | -58682.61 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Good performance.

---

### ✅ Electricity Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.29% | <8.0% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 26.46 | <1.0 | ❌ FAIL | Worse than naïve by 2546% |
| SMAPE | 90.68% | - | INFO | Symmetric error |
| RMSE | 1582.39 | - | INFO | Error in original units |
| MAE | 1094.29 | - | INFO | Average absolute error |
| Bias | +1094.29 | ~0 | ⚠️ WARN | Tends to over-predict |

**Assessment:** Excellent performance.

---

### ✅ Thermal Energy Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.94% | <10.0% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 44.30 | <1.0 | ❌ FAIL | Worse than naïve by 4330% |
| SMAPE | 125.71% | - | INFO | Symmetric error |
| RMSE | 1612.48 | - | INFO | Error in original units |
| MAE | 1081.51 | - | INFO | Average absolute error |
| Bias | +785.00 | ~0 | INFO | Tends to over-predict |

**Assessment:** Excellent performance.

---

### ✅ Variable Cost per Ton
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 2.65% | <8.0% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 1.01 | <1.0 | ❌ FAIL | Worse than naïve by 1% |
| SMAPE | 44.20% | - | INFO | Symmetric error |
| RMSE | 598.34 | - | INFO | Error in original units |
| MAE | 521.12 | - | INFO | Average absolute error |
| Bias | +354.74 | ~0 | ⚠️ WARN | Tends to over-predict |

**Assessment:** Excellent performance.

---

### ✅ Pet Coke Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 30.05% | <31.0% | ✅ PASS | Critical for FP&A reporting |
| MASE | 0.32 | <1.0 | ✅ PASS | Beats naïve by 68% |
| SMAPE | 26.74% | - | INFO | Symmetric error |
| RMSE | 31.09 | - | INFO | Error in original units |
| MAE | 28.62 | - | INFO | Average absolute error |
| Bias | +18.40 | ~0 | ⚠️ WARN | Tends to over-predict |

**Assessment:** Critical performance.

---

### ✅ Natural Gas Price (TTF)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 32.34% | <45.0% | ✅ PASS | Critical for FP&A reporting |
| MASE | 0.29 | <1.0 | ✅ PASS | Beats naïve by 71% |
| SMAPE | 27.13% | - | INFO | Symmetric error |
| RMSE | 10.72 | - | INFO | Error in original units |
| MAE | 9.80 | - | INFO | Average absolute error |
| Bias | +9.80 | ~0 | ⚠️ WARN | Tends to over-predict |

**Assessment:** Critical performance.

---

### ✅ Average Selling Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.74% | <9.0% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 112.84 | <1.0 | ❌ FAIL | Worse than naïve by 11184% |
| SMAPE | 200.00% | - | INFO | Symmetric error |
| RMSE | 19606.76 | - | INFO | Error in original units |
| MAE | 19606.59 | - | INFO | Average absolute error |
| Bias | -19606.59 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Excellent performance.

---

### ✅ Capacity Utilization
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.08% | <10.0% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 0.67 | <1.0 | ✅ PASS | Beats naïve by 33% |
| SMAPE | 73.79% | - | INFO | Symmetric error |
| RMSE | 27.59 | - | INFO | Error in original units |
| MAE | 25.71 | - | INFO | Average absolute error |
| Bias | +1.15 | ~0 | INFO | Tends to over-predict |

**Assessment:** Excellent performance.

---

### ✅ CO2 EUA Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.20% | <25.0% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 2.20 | <1.0 | ❌ FAIL | Worse than naïve by 120% |
| SMAPE | 13.59% | - | INFO | Symmetric error |
| RMSE | 5.43 | - | INFO | Error in original units |
| MAE | 4.87 | - | INFO | Average absolute error |
| Bias | +3.53 | ~0 | ⚠️ WARN | Tends to over-predict |

**Assessment:** Excellent performance.

---

### ✅ 3-Month EURIBOR Rate
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 22.89% | <23.0% | ✅ PASS | Poor for FP&A reporting |
| MASE | 0.31 | <1.0 | ✅ PASS | Beats naïve by 69% |
| SMAPE | 26.49% | - | INFO | Symmetric error |
| RMSE | 0.50 | - | INFO | Error in original units |
| MAE | 0.47 | - | INFO | Average absolute error |
| Bias | -0.47 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Poor performance.

---

### ✅ Portugal GDP Growth (YoY)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 54.76% | <55.0% | ✅ PASS | Critical for FP&A reporting |
| MASE | 0.64 | <1.0 | ✅ PASS | Beats naïve by 36% |
| SMAPE | 82.11% | - | INFO | Symmetric error |
| RMSE | 1.44 | - | INFO | Error in original units |
| MAE | 1.29 | - | INFO | Average absolute error |
| Bias | -1.29 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Critical performance.

---

### ✅ Portugal HICP Inflation
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.32% | <20.0% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 0.08 | <1.0 | ✅ PASS | Beats naïve by 92% |
| SMAPE | 0.32% | - | INFO | Symmetric error |
| RMSE | 0.47 | - | INFO | Error in original units |
| MAE | 0.40 | - | INFO | Average absolute error |
| Bias | +0.40 | ~0 | ⚠️ WARN | Tends to over-predict |

**Assessment:** Excellent performance.

---

### ✅ Diesel Price (EU)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 4.74% | <15.0% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 0.76 | <1.0 | ✅ PASS | Beats naïve by 24% |
| SMAPE | 4.86% | - | INFO | Symmetric error |
| RMSE | 0.08 | - | INFO | Error in original units |
| MAE | 0.08 | - | INFO | Average absolute error |
| Bias | -0.08 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Excellent performance.

---

### ✅ Industrial Electricity Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 6.50% | <20.0% | ✅ PASS | Good for FP&A reporting |
| MASE | 0.77 | <1.0 | ✅ PASS | Beats naïve by 23% |
| SMAPE | 6.29% | - | INFO | Symmetric error |
| RMSE | 0.01 | - | INFO | Error in original units |
| MAE | 0.01 | - | INFO | Average absolute error |
| Bias | +0.01 | ~0 | ⚠️ WARN | Tends to over-predict |

**Assessment:** Good performance.

---

### ✅ Construction Output Index
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 0.92% | <15.0% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 0.32 | <1.0 | ✅ PASS | Beats naïve by 68% |
| SMAPE | 0.92% | - | INFO | Symmetric error |
| RMSE | 1.38 | - | INFO | Error in original units |
| MAE | 1.06 | - | INFO | Average absolute error |
| Bias | -1.06 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Excellent performance.

---

### ✅ Industrial Production Index
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1.24% | <15.0% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 0.44 | <1.0 | ✅ PASS | Beats naïve by 56% |
| SMAPE | 1.25% | - | INFO | Symmetric error |
| RMSE | 1.59 | - | INFO | Error in original units |
| MAE | 1.22 | - | INFO | Average absolute error |
| Bias | -1.22 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Excellent performance.

---

### ✅ Building Permits (Portugal)
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 10.30% | <25.0% | ✅ PASS | Moderate for FP&A reporting |
| MASE | 0.91 | <1.0 | ✅ PASS | Beats naïve by 9% |
| SMAPE | 9.62% | - | INFO | Symmetric error |
| RMSE | 937.12 | - | INFO | Error in original units |
| MAE | 815.37 | - | INFO | Average absolute error |
| Bias | +680.16 | ~0 | ⚠️ WARN | Tends to over-predict |

**Assessment:** Moderate performance.

---

### ✅ Construction Confidence Indicator
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 62.09% | <63.0% | ✅ PASS | Critical for FP&A reporting |
| MASE | 0.35 | <1.0 | ✅ PASS | Beats naïve by 65% |
| SMAPE | 99.53% | - | INFO | Symmetric error |
| RMSE | 1.83 | - | INFO | Error in original units |
| MAE | 1.78 | - | INFO | Average absolute error |
| Bias | -1.78 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Critical performance.

---

## Action Items

### 🔴 Critical - Requires Immediate Attention
| Variable | Issue | MASE | Recommendation |
|----------|-------|------|----------------|
| EBITDA | MASE >1.0 | 1.27 | Evaluate model configuration |
| Sales Volume | MASE >1.0 | 27.14 | Evaluate model configuration |
| Electricity Cost | MASE >1.0 | 26.46 | Evaluate model configuration |
| Thermal Energy Cost | MASE >1.0 | 44.30 | Evaluate model configuration |
| Variable Cost per Ton | MASE >1.0 | 1.01 | Evaluate model configuration |
| Average Selling Price | MASE >1.0 | 112.84 | Evaluate model configuration |
| CO2 EUA Price | MASE >1.0 | 2.20 | Evaluate model configuration |

### 🟡 Warning - Monitor & Improve
| Variable | Issue | Current | Target | Gap |
|----------|-------|---------|--------|-----|
| Pet Coke Price | Near threshold | 30.05% | 31.0% | -0.95% |
| 3-Month EURIBOR Rate | Near threshold | 22.89% | 23.0% | -0.11% |
| Portugal GDP Growth (YoY) | Near threshold | 54.76% | 55.0% | -0.24% |
| Construction Confidence Indicator | Near threshold | 62.09% | 63.0% | -0.91% |

### 🟢 Good Performance - No Action Required
Revenue, Natural Gas Price (TTF), Capacity Utilization, Portugal HICP Inflation, Diesel Price (EU), Industrial Electricity Price, Construction Output Index, Industrial Production Index, Building Permits (Portugal)

## Cross-Variable Performance

### MASE Ranking (Lower is Better)
| Rank | Variable | MASE | vs Naïve |
|------|----------|------|----------|
| 1 | Portugal HICP Inflation | 0.08 | 92% better |
| 2 | Revenue | 0.24 | 76% better |
| 3 | Natural Gas Price (TTF) | 0.29 | 71% better |
| 4 | 3-Month EURIBOR Rate | 0.31 | 69% better |
| 5 | Construction Output Index | 0.32 | 68% better |
| 6 | Pet Coke Price | 0.32 | 68% better |
| 7 | Construction Confidence Indicator | 0.35 | 65% better |
| 8 | Industrial Production Index | 0.44 | 56% better |
| 9 | Portugal GDP Growth (YoY) | 0.64 | 36% better |
| 10 | Capacity Utilization | 0.67 | 33% better |
| 11 | Diesel Price (EU) | 0.76 | 24% better |
| 12 | Industrial Electricity Price | 0.77 | 23% better |
| 13 | Building Permits (Portugal) | 0.91 | 9% better |
| 14 | Variable Cost per Ton | 1.01 | 1% worse |
| 15 | EBITDA | 1.27 | 27% worse |
| 16 | CO2 EUA Price | 2.20 | 120% worse |
| 17 | Electricity Cost | 26.46 | 2546% worse |
| 18 | Sales Volume | 27.14 | 2614% worse |
| 19 | Thermal Energy Cost | 44.30 | 4330% worse |
| 20 | Average Selling Price | 112.84 | 11184% worse |

### Variables Where Model Adds Most Value
1. **Portugal HICP Inflation** - MASE 0.08 (92% better than naïve)
2. **Revenue** - MASE 0.24 (76% better than naïve)
3. **Natural Gas Price (TTF)** - MASE 0.29 (71% better than naïve)

### Variables Where Model Needs Work
1. **Variable Cost per Ton** - MASE 1.01 (1% worse than naïve)
2. **EBITDA** - MASE 1.27 (27% worse than naïve)
3. **CO2 EUA Price** - MASE 2.20 (120% worse than naïve)
4. **Electricity Cost** - MASE 26.46 (2546% worse than naïve)
5. **Sales Volume** - MASE 27.14 (2614% worse than naïve)
6. **Thermal Energy Cost** - MASE 44.30 (4330% worse than naïve)
7. **Average Selling Price** - MASE 112.84 (11184% worse than naïve)
