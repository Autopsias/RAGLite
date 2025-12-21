# ATDD Checklist: Story 7B.2 - Data Characteristics Analyzer

**Story:** 7B.2 - Data Characteristics Analyzer
**Epic:** 7B - Intelligent Model Selection Framework
**TDD Phase:** RED (All tests failing - module not implemented)

---

## Test Summary

| Metric | Value |
|--------|-------|
| Total Tests | 58 |
| Passing | 0 |
| Failing | 58 |
| Test File | `tests/unit/test_data_analyzer.py` |
| Created | 2025-12-20 |

---

## Acceptance Criteria Coverage

### AC1: Combined ADF + KPSS Stationarity Test
**Status:** RED

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-1.1 | `test_ac1_1_implement_adf_test` | FAIL | Implement ADF test (null: non-stationary) |
| TEST-AC-1.2 | `test_ac1_2_implement_kpss_test` | FAIL | Implement KPSS test (null: stationary) |
| TEST-AC-1.3 | `test_ac1_3_kwiatkowski_protocol_stationary` | FAIL | Kwiatkowski protocol - STATIONARY case |
| TEST-AC-1.4 | `test_ac1_4_kwiatkowski_protocol_non_stationary` | FAIL | Kwiatkowski protocol - NON_STATIONARY case |
| TEST-AC-1.5 | `test_ac1_5_return_stationarity_enum` | FAIL | Return stationarity enum |
| TEST-AC-1.6 | `test_ac1_6_return_both_pvalues` | FAIL | Return both p-values |
| TEST-AC-1.7 | `test_ac1_7_suggest_differencing_order_zero` | FAIL | Suggest differencing=0 for stationary |
| TEST-AC-1.8 | `test_ac1_8_suggest_differencing_order_one` | FAIL | Suggest differencing=1 for non-stationary |

---

### AC2: Seasonality Detection via ACF Analysis
**Status:** RED

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-2.1 | `test_ac2_1_compute_acf_for_monthly` | FAIL | Compute ACF for 24 lags (monthly) |
| TEST-AC-2.2 | `test_ac2_2_compute_acf_for_quarterly` | FAIL | Compute ACF for 8 lags (quarterly) |
| TEST-AC-2.3 | `test_ac2_3_detect_seasonal_peaks` | FAIL | Detect seasonal peaks at lag=period |
| TEST-AC-2.4 | `test_ac2_4_calculate_seasonal_strength` | FAIL | Calculate seasonal strength (0-1) |
| TEST-AC-2.5 | `test_ac2_5_classify_no_seasonality` | FAIL | Classify NONE for no seasonality |
| TEST-AC-2.6 | `test_ac2_6_classify_additive_seasonality` | FAIL | Classify ADDITIVE seasonality |
| TEST-AC-2.7 | `test_ac2_7_classify_multiplicative_seasonality` | FAIL | Classify MULTIPLICATIVE seasonality |
| TEST-AC-2.8 | `test_ac2_8_return_seasonal_period` | FAIL | Return seasonal period (12/4) |

---

### AC3: Trend Detection via Linear Regression
**Status:** RED

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-3.1 | `test_ac3_1_fit_ols_regression` | FAIL | Fit OLS regression: y = a + b*t |
| TEST-AC-3.2 | `test_ac3_2_calculate_trend_slope` | FAIL | Calculate trend slope (b coefficient) |
| TEST-AC-3.3 | `test_ac3_3_calculate_trend_significance` | FAIL | Calculate trend significance (p-value) |
| TEST-AC-3.4 | `test_ac3_4_classify_significant_trend` | FAIL | Classify significant trend (p<0.05) |
| TEST-AC-3.5 | `test_ac3_5_return_direction_up` | FAIL | Return direction UP |
| TEST-AC-3.6 | `test_ac3_6_return_direction_down` | FAIL | Return direction DOWN |
| TEST-AC-3.7 | `test_ac3_7_return_direction_flat` | FAIL | Return direction FLAT |

---

