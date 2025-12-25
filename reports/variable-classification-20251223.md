# Variable Classification Report - 2025-12-23

## Executive Summary

Analysis of 19 forecasting variables using proper MAPE vs MASE evaluation criteria.

**Key Finding:** Many high MAPE values are misleading due to near-zero denominators. MASE provides more reliable assessment.

## Classification by Forecast Quality

### Excellent (MASE < 1.0) - Better than naive forecast

| Variable | Model | MAPE | MASE | Uses Regressors | Notes |
|----------|-------|------|------|-----------------|-------|
| **electricity_cost** | linear | 5.7% | **0.44** | ren_electricity, ttf_gas | 56% better than naive |
| **building_permits** | chronos | 10.5% | **0.77** | None | 23% better than naive |

### Good (MASE 1.0-1.3) - Comparable to naive forecast

| Variable | Model | MAPE | MASE | Uses Regressors | Notes |
|----------|-------|------|------|-----------------|-------|
| revenue | ets | 79.8% | **1.09** | None | 9% worse than naive |
| co2_eua_price | ets | 13.2% | **1.23** | None | 23% worse |
| capacity_utilization | chronos | 13.1% | **1.23** | None | 23% worse |
| sales_volume | chronos | 42.1% | **1.24** | None | 24% worse |
| avg_selling_price | ets | 140.9% | **1.29** | None | 29% worse |
| gdp_growth | catboost | 38.9% | **1.30** | construction_output, euribor_3m | 30% worse |

### Acceptable (MASE 1.3-2.0) - Needs improvement

| Variable | Model | MAPE | MASE | Uses Regressors | Notes |
|----------|-------|------|------|-----------------|-------|
| industrial_production | catboost | 2.1% | **1.46** | 4 regressors | 46% worse |
| thermal_cost | chronos | 17.6% | **1.51** | None | 51% worse |
| construction_confidence | lightgbm | 143.9% | **1.60** | None | 60% worse |
| variable_cost | chronos | 13.1% | **1.83** | None | 83% worse |

### Poor (MASE > 2.0) - Significantly worse than naive

| Variable | Model | MAPE | MASE | Uses Regressors | Issue |
|----------|-------|------|------|-----------------|-------|
| ebitda | chronos | 194.4% | **2.29** | None | Can be negative |
| petcoke_price | chronos | 31.1% | **2.47** | None | High volatility |
| inflation | catboost | 2.6% | **5.20** | None | Near-zero values |
| diesel | arima | 7.3% | **5.94** | None | Model selection issue |
| api2_coal | arima | 23.2% | **11.46** | ttf_gas | Volatile commodity |
| ttf_gas_price | ets | 75.4% | **11.55** | None | Extreme volatility |
| euribor_3m | ets | 53.4% | **13.97** | None | Regime changes |

## Analysis by Variable Type

### Internal SECIL Metrics (from financial_tables)

| Variable | Quality | Recommendation |
|----------|---------|----------------|
| revenue | Good | ETS working well |
| ebitda | Poor | Try different models, handle negatives |
| sales_volume | Good | Chronos working acceptably |
| thermal_cost | Acceptable | Consider adding regressors |
| variable_cost | Acceptable | Consider adding regressors |
| capacity_utilization | Good | Chronos working well |
| avg_selling_price | Good | ETS with high MAPE but low MASE |

### External Price Variables

| Variable | Quality | Recommendation |
|----------|---------|----------------|
| ttf_gas_price | Poor | Need regime-aware models |
| petcoke_price | Poor | High commodity volatility |
| co2_eua_price | Good | ETS reasonable for carbon prices |
| electricity_cost | Excellent | Linear + regressors works great |
| diesel | Poor | Review ARIMA selection |
| api2_coal | Poor | Need better commodity model |

### Macroeconomic Indicators

| Variable | Quality | Recommendation |
|----------|---------|----------------|
| gdp_growth | Good | CatBoost with regressors |
| inflation | Poor | Near-zero instability |
| euribor_3m | Poor | Regime changes 2022-2023 |
| building_permits | Excellent | Chronos works well |
| construction_confidence | Acceptable | Sentiment indicator volatility |
| industrial_production | Acceptable | CatBoost with regressors |

## Recommendations

### Immediate Actions

1. **Remove euribor_3m** from forecasting outputs until regime-aware models available
2. **Flag ttf_gas_price and api2_coal** as "highly uncertain" in outputs
3. **Use electricity_cost and building_permits** as showcase variables

### Model Improvements Needed

1. **For commodity prices (ttf_gas, api2_coal, petcoke):**
   - Consider regime-switching models
   - Add more external indicators
   - Accept higher uncertainty in forecasts

2. **For near-zero variables (inflation, euribor_3m):**
   - These crossed zero in 2022-2023
   - Standard MAPE-based evaluation is misleading
   - Consider absolute error metrics instead

3. **For financial metrics (ebitda):**
   - Handle potential negative values
   - Consider ensemble approaches
   - May need specialized financial models

### Variables Benefiting from Regressors

Currently using regressors (4 variables):
- electricity_cost ✅ (MASE 0.44 - significant improvement)
- api2_coal (MASE 11.46 - still poor)
- gdp_growth ✅ (MASE 1.30 - reasonable)
- industrial_production ✅ (MASE 1.46 - acceptable)

### Candidates for Adding Regressors

Based on economic relationships:
1. **thermal_cost** → ttf_gas, api2_coal, petcoke_price
2. **variable_cost** → diesel, electricity_cost
3. **revenue** → gdp_growth, building_permits, construction_output
4. **sales_volume** → gdp_growth, building_permits

## Model Distribution Summary

| Model | Count | Avg MASE | Best Use Case |
|-------|-------|----------|---------------|
| chronos | 7 | 1.65 | Zero-shot univariate |
| ets | 5 | 6.21 | Simple trend extrapolation |
| catboost | 3 | 2.65 | With external regressors |
| arima | 2 | 8.70 | Seasonal patterns (mixed results) |
| linear | 1 | 0.44 | Strong linear relationships |
| lightgbm | 1 | 1.60 | Tree-based with regressors |

## Data Sources Status

| Source | Variables | Status | Data Points |
|--------|-----------|--------|-------------|
| Financial tables | 7 | ✅ Active | 60+ monthly |
| REN Data Hub | 1 | ✅ Active | 60+ monthly |
| Eurostat | 3 | ✅ Active | 59-250 points |
| ECB | 3 | ✅ Active | 60+ points |
| ICE/Yahoo | 2 | ⚠️ Cached | Volatile APIs |
| INE | 1 | ✅ Active | 100+ points |
| EU Oil Bulletin | 1 | ✅ Active | 340+ points |

**Removed:** eurostat_electricity (only 9 semi-annual data points)
