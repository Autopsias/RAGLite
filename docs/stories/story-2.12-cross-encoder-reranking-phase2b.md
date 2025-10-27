# Story 2.12: Cross-Encoder Re-Ranking (Phase 2B Fallback)

Status: ON HOLD - Awaiting Story 2.13 Validation

**⚠️ CONDITIONAL STORY:** Only implement if Story 2.13 (SQL Table Search) achieves <70% retrieval accuracy.

**Context Update (2025-10-26):**
Phase 2A failed with 18% accuracy due to semantic search being unable to distinguish tables with identical headers. Story 2.13 (SQL Table Search) is now the primary path (expected 70-80% accuracy based on production evidence from FinRAG, Bloomberg, Salesforce). This story (cross-encoder re-ranking) serves as a fallback to add +3-5pp improvement if Story 2.13 achieves <70%.

**Dependencies:**
- ✅ Story 2.13 must be validated first
- ✅ Story 2.7 (Multi-Index Search) complete
- Trigger condition: Story 2.13 accuracy <70%

**NOTE:** This story was originally numbered 2.8 but renumbered to 2.12 to accommodate Phase 2A course correction stories (2.8-2.11) identified in the Phase 2A Deep Dive Analysis (2025-10-25).

## Story

As a **RAG retrieval system**,
I want **two-stage retrieval with cross-encoder re-ranking of multi-index search results**,
so that **precision improves from 70-75% to 75-80% by applying joint attention scoring to top candidates**.

## Context

Story 2.12 is part of **Epic 2 Phase 2B: Structured Multi-Index** (CONDITIONAL - only triggered if Phase 2A achieves <70% accuracy even after Stories 2.8-2.11 course correction). This story adds a second-stage re-ranking layer on top of Story 2.7's multi-index search architecture.

**Dependencies:**
- ✅ Story 2.7 complete (Multi-Index Search Architecture operational)
- ✅ Story 2.6 complete (PostgreSQL table extraction and storage)

**Strategic Rationale:**
Cross-encoder re-ranking provides joint attention between query and document, offering higher precision than bi-encoder (Fin-E5) semantic search alone. Research evidence (T₂-RAGBench, MS MARCO) demonstrates +3-5% precision improvement with ~150-200ms latency overhead. This is the final optimization step in Phase 2B before AC3 validation (Story 2.9).

**Two-Stage Retrieval Pipeline:**
1. **Stage 1 (Fast):** Multi-index search retrieves top-20 candidates (~3s p95)
2. **Stage 2 (Accurate):** Cross-encoder re-ranks top-20 → top-5 (~150-200ms)

This approach balances speed (stage 1) with precision (stage 2), keeping total latency well within NFR13 (<15s p95).

## Acceptance Criteria

### AC1: Cross-Encoder Model Integration (4 hours)

**Goal:** Integrate sentence-transformers cross-encoder model for re-ranking

**Technical Specifications:**
- Create `raglite/retrieval/reranker.py` (~100 lines)
- Main function: `rerank_results(query: str, results: List[SearchResult], top_k: int = 5) -> List[SearchResult]`
- Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Input: Query + top-20 results from multi-index search (Story 2.7)
- Output: Re-ranked top-k results with cross-encoder scores

**Model Details:**
- **Architecture:** MiniLM-L-6 (6-layer transformer)
- **Training:** MS MARCO passage ranking dataset
- **Size:** ~82MB (lightweight, suitable for MVP)
- **Performance:** 150-200ms for 20 documents @ batch_size=8

**Implementation:**
```python
from sentence_transformers import CrossEncoder
from typing import List
from raglite.retrieval.multi_index_search import SearchResult

class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize cross-encoder re-ranker."""
        self.model = CrossEncoder(model_name)

    async def rerank_results(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 5
    ) -> List[SearchResult]:
        """Re-rank search results using cross-encoder.

        Args:
            query: User query string
            results: Initial search results from multi-index search
            top_k: Number of top results to return after re-ranking

        Returns:
            Re-ranked results with updated scores
        """
        # Create query-document pairs
        pairs = [(query, result.text) for result in results]

        # Score pairs with cross-encoder (joint attention)
        scores = self.model.predict(pairs)

        # Update result scores and re-rank
        for result, score in zip(results, scores):
            result.score = float(score)
            result.metadata["reranker_score"] = float(score)

        # Sort by cross-encoder score and return top-k
        reranked = sorted(results, key=lambda r: r.score, reverse=True)
        return reranked[:top_k]
```

