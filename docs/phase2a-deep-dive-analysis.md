# Phase 2A Deep Dive Analysis: Root Cause Investigation

**Document Version:** 1.0
**Date:** 2025-10-25
**Authors:** Development Team + Deep Investigation
**Status:** CRITICAL - Requires Immediate PM Review & Course Correction

---

## Executive Summary

**Problem Statement:**
Phase 2A implementation (Stories 2.3-2.7) achieved **52% accuracy**, showing **ZERO improvement** over the 56% baseline, with a -4pp regression. Expected improvement was +8-12pp (68-72% target).

**Gap from Expected Performance:** -16 to -20 percentage points

**Investigation Outcome:**
Comprehensive root cause analysis identified **FOUR CRITICAL ISSUES** that must be resolved before Phase 2A can succeed:

1. **Severe table fragmentation** (8.6 chunks per table)
2. **Broken ground truth validation** (zero page references)
3. **Over-aggressive query routing** (48% → SQL when only 4% should)
4. **Hybrid search score normalization bug** (artificial 1.0 scores)

**Recommendation:**
**DO NOT proceed to Phase 2B** until Phase 2A core issues are resolved. The problems are architectural and data quality, not missing features.

---

## Investigation Timeline

### Session Context

This investigation followed multiple failed attempts to achieve Phase 2A accuracy improvements:

1. **Initial Phase 2A Implementation** (Stories 2.3-2.7)
   - Fixed 512-token chunking
   - LLM metadata extraction (94-99% success rate)
   - PostgreSQL structured storage (1,592 chunks)
   - Multi-index search orchestration
   - Result: 52% accuracy (no improvement)

2. **First Root Cause Discovery** - PostgreSQL Full-Text Search Issues
   - Missing tsvector trigger (100% NULL values) → **FIXED**
   - Test harness not using multi-index search → **FIXED**
   - Strict AND logic in plainto_tsquery() → **PARTIALLY FIXED**

3. **Second Root Cause Discovery** - Query Preprocessing
   - Temporal/keyword mismatch ("August 2025" vs "Aug-25 YTD")
   - Implemented query preprocessing with metadata filters → **IMPLEMENTED**
   - Result: 52% → 46% regression (-6pp)

4. **Third Root Cause Discovery** - Test Harness Function Mismatch
   - Tests switched from `search_documents()` to `hybrid_search()`
   - Hybrid search has different ranking behavior
   - Identified need for deeper analysis → **TRIGGERED ULTRATHINK**

5. **Ultra-Deep Analysis** (Current)
   - Comprehensive multi-dimensional investigation
   - Identified 4 critical root causes
   - Provided actionable recommendations

---

## Root Cause #1: Severe Table Fragmentation 🔴 CRITICAL

### Discovery

**Evidence:**
```
Table Chunking Analysis:
  Total table chunks: 1466
  Unique tables: 171
  Average table chunk size: 3428 chars
  Chunks per table: 8.6  ← CRITICAL FRAGMENTATION
```

**Analysis:**
- Fixed 512-token chunking splits tables across **8.6 chunks on average**
- Financial tables contain related data (headers, row labels, values, units)
- Splitting destroys semantic coherence of tabular data

### Impact on Accuracy

**Why This Causes 52% Plateau:**

1. **Fragmented Context:**
   - Query: "What is the EBITDA margin in August 2025?"
   - Chunk 1: Contains column headers "EBITDA | Margin | %"
   - Chunk 2: Contains row label "August 2025"
   - Chunk 3: Contains the actual value "23.4%"
   - Chunk 4: Contains units and notes

2. **Semantic Search Fails:**
   - Vector embeddings for fragments lack full table context
   - LLM cannot reconstruct table relationships from fragments
   - High-scoring chunks may not contain the answer

3. **Metadata Extraction Degrades:**
   - LLM sees partial tables during metadata extraction
   - Cannot accurately determine metric category from header fragments
   - Temporal information may be in different chunk than metric

