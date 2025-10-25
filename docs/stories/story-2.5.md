# Story 2.5: AC3 Validation and Optimization (Decision Gate)

Status: ⚠️ COMPLETE - DECISION GATE FAILED (18% vs 70% target) - ESCALATE TO PHASE 2B

## DECISION GATE RESULTS (2025-10-22 23:57)

### ⚠️ CRITICAL: DECISION GATE FAILED

**Retrieval Accuracy: 18.0% (9/50 queries)**
**Attribution Accuracy: 18.0% (9/50 queries)**
**Target: ≥70.0% (35/50 queries required)**

**Shortfall: 52 percentage points below target**

**Decision: ❌ Epic 2 Phase 2A INCOMPLETE - MUST ESCALATE TO PHASE 2B**

---

### Test Execution Summary

**AC1 - Full Ground Truth Execution: ✅ PASSED**
- All 50 queries executed successfully
- Average latency: ~30ms (well below <15s p95 NFR13 requirement)
- Test duration: 4.1 seconds
- Results exported to: `docs/stories/AC1-ground-truth-results.json`

**AC2 - DECISION GATE: ❌ FAILED**
- Retrieval accuracy: 18.0% vs 70.0% target
- Only 9 out of 50 queries retrieved correct pages in top-5
- 41 queries failed (82% failure rate)
- Failure report: `docs/stories/AC2-decision-gate-failure-report.json`

**AC3 - Attribution Accuracy: ❌ FAILED**
- Attribution accuracy: 18.0% vs 95.0% target (NFR7 violation)
- Same failure pattern as retrieval
- 41 queries failed to provide correct source citations

**AC6 - Query Performance: ✅ PASSED**
- p50 latency: ~25ms
- p95 latency: ~45ms
- p99 latency: ~60ms
- All well below <15s target (NFR13 compliant)

---

### Root Cause Analysis

**Primary Issue: Page-Level Accuracy Failure**

The hybrid search system is finding **semantically relevant** content (similarity scores 0.6-0.8 range) but **NOT the exact pages** specified in ground truth expectations.

**Example Failure Pattern:**
- Query: "What is the variable cost per ton for Portugal Cement?"
- Expected: Page 46
- Retrieved: Pages 42, 30, 17, 43, 15
- Similarity score: 0.679 (decent relevance)

**Potential Root Causes:**
1. **Ground Truth Calibration Issue:** Expected pages may not align with where Docling actually extracted the information
2. **Fixed Chunking Side Effects (Story 2.3):** 512-token fixed chunks may split critical information across chunks
3. **BM25 Weight Imbalance:** Alpha=0.7 (70% semantic, 30% keyword) may be insufficient for precise page targeting
4. **Table Detection Gaps:** Many queries target financial tables which may be split across multiple pages

**What Worked:**
- ✅ Hybrid search retrieves relevant content (scores 0.6-0.8)
- ✅ Query latency excellent (~30ms average)
- ✅ Test infrastructure robust (465-line test suite executed flawlessly)
- ✅ Conftest fix worked (full 176-chunk PDF ingested correctly)

---

## Implementation Status (Session 2 - 2025-10-22)

**✅ COMPLETED:**
- AC1 test suite implemented (`tests/integration/test_ac3_ground_truth.py` - 465 lines)
- AC2 DECISION GATE test implemented and executed
- AC3 attribution validation test implemented and executed
- AC6 latency validation confirmed (<15s p95)
- Conftest fixture modified to preserve full PDF (lines 38-48)
- Execution script created (`scripts/run-ac2-decision-gate.sh`)
- Full 160-page PDF ingested (176 chunks in Qdrant)
- DECISION GATE test executed (4.1s duration)
- Failure reports generated (JSON format)

**❌ FAILED:**
- AC2 DECISION GATE: 18% vs 70% target
- AC3 Attribution: 18% vs 95% target

**⏭️ NEXT (Conditional on PM Approval):**
- AC4 Failure Mode Analysis (requires detailed review of 41 failed queries)
- Epic 2 Phase 2B planning and estimation

---

## Mandatory Next Steps

### 1. PM Escalation (IMMEDIATE)

**Decision Required:** Approve Phase 2B (Structured Multi-Index) implementation

**Options:**
- **Option A (RECOMMENDED):** Proceed to Phase 2B
  - **Effort:** 3-4 weeks (15-20 story points)
  - **Target:** 70-80% accuracy with PostgreSQL + Qdrant + cross-encoder
  - **Risk:** Medium (proven approach, research-validated)

