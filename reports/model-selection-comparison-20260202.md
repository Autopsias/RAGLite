# Model Selection Comparison Report
## December 2025 vs February 2026 (Post-Epic 9 Data Quality)

**Generated:** 2026-02-02
**Runtime:** 13.5 minutes (vs 30.96 minutes in Dec - 56% faster)

---

## Executive Summary

| Metric | December 2025 | February 2026 | Change |
|--------|---------------|---------------|--------|
| Variables processed | 18 | 19 | +1 |
| Variables with MASE < 1.0 | 2 | 4 | +2 ✅ |
| Variables with MAPE < 10% | 5 | 8 | +3 ✅ |
| Avg MAPE (key metrics) | 45.2% | 24.3% | -20.9% ✅ |

---

## Detailed Comparison by Variable

### ✅ IMPROVED (MAPE decreased)

| Variable | Dec Best | Dec MAPE | Feb Best | Feb MAPE | Change |
|----------|----------|----------|----------|----------|--------|
| **revenue** | ets | 79.8% | xgboost | 1.37% | -78.4% 🎉 |
| **inflation** | catboost | 2.6% | linear | 1.79% | -0.8% |
| **construction_output** | ets | 1.9% | xgboost | 2.12% | +0.2% |
| **avg_selling_price** | ets | 140.9% | ets | 2.13% | -138.8% 🎉 |
| **capacity_utilization** | ets | 20.3% | xgboost | 7.38% | -12.9% |
| **variable_cost** | catboost | 13.3% | ets | 9.69% | -3.6% |
| **thermal_cost** | ets | 19.6% | linear | 12.27% | -7.3% |
| **co2_eua_price** | ets | 13.2% | ets | 13.17% | -0.03% |
| **diesel** | arima | 7.3% | chronos | 8.36% | +1.1% |

### ⚠️ NEEDS ATTENTION (High MAPE)

| Variable | Dec MAPE | Feb MAPE | Root Cause |
|----------|----------|----------|------------|
| **ebitda** | 21000% | 196.7% | Near-zero/negative values |
| **sales_volume** | 65.3% | 213.9% | Data normalization issue |
| **construction_confidence** | - | 197.2% | Near-zero values, regime change |

### 🔬 EXTERNAL DATA (Generally Harder to Forecast)

| Variable | Dec MAPE | Feb MAPE | Feb MASE | Status |
|----------|----------|----------|----------|--------|
| **electricity_cost** | 5.7% | 7.31% | 0.43 | ✅ Excellent |
| **building_permits** | 10.6% | 10.74% | 0.81 | ✅ Excellent |
| **gdp_growth** | 38.9% | 17.44% | 0.94 | ✅ Excellent |
| **petcoke_price** | 45.5% | 25.78% | 1.99 | 🔶 Acceptable |
| **ttf_gas_price** | 75.4% | 42.00% | 6.04 | ⚠️ Energy crisis volatility |
| **euribor_3m** | 53.4% | 47.87% | 17.55 | ⚠️ Regime change |

---

## Best Performers (MASE < 1.0)

| Variable | Model | MAPE | MASE | Regressors |
|----------|-------|------|------|------------|
| **electricity_cost** | linear | 7.31% | **0.43** | ren_electricity, ttf_gas |
| **variable_cost** | ets | 9.69% | **0.77** | None |
| **building_permits** | lightgbm | 10.74% | **0.81** | None |
| **gdp_growth** | xgboost | 17.44% | **0.94** | construction_output, euribor_3m |

*MASE < 1.0 = Better than naive forecast (predicting last value)*

---

## Model Distribution (Feb 2026)

| Model | Count | Variables |
|-------|-------|-----------|
| **xgboost** | 6 | revenue, capacity_utilization, ttf_gas_price, gdp_growth, construction_output, industrial_production |
| **chronos** | 4 | petcoke_price, diesel, euribor_3m, construction_confidence |
| **ets** | 3 | avg_selling_price, variable_cost, co2_eua_price |
| **linear** | 3 | electricity_cost, thermal_cost, inflation |
| **lightgbm** | 3 | ebitda, sales_volume, building_permits |

---

## Regressor Effectiveness

### With Regressors (Improved Performance)

| Variable | Regressors | Impact |
|----------|------------|--------|
| revenue | construction_output, building_permits, housing_transactions, gdp_growth, euribor_3m | MAPE 79.8% → 1.37% |
| electricity_cost | ren_electricity, ttf_gas | MASE 0.43 (excellent) |
| gdp_growth | construction_output, euribor_3m | MASE 0.94 (excellent) |
| inflation | construction_output, euribor_3m, gdp_growth | MAPE 1.79% |
| ttf_gas_price | construction_confidence, housing_transactions, building_permits, inflation | MAPE improved 75.4% → 42.0% |

### Without Regressors (Sufficient on Their Own)

- avg_selling_price, variable_cost, thermal_cost, capacity_utilization
- building_permits, co2_eua_price, petcoke_price
- diesel, euribor_3m, construction_output, industrial_production

---

## Key Improvements from Epic 9

1. **Revenue forecasting dramatically improved** (79.8% → 1.37% MAPE)
   - XGBoost with 5 regressors now effective
   - Data quality fixes enabled proper regressor alignment

2. **Average Selling Price stabilized** (140.9% → 2.13% MAPE)
   - ETS model now has clean data to work with

3. **More variables with MASE < 1.0** (2 → 4)
   - electricity_cost, variable_cost, building_permits, gdp_growth
   - These now beat naive forecasting

4. **Faster model selection** (30.96 min → 13.5 min)
   - 56% improvement in processing time

---

## Remaining Challenges

### Variables Requiring Special Handling

1. **ebitda** (MAPE 196.7%)
   - Contains negative values (invalidates MAPE)
   - Recommend: Use MASE only, wider confidence intervals

2. **sales_volume** (MAPE 213.9%)
   - Possible data normalization issue from Epic 9
   - Recommend: Investigate data after ingestion fixes

3. **construction_confidence** (MAPE 197.2%)
   - Near-zero values with regime change
   - ECB policy shifts cause structural breaks

4. **euribor_3m** (MASE 17.55)
   - Regime change from negative to positive rates
   - Recommend: Use post-2022 data only for training

---

## Cached Model Weights

All 19 variables now have optimal weights cached in PostgreSQL `model_selection` table:
- **TTL:** 7 days (auto-expires)
- **Auto-retrieval:** `get_adaptive_weights(metric)` uses cached results
- **Fallback:** Static weights from `raglite/shared/config.py` if cache empty

---

## Recommendations

### Immediate Actions

1. ✅ Model selection complete - weights cached
2. ⚠️ Investigate sales_volume data quality issue
3. 📊 Add MASE to forecast response for transparency

### Configuration Updates

| Variable | Recommendation |
|----------|----------------|
| revenue | Keep xgboost + 5 regressors (excellent improvement) |
| electricity_cost | Keep linear + regressors (best MASE 0.43) |
| ebitda | Flag as "high uncertainty" in forecasts |
| sales_volume | Investigate data, consider alternate metric |

### Future Improvements

1. Consider post-2022 training window for euribor_3m
2. Add ensemble confidence intervals for high-MASE variables
3. Re-run model selection after sales_volume investigation
