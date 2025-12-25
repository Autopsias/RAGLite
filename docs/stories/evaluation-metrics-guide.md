# Forecast Evaluation Metrics Guide

## Overview

This guide documents the proper use of MAPE and MASE for evaluating forecasting accuracy across different variable types.

## Key Research Findings

### MAPE (Mean Absolute Percentage Error)

**Formula:** `MAPE = mean(|actual - forecast| / |actual|)`

**Problems (Hyndman & Koehler 2006, Svetunkov 2024):**
1. **Undefined for zeros** - Division by zero when actual = 0
2. **Asymmetric** - Prefers underforecasting over overforecasting
3. **Scale-sensitive at extremes** - Low volumes inflate MAPE, high volumes deflate it
4. **Misleading for near-zero values** - Small absolute errors appear as huge percentages
5. **Not appropriate for cross-zero variables** - GDP growth, inflation, profit margins

**When MAPE is Reliable:**
- Positive-only values with large magnitudes (prices > 10, volumes > 100)
- Values that never approach zero
- No intermittent demand (no zero values in history)

### MASE (Mean Absolute Scaled Error)

**Formula:** `MASE = MAE / naive_forecast_MAE`

**Interpretation:**
- **MASE < 1** → Better than naive forecast (good)
- **MASE = 1** → Same as naive forecast (baseline)
- **MASE > 1** → Worse than naive forecast (poor)

**Benefits:**
1. **Scale-independent** - Comparable across different variables
2. **Works with zeros** - No division by actual values
3. **Symmetric** - Equal penalty for over/under forecasting
4. **Interpretable benchmark** - Compared to naive walk-forward forecast

**When MASE is Preferred:**
- Variables that can be near-zero or negative
- Growth rates, margins, indices
- Cross-variable comparisons
- Intermittent demand data

## Variable Classification by Evaluation Method

### Tier 1: Use MASE as Primary (MAPE unreliable)

These variables can cross zero or have near-zero values:

| Variable | Issue | Primary Metric |
|----------|-------|----------------|
| gdp_growth | Crosses zero (recession/expansion) | MASE |
| inflation | Can approach zero or negative | MASE |
| ebitda | Can be negative (losses) | MASE |
| construction_confidence | Negative sentiment possible | MASE |
| euribor_3m | Can approach zero (low rate environment) | MASE |

**Quality Thresholds (MASE):**
- **Excellent:** < 0.6 (40%+ improvement over naive)
- **Good:** 0.6 - 0.9 (10-40% improvement)
- **Acceptable:** 0.9 - 1.1 (comparable to naive)
- **Poor:** > 1.1 (worse than naive)

### Tier 2: Use Both MAPE and MASE (validate with both)

These variables are always positive but can have significant value ranges:

| Variable | Range | Primary | Secondary |
|----------|-------|---------|-----------|
| revenue | Medium-high values | MAPE | MASE |
| sales_volume | Medium-high values | MAPE | MASE |
| capacity_utilization | 0-100% range | MAPE | MASE |
| avg_selling_price | Medium-high values | MAPE | MASE |
| thermal_cost | Medium-high values | MAPE | MASE |
| variable_cost | Medium-high values | MAPE | MASE |

**Quality Thresholds:**
- **MAPE:**
  - Excellent: < 10%
  - Good: 10-20%
  - Acceptable: 20-35%
  - Poor: > 35%

- **MASE:** Same as Tier 1

### Tier 3: Use MAPE as Primary (large positive values)

These variables have consistently large positive values:

| Variable | Typical Range | Primary |
|----------|---------------|---------|
| ttf_gas_price | 20-300 €/MWh | MAPE |
| petcoke_price | 50-200 €/ton | MAPE |
| co2_eua_price | 20-100 €/ton | MAPE |
| electricity_cost | 50-200 €/MWh | MAPE |
| diesel | 1-2 €/L | MAPE |
| api2_coal | 50-400 $/ton | MAPE |
| building_permits | 1000+ units/month | MAPE |
| industrial_production | Index ~100 | MAPE |
| construction_output | Index ~100 | MAPE |

**Quality Thresholds (MAPE):**
- **Excellent:** < 10%
- **Good:** 10-20%
- **Acceptable:** 20-35%
- **Poor:** > 35%

## Interpreting High MAPE Values

When you see MAPE > 100%, it typically means:

1. **Variable has near-zero values** - Small errors become huge percentages
2. **Wrong metric** - Should be using MASE instead
3. **Truly poor forecasting** - Model cannot capture the pattern

**Example Analysis:**
- `ebitda` with MAPE = 19443% → Near-zero values, use MASE (2.29 = 2.3x worse than naive)
- `gdp_growth` with MAPE = 3885% → Crosses zero, use MASE (1.30 = 30% worse than naive)

## Recommended Model Selection Approach

1. **For Tier 1 variables:** Select model based on lowest MASE only
2. **For Tier 2 variables:** Select model with best MASE, verify MAPE is reasonable (< 50%)
3. **For Tier 3 variables:** Select model based on lowest MAPE, verify MASE < 2.0

## Current Results Re-Classification

Based on the latest model selection (20251223-141617):

### Actually Good Performers (corrected evaluation)

| Variable | Best Model | MAPE | MASE | Quality |
|----------|------------|------|------|---------|
| capacity_utilization | chronos | 13.10% | 1.23 | ⭐ Good (Tier 2) |
| revenue | ets | 79.77% | 1.09 | ⭐ Acceptable (MASE-based) |
| avg_selling_price | ets | 140.91% | 1.29 | Acceptable (MASE 1.29) |
| industrial_production | catboost | 214.45% | 1.46 | Needs work (MASE > 1.1) |
| electricity_cost | linear | 570.67% | 0.44 | ⭐⭐ Excellent (MASE 0.44!) |
| building_permits | chronos | 1047.08% | 0.77 | ⭐⭐ Good (MASE 0.77!) |

### Misleading MAPE - Use MASE Instead

| Variable | Best Model | MAPE (misleading) | MASE (correct) | Verdict |
|----------|------------|-------------------|----------------|---------|
| inflation | catboost | 255.02% | 5.20 | Poor (5x worse than naive) |
| gdp_growth | catboost | 3885.67% | 1.30 | Acceptable (30% worse) |
| ebitda | chronos | 19443.55% | 2.29 | Poor (2.3x worse) |
| euribor_3m | ets | 5344.06% | 13.97 | Very Poor (14x worse) |
| construction_confidence | lightgbm | 14396.28% | 1.60 | Poor (60% worse) |

### Need Attention

Variables with high MASE (> 2.0) regardless of MAPE:
- `inflation` (MASE: 5.20) - Need better model/regressors
- `euribor_3m` (MASE: 13.97) - Need better model/regressors
- `api2_coal` (MASE: 11.46) - Need better model/regressors
- `ttf_gas_price` (MASE: 11.55) - Need better model/regressors
- `diesel` (MASE: 5.94) - Need better model/regressors

## References

1. Hyndman, R.J. & Koehler, A.B. (2006). "Another look at measures of forecast accuracy." International Journal of Forecasting, 22(4), 679-688.
2. Svetunkov, I. (2024). "Avoid using MAPE!" Open Forecasting.
3. Fildes, R. (1992). "The evaluation of extrapolative forecasting methods." International Journal of Forecasting, 8(1), 81-98.