**Validation:**
- Unit tests: Re-rank 20 mock results, verify top-k ordering
- Model loading: <5s on first initialization (cached afterward)
- Batch processing: Process 20 documents in single batch

**Success Criteria:**
- ✅ Cross-encoder model loaded successfully
- ✅ Re-ranking function returns top-k results
- ✅ Scores updated correctly (cross-encoder scores replace fusion scores)
- ✅ Model initialization <5s

---

### AC2: Integration with Multi-Index Search (4 hours)

**Goal:** Integrate re-ranker as post-processing step in multi-index search pipeline

**Technical Specifications:**
- Update `raglite/retrieval/multi_index_search.py` (+50 lines)
- Modify `multi_index_search()` to retrieve top-20, then re-rank to top-k
- Add configuration flag: `use_reranker: bool = True` (default enabled)

**Modified Pipeline:**
```python
async def multi_index_search(
    query: str,
    top_k: int = 5,
    use_reranker: bool = True
) -> List[SearchResult]:
    """Multi-index search with optional cross-encoder re-ranking.

    Args:
        query: Natural language query
        top_k: Final number of results to return
        use_reranker: If True, apply cross-encoder re-ranking

    Returns:
        Search results (re-ranked if use_reranker=True)
    """
    # Stage 1: Multi-index search (retrieve top-20 for re-ranking)
    retrieval_k = 20 if use_reranker else top_k
    results = await _execute_multi_index_search(query, retrieval_k)

    # Stage 2: Cross-encoder re-ranking (if enabled)
    if use_reranker and len(results) > top_k:
        logger.info("Applying cross-encoder re-ranking", extra={
            "initial_results": len(results),
            "target_top_k": top_k
        })
        reranker = get_reranker()  # Singleton pattern
        results = await reranker.rerank_results(query, results, top_k)

    return results[:top_k]
```

**Fallback Logic:**
- If cross-encoder fails, return top-k from stage 1 (multi-index fusion scores)
- Log re-ranking errors but don't crash the query pipeline
- Graceful degradation: `use_reranker=False` disables re-ranking

**Validation:**
- Integration tests: End-to-end query with re-ranking enabled
- Test fallback: Mock re-ranker failure, verify top-k returned from stage 1
- Test configuration: `use_reranker=False` skips re-ranking step

**Success Criteria:**
- ✅ Multi-index search returns top-20 candidates
- ✅ Re-ranker processes top-20 → top-k
- ✅ Fallback logic functional (re-ranker failure → stage 1 results)
- ✅ Configuration flag toggles re-ranking on/off

---

### AC3: MCP Tool Integration and Observability (2 hours)

**Goal:** Update MCP tool to support re-ranking and add observability metrics

**Technical Specifications:**
- Update `raglite/main.py` (modify existing tool, ~20 lines)
- Add `use_reranker` parameter to `QueryRequest` model
- Track re-ranking metrics in structured logs

**QueryRequest Update:**
```python
class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    top_k: int = Field(5, description="Number of results to return")
    use_reranker: bool = Field(True, description="Apply cross-encoder re-ranking")
```

**MCP Tool Update:**
```python
@mcp.tool()
async def query_financial_documents(request: QueryRequest) -> QueryResponse:
    """Query financial documents with multi-index search and re-ranking."""

    logger.info("Query received", extra={
        "query": request.query,
        "top_k": request.top_k,
        "use_reranker": request.use_reranker
    })

    # Multi-index search with optional re-ranking
    results = await multi_index_search(
        request.query,
        request.top_k,
        use_reranker=request.use_reranker
    )

    # Log retrieval metrics
    logger.info("Retrieval complete", extra={
        "result_count": len(results),
        "reranker_applied": request.use_reranker,
        "top_score": results[0].score if results else None
    })

    # Existing synthesis logic unchanged
    answer = await synthesize_answer(request.query, results)

    return QueryResponse(
        answer=answer,
        sources=[r.metadata for r in results],
        retrieval_method="multi-index-reranked" if request.use_reranker else "multi-index"
    )
```