- **Option B:** Investigate ground truth calibration first
  - **Effort:** 1-2 days
  - **Goal:** Verify if expected pages match Docling extraction
  - **Risk:** Low effort, may not solve core issue

- **Option C:** Accept 18% accuracy and pivot strategy
  - **Risk:** High - NFR6 (90%+ accuracy) will NOT be achievable

### 2. Technical Investigation (1-2 days)

Before committing to Phase 2B, investigate:

**A. Ground Truth Validation:**
- Manually inspect PDF pages 46, 47, 77, 108 in Acrobat/Preview
- Compare with Docling extraction output
- Verify expected answers actually appear on claimed pages

**B. Chunk-to-Page Mapping Audit:**
- Query Qdrant for chunks containing known answers
- Verify page_number payload matches ground truth expectations
- Check if fixed 512-token chunking split answers across chunks

**C. Failure Pattern Analysis:**
- Review `docs/stories/AC1-ground-truth-results.json` (full 50-query details)
- Categorize failures: table queries, multi-hop, entity-based, temporal
- Identify if failures cluster around specific page ranges or query types

### 3. Phase 2B Planning (if approved)

**Epic 2 Phase 2B: Structured Multi-Index**
- Story 2.6: PostgreSQL Schema + Metadata Tables (3 days)
- Story 2.7: Hybrid Qdrant + PostgreSQL Search (4 days)
- Story 2.8: Cross-Encoder Reranking (2 days)
- Story 2.9: AC3 Re-validation ≥75% (2-3 days)
- **Total:** 11-12 days → 2.5 weeks

**Expected Outcome:** 70-80% accuracy (research-validated approach)

## Story

As a QA engineer,
I want comprehensive accuracy validation,
so that we can verify ≥70% retrieval accuracy and decide if Epic 2 is complete.

## Acceptance Criteria

**AC1: Full Ground Truth Execution** (4 hours)
- Run all 50 ground truth queries from test suite
- Measure retrieval accuracy (% queries with correct chunk in top-5)
- Measure attribution accuracy (% correct source citations)
- Document test execution results with detailed metrics
- **Source:** [Epic 2 PRD: docs/prd/epic-2-advanced-rag-enhancements.md - Story 2.5 AC1]
- **Goal:** Establish baseline accuracy post-Stories 2.3 + 2.4 implementation

**AC2: DECISION GATE - Retrieval Accuracy ≥70%** (30 min) ⭐ MANDATORY
- **MANDATORY:** Retrieval accuracy ≥70.0% (35/50 queries pass)
- **This is the DECISION GATE for Epic 2 completion**
- Calculate pass rate: (successful_queries / 50) × 100%
- IF ≥70% → Epic 2 Phase 2A COMPLETE → Recommend Epic 3 start
- IF <70% → Escalate to PM for Phase 2B (Structured Multi-Index) approval
- **Source:** [Epic 2 PRD: docs/prd/epic-2-advanced-rag-enhancements.md - Story 2.5 AC2]
- **Critical Path:** This AC determines Epic 2 success/failure and unlocks Epic 3-5

**AC3: Attribution Accuracy ≥95%** (30 min)
- Attribution accuracy ≥95.0% (NFR7 compliance)
- Verify correct document, page, section references in top-5 results
- Document attribution failures with root cause analysis
- **Source:** [Epic 2 PRD: docs/prd/epic-2-advanced-rag-enhancements.md - Story 2.5 AC3]
- **NFR:** NFR7 - 95%+ source attribution accuracy

**AC4: Failure Mode Analysis** (1 day) - CONDITIONAL
- **Trigger:** ONLY if AC2 <70% accuracy (15% probability)
- Analyze all failed queries (queries where correct chunk NOT in top-5)
- Categorize failure types:
  - Table queries (complex financial tables)
  - Multi-hop reasoning (requires 2+ document chunks)
  - Entity-based queries (specific companies, metrics, departments)
  - Temporal queries (time-series, trends, comparisons)
- Document failure patterns with examples
- Recommend Phase 2B/2C approaches based on failure analysis
- **Source:** [Epic 2 PRD: docs/prd/epic-2-advanced-rag-enhancements.md - Story 2.5 AC4]
- **Goal:** Inform decision on Phase 2B (Structured Multi-Index) vs Phase 2C (Hybrid GraphRAG)

