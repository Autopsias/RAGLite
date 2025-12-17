# Data Quality Audit Results

**Timestamp:** 2025-12-16T14:34:53.448913
**Runtime:** 5.1s

## Summary

- Variables audited: 20
- Total checks: 160
- Pass rate: 36.2%

| Status | Count |
|--------|-------|
| PASS | 25 |
| WARN | 12 |
| FAIL | 32 |
| SKIP | 91 |

## Variable Summary

| Variable | Status | Pass | Warn | Fail |
|----------|--------|------|------|------|
| avg_selling_price | ✗ FAIL | 2 | 2 | 3 |
| capacity_utilization | ✗ FAIL | 1 | 1 | 3 |
| ebitda | ✗ FAIL | 2 | 3 | 3 |
| electricity_cost | ✗ FAIL | 2 | 1 | 4 |
| petcoke_price | ✗ FAIL | 3 | 1 | 1 |
| revenue | ✗ FAIL | 0 | 1 | 5 |
| sales_volume | ✗ FAIL | 1 | 1 | 4 |
| thermal_cost | ✗ FAIL | 3 | 1 | 3 |
| ttf_gas_price | ✗ FAIL | 4 | 0 | 1 |
| variable_cost | ✗ FAIL | 2 | 1 | 5 |
| building_permits | ✓ PASS | 0 | 0 | 0 |
| co2_eua_price | ✓ PASS | 5 | 0 | 0 |
| construction_confidence | ✓ PASS | 0 | 0 | 0 |
| construction_output | ✓ PASS | 0 | 0 | 0 |
| diesel | ✓ PASS | 0 | 0 | 0 |
| euribor_3m | ✓ PASS | 0 | 0 | 0 |
| eurostat_electricity | ✓ PASS | 0 | 0 | 0 |
| gdp_growth | ✓ PASS | 0 | 0 | 0 |
| industrial_production | ✓ PASS | 0 | 0 | 0 |
| inflation | ✓ PASS | 0 | 0 | 0 |

## Issues Requiring Attention

### avg_selling_price

- ✗ **value_range**: 16 values (2.1%) below min 50; 3 values (0.4%) above max 200; 2 values (0.3%) non-positive
  - Sample data:
    - `{'value': Decimal('44.40'), 'issue': 'below_min'}`
    - `{'value': Decimal('44.40'), 'issue': 'below_min'}`
    - `{'value': Decimal('41.00'), 'issue': 'below_min'}`
- ! **robust_outliers**: 5 outliers (0.6%) detected
  - Sample data:
    - `{'value': 0.0, 'z_score': -4.57}`
    - `{'value': 0.0, 'z_score': -4.57}`
    - `{'value': 526.4, 'z_score': 17.9}`
- ! **effective_frequency**: Year-end only data in years: [2021, 2022]
- ✗ **time_index_integrity**: 36 duplicate dates; 11 out-of-order transitions; 251 unparseable dates (32.5%)
- ✗ **missing_data_pattern**: Max gap: 12.2 months (threshold: 2)

### capacity_utilization

- ✗ **value_range**: 42 values (1.1%) above max 100; 670 values (17.2%) non-positive
  - Sample data:
    - `{'value': Decimal('487.41'), 'issue': 'above_max'}`
    - `{'value': Decimal('227.74'), 'issue': 'above_max'}`
    - `{'value': Decimal('114.28'), 'issue': 'above_max'}`
- ! **robust_outliers**: 252 outliers (6.5%) detected
  - Sample data:
    - `{'value': 37.42, 'z_score': 4.77}`
    - `{'value': 29.91, 'z_score': 3.65}`
    - `{'value': 29.91, 'z_score': 3.65}`
- ✗ **time_index_integrity**: 78 duplicate dates; 11 out-of-order transitions; 2174 unparseable dates (28.8%)
- ✗ **missing_data_pattern**: High missing rate: 48.3% (max 20.0%)

### ebitda

- ✗ **entity_contamination**: Leakage detected: fuzzy=618, exact=43 (14.4x)
  - Sample data:
    - `{'entity': 'Angola Cement + Group Structure'}`
    - `{'entity': 'Angola + Group Structure'}`
    - `{'entity': 'EBITDA Angola + Group Structure'}`
- ! **unit_consistency**: Possible scale issue: median=129.36, expected~15000.00 (0.0x)
- ✗ **robust_outliers**: 11 outliers (25.6%) detected
  - Sample data:
    - `{'value': 18857.0, 'z_score': 228.42}`
    - `{'value': 34112.0, 'z_score': 414.49}`
    - `{'value': 142495.0, 'z_score': 1736.45}`
- ! **effective_frequency**: Low frequency: 1.5 points/year (expected monthly)
- ! **time_index_integrity**: 40 unparseable dates (93.0%)
- ✗ **missing_data_pattern**: Max gap: 12.2 months (threshold: 2)

### electricity_cost

- ✗ **value_range**: 136 values (82.9%) below min 0; 15 values (9.1%) above max 100; 136 values (82.9%) non-positive
  - Sample data:
    - `{'value': Decimal('-8.50'), 'issue': 'below_min'}`
    - `{'value': Decimal('-9.90'), 'issue': 'below_min'}`
    - `{'value': Decimal('-9.90'), 'issue': 'below_min'}`
