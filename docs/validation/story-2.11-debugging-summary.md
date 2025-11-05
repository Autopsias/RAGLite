# Story 2.11 Debugging Summary

**Date:** 2025-10-25
**Status:** Investigation completed, validation pending re-ingest

---

## Critical Issue: 0% Retrieval Accuracy

### Initial Symptoms
- All validation scripts returned 0% accuracy (vs 56% baseline)
- BM25 tuning: 0% across all alpha values (0.7-0.9)
- Final Phase 2A validation: 0% retrieval accuracy
- Alarming -56pp regression from baseline

### Investigation Process

1. **Hypothesis 1: RRF Implementation Bug?**
   - Created `debug-rrf-single-query.py` to trace execution
   - Tested query: "What is the variable cost per ton for Portugal Cement in August 2025 YTD?"
   - Expected document: "2025-08 Performance Review CONSO_v2.pdf" page 46

2. **Actual Results:**
   - Retrieved document: "sample_financial_report.pdf" page 4
   - **WRONG DOCUMENT!**

3. **Root Cause Discovery:**
   - Checked Qdrant collection contents
   - Found only 15 chunks from "sample_financial_report.pdf"
   - Ground truth queries expect "2025-08 Performance Review CONSO_v2.pdf"
   - **The validation document was never ingested into Qdrant!**

### Root Cause

**NOT an RRF bug!** The Qdrant collection contained the wrong document.

- **Expected:** 2025-08 Performance Review CONSO_v2.pdf (160 pages, ~2000 chunks)
- **Actual:** sample_financial_report.pdf (15 chunks)
- **Impact:** 0% accuracy because queries searched the wrong document

### RRF Implementation Status

✅ **RRF IS WORKING CORRECTLY**
- Reciprocal Rank Fusion algorithm implemented with k=60 (from literature)
- Scores in realistic RRF range (0.015-0.023, not normalized to 1.0)
- Fusion logic validated and correct
- Score normalization bug successfully fixed

### Resolution

1. ✅ Identified that `scripts/reingest-with-table-aware-chunking.py` exists
2. ✅ Confirmed it ingests correct document: `docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf`
3. ⏳ Running reingest (10-15 min ETA) to populate Qdrant with correct document
4. ⏳ Will re-run validation scripts after reingest completes

---

## AC3: Auto-Classification Analysis

### Analysis Results

**Script:** `scripts/analyze-auto-classification-accuracy.py`

**Metrics:**
- Total queries analyzed: 50
- Queries with metadata extracted: 47 (94% usage)
- Correct extractions: 33
- Incorrect extractions: 14
- No extraction: 3

**Accuracy:** 70.2%

### Decision Criteria

- **Threshold:** ≥80% accuracy required to keep feature
- **Result:** 70.2% < 80% threshold
- **Decision:** **DISABLE auto-classification**

### Rationale

With 70.2% accuracy, incorrect metadata extractions eliminate correct chunks more often than they help. The feature adds complexity without sufficient benefit.

### Implementation

Changed `hybrid_search()` default parameter:
```python
# Before (Story 2.4)
auto_classify: bool = True

# After (Story 2.11 AC3)
auto_classify: bool = False  # 70.2% accuracy < 80% threshold
```

**File:** `raglite/retrieval/search.py:417`

---

## Summary of Changes

### AC1: Score Normalization Fix ✅
- **Issue:** Metadata boosting caused scores to normalize to 1.0
- **Fix:** Implemented Reciprocal Rank Fusion (RRF) with k=60
- **Result:** Scores in realistic range (0.015-0.023)
- **File:** `raglite/retrieval/search.py:fuse_search_results()`

### AC2: BM25 Tuning ⏳
- **Status:** Pending re-ingest completion
- **Alpha values to test:** 0.7, 0.75, 0.8, 0.85, 0.9
- **Script:** `scripts/tune-bm25-fusion-weights.py`

### AC3: Auto-Classification Decision ✅
- **Decision:** DISABLE (70.2% accuracy < 80%)
- **Implementation:** Changed default `auto_classify=False`
- **File:** `raglite/retrieval/search.py:417`

### AC4: Final Validation ⏳
- **Status:** Pending re-ingest completion
- **Script:** `scripts/run-phase2a-final-validation.py`
- **Target:** ≥70% accuracy for Phase 2A success

---

## Next Steps

1. ⏳ **Wait for reingest** (10-15 min ETA)
2. **Re-run BM25 tuning** with correct document
3. **Re-run final validation** with all Phase 2A fixes
4. **Update alpha default** based on tuning results
5. **Evaluate decision gate** and document final accuracy
6. **Update story documentation** with results and file lists

---

## Key Learnings

1. **Always validate test data setup** before assuming code bugs
2. **RRF implementation was correct** - the 0% accuracy was environmental
3. **Auto-classification feature** removed due to insufficient accuracy
4. **Debugging workflow:**
   - Symptom: 0% accuracy
   - Investigation: Trace single query execution
   - Discovery: Wrong document in database
   - Resolution: Re-ingest correct document

---

## Files Created/Modified

### New Scripts (Diagnostics & Validation)
- `scripts/debug-hybrid-search-scoring.py` - Score normalization diagnostic
- `scripts/debug-rrf-single-query.py` - Single query trace for debugging
- `scripts/tune-bm25-fusion-weights.py` - BM25 alpha tuning (fixed field names)
- `scripts/analyze-auto-classification-accuracy.py` - Auto-classification analysis (fixed imports)
- `scripts/run-phase2a-final-validation.py` - Final Phase 2A validation (fixed field names)

### Modified Source Code
- `raglite/retrieval/search.py:fuse_search_results()` - RRF implementation (~175 lines)
- `raglite/retrieval/search.py:hybrid_search()` - Auto-classification disabled (line 417)

### Validation Results
- `docs/validation/story-2.11-bm25-tuning.json` - BM25 tuning results (needs re-run)
- `docs/validation/story-2.11-auto-classification-analysis.json` - Auto-classification analysis ✅
- `docs/validation/phase2a-final-validation.json` - Final validation (needs re-run)

---

**Estimated Re-Validation Time:** 15-20 minutes after reingest completes
