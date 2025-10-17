# Story 2.1: Hybrid Search (BM25 + Semantic Fusion)

**Status:** DRAFT (Ready for review)
**Epic:** 2 - Advanced RAG Enhancements
**Priority:** HIGH - Addresses keyword coverage gaps (44% of baseline failures)
**Duration:** 6-8 hours
**Assigned:** Dev Agent (Amelia)
**Prerequisites:** Epic 1 complete, tech stack approval for `rank_bm25`

---

## Story

**As a** user querying financial documents,
**I want** hybrid search combining keyword matching (BM25) with semantic search (Fin-E5),
**so that** queries with specific financial terms and numbers retrieve correct pages with high precision.

---

## Context

**Current State (Epic 1 Baseline - Story 1.15B):**
- ✅ Retrieval Accuracy: 56.0% (28/50 queries pass)
- ✅ Attribution Accuracy: 32.0% (16/50 queries pass)
- ✅ Performance: p50=33.20ms, p95=63.34ms
- ❌ NFR6 Target: 90%+ retrieval (34pp gap)
- ❌ NFR7 Target: 95%+ attribution (63pp gap)

**Baseline Failure Analysis (from Story 1.15B):**
- **Keyword coverage gaps:** 44% of failures (22/50 queries)
  - Example: "23.2 EUR/ton" not found in top-5 semantic results
  - Example: "EBITDA" terminology mismatch in embeddings
- **Page ranking issues:** 32% attribution failures (16/50 queries)
  - Correct content retrieved but wrong page prioritized

**Root Cause:** Single-stage semantic search insufficient for financial domain precision

**Solution:** Hybrid search combining BM25 (keyword precision) + Fin-E5 (semantic context)

---

## Research Foundation

**Based on:**
- BM25 Architecture Decision Record (`docs/epic-2-preparation/bm25-architecture-decision-record.md`)
- Financial Embedding Model Comparison (`docs/epic-2-preparation/financial-embedding-model-comparison.md`)

**Key Research Findings:**
1. **Qdrant v1.15+ supports sparse vectors** (BM25) via external computation
2. **rank_bm25 library** is industry-standard (used by LlamaIndex, Haystack, mem0ai, MetaGPT)
3. **Hybrid fusion strategies:** Weighted sum (alpha=0.7) OR Reciprocal Rank Fusion (RRF)
4. **BM25 parameters for financial docs:** k1=1.7, b=0.6 (tuned for dense technical content)
5. **Expected improvement:** +15-20% retrieval accuracy (based on ArXiv 2024 hybrid search benchmarks)

---

## Acceptance Criteria

### AC1: BM25 Index Creation (2 hours)

**Subtask 1.1: Install rank_bm25 library** (10 min)
- Add `rank-bm25` to `pyproject.toml`
- Run `uv add rank-bm25`
- Verify installation: `import rank_bm25`

**Subtask 1.2: Create BM25 index during ingestion** (45 min)
- Modify `raglite/ingestion/pipeline.py`
- After chunk creation, tokenize chunks for BM25
- Create BM25Okapi index with parameters: k1=1.7, b=0.6
- Store sparse vectors in Qdrant collection

**Code Pattern (from research):**
```python
from rank_bm25 import BM25Okapi

# Tokenize documents
tokenized_docs = [chunk.text.split() for chunk in chunks]

# Create BM25 index with financial document parameters
bm25 = BM25Okapi(tokenized_docs, k1=1.7, b=0.6)
```

**Subtask 1.3: Store BM25 sparse vectors in Qdrant** (45 min)
- Configure Qdrant collection with sparse vector support
- Generate BM25 sparse vectors (indices + values)
- Upsert points with both dense (Fin-E5) and sparse (BM25) vectors

**Configuration (from research):**
```python
from qdrant_client import models

client.create_collection(
    collection_name="financial_docs",
    vectors_config={
        "text-dense": models.VectorParams(
            size=1024,  # Fin-E5 dimension
            distance=models.Distance.COSINE,
        )
    },
    sparse_vectors_config={
        "text-sparse": models.SparseVectorParams(
            index=models.SparseIndexParams(on_disk=False),
        )
    }
)
```

**Subtask 1.4: Unit test BM25 indexing** (30 min)
- Test: BM25 index created with 321 chunks
- Test: Sparse vectors generated correctly
- Test: Parameters k1=1.7, b=0.6 applied

**Deliverables:**
- ✅ BM25 index functional
- ✅ Sparse vectors stored in Qdrant
- ✅ Unit tests passing

---

### AC2: Hybrid Search Query Implementation (2 hours)

**Subtask 2.1: Implement BM25 query** (45 min)
- Modify `raglite/retrieval/search.py`
- Add `hybrid_search()` function
- Query both dense (Fin-E5) and sparse (BM25) vectors
- Return separate result sets for fusion