### Recommendation

**Solution:** Implement table-aware chunking strategy

**Approach:**
1. **Table Detection:** Keep complete tables as single chunks (up to 4096 tokens)
2. **Table Splitting:** Only split if table exceeds model context window
   - Split by logical rows (preserve column headers in each chunk)
   - Add table context prefix to each chunk
3. **Non-Table Content:** Use existing 512-token fixed chunking

**Story Requirements:**
- Story 2.8: "Implement Table-Aware Chunking Strategy"
- Estimated Effort: 6-8 hours
- Dependencies: None (can implement immediately)
- Acceptance Criteria:
  - AC1: Tables <4096 tokens kept intact (single chunk)
  - AC2: Large tables split by rows, headers preserved
  - AC3: Re-ingestion reduces chunks per table from 8.6 → 1.2
  - AC4: Accuracy improvement validated (expect +10-15pp)

**Implementation Notes:**
```python
# Pseudocode for table-aware chunking
def chunk_document(doc):
    chunks = []
    for element in doc.elements:
        if element.type == 'table':
            if token_count(element) < 4096:
                # Keep table intact
                chunks.append(element)
            else:
                # Split by rows, preserve headers
                chunks.extend(split_table_by_rows(element))
        else:
            # Use fixed 512-token chunking for text
            chunks.extend(fixed_chunk(element, size=512))
    return chunks
```

**Files to Modify:**
- `raglite/ingestion/pipeline.py` (add table-aware logic)
- `raglite/ingestion/contextual.py` (update chunking strategy)

---

## Root Cause #2: Broken Ground Truth Validation 🔴 CRITICAL

### Discovery

**Evidence:**
```
Ground Truth Statistics:
  Total queries: 50
  Unique pages referenced: 0  ← NO PAGE VALIDATION!
  Unique documents referenced: 1
```

**Analysis:**
- Ground truth file `tests/fixtures/ground_truth.py` has **ZERO expected page references**
- Accuracy tests cannot validate if correct pages are retrieved
- The 52% metric measures something different than intended

### Impact on Accuracy Measurement

**Why This Invalidates All Results:**

1. **No Page-Level Validation:**
   ```python
   # Current ground truth structure (BROKEN)
   {
       "id": 1,
       "question": "What is the EBITDA margin?",
       "category": "metrics",
       "source_document": "financial_report.pdf",
       "expected_pages": []  # ← EMPTY!
   }
   ```

2. **Cannot Measure Retrieval Accuracy:**
   - Tests show "correct: 10" for all sample queries
   - No way to know if Phase 2A improvements work
   - 52% metric may be measuring LLM synthesis, not retrieval

3. **Wasted Development Effort:**
   - Hours spent debugging retrieval issues
   - Cannot validate if PostgreSQL table search helps
   - Cannot measure multi-index search effectiveness

### Recommendation

**Solution:** Fix ground truth with proper page references

**Approach:**
1. **Manual Annotation:** Review financial PDF and add page numbers for each query
2. **Validation:** Ensure pages contain actual answers
3. **Coverage:** Verify all 50 queries have page references

**Story Requirements:**
- Story 2.9: "Fix Ground Truth Page References"
- Estimated Effort: 3-4 hours (manual annotation)
- Dependencies: Access to source PDF
- Acceptance Criteria:
  - AC1: All 50 queries have `expected_pages` populated
  - AC2: Page references validated against PDF content
  - AC3: Accuracy test suite validates page-level retrieval
  - AC4: Baseline re-run with correct validation

**Implementation Example:**
```python
# Fixed ground truth structure
{
    "id": 1,
    "question": "What is the EBITDA margin for Portugal Cement in August 2025?",
    "category": "metrics",
    "source_document": "financial_report_aug2025.pdf",
    "expected_pages": [45, 133],  # ← REQUIRED!
    "expected_answer_contains": ["23.4%", "EBITDA", "Portugal"]
}
```