**Observability Metrics:**
- Log re-ranking decision: `{"reranker_applied": true/false}`
- Log latency breakdown: `{"stage1_ms": 3200, "stage2_rerank_ms": 180}`
- Track score changes: `{"pre_rerank_score": 0.72, "post_rerank_score": 0.89}`

**Validation:**
- Integration test: MCP query with `use_reranker=true` and `use_reranker=false`
- Verify logging includes re-ranking metrics
- Test backward compatibility (existing clients default to re-ranking enabled)

**Success Criteria:**
- ✅ MCP tool parameter `use_reranker` functional
- ✅ Observability logging includes re-ranking metrics
- ✅ Backward compatibility maintained (default=True)
- ✅ End-to-end MCP test passing

---

### AC4: Performance Validation (4 hours)

**Goal:** Validate re-ranking meets NFR13 performance requirements

**Performance Targets:**
- Re-ranking latency <250ms for 20 documents (p95)
- Total query latency <15s (p95, NFR13 compliance)
- Re-ranking overhead <5% of total query time

**Test Methodology:**
- Run 50 ground truth queries with re-ranking enabled
- Measure latency breakdown:
  - Stage 1: Multi-index search time (~3s p95)
  - Stage 2: Re-ranking time (target <250ms p95)
  - Synthesis time (~10s p95)
  - Total end-to-end time (target <15s p95)

**Benchmark Queries:**
- 20 SQL-heavy queries (table lookups)
- 20 semantic text queries
- 10 hybrid queries (combined retrieval)

**Latency Budget with Re-Ranking:**
```
Stage 1 (Multi-index search):  <3s   (p95) [AC2 from Story 2.7]
Stage 2 (Re-ranking):          <250ms (p95) [NEW - Story 2.8]
Synthesis (Claude):            <10s  (p95) [Existing baseline]
---------------------------------------------------------
Total:                         <15s  (p95) [NFR13 COMPLIANT]
```

**Validation:**
- Measure p50, p95, p99 latency for all 50 queries
- Document re-ranking overhead vs no-reranking baseline
- Identify any queries exceeding 250ms re-ranking threshold

**Success Criteria:**
- ✅ p95 re-ranking latency <250ms
- ✅ p95 total query latency <15s (NFR13 compliance)
- ✅ Re-ranking overhead <5% of total query time
- ✅ Performance report documented

---

### AC5: Accuracy Improvement Validation (4 hours)

**Goal:** Validate re-ranking improves retrieval accuracy

**Accuracy Targets:**
- **Baseline (Story 2.7):** 70-75% retrieval accuracy (multi-index fusion)
- **Target (Story 2.8):** 75-80% retrieval accuracy (+3-5pp improvement)

**Test Methodology:**
- Run 50 ground truth queries with and without re-ranking
- Compare accuracy:
  - **Without re-ranking:** Top-5 from multi-index fusion
  - **With re-ranking:** Top-5 after cross-encoder re-ranking
- Measure:
  - Retrieval accuracy (% queries with correct chunk in top-5)
  - Precision@5 (% relevant results in top-5)
  - Mean Reciprocal Rank (MRR)

**Expected Results:**
```
Metric                  | Without Re-ranking | With Re-ranking | Δ
-----------------------|-------------------|-----------------|--------
Retrieval Accuracy     | 70-75%            | 75-80%          | +3-5pp
Precision@5            | 0.65-0.70         | 0.70-0.75       | +0.05
MRR                    | 0.68-0.73         | 0.73-0.78       | +0.05
```

