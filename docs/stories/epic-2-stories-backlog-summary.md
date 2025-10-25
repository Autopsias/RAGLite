# Epic 2: Stories Backlog Summary

**Epic:** Epic 2: Advanced RAG Architecture Enhancement
**Status:** CRITICAL (blocks Epic 3-5)
**Created:** 2025-10-19
**Purpose:** Backlog summary for creating Stories 2.1-2.5 in project management system

---

## Story 2.1: Implement pypdfium Backend for Docling (Phase 1)

**Priority:** 🔴 CRITICAL (blocks Phase 2A)
**Effort:** 4 hours
**Timeline:** Week 1, Day 1 (T+0 to T+0.5)
**Phase:** Phase 1 - PDF Ingestion Performance Optimization

**User Story:**
As a developer, I want to replace the default PDF.js backend with pypdfium for Docling, so that PDF processing uses 50-60% less memory and runs faster for iterative testing.

**Acceptance Criteria:**
1. **AC1: Docling Backend Configuration** (1 hour)
   - Configure `PdfiumBackend` in `raglite/ingestion/pipeline.py`
   - Remove default PDF.js backend configuration
   - Validate backend switch successful

2. **AC2: Memory Usage Validation** (1 hour)
   - Measure memory usage before/after pypdfium switch
   - Validate 50-60% memory reduction vs PDF.js baseline
   - Document memory footprint in test results

3. **AC3: Table Accuracy Validation** (1 hour)
   - Re-run AC1 test suite (20 ground truth table queries)
   - Validate 97.9% table extraction accuracy maintained
   - No regressions from baseline Docling behavior

4. **AC4: Performance Baseline** (1 hour)
   - Measure ingestion speed for sample PDF (2025-08 Performance Review)
   - Document baseline: pages/min, total time, chunk count
   - Validate pypdfium ≥1.0x speed (no regression, speedup comes in Story 2.2)

**Dependencies:**
- Docling 2.0+ installed (already in tech stack)
- pypdfium2 package installed

**Success Metrics:**
- Memory usage reduced by 50-60%
- Table accuracy ≥97.9% (no regression)
- Ingestion speed ≥baseline (no slowdown)

**Notes:**
- This story focuses on memory optimization, not speed optimization
- Speed optimization comes in Story 2.2 (parallelism)
- Prepares for faster iteration testing in Phase 2A

---

## Story 2.2: Implement Page-Level Parallelism (4-8 Threads) (Phase 1)

**Priority:** 🔴 CRITICAL (blocks Phase 2A)
**Effort:** 8 hours
**Timeline:** Week 1, Day 1-2 (T+0.5 to T+1.5)
**Phase:** Phase 1 - PDF Ingestion Performance Optimization

**User Story:**
As a developer, I want to enable page-level parallelism in Docling, so that PDF ingestion is 1.7-2.5x faster and enables rapid testing of chunking strategies in Phase 2A.

**Acceptance Criteria:**
1. **AC1: Parallel Processing Configuration** (2 hours)
   - Add `max_num_workers=8` to Docling `DocumentConverter` config
   - Enable page-level parallelism in `raglite/ingestion/pipeline.py`
   - Validate parallel processing engaged (log thread usage)

2. **AC2: Performance Validation** (2 hours) ⭐ MANDATORY
   - Re-run ingestion on sample PDF with parallelism enabled
   - Measure speedup vs Story 2.1 baseline (single-threaded pypdfium)
   - **MANDATORY:** 1.7-2.5x speedup achieved (e.g., 8.2 min → 3.3-4.8 min)

3. **AC3: Accuracy Validation** (2 hours) ⭐ MANDATORY
   - Re-run AC1 test suite (20 ground truth table queries)
   - **MANDATORY:** 97.9% table accuracy maintained (no regression from parallelism)
   - Validate chunk count consistency with baseline

4. **AC4: Thread Safety Validation** (2 hours)
   - Run ingestion 3 times with parallelism enabled
   - Validate deterministic output (same chunk count, same embeddings)
   - Validate no race conditions or data corruption

**Dependencies:**
- Story 2.1 complete (pypdfium backend)

**Success Metrics:**
- Speedup: 1.7-2.5x vs baseline ✅
- Table accuracy: ≥97.9% (no regression) ✅
- Deterministic output across runs ✅

**Notes:**
- **Phase 1 COMPLETE** after this story
- Enables rapid iteration testing in Phase 2A (fixed chunking)
- Combined Phase 1 speedup: 1.7-2.5x (best case 8.2 min → 3.3 min)

---

## Story 2.3: Refactor Chunking Strategy to Fixed 512-Token Approach (Phase 2A)

**Priority:** 🔴 CRITICAL (blocks Epic 3)
**Effort:** 16 hours
**Timeline:** Week 2, Day 1-2 (T+3 to T+5)
**Phase:** Phase 2A - Research-Validated Fixed Chunking

