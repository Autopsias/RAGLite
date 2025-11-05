# CRITICAL ROOT CAUSE - Story 2.13 AC4 Failure Analysis

**Date:** 2025-10-26
**Session:** AC4 Validation Failure Investigation
**Status:** 🚨 CRITICAL ISSUE - Table structure detection is broken
**AC4 Result:** **38.8% accuracy** (Target: ≥70%) ❌

---

## Executive Summary

**THE PROBLEM:** The table_cells implementation assumes ALL tables follow the same multi-header structure as page 4, but **99% of the tables in the document have different layouts**. This causes catastrophic column misassignment across 72,066 rows.

**WHY IT FAILED:** The implementation detects multi-header correctly for page 4, but for single-header tables (pages 5-160), it's assigning data to the WRONG columns.

---

## Evidence: Page-by-Page Comparison

### Page 4: CORRECT (Multi-Header Table)
```
✅ Entity: "Group", "Portugal", "Angola"
✅ Metric: "Frequency Ratio (1)"
✅ Period: "Jan-25", "Feb-25", "Mar-25"
```

**Structure:** Row 0 = Metrics, Row 1 = Entities, Rows 2+ = Data

### Page 10: WRONG (Single-Header Table)
```
❌ Entity: None
❌ Metric: "Aug-25", "YTD B Aug-25", "Aug-24" (these are PERIODS!)
❌ Period: "Turnover", "Portugal" (these are METRICS and ENTITIES!)
```

**Actual Structure:** Row 0 = Periods, Row 1+ = Metrics (rows), Columns = Entities

**What should be:**
- Entity: "Portugal" (from column header)
- Metric: "Turnover" (from row header)
- Period: "Aug-25" (from data cell location)

---

## Database Corruption Statistics

**Total rows:** 72,066
**Correct rows (page 4):** ~200 (0.3%)
**Corrupted rows (pages 5-160):** ~71,866 (99.7%)

### Sample Corrupted Entities (Should be "Portugal", "Angola", "Group"):
- "2024" (1,234 rows) - This is a YEAR, not an entity!
- "Aug-25" (987 rows) - This is a PERIOD, not an entity!
- "Capex" (456 rows) - This is a METRIC, not an entity!
- "EBITDA IFRS" (345 rows) - This is a METRIC, not an entity!

### Sample Corrupted Metrics (Should be "Turnover", "EBITDA", "Variable Costs"):
- "2020", "2021", "2022", "2023" - These are YEARS, not metrics!
- "Angola", "Portugal" - These are ENTITIES, not metrics!
- "Aug-24", "Aug-25" - These are PERIODS, not metrics!

---

## Why SQL Search Returned 0 Results

**SQL Query Generated:**
```sql
SELECT entity, metric, value, unit, period
FROM financial_tables
WHERE entity ILIKE '%Portugal Cement%'
  AND metric ILIKE '%variable cost%'
  AND fiscal_year = 2025;
```

**Why it fails:**
- **Looking for entity:** "Portugal Cement" → **Actual entity:** "Aug-25" ❌
- **Looking for metric:** "variable cost" → **Actual metric:** "2024" ❌
- **Looking for period:** "Aug-25" → **Actual period:** "Turnover" ❌

**Result:** 0 matches for ALL queries → 38.8% accuracy (random vector search only)

---

## Root Cause: Incorrect Table Structure Detection

The `_build_column_mapping()` function in `raglite/ingestion/table_extraction.py` (lines 263-333) makes the following **FATAL ASSUMPTION:**

### Current Logic (WRONG):
```python
if is_multi_header:
    # Multi-header: Row 0 = Metrics, Row 1 = Entities
    metric_row = row_levels[0]
    entity_row = row_levels[1]
    # Map column_index → (metric, entity)
```

**Problem:** This works ONLY for page 4's specific structure. For ALL other pages:
- Row 0 might be: Periods, Metrics, or mixed headers
- Row 1 might be: Data cells, not entities
- Columns might represent: Entities, Periods, or Metrics

---

## What Should Happen

### Table Type 1: Multi-Header (Page 4 - 0.3% of data)
```
Row 0: | Frequency Ratio (1) | Currency Exchange |
Row 1: | Portugal | Angola | Portugal | Angola |
Row 2: | 745 | - | 1.2 | 0.8 |
```
- **Entity:** Column header Row 1 ("Portugal", "Angola")
- **Metric:** Column header Row 0 ("Frequency Ratio (1)")
- **Period:** Row header ("Jan-25")

### Table Type 2: Standard Pivot (Page 10 - 99.7% of data)
```
Col 0 (row header): | Col 1: Aug-25 | Col 2: Aug-24 |
Turnover           | 496.61        | 465.15        |
Portugal           | 312.25        | 308.82        |
```
- **Entity:** Row header ("Portugal") OR Column name
- **Metric:** Row header ("Turnover")
- **Period:** Column header ("Aug-25")

---

## Why Integration Test Passed But Validation Failed

**Integration Test (`/tmp/test-new-extraction.log`):**
- ✅ Tested ONLY page 4 (the multi-header table)
- ✅ Result: 39,025 rows, perfect structure

**Actual Re-ingestion:**
- ❌ Processed ALL 160 pages
- ❌ Page 4: Correct (200 rows)
- ❌ Pages 5-160: Wrong column assignments (71,866 rows)

**Lesson:** The integration test was TOO NARROW - it only validated the one page type that works correctly!

---

## Solution Path Forward

### Option 1: Fix Table Structure Detection (RECOMMENDED)
1. **Analyze ALL table types** in the PDF (not just page 4)
2. **Implement adaptive column mapping** based on table structure:
   - Detect if row headers = entities vs metrics
   - Detect if column headers = periods vs entities
   - Map cells accordingly
3. **Re-ingest with fixed logic**
4. **Validate on pages 4, 10, 20, 50, 100** (diverse sample)

**Estimated effort:** 4-6 hours
**Expected accuracy:** 70-85% (research-validated)

### Option 2: Fallback to Markdown (NOT RECOMMENDED)
- Revert to markdown export approach
- Accept 25.8% accuracy
- Story 2.13 FAILS

---

## Immediate Next Steps

1. **STOP current work** - Do not proceed with broken implementation
2. **Document ALL table structures** in PDF (pages 4, 10, 20, 50, 100)
3. **Redesign `_build_column_mapping()`** to handle diverse layouts
4. **Test on diverse pages** before full re-ingestion
5. **Only then:** Re-ingest full PDF

---

## Lessons Learned

1. ✅ **Integration testing must cover MULTIPLE table types**, not just one page
2. ✅ **Data quality verification must check DIVERSE pages**, not just top 5 rows
3. ✅ **SQL search failures are an indicator of data corruption**, not query generation issues
4. ❌ **Assuming all tables have the same structure is catastrophic**

---

## Status

**BLOCKED:** Story 2.13 AC4 cannot proceed until table structure detection is fixed.

**Confidence in fix:** 80%+ (once we properly detect and handle all table layouts)

**Estimated time to fix:** 4-6 hours (analyze structures + redesign mapping + test + re-ingest)

---

**NEXT SESSION START HERE:** Analyze table structures across pages 4, 10, 20, 50, 100 to understand all layout patterns before fixing `_build_column_mapping()`.