**AC5: BM25 Index Rebuild** (2 hours)
- Rebuild BM25 keyword index for new chunk structure (180-220 chunks, down from 504)
- Verify hybrid search (semantic + keyword fusion) still works
- Test BM25 + semantic score fusion with Reciprocal Rank Fusion (RRF)
- Measure hybrid search improvement over semantic-only baseline
- **Source:** [Epic 2 PRD: docs/prd/epic-2-advanced-rag-enhancements.md - Story 2.5 AC5]
- **Context:** Story 2.3 reduced chunk count from 504 → ~200, requiring BM25 index rebuild

**AC6: Performance Validation** (2 hours)
- p50 query latency <5s (target for user experience)
- p95 query latency <15s (NFR13 compliance)
- Measure query latency across all 50 ground truth queries
- Document latency distribution (p50, p75, p90, p95, p99)
- **Source:** [Epic 2 PRD: docs/prd/epic-2-advanced-rag-enhancements.md - Story 2.5 AC6]
- **NFR:** NFR13 - <15s p95 query response time

## Tasks / Subtasks

- [ ] Task 1: Prepare Ground Truth Test Suite (AC1 - 2 hours)
  - [ ] 1.1: Verify 50 ground truth queries in test suite
  - [ ] 1.2: Ensure test data (160-page PDF) re-ingested with Stories 2.3 + 2.4 changes
  - [ ] 1.3: Validate Qdrant collection has ~200 chunks (down from 504 element-aware)
  - [ ] 1.4: Create test script for batch query execution with metrics collection
- [ ] Task 2: Execute Full Accuracy Validation (AC1 - 2 hours)
  - [ ] 2.1: Run all 50 ground truth queries against updated RAG system
  - [ ] 2.2: Measure retrieval accuracy (% queries with correct chunk in top-5)
  - [ ] 2.3: Measure attribution accuracy (% correct source citations)
  - [ ] 2.4: Document results in structured format (JSON/CSV for analysis)
- [ ] Task 3: DECISION GATE Evaluation (AC2 - 30 min)
  - [ ] 3.1: Calculate retrieval accuracy percentage: (successful_queries / 50) × 100%
  - [ ] 3.2: IF ≥70%: Document Epic 2 Phase 2A COMPLETE status
  - [ ] 3.3: IF ≥70%: Recommend Epic 3 planning start
  - [ ] 3.4: IF <70%: Escalate to PM with failure analysis (Task 5)
  - [ ] 3.5: Update Epic 2 status in bmm-workflow-status.md based on decision gate result
- [ ] Task 4: Validate Attribution Accuracy (AC3 - 30 min)
  - [ ] 4.1: Verify ≥95% attribution accuracy (NFR7 compliance)
  - [ ] 4.2: Analyze attribution failures (wrong document/page/section)
  - [ ] 4.3: Document attribution error patterns
  - [ ] 4.4: Create attribution accuracy report
- [ ] Task 5: Failure Mode Analysis (AC4 - 1 day) - CONDITIONAL (<70% trigger)
  - [ ] 5.1: Extract all failed queries (correct chunk NOT in top-5)
  - [ ] 5.2: Categorize failures by type (table, multi-hop, entity, temporal)
  - [ ] 5.3: Analyze failure patterns and root causes
  - [ ] 5.4: Recommend Phase 2B (Structured Multi-Index) or Phase 2C (Hybrid GraphRAG)
  - [ ] 5.5: Create failure analysis report for PM escalation
- [ ] Task 6: Rebuild BM25 Index (AC5 - 2 hours)
  - [ ] 6.1: Delete old BM25 index (built for 504 element-aware chunks)
  - [ ] 6.2: Rebuild BM25 index for new 180-220 fixed chunks
  - [ ] 6.3: Verify hybrid search (BM25 + semantic) fusion still works
  - [ ] 6.4: Test Reciprocal Rank Fusion (RRF) score combination
  - [ ] 6.5: Measure hybrid search improvement over semantic-only baseline
- [ ] Task 7: Validate Query Performance (AC6 - 2 hours)
  - [ ] 7.1: Measure query latency for all 50 ground truth queries
  - [ ] 7.2: Calculate latency distribution (p50, p75, p90, p95, p99)
  - [ ] 7.3: Verify p50 <5s and p95 <15s (NFR13 compliance)
  - [ ] 7.4: Document performance metrics and any latency outliers
- [ ] Task 8: Update Documentation (1 hour)
  - [ ] 8.1: Update story 2.5 with validation results
  - [ ] 8.2: Document decision gate outcome (≥70% or escalation)
  - [ ] 8.3: Update Epic 2 status in PRD based on AC2 result
  - [ ] 8.4: Update bmm-workflow-status.md with Epic 2 Phase 2A completion (if ≥70%)

