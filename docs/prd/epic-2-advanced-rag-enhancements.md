# Epic 2: Advanced RAG Architecture Enhancement

**Status:** IN PROGRESS
**Priority:** 🔴 **CRITICAL** (blocks Epic 3-5)
**Duration:** 2-3 weeks (best case, Phase 1+2A) to 18 weeks (worst case, all contingencies)
**Goal:** Achieve minimum 70% retrieval accuracy through staged RAG architecture enhancement

**⚠️ STRATEGIC PIVOT (2025-10-19):**
Epic 2 has been redefined following the catastrophic failure of element-aware chunking (Story 2.2 achieved 42% vs 56% baseline = -14pp regression). This epic now implements a **staged RAG architecture approach** with decision gates at each phase.

---

## Epic Overview

Epic 2 pivots from the failed element-aware chunking approach (42% accuracy, -14pp regression) to a staged RAG architecture enhancement strategy. This epic implements PDF ingestion optimization followed by a research-validated fixed chunking approach, with contingency paths to Structured Multi-Index or Hybrid Architecture if accuracy thresholds are not met.

**Root Cause of Pivot:**
Story 2.2 (Element-Aware Chunking) implemented the **exact failure mode warned against in research** (Yepes et al. 2024):
- Research evidence: Element-based "Keywords Chipper" = **46.10% accuracy**
- Research evidence: Fixed 512-token chunks = **68.09% accuracy**
- **We built the 46% solution instead of the 68% solution**

**New Approach:**
Staged implementation with empirical decision gates based on production-proven RAG patterns.

---

## Business Value

- **Achieve minimum 70% retrieval accuracy** (unblock Epic 3-5)
- **1.7-2.5x faster PDF ingestion** (accelerate testing iterations)
- **Production-proven approaches** (68-72% guaranteed by research)
- **Staged implementation with decision gates** (minimize risk)
- **Cost-efficient path to accuracy** (start simple, escalate only if needed)

---

## Success Criteria

Epic 2 is considered COMPLETE when:

- ✅ **Retrieval accuracy ≥70%** (MANDATORY for Epic 3)
- ✅ **Attribution accuracy ≥95%** (NFR7 compliance)
- ✅ **Query response time <15s p95** (NFR13 compliance)
- ✅ **All 50 AC3 ground truth queries validated**
- ✅ **PRD Epic 2 documentation updated**
- ✅ **Technology stack documentation updated**
- ✅ **Test suite passing with new chunking strategy**

---

## Implementation Phases

### PHASE 1: PDF Ingestion Performance Optimization (1-2 days)

**Goal:** 1.7-2.5x speedup (8.2 min → 3.3-4.8 min for 160-page PDF)
**Risk:** LOW (empirically validated by Docling official benchmarks)
**Strategic Benefit:** Faster ingestion enables quicker RAG testing iterations in Phase 2

---

### Story 2.1: Implement pypdfium Backend for Docling

**Priority:** 🔴 CRITICAL (blocks Phase 2A)
**Effort:** 4 hours
**Goal:** Replace default PDF.js backend with pypdfium for 50-60% memory reduction and faster processing

**As a** system administrator,
**I want** Docling configured with pypdfium backend,
**so that** PDF ingestion is faster and uses less memory.

#### Acceptance Criteria

1. **AC1: Docling Backend Configuration** (1 hour)
   - Configure `PdfiumBackend` in `raglite/ingestion/pipeline.py`
   - Remove default PDF.js backend configuration
   - Validate backend switch successful

2. **AC2: Ingestion Validation** (1 hour)
   - Ingest test PDF (160 pages) successfully
   - Verify all pages processed
   - Verify table extraction still works

3. **AC3: Table Accuracy Maintained** (1 hour)
   - Run 10 ground truth table queries
   - Validate table extraction accuracy ≥97.9% (no degradation)
   - Document any accuracy changes

4. **AC4: Memory Reduction Validation** (1 hour)
   - Measure peak memory usage during ingestion
   - Expected: 50-60% reduction (6.2GB → 2.4GB)
   - Document memory usage before/after

#### Expected Impact