**Files to Modify:**
- `tests/fixtures/ground_truth.py` (add page references)
- `scripts/accuracy_utils.py` (validate page-level accuracy function)

---

## Root Cause #3: Over-Aggressive Query Classification 🟡 HIGH

### Discovery

**Evidence:**
```
Query Routing Distribution:
  sql_only: 24 (48.0%)  ← OVER-ROUTING
  vector_only: 22 (44.0%)
  hybrid: 4 (8.0%)

Routing Correctness Analysis:
  Queries with temporal info: 2 (4%)  ← ACTUAL NEED
  Queries routed to SQL: 24 (48%)  ← 12x TOO MANY
```

**Analysis:**
- Heuristic classifier in `query_classifier.py` routes 48% to SQL_ONLY
- But only 4% of queries have temporal qualifiers requiring SQL
- 44% of queries incorrectly routed to SQL

### Impact on Performance

**Why This Hurts Accuracy:**

1. **Failed SQL Searches:**
   - SQL-routed queries return 0 results (PostgreSQL search fails)
   - Falls back to vector search, adding 500-1000ms latency
   - User sees: "SQL search returned no results, falling back to vector search"

2. **Query Preprocessing Applied Incorrectly:**
   - Stopword removal ("What is the") designed for SQL queries
   - Applied to non-temporal queries, removing useful context
   - Example: "What are the raw materials costs?" → "are raw materials costs"

3. **Wasted PostgreSQL Resources:**
   - 44% of queries unnecessarily hit PostgreSQL
   - Connection overhead + query planning for zero results
   - Database load for no benefit

### Recommendation

**Solution:** Fix query classification heuristics

**Approach:**
1. **Tighten SQL Routing:**
   - Only route if explicit temporal terms present ("August 2025", "Q3 2024")
   - Require both metric + temporal for SQL_ONLY
   - Default to HYBRID for uncertain cases

2. **Improve Heuristics:**
   ```python
   # Current (BROKEN)
   if any(metric in query for metric in FINANCIAL_METRICS):
       return QueryType.SQL_ONLY  # Too broad!

   # Fixed (CORRECT)
   has_metric = any(metric in query for metric in FINANCIAL_METRICS)
   has_temporal = any(term in query for term in TEMPORAL_TERMS)

   if has_metric and has_temporal:
       return QueryType.HYBRID  # Use both indexes
   elif has_metric:
       return QueryType.VECTOR_ONLY  # Semantic search sufficient
   ```

3. **Add Logging:**
   - Log routing decisions for debugging
   - Track SQL fallback rate (should be <5%)

**Story Requirements:**
- Story 2.10: "Fix Query Classification Over-Routing"
- Estimated Effort: 3-4 hours
- Dependencies: None
- Acceptance Criteria:
  - AC1: SQL_ONLY routing reduced from 48% → 8% (temporal queries only)
  - AC2: HYBRID routing increased to 50%+ (most queries)
  - AC3: SQL fallback rate <5%
  - AC4: Average query latency reduced by 300-500ms

**Files to Modify:**
- `raglite/retrieval/query_classifier.py` (fix classification logic)
- `raglite/retrieval/multi_index_search.py` (add routing metrics logging)

---

## Root Cause #4: Hybrid Search Score Normalization Bug 🟡 MEDIUM

### Discovery

**Evidence:**
```
Method Comparison:
  semantic:    score=0.872 | pages=[133, 71, 43]
  hybrid:      score=1.000 | pages=[69, 70, 72]  ← SUSPICIOUS
  multi_index: score=1.000 | pages=[69, 70, 72]  ← SUSPICIOUS
```

**Analysis:**
- Hybrid search and multi-index search always return `score=1.000`
- Pure semantic search returns realistic scores (0.802-0.872)
- Different pages returned between methods → ranking has changed

### Impact on Ranking Quality

**Why This Causes 52% → 46% Regression:**