**Research Evidence:**
- T₂-RAGBench (2024): Cross-encoder re-ranking +5-10% precision over bi-encoders
- MS MARCO (2024): MiniLM cross-encoder +3-5% MRR improvement
- FinSage (Snowflake AI): Re-ranking critical for financial domain precision

**Validation:**
- A/B test: 25 queries without re-ranking vs 25 queries with re-ranking
- Statistical significance: p-value <0.05 (paired t-test)
- Failure analysis: Document any queries with accuracy regression

**Success Criteria:**
- ✅ Retrieval accuracy improvement ≥3pp (75%+ target)
- ✅ Precision@5 improvement ≥0.03
- ✅ Statistical significance confirmed (p<0.05)
- ✅ No catastrophic failures (accuracy regression >5pp on any query)

---

### AC6: Error Handling and Fallback Logic (2 hours)

**Goal:** Implement robust error handling for re-ranking failures

**Failure Scenarios:**
1. **Cross-encoder model fails to load**
   - Fallback: Disable re-ranking, use multi-index fusion scores
   - Log: "Cross-encoder initialization failed, re-ranking disabled"
   - System continues serving queries (degraded accuracy acceptable)

2. **Re-ranking timeout (>5s)**
   - Fallback: Return top-k from stage 1 (multi-index search)
   - Timeout threshold: 5s for 20-document batch
   - Log: "Re-ranking timeout, returning stage 1 results"

3. **Re-ranking batch processing error**
   - Fallback: Return stage 1 results
   - Log: "Re-ranking failed: {error}, returning fusion scores"
   - Don't crash query pipeline

4. **Empty results from stage 1**
   - Skip re-ranking (no candidates to re-rank)
   - Return empty results with appropriate message

**Testing:**
- Unit tests: Mock cross-encoder failures, verify fallback behavior
- Integration tests: Simulate timeout scenarios
- Chaos testing: Random re-ranking failures during 50-query test suite

**Success Criteria:**
- ✅ All 4 failure scenarios handled gracefully
- ✅ System never crashes on re-ranker failures
- ✅ Fallback logic tested and documented
- ✅ Error messages clear and actionable

---

## Tasks / Subtasks

- [ ] **Task 1: Cross-Encoder Integration (AC1)** - 4 hours
  - [ ] 1.1: Create `reranker.py` with CrossEncoder model loading
  - [ ] 1.2: Implement `rerank_results()` function with batch processing
  - [ ] 1.3: Write unit tests for re-ranking (20 documents → top-5)
  - [ ] 1.4: Validate model initialization <5s

- [ ] **Task 2: Multi-Index Pipeline Integration (AC2)** - 4 hours
  - [ ] 2.1: Update `multi_index_search()` to retrieve top-20
  - [ ] 2.2: Add cross-encoder re-ranking as stage 2
  - [ ] 2.3: Implement `use_reranker` configuration flag
  - [ ] 2.4: Write integration tests (with/without re-ranking)

- [ ] **Task 3: MCP Tool Update (AC3)** - 2 hours
  - [ ] 3.1: Add `use_reranker` parameter to QueryRequest
  - [ ] 3.2: Update `query_financial_documents` MCP tool
  - [ ] 3.3: Add observability logging (latency breakdown, score changes)
  - [ ] 3.4: Write end-to-end MCP tests

- [ ] **Task 4: Performance Validation (AC4)** - 4 hours
  - [ ] 4.1: Run 50 ground truth queries with latency measurement
  - [ ] 4.2: Measure p50/p95/p99 latency breakdown (stage 1 + stage 2)
  - [ ] 4.3: Validate NFR13 compliance (<15s p95)
  - [ ] 4.4: Document performance report

- [ ] **Task 5: Accuracy Validation (AC5)** - 4 hours
  - [ ] 5.1: A/B test: 25 queries without re-ranking vs 25 with re-ranking
  - [ ] 5.2: Calculate retrieval accuracy, Precision@5, MRR
  - [ ] 5.3: Statistical significance testing (paired t-test)
  - [ ] 5.4: Document accuracy improvement report

