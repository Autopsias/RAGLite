# Story 2.11 - Phase 2A Failure Analysis

**Date:** 2025-10-26
**Status:** ⚠️ **PHASE 2A FAILED** - Escalate to Phase 2B
**Severity:** CRITICAL

---

## Executive Summary

Phase 2A implementation **failed to meet accuracy targets** and resulted in a **significant regression** from baseline performance.

**Key Metrics:**
- **Final Accuracy: 18.0%** (9/50 correct)
- **Baseline Accuracy: 56.0%**
- **Regression: -38.0pp** (68% relative decrease)
- **Target: ≥70%** (missed by -52pp)
- **Decision:** ESCALATE TO PHASE 2B (PM approval required)

**Positive Findings:**
- ✅ Attribution Accuracy: 100.0% (target: ≥95%)
- ✅ Latency p95: 80ms (target: <15000ms)
- ✅ Latency p50: 55ms

---

## Phase 2A Implementations

### Story 2.8: Table-Aware Chunking ✅ (Technical)
- **Implementation:** 4096-token threshold with row-based splitting for large tables
- **Results:**
  - Chunks per table: 1.25 (target: ≤1.5) ✅
  - Total chunks: 190 (160 pages)
  - Table chunks: 171 (90%)
  - Max chunk size: 4096 tokens ✅

**Concern:** Large table chunks (avg 1568 tokens) may cause semantic dilution

### Story 2.9: Ground Truth Page References ✅
- **Implementation:** 50 validated Q&A pairs with page numbers
- **Quality:** All queries manually validated against PDF content

### Story 2.10: Query Routing Fix ✅
- **Implementation:** Reduced over-routing to SQL from 48% → 8%
- **Impact:** More queries processed by hybrid RAG retrieval

### Story 2.11: Hybrid Search Improvements ✅ (Technical)

#### AC1: RRF Score Normalization
- **Implementation:** Reciprocal Rank Fusion (k=60)
- **Status:** ✅ Scores in realistic range (0.015-0.023)
- **Concern:** RRF ranking may not match expected behavior

#### AC2: BM25 Tuning
- **Results:** All alpha values (0.7-0.9) = 18.0% accuracy
- **Finding:** BM25 weight has ZERO impact on accuracy
- **Implication:** BM25 and semantic search returning identical results

#### AC3: Auto-Classification
- **Analysis:** 70.2% accuracy (below 80% threshold)
- **Decision:** DISABLED by default ✅
- **Implementation:** Changed `auto_classify=False` in hybrid_search()

---

## Failure Analysis

### Accuracy Breakdown

```
Baseline:      56.0% (28/50 correct)
Phase 2A:      18.0% (9/50 correct)
Regression:    -38.0pp (-68% relative)
Target:        70.0%
Gap to target: -52.0pp
```

### Critical Findings

1. **Massive Regression (-38pp)**
   - Phase 2A made accuracy WORSE, not better
   - Only 9/50 queries answered correctly vs 28/50 baseline
   - Lost 19 previously correct queries

2. **BM25 Has Zero Impact**
   - All alpha values (0.7-0.9) produce identical 18% accuracy
   - Suggests BM25 and semantic search returning same results
   - Fusion parameter has no effect on ranking

3. **RRF May Be Broken**
   - Despite correct scores (0.015-0.023 range)
   - Ranking logic may not be functioning as expected
   - Need to investigate RRF ranking vs weighted sum ranking

4. **Table-Aware Chunking May Harm Retrieval**
   - Larger chunks (avg 1568 tokens) may dilute semantic meaning
   - 90% of chunks are tables (171/190)
   - Semantic embeddings may not capture table details effectively

---

## Root Cause Hypotheses

### Hypothesis 1: RRF Implementation Bug ⚠️ **MOST LIKELY**
**Symptoms:**
- All alpha values produce identical accuracy
- Significant regression from baseline
- Scores look correct but rankings may be wrong

**Evidence:**
- Alpha tuning shows zero sensitivity (all 18%)
- This shouldn't happen with working fusion

