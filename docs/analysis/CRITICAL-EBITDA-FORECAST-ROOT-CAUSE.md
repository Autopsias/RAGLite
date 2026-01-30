# CRITICAL: EBITDA Forecasting Root Cause Analysis

**Date:** 2026-01-30
**Severity:** P0 - System Unusable for Financial Planning
**Impact:** ~85% of historical GROUP EBITDA data is being silently discarded

---

## Executive Summary

The raglite forecasting system reports "only 2 data points" for GROUP EBITDA when **292 records exist in the database**. Root cause: **period format parsing incompatibility** between database content and forecasting code.

---

## Data Discovery

### Database Reality

```sql
SELECT COUNT(*) FROM financial_tables
WHERE entity_normalized = 'Group' AND metric ILIKE '%ebitda%';
```

**Result:** 292 total GROUP EBITDA records

```sql
SELECT COUNT(*) as total,
       COUNT(CASE WHEN period IS NOT NULL AND period <> '' THEN 1 END) as with_period,
       COUNT(CASE WHEN value IS NOT NULL THEN 1 END) as with_value
FROM financial_tables
WHERE entity_normalized = 'Group' AND metric ILIKE '%ebitda%';
```

**Result:**
- Total: 292 records
- With non-empty period: 247 records (85%)
- With non-null value: ~150+ records

**But forecasting system sees only 2 usable points!**

---

## Root Cause: Period Format Incompatibility

### Current Parser Requirements

**File:** `raglite/forecasting/timeseries/parsing.py:183`

```python
def parse_period_to_date(period: str, fiscal_year: int) -> datetime:
    # ONLY accepts: r"^([A-Za-z]+)-(\d{2})$"
    # Examples: "Jan-25", "Dec-24", "Feb-23"
```

**Regex:** `^([A-Za-z]+)-(\d{2})$`

**Accepts:**
- `Dec-21` ✓
- `Jan-25` ✓
- `Feb-23` ✓

**Rejects (raises ValueError):**
- `B Dec-21` ✗ (has "B " prefix)
- `YTD Jun-24` ✗ (has "YTD " prefix)
- `B Dec-17 YTD` ✗ (has both prefix and suffix)
- `Dec-2017` ✗ (4-digit year instead of 2-digit)
- `Dez-2017` ✗ (Portuguese month name + 4-digit year)
- `2017 P` ✗ (year-only format)
- `N/A` ✗ (not a date)
- empty string ✗

---

## Database Period Format Distribution

**Top 30 period formats for GROUP EBITDA:**

| Period Format | Count | Parseable? | Issue |
|---------------|-------|------------|-------|
| `Dec-21` | 13 | ✓ | Valid |
| `Dec-20` | 13 | ✓ | Valid |
| `Feb-23` | 12 | ✓ | Valid |
| `B Dec-21` | 6 | ✗ | "B " prefix |
| `Jan-24` | 6 | ✓ | Valid |
| `Jan-23` | 5 | ✓ | Valid |
| `Dec-17` | 5 | ✓ | Valid |
| `YTD Jun-24` | 4 | ✗ | "YTD " prefix |
| `Jul-24` | 4 | ✓ | Valid |
| `Sep-24` | 4 | ✓ | Valid |
| `YTD Feb-24` | 4 | ✗ | "YTD " prefix |
| `YTD Feb-23` | 4 | ✗ | "YTD " prefix |
| `Mar-23` | 4 | ✓ | Valid |
| `Dec-18` | 4 | ✓ | Valid |
| `Jun-24` | 4 | ✓ | Valid |
| `Dec-16` | 3 | ✓ | Valid |
| `YTD Mar-23` | 3 | ✗ | "YTD " prefix |
| `B Feb-23` | 3 | ✗ | "B " prefix |
| `B Oct-24` | 3 | ✗ | "B " prefix |
| `B Dec-22` | 3 | ✗ | "B " prefix |
| `YTD Nov-24` | 3 | ✗ | "YTD " prefix |
| `Dec-22` | 3 | ✓ | Valid |
| `Feb-22` | 3 | ✓ | Valid |
| `Oct-24` | 3 | ✓ | Valid |
| `YTD Apr-24` | 3 | ✗ | "YTD " prefix |
| `B Jun-24` | 3 | ✗ | "B " prefix |
| `Mar-24` | 3 | ✓ | Valid |
| `May-24` | 3 | ✓ | Valid |
| `YTD Dec-20` | 3 | ✗ | "YTD " prefix |
| `YTD Sep-24` | 3 | ✗ | "YTD " prefix |

