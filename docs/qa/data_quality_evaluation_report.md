# Data Quality Evaluation Report - 12 Forecasting Variables

**Generated:** 2026-01-28
**Audit Runtime:** 11.6s
**Variables Evaluated:** 12

---

## Executive Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Variables READY | 0/12 | ≥8/12 | ❌ CRITICAL |
| Variables CRITICAL | 9 | 0 | ❌ |
| Variables NEEDS_WORK | 3 | - | ⚠️ |
| Overall Pass Rate | 50.0% | >70% | ❌ |
| Total Checks Passed | 36 | - | - |
| Total Checks Warned | 13 | - | - |
| Total Checks Failed | 23 | - | - |

---

## Variable Status Classification

### CRITICAL (Blocks Forecasting) - 9 Variables

| Variable | Primary Issues | Severity |
|----------|---------------|----------|
| **headcount** | 6.5x entity contamination, 20.3% outliers, 48.7 month gaps | P0 |
| **revenue** | 33.3% outliers, 70.9% unparseable dates, value range issues | P0 |
| **variable_cost** | 20.3% outliers, 38.3% unparseable dates, value range | P0 |
| **other_costs** | 61.9 month gaps, 10.4% outliers | P0 |
| **thermal_cost** | 27.8% outliers, 33.3% unparseable dates | P1 |
| **fixed_costs** | Sign convention issue, 33.2% unparseable dates | P1 |
| **capacity_utilization** | Values >150%, 29.6% unparseable dates | P1 |
| **ebitda** | 1.8x entity contamination, 93.6% unparseable dates | P1 |
| **capex** | 91.7% unparseable dates, low frequency | P1 |

### NEEDS_WORK (Minor Issues) - 3 Variables

| Variable | Issues | Status |
|----------|--------|--------|
| **avg_selling_price** | Minor entity leakage (1.2x) | Close to READY |
| **electricity_cost** | Minor entity leakage (1.3x) | Close to READY |
| **sales_volume** | Minor entity leakage (1.2x) | Close to READY |

### READY - 0 Variables

No variables currently pass all quality gates.

---

## Issue Analysis by Category

### 1. Time Index Integrity (Most Critical)

Almost all variables have significant date parsing issues:

| Variable | Unparseable % | Root Cause |
|----------|--------------|------------|
| headcount | 97.3% | Period format inconsistency |
| ebitda | 93.6% | Period format inconsistency |
| capex | 91.7% | Period format inconsistency |
| revenue | 70.9% | Period format inconsistency |
| variable_cost | 38.3% | Period format inconsistency |
| thermal_cost | 33.3% | Period format inconsistency |
| fixed_costs | 33.2% | Period format inconsistency |
| other_costs | 33.3% | Period format inconsistency |
| capacity_utilization | 29.6% | Period format inconsistency |

**Root Cause:** The audit uses `%b-%y` format (e.g., "Jan-25") but the database contains various formats including year-only, quarters, and date strings.

**Recommended Fix:** Implement multi-format period parsing in the data quality orchestrator.

### 2. Entity Contamination

| Variable | Ratio | Status | Sample Contaminated Entities |
|----------|-------|--------|------------------------------|
| headcount | 6.5x | FAIL | PORTUGAL*, Portugal Aggregates, Portugal Bags |
| ebitda | 1.8x | FAIL | Angola Cement + Group Structure |
| fixed_costs | 1.4x | WARN | - |
| thermal_cost | 1.4x | WARN | - |
| other_costs | 1.4x | WARN | - |
| electricity_cost | 1.3x | WARN | - |
| avg_selling_price | 1.2x | WARN | - |
| variable_cost | 1.2x | WARN | - |
| sales_volume | 1.2x | WARN | - |

**Root Cause:** ILIKE patterns matching unintended rows (e.g., '%portugal%' matches "Portugal Aggregates").

**Recommended Fix:**
- Switch to EXACT match mode using `entity_normalized` column
- Update entity matching to use normalized canonical entities

### 3. Outlier Detection

| Variable | Outlier % | Threshold | Status |
|----------|-----------|-----------|--------|
| revenue | 33.3% | 10% | FAIL |
| thermal_cost | 27.8% | 10% | FAIL |
| variable_cost | 20.3% | 10% | FAIL |
| headcount | 20.3% | 10% | FAIL |
| other_costs | 10.4% | 10% | FAIL |
| capacity_utilization | 6.4% | 10% | WARN |
| capex | 2.1% | 10% | WARN |
| fixed_costs | 1.9% | 10% | WARN |