- [ ] **Task 6: Error Handling (AC6)** - 2 hours
  - [ ] 6.1: Implement model loading failure fallback
  - [ ] 6.2: Add timeout handling (5s threshold)
  - [ ] 6.3: Handle empty results gracefully
  - [ ] 6.4: Write chaos tests for all failure scenarios

## Dev Notes

### Architecture Patterns

**Two-Stage Retrieval (Cross-Encoder Re-Ranking):**
This story implements a research-validated two-stage retrieval pattern:
- **Stage 1 (Fast):** Bi-encoder (Fin-E5) retrieves top-20 candidates (~3s)
- **Stage 2 (Accurate):** Cross-encoder re-ranks top-20 → top-5 (~200ms)

**Why Two-Stage?**
- **Bi-encoders (Fin-E5):** Fast but approximate (independent query/document encoding)
- **Cross-encoders (MiniLM):** Accurate but slow (joint attention query ⊗ document)
- **Solution:** Use bi-encoder for fast retrieval, cross-encoder for precise re-ranking

**Research Evidence:**
- MS MARCO: Cross-encoder MRR@10 = 0.377 vs bi-encoder 0.325 (+16% improvement)
- T₂-RAGBench: Cross-encoder +5-10% precision over bi-encoders
- Financial RAG (FinSage): Re-ranking critical for precision in table-heavy workloads

**Simplicity Principle:**
- NO custom cross-encoder training (use pre-trained MS MARCO model)
- NO complex re-ranking frameworks (direct sentence-transformers API)
- Direct model integration (~100 lines of code)

### Project Structure Notes

**New Files Created:**
```
raglite/retrieval/
└── reranker.py              (~100 lines) - AC1: Cross-encoder re-ranking
```

**Modified Files:**
```
raglite/retrieval/multi_index_search.py  (~50 lines modified) - AC2: Two-stage pipeline
raglite/main.py                          (~20 lines modified) - AC3: MCP tool update
```

**Total Impact:** +100 new lines, 70 lines modified

**Alignment with Architecture:**
- Follows repository structure from `docs/architecture/3-repository-structure-monolithic.md`
- Uses retrieval/ module patterns from Epic 1 and Story 2.7
- Maintains existing multi-index search interface (backward compatible)

### Testing Standards

**Test Coverage Requirements:**
- Unit tests: `tests/unit/test_reranker.py` (AC1, AC6)
- Integration tests: `tests/integration/test_multi_index_reranking.py` (AC2-AC3)
- Performance tests: `tests/performance/test_reranking_latency.py` (AC4)
- Accuracy tests: `scripts/run-reranking-accuracy-tests.py` (AC5)

**Ground Truth Validation:**
- Reuse existing 50-query test suite from Epic 1
- A/B comparison: Multi-index fusion vs Multi-index + re-ranking
- Expected improvement: +3-5pp accuracy (70-75% → 75-80%)

### Coding Standards

**Type Hints (Mandatory):**
```python
async def rerank_results(
    query: str,
    results: List[SearchResult],
    top_k: int = 5
) -> List[SearchResult]:
    """Re-rank search results using cross-encoder."""
```

**Structured Logging:**
```python
logger.info(
    "Cross-encoder re-ranking complete",
    extra={
        "rerank_time_ms": 185,
        "input_count": 20,
        "output_count": 5,
        "top_score": 0.89
    }
)
```

**Error Handling:**
```python
try:
    results = await reranker.rerank_results(query, results, top_k)
except RerankerTimeoutError:
    logger.warning("Re-ranking timeout, returning stage 1 results")
    results = results[:top_k]  # Fallback to fusion scores
```

### References