1. **BM25 Fusion Degradation:**
   - Hybrid search uses 70% semantic + 30% BM25 fusion
   - BM25 may be upranking wrong chunks (keyword matches over semantics)
   - Score normalization hides actual relevance scores

2. **Auto-Classification Extracting Wrong Filters:**
   - `hybrid_search(auto_classify=True)` extracts metadata filters
   - LLM may extract incorrect filters from queries
   - Hard filters eliminate correct chunks

3. **Lost Visibility:**
   - Score=1.0 for all results prevents debugging
   - Cannot tune fusion weights without real scores
   - Cannot identify which search method performs better

### Recommendation

**Solution:** Debug and fix hybrid search scoring

**Approach:**
1. **Investigate Score Normalization:**
   - Find where scores are being set to 1.0
   - Preserve raw fusion scores for analysis
   - Add logging for score components (semantic vs BM25)

2. **Tune BM25 Fusion Weights:**
   - Current: alpha=0.7 (70% semantic, 30% BM25)
   - Test: alpha=0.85 (reduce BM25 influence)
   - Validate on ground truth queries

3. **Review Auto-Classification:**
   - Log extracted filters for debugging
   - Compare auto-classified vs manual filters
   - Consider disabling auto-classification (use explicit filters only)

**Story Requirements:**
- Story 2.11: "Fix Hybrid Search Score Normalization & Fusion"
- Estimated Effort: 4-6 hours
- Dependencies: Story 2.9 (ground truth fix for validation)
- Acceptance Criteria:
  - AC1: Hybrid search returns realistic scores (not 1.0)
  - AC2: BM25 fusion weight tuned (test 0.7, 0.8, 0.85)
  - AC3: Auto-classification accuracy >80% or disabled
  - AC4: Hybrid search matches or exceeds semantic baseline

**Files to Modify:**
- `raglite/retrieval/search.py` (fix `hybrid_search()` scoring)
- `raglite/retrieval/multi_index_search.py` (fix `merge_results()` fusion)

---

## Additional Context: What We Fixed (But Didn't Help)

### PostgreSQL Full-Text Search Issues ✅ RESOLVED

**Issues Fixed:**
1. **Missing tsvector trigger** - 100% NULL content_tsv values
   - Created trigger function and backfilled 1,592 rows
   - Verification: Full-text search now works (169 'variable cost' matches)

2. **Test harness not using multi-index search**
   - Updated `run-accuracy-tests.py` to call `multi_index_search()`
   - Proper SearchResult → QueryResult conversion

3. **Temporal format mismatch**
   - Implemented query preprocessing (`query_preprocessing.py`)
   - Extracts keywords and temporal filters
   - Normalizes "August 2025" → "Aug-25%" for LIKE matching
   - Added LIKE pattern support in `search_tables_with_metadata_filter()`

**Why These Didn't Improve Accuracy:**
- PostgreSQL search works correctly NOW
- But underlying issues (table fragmentation, broken ground truth) prevent gains
- Query preprocessing validated: 2/3 test queries return results
- Multi-index search correctly implemented but cannot compensate for fragmented data

**Files Modified:**
- `scripts/fix-tsvector-trigger.py` (new)
- `raglite/retrieval/query_preprocessing.py` (new)
- `raglite/structured/table_retrieval.py` (added LIKE support)
- `raglite/retrieval/multi_index_search.py` (integrated preprocessing)
- `scripts/run-accuracy-tests.py` (switched to multi-index search)

---

## Revised Phase 2A Implementation Plan

### Current State

**Completed Stories:**
- ✅ Story 2.3: Fixed 512-token chunking (ISSUE: causes table fragmentation)
- ✅ Story 2.4: LLM metadata extraction (94-99% success - WORKING WELL)
- ✅ Story 2.6: PostgreSQL structured storage (1,592 chunks - WORKING)
- ✅ Story 2.7: Multi-index search orchestration (IMPLEMENTED, needs tuning)

