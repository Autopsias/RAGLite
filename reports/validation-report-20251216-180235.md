# RAGLite Forecasting Validation Report
Generated: 2025-12-16T18:02:35.020518
Runtime: 436.1 seconds

## Overall Assessment: ❌ FAIL

### Quality Gate Results
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Variables Passing MAPE | ≥9/20 | 12/20 | ✅ PASS |
| Variable Cost MAPE | <8.0% | 47.26% | ❌ FAIL |
| Average MASE | <1.0 | 13.81 | ❌ FAIL |

### Quick Summary
- **Excellent (MAPE <5%):** 5 variables
- **Good (MAPE 5-15%):** 3 variables
- **Needs Improvement (MAPE 15-30%):** 2 variables
- **Critical (MAPE >30%):** 10 variables

**Average MAPE:** 370.58%
**Average MASE:** 13.81 (worse than naïve)

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
| MAPE | 3.82% | <5.5% | ✅ PASS | Excellent for FP&A reporting |
| MASE | 1.28 | <1.0 | ❌ FAIL | Worse than naïve by 28% |
| SMAPE | 3.89% | - | INFO | Symmetric error |
| RMSE | 33.86 | - | INFO | Error in original units |
| MAE | 33.48 | - | INFO | Average absolute error |
| Bias | -33.48 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Excellent performance.

---

### ❌ EBITDA
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 100.00% | <5.0% | ❌ FAIL | Critical for FP&A reporting |
| MASE | 2.16 | <1.0 | ❌ FAIL | Worse than naïve by 116% |
| SMAPE | 200.00% | - | INFO | Symmetric error |
| RMSE | 19.06 | - | INFO | Error in original units |
| MAE | 18.95 | - | INFO | Average absolute error |
| Bias | -18.95 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Critical performance.

---

### ❌ Sales Volume
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 1149.66% | <10.0% | ❌ FAIL | Critical for FP&A reporting |
| MASE | 23.53 | <1.0 | ❌ FAIL | Worse than naïve by 2253% |
| SMAPE | 200.00% | - | INFO | Symmetric error |
| RMSE | 50912.15 | - | INFO | Error in original units |
| MAE | 50892.85 | - | INFO | Average absolute error |
| Bias | -50892.85 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Critical performance.

---

### ❌ Electricity Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 25.57% | <8.0% | ❌ FAIL | Poor for FP&A reporting |
| MASE | 1.52 | <1.0 | ❌ FAIL | Worse than naïve by 52% |
| SMAPE | 21.87% | - | INFO | Symmetric error |
| RMSE | 72.97 | - | INFO | Error in original units |
| MAE | 62.70 | - | INFO | Average absolute error |
| Bias | +60.98 | ~0 | ⚠️ WARN | Tends to over-predict |

**Assessment:** Poor performance.

---

### ❌ Thermal Energy Cost
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 14.52% | <10.0% | ❌ FAIL | Moderate for FP&A reporting |
| MASE | 1.72 | <1.0 | ❌ FAIL | Worse than naïve by 72% |
| SMAPE | 16.24% | - | INFO | Symmetric error |
| RMSE | 52.40 | - | INFO | Error in original units |
| MAE | 41.90 | - | INFO | Average absolute error |
| Bias | -22.44 | ~0 | INFO | Tends to under-predict |

**Assessment:** Moderate performance.

---

### ❌ Variable Cost per Ton
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 47.26% | <8.0% | ❌ FAIL | Critical for FP&A reporting |
| MASE | 0.89 | <1.0 | ✅ PASS | Beats naïve by 11% |
| SMAPE | 37.97% | - | INFO | Symmetric error |
| RMSE | 460.64 | - | INFO | Error in original units |
| MAE | 457.46 | - | INFO | Average absolute error |
| Bias | +457.46 | ~0 | ⚠️ WARN | Tends to over-predict |

**Assessment:** Critical performance.

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

### ❌ Average Selling Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 5660.30% | <9.0% | ❌ FAIL | Critical for FP&A reporting |
| MASE | 231.70 | <1.0 | ❌ FAIL | Worse than naïve by 23070% |
| SMAPE | 200.00% | - | INFO | Symmetric error |
| RMSE | 40259.77 | - | INFO | Error in original units |
| MAE | 40259.58 | - | INFO | Average absolute error |
| Bias | -40259.58 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Critical performance.

---

### ❌ Capacity Utilization
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 134.31% | <10.0% | ❌ FAIL | Critical for FP&A reporting |
| MASE | 0.67 | <1.0 | ✅ PASS | Beats naïve by 33% |
| SMAPE | 73.77% | - | INFO | Symmetric error |
| RMSE | 27.59 | - | INFO | Error in original units |
| MAE | 25.71 | - | INFO | Average absolute error |
| Bias | +1.22 | ~0 | INFO | Tends to over-predict |