**Code Pattern:**
```python
async def hybrid_search(
    query: str,
    top_k: int = 5,
    alpha: float = 0.7  # 70% semantic, 30% BM25
) -> List[SearchResult]:
    # BM25 query
    bm25_scores = bm25.get_scores(query.split())

    # Semantic query (existing)
    semantic_results = await semantic_search(query, top_k=20)

    # Fuse results
    hybrid_results = fuse_results(
        semantic_results, bm25_scores, alpha=alpha
    )

    return hybrid_results[:top_k]
```

**Subtask 2.2: Implement score fusion** (45 min)
- Implement weighted sum fusion (alpha=0.7)
- Normalize BM25 and semantic scores to [0, 1]
- Combine: `hybrid_score = alpha * semantic + (1 - alpha) * bm25`
- Sort and return top-k results

**Fusion Formula (from research):**
```python
def fuse_results(semantic_results, bm25_scores, alpha=0.7):
    # Normalize semantic scores (cosine similarity already [0, 1])
    semantic_norm = [r.score for r in semantic_results]

    # Normalize BM25 scores to [0, 1]
    bm25_max = max(bm25_scores)
    bm25_norm = [score / bm25_max if bm25_max > 0 else 0
                  for score in bm25_scores]

    # Weighted fusion
    hybrid_scores = [
        alpha * sem + (1 - alpha) * bm25
        for sem, bm25 in zip(semantic_norm, bm25_norm)
    ]

    return sorted(
        zip(semantic_results, hybrid_scores),
        key=lambda x: x[1],
        reverse=True
    )
```

**Subtask 2.3: Add configuration parameter** (15 min)
- Add `enable_hybrid` parameter to search functions
- Default: `enable_hybrid=True` (hybrid mode for production)
- Support fallback to semantic-only if BM25 unavailable

**Subtask 2.4: Unit test hybrid search** (15 min)
- Test: Hybrid search returns combined results
- Test: Alpha parameter affects ranking
- Test: Semantic-only fallback works

**Deliverables:**
- ✅ `hybrid_search()` function implemented
- ✅ Score fusion working (weighted sum, alpha=0.7)
- ✅ Unit tests passing

---

### AC3: BM25 Parameter Tuning (1 hour)

**Subtask 3.1: Baseline hybrid search test** (15 min)
- Run ground truth suite (50 queries) with k1=1.7, b=0.6, alpha=0.7
- Measure: Retrieval accuracy, attribution accuracy
- Document baseline hybrid performance

**Subtask 3.2: Tune k1 parameter** (15 min)
- Test k1 values: [1.5, 1.7, 2.0]
- Run 10-15 financial-heavy queries from ground truth
- Identify optimal k1 for retrieval accuracy

**Subtask 3.3: Tune b parameter** (15 min)
- Test b values: [0.5, 0.6, 0.7]
- Run 10-15 queries on documents with varying lengths
- Identify optimal b for attribution accuracy

**Subtask 3.4: Tune alpha (fusion weight)** (15 min)
- Test alpha values: [0.6, 0.7, 0.8]
- Measure retrieval accuracy for each
- Select alpha that maximizes retrieval + attribution

**Expected Optimal Values (from research):**
- k1: 1.5-2.0 (start 1.7)
- b: 0.5-0.7 (start 0.6)
- alpha: 0.6-0.8 (start 0.7)

**Deliverables:**
- ✅ Optimal BM25 parameters documented
- ✅ Optimal fusion alpha documented
- ✅ Tuning results in completion notes

---

### AC4: Integration with MCP Server (30 min)

**Subtask 4.1: Update MCP tool** (15 min)
- Modify `raglite/main.py` MCP tool
- Call `hybrid_search()` instead of `semantic_search()`
- Pass `enable_hybrid=True` by default

**Subtask 4.2: Integration test** (15 min)
- Test: MCP query returns hybrid search results
- Verify: Response format unchanged (backward compatible)
- Document: Hybrid mode enabled in MCP

**Deliverables:**
- ✅ MCP tool uses hybrid search
- ✅ Integration test passing

---

### AC5: Unit Tests (1 hour)

**Test Suite:** `tests/unit/test_hybrid_search.py` (NEW)

**Test 1: test_bm25_index_creation()** (15 min)
- Create BM25 index with 10 sample chunks
- Verify: Index created successfully
- Verify: Tokenization correct

**Test 2: test_bm25_query()** (15 min)
- Query BM25 index with "EBITDA"
- Verify: Scores returned for all chunks
- Verify: Relevant chunks ranked higher

**Test 3: test_score_fusion_weighted_sum()** (15 min)
- Mock semantic and BM25 scores
- Call fusion function with alpha=0.7
- Verify: Combined scores correct
- Verify: Top-k ranking correct

