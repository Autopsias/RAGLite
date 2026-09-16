# EBITDA Forecast Data Quality Gaps Analysis

**Generated:** 2026-02-03
**Context:** EBITDA forecast improvements revealed data quality issues not fully resolved by Epic 9

---

## Summary

During implementation of EBITDA forecast improvements (lagged correlations, seasonal future regressors, multiplicative seasonality), several data quality issues were discovered that prevent reliable EBITDA forecasting despite Epic 9's 100% classification accuracy claim.

---

## Issues Found During Forecasting

### Issue 1: Unit Mixing Within Same Metric ❌ NOT RESOLVED

**Symptom:** Forecasting rejected data with "Unit mixing too severe"

**Evidence:**
```sql
-- Same metric, different units
EBITDA IFRS | Brazil | YTD Mar-23 | -17.00 | 1000 BRL
EBITDA IFRS | GROUP  | YTD Sep-25 | 150.50 | M EUR
```

**Epic 9 Status:** Classification pipeline stores `unit` but does NOT:
- Normalize units to common base (e.g., all to EUR)
- Flag mixed-unit rows for exclusion
- Convert BRL → EUR using exchange rates

**Gap:** `value_type` classification exists but unit normalization is missing.

---

### Issue 2: Entity Inconsistency for "GROUP" ⚠️ PARTIALLY RESOLVED

**Symptom:** Multiple entity names mapping to same logical entity

**Evidence:**
```
entity values referring to GROUP:
- "GROUP"
- "SECIL Group"
- "Group"
- "GROUP PORTUGAL"
- "Portugal Group"
```

**Epic 9 Status:**
- ✅ `entity_normalized` column exists
- ✅ `entity_level` classification works (consolidated, geographic, etc.)
- ❌ Forecasting extraction NOT consistently using `entity_normalized`

**Gap:** Extraction queries use `entity` column directly, not `entity_normalized`.

---

### Issue 3: Outliers Not Flagged ❌ NOT RESOLVED

**Symptom:** Extreme outliers distort forecasts

**Evidence:**
```
YTD B Nov-24 | SECIL Group | 5466.00 M EUR  (outlier - likely typo or wrong unit)
YTD Nov-24   | GROUP       | 150.06 M EUR  (normal range)
```

**Epic 9 Status:** No outlier detection/flagging during classification.

**Gap:** Need `is_outlier` flag or confidence score for extreme values.

---

### Issue 4: Budget vs Actual Mixing ⚠️ PARTIALLY RESOLVED

**Symptom:** Budget data (B prefix) mixed with actual data

**Evidence:**
```
period values showing budget/actual mixing:
- "B Apr-24" (budget)
- "Apr-24" (actual)
- "YTD B Dec-22" (YTD budget)
- "YTD Dec-22" (YTD actual)
```

**Epic 9 Status:**
- ✅ `value_type` classification correctly identifies: actual, budget, variance, forecast
- ✅ `period_type` classification identifies: monthly_actual, ytd_actual, budget, ytd_budget
- ✅ Forecasting query filters: `value_type = 'actual'`

**Why Still Failing:**
The classification reports 711 `budget` and 326 `ytd_budget` rows for EBITDA metrics.
But 558 rows have `period_type = 'unknown'` which are NOT filtered out cleanly.

**Gap:** `unknown` classifications need manual review/fallback handling.

---

### Issue 5: Missing Period Information ⚠️ PARTIALLY RESOLVED

**Symptom:** Many rows have `period = NULL` or unparseable periods

**Evidence:**
```sql
-- EBITDA rows with period issues
EBITDA | Secil Group | N/A | N/A | 11.01 | M EUR
EBITDA | Secil Group | N/A | N/A | N/A   | M EUR
```

**Epic 9 Status:**
- ✅ `period_type` column populated
- 558 rows classified as `unknown` for EBITDA metrics (10% of EBITDA data)

**Gap:** `unknown` period_type rows need either:
1. LLM-based period inference from document context
2. Exclusion from forecasting queries