## Dev Notes

### Epic 2 Context - CRITICAL DECISION GATE

**Critical Background:**
Story 2.5 is the **FINAL STORY in Epic 2 Phase 2A** and contains the **DECISION GATE** that determines:
- ✅ Epic 2 COMPLETE (if ≥70% accuracy) → Proceed to Epic 3
- ⚠️ Epic 2 Phase 2B Required (if <70% accuracy) → Structured Multi-Index approach (+3-4 weeks)

**Epic 2 Phase 2A Progress:**
- ✅ **Story 2.1 COMPLETE:** pypdfium backend (50-60% memory reduction, 1.7-2.5x speedup)
- ✅ **Story 2.2 COMPLETE:** Page-level parallelism (1.55x speedup, Phase 1 complete)
- ✅ **Story 2.3 COMPLETE:** Fixed 512-token chunking (Yepes et al. 2024: 68.09% baseline)
- ✅ **Story 2.4 COMPLETE:** LLM metadata injection (GPT-5 nano, +2-3pp expected boost)
- 🔄 **Story 2.5 IN PROGRESS:** AC3 validation → **DECISION GATE at T+17 (Week 3, Day 3)**

**Expected Accuracy Range (Research-Validated):**
- **Baseline (Story 2.3 only):** 68-72% (Yepes et al. 2024 - fixed 512-token chunks)
- **With Metadata (Story 2.4):** 70-75% (+2-3pp from metadata boosting, Snowflake research)
- **Decision Gate Target:** ≥70.0% (35/50 queries pass)

**Decision Gate Scenarios:**

1. **BEST CASE (80% probability): ≥70% Accuracy**
   - Epic 2 Phase 2A COMPLETE ✅
   - Epic 2 SUCCESS → Unblocks Epic 3-5
   - Timeline: 2-3 weeks total (as projected)
   - Next: Epic 3 planning (Intelligence Features)

2. **CONTINGENCY (15% probability): 64-69% Accuracy**
   - Epic 2 Phase 2A FAILED → Escalate to Phase 2B
   - Approach: Structured Multi-Index (PostgreSQL + Qdrant + cross-encoder)
   - Timeline: +3-4 weeks (total 5-7 weeks)
   - Expected: 70-80% accuracy with structured approach
   - Decision Authority: PM (John) + User approval required

3. **CRITICAL ESCALATION (5% probability): <64% Accuracy**
   - Epic 2 Phase 2A CATASTROPHIC FAILURE
   - Approach: Phase 2C Hybrid GraphRAG (Neo4j + PostgreSQL + Qdrant)
   - Timeline: +9-10 weeks (total 11-13 weeks)
   - Expected: 75-92% accuracy with GraphRAG
   - Decision Authority: PM (John) + User + Strategy review

**Impact of Decision Gate:**
- **IF ≥70%:** Epic 2 complete, proceed to Epic 3-5 (forecasting, insights, production)
- **IF <70%:** Epic 2 extends with contingency phases, delays Epic 3-5 by 3-10 weeks

### Architecture Patterns and Constraints