**Result:** 52% accuracy (no improvement, -4pp vs baseline)

### Required Fixes (Course Correction)

**NEW Stories Required:**

| Story | Title | Effort | Priority | Dependency |
|-------|-------|--------|----------|------------|
| 2.8 | Implement Table-Aware Chunking Strategy | 6-8h | CRITICAL | None |
| 2.9 | Fix Ground Truth Page References | 3-4h | CRITICAL | None |
| 2.10 | Fix Query Classification Over-Routing | 3-4h | HIGH | None |
| 2.11 | Fix Hybrid Search Score Normalization & Fusion | 4-6h | MEDIUM | Story 2.9 |

**Total Estimated Effort:** 16-22 hours (2-3 days)

### Expected Outcomes After Fixes

**Story 2.8 (Table-Aware Chunking):**
- Chunks per table: 8.6 → 1.2
- Semantic coherence restored
- Expected accuracy gain: +10-15pp

**Story 2.9 (Ground Truth Fix):**
- Proper validation enabled
- Can measure actual retrieval accuracy
- Confidence in metrics restored

**Story 2.10 (Query Classification):**
- SQL routing: 48% → 8%
- Latency reduction: -300-500ms p50
- Fewer failed searches

**Story 2.11 (Hybrid Search Fix):**
- BM25 fusion tuned for financial queries
- Score visibility restored
- Expected accuracy: match or exceed semantic baseline

**Combined Expected Result:** **65-75% accuracy** (Phase 2A target range)

---

## Comparison: Phase 2A vs Phase 2B

### Phase 2A (Current - After Fixes)

**Approach:** Fixed chunking + metadata + PostgreSQL tables + multi-index

**Pros:**
- Simpler architecture (no Neo4j)
- Lower operational complexity
- Metadata extraction already working (94-99%)
- PostgreSQL infrastructure in place

**Cons:**
- Requires table-aware chunking (NEW work)
- Limited relationship modeling
- May plateau at 70-75%

**Risk:** Medium (fixes are straightforward)

### Phase 2B (Alternative - If Phase 2A Fails)

**Approach:** Neo4j graph + PostgreSQL tables + Qdrant vectors

**Pros:**
- Explicit relationship modeling
- Research shows 75-92% accuracy potential
- Better for complex multi-hop queries

**Cons:**
- High complexity (3 databases)
- Significant new infrastructure
- 6-week implementation
- High operational cost

**Risk:** High (complex architecture, untested integration)

### Recommendation

**Proceed with Phase 2A fixes FIRST:**
1. Table-aware chunking is necessary regardless of Phase 2B
2. Ground truth fix required for any validation
3. Query classification fix is quick win
4. If Phase 2A achieves 65-75%, meets minimum requirements
5. Only proceed to Phase 2B if fixes yield <70%

---

## Action Items for PM

### Immediate Actions (Next 24 hours)

1. **Review this analysis document**
   - Validate root causes
   - Approve course correction
   - Confirm revised stories

2. **Create new stories in backlog**
   - Story 2.8: Table-Aware Chunking
   - Story 2.9: Ground Truth Fix
   - Story 2.10: Query Classification Fix
   - Story 2.11: Hybrid Search Fix

3. **Update sprint plan**
   - Pause Phase 2B planning
   - Prioritize Phase 2A fixes
   - Allocate 2-3 days for implementation

### Decision Gates

**After Story 2.8 + 2.9 Complete:**
- Re-run accuracy tests with fixed ground truth
- Measure table-aware chunking impact
- **Decision:** If <65% accuracy → proceed to Stories 2.10-2.11
- **Decision:** If ≥70% accuracy → Phase 2A SUCCESS

**After All Fixes Complete:**
- **Decision:** If ≥70% accuracy → Epic 2 COMPLETE, proceed to Epic 3
- **Decision:** If 65-70% accuracy → Re-evaluate Phase 2B need
- **Decision:** If <65% accuracy → Escalate to Phase 2B planning

