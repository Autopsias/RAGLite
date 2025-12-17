# RAGLite Forecasting Validation Report
Generated: 2025-12-17T10:20:03.321970
Runtime: 18.6 seconds

## Overall Assessment: ❌ FAIL

### Quality Gate Results
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Variables Passing MAPE | ≥9/1 | 0/1 | ❌ FAIL |
| Average MASE | <1.0 | 1.57 | ❌ FAIL |

### Quick Summary
- **Excellent (MAPE <5%):** 0 variables
- **Good (MAPE 5-15%):** 0 variables
- **Needs Improvement (MAPE 15-30%):** 1 variables
- **Critical (MAPE >30%):** 0 variables

**Average MAPE:** 16.87%
**Average MASE:** 1.57 (worse than naïve)

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

### ❌ CO2 EUA Price
| Metric | Value | Target | Status | Interpretation |
|--------|-------|--------|--------|----------------|
| MAPE | 16.87% | <25.0% | ❌ FAIL | Moderate - needs investigation |
| MASE | 1.57 | <1.0 | ❌ FAIL | Worse than naïve by 57% |
| SMAPE | 17.74% | - | INFO | Symmetric error |
| RMSE | 14.94 | - | INFO | Error in original units |
| MAE | 12.49 | - | INFO | Average absolute error |
| Bias | -6.01 | ~0 | INFO | Tends to under-predict |

**Assessment:** Moderate performance.

---

## Action Items

### 🔴 Critical - Requires Immediate Attention
| Variable | Issue | MASE | Recommendation |
|----------|-------|------|----------------|
| CO2 EUA Price | MASE >1.0 | 1.57 | Evaluate model configuration |


## Actionable Guidance


### ⚙️ Consider Threshold Adjustment (No Reingestion)

**CO2 EUA Price** - MAPE 16.9% exceeds threshold 25.0%
- **Analysis:** Review data quality, regressors, and model configuration
- **Recommendation:** Run targeted diagnosis on this variable

## Cross-Variable Performance

### MASE Ranking (Lower is Better)
| Rank | Variable | MASE | vs Naïve |
|------|----------|------|----------|
| 1 | CO2 EUA Price | 1.57 | 57% worse |

### Variables Where Model Adds Most Value
1. **CO2 EUA Price** - MASE 1.57 (-57% better than naïve)

### Variables Where Model Needs Work
1. **CO2 EUA Price** - MASE 1.57 (57% worse than naïve)