**Ground Truth Test Suite Pattern:**
```python
import pytest
from raglite.retrieval.search import hybrid_search
from tests.fixtures.ground_truth_queries import GROUND_TRUTH_QUERIES

@pytest.mark.asyncio
async def test_ac1_full_ground_truth_execution():
    """Execute all 50 ground truth queries and measure accuracy.

    Test Structure:
        - 50 ground truth queries from test suite
        - Each query has: question, expected_document, expected_page, expected_chunk
        - Measure: retrieval accuracy (correct chunk in top-5)
        - Measure: attribution accuracy (correct document + page)

    Expected Results:
        - Retrieval accuracy: 70-75% (35-37.5 / 50 queries pass)
        - Attribution accuracy: ≥95% (NFR7 compliance)

    Returns:
        AccuracyMetrics(
            retrieval_accuracy: float,  # 70-75% expected
            attribution_accuracy: float, # ≥95% required
            total_queries: int,           # 50
            successful_queries: int,      # 35-37 expected
            failed_queries: List[FailedQuery]  # For AC4 analysis
        )
    """
    results = []

    for query in GROUND_TRUTH_QUERIES:
        # Execute hybrid search (BM25 + semantic)
        search_results = await hybrid_search(
            query=query.question,
            top_k=5
        )

        # Validate retrieval (correct chunk in top-5)
        retrieval_success = any(
            result.chunk_id == query.expected_chunk_id
            for result in search_results
        )

        # Validate attribution (correct document + page)
        attribution_success = any(
            result.document == query.expected_document and
            result.page_number == query.expected_page
            for result in search_results
        )

        results.append({
            "query": query.question,
            "retrieval_success": retrieval_success,
            "attribution_success": attribution_success,
            "top_5_chunks": [r.chunk_id for r in search_results]
        })

    # Calculate accuracy metrics
    retrieval_accuracy = sum(r["retrieval_success"] for r in results) / 50 * 100
    attribution_accuracy = sum(r["attribution_success"] for r in results) / 50 * 100

    # AC2 DECISION GATE
    assert retrieval_accuracy >= 70.0, (
        f"DECISION GATE FAILED: Retrieval accuracy {retrieval_accuracy:.1f}% < 70% target. "
        f"Epic 2 Phase 2A incomplete. Escalate to PM for Phase 2B approval."
    )

    # AC3 NFR7 Compliance
    assert attribution_accuracy >= 95.0, (
        f"NFR7 FAILED: Attribution accuracy {attribution_accuracy:.1f}% < 95% required"
    )

    return AccuracyMetrics(
        retrieval_accuracy=retrieval_accuracy,
        attribution_accuracy=attribution_accuracy,
        total_queries=50,
        successful_queries=sum(r["retrieval_success"] for r in results),
        failed_queries=[r for r in results if not r["retrieval_success"]]
    )
```

**Failure Mode Analysis Pattern (Conditional):**
```python
def analyze_failure_modes(failed_queries: List[FailedQuery]) -> FailureAnalysis:
    """Categorize query failures to inform Phase 2B/2C decision.

    Failure Categories:
        - TABLE_QUERY: Complex financial tables (recommend Phase 2B structured)
        - MULTI_HOP: Requires 2+ chunks (recommend Phase 2C GraphRAG)
        - ENTITY_BASED: Specific companies/metrics (recommend metadata expansion)
        - TEMPORAL: Time-series/trends (recommend Phase 2C GraphRAG)

    Decision Logic:
        - IF >50% TABLE_QUERY failures → Phase 2B (Structured Multi-Index)
        - IF >50% MULTI_HOP failures → Phase 2C (GraphRAG)
        - IF >50% ENTITY_BASED failures → Expand metadata extraction (LLM tuning)
    """
    categorized_failures = {
        "table": [],
        "multi_hop": [],
        "entity": [],
        "temporal": []
    }

    for query in failed_queries:
        # Categorize failure type based on query content and expected chunk
        if "table" in query.expected_chunk.lower():
            categorized_failures["table"].append(query)
        elif "compare" in query.question or "correlation" in query.question:
            categorized_failures["multi_hop"].append(query)
        # ... categorization logic

    # Recommend approach based on dominant failure type
    if len(categorized_failures["table"]) > len(failed_queries) / 2:
        recommendation = "Phase 2B: Structured Multi-Index (SQL tables + vector)"
    elif len(categorized_failures["multi_hop"]) > len(failed_queries) / 2:
        recommendation = "Phase 2C: Hybrid GraphRAG (Neo4j + PostgreSQL + Qdrant)"
    else:
        recommendation = "Optimize metadata extraction (expand LLM prompt)"

    return FailureAnalysis(
        categorized_failures=categorized_failures,
        recommendation=recommendation
    )
```

**BM25 Index Rebuild Pattern:**
```python
from rank_bm25 import BM25Okapi
import pickle

def rebuild_bm25_index(chunks: List[Chunk]) -> BM25Okapi:
    """Rebuild BM25 index for new fixed-chunking structure.

    Context:
        - Story 2.3 reduced chunk count: 504 element-aware → ~200 fixed chunks
        - Old BM25 index built for 504 chunks is now invalid
        - Rebuild required for hybrid search to work correctly

    Args:
        chunks: List of Chunk objects from fixed 512-token chunking

    Returns:
        BM25Okapi index for keyword-based retrieval

    Algorithm:
        1. Tokenize all chunk texts (simple whitespace split)
        2. Create BM25Okapi index from tokenized corpus
        3. Save index to disk for persistence
        4. Verify index size matches chunk count (~200)
    """
    # Tokenize chunk texts
    tokenized_corpus = [chunk.text.lower().split() for chunk in chunks]

    # Create BM25 index
    bm25_index = BM25Okapi(tokenized_corpus)

    # Save index to disk
    with open("data/bm25_index.pkl", "wb") as f:
        pickle.dump(bm25_index, f)

    # Verify index size
    assert len(tokenized_corpus) == len(chunks), "Index size mismatch"

    return bm25_index
```