- ✗ **robust_outliers**: 31 outliers (18.9%) detected
  - Sample data:
    - `{'value': 24.6, 'z_score': 8.55}`
    - `{'value': 1531.8, 'z_score': 415.2}`
    - `{'value': 25.1, 'z_score': 8.69}`
- ! **effective_frequency**: Year-end only data in years: [2018, 2019]
- ✗ **time_index_integrity**: 24 duplicate dates; 11 out-of-order transitions; 56 unparseable dates (34.1%)
- ✗ **missing_data_pattern**: Max gap: 38.6 months (threshold: 2)

### petcoke_price

- ✗ **robust_outliers**: 217 outliers (17.2%) detected
  - Sample data:
    - `{'value': 233.60000610351562, 'z_score': 3.87}`
    - `{'value': 246.5, 'z_score': 4.3}`
    - `{'value': 274.0, 'z_score': 5.22}`
- ! **effective_frequency**: Year-end only data in years: [2020]

### revenue

- ✗ **value_range**: 698 values (6.7%) below min 0; 99 values (0.9%) above max 500000; 908 values (8.7%) non-positive
  - Sample data:
    - `{'value': Decimal('-391.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-360.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-9.71'), 'issue': 'below_min'}`
- ✗ **unit_consistency**: Scale mismatch: median=34.00, expected~30000.00 (0x off)
- ✗ **robust_outliers**: 3584 outliers (34.3%) detected
  - Sample data:
    - `{'value': 1399.0, 'z_score': 27.08}`
    - `{'value': 597.0, 'z_score': 11.17}`
    - `{'value': 596.0, 'z_score': 11.15}`
- ! **effective_frequency**: Year-end only data in years: [2016, 2017, 2018, 2019, 2020, 2021]
- ✗ **time_index_integrity**: 47 duplicate dates; 11 out-of-order transitions; 7144 unparseable dates (65.8%)
- ✗ **missing_data_pattern**: Max gap: 12.2 months (threshold: 2)

### sales_volume

- ✗ **value_range**: 8 values (0.5%) below min 0; 267 values (16.6%) above max 500; 8 values (0.5%) non-positive
  - Sample data:
    - `{'value': Decimal('-558.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-1.87'), 'issue': 'below_min'}`
    - `{'value': Decimal('-941.00'), 'issue': 'below_min'}`
- ✗ **robust_outliers**: 243 outliers (15.1%) detected
  - Sample data:
    - `{'value': 2339.0, 'z_score': 18.42}`
    - `{'value': 1099.0, 'z_score': 8.09}`
    - `{'value': 1181.0, 'z_score': 8.78}`
- ! **effective_frequency**: Year-end only data in years: [2017, 2018, 2019, 2021]
- ✗ **time_index_integrity**: 41 duplicate dates; 11 out-of-order transitions; 495 unparseable dates (30.8%)
- ✗ **missing_data_pattern**: Max gap: 24.4 months (threshold: 2)

### thermal_cost

- ✗ **value_range**: 132 values (100.0%) below min 0; 132 values (100.0%) non-positive
  - Sample data:
    - `{'value': Decimal('-10.10'), 'issue': 'below_min'}`
    - `{'value': Decimal('-10.10'), 'issue': 'below_min'}`
    - `{'value': Decimal('-8.80'), 'issue': 'below_min'}`
- ✗ **robust_outliers**: 34 outliers (25.8%) detected
  - Sample data:
    - `{'value': -10.1, 'z_score': -6.75}`
    - `{'value': -10.1, 'z_score': -6.75}`
    - `{'value': -8.8, 'z_score': -4.55}`
- ✗ **time_index_integrity**: 20 duplicate dates; 9 out-of-order transitions; 44 unparseable dates (33.3%)
- ! **missing_data_pattern**: Max gap: 3.1 months (threshold: 2)

### ttf_gas_price

- ✗ **robust_outliers**: 225 outliers (11.0%) detected
  - Sample data:
    - `{'value': 97.77400207519531, 'z_score': 3.73}`
    - `{'value': 93.625, 'z_score': 3.51}`
    - `{'value': 96.6520004272461, 'z_score': 3.67}`

### variable_cost

- ✗ **entity_contamination**: Leakage detected: fuzzy=560, exact=0 (560.0x)
  - Sample data:
    - `{'entity': 'Portugal'}`
    - `{'entity': 'Portugal Cement'}`
    - `{'entity': 'Portugal Ready Mix'}`
- ✗ **value_range**: 13 values (2.3%) below min -500; 268 values (47.9%) above max 0; 268 values (47.9%) non-negative
  - Sample data:
    - `{'value': Decimal('-8171.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-12244.00'), 'issue': 'below_min'}`
    - `{'value': Decimal('-160032.00'), 'issue': 'below_min'}`
- ✗ **robust_outliers**: 128 outliers (22.9%) detected
  - Sample data:
    - `{'value': 141.3, 'z_score': 4.59}`
    - `{'value': 280.2, 'z_score': 8.86}`
    - `{'value': 268.4, 'z_score': 8.5}`
- ! **effective_frequency**: Year-end only data in years: [2016, 2017, 2018, 2019]
- ✗ **time_index_integrity**: 37 duplicate dates; 11 out-of-order transitions; 219 unparseable dates (39.1%)
- ✗ **missing_data_pattern**: Max gap: 26.4 months (threshold: 3)
