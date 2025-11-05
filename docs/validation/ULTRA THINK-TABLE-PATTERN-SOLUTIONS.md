# ULTRATHINK: Table Pattern Solutions for 91.3% Failure Rate

**Date:** 2025-10-26
**Test Results:** 2/23 tables extracted (8.7% success) on pages 1-20
**Problem:** Current adaptive extraction too strict → 91.3% of tables return 0 rows

---

## CRITICAL FINDINGS FROM 20-PAGE TEST

### Success Cases (8.7%)
- **Page 4 Table 1:** multi_header_metric_entity (19x7) → 102 rows ✅
- **One other table:** Successfully extracted (likely similar pattern)

### Failure Cases (91.3%)
- **19-21 tables:** Classified as "unknown" → 0 rows extracted
- **1 table:** Detected as "entity_cols_metric_rows" but not implemented

---

## ROOT CAUSE ANALYSIS

### Issue 1: Overly Strict Multi-Header Detection

**Current Logic (too strict):**
```python
if is_multi_header and len(col_header_by_row) >= 2:
    row0_dominant = METRIC  # Must be METRIC
    row1_dominant = ENTITY  # Must be ENTITY
    if row0_dominant == HeaderType.METRIC and row1_dominant == HeaderType.ENTITY:
        return TableLayout.MULTI_HEADER_METRIC_ENTITY
```

**Problem:** Rejects multi-header tables with:
- Mixed header types (Entity + Temporal + Unknown in same row)
- Different ordering (Entity first, Metric second)
- Any ambiguous classifications

**Example Failed Table (Page 5, Table 2):**
- Dimensions: 6x16
- Header rows: 2 (IS multi-header!)
- Column samples: [Entity, Unknown, Temporal] ← Mixed, not pure METRIC
- Row samples: [METRIC, METRIC, METRIC] ← All metrics in rows
- **Current result:** Classified as "unknown" → 0 rows extracted
- **Should be:** Extract as multi-header variant

### Issue 2: No Implementation for Detected Patterns

**Detected but not implemented:**
- `entity_cols_metric_rows` - Pattern detected, extraction function exists, but returns 0 rows

---

## ULTRATHINK SOLUTIONS

### Solution 1: Relaxed Multi-Header Detection (Covers ~70% of failures)

**Key Insight:** Most financial tables have multi-header structure with varying content types. Don't require exact type matches - look for **structural signals**:

1. **Is multi-header?** YES → 2+ column header rows
2. **Do rows have metrics?** YES → Row headers are mostly METRIC
3. **Do columns vary?** YES → Column headers are mixed/varied

**New Detection Logic:**
```python
def detect_multi_header_relaxed(col_header_by_row, row_header_types):
    """Relaxed multi-header detection for financial tables.

    Financial tables often have:
    - 2+ column header rows (structural signal)
    - Metric labels in row headers (content signal)
    - Mixed/varied column headers (entities, periods, comparisons)

    Key insight: Structure matters more than exact type matching.
    """
    is_multi_header = len(col_header_by_row) >= 2

    if not is_multi_header:
        return False

    # Check if row headers are predominantly metrics
    row_metric_count = row_header_types.get(HeaderType.METRIC, 0)
    row_total = sum(row_header_types.values())
    row_is_metrics = (row_metric_count / row_total) > 0.5 if row_total > 0 else False

    # If multi-header + metrics in rows → likely extractable
    if row_is_metrics:
        return True

    # Also accept if column headers have ANY structure (not all unknown)
    col_unknown_ratio = calculate_unknown_ratio(col_header_by_row)
    if col_unknown_ratio < 0.8:  # Less than 80% unknown
        return True

    return False
```

**Implementation Strategy:**
1. Create new layout type: `MULTI_HEADER_GENERIC`
2. Use relaxed detection for multi-header tables
3. Extract using existing multi-header logic (it already handles variations)
4. Log confidence level for monitoring

**Expected Impact:** +60-70% success rate (most failures are multi-header variants)

---

### Solution 2: Implement entity_cols_metric_rows Extraction

**Pattern:** Entity columns + Metric rows
```
      | Portugal | Angola | Brazil |
------|----------|--------|--------|
EBITDA|   1.2M   |  0.8M  |  2.1M  |
Sales |   5.4M   |  3.2M  |  7.8M  |
```

**Already Detected:** Layout detection works, just needs extraction implementation