- **Memory:** 50-60% reduction (6.2GB → 2.4GB)
- **Speed:** 1.0x baseline (unchanged at this step)
- **Accuracy:** 97.9% maintained
- **Risk:** LOW (pypdfium is official Docling backend)

#### Decision Gate

- **IF successful:** Proceed to Story 2.2
- **IF failed:** Escalate to PM (technology stack issue)

**Technologies:** pypdfium (APPROVED - new dependency)

**Files Modified:**
- `raglite/ingestion/pipeline.py` (~15 lines - backend configuration)
- `pyproject.toml` (+1 dependency: pypdfium)

---

### Story 2.2: Implement Page-Level Parallelism (4-8 Threads)

**Priority:** 🔴 CRITICAL (blocks Phase 2A)
**Effort:** 4 hours
**Depends On:** Story 2.1
**Goal:** Add concurrent page processing to Docling for 1.7-2.5x speedup

**As a** system administrator,
**I want** page-level parallel processing,
**so that** PDF ingestion is 1.7-2.5x faster.

#### Acceptance Criteria

1. **AC1: Parallel Processing Configuration** (2 hours)
   - Configure Docling with `max_num_pages_visible=4`
   - Implement page-level concurrency (4-8 threads)
   - Handle thread pool cleanup

2. **AC2: Speedup Validation** (1 hour)
   - Ingest test PDF (160 pages) with parallelism
   - Measure ingestion time: target 3.3-4.8 min (vs 8.2 min baseline)
   - Calculate speedup: target 1.7-2.5x

3. **AC3: Speedup Documentation** (30 min)
   - Document ingestion time before/after
   - Document speedup factor (1.7x-2.5x range)
   - Document optimal thread count (4 vs 8)

4. **AC4: No Race Conditions** (30 min)
   - Test 10 consecutive ingestions
   - Verify no deadlocks or race conditions
   - Verify output deterministic (same chunks every time)

#### Expected Impact

- **Speed:** 1.7-2.5x faster ingestion (8.2 min → 3.3-4.8 min)
- **Accuracy:** 97.9% maintained
- **Memory:** 2.4GB maintained (from Story 2.1)
- **Strategic:** Faster iterations for Phase 2A testing

#### Decision Gate

- **IF ≥1.7x speedup:** Phase 1 COMPLETE → Proceed to Phase 2A
- **IF <1.7x speedup:** Escalate to PM (expected speedup not achieved)

**Technologies:** Docling parallelism (no new dependencies)

**Files Modified:**
- `raglite/ingestion/pipeline.py` (~30 lines - parallel configuration)

---

### PHASE 2A: Fixed Chunking + Metadata (1-2 weeks)

**Goal:** Achieve 68-72% retrieval accuracy (unblock Epic 3)
**Probability:** 80% success (research-validated: 68-72% accuracy)
**Risk:** MEDIUM-LOW (production-proven approach)
**Decision Gate:** IF ≥70% → STOP (Epic 2 complete), IF <70% → Phase 2B

---

### Story 2.3: Refactor Chunking Strategy to Fixed 512-Token Approach

**Priority:** 🔴 CRITICAL
**Effort:** 3 days
**Depends On:** Story 2.2 (Phase 1 complete)
**Goal:** Replace element-aware chunking with research-validated fixed 512-token chunks with 50-token overlap

**As a** RAG system,
**I want** fixed 512-token chunking with 50-token overlap,
**so that** retrieval accuracy improves from 42% to 68-72%.

#### Acceptance Criteria

1. **AC1: Remove Element-Aware Logic** (4 hours)
   - Delete element-aware chunking code from `raglite/ingestion/pipeline.py`
   - Remove ElementType enum from `raglite/shared/models.py`
   - Remove element detection logic

2. **AC2: Implement Fixed 512-Token Chunking** (1 day)
   - Chunk size: 512 tokens
   - Overlap: 50 tokens
   - Tokenizer: OpenAI tiktoken (cl100k_base)
   - Preserve sentence boundaries when possible

3. **AC3: Table Boundary Preservation** (4 hours)
   - Detect Docling TableItem objects
   - Ensure tables NOT split mid-row
   - If table >512 tokens, keep as single chunk (exception to 512-token rule)

