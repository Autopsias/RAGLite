# Forecasting Accuracy Improvement Analysis

**Date**: 2025-12-13
**Story**: 6.23 - Variable Cost MAPE Final Validation
**Objective**: Apply Variable Cost pattern (flat growth + no regressors) to other sparse data variables

## Summary

Applied the successful Variable Cost forecasting pattern to 4 additional sparse data variables:
- Electricity Cost
- Thermal Energy Cost
- Average Selling Price
- Capacity Utilization

**Result**: Mixed success - only Variable Cost continues to pass (<8.5% MAPE target).

## Changes Made

### 1. Disabled External Regressors
**File**: `/Users/ricardocarvalho/DeveloperFolder/RAGLite/raglite/forecasting/regressor_config.py`

Disabled regressors for sparse data variables (<150 data points):
```python
# Before (Story 6.20)
"electricity_cost": ["eurostat_electricity", "industrial_production"],
"thermal_cost": ["api2_coal", "ttf_gas", "industrial_production"],
"avg_selling_price": ["construction_confidence", "gdp_growth", "inflation", "diesel"],
"capacity_utilization": ["construction_output", "gdp_growth", "industrial_production"],

# After (Story 6.23)
"electricity_cost": [],  # Sparse data <100 points causes overfitting
"thermal_cost": [],  # Sparse data <100 points causes overfitting
"avg_selling_price": [],  # Sparse data <100 points causes overfitting
"capacity_utilization": [],  # Sparse data <150 points causes overfitting
```

### 2. Enabled Flat Growth for Prophet
**File**: `/Users/ricardocarvalho/DeveloperFolder/RAGLite/raglite/forecasting/hybrid.py`

Extended flat growth detection to include energy, price, and utilization metrics:
```python
# Before
cost_metrics_flat_growth = ["variable_cost", "variable cost"]

# After
cost_metrics_flat_growth = [
    "variable_cost", "variable cost",
    "electricity_cost", "electrical energy",
    "thermal_cost", "thermal energy",
    "avg_selling_price", "sales price em - cement", "sales price im",
    "capacity_utilization", "frequency ratio",
]
```

## Validation Results

### Current State (After Changes)

| Variable | Target MAPE | Actual MAPE | Status | Data Points | Value Range |
|----------|-------------|-------------|--------|-------------|-------------|
| **Variable Cost** | <8.5% | **8.04%** | **PASS** | 24 | -281 to -154 |
| Electricity Cost | <8.0% | 650.81% | FAIL | 29 | -22,128 to -189 |
| Thermal Energy Cost | <10.0% | 275.68% | FAIL | 29 | -17,801 to -326 |
| Average Selling Price | <6.0% | 25.99% | FAIL | 29 | 1,773 to 3,570 |
| Capacity Utilization | <10.0% | 131.82% | FAIL | 7 | 54 to 425 |

### Quality Gate
- **Result**: FAILED
- **Requirement**: 10/12 variables passing
- **Actual**: 1/12 variables passing (8.3%)
- **Variable Cost**: 8.04% (target: <8.5%) ✓

## Root Cause Analysis

### Why Variable Cost Passes

1. **Moderate data points**: 24 points (vs 7-29 for others)
2. **Stable range**: Values vary 2x (-281 to -154)
3. **No extreme outliers**: All values within expected range
4. **Consistent negative values**: No sign changes

### Why Other Variables Fail

#### 1. Electricity Cost (650.81% MAPE)
- **Extreme outliers**: -22,128 (min) vs -189 (max)
- **Range variation**: 117x difference
- **Data quality issue**: Likely incorrect extraction or unit mismatch
- **Negative values**: Suggests cost representation issue

#### 2. Thermal Energy Cost (275.68% MAPE)
- **Extreme outliers**: -17,801 (min) vs -326 (max)
- **Range variation**: 55x difference
- **Data quality issue**: Similar to electricity cost
- **Negative values**: Inconsistent with typical cost data

#### 3. Average Selling Price (25.99% MAPE)
- **Positive values**: 1,773 to 3,570 (expected for prices)
- **Moderate variation**: 2x range (reasonable)
- **MAPE slightly high**: 25.99% vs 6.0% target
- **Possible issue**: Insufficient data or seasonal patterns