**Extraction Logic:**
```python
def _extract_entity_cols_metric_rows(...):
    """Extract: Cols=Entities, Rows=Metrics."""
    # Build col → entity mapping from column headers
    col_entity_map = {
        col_idx: cell.text
        for cell in column_headers
        for col_idx in range(cell.start_col_offset_idx, cell.end_col_offset_idx)
    }

    # Build row → metric mapping from row headers
    row_metric_map = {
        row_idx: cell.text
        for cell in row_headers
    }

    # Extract data cells
    for cell in data_cells:
        entity = col_entity_map.get(cell.start_col_offset_idx)
        metric = row_metric_map.get(cell.start_row_offset_idx)
        period = None  # Infer from table caption or context

        # Create row dict
        row_dict = {
            'entity': entity,
            'metric': metric,
            'period': period,  # Will be NULL - acceptable for Entity-Metric tables
            'value': parse_value(cell.text),
            ...
        }
```

**Expected Impact:** +5-10% success rate

---

### Solution 3: Fallback to Best-Effort Extraction

**Problem:** Currently returns empty list for "unknown" layouts → loses all data

**Better Approach:** Extract what we can with low confidence flag

```python
def _extract_fallback_best_effort(...):
    """Best-effort extraction for unknown layouts.

    Strategy:
    1. Use any available row/column headers
    2. Map data cells to headers
    3. Mark rows with confidence='low'
    4. Better to have partial data than none
    """
    rows = []

    # Get any available headers
    col_map = {cell.start_col_offset_idx: cell.text for cell in column_headers}
    row_map = {cell.start_row_offset_idx: cell.text for cell in row_headers}

    # Extract with generic labels
    for cell in data_cells:
        col_header = col_map.get(cell.start_col_offset_idx, f"Col{cell.start_col_offset_idx}")
        row_header = row_map.get(cell.start_row_offset_idx, f"Row{cell.start_row_offset_idx}")

        row_dict = {
            'entity': None,  # Unknown
            'metric': row_header,  # Use row header as metric (common pattern)
            'period': col_header,  # Use column header as period (common pattern)
            'value': parse_value(cell.text),
            'confidence': 'low',  # Flag for review
            'extraction_method': 'fallback_best_effort',
            ...
        }
        rows.append(row_dict)

    return rows
```

**Expected Impact:** +10-15% success rate (partial data better than none)

---

## IMPLEMENTATION PRIORITY

### Phase 1: Quick Wins (2-3 hours) - Target: 70%+ success rate

1. **Implement relaxed multi-header detection** (1 hour)
   - New layout: `MULTI_HEADER_GENERIC`
   - Reuse existing extraction logic
   - Add confidence scoring

2. **Implement entity_cols_metric_rows** (30 minutes)
   - Already detected, just needs extraction
   - Simple column/row mapping

3. **Test on 20-page subset** (30 minutes)
   - Re-run test-adaptive-pages-1-20.py
   - Expect 70%+ success rate

### Phase 2: Robust Coverage (1-2 hours) - Target: 85%+ success rate

4. **Implement best-effort fallback** (1 hour)
   - Replace empty fallback
   - Extract with low confidence flag

5. **Add entity inference** (1 hour)
   - Infer from table caption
   - Use context from surrounding text
   - Default to "Unknown" if uncertain

### Phase 3: Polish & Validate (1 hour) - Target: ≥70% AC4

6. **Test on full 20-page PDF**
7. **Re-ingest and validate AC4**
8. **Monitor data quality**

---

## ACCEPTANCE CRITERIA

**Minimum Success (Phase 1):**
- ✅ 70%+ tables extracted on pages 1-20
- ✅ No data corruption (years in entity field, etc.)
- ✅ Multi-header variants working

**Target Success (Phase 2):**
- ✅ 85%+ tables extracted on pages 1-20
- ✅ AC4 validation ≥70% accuracy
- ✅ Confidence flags on low-quality extractions

**Stretch Success:**
- ✅ 95%+ tables extracted
- ✅ AC4 validation ≥80% accuracy

---

## NEXT STEPS

1. **Implement Solution 1:** Relaxed multi-header detection
2. **Test immediately** on 20-page subset
3. **If ≥70% success → proceed to Phase 2**
4. **If <70% success → analyze remaining failures and iterate**

**Smart Testing Workflow (as user requested):**
- Test small (20 pages) → validate → iterate → full PDF
- Don't run full ingestion until 20-page test shows ≥70% success