**Assessment:** Critical performance.

---

### ❌ CO2 EUA Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 50.01% | <25.0% | ❌ FAIL | Critical for FP&A reporting |
| MASE | 7.63 | <1.0 | ❌ FAIL | Worse than naïve by 663% |
| SMAPE | 65.37% | - | INFO | Symmetric error |
| RMSE | 17.37 | - | INFO | Error in original units |
| MAE | 16.86 | - | INFO | Average absolute error |
| Bias | -11.38 | ~0 | ⚠️ WARN | Tends to under-predict |

**Assessment:** Critical performance.

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
| Revenue | MASE >1.0 | 1.28 | Evaluate model configuration |
| EBITDA | MASE >1.0 | 2.16 | Evaluate model configuration |
| Sales Volume | MASE >1.0 | 23.53 | Evaluate model configuration |
| Electricity Cost | MASE >1.0 | 1.52 | Evaluate model configuration |
| Thermal Energy Cost | MASE >1.0 | 1.72 | Evaluate model configuration |
| Average Selling Price | MASE >1.0 | 231.70 | Evaluate model configuration |
| CO2 EUA Price | MASE >1.0 | 7.63 | Evaluate model configuration |

### 🟡 Warning - Monitor & Improve
| Variable | Issue | Current | Target | Gap |
|----------|-------|---------|--------|-----|
| Variable Cost per Ton | Exceeds target | 47.26% | 8.0% | +39.26% |
| Pet Coke Price | Near threshold | 30.05% | 31.0% | -0.95% |
| Capacity Utilization | Exceeds target | 134.31% | 10.0% | +124.31% |
| 3-Month EURIBOR Rate | Near threshold | 22.89% | 23.0% | -0.11% |
| Portugal GDP Growth (YoY) | Near threshold | 54.76% | 55.0% | -0.24% |
| Construction Confidence Indicator | Near threshold | 62.09% | 63.0% | -0.91% |

### 🟢 Good Performance - No Action Required
Natural Gas Price (TTF), Portugal HICP Inflation, Diesel Price (EU), Industrial Electricity Price, Construction Output Index, Industrial Production Index, Building Permits (Portugal)

## Cross-Variable Performance

### MASE Ranking (Lower is Better)
| Rank | Variable | MASE | vs Naïve |
|------|----------|------|----------|
| 1 | Portugal HICP Inflation | 0.08 | 92% better |
| 2 | Natural Gas Price (TTF) | 0.29 | 71% better |
| 3 | 3-Month EURIBOR Rate | 0.31 | 69% better |
| 4 | Construction Output Index | 0.32 | 68% better |
| 5 | Pet Coke Price | 0.32 | 68% better |
| 6 | Construction Confidence Indicator | 0.35 | 65% better |
| 7 | Industrial Production Index | 0.44 | 56% better |
| 8 | Portugal GDP Growth (YoY) | 0.64 | 36% better |
| 9 | Capacity Utilization | 0.67 | 33% better |
| 10 | Diesel Price (EU) | 0.76 | 24% better |
| 11 | Industrial Electricity Price | 0.77 | 23% better |
| 12 | Variable Cost per Ton | 0.89 | 11% better |
| 13 | Building Permits (Portugal) | 0.91 | 9% better |
| 14 | Revenue | 1.28 | 28% worse |
| 15 | Electricity Cost | 1.52 | 52% worse |
| 16 | Thermal Energy Cost | 1.72 | 72% worse |
| 17 | EBITDA | 2.16 | 116% worse |
| 18 | CO2 EUA Price | 7.63 | 663% worse |
| 19 | Sales Volume | 23.53 | 2253% worse |
| 20 | Average Selling Price | 231.70 | 23070% worse |

### Variables Where Model Adds Most Value
1. **Portugal HICP Inflation** - MASE 0.08 (92% better than naïve)
2. **Natural Gas Price (TTF)** - MASE 0.29 (71% better than naïve)
3. **3-Month EURIBOR Rate** - MASE 0.31 (69% better than naïve)

### Variables Where Model Needs Work
1. **Revenue** - MASE 1.28 (28% worse than naïve)
2. **Electricity Cost** - MASE 1.52 (52% worse than naïve)
3. **Thermal Energy Cost** - MASE 1.72 (72% worse than naïve)
4. **EBITDA** - MASE 2.16 (116% worse than naïve)
5. **CO2 EUA Price** - MASE 7.63 (663% worse than naïve)
6. **Sales Volume** - MASE 23.53 (2253% worse than naïve)
7. **Average Selling Price** - MASE 231.70 (23070% worse than naïve)