### AC4: Volatility Measurement
**Status:** RED

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-4.1 | `test_ac4_1_calculate_coefficient_of_variation` | FAIL | Calculate CV = std/mean |
| TEST-AC-4.2 | `test_ac4_2_classify_volatility_low` | FAIL | Classify LOW (CV < 0.1) |
| TEST-AC-4.3 | `test_ac4_3_classify_volatility_medium` | FAIL | Classify MEDIUM (0.1 <= CV < 0.3) |
| TEST-AC-4.4 | `test_ac4_4_classify_volatility_high` | FAIL | Classify HIGH (CV >= 0.3) |
| TEST-AC-4.5 | `test_ac4_5_return_cv_value` | FAIL | Return CV value and classification |

---

### AC5: Data Quality Metrics
**Status:** RED

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-5.1 | `test_ac5_1_calculate_data_length` | FAIL | Calculate data length |
| TEST-AC-5.2 | `test_ac5_2_calculate_missing_ratio` | FAIL | Calculate missing ratio (NaN/total) |
| TEST-AC-5.3 | `test_ac5_3_count_outliers_using_iqr` | FAIL | Count outliers using IQR method |
| TEST-AC-5.4 | `test_ac5_4_return_quality_metrics` | FAIL | Return quality metrics in DataCharacteristics |
| TEST-AC-5.5 | `test_ac5_5_no_missing_values` | FAIL | Return missing_ratio=0 for complete data |

---

### AC6: Return DataCharacteristics with Model Recommendations
**Status:** RED

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-6.1 | `test_ac6_1_return_datacharacteristics_dataclass` | FAIL | Return DataCharacteristics dataclass |
| TEST-AC-6.2 | `test_ac6_2_include_recommended_models` | FAIL | Include recommended_models: list[str] |
| TEST-AC-6.3 | `test_ac6_3_include_model_rationale` | FAIL | Include model_rationale: str |
| TEST-AC-6.4 | `test_ac6_4_prioritize_recommendations` | FAIL | Prioritize recommendations (best first) |
| TEST-AC-6.5 | `test_ac6_5_recommend_arima_linear_for_stationary` | FAIL | Recommend ARIMA/Linear for stationary |
| TEST-AC-6.6 | `test_ac6_6_recommend_prophet_ets_for_non_stationary` | FAIL | Recommend Prophet/ETS for non-stationary |
| TEST-AC-6.7 | `test_ac6_7_recommend_seasonal_models_for_seasonal_data` | FAIL | Recommend SARIMA/ETS/Prophet for seasonal |
| TEST-AC-6.8 | `test_ac6_8_recommend_ml_models_for_high_volatility` | FAIL | Recommend XGBoost/LightGBM for high volatility |
| TEST-AC-6.9 | `test_ac6_9_recommend_chronos_for_cold_start` | FAIL | Recommend Chronos-2 for cold-start (<12 pts) |
| TEST-AC-6.10 | `test_ac6_10_recommend_prophet_for_significant_trend` | FAIL | Recommend Prophet for significant trend |
| TEST-AC-6.11 | `test_ac6_11_handle_edge_case_constant_values` | FAIL | Handle constant values edge case |
| TEST-AC-6.12 | `test_ac6_12_handle_edge_case_short_series` | FAIL | Handle very short series edge case |

---

### AC7: Module Exports and Integration
**Status:** RED

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-7.1 | `test_ac7_1_export_datacharacteristics` | FAIL | Export DataCharacteristics |
| TEST-AC-7.2 | `test_ac7_2_export_stationarity_enum` | FAIL | Export Stationarity enum |
| TEST-AC-7.3 | `test_ac7_3_export_seasonality_type_enum` | FAIL | Export SeasonalityType enum |
| TEST-AC-7.4 | `test_ac7_4_export_volatility_level_enum` | FAIL | Export VolatilityLevel enum |
| TEST-AC-7.5 | `test_ac7_5_export_trend_direction_enum` | FAIL | Export TrendDirection enum |
| TEST-AC-7.6 | `test_ac7_6_export_analyze_data_characteristics_function` | FAIL | Export analyze_data_characteristics |

---