4. **AC4: Clean Collection and Re-ingest** (4 hours)
   - Delete contaminated Qdrant collection
   - Recreate collection with clean schema
   - Re-ingest test PDF (160 pages)
   - Verify chunk count: 250-350 (vs 504 element-aware)

5. **AC5: Chunk Count Validation** (1 hour)
   - Expected chunk count: 250-350
   - Measure chunk size consistency: 512 tokens ±50 variance
   - Document chunk count and size distribution

6. **AC6: Chunk Size Consistency** (1 hour)
   - Measure chunk size: mean=512, std<50
   - Verify 95% of chunks within 462-562 token range
   - Document outliers (tables >512 tokens)

#### Expected Impact

- **Accuracy:** 42% → 68-72% (+26-30pp improvement)
- **Chunks:** 504 → 250-350 (-50% chunk count)
- **Research Evidence:** Yepes et al. (2024) - 68.09% accuracy on financial reports

#### Decision Gate

- **IF implemented successfully:** Proceed to Story 2.4
- **IF technical blockers:** Escalate to PM

**Technologies:** tiktoken (APPROVED - new dependency)

**Files Modified:**
- `raglite/ingestion/pipeline.py` (-150 lines element-aware, +80 lines fixed chunking)
- `raglite/shared/models.py` (-30 lines element types)
- `pyproject.toml` (+1 dependency: tiktoken)

---

### Story 2.4: Add LLM-Generated Contextual Metadata Injection

**Priority:** 🟠 HIGH
**Effort:** 2 days
**Depends On:** Story 2.3
**Goal:** Implement Claude API-based metadata extraction (fiscal period, company, department) and inject into chunk payload

**As a** RAG system,
**I want** LLM-generated metadata (fiscal period, company, department),
**so that** queries can filter by business context and improve precision.

#### Acceptance Criteria

1. **AC1: Metadata Extraction Function** (1 day)
   - Use Claude 3.7 Sonnet API
   - Extract: fiscal_period, company_name, department_name
   - Prompt: "Extract fiscal period, company name, and department from this text"
   - Cache results per document (not per chunk)

2. **AC2: Metadata Schema Update** (2 hours)
   - Add metadata fields to Chunk model: fiscal_period, company_name, department_name
   - Update Qdrant payload schema
   - Ensure backward compatibility

3. **AC3: Metadata Injection** (4 hours)
   - Inject metadata into Qdrant chunk payload
   - Metadata accessible via search filters
   - Document metadata usage patterns

4. **AC4: Metadata Caching** (2 hours)
   - Cache metadata extraction results per document
   - Avoid re-extracting for every chunk (performance optimization)
   - Measure: <$0.10 per document metadata extraction

5. **AC5: Cost Validation** (1 hour)
   - Measure Claude API token usage
   - Expected cost: <$0.10 per 160-page document
   - Document metadata extraction cost per document

#### Expected Impact

- **Accuracy:** 68-72% → 70-75% (+2-3pp improvement via metadata boosting)
- **Cost:** $0.05-0.10 per document (one-time extraction)
- **Research Evidence:** Snowflake research - 20% improvement over large chunks

#### Decision Gate

- **IF implemented successfully:** Proceed to Story 2.5
- **IF technical blockers:** Escalate to PM

**Technologies:** Claude 3.7 Sonnet API (already approved), tiktoken

**Files Modified:**
- `raglite/ingestion/pipeline.py` (+100 lines - metadata extraction)
- `raglite/shared/models.py` (+20 lines - metadata fields)

---

### Story 2.5: AC3 Validation and Optimization (Target: ≥70% Accuracy) - DECISION GATE

**Status:** ⚠️ FAILED - 52% accuracy, course correction required (Stories 2.8-2.11)
**Priority:** 🔴 CRITICAL (Epic 2 completion gate)
**Effort:** 2-3 days
**Depends On:** Story 2.4
**Goal:** Run full AC3 ground truth test suite (50 queries) and optimize chunking if needed

**⚠️ OUTCOME (2025-10-25):** AC2 FAILED with 52% accuracy (vs ≥70% target). Deep-dive analysis identified 4 critical root causes requiring course correction via Stories 2.8-2.11 before re-validation.