**Test 4: test_hybrid_search_end_to_end()** (15 min)
- Create test collection with 5 chunks
- Run hybrid search query
- Verify: Results include both semantic and BM25 matches
- Verify: Hybrid outperforms semantic-only

**Deliverables:**
- ✅ 4 unit tests passing
- ✅ Test coverage: BM25 indexing, querying, fusion, end-to-end

---

### AC6: Integration Tests (1 hour)

**Test Suite:** `tests/integration/test_hybrid_search_integration.py` (NEW)

**Test 1: test_hybrid_search_exact_numbers()** (20 min)
- Query: "What is the variable cost per ton?" (expects "23.2")
- Verify: Page 46 in top-3 results (BM25 should find "23.2")
- Measure: Improvement over semantic-only

**Test 2: test_hybrid_search_financial_terms()** (20 min)
- Query: "What is the EBITDA IFRS margin for Portugal Cement?"
- Verify: Page 46 in top-3 results (BM25 should find "EBITDA")
- Measure: Improvement over semantic-only

**Test 3: test_hybrid_search_full_ground_truth()** (20 min)
- Run full 50-query ground truth suite
- Measure: Retrieval accuracy with hybrid search
- Compare: Baseline (56%) vs hybrid (target: 71-76%)

**Success Criteria:**
- Retrieval accuracy ≥ 70% (baseline 56% + 14pp improvement)
- Attribution accuracy ≥ 45% (baseline 32% + 13pp improvement)

**Deliverables:**
- ✅ 3 integration tests passing
- ✅ Hybrid search accuracy improvement measured

---

### AC7: Performance Validation (30 min)

**Subtask 7.1: Latency benchmarking** (15 min)
- Run 10-query performance test
- Measure: p50, p95 latency with hybrid search
- Compare: Baseline (33ms p50) vs hybrid (target: <150ms p50)

**Subtask 7.2: NFR13 compliance check** (15 min)
- Verify: p95 latency < 10,000ms
- Document: Latency impact (+3-4x expected)
- Confirm: 9,935ms budget - 150ms hybrid = 9,785ms remaining ✅

**Expected Latency:**
- p50: ~100-150ms (3-4x increase from 33ms)
- p95: ~200-300ms (3-5x increase from 63ms)
- **Within NFR13 budget:** ✅ YES (9,785ms remaining)

**Deliverables:**
- ✅ Latency benchmarks documented
- ✅ NFR13 compliance verified

---

## Testing

**Unit Tests:**
- `tests/unit/test_hybrid_search.py` - 4 tests (BM25, fusion, hybrid search)

**Integration Tests:**
- `tests/integration/test_hybrid_search_integration.py` - 3 tests (exact numbers, financial terms, full ground truth)

**Performance Tests:**
- Latency benchmark: 10-query test (p50, p95 measurement)

**Regression Tests:**
- `tests/integration/test_epic2_regression.py` - Ensure no degradation below 56%/32% baseline

---

## Success Criteria

Story 2.1 is COMPLETE when:
1. ✅ BM25 index created and stored in Qdrant sparse vectors (AC1)
2. ✅ Hybrid search implemented with weighted sum fusion (AC2)
3. ✅ BM25 parameters tuned (k1, b, alpha optimal values documented) (AC3)
4. ✅ MCP tool uses hybrid search (AC4)
5. ✅ 4 unit tests passing (AC5)
6. ✅ 3 integration tests passing (AC6)
7. ✅ Retrieval accuracy ≥70% (target: 71-76%) (AC6)
8. ✅ p95 latency <10,000ms (NFR13 compliance) (AC7)

**Quality Gate:** AC6 (retrieval accuracy ≥70%) is mandatory for story completion.

---

## Deliverables

**Code Files:**
- `raglite/ingestion/pipeline.py` - BM25 index creation (+50 lines)
- `raglite/retrieval/search.py` - Hybrid search implementation (+120 lines)
- `tests/unit/test_hybrid_search.py` - Unit tests (NEW, 150 lines)
- `tests/integration/test_hybrid_search_integration.py` - Integration tests (NEW, 120 lines)

**Configuration:**
- `pyproject.toml` - Add `rank-bm25` dependency

**Documentation:**
- Completion notes - BM25 parameters, fusion alpha, accuracy improvement
- Tech stack update - Add `rank-bm25` to approved libraries table

---

## Decision Gate (After Story 2.1 Validation)

**Path 1: Retrieval ≥75%** (Likely)
- ✅ Strong improvement (+19pp from baseline 56%)
- Decision: Skip Story 2.2 (Fin-E5 already optimal), proceed to Story 2.3 if <90%

**Path 2: Retrieval 70-74%**
- ⚠️ Moderate improvement (+14-18pp)
- Decision: Evaluate Story 2.2 (Financial Embeddings) OR Story 2.3 (Table-Aware Chunking)