### Edge Cases
**Status:** RED

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| EDGE-1 | `test_edge_case_empty_series` | FAIL | Handle empty series |
| EDGE-2 | `test_edge_case_three_points` | FAIL | Handle 3-point series (min 4 required) |
| EDGE-3 | `test_edge_case_all_nans` | FAIL | Handle all-NaN series |
| EDGE-4 | `test_edge_case_negative_values` | FAIL | Handle negative values |
| EDGE-5 | `test_edge_case_zero_mean` | FAIL | Handle zero-mean series |
| EDGE-6 | `test_edge_case_frequency_detection` | FAIL | Auto-detect frequency from index |
| EDGE-7 | `test_datacharacteristics_has_all_fields` | FAIL | Verify all fields present |

---

## Test Fixtures

The test file includes the following synthetic data fixtures with known properties:

| Fixture | Properties | Purpose |
|---------|------------|---------|
| `stationary_series` | White noise, constant mean/variance | Test STATIONARY classification |
| `non_stationary_series` | Random walk, unit root | Test NON_STATIONARY classification |
| `trending_series` | Strong upward trend (slope ~2.0) | Test UP trend detection |
| `downward_trending_series` | Strong downward trend | Test DOWN trend detection |
| `seasonal_series` | Monthly seasonality (period=12) | Test seasonality detection |
| `multiplicative_seasonal_series` | Variance scales with level | Test MULTIPLICATIVE type |
| `quarterly_series` | Quarterly frequency (period=4) | Test quarterly handling |
| `high_volatility_series` | CV > 0.3 | Test HIGH volatility |
| `low_volatility_series` | CV < 0.1 | Test LOW volatility |
| `short_series` | 6 data points | Test cold-start detection |
| `very_short_series` | 4 data points | Test minimum data edge case |
| `constant_series` | All same values | Test constant value error |
| `series_with_nans` | 5 NaN values in 60 obs | Test missing ratio |
| `series_with_outliers` | 3 obvious outliers | Test IQR outlier detection |

---

## Implementation Checklist

### Files to Create

- [ ] `raglite/forecasting/data_analyzer.py` (~350 LOC)
  - [ ] Stationarity enum
  - [ ] SeasonalityType enum
  - [ ] VolatilityLevel enum
  - [ ] TrendDirection enum
  - [ ] DataCharacteristics dataclass
  - [ ] `_test_stationarity()` helper
  - [ ] `_detect_seasonality()` helper
  - [ ] `_detect_trend()` helper
  - [ ] `_measure_volatility()` helper
  - [ ] `_assess_data_quality()` helper
  - [ ] `_recommend_models()` helper
  - [ ] `_clean_series()` helper
  - [ ] `analyze_data_characteristics()` main function

### Dependencies (Already Available)

- `statsmodels.tsa.stattools.adfuller` - ADF test
- `statsmodels.tsa.stattools.kpss` - KPSS test
- `statsmodels.tsa.stattools.acf` - Autocorrelation function
- `scipy.stats.linregress` - Linear regression

---

## Run Commands

```bash
# Run all tests (will fail in RED phase)
uv run pytest tests/unit/test_data_analyzer.py -v

# Run specific AC tests
uv run pytest tests/unit/test_data_analyzer.py::TestStationarityTests -v
uv run pytest tests/unit/test_data_analyzer.py::TestSeasonalityDetection -v
uv run pytest tests/unit/test_data_analyzer.py::TestTrendDetection -v
uv run pytest tests/unit/test_data_analyzer.py::TestVolatilityMeasurement -v
uv run pytest tests/unit/test_data_analyzer.py::TestDataQualityMetrics -v
uv run pytest tests/unit/test_data_analyzer.py::TestModelRecommendations -v
uv run pytest tests/unit/test_data_analyzer.py::TestModuleExports -v
uv run pytest tests/unit/test_data_analyzer.py::TestEdgeCases -v

# Check coverage after implementation
uv run pytest tests/unit/test_data_analyzer.py --cov=raglite/forecasting/data_analyzer --cov-report=term-missing
```

---

## Next Steps

1. **GREEN Phase:** Implement `raglite/forecasting/data_analyzer.py` to make all tests pass
2. **REFACTOR Phase:** Optimize implementation while keeping tests green
3. **Coverage Check:** Verify >80% coverage on new module

---

## References

- [Story 7B.2](../stories/7b-2-data-characteristics-analyzer.md) - Full story definition
- [Epic 7B](../../prd/epic-7-intelligent-model-selection.md) - Parent epic
- [statsmodels ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html)
- [statsmodels KPSS](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html)