**As a** QA engineer,
**I want** comprehensive accuracy validation,
**so that** we can verify ≥70% retrieval accuracy and decide if Epic 2 is complete.

#### Acceptance Criteria

1. **AC1: Full Ground Truth Execution** (4 hours)
   - Run all 50 ground truth queries
   - Measure retrieval accuracy (% queries with correct chunk in top-5)
   - Measure attribution accuracy (% correct source citations)

2. **AC2: DECISION GATE - Retrieval Accuracy ≥70%** (30 min) ⭐ MANDATORY
   - **MANDATORY:** Retrieval accuracy ≥70.0% (35/50 queries pass)
   - **This is the DECISION GATE for Epic 2 completion**
   - IF ≥70% → Epic 2 COMPLETE
   - IF <70% → Escalate to PM for Phase 2B approval

3. **AC3: Attribution Accuracy ≥95%** (30 min)
   - Attribution accuracy ≥95.0%
   - Correct document, page, section references
   - NFR7 compliance

4. **AC4: Failure Mode Analysis** (1 day)
   - Analyze all failed queries (<70% accuracy scenario)
   - Categorize failure types (table queries, multi-hop, entity-based, etc.)
   - Document failure patterns
   - Recommend Phase 2B/2C approaches if needed

5. **AC5: BM25 Index Rebuild** (2 hours)
   - Rebuild BM25 index for new chunk structure (250-350 chunks)
   - Verify hybrid search still works
   - Test BM25 + semantic fusion

6. **AC6: Performance Validation** (2 hours)
   - p50 query latency <5s
   - p95 query latency <15s
   - NFR13 compliance verified

#### Expected Impact

- **Accuracy:** 68-72% target (research-validated)
- **Decision:** IF ≥70% → Epic 2 COMPLETE (proceed to Epic 3)
- **Decision:** IF <70% → Phase 2B Structured Multi-Index (3-4 weeks, 70-80% expected)

#### Decision Gate

- **IF ≥70%:** Epic 2 COMPLETE → Proceed to Epic 3 🎉
- **IF <70%:** Escalate to PM for Phase 2B (Structured Multi-Index) approval
- **IF <64%:** CRITICAL ESCALATION → Strategy review required

**Technologies:** pytest, ground truth test suite

**Files Modified:**
- `tests/integration/test_hybrid_search_integration.py` (updates for new chunking)

---

### PHASE 2A COURSE CORRECTION (2-3 days)