**Investigation Needed:**
- Compare RRF rankings vs weighted sum rankings
- Validate document key matching in RRF
- Check if BM25 rankings are being used correctly

### Hypothesis 2: Table-Aware Chunking Semantic Dilution
**Symptoms:**
- 90% of chunks are large tables (avg 1568 tokens)
- Table chunks may have weak semantic embeddings
- Embeddings may not capture specific data points

**Evidence:**
- Queries ask for specific numbers/metrics
- Large table chunks contain many unrelated data points
- Embedding model may not distinguish relevant rows

**Investigation Needed:**
- Test baseline chunking (512 tokens) vs table-aware (4096 tokens)
- Compare retrieval accuracy with different chunk sizes
- Analyze which queries fail with table-aware chunking

### Hypothesis 3: BM25 Index Corruption
**Symptoms:**
- BM25 has zero impact on accuracy
- All alpha values identical

**Evidence:**
- BM25 tuning should show variance
- Either BM25 broken OR identical to semantic

**Investigation Needed:**
- Validate BM25 index contents
- Test BM25-only search (alpha=0)
- Compare BM25 vs semantic rankings

### Hypothesis 4: Ground Truth Validation Issues
**Symptoms:**
- Dramatic accuracy drop

**Evidence:**
- Ground truth queries manually validated
- Document successfully ingested (190 chunks)

**Likelihood:** LOW - data setup verified

---

## Performance Comparison

| Metric | Baseline | Phase 2A | Change |
|--------|----------|----------|--------|
| Retrieval Accuracy | 56.0% | 18.0% | **-38.0pp** ❌ |
| Attribution Accuracy | ~50% | 100.0% | +50.0pp ✅ |
| p50 Latency | ~200ms | 55ms | -145ms ✅ |
| p95 Latency | ~500ms | 80ms | -420ms ✅ |
| Chunks | ~2000 | 190 | -91% |
| Chunks per table | 8.6 | 1.25 | -85% ✅ |

**Analysis:**
- Attribution and latency significantly improved ✅
- But retrieval accuracy collapsed ❌
- Fewer chunks (190 vs 2000) may be too aggressive

---

## Impact Assessment

### Business Impact: CRITICAL ❌
- Cannot proceed to Epic 3 (AI Intelligence)
- Phase 2B implementation required (3-4 weeks)
- PostgreSQL + cross-encoder re-ranking needed
- PM approval required for Phase 2B budget

### Technical Debt: MODERATE ⚠️
- RRF implementation may need rewrite/revert
- Table-aware chunking may need tuning
- BM25 index may need recreation
- Auto-classification feature disabled (simplifies codebase) ✅

---

## Next Steps

### Immediate (T+0 to T+2)

1. **Escalate to PM** ⚠️
   - Present Phase 2A failure analysis
   - Request approval for Phase 2B (3-4 weeks)
   - Discuss alternatives (revert to baseline? fix RRF?)

2. **Deep Dive Investigation** 🔍
   - **Priority 1:** Debug RRF implementation
   - Compare RRF vs weighted sum rankings side-by-side
   - Test semantic-only search (disable BM25)
   - Test BM25-only search (alpha=0)

3. **Test Chunking Impact**
   - Re-ingest with baseline 512-token chunking
   - Compare accuracy: table-aware vs fixed chunking
   - Determine if table-aware chunking is the problem

### Phase 2B Planning (Conditional)

**IF PM approves Phase 2B:**
- PostgreSQL for structured metadata search
- Qdrant for semantic search
- Cross-encoder re-ranking for precision
- Expected accuracy: 70-80%
- Timeline: 3-4 weeks
- Budget: Additional infrastructure costs

---

## Lessons Learned

1. **Always validate incrementally**
   - Should have tested each fix independently
   - Combining 4 major changes made debugging harder
   - RRF + table-aware chunking tested together = unclear root cause

2. **Baseline testing is critical**
   - Should have run baseline validation before implementing fixes
   - Would have caught regression earlier
   - Baseline metrics guide improvement validation

