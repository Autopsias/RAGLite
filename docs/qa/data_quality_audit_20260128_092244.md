# Data Quality Audit Results

**Timestamp:** 2026-01-28T09:22:44.024174
**Runtime:** 11.6s

## Summary

- Variables audited: 12
- Total checks: 96
- Pass rate: 50.0%

| Status | Count |
|--------|-------|
| PASS | 36 |
| WARN | 13 |
| FAIL | 23 |
| SKIP | 24 |

## Variable Summary

| Variable | Status | Pass | Warn | Fail |
|----------|--------|------|------|------|
| capacity_utilization | ✗ FAIL | 2 | 1 | 2 |
| capex | ✗ FAIL | 5 | 2 | 1 |
| ebitda | ✗ FAIL | 5 | 2 | 1 |
| fixed_costs | ✗ FAIL | 4 | 2 | 2 |
| headcount | ✗ FAIL | 2 | 0 | 5 |
| other_costs | ✗ FAIL | 3 | 1 | 4 |
| revenue | ✗ FAIL | 3 | 0 | 3 |
| thermal_cost | ✗ FAIL | 5 | 1 | 2 |
| variable_cost | ✗ FAIL | 4 | 1 | 3 |
| avg_selling_price | ! WARN | 1 | 1 | 0 |
| electricity_cost | ! WARN | 1 | 1 | 0 |
| sales_volume | ! WARN | 1 | 1 | 0 |

## Issues Requiring Attention

### ebitda

- ✗ **entity_contamination**: Leakage detected: fuzzy=626, exact=342 (1.8x)
  - Sample data:
    - `{'entity': 'Angola Cement + Group Structure'}`
    - `{'entity': 'Angola + Group Structure'}`
    - `{'entity': 'EBITDA Angola + Group Structure'}`
- ! **effective_frequency**: Low frequency: 1.5 points/year (expected monthly)
- ! **time_index_integrity**: 44 unparseable dates (93.6%)

### revenue

- ✗ **value_range**: 12 values (0.1%) below min -100000
  - Sample data:
    - `{'value': Decimal('-193534.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-499870.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-214641.00'), 'issue': 'below_min'}`
- ✗ **robust_outliers**: 4331 outliers (33.3%) detected
  - Sample data:
    - `{'value': 597.0, 'z_score': 14.47}`
    - `{'value': 596.0, 'z_score': 14.45}`
    - `{'value': 1399.0, 'z_score': 34.72}`
- ✗ **time_index_integrity**: 49 duplicate dates; 11 out-of-order transitions; 9614 unparseable dates (70.9%)

### variable_cost

- ! **entity_contamination**: Minor leakage: fuzzy=656, exact=555 (1.2x)
- ✗ **value_range**: 9 values (1.4%) below min -10000; 38 values (5.8%) above max 10000
  - Sample data:
    - `{'value': Decimal('-12244.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-160032.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-32421.00'), 'issue': 'below_min'}`
- ✗ **robust_outliers**: 133 outliers (20.3%) detected
  - Sample data:
    - `{'value': 141.3, 'z_score': 5.88}`
    - `{'value': 280.2, 'z_score': 11.29}`
    - `{'value': 268.4, 'z_score': 10.83}`
- ✗ **time_index_integrity**: 39 duplicate dates; 11 out-of-order transitions; 251 unparseable dates (38.3%)

### sales_volume

- ! **entity_contamination**: Minor leakage: fuzzy=714, exact=588 (1.2x)

### electricity_cost

- ! **entity_contamination**: Minor leakage: fuzzy=212, exact=164 (1.3x)

### thermal_cost

- ! **entity_contamination**: Minor leakage: fuzzy=180, exact=132 (1.4x)
- ✗ **robust_outliers**: 50 outliers (27.8%) detected
  - Sample data:
    - `{'value': -8.8, 'z_score': -4.55}`
    - `{'value': -8.8, 'z_score': -4.55}`
    - `{'value': -10.1, 'z_score': -6.75}`