**Trigger:** Story 2.5 FAILED with 52% accuracy (2025-10-25)
**Root Cause Analysis:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/phase2a-deep-dive-analysis.md`
**Goal:** Fix 4 critical root causes before re-validation
**Expected Outcome:** 65-75% accuracy (Phase 2A target range)

**Sprint Change Proposal:** Approved 2025-10-25 by PM (John) + User (Ricardo)

---

### Story 2.8: Implement Table-Aware Chunking Strategy

**Priority:** 🔴 CRITICAL
**Effort:** 6-8 hours
**Goal:** Fix severe table fragmentation (8.6 chunks/table → 1.2 chunks/table)

**Problem:** Fixed 512-token chunking splits tables across multiple chunks, destroying semantic coherence.

**Solution:** Preserve complete tables as single chunks (<4096 tokens) or split by rows with headers preserved (>4096 tokens).

**Expected Impact:** +10-15pp accuracy improvement from restored table semantic coherence.

---

### Story 2.9: Fix Ground Truth Page References

**Priority:** 🔴 CRITICAL
**Effort:** 3-4 hours
**Goal:** Add page references to all 50 ground truth queries for proper validation

**Problem:** All ground truth queries have zero expected page references, making accuracy metrics invalid.

**Solution:** Manually annotate all 50 queries with correct page numbers from source PDF.

**Expected Impact:** Valid accuracy metrics, confidence in measurements restored.

---

### Story 2.10: Fix Query Classification Over-Routing

**Priority:** 🟠 HIGH
**Effort:** 3-4 hours
**Goal:** Reduce SQL over-routing from 48% → 8%

**Problem:** Heuristic classifier routes 48% of queries to SQL when only 4% have temporal qualifiers.

**Solution:** Require BOTH metric terms AND temporal terms for SQL_ONLY routing.

**Expected Impact:** -300-500ms p50 latency reduction, fewer failed SQL searches.

---

### Story 2.11: Fix Hybrid Search Score Normalization & Fusion

**Priority:** 🟡 MEDIUM
**Effort:** 4-6 hours
**Goal:** Debug hybrid search scoring bug and tune BM25 fusion weights

**Problem:** All hybrid searches return score=1.0, hiding actual relevance ranking.

**Solution:** Fix scoring bug, preserve raw fusion scores, tune BM25 fusion weight (alpha parameter).

**Expected Impact:** Improved ranking quality, score visibility for debugging.

---

### Story 2.5 RE-VALIDATION (After Stories 2.8-2.11)

**Goal:** Re-run AC3 validation with all fixes applied
**Expected Accuracy:** 65-75% (Phase 2A target range)

**Decision Gate:**
- IF ≥70% → Epic 2 COMPLETE → Proceed to Epic 3 🎉
- IF 65-70% → Re-evaluate Phase 2B necessity
- IF <65% → Escalate to Phase 2B (PM approval required)

---

## PHASE 2B: Structured Multi-Index (CONDITIONAL - 3-4 weeks)

**Trigger:** ONLY if Phase 2A achieves <70% accuracy after Stories 2.8-2.11 course correction
**Probability:** LOW (expected 65-75% from course correction)
**Goal:** Achieve 70-80% retrieval accuracy
**Approach:** SQL tables + vector search + re-ranking (FinSage pattern)

**Status Update (2025-10-25):**
- ✅ Story 2.6: PostgreSQL Schema + Data Migration (COMPLETE)
- ✅ Story 2.7: Multi-Index Search Architecture (COMPLETE)
- ⏸️ Story 2.12: Cross-Encoder Re-Ranking (ON HOLD - awaiting Phase 2A re-validation)
- ⏸️ Story 2.13: AC3 Validation (ON HOLD - awaiting Story 2.12)

**NOTE:** Stories 2.6-2.7 were implemented proactively during Phase 2A. If Phase 2A course correction achieves ≥70%, Phase 2B remaining stories (2.12-2.13) will be SKIPPED.

**Expected Outcome:** 70-80% accuracy
**Decision Gate:** IF ≥75% → STOP, IF <75% → Phase 2C

---

## PHASE 2C: Hybrid Architecture (CONDITIONAL - 6 weeks)

**Trigger:** ONLY if Phase 2B achieves <75% accuracy (5% probability)
**Goal:** Achieve 75-92% retrieval accuracy
**Approach:** GraphRAG + Structured + Vector (full multi-index)

**Production Evidence:**
- BlackRock/NVIDIA HybridRAG: 0.96 answer relevancy (SOTA)
- BNP Paribas GraphRAG: 6% hallucination reduction, 80% token savings

**Stories (if triggered):**
- 2.10: Neo4j Graph Database Integration
- 2.11: Entity Extraction & Graph Construction
- 2.12: Intelligent Query Routing Across 3 Indexes
- 2.13: AC3 Validation (Target: ≥80%)

**Expected Outcome:** 75-92% accuracy
**Decision Gate:** STOP when ≥80%

---

## PHASE 3: Agentic Coordination (OPTIONAL - 2-16 weeks)

**Trigger:** ONLY if Phase 2 (any path) achieves <85% accuracy (20% probability)
**Goal:** Achieve 90-95% retrieval accuracy
**Approach:** LLM-based query planning + specialist agents

**Production Evidence:**
- AWS, CapitalOne, NVIDIA agentic RAG systems
- +15-20pp accuracy improvement over non-agentic

**Framework:** LangGraph + AWS Strands OR Claude Agent SDK

**Expected Outcome:** 90-95% accuracy

---

## Epic 2 Dependencies

**Prerequisites:**
- ✅ Epic 1 complete (Stories 1.1-1.12)
- ✅ Story 2.1 (Hybrid Search) completed and validated
- ✅ Story 2.2 (Element Chunking) FAILED (42% accuracy = pivot trigger)

**Blocks:**
- Epic 3 (Intelligence Features) - needs Epic 2 complete (≥70% accuracy)
- Epic 4 (Forecasting) - needs Epic 3 complete
- Epic 5 (Production) - needs Epic 3-4 complete

---

## Technologies Summary

**APPROVED (Phase 1 + 2A):**
- ✅ pypdfium (PDF backend for Docling)
- ✅ tiktoken (OpenAI tokenizer for fixed chunking)
- ✅ Claude 3.7 Sonnet API (metadata extraction)

**CONDITIONAL (Phase 2B):**
- ⚠️ PostgreSQL 16 (structured table storage)

**CONDITIONAL (Phase 2C):**
- ⚠️ Neo4j 5.x (knowledge graph)
- ⚠️ PostgreSQL 16 (structured table storage)

**CONDITIONAL (Phase 3):**
- ⚠️ LangGraph + AWS Strands (agentic orchestration)
- ⚠️ Claude Agent SDK (alternative)

**Decision Authority:** PM (John) approves at each decision gate based on accuracy validation results.

---

## Timeline Summary

**Updated Timeline (2025-10-25 - Post-Course Correction):**

**Best Case (Phase 1 + 2A with Course Correction):**
- Week 1: Phase 1 (PDF optimization) - 1-2 days ✅ COMPLETE
- Week 2-3: Phase 2A Initial (Stories 2.3-2.7) - 1-2 weeks ✅ COMPLETE (52% accuracy)
- **Week 3-4: Phase 2A Course Correction (Stories 2.8-2.11) - 2-3 days** ⭐ CURRENT
- Week 4: AC3 Re-validation → Target ≥70% accuracy → Epic 2 COMPLETE
- **Total: 3-4 weeks (revised from 2-3 weeks)**

**If Course Correction Insufficient (<70%):**
- Week 1-4: Phase 1 + 2A (as above)
- Week 5-8: Phase 2B Remaining (Stories 2.12-2.13) - 3-4 weeks
- Week 8: AC3 Validation → ≥75% accuracy → Epic 2 COMPLETE
- **Total: 7-9 weeks**

**Worst Case (All paths):**
- Week 1-8: Phase 1 + 2A + 2B (as above)
- Week 9-14: Phase 2C (Hybrid Architecture) - 6 weeks
- Week 15-31: Phase 3 (Agentic Coordination) - 2-16 weeks (staged)
- **Total: 15-31 weeks**

**Most Likely Outcome:** 3-4 weeks (Phase 2A course correction achieves 65-75% accuracy) ✅

**Probability Analysis:**
- 80% chance: Course correction achieves 65-75% (Epic 2 complete or nearly complete)
- 15% chance: Need Phase 2B Stories 2.12-2.13 (cross-encoder re-ranking)
- 5% chance: Need Phase 2C (full hybrid architecture)

---

## Rationale

**Why This Pivot:**
- Element-aware chunking **catastrophic failure** (42% vs 56% baseline = -14pp)
- Research evidence: Fixed 512-token = 68.09% accuracy (Yepes et al. 2024)
- Production-proven approaches reduce risk (BlackRock, BNP Paribas, FinSage)
- Staged implementation with decision gates minimizes wasted effort

**Why Sequential Phases:**
- Test accuracy after EACH phase (decision gates prevent over-engineering)
- STOP when 70% achieved (Epic 2 success criteria)
- Start simple (fixed chunking), escalate only if needed (structured → hybrid → agentic)

**Why These Technologies:**
- pypdfium: Official Docling backend (1.7-2.5x speedup proven)
- Fixed chunking: Research-validated (68% accuracy guaranteed)
- Conditional tech: Approved contingency paths based on empirical decision gates

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-19 | 2.0 | Epic 2 complete rewrite after element-aware pivot | Product Owner (Sarah) |
| 2025-10-18 | 1.5 | Story 2.2 FAILED (42% accuracy) - pivot analysis | PM (John) + Dev (Amelia) |
| 2025-10-16 | 1.0 | Epic 2 created from implementation plan Option C Phase 2 | Scrum Master (Bob) |

---

**Epic Status:** IN PROGRESS
**Current Phase:** Phase 1 (PDF Optimization)
**Next Milestone:** T+2 (Phase 1 complete, Phase 2A start)
**Expected Completion:** T+17 (Week 3, Day 3 - AC3 Decision Gate)
