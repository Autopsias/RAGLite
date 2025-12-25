# Model Selection Analysis Report - December 23, 2025

## Executive Summary

Comprehensive analysis of 18 forecasting variables with focus on:
1. MAPE vs MASE metric evaluation
2. Regressor effectiveness investigation
3. Date alignment bug fix
4. Poor performer root cause analysis

### Key Findings

| Finding | Impact | Action |
|---------|--------|--------|
| **Date alignment bug** | 0% regressor overlap for external time series | Fixed via month-start normalization |
| **EBITDA regressors** | Don't improve due to data characteristics | Accept MASE 2.21 baseline |
| **Poor performers** | ttf_gas, euribor_3m, api2_coal have MASE >11 | Accept as systemic limitation |
| **Excellent performers** | electricity_cost (0.44), building_permits (0.79) | Use as showcase |

---

## 1. Date Alignment Bug Fix

### Problem Identified
External time series (ttf_gas_price, api2_coal, etc.) were resampled to month-END dates (`2017-10-31`), while regressors use month-START dates (`2017-10-01`). This caused 0% overlap during regressor alignment.

### Root Cause
```python
# timeseries_extract.py line 3017:
monthly = df.resample("ME").mean()  # Month-END

# model_selection.py alignment used direct reindex:
aligned = reg_series.reindex(target_index, method="ffill")  # No date match!
```

### Fix Applied
```python
# model_selection.py - Normalize both to month-start before alignment
normalized_target = target_index.to_period("M").to_timestamp()
reg_normalized.index = reg_series.index.to_period("M").to_timestamp()
aligned = reg_normalized.reindex(normalized_target, method="ffill")
```

### Result
| Variable | Before Fix | After Fix |
|----------|-----------|-----------|
| ttf_gas_price - construction_confidence | 0% overlap | 100% aligned |
| ttf_gas_price - gdp_growth | 0% overlap | 100% aligned |
| ttf_gas_price - inflation | 0% overlap | 100% aligned |
| ttf_gas_price - diesel | 12% overlap | 100% aligned |

---

## 2. MAPE vs MASE Evaluation

### When to Trust Each Metric

| Metric | Trust When | Don't Trust When |
|--------|------------|------------------|
| **MAPE** | Values consistently >10 | Near-zero values, negative values |
| **MASE** | Always reliable | (Always use as primary metric) |

### Why MASE is Superior

MASE (Mean Absolute Scaled Error) benchmarks against a naive forecast:
- MASE < 1.0 = Better than naive (predicting last value)
- MASE = 1.0 = Same as naive
- MASE > 1.0 = Worse than naive

**Critical**: High MAPE with low MASE indicates MAPE inflation from denominators, not poor forecasting.

### Variable Classification by MASE

#### Excellent (MASE < 1.0)
| Variable | Model | MAPE | MASE | Regressors |
|----------|-------|------|------|------------|
| electricity_cost | linear | 5.7% | **0.44** | ren_electricity, ttf_gas |
| building_permits | lightgbm | 10.6% | **0.79** | None |

#### Good (MASE 1.0-1.3)
| Variable | Model | MAPE | MASE | Regressors |
|----------|-------|------|------|------------|
| revenue | ets | 79.8% | **1.09** | None |
| co2_eua_price | ets | 13.2% | **1.23** | None |
| avg_selling_price | ets | 140.9% | **1.29** | None |
| gdp_growth | catboost | 38.9% | **1.30** | construction_output, euribor_3m |

#### Acceptable (MASE 1.3-2.0)
| Variable | Model | MAPE | MASE | Regressors |
|----------|-------|------|------|------------|
| sales_volume | lightgbm | 65.3% | **1.41** | None |
| variable_cost | catboost | 13.3% | **1.62** | api2_coal, ttf_gas |
| thermal_cost | ets | 19.6% | **1.68** | None |
| capacity_utilization | ets | 20.3% | **1.81** | None |
| construction_output | ets | 1.9% | **1.93** | None |

#### Poor (MASE > 2.0)
| Variable | Model | MAPE | MASE | Root Cause |
|----------|-------|------|------|------------|
| ebitda | lightgbm | 21000% | **2.21** | Negative/near-zero values |
| petcoke_price | xgboost | 45.5% | **2.79** | Commodity volatility |
| inflation | catboost | 2.6% | **5.20** | Near-zero values |
| diesel | arima | 7.3% | **5.94** | Model selection issue |
| api2_coal | arima | 23.2% | **11.46** | 2022 energy crisis |
| ttf_gas_price | ets | 75.4% | **11.55** | 2022 energy crisis |
| euribor_3m | ets | 53.4% | **13.97** | Regime change |

---

## 3. EBITDA Regressor Investigation

### Data Characteristics
- **Points**: 40 (limited for ML models)
- **Date range**: 2022-03 to 2025-09
- **Value range**: -41.70 to 149.08 M EUR
- **Near-zero values**: 6 (15%)
- **Negative values**: 3 (7.5%)

### Configured Regressors
| Regressor | Overlap | Issue |
|-----------|---------|-------|
| euribor_3m | 100% | Good alignment |
| ttf_gas | 67.5% | Below 80% threshold |
| diesel | 15% | Critical - almost no data |
| api2_coal | 70% | Below 80% threshold |

### Model Selection Results
| Model | MAPE | MASE | With Regressors |
|-------|------|------|-----------------|
| lightgbm | 21000% | **2.21** | Yes (same as No) |
| chronos | 19444% | 2.29 | No |
| ets | 31797% | 2.66 | No |