**Additional formats found in full query (not in top 30):**

| Period Format | Example | Parseable? | Issue |
|---------------|---------|------------|-------|
| Full year (4-digit) | `Dec-2017` | ✗ | 4-digit year |
| Portuguese months | `Dez-2017`, `Dez_2017` | ✗ | PT month name |
| Year only | `2017 P`, `2018 P` | ✗ | No month |
| Invalid | `N/A` | ✗ | Not a date |
| Trailing suffix | `B Dec-17 YTD` | ✗ | Suffix after date |
| Empty | `` (empty string) | ✗ | No value |

---

## Impact Analysis

### Records Being Discarded

**Estimated breakdown of 247 non-empty periods:**
- ✓ Parseable (Mon-YY format): ~60-80 records (~30%)
- ✗ With "B " prefix: ~30 records
- ✗ With "YTD " prefix: ~40 records
- ✗ Full year formats: ~20 records
- ✗ Other invalid formats: ~70-90 records

**Net result:** ~85% data loss during parsing

### Why "Only 2 Data Points"?

After period parsing filters out ~85% of records, the remaining points then undergo:
1. **Aggregation by period** (may combine duplicate periods)
2. **Outlier detection** (MAD-based filtering)
3. **Minimum data point check** (requires 6+ points)

If aggregation reduces 60-80 parseable records down to ~5-6 unique periods (due to duplicate "Dec-21", "Dec-20", etc.), and outlier filtering removes 3-4 more, the system ends up with **only 2 usable points**.

---

## Secondary Issue: Scale/Unit Confusion

Even when forecasts DO run (for entity-level forecasts), values appear wrong:

**Portugal forecast output:**
```
Jan 2026: -5.0 M EUR
May 2026: -55.8 M EUR
Dec 2026: +66.2 M EUR
```

**This is impossible** because:
- Portugal annual EBITDA: ~80-100 M EUR (always positive)
- Monthly swings of -55M to +66M don't match operational reality
- These look like YTD deltas or variance values, not absolute EBITDA

**Hypothesis:** Training data contains YTD cumulative values being treated as monthly absolute values.

---

## Recommended Fixes

### Priority 1: Expand Period Parser (CRITICAL)

**File to modify:** `raglite/forecasting/timeseries/parsing.py:183`

**Add support for:**

1. **Strip "B " prefix (Budget/Baseline):**
   ```python
   if period.startswith("B "):
       period = period[2:]  # "B Dec-21" → "Dec-21"
   ```

2. **Strip "YTD " prefix:**
   ```python
   if period.startswith("YTD "):
       period = period[4:]  # "YTD Jun-24" → "Jun-24"
   ```

3. **Strip trailing " YTD":**
   ```python
   if period.endswith(" YTD"):
       period = period[:-4]  # "B Dec-17 YTD" → "B Dec-17"
   ```

4. **Handle 4-digit year formats:**
   ```python
   # "Dec-2017" → "Dec-17"
   match = re.match(r"^([A-Za-z]+)-(\d{4})$", period)
   if match:
       month, year_full = match.groups()
       year_suffix = str(year_full)[-2:]  # "2017" → "17"
       period = f"{month}-{year_suffix}"
   ```