**Architecture Documents:**
- [Source: docs/architecture/3-repository-structure-monolithic.md#retrieval-layer] - Module structure
- [Source: docs/architecture/6-complete-reference-implementation.md] - Coding patterns
- [Source: docs/architecture/5-technology-stack-definitive.md#phase-2] - Cross-encoder approval (Story 2.4)

**PRD Documents:**
- [Source: docs/prd/epic-2-advanced-rag-enhancements.md#phase-2b] - Phase 2B goals
- [Source: docs/prd/epic-2-advanced-rag-enhancements.md#story-27] - Multi-index search (dependency)

**Research Evidence:**
- MS MARCO Passage Ranking: Cross-encoder benchmark dataset
- T₂-RAGBench (2024): Cross-encoder +5-10% precision improvement
- FinSage (Snowflake AI): Re-ranking pattern for financial RAG
- sentence-transformers docs: https://www.sbert.net/docs/pretrained_cross-encoders.html

**Technology Stack:**
- sentence-transformers ≥2.2,<3.0 (APPROVED - Phase 2)
- Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (pre-trained)
- Story 2.7 dependency: Multi-index search operational

### Known Constraints

**CONDITIONAL IMPLEMENTATION:**
This story is ONLY implemented if:
1. Phase 2A (Story 2.3-2.5) achieves <70% retrieval accuracy
2. Story 2.7 (Multi-Index Search) is complete

**Probability:** 15% (research suggests 80% chance Phase 2A achieves 68-72%, triggering Phase 2B)

**Decision Authority:** PM (John) approves at Phase 2A decision gate (T+17, Week 3 Day 3)

**Dependency Chain:**
- Story 2.7 MUST be complete (Multi-index search operational)
- Phase 2A MUST have failed decision gate (<70% accuracy)
- PM approval MUST be granted for Phase 2B continuation

### NFR Compliance

**NFR13 (Performance):**
- Target: <15s p95 query latency
- Re-ranking budget: <250ms for 20 documents
- Validated in AC4

**NFR6 (Accuracy):**
- Target: 75-80% retrieval accuracy (Phase 2B goal with re-ranking)
- +3-5pp improvement over Story 2.7 baseline
- Validated in AC5 and Story 2.9

**NFR7 (Attribution):**
- ≥95% source attribution accuracy maintained
- Re-ranked results preserve metadata (document_id, page_number)
- Cross-encoder scores stored in metadata for observability

### Model Selection Rationale

**Why cross-encoder/ms-marco-MiniLM-L-6-v2?**
1. **Pre-trained on MS MARCO:** State-of-art passage ranking benchmark
2. **Lightweight:** 82MB model, 6-layer transformer (vs 12-layer alternatives)
3. **Fast:** 150-200ms for 20 documents @ batch_size=8
4. **Production-proven:** Used by major RAG systems (Qdrant docs, OpenAI cookbook)
5. **Free:** No API costs, local inference

**Alternatives Considered:**
- `cross-encoder/ms-marco-MiniLM-L-12-v2` (12 layers): 2x latency, +2% accuracy (rejected - latency budget)
- `cross-encoder/ms-marco-electra-base` (ELECTRA): +5% accuracy, 3x latency (rejected - complexity)
- Cohere Rerank API: +10% accuracy, $0.002/query (deferred to Phase 4 - cost optimization)

## Dev Agent Record

### Context Reference

- [Story Context XML](story-context-2.12.xml) - Generated 2025-10-24 (originally story-context-2.8.xml)

### Agent Model Used

Claude 3.7 Sonnet (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

---

**Story Status:** Draft
**Story Owner:** TBD (awaiting PM approval at Phase 2A decision gate)
**Next Step:** Wait for Stories 2.8-2.11 completion and re-validation
**Estimated Effort:** 2-3 days (20 hours total)
**Epic:** Epic 2 - Advanced RAG Architecture Enhancement (Phase 2B)

**Created Date:** 2025-10-24
**Created By:** Scrum Master (Bob)
**Triggered By:** Epic 2 Phase 2B contingency path (CONDITIONAL)

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-25 | 1.1 | Story renumbered from 2.8 → 2.12 to accommodate Phase 2A course correction stories (2.8-2.11) | Product Manager (John) |
| 2025-10-24 | 1.0 | Story 2.8 created from Epic 2 PRD Phase 2B with cross-encoder re-ranking approach based on research evidence (MS MARCO, T₂-RAGBench, FinSage) | Scrum Master (Bob) |