**User Story:**
As a developer, I want to replace element-aware chunking with research-validated fixed 512-token chunks, so that retrieval accuracy increases from 42% to 68-72% (Yepes et al. 2024 validated approach).

**Acceptance Criteria:**
1. **AC1: Fixed Tokenization Implementation** (4 hours)
   - Install `tiktoken` (OpenAI tokenizer) for consistent token counting
   - Implement fixed 512-token chunking in `raglite/ingestion/pipeline.py`
   - Remove element-based chunking logic (table-aware splitting removed)
   - Add 10% overlap (51 tokens) per Yepes et al. 2024 best practices

2. **AC2: Chunk Generation Validation** (2 hours)
   - Re-ingest sample PDF with fixed chunking
   - Validate chunk count reduced vs element-aware baseline (504 → ~300-350)
   - Validate chunks are 512 tokens ±5% (due to sentence boundary alignment)
   - Document chunk statistics: count, avg tokens, overlap

3. **AC3: Baseline Accuracy Test** (4 hours)
   - Re-run AC3 test suite (50 ground truth queries, extended from 20)
   - Measure retrieval accuracy with fixed 512-token chunks
   - **Target:** 68-72% accuracy (Yepes et al. 2024 expected range)
   - Document accuracy improvement vs element-aware baseline (42%)

4. **AC4: Table Handling Validation** (3 hours)
   - Manually inspect 5 table-heavy chunks from sample PDF
   - Validate tables split mid-row handled gracefully (LLM synthesis compensates)
   - Test 5 table-specific queries to ensure no catastrophic regression
   - Document table handling behavior and known limitations

5. **AC5: Performance Validation** (3 hours)
   - Measure ingestion time with fixed chunking vs element-aware
   - Validate speedup maintained from Phase 1 (1.7-2.5x vs original baseline)
   - Measure query latency: ensure <15s p95 maintained (NFR13)

**Dependencies:**
- Story 2.2 complete (parallelism)
- tiktoken package installed

**Success Metrics:**
- Retrieval accuracy: 68-72% (26-30pp improvement vs 42% baseline) ✅
- Chunk count reduced: ~300-350 chunks (vs 504 element-aware) ✅
- Ingestion speed: 1.7-2.5x vs original baseline ✅

**Notes:**
- **CRITICAL:** This story implements the research-validated approach from Yepes et al. 2024
- Removes over-fragmentation issue (504 → ~320 chunks)
- Prepares for Story 2.4 (LLM metadata injection)

---

## Story 2.4: Add LLM-Generated Contextual Metadata Injection (Phase 2A)

**Priority:** 🔴 CRITICAL (blocks Story 2.5 decision gate)
**Effort:** 12 hours
**Timeline:** Week 2, Day 3 - Week 3, Day 1 (T+5 to T+7)
**Phase:** Phase 2A - Research-Validated Fixed Chunking

**User Story:**
As a developer, I want to inject LLM-generated contextual metadata into each chunk, so that retrieval accuracy improves by 3-5pp through better semantic understanding (70-75% target range).

**Acceptance Criteria:**
1. **AC1: Contextual Prepending Implementation** (4 hours)
   - Implement LLM call (Claude 3.7 Sonnet) to generate 1-2 sentence chunk context
   - Prepend generated context to each chunk before embedding
   - Add retry logic and error handling for LLM API failures
   - Document metadata generation prompt template

2. **AC2: Cost and Latency Validation** (2 hours)
   - Measure LLM API cost per chunk (Claude 3.7 Sonnet pricing)
   - Measure added latency to ingestion pipeline
   - Validate cost acceptable for POC scope (<$10 for sample PDF)
   - Document cost/latency tradeoffs

3. **AC3: Accuracy Improvement Test** (4 hours)
   - Re-ingest sample PDF with contextual metadata enabled
   - Re-run AC3 test suite (50 ground truth queries)
   - **Target:** 70-75% accuracy (3-5pp improvement vs Story 2.3 baseline)
   - Document metadata impact on retrieval quality

4. **AC4: Metadata Quality Spot Check** (2 hours)
   - Manually inspect 10 random chunks and their generated metadata
   - Validate metadata accurately summarizes chunk content and document context
   - Validate no hallucinations or misleading context injected
   - Document metadata quality observations

**Dependencies:**
- Story 2.3 complete (fixed chunking)
- Claude API access configured

**Success Metrics:**
- Retrieval accuracy: 70-75% (3-5pp improvement vs 68-72% baseline) ✅
- LLM cost per PDF: <$10 (POC acceptable) ✅
- Metadata quality: 90%+ accurate on spot check ✅

**Notes:**
- Based on Yepes et al. 2024 "Contextual Prepending" technique
- Critical for achieving 70%+ accuracy threshold in Story 2.5
- Prepares for Story 2.5 DECISION GATE

---

## Story 2.5: AC3 Validation and Optimization (Target: ≥70% Accuracy) - DECISION GATE (Phase 2A)

