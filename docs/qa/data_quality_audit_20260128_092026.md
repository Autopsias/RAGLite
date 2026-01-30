# Data Quality Audit Results

**Timestamp:** 2026-01-28T09:20:26.369077
**Runtime:** 6.7s

## Summary

- Variables audited: 12
- Total checks: 96
- Pass rate: 0.0%

| Status | Count |
|--------|-------|
| PASS | 0 |
| WARN | 0 |
| FAIL | 20 |
| SKIP | 76 |

## Variable Summary

| Variable | Status | Pass | Warn | Fail |
|----------|--------|------|------|------|
| avg_selling_price | ✗ FAIL | 0 | 0 | 2 |
| capex | ✗ FAIL | 0 | 0 | 2 |
| ebitda | ✗ FAIL | 0 | 0 | 2 |
| electricity_cost | ✗ FAIL | 0 | 0 | 2 |
| fixed_costs | ✗ FAIL | 0 | 0 | 2 |
| headcount | ✗ FAIL | 0 | 0 | 2 |
| other_costs | ✗ FAIL | 0 | 0 | 2 |
| sales_volume | ✗ FAIL | 0 | 0 | 2 |
| thermal_cost | ✗ FAIL | 0 | 0 | 2 |
| variable_cost | ✗ FAIL | 0 | 0 | 2 |
| capacity_utilization | ✓ PASS | 0 | 0 | 0 |
| revenue | ✓ PASS | 0 | 0 | 0 |

## Issues Requiring Attention

### ebitda

- ✗ **entity_contamination**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^

- ✗ **entity_coverage**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^


### variable_cost

- ✗ **entity_contamination**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^

- ✗ **entity_coverage**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^


### sales_volume

- ✗ **entity_contamination**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^

- ✗ **entity_coverage**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^


### electricity_cost

- ✗ **entity_contamination**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^

- ✗ **entity_coverage**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^


### thermal_cost

- ✗ **entity_contamination**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^

- ✗ **entity_coverage**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^


### avg_selling_price

- ✗ **entity_contamination**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^

- ✗ **entity_coverage**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^


### capex

- ✗ **entity_contamination**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^

- ✗ **entity_coverage**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^


### fixed_costs

- ✗ **entity_contamination**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^

- ✗ **entity_coverage**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^


### headcount

- ✗ **entity_contamination**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^

- ✗ **entity_coverage**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^


### other_costs

- ✗ **entity_contamination**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^

- ✗ **entity_coverage**: Query error: syntax error at or near "#"
LINE 1:   # nosec
          ^