**Conclusion**: Regressors don't help EBITDA because:
1. Poor data alignment (diesel 15% overlap)
2. Only 40 data points insufficient for multivariate models
3. Target has negative values (invalidates MAPE)
4. Energy prices (regressors) shifted dramatically in 2022

---

## 4. Poor Performer Root Cause Analysis

### TTF Gas Price (MASE 11.55)
| Metric | Value |
|--------|-------|
| Coefficient of Variation | 99.1% |
| Max monthly spike | +60.1% |
| Max monthly drop | -45.2% |
| Extreme moves (>30%) | 10 months |

**Regime Analysis**:
- Period 1 (2017-2019): mean €18.96/MWh
- Period 2 (2019-2021): mean €21.19/MWh
- Period 3 (2021-2023): mean €89.67/MWh (energy crisis peak)
- Period 4 (2023-2025): mean €35.50/MWh

**Root Cause**: 2022 energy crisis caused unprecedented +211% mean shift.

### Euribor_3m (MASE 13.97)
| Metric | Value |
|--------|-------|
| Coefficient of Variation | 101.0% |
| Near-zero values | 35% of data |
| Max monthly spike | +978% |
| Mean shift | +721.6% |

**Regime Analysis**:
- Period 1 (2020-2022): mean -0.55% (negative rates)
- Period 2 (2022-2023): mean 1.31% (transition)
- Period 3 (2023-2024): mean 3.81% (new regime)
- Period 4 (2024-2025): mean 2.44% (stabilizing)

**Root Cause**: ECB policy regime change from negative to positive rates.

### API2 Coal (MASE 11.46)
| Metric | Value |
|--------|-------|
| Coefficient of Variation | 54.5% |
| Max monthly spike | +35.8% |
| Max monthly drop | -40.0% |
| Mean shift | -43.0% |

**Regime Analysis**:
- Correlated with TTF gas crisis (substitution effect)
- Russia-Ukraine conflict supply chain disruption
- Price spike to €244/ton in 2022, now €104/ton

**Root Cause**: Geopolitical events and energy crisis spillover.

---

## 5. Recommendations

### Immediate Actions

1. **Deploy date alignment fix** - Critical for regressor effectiveness
2. **Use MASE as primary evaluation metric** - More reliable than MAPE
3. **Flag uncertain variables** - ttf_gas_price, euribor_3m, api2_coal

### Model Configuration

| Variable | Recommendation |
|----------|---------------|
| electricity_cost | Keep linear + regressors (best performer) |
| building_permits | Keep lightgbm (excellent MASE) |
| revenue | Consider adding regressors now that alignment fixed |
| thermal_cost | Add ttf_gas, api2_coal regressors |
| ttf_gas_price | Test with regressors after alignment fix |
| euribor_3m | Consider post-2022 data only |

### Variables to Re-evaluate After Fix

The date alignment fix may significantly improve these:
- ttf_gas_price (now has regressor alignment)
- petcoke_price (commodity correlation)
- thermal_cost (energy cost drivers)
- variable_cost (operational cost drivers)

### Acceptance Criteria for Poor Performers

For variables with MASE >5 due to external shocks:
- Accept higher uncertainty in forecasts
- Add disclaimer: "Subject to significant external risk factors"
- Consider ensemble with wider confidence intervals
- Use post-crisis data only for current regime

---

## 6. Technical Details

### Files Modified
- `raglite/forecasting/model_selection.py` - Date normalization fix

### Files Created
- `scripts/investigate_regressor_alignment.py` - Alignment analysis
- `scripts/investigate_poor_performers.py` - Root cause analysis
- `reports/model-selection-analysis-20251223.md` - This report

### Key Code Change
```python
# Before (broken):
aligned = reg_series.reindex(target_index, method="ffill")

# After (fixed):
normalized_target = target_index.to_period("M").to_timestamp()
reg_normalized.index = reg_series.index.to_period("M").to_timestamp()
reg_normalized = reg_normalized.groupby(reg_normalized.index).mean()
aligned = reg_normalized.reindex(normalized_target, method="ffill")
aligned.index = target_index
```

---

## Appendix: Full Model Selection Results (Latest Run)

| Variable | Best Model | MAPE | MASE | Uses Regressors | Regressor Set |
|----------|------------|------|------|-----------------|---------------|
| revenue | ets | 79.8% | 1.09 | No | - |
| ebitda | lightgbm | 21000% | 2.21 | No | - |
| sales_volume | lightgbm | 65.3% | 1.41 | No | - |
| thermal_cost | ets | 19.6% | 1.68 | No | - |
| variable_cost | catboost | 13.3% | 1.62 | Yes | api2_coal, ttf_gas |
| capacity_utilization | ets | 20.3% | 1.81 | No | - |
| avg_selling_price | ets | 140.9% | 1.29 | No | - |
| ttf_gas_price | ets | 75.4% | 11.55 | No | - |
| petcoke_price | xgboost | 45.5% | 2.79 | Yes | gdp_growth, inflation, diesel |
| co2_eua_price | ets | 13.2% | 1.23 | No | - |
| electricity_cost | linear | 5.7% | 0.44 | Yes | ren_electricity, ttf_gas |
| diesel | arima | 7.3% | 5.94 | No | - |
| api2_coal | arima | 23.2% | 11.46 | Yes | ttf_gas |
| gdp_growth | catboost | 38.9% | 1.30 | Yes | construction_output, euribor_3m |
| inflation | catboost | 2.6% | 5.20 | No | - |
| euribor_3m | ets | 53.4% | 13.97 | No | - |
| construction_output | ets | 1.9% | 1.93 | No | - |
| building_permits | lightgbm | 10.6% | 0.79 | No | - |

---

*Generated: 2025-12-23*