**Priority:** 🔴 CRITICAL (Epic 2 completion gate)
**Effort:** 8 hours
**Timeline:** Week 3, Day 2-3 (T+15 to T+17)
**Phase:** Phase 2A - Research-Validated Fixed Chunking

**User Story:**
As a Product Owner, I want to validate retrieval accuracy against the 70% threshold using the full AC3 test suite, so that I can determine if Epic 2 is complete or requires escalation to Phase 2B contingency.

**Acceptance Criteria:**
1. **AC1: Full Test Suite Execution** (2 hours)
   - Execute AC3 test suite (50 ground truth queries) with fixed chunking + metadata
   - Measure retrieval accuracy, precision, recall, F1 score
   - Document per-query results and failure analysis
   - Generate test report with detailed metrics

2. **AC2: DECISION GATE - Retrieval Accuracy ≥70%** (30 min) ⭐ MANDATORY
   - **MANDATORY:** Retrieval accuracy ≥70.0% (35/50 queries pass)
   - **This is the DECISION GATE for Epic 2 completion**
   - IF ≥70% → Epic 2 COMPLETE, proceed to Epic 3
   - IF <70% → Escalate to PM for Phase 2B approval (Structured Multi-Index)

3. **AC3: Query Failure Analysis** (2 hours)
   - Categorize failed queries by failure mode (multi-hop, numerical, ambiguous)
   - Identify root causes for top 5 failure queries
   - Document whether failures are addressable in Phase 2B or Phase 2C
   - Generate recommendations for PM decision

4. **AC4: Performance Validation** (2 hours)
   - Measure end-to-end query latency (ingestion to answer synthesis)
   - Validate <15s p95 latency maintained (NFR13)
   - Measure ingestion time for sample PDF (validate 1.7-2.5x speedup maintained)
   - Document performance metrics for Epic 2 summary

5. **AC5: Stretch Goal - Source Attribution Validation** (1.5 hours)
   - Test source citation accuracy on 20 queries
   - Validate ≥95% attribution accuracy (NFR7)
   - Document citation quality and failure modes

**Dependencies:**
- Story 2.4 complete (contextual metadata)
- AC3 test suite (50 ground truth queries) ready

**Success Metrics:**
- **MANDATORY:** Retrieval accuracy ≥70.0% (35/50 queries) ✅
- Query latency: <15s p95 (NFR13) ✅
- Attribution accuracy: ≥95% (NFR7 - stretch) ✅

**DECISION GATE OUTCOMES:**

**IF ≥70% accuracy:**
- ✅ **Epic 2 COMPLETE**
- ✅ Epic 3-5 UNBLOCKED
- ✅ Phase 2B-C skipped (5% probability realized)
- ✅ Project proceeds on 2-3 week timeline (best case)

**IF <70% accuracy:**
- ⚠️ **Escalate to PM (John)**
- ⚠️ Request approval for Phase 2B (Structured Multi-Index)
- ⚠️ Timeline extends to 6-7 weeks (Phase 2B contingency)
- ⚠️ Root cause analysis required (why did research-validated approach fail?)

**Notes:**
- **This is the CRITICAL decision gate for Epic 2**
- Expected outcome: 70-75% accuracy (Yepes et al. 2024 validated)
- IF failed: Indicates dataset-specific challenges requiring structured approach
- Timeline: T+17 (Week 3, Day 3) - absolute latest decision point

---

## Backlog Creation Instructions

**For PM or Backlog Manager:**

1. Create 5 new stories in project management system (Jira, Azure DevOps, etc.)
2. Use story titles exactly as written above
3. Set Priority: 🔴 CRITICAL for all 5 stories
4. Set Epic Link: Epic 2 - Advanced RAG Architecture Enhancement
5. Set Dependencies:
   - Story 2.2 depends on Story 2.1
   - Story 2.3 depends on Story 2.2
   - Story 2.4 depends on Story 2.3
   - Story 2.5 depends on Story 2.4
6. Set Timeline:
   - Stories 2.1-2.2: Week 1 (Phase 1 - 1-2 days)
   - Stories 2.3-2.4: Week 2-3 (Phase 2A - 1-2 weeks)
   - Story 2.5: Week 3 Day 2-3 (DECISION GATE - T+17)
7. Copy acceptance criteria verbatim from this document
8. Add labels: `epic-2`, `phase-1` (for 2.1-2.2), `phase-2a` (for 2.3-2.5), `decision-gate` (for 2.5)

**Estimated Total Effort:** 48 hours (6 days)
**Estimated Timeline:** 2-3 weeks (includes testing, iteration, decision gate)
**Success Probability:** 95% (Yepes et al. 2024 validated approach)

---

**Document Status:** ✅ READY FOR BACKLOG CREATION
**Last Updated:** 2025-10-19
**Owner:** Product Owner (Sarah)
**Next Action:** Create Stories 2.1-2.5 in backlog, notify Dev (Amelia) when ready to start Phase 1
