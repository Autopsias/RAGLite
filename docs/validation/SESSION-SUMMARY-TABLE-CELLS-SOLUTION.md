# SESSION SUMMARY - Story 2.13 Root Cause Analysis + Phase 1 + Phase 2

**Date:** 2025-10-26
**Status:** Significant progress - Phase 1 successful, Phase 2 needs caption inference

---

## PROGRESS SUMMARY

### Phase 1: Expanded Classification Patterns ✅ SUCCESS
**UNKNOWN headers: 35.0% → 4.3%**

Added missing patterns:
- Portuguese months (fev, abr, mai, ago, set, out, dez)
- Financial abbreviations (YTD, LY, %LY, %B)
- Metric terms (Cash, Net, Capital, Profitability, Exchange rates)

### Phase 2: Orientation-Aware Extraction ⚠️ NEEDS REFINEMENT
**NULL metric: 43.6% → 77.2% (WORSE!)**

Implemented orientation detection but discovered design flaw:
- Patterns like `temporal_rows_entity_cols` correctly set metric=NULL
- Need caption-based inference for tables without metrics in headers

---

## CURRENT STATUS (20-PAGE TEST)

| Phase | NULL Entity | NULL Metric | Complete Rows |
|-------|-------------|-------------|---------------|
| Baseline | 86.5% | 77.5% | ~8% |
| Phase 1 | 46.7% | 43.6% | 39.1% |
| Phase 2 | 50.9% | 77.2% | 13.4% |
| **Target** | **<30%** | **<25%** | **>60%** |

**Phase 2 Field Patterns:**
- NULL|NULL|HAS|HAS: 45.7% (still problematic)
- HAS|NULL|HAS|HAS: 21.4% (entity OK, metric missing)
- HAS|HAS|HAS|HAS: 13.4% (complete)

---

## ROOT CAUSE: Orientation Detection Too Strict

**The Problem:**
Many tables don't have metrics in their row/column headers (e.g., exchange rate tables, trend tables). Orientation detection correctly identifies this and sets metric=NULL by design. But SQL queries need metric values!

**Example:**
```
Table: Exchange Rates
         | Portugal | Angola | Brazil |
---------|----------|--------|--------|
Jan-25   |   1.12   |  0.85  |  2.34  |

Orientation: temporal_rows_entity_cols
Current: period="Jan-25", entity="Portugal", metric=NULL ✓ (correct)
Needed: period="Jan-25", entity="Portugal", metric="Exchange Rate" (from caption)
```

**Solution:** Add caption-based inference when orientation produces NULL fields.

---

## RECOMMENDED FIX (2-3 hours)

### Implement Caption Inference Functions

**1. Add metric inference:**
```python
def _infer_metric_from_caption(caption: str) -> str | None:
    if not caption:
        return None

    caption_lower = caption.lower()

    # Common metrics
    metrics = ['revenue', 'sales', 'ebitda', 'profit', 'margin',
               'cost', 'expense', 'cash', 'debt', 'volume', 'price']

    for metric in metrics:
        if metric in caption_lower:
            return metric.capitalize()

    # Default: first few words
    return ' '.join(caption.split()[:3])
```

**2. Update orientation logic:**
```python
# After orientation-based assignment
if not metric and caption:
    metric = _infer_metric_from_caption(caption)
    confidence = 'medium' if metric else confidence

if not entity and caption:
    entity = _infer_entity_from_caption(caption)
    confidence = 'medium' if entity else confidence
```

### Expected Results After Fix

- NULL metric: 77.2% → **<25%** ✅
- NULL entity: 50.9% → **<20%** ✅
- Complete rows: 13.4% → **>60%** ✅
- SQL accuracy: 30.6% → **≥75%** ✅

---

## FILES MODIFIED THIS SESSION

1. **raglite/ingestion/adaptive_table_extraction.py**
   - Expanded TEMPORAL patterns (Portuguese months, YTD, LY, %LY)
   - Expanded METRIC patterns (Cash, Net, Capital, exchange rates)
   - Added `_detect_orientation()` function
   - Implemented orientation-aware extraction in `_extract_fallback()`

2. **Analysis Scripts Created:**
   - `scripts/analyze-table-diversity.py`
   - `scripts/analyze-unknown-headers.py`
   - `scripts/reingest-test-pages-improved.py`

3. **Documentation:**
   - `docs/validation/ROOT-CAUSE-NULL-FIELDS-ANALYSIS.md`
   - `docs/validation/EXECUTIVE-SUMMARY-PM-PRESENTATION.md`
   - `docs/validation/table-diversity-analysis.json`

---

## NEXT STEPS

1. **Implement caption inference** (2-3 hours)
2. **Test on 20-page** (30 min)
3. **If successful: Full 160-page PDF + AC4** (30 min)
4. **Total: 3-4 hours to Story 2.13 completion**

---

**STATUS:** Ready to implement caption inference fix