---

### Issue 6: YTD vs Monthly Aggregation Conflicts ⚠️ PARTIALLY RESOLVED

**Symptom:** Same time period has both YTD and monthly values

**Evidence:**
```
YTD Sep-24 | GROUP | 118.65 M EUR (cumulative Jan-Sep)
Sep-24     | GROUP |  23.81 M EUR (single month)
```

**Epic 9 Status:**
- ✅ `period_type` distinguishes `ytd_actual` vs `monthly_actual`
- ✅ Forecasting query uses period_type for filtering

**Why Still Failing:**
YTD normalization in extraction pipeline converts YTD → monthly by differencing,
but this fails when months are missing (gaps in data).

**Gap:** YTD-to-monthly conversion needs gap-aware interpolation.

---

## Comparison with Epic 9 Objectives

| Epic 9 Objective | Status | Gap |
|------------------|--------|-----|
| Period type classification (95%+) | ✅ 100% | 10% `unknown` for EBITDA |
| Value type classification (90%+) | ✅ 100% | Not filtering all budget data |
| Entity level classification (90%+) | ✅ 100% | Not used in extraction queries |
| Direct queries by period_type | ✅ Implemented | `unknown` values pass through |
| Code simplification | ✅ Done | Still complex due to edge cases |

---

## Recommended Fixes

### Priority 1: Entity Normalization in Queries (Quick Fix)

**Change:** Update extraction to use `entity_normalized` instead of `entity`

```sql
-- Current (problematic)
WHERE entity ILIKE '%GROUP%'

-- Fixed
WHERE entity_normalized = 'Group'
```

### Priority 2: Exclude Unknown Classifications

**Change:** Strengthen filtering to exclude `unknown` values

```sql
-- Current
AND (period_type IS NULL OR period_type IN ('ytd_actual', 'monthly_actual'))
AND period_type != 'unknown'

-- Fixed (explicit exclusion)
AND period_type IN ('ytd_actual', 'monthly_actual')
AND value_type = 'actual'
```

### Priority 3: Unit Normalization (Medium Effort)

**Change:** Add unit normalization during ingestion or extraction:
1. Convert all values to base unit (EUR)
2. Store conversion rate used
3. Flag rows where conversion is uncertain

### Priority 4: Outlier Detection (Medium Effort)

**Change:** Add statistical outlier detection during classification:
1. Calculate z-score or IQR for each metric
2. Flag outliers with `is_potential_outlier` column
3. Exclude flagged rows from forecasting

### Priority 5: Unknown Classification Review (Manual)

**Change:** Review 558 EBITDA rows with `period_type = 'unknown'`:
1. Manually classify or mark as unusable
2. Improve period classifier patterns for edge cases

---

## Database Statistics

```
Total EBITDA rows: 5,637
- period_type breakdown:
  - monthly_actual: 2,790 (49%)
  - ytd_actual: 1,252 (22%)
  - budget: 711 (13%)
  - unknown: 558 (10%) ← Problem area
  - ytd_budget: 326 (6%)

- value_type breakdown:
  - actual: 4,201 (75%)
  - budget: 1,095 (19%)
  - unknown: 290 (5%) ← Problem area
  - variance: 43 (1%)
  - forecast: 8 (<1%)

- entity_level breakdown:
  - unknown: 1,983 (35%) ← Large problem area
  - geographic: 1,411 (25%)
  - company_only: 870 (15%)
  - segment: 795 (14%)
  - consolidated: 578 (10%)
```

---

## Conclusion

Epic 9 successfully implemented the classification infrastructure, but the **forecasting extraction pipeline** is not fully utilizing these classifications. Additionally, **10-35% of EBITDA data** has `unknown` classifications that pass through filters and corrupt forecasts.

The EBITDA forecast improvements (lagged correlations, seasonal strategy, etc.) are working correctly - the issue is **data quality at the source**, not the forecasting algorithms.