---

## Supporting Evidence

### Diagnostic Scripts Created

All diagnostic scripts available in `scripts/` directory:

1. **`fix-tsvector-trigger.py`** - Fixed PostgreSQL tsvector issue
2. **`test-websearch-tsquery.py`** - Validated query preprocessing
3. **`test-query-preprocessing.py`** - Tested metadata filtering
4. **`analyze-chunk-content.py`** - Investigated chunk-query mismatch
5. **`diagnose-tsquery.py`** - Analyzed full-text search behavior
6. **`debug-accuracy-regression.py`** - Traced 52%→46% regression
7. **`ultrathink-phase2a-baseline.py`** - Comprehensive root cause analysis

### Key Metrics

**Database Statistics:**
- Total chunks: 1,592
- Unique pages: 141
- Chunks with metadata: 1,451 (91.1%)
- Average chunk size: 3,583 chars
- Table chunks: 1,466 (92%)
- Chunks per table: 8.6 ← **CRITICAL ISSUE**

**Query Statistics:**
- Total queries: 50
- Temporal queries: 2 (4%)
- SQL-routed queries: 24 (48%) ← **OVER-ROUTING**
- Metric-specific: 27 (54%)
- Geographic-specific: 5 (10%)

**Accuracy Results:**
- Baseline (semantic): 56%
- Phase 2A (multi-index): 52%
- Regression: -4pp
- Gap from expected: -16 to -20pp

---

## Conclusion

Phase 2A's failure to improve accuracy is due to **four specific, fixable issues**:

1. **Table fragmentation** (8.6 chunks/table) prevents semantic coherence
2. **Broken ground truth** (zero page refs) prevents proper validation
3. **Over-routing to SQL** (48% vs 4%) causes latency and fallbacks
4. **Hybrid search bugs** mask ranking degradation

**None of these require Phase 2B's complex architecture to fix.**

Implementing Stories 2.8-2.11 (16-22 hours) should achieve **65-75% accuracy**, meeting Phase 2A objectives and unblocking Epic 3 development.

**Recommendation: Implement fixes before considering Phase 2B.**

---

## Appendix: File Inventory

### New Files Created During Investigation

**Scripts:**
- `scripts/fix-tsvector-trigger.py`
- `scripts/test-websearch-tsquery.py`
- `scripts/test-query-preprocessing.py`
- `scripts/analyze-chunk-content.py`
- `scripts/diagnose-tsquery.py`
- `scripts/debug-accuracy-regression.py`
- `scripts/ultrathink-phase2a-baseline.py`

**Source Code:**
- `raglite/retrieval/query_preprocessing.py` (new module)

### Modified Files

**Core Retrieval:**
- `raglite/structured/table_retrieval.py` (added LIKE pattern support)
- `raglite/retrieval/multi_index_search.py` (integrated query preprocessing)

**Testing:**
- `scripts/run-accuracy-tests.py` (switched to multi-index search)

### Files Requiring Future Changes

**For Story 2.8 (Table-Aware Chunking):**
- `raglite/ingestion/pipeline.py` (add table detection logic)
- `raglite/ingestion/contextual.py` (implement table-aware strategy)

**For Story 2.9 (Ground Truth Fix):**
- `tests/fixtures/ground_truth.py` (add page references)
- `scripts/accuracy_utils.py` (validate page-level accuracy)

**For Story 2.10 (Query Classification):**
- `raglite/retrieval/query_classifier.py` (fix classification logic)
- `raglite/retrieval/multi_index_search.py` (add routing metrics)

**For Story 2.11 (Hybrid Search Fix):**
- `raglite/retrieval/search.py` (fix hybrid_search() scoring)
- `raglite/retrieval/multi_index_search.py` (fix merge_results() fusion)

---

**End of Document**

*This analysis represents comprehensive investigation of Phase 2A performance issues and provides actionable path forward for course correction.*