**Key Constraints:**
- **NO custom test frameworks** - Use pytest with standard fixtures
- **KISS principle** - Direct test execution, no test orchestration layers
- **Decision gate is MANDATORY** - AC2 ≥70% is Epic 2 success/failure
- **Failure analysis CONDITIONAL** - Only if AC2 <70% (15% probability)
- **Source:** [CLAUDE.md - Anti-Over-Engineering Rules]

### Testing Standards Summary

**Test Suite Structure:**
```
tests/
├── integration/
│   ├── test_ac3_ground_truth.py          # AC1, AC2, AC3 - Full ground truth suite
│   ├── test_failure_mode_analysis.py     # AC4 - Conditional failure analysis
│   ├── test_bm25_index_rebuild.py        # AC5 - BM25 index rebuild validation
│   └── test_query_performance.py         # AC6 - Performance validation (NFR13)
└── fixtures/
    └── ground_truth_queries.py            # 50 ground truth Q&A pairs
```

**Ground Truth Test Data:**
- 50 queries covering:
  - Simple factual retrieval (20 queries)
  - Complex table queries (15 queries)
  - Multi-document synthesis (10 queries)
  - Temporal/trend analysis (5 queries)
- Expected results for each query:
  - Correct document ID
  - Correct page number
  - Correct chunk ID (for top-5 validation)

**Performance Benchmarks (AC6):**
- p50 latency: <5s target (user experience)
- p95 latency: <15s MANDATORY (NFR13 compliance)
- Measure across all 50 queries for statistical validity

### Project Structure Notes

**Files Modified:**
- `tests/integration/test_ac3_ground_truth.py` (+150 lines - AC1/AC2/AC3 tests)
- `tests/integration/test_failure_mode_analysis.py` (+100 lines - AC4 conditional)
- `tests/integration/test_bm25_index_rebuild.py` (+50 lines - AC5 validation)
- `tests/integration/test_query_performance.py` (+80 lines - AC6 performance)
- `tests/fixtures/ground_truth_queries.py` (existing - 50 queries)
- `raglite/retrieval/search.py` (potential fixes if accuracy <70%)

**Expected Lines of Code:**
- Test suite: ~380 lines
- Fixes (if needed): ~50-100 lines
- Total: ~430-480 lines

### References

**Research Citations:**
- [Yepes et al. (2024)] Fixed 512-token chunks: 68.09% accuracy baseline
- [Snowflake Research] Metadata boosting: +20% improvement over large chunks alone
- [Epic 2 PRD] docs/prd/epic-2-advanced-rag-enhancements.md - Story 2.5 specifications
- [Tech Spec] docs/tech-spec-epic-2.md - Epic 2 technical approach
- [CLAUDE.md] Anti-over-engineering rules and constraints

**Decision Gate Authority:**
- PM (John): Phase 2B/2C approval authority
- User (Ricardo): Final go/no-go on contingency phases
- Story 2.5 AC2: Provides empirical data for decision

## Dev Agent Record

### Context Reference

- `docs/stories/story-context-2.5.xml` (Generated: 2025-10-22)

### Agent Model Used

<!-- Will be populated by dev agent -->

### Debug Log References

<!-- Will be populated during implementation -->

### Completion Notes List

<!-- Will be populated after AC1-AC6 validation -->

### File List

**Test Files Created/Modified:**
- tests/integration/test_ac3_ground_truth.py
- tests/integration/test_failure_mode_analysis.py
- tests/integration/test_bm25_index_rebuild.py
- tests/integration/test_query_performance.py

**Potential Code Fixes (if AC2 <70%):**
- raglite/retrieval/search.py (hybrid search tuning)
- raglite/ingestion/pipeline.py (chunking adjustments)

**Documentation Updates:**
- docs/prd/epic-2-advanced-rag-enhancements.md (Epic 2 status)
- docs/bmm-workflow-status.md (Phase 2A completion or escalation)
- docs/stories/story-2.5.md (validation results)

---

## Change Log

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2025-10-22 | 1.0 | Story 2.5 created by SM agent (Bob) - AC3 Decision Gate for Epic 2 Phase 2A | Scrum Master (Bob) |
