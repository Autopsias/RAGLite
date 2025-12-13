# Quick Fix Summary: Variable Validation Failures

**Status:** 1/12 variables passing → Need to fix 11 variables
**Root Cause:** 2 critical bugs in Qdrant extraction logic
**Priority:** P0 (blocks quality gate)

---

## Issues Discovered

### Issue 1: Duplicate Dates (10 variables showing N/A)

**Problem:**
```python
# extract_metric_from_qdrant_chunks() extracts:
2025-01-01: 835518.00 - Jan-25 Turnover+Vat
2025-01-01: 826584.00 - Jan-24 Turnover+Vat  ← DUPLICATE! (should be 2024-01-01)
```

**Root Cause:** `parse_period_to_date("Jan-24", 2025)` ignores the "24" suffix and uses fixed year `2025`

**Fix:** Extract year from period suffix:
```python
# Before:
year = 2000 + int(year_str)  # Fixed year from parameter

# After:
match = re.match(r"^([A-Za-z]+)-(\d{2})$", period.strip())
year_suffix = int(match.group(2))
year = 2000 + year_suffix  # Extract from period label
```

**Files:** `/raglite/forecasting/timeseries_extract.py` line 1128

---

### Issue 2: EBITDA YTD Conversion (577% MAPE)

**Problem:** YTD→Monthly conversion doesn't detect year boundaries:
```python
# Data sequence: Mar-24 (YTD=39M), Apr-24 (YTD=51M), ... Dec-24 (YTD=155M), Jan-25 (YTD=23M)
# Current logic: Jan-25 monthly = 23M - 155M = -132M (WRONG!)
# Should be: Reset baseline at year boundary, Jan-25 monthly = 23M
```

**Fix:** Detect year gaps and reset baseline:
```python
if prev_date is not None:
    if p.date.year != prev_date.year:
        logger.info("Year boundary detected, resetting YTD baseline")
        prev_ytd = 0.0
        monthly_value = p.value
```

**Files:** `/raglite/forecasting/timeseries_extract.py` lines 418-440

---

## Quick Test Commands

```bash
# Test 1: Verify Revenue extraction (should show no duplicates)
uv run python -c "
import asyncio
from raglite.forecasting.timeseries_extract import extract_timeseries_from_sql
from collections import Counter

async def test():
    data = await extract_timeseries_from_sql(metric='Turnover+VAT', min_points=6)
    dates = [p.date for p in data.points]
    duplicates = [d for d, count in Counter(dates).items() if count > 1]
    if duplicates:
        print(f'❌ DUPLICATES FOUND: {len(duplicates)} dates')
    else:
        print(f'✅ NO DUPLICATES ({len(data.points)} points)')

asyncio.run(test())
"

# Test 2: Verify EBITDA MAPE
uv run python scripts/validate_forecasting_unified.py --variable ebitda

# Test 3: Full validation
uv run python scripts/validate_forecasting_unified.py --full
```

---

## Expected Results

### Before Fixes
```
Variables: 1/12 passed (8.3%)
Quality Gate: FAILED

✅ Variable Cost: 8.04%
❌ Revenue: N/A (duplicate dates crash)
❌ EBITDA: 577% (YTD conversion bug)
❌ Sales Volume: N/A (duplicate dates crash)
❌ 8 other variables: N/A or high MAPE
```

### After Fixes
```
Variables: 10/12 passed (83.3%)
Quality Gate: PASSED ✅

✅ Variable Cost: 8.04%
✅ Revenue: <5%
✅ EBITDA: <5%
✅ Sales Volume: <5%
✅ Electricity Cost: <8%
✅ Thermal Cost: <10%
✅ Avg Selling Price: <6%
✅ Capacity Utilization: <10%
❌ Pet Coke, TTF Gas, CO2, Clinker: N/A (external-only, future work)
```

---

## Files to Modify

1. `/raglite/forecasting/timeseries_extract.py`
   - Line 1128: Fix `parse_period_to_date()` to extract year
   - Line 935: Add deduplication safety net
   - Line 418: Fix EBITDA YTD conversion with gap detection

**Total Changes:** ~50 lines across 3 functions

**Estimated Time:** 2-3 hours (coding + testing)

---

## Detailed Report

See `/docs/investigation-report-variable-failures.md` for full analysis with code examples.