**Root Cause:**
- Revenue: Scale mixing (M EUR vs kEUR vs EUR)
- Cost variables: Sign convention inconsistencies
- Headcount: Negative values indicating variance/delta rather than absolutes

### 4. Value Range Violations

| Variable | Issue | Sample Values |
|----------|-------|---------------|
| headcount | Negative values | -162, -794, -86 |
| capacity_utilization | Values >150% | 227.7%, 487.4%, 591.9% |
| variable_cost | Outside -10k to 10k | -12244, -160032, -32421 |
| revenue | Below -100k | -193534, -499870, -214641 |
| other_costs | Below -200 | -304, -667 |
| fixed_costs | Non-negative | 58 |

**Root Cause:**
- Negative values often represent year-over-year changes
- Capacity utilization >100% may be valid for multi-shift operations
- Revenue negatives likely represent adjustments/corrections

### 5. Missing Data Gaps

| Variable | Max Gap (months) | Threshold | Status |
|----------|-----------------|-----------|--------|
| other_costs | 61.9 | 13 | FAIL |
| headcount | 48.7 | 13 | FAIL |
| variable_cost | 26.4 | 13 | PASS |
| capex | 12.2 | 13 | PASS |

---

## Priority Remediation Plan

### P0 - Must Fix This Sprint

1. **Fix Period Parsing (All Variables)**
   - Implement multi-format date parser (`%b-%y`, `%Y`, `Q%q-%Y`, etc.)
   - Expected impact: Reduce unparseable dates from 30-97% to <5%

2. **Fix Entity Matching (headcount, ebitda)**
   - Switch from ILIKE to EXACT match using entity_normalized
   - Update variable_configs.py with correct match mode

3. **Fix Sign Convention (headcount, fixed_costs)**
   - Validate config expectations match actual data signs
   - Update allow_negative settings in variable_configs.py

### P1 - Fix Next Sprint

1. **Review Outlier Thresholds**
   - Revenue: Likely scale mixing issue, not true outliers
   - Cost variables: May need separate configs for absolute vs delta values

2. **Fix Capacity Utilization Range**
   - Update max_value from 150 to 600 (multi-shift valid)
   - Or add check for expected vs actual scale

3. **Address Missing Data Gaps**
   - other_costs and headcount have >4 year gaps
   - May indicate data extraction pattern issues

---

## Configuration Updates Required

### `variable_configs.py` Changes

```python
# headcount - fix entity match mode
"headcount": VariableQualityConfig(
    entity=EntityConfig(
        match_mode=EntityMatchMode.EXACT,  # Changed from ILIKE
        required_entity="portugal",
        contamination_check=True,
    ),
    # ... rest of config
)

# ebitda - fix entity match mode
"ebitda": VariableQualityConfig(
    entity=EntityConfig(
        match_mode=EntityMatchMode.EXACT,  # Changed from ILIKE
        required_entity="GROUP",
        contamination_check=True,
    ),
    # ... rest of config
)

# capacity_utilization - fix value range
"capacity_utilization": VariableQualityConfig(
    value_range=ValueRangeConfig(
        min_value=0,
        max_value=600,  # Changed from 150
    ),
    # ... rest of config
)
```

---

## Success Criteria

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Variables READY | 0/12 | ≥8/12 | 8 variables |
| Pass Rate | 50.0% | >70% | 20pp |
| Entity Contamination FAILs | 2 | 0 | 2 fixes |
| Outlier FAILs | 5 | 0 | 5 reviews |
| Unparseable Dates | 30-97% | <5% | Major fix |

---

## Next Steps

1. **Immediate:** Fix nosec SQL comment issues (DONE - fixed in this session)
2. **This Sprint:** Fix period parsing in orchestrator
3. **This Sprint:** Update entity match modes in variable_configs.py
4. **Next Sprint:** Review outlier detection thresholds
5. **Next Sprint:** Address missing data gap issues

---

## Files Modified During This Evaluation

| File | Change |
|------|--------|
| `raglite/forecasting/data_quality/checks/entity_checks_helpers.py` | Fixed nosec comment placement in SQL queries |
| `raglite/forecasting/data_quality/orchestrator.py` | Fixed nosec comment placement in SQL query |

---

## Appendix: Full Check Results

See exported reports:
- JSON: `docs/qa/data_quality_audit_20260128_092244.json`
- Markdown: `docs/qa/data_quality_audit_20260128_092244.md`
