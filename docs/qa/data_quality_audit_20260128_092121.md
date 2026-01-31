# Data Quality Audit Results

**Timestamp:** 2026-01-28T09:21:21.526200
**Runtime:** 10.6s

## Summary

- Variables audited: 12
- Total checks: 96
- Pass rate: 55.0%

| Status | Count |
|--------|-------|
| PASS | 11 |
| WARN | 7 |
| FAIL | 2 |
| SKIP | 76 |

## Variable Summary

| Variable | Status | Pass | Warn | Fail |
|----------|--------|------|------|------|
| ebitda | ✗ FAIL | 1 | 0 | 1 |
| headcount | ✗ FAIL | 1 | 0 | 1 |
| avg_selling_price | ! WARN | 1 | 1 | 0 |
| capacity_utilization | ✓ PASS | 0 | 0 | 0 |
| capex | ✓ PASS | 2 | 0 | 0 |
| electricity_cost | ! WARN | 1 | 1 | 0 |
| fixed_costs | ! WARN | 1 | 1 | 0 |
| other_costs | ! WARN | 1 | 1 | 0 |
| revenue | ✓ PASS | 0 | 0 | 0 |
| sales_volume | ! WARN | 1 | 1 | 0 |
| thermal_cost | ! WARN | 1 | 1 | 0 |
| variable_cost | ! WARN | 1 | 1 | 0 |

## Issues Requiring Attention

### ebitda

- ✗ **entity_contamination**: Leakage detected: fuzzy=626, exact=342 (1.8x)
  - Sample data:
    - `{'entity': 'Angola Cement + Group Structure'}`
    - `{'entity': 'Angola + Group Structure'}`
    - `{'entity': 'EBITDA Angola + Group Structure'}`

### variable_cost

- ! **entity_contamination**: Minor leakage: fuzzy=656, exact=555 (1.2x)

### sales_volume

- ! **entity_contamination**: Minor leakage: fuzzy=714, exact=588 (1.2x)

### electricity_cost

- ! **entity_contamination**: Minor leakage: fuzzy=212, exact=164 (1.3x)

### thermal_cost

- ! **entity_contamination**: Minor leakage: fuzzy=180, exact=132 (1.4x)

### avg_selling_price

- ! **entity_contamination**: Minor leakage: fuzzy=916, exact=772 (1.2x)

### fixed_costs

- ! **entity_contamination**: Minor leakage: fuzzy=361, exact=265 (1.4x)

### headcount

- ✗ **entity_contamination**: Leakage detected: fuzzy=2714, exact=419 (6.5x)
  - Sample data:
    - `{'entity': 'PORTUGAL*'}`
    - `{'entity': 'Portugal Aggregates'}`
    - `{'entity': 'Portugal Bags'}`

### other_costs

- ! **entity_contamination**: Minor leakage: fuzzy=183, exact=135 (1.4x)