3. **Alpha tuning revealed RRF issue**
   - All alpha values producing identical accuracy = red flag
   - This finding suggests RRF implementation problem
   - Should investigate fusion logic immediately

4. **Table-aware chunking needs validation**
   - Large chunks may hurt semantic search
   - Need to balance: coherence vs semantic precision
   - May need hybrid approach: small chunks for text, large for tables

---

## Files Created/Modified

### Validation Scripts
- `scripts/debug-hybrid-search-scoring.py` - RRF score diagnostic
- `scripts/debug-rrf-single-query.py` - Single query trace
- `scripts/tune-bm25-fusion-weights.py` - Alpha tuning
- `scripts/analyze-auto-classification-accuracy.py` - Auto-classification analysis
- `scripts/run-phase2a-final-validation.py` - Final validation

### Source Code Changes
- `raglite/retrieval/search.py:fuse_search_results()` - RRF implementation (~175 lines)
- `raglite/retrieval/search.py:hybrid_search()` - Auto-classification disabled (line 417)

### Validation Results
- `docs/validation/story-2.11-bm25-tuning.json` - All alphas 18%
- `docs/validation/story-2.11-auto-classification-analysis.json` - 70.2% accuracy
- `docs/validation/phase2a-final-validation.json` - **18% final accuracy** ❌
- `docs/validation/story-2.11-debugging-summary.md` - Investigation log
- `docs/validation/story-2.11-phase2a-failure-analysis.md` - This document

---

## Recommendations

### ✅ ROOT CAUSE IDENTIFIED: See CRITICAL-ROOT-CAUSE-FOUND.md

**Discovery:** Table-aware chunking creates semantically indistinguishable chunks (all headers, data buried).

**Production-Proven Solution:** See Story 2.13 (SQL Table Search)

### Recommended Path: Story 2.13 (SQL Table Search) - Phase 2A-REVISED

**Rationale:** Production systems (Bloomberg, FinRAG, TableRAG, Salesforce) all use SQL for table queries

**Architecture:**
- **SQL database** for structured table queries (exact matching)
- **Vector search** for text queries (semantic similarity)
- **Query classifier** to route between SQL and vector (already implemented in Story 2.10!)

**Expected Accuracy:** 70-80% (FinRAG nDCG@10 0.804)

**Advantages over Phase 2B (Cross-Encoder):**
- **Simpler:** Reuse existing PostgreSQL + query classifier
- **Faster:** SQL <50ms vs cross-encoder 150-200ms
- **Production-Proven:** Battle-tested by Bloomberg, FinRAG, Salesforce

**Timeline:** 1-2 weeks (8 days)
**Risk:** LOW (production-validated approach)

### Alternative 1: Phase 2B Cross-Encoder Re-Ranking (Story 2.12)

**If SQL achieves <70%:**
- Add cross-encoder re-ranking layer
- Expected: +3-5pp accuracy improvement (75-80% total)
- Latency overhead: +150-200ms
- Timeline: 2-3 days

### Alternative 2: Revert to Baseline Chunking

**NOT RECOMMENDED:** Research shows 512-1024 token chunks optimal, but doesn't solve the fundamental problem (semantic search can't distinguish table headers)

**Timeline:** 15 min (re-ingest)
**Risk:** MEDIUM (may restore 56% baseline but doesn't achieve 70% target)

---

## Conclusion

Phase 2A implementation **failed** with a **-38pp regression** from baseline (18% vs 56%). The combination of RRF fusion and table-aware chunking appears to have degraded retrieval accuracy significantly.

**Critical finding:** All alpha values produce identical 18% accuracy, strongly suggesting an RRF implementation bug or BM25 index issue.

**Decision:** ESCALATE TO PHASE 2B pending PM approval and RRF investigation.

**Recommended Next Step:** Deep-dive RRF debugging to determine if implementation can be fixed, or if Phase 2B PostgreSQL + cross-encoder approach is required.

---

**Report Generated:** 2025-10-26 00:04 UTC
**Author:** Dev Agent (Amelia)
**Stakeholders:** PM, User, Architecture Team