- ✗ **time_index_integrity**: 24 duplicate dates; 11 out-of-order transitions; 60 unparseable dates (33.3%)

### avg_selling_price

- ! **entity_contamination**: Minor leakage: fuzzy=916, exact=772 (1.2x)

### capacity_utilization

- ✗ **value_range**: 32 values (0.6%) above max 150
  - Sample data:
    - `{'value': Decimal('227.74'), 'issue': 'above_max'}`
    - `{'value': Decimal('487.41'), 'issue': 'above_max'}`
    - `{'value': Decimal('591.93'), 'issue': 'above_max'}`
- ! **robust_outliers**: 331 outliers (6.4%) detected
  - Sample data:
    - `{'value': 37.42, 'z_score': 5.19}`
    - `{'value': 29.91, 'z_score': 3.98}`
    - `{'value': 29.91, 'z_score': 3.98}`
- ✗ **time_index_integrity**: 78 duplicate dates; 11 out-of-order transitions; 2914 unparseable dates (29.6%)

### capex

- ! **robust_outliers**: 1 outliers (2.1%) detected
  - Sample data:
    - `{'value': 926.0, 'z_score': 59.91}`
- ! **effective_frequency**: Low frequency: 2.0 points/year (expected monthly)
- ✗ **time_index_integrity**: 2 duplicate dates; 44 unparseable dates (91.7%)

### fixed_costs

- ! **entity_contamination**: Minor leakage: fuzzy=361, exact=265 (1.4x)
- ✗ **value_range**: 1 values (0.3%) non-negative
  - Sample data:
    - `{'value': Decimal('58.00'), 'issue': 'non_negative'}`
- ! **robust_outliers**: 7 outliers (1.9%) detected
  - Sample data:
    - `{'value': -63.4, 'z_score': -4.45}`
    - `{'value': -63.4, 'z_score': -4.45}`
    - `{'value': -85.5, 'z_score': -6.25}`
- ✗ **time_index_integrity**: 24 duplicate dates; 11 out-of-order transitions; 120 unparseable dates (33.2%)

### headcount

- ✗ **entity_contamination**: Leakage detected: fuzzy=2714, exact=419 (6.5x)
  - Sample data:
    - `{'entity': 'PORTUGAL*'}`
    - `{'entity': 'Portugal Aggregates'}`
    - `{'entity': 'Portugal Bags'}`
- ✗ **value_range**: 15 values (0.6%) below min 0; 17 values (0.7%) non-positive
  - Sample data:
    - `{'value': Decimal('-162.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-794.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-86.00'), 'issue': 'below_min'}`
- ✗ **robust_outliers**: 501 outliers (20.3%) detected
  - Sample data:
    - `{'value': 230.0, 'z_score': 3.97}`
    - `{'value': 861.0, 'z_score': 16.86}`
    - `{'value': 230.0, 'z_score': 3.97}`
- ✗ **time_index_integrity**: 13 duplicate dates; 9 out-of-order transitions; 2641 unparseable dates (97.3%)
- ✗ **missing_data_pattern**: Max gap: 48.7 months (threshold: 13)

### other_costs

- ! **entity_contamination**: Minor leakage: fuzzy=183, exact=135 (1.4x)
- ✗ **value_range**: 2 values (1.1%) below min -200
  - Sample data:
    - `{'value': Decimal('-304.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-667.00'), 'issue': 'below_min'}`
- ✗ **robust_outliers**: 19 outliers (10.4%) detected
  - Sample data:
    - `{'value': 20.2, 'z_score': 4.23}`
    - `{'value': 20.2, 'z_score': 4.23}`
    - `{'value': 81.7, 'z_score': 20.18}`
- ✗ **time_index_integrity**: 24 duplicate dates; 11 out-of-order transitions; 61 unparseable dates (33.3%)
- ✗ **missing_data_pattern**: Max gap: 61.9 months (threshold: 13)