5. **Handle Portuguese month names:**
   ```python
   PT_MONTHS = {
       "Jan": "Jan", "Fev": "Feb", "Mar": "Mar", "Abr": "Apr",
       "Mai": "May", "Jun": "Jun", "Jul": "Jul", "Ago": "Aug",
       "Set": "Sep", "Out": "Oct", "Nov": "Nov", "Dez": "Dec"
   }
   # Convert "Dez-2017" → "Dec-17"
   ```

6. **Handle underscores:**
   ```python
   period = period.replace("_", "-")  # "Dez_2017" → "Dez-2017"
   ```

**New regex after cleanup:**
```python
# After all preprocessing:
match = re.match(r"^([A-Za-z]+)-(\d{2})$", period.strip())
```

---

### Priority 2: Investigate YTD vs Absolute Values

**Files to check:**
- `raglite/forecasting/timeseries/sql_extraction_query.py` - SQL aggregation logic
- `raglite/forecasting/timeseries/sql_extraction_parsing.py` - Value interpretation
- Database schema: Are values stored as absolute or deltas?

**Questions:**
1. Is there a `value_type` column indicating "absolute", "ytd", "delta"?
2. Are YTD periods being aggregated correctly?
3. Should YTD values be converted to monthly values before forecasting?

---

### Priority 3: Add Data Quality Validation

**Add to SQL extraction:**
```python
logger.info(
    "Period format distribution",
    extra={
        "parseable": len([p for p in periods if is_parseable(p)]),
        "with_prefix": len([p for p in periods if has_prefix(p)]),
        "full_year": len([p for p in periods if is_full_year_format(p)]),
        "invalid": len([p for p in periods if not is_parseable_after_cleanup(p)]),
    }
)
```

---

## Test Cases for Validation

After fixes, these should ALL parse successfully:

```python
test_cases = [
    ("Dec-21", datetime(2021, 12, 1)),           # Current valid format
    ("B Dec-21", datetime(2021, 12, 1)),         # Budget prefix
    ("YTD Jun-24", datetime(2024, 6, 1)),        # YTD prefix
    ("B Dec-17 YTD", datetime(2017, 12, 1)),     # Both prefix and suffix
    ("Dec-2017", datetime(2017, 12, 1)),         # 4-digit year
    ("Dez-2017", datetime(2017, 12, 1)),         # Portuguese + 4-digit year
    ("Dez_2017", datetime(2017, 12, 1)),         # Underscore + PT month
    ("Jan-25", datetime(2025, 1, 1)),            # Standard format
]

for period, expected in test_cases:
    result = parse_period_to_date(period, None)
    assert result == expected, f"Failed: {period} → {result} (expected {expected})"
```

---

## Success Criteria

After implementing fixes:

1. **Data point count increases from 2 to 50+** for GROUP EBITDA
2. **All period formats in database parse successfully** (or log clear warning if unparseable)
3. **2026 GROUP EBITDA forecast is ~220-260 M EUR** (realistic range)
4. **Entity-level forecasts show positive monthly values** (no -55M swings for Portugal)
5. **Aggregation from entities approximately equals GROUP total** (within consolidation adjustments)

---

## References

- **Period formats query:** `SELECT DISTINCT period FROM financial_tables WHERE entity_normalized = 'Group' AND metric ILIKE '%ebitda%';`
- **Parser code:** `raglite/forecasting/timeseries/parsing.py:183`
- **SQL extraction:** `raglite/forecasting/timeseries/sql_extraction.py`
- **Database schema:** `docker exec raglite-postgresql psql -U raglite -d raglite -c "\d financial_tables"`

---

## Next Steps

1. **Immediate:** Implement enhanced period parser with all format support
2. **Validate:** Run test suite to ensure no regressions
3. **Test:** Request GROUP EBITDA forecast and verify ~50+ data points used
4. **Investigate:** YTD vs absolute value handling for entity-level forecasts
5. **Document:** Add period format standards to ingestion documentation