**Path 3: Retrieval <70%**
- ❌ Insufficient improvement (<+14pp)
- Decision: Investigate BM25 parameters, consider alternative fusion strategy (RRF)

---

## Rollback Plan

**Scenario 1: rank_bm25 approval denied**
- **Action:** Use Qdrant built-in BM25 (`fastembed_sparse_model="Qdrant/bm25"`)
- **Impact:** Less parameter control, acceptable fallback
- **Timeline:** No delay (alternative already researched)

**Scenario 2: Hybrid search accuracy <70%**
- **Action:** Debug BM25 parameters, test RRF fusion instead of weighted sum
- **Timeline:** +2-4 hours investigation
- **Escalation:** Architect review if no improvement

**Scenario 3: Latency exceeds 10s NFR13**
- **Action:** Optimize BM25 query, cache BM25 index, reduce top-k
- **Impact:** Unlikely (99.6% budget remaining)
- **Escalation:** Performance profiling if latency unexpectedly high

---

## Dependencies

**Prerequisites (Must Be Met):**
- ✅ Epic 1 complete (baseline 56%/32% established)
- ✅ Tech stack approval for `rank_bm25` (Task 3 from preparation sprint)
- ✅ BM25 Architecture Decision Record reviewed
- ✅ Testing infrastructure ready (Murat's tracking scripts)

**Blocks:**
- Story 2.2 (Financial Embeddings) - depends on Story 2.1 validation results
- Story 2.3 (Table-Aware Chunking) - depends on Story 2.1 accuracy

**Blocked By:**
- Tech stack approval for `rank_bm25` (BLOCKER - must approve before implementation)

---

## Key Files

**Input Files:**
- `docs/epic-2-preparation/bm25-architecture-decision-record.md` - BM25 technical guidance
- `tests/fixtures/ground_truth.py` - 50 test queries
- `baseline-accuracy-report-FINAL.txt` - Epic 1 baseline (56%/32%)

**Files to Modify:**
- `raglite/ingestion/pipeline.py` - BM25 index creation
- `raglite/retrieval/search.py` - Hybrid search implementation
- `raglite/main.py` - MCP tool integration
- `pyproject.toml` - Add rank-bm25 dependency

**Files to Create:**
- `tests/unit/test_hybrid_search.py` - Unit tests
- `tests/integration/test_hybrid_search_integration.py` - Integration tests
- Completion notes (in this file)

---

## Dev Notes

### Requirements Context

**Story Purpose:** Improve retrieval accuracy from 56% → 71-76% via hybrid search (BM25 + semantic)

**Why Story 2.1 Exists:**
- Baseline failure analysis: 44% failures due to keyword coverage gaps
- Financial domain: Exact numbers ("23.2") and terms ("EBITDA") critical
- Single-stage semantic search: Insufficient for precision retrieval

**Architecture Alignment:**
- Uses rank_bm25 library (industry-standard, KISS-compliant)
- Qdrant sparse vector support (native integration)
- Direct SDK usage (no custom wrappers or abstractions)
- Weighted sum fusion (simple, interpretable, fast)

**NFR Targets:**
- NFR6: 90%+ retrieval accuracy (Story 2.1 targets 71-76%, progress toward goal)
- NFR7: 95%+ attribution accuracy (Story 2.1 targets 45%, progress toward goal)
- NFR13: <10s p95 latency (Story 2.1 adds ~150ms, well within 9,935ms budget)

### Project Structure Notes

**Implementation Effort:** 6-8 hours
- BM25 indexing: 2 hours
- Hybrid search: 2 hours
- Parameter tuning: 1 hour
- MCP integration: 30 min
- Testing: 2 hours
- Validation: 30 min

**Expected Code Size:**
- `pipeline.py`: +50 lines (BM25 indexing)
- `search.py`: +120 lines (hybrid search, fusion)
- Unit tests: 150 lines
- Integration tests: 120 lines
- **Total: ~440 lines** (within Epic 2 scope)

### References

**Research Documents:**
- `docs/epic-2-preparation/bm25-architecture-decision-record.md`
- `docs/epic-2-preparation/financial-embedding-model-comparison.md`
- ArXiv:2508.01405v1 - Hybrid search trade-offs
- Weaviate Blog: "Hybrid Search Explained" (2025)

**Technology Documentation:**
- rank_bm25: https://github.com/dorianbrown/rank_bm25
- Qdrant sparse vectors: https://qdrant.tech/articles/sparse-vectors/
- BM25 algorithm: https://en.wikipedia.org/wiki/Okapi_BM25

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-16 | 1.0 | Story created from Epic 2 PRD with BM25 hybrid search approach (updated from post-search re-ranking to proper BM25 + semantic fusion based on research findings) | Scrum Master (Bob) |

---

## QA Results

*Results from QA review will be added here*

---

## Senior Developer Review (AI)

*To be completed after story execution*