#### 4. Capacity Utilization (131.82% MAPE)
- **Insufficient data**: Only 7 points (barely above min of 6)
- **High variation**: 54 to 425 (7.9x range)
- **Data quality issue**: Utilization >100% suggests percentage vs ratio confusion
- **Holdout validation**: 4-point holdout on 7 points leaves only 3 for training

## Hypotheses

### Hypothesis 1: Data Extraction Issues
**Evidence**:
- Electricity/Thermal costs have extreme negative outliers (-22k, -17k)
- These outliers suggest unit mismatches (e.g., EUR/ton vs EUR total)
- Capacity utilization >100% suggests percentage encoding issues

**Recommendation**: Audit Qdrant extraction for these metrics

### Hypothesis 2: Insufficient Training Data
**Evidence**:
- Capacity Utilization: 7 points total, 3 for training after 4-point holdout
- Prophet requires ≥10 points for reliable forecasts
- Frequency Ratio (same metric) has 102 raw points but only 7 after aggregation

**Recommendation**: Reduce holdout size for small datasets (2 points instead of 4)

### Hypothesis 3: Model Configuration Still Suboptimal
**Evidence**:
- Average Selling Price has clean data but 25.99% MAPE (vs 6% target)
- Flat growth + no regressors might not be the right pattern for all metrics
- Price metrics might need different configuration than cost metrics

**Recommendation**: Test alternative configurations for price metrics

## Recommendations

### Priority 1: Data Quality Fixes (Blocking)

1. **Audit Electrical Energy extraction**
   - Investigate -22,128 outlier
   - Verify unit consistency (EUR/ton vs EUR total)
   - Check entity filtering (Portugal vs Spain/Morocco)

2. **Audit Thermal Energy extraction**
   - Investigate -17,801 outlier
   - Same unit consistency checks as electricity

3. **Fix Capacity Utilization aggregation**
   - 102 raw points → 7 aggregated (issue in aggregation logic)
   - Verify percentage vs ratio representation
   - Consider using Frequency Ratio directly (no alias mapping)

### Priority 2: Validation Methodology (Quick Win)

4. **Adaptive holdout size**
   - Current: Fixed 4-point holdout
   - Proposed: `min(4, len(data) * 0.20)` (20% of data, capped at 4)
   - For 7-point series: 1-2 point holdout instead of 4
   - For 24-point series: Keep 4-point holdout

### Priority 3: Model Refinement (Experimental)

5. **Test variable-specific configurations**
   - Cost metrics (Variable, Electricity, Thermal): `growth='flat'`, no seasonality, no regressors ✓
   - Price metrics (Avg Selling Price): Test `growth='linear'` with inflation regressor
   - Utilization metrics: Test `growth='logistic'` with cap=100%

6. **Outlier detection and handling**
   - Flag values >3 standard deviations from mean
   - Option to exclude outliers during training
   - Re-include for MAPE calculation (test full robustness)

## Next Steps

### Immediate Actions (Today)

1. ✅ Applied Variable Cost pattern to 4 additional variables
2. ⏭️ Document data quality issues for triage
3. ⏭️ Create data quality audit script for energy/utilization metrics

### Short-Term (This Week)

4. Fix data extraction for Electricity/Thermal costs
5. Fix Capacity Utilization aggregation
6. Implement adaptive holdout sizing
7. Re-run validation after data quality fixes

### Medium-Term (Next Week)

8. Test variable-specific model configurations
9. Implement outlier detection and handling
10. Final validation run for quality gate

## Success Criteria

**Story 6.23 Quality Gate**:
- ≥10/12 variables passing their MAPE targets
- Variable Cost MAPE ≤8.5% ✓

**Current Progress**:
- 1/12 variables passing (need 9 more)
- Blocked by data quality issues in 3 variables
- Methodology issues in 1 variable (Capacity Utilization)

## Lessons Learned

1. **Sparse data pattern works**: Variable Cost proves flat growth + no regressors can achieve <8.5% MAPE
2. **Data quality is critical**: Extreme outliers (117x range) make forecasting impossible
3. **One size doesn't fit all**: Same pattern doesn't work for all variable types (cost vs price vs utilization)
4. **Training data minimums matter**: 7 points with 4-point holdout leaves insufficient training data
5. **Validation methodology matters**: Fixed holdout size doesn't scale to varying dataset sizes

## References

- **Story 6.23**: Variable Cost MAPE Final Validation
- **Story 6.20**: Regressor Config for Cement Industry
- **Baseline Results**: 1/12 passing before changes
- **Target**: 10/12 passing for quality gate
