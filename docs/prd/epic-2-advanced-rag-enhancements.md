# Epic 2: Advanced RAG Enhancements (Phase 2)

**Status:** CONDITIONAL (only if Epic 1 baseline <90% retrieval or <95% attribution)
**Priority:** MEDIUM
**Duration:** 4-10 weeks (depends on how many stories needed)
**Goal:** Achieve 95-98% retrieval accuracy through incremental RAG improvements

**⚠️ IMPLEMENTATION STRATEGY:**
- Stories implemented **SEQUENTIALLY** (not parallel)
- Test **AFTER EACH** story
- **STOP** when 95% accuracy achieved
- Do NOT implement all 6 stories unless necessary

---

## Epic Overview

This epic contains 6 RAG enhancement stories that are implemented sequentially with decision gates after EACH story. Implementation **STOPS** when 95% accuracy is achieved.

**ONLY IMPLEMENT IF:**
- Story 1.15B baseline shows <90% retrieval accuracy OR <95% attribution accuracy

**Expected Progression:**
- Baseline (ACTUAL Post-Epic 1): 56.0% retrieval accuracy ⚠️ (Reality: 34-36pp below assumptions)
- After Story 2.1 (Hybrid Search): 56.0% accuracy ❌ FAILED - no improvement (whitespace tokenization inadequate)
- After Story 2.2 (Element Chunking): 64-68% accuracy (+8-12pp conservative estimate) ✅ Phase 1
- After Story 2.3 (Query Preprocessing): 74-76% accuracy (+6-8pp) ✅ Phase 2
- After Story 2.4 (Table Summarization): 78-80% accuracy (+4-6pp) ✅ Phase 3 → Epic 2 Target Exceeded

**Technologies Added:**
- sentence-transformers (cross-encoder re-ranking) ✅ Already in requirements
- OpenAI API (optional: embeddings, query expansion)
- FinBERT (optional: financial embeddings)
- Qdrant multi-collection support

---

## Story 2.1: Phase 2A - Hybrid Search (FAILED - PIVOT)

**Status:** ❌ CLOSED - Failed AC6 (56% accuracy vs ≥70% target)
**Date Closed:** 2025-10-18
**Outcome:** BM25 approach inadequate for financial documents with complex tables
**Root Cause:** Whitespace tokenization destroys table structure; length normalization bias; low BM25 coverage
**Decision:** PIVOT to Stories 2.2-2.4 (element-based chunking + query preprocessing + table summarization)
**Research Evidence:** Jimeno Yepes et al. (2024), Kim et al. (ICLR 2025), Min et al. (NAACL 2024)

**Goal (Original):** Combine semantic vector search with keyword matching for precision

**Lessons Learned:**
- ✅ Whitespace tokenization inadequate for financial domain (numbers split: "23.2 EUR/ton")
- ✅ BM25 length normalization bias inflates short chunk scores (confidentiality notices)
- ✅ Table structure lost in linear token streams (semantic coherence destroyed)
- ✅ Element-based chunking required for complex financial documents
- ✅ Research validation: +16.3pp page-level recall with element-aware boundaries (Jimeno Yepes et al.)

**As a** system,
**I want** to combine vector search with keyword matching and re-ranking,
**so that** queries with specific numbers or financial terms retrieve correct chunks with higher precision.

### Acceptance Criteria

1. **Post-search keyword re-ranking implemented** (2 hours)
   - Retrieve top-20 candidates via semantic search
   - Extract keywords from query (financial terms, numbers, units)
   - Score documents by keyword presence + semantic similarity
   - Re-rank to top-5 using combined score

2. **Scoring formula configured** (30 min)
   - Default: 70% semantic + 30% keyword (configurable)
   - Test alternative weights (80/20, 60/40) on ground truth
   - Document optimal weighting in completion notes

3. **Financial term detection** (1 hour)
   - Identify financial keywords: EBITDA, CAPEX, YTD, margins, EUR/ton
   - Boost scores for exact matches on numeric values
   - Case-insensitive matching for terms

4. **Integration with existing search** (30 min)
   - Update `retrieval/search.py` to support hybrid mode
   - Add `enable_hybrid` parameter to search functions
   - Default: hybrid=True for production

5. **Unit tests** (1 hour)
   - Test keyword extraction from queries
   - Test scoring formula variations
   - Test re-ranking logic

6. **Integration tests** (1 hour)
   - Test queries with exact numbers (e.g., "23.2 EUR/ton")
   - Verify correct chunks in top 3 (vs. semantic-only top 10)
   - Measure accuracy improvement on ground truth

7. **Accuracy validation** (30 min)
   - Run full ground truth test (50 queries)
   - Measure: Retrieval accuracy with hybrid search
   - Target: ≥92% (up from 85-89% baseline)

### Expected Impact

- +5-10% retrieval accuracy (better for queries with specific numbers/terms)
- Queries with "23.2", "50.6%", "EBITDA" will find correct chunks in top 3
- No latency impact (post-search re-ranking is fast)

### Decision Gate

- **IF ≥92%:** Continue to Story 2.2 (Financial Embeddings)
- **IF ≥95%:** STOP - Phase 2 complete, proceed to Epic 3

**Technologies:** Qdrant SDK (no new dependencies)

**Files Modified:**
- `raglite/retrieval/search.py` (+80 lines)
- `tests/unit/test_retrieval.py` (+100 lines)
- `tests/integration/test_retrieval_integration.py` (+80 lines)

---

## Story 2.2: Phase 2B - Element-Based Chunking Enhancement (1 week)

**Status:** ✅ READY FOR IMPLEMENTATION (Priority: HIGH - Critical path after Story 2.1 pivot)
**Research Foundation:** Jimeno Yepes et al. (2024) arXiv:2402.05131, Kim et al. (ICLR 2025) arXiv:2503.15191
**Detailed Specification:** `docs/stories/story-2.2-element-chunking.md` (1,144 lines)

**Goal:** Replace fixed 512-token chunking with structure-aware boundaries (tables, sections, paragraphs) using Docling's element detection

**As a** RAG system processing financial documents,
**I want** structure-aware chunking that respects element boundaries,
**so that** chunks preserve semantic coherence and improve retrieval accuracy from 56% to 64-68%.

### Acceptance Criteria

1. **Element-Aware Chunk Boundaries** (AC1) ⭐ CRITICAL
   - Chunks MUST NOT split tables mid-row (tables are indivisible units)
   - Chunks MUST NOT split section headers from their content
   - Tables <2,048 tokens stored as single chunk
   - Sections >512 tokens split at paragraph boundaries (not mid-sentence)

2. **Chunk Metadata Enhancement** (AC2) ⭐ CRITICAL
   - Add `element_type` field: "table" | "section" | "paragraph" | "list" | "mixed"
   - Add `section_title` field for context (e.g., "Revenue by Segment")
   - Preserve existing fields: `page_number`, `chunk_index`, `source_document`

3. **Retrieval Accuracy Validation** (AC3) ⭐ CRITICAL - DECISION GATE
   - Run 50-query ground truth test suite
   - **MANDATORY:** Retrieval accuracy ≥64.0% (32/50 queries pass) - minimum viable improvement
   - **TARGET:** Retrieval accuracy ≥68.0% (34/50 queries pass) - research-backed stretch goal
   - Attribution accuracy ≥45.0% (maintain or improve over 40% baseline)

4. **Performance & NFR Compliance** (AC4)
   - Ingestion time ≤30s per 100 pages (same as baseline)
   - Memory usage ≤4 GB during ingestion
   - p95 retrieval latency <10,000ms (NFR13)

5. **Backward Compatibility** (AC5)
   - Qdrant collection schema remains compatible (additive changes only)
   - `hybrid_search()` API signature unchanged
   - Existing queries work without modification

### Expected Impact

- **Accuracy:** 56% → 64-68% (+8-12pp conservative, based on Jimeno Yepes et al.)
- **Table Queries:** +15-25% improvement on number-heavy queries
- **Semantic Coherence:** Tables and sections preserved intact
- **Research Evidence:** +16.3pp page-level recall, +24.8% ROUGE, +80.8% BLEU (arXiv:2402.05131)

### Decision Gate

- **IF <64%:** ESCALATE to PM for strategy review (approach may be insufficient)
- **IF 64-68%:** PROCEED to Story 2.3 with caution flag
- **IF ≥68%:** PROCEED to Story 2.3 with high confidence

### Implementation Timeline (5-7 days)

- **Day 1-2:** Data models & Docling element extraction
- **Day 3-4:** Smart chunking algorithm (respect table/section boundaries)
- **Day 5:** Qdrant integration & metadata enhancement
- **Day 6:** End-to-end validation & accuracy testing
- **Day 7:** Documentation & handoff

**Technologies:** Docling (already approved) - ZERO new dependencies

**Files Modified:**
- `raglite/ingestion/pipeline.py` (~80 lines - element extraction + chunking)
- `raglite/shared/models.py` (~30 lines - ElementType enum, DocumentElement, Chunk enhancements)
- `tests/unit/test_element_extraction.py` (NEW - 150 lines)
- `tests/unit/test_element_chunking.py` (NEW - 150 lines)
- `tests/integration/test_element_metadata.py` (NEW - 100 lines)

---

## Story 2.3: Phase 2C - Query Preprocessing & Retrieval Optimization (2 weeks)

**Status:** 📋 PLANNED (depends on Story 2.2 achieving ≥65% accuracy)
**Research Foundation:** Kim et al. (ICLR 2025 Workshop) arXiv:2503.15191
**Detailed Specification:** `docs/epic-2-preparation/implementation-plan-stories-2.2-2.4.md` (lines 236-428)

**Goal:** Implement pre-retrieval query enhancement and post-retrieval optimization without fine-tuning embeddings

**Target Accuracy:** 68% → 74-76% (+6-8pp)
**Risk Level:** MEDIUM
**Effort:** 2 weeks

**As a** RAG system handling financial queries,
**I want** query preprocessing (financial acronym expansion, number normalization) and retrieval optimization (metadata boosting, chunk bundling),
**so that** retrieval accuracy improves from 68% to 74-76%.

### Key Features

1. **Query Rewriting for Financial Terms**
   - Expand acronyms: "EBITDA" → "EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization)"
   - Normalize numbers: "23.2" → "23.2 | twenty-three point two"
   - Expand units: "EUR/ton" → "EUR/ton | euros per ton"

2. **Metadata-Aware Filtering**
   - Number-heavy queries prioritize `element_type="table"` results
   - Trend queries ("change", "growth") expand to adjacent time periods
   - Section-aware boosting: "revenue" query boosts `section_title="Revenue"` chunks

3. **Chunk Bundling for Context**
   - Retrieve top-20 candidates, expand each with ±1 adjacent chunk (same section)
   - Re-rank expanded bundles using similarity threshold (tau=0.7)
   - Return top-5 after bundling

### Decision Gate

- **IF <74%:** Continue to Story 2.4 (Table Summarization)
- **IF ≥74% AND <70% original target:** Consider stopping (reassess Epic 2 target)
- **IF ≥74% AND meets 70% Epic 2 target:** MAY STOP (Epic 2 complete)

**Technologies:** ZERO new dependencies (Python stdlib + existing stack)

---

## Story 2.4: Phase 2D - Table-to-Text Summarization (3 weeks)

**Status:** 📋 PLANNED (depends on Story 2.3 achieving ≥74% but missing ≥78% stretch goal)
**Research Foundation:** Min et al. (NAACL 2024) ACL Anthology
**Detailed Specification:** `docs/epic-2-preparation/implementation-plan-stories-2.2-2.4.md` (lines 431-643)

**Goal:** Generate LLM summaries of financial tables; embed both raw table + summary for improved semantic matching

**Target Accuracy:** 74% → 78-80% (+4-6pp)
**Risk Level:** MEDIUM
**Effort:** 3 weeks
**Cost:** ~$0.60 per 160-page document (Claude 3.7 Sonnet API)

**As a** RAG system processing complex financial tables,
**I want** LLM-generated table summaries stored alongside raw tables,
**so that** semantic search finds tables via both structure and natural language descriptions.

### Key Features

1. **LLM-Based Table Summarization**
   - Use Claude 3.7 Sonnet API (already approved in tech stack)
   - Prompt: "Summarize this financial table in 2-3 sentences, focusing on key figures, trends, and insights"
   - Summary length: 50-150 words per table

2. **Dual Chunk Storage**
   - Store TWO chunks per table: (1) Raw Markdown table, (2) LLM summary
   - Link via `parent_chunk_id` metadata field
   - Enables both structured and semantic table retrieval

3. **Cost & Performance Monitoring**
   - Track API token usage per table
   - Monitor summarization latency (target: <5s per table)
   - Budget: <$10 per full corpus re-ingestion

### Decision Gate

- **IF ≥78%:** Epic 2 COMPLETE (exceeds 70% target, approaches 80%)
- **IF <78%:** ESCALATE to PM for Epic 2 strategy review

**Technologies:** Claude 3.7 Sonnet API (already approved) - ZERO new dependencies

---

## ⚠️ ARCHIVED STORIES (Pre-Pivot Approach - Phase 3+ Only)

The following stories (OLD 2.3-2.6) assumed a 90%+ baseline and are now **DEFERRED** after Story 2.1 pivot. They MAY be revisited in Phase 3+ if element-based approach (NEW Stories 2.2-2.4) proves insufficient to reach 90%+ accuracy.

---

## Story 2.5 (OLD 2.3): Phase 2C - Table-Aware Chunking (ARCHIVED - see NEW Story 2.2)

**Goal:** Preserve financial tables intact during chunking (prevent mid-table splits)

**As a** system,
**I want** to keep entire financial tables in single chunks with surrounding context,
**so that** tabular queries retrieve complete data without mid-table splits.

### Acceptance Criteria

1. **Docling TableItem detection** (2 hours)
   - Identify Docling `TableItem` objects during ingestion
   - Extract table boundaries (start/end positions)
   - Mark table chunks with metadata (`chunk_type="table"`)

2. **Table-aware chunking logic** (3 hours)
   - Keep entire table in single chunk (even if >500 words)
   - Include 2 sentences before table (context)
   - Include 2 sentences after table (context)
   - Preserve table structure in chunk text

3. **Table chunk boosting** (1 hour)
   - Add `chunk_type` metadata field to Chunk model
   - Boost table chunks in search (1.2x score multiplier)
   - Prioritize table chunks for tabular queries

4. **Unit tests** (2 hours)
   - Test table detection from Docling output
   - Test chunking preserves full tables
   - Test context inclusion (before/after sentences)

5. **Integration tests** (2 hours)
   - Test end-to-end ingestion with tables
   - Verify: Tables no longer split mid-row
   - Verify: Table queries retrieve table chunks first

6. **Validation** (30 min)
   - Run full ground truth test with table-aware chunking
   - Measure: Retrieval accuracy on tabular queries
   - Target: ≥95% (up from 94-96%)

### Expected Impact

- +5-8% accuracy on tabular queries
- +15-20% accuracy on table-specific questions
- No performance degradation (larger chunks, but fewer total chunks)

### Decision Gate

- **IF ≥95%:** STOP - Phase 2 complete, proceed to Epic 3
- **IF <95%:** Continue to Story 2.4 (Cross-Encoder Re-ranking)

**Technologies:** Docling TableItem API (already available)

**Files Modified:**
- `raglite/ingestion/pipeline.py` (+120 lines - table detection + chunking)
- `raglite/shared/models.py` (+10 lines - chunk_type field)
- `raglite/retrieval/search.py` (+30 lines - table boosting)
- `tests/unit/test_ingestion.py` (+150 lines)
- `tests/integration/test_ingestion_integration.py` (+100 lines)

---

## Story 2.4: Phase 2D - Cross-Encoder Re-ranking (6-8 hours)

**Goal:** Add second-stage re-ranking with cross-encoder for improved precision

**As a** system,
**I want** to re-rank top-20 vector search results using a cross-encoder model,
**so that** the final top-5 results have higher relevance precision.

### Acceptance Criteria

1. **Cross-encoder model integration** (2 hours)
   - Load model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
   - Implement two-stage retrieval:
     - Stage 1: Vector search → retrieve top-20 candidates
     - Stage 2: Cross-encoder → re-rank to top-5

2. **Re-ranking logic** (2 hours)
   - Process query+document pairs through cross-encoder
   - Generate relevance scores (0-1) for each pair
   - Sort by cross-encoder scores, return top-5

3. **Performance optimization** (1 hour)
   - Batch processing for cross-encoder (process 20 pairs at once)
   - Measure latency impact (expect +150-200ms)
   - Verify: Total latency still <10s (NFR5)

4. **Unit tests** (1 hour)
   - Test cross-encoder scoring
   - Test re-ranking logic

5. **Integration tests** (1 hour)
   - Test two-stage retrieval end-to-end
   - Verify: Top-5 more relevant than vector-only
   - Measure: Precision@5 improvement

6. **Validation** (30 min)
   - Run full ground truth test with cross-encoder
   - Measure: Retrieval accuracy, precision@5
   - Target: ≥95% (up from previous stage)

### Expected Impact

- +3-5% precision improvement (top-5 more accurate)
- +150ms latency (acceptable, still <10s total)
- More robust to query phrasing variations

### Decision Gate

- **IF ≥95%:** STOP - Phase 2 complete, proceed to Epic 3
- **IF <95%:** Continue to Story 2.5 (Query Expansion)

**Technologies:** sentence-transformers (cross-encoder)

**Files Modified:**
- `raglite/shared/clients.py` (+40 lines - cross-encoder singleton)
- `raglite/retrieval/search.py` (+100 lines - two-stage retrieval)
- `tests/unit/test_retrieval.py` (+80 lines)
- `tests/integration/test_retrieval_integration.py` (+60 lines)

---

## Story 2.5: Phase 2E - Query Expansion (4-6 hours, OPTIONAL)

**Goal:** Expand queries with synonyms and related terms for better recall

**As a** system,
**I want** to generate 3-5 query variations and fuse results,
**so that** queries with synonyms or paraphrases find relevant content.

### Acceptance Criteria

1. **Claude API query expansion** (2 hours)
   - Use Claude API to generate 3-5 query variations
   - Example: "variable costs" → ["variable expenses", "variable costs EUR/ton", "cost per ton"]
   - Prompt engineering for financial domain

2. **Parallel search implementation** (1 hour)
   - Search with each variation (parallel execution)
   - Collect all results (3-5 result sets)

3. **Reciprocal Rank Fusion (RRF)** (2 hours)
   - Fuse results using RRF algorithm
   - Rank documents by fused scores
   - Return top-k from fused results

4. **Unit tests** (1 hour)
   - Test query expansion
   - Test RRF fusion

5. **Integration tests** (1 hour)
   - Test end-to-end query expansion pipeline
   - Verify: Queries with synonyms find content
   - Measure: Recall improvement

6. **Validation** (30 min)
   - Run full ground truth test with query expansion
   - Measure: Retrieval accuracy, recall
   - Target: ≥95% (up from previous stage)

### Expected Impact

- +2-5% recall improvement
- +500-800ms latency (parallel searches + LLM call)
- More robust to query phrasing variations

### Decision Gate

- **IF ≥95%:** STOP - Phase 2 complete
- **IF <95%:** Continue to Story 2.6 (Multi-Vector)

**Technologies:** Anthropic API (Claude for query expansion)

**Files Modified:**
- `raglite/retrieval/search.py` (+150 lines - query expansion + RRF)
- `tests/unit/test_retrieval.py` (+100 lines)
- `tests/integration/test_retrieval_integration.py` (+80 lines)

---

## Story 2.6: Phase 2F - Multi-Vector Representations (12-16 hours, OPTIONAL)

**Goal:** Store multiple embeddings per chunk (content, keywords, summary) for robustness

**As a** system,
**I want** to generate 3 vector representations per chunk and search all collections,
**so that** different query styles (keyword, semantic, conceptual) all achieve high accuracy.

### Acceptance Criteria

1. **Multi-vector generation** (4 hours)
   - Generate 3 representations per chunk:
     1. Content vector: Full chunk text (current approach)
     2. Keyword vector: LLM-extracted keywords only
     3. Summary vector: LLM-generated 2-3 sentence summary
   - Use Claude API for keyword/summary extraction

2. **Qdrant multi-collection setup** (3 hours)
   - Create 3 Qdrant collections: `content`, `keywords`, `summary`
   - Store embeddings in separate collections
   - Link chunks via `chunk_id` metadata

3. **Multi-collection search** (3 hours)
   - Search all 3 collections in parallel
   - Fuse results using RRF
   - Return top-k from fused results

4. **Unit tests** (2 hours)
   - Test multi-vector generation
   - Test multi-collection storage

5. **Integration tests** (2 hours)
   - Test end-to-end multi-vector pipeline
   - Verify: Different query styles achieve high accuracy
   - Measure: Accuracy improvement

6. **Validation** (1 hour)
   - Run full ground truth test with multi-vector
   - Measure: Retrieval accuracy across query types
   - Target: ≥98% (exceeds NFR6/NFR7)

### Expected Impact

- +5-10% accuracy across varied query styles
- +3x storage (3 collections instead of 1)
- +3x ingestion time (generate 3 representations)
- More robust to query phrasing variations

### Decision Gate

- **IF ≥98%:** Phase 2 complete (advanced optimization achieved)

**Technologies:** Qdrant multi-collection, Claude API (keyword/summary extraction)

**Files Modified:**
- `raglite/ingestion/pipeline.py` (+200 lines - multi-vector generation)
- `raglite/retrieval/search.py` (+150 lines - multi-collection search)
- `tests/unit/test_ingestion.py` (+150 lines)
- `tests/unit/test_retrieval.py` (+120 lines)
- `tests/integration/test_retrieval_integration.py` (+100 lines)

---

## Epic 2 Success Criteria

**Overall Epic Success:**
- ✅ 95%+ retrieval accuracy (exceeds NFR6)
- ✅ 95%+ attribution accuracy (meets NFR7)
- ✅ <10s response time maintained (NFR5)
- ✅ Sequential implementation with decision gates
- ✅ STOP when 95% achieved (prevent over-engineering)

**Technologies Summary:**
- sentence-transformers (cross-encoder re-ranking)
- OpenAI API (optional: embeddings, query expansion)
- FinBERT (optional: financial embeddings)
- Qdrant multi-collection support
- Anthropic API (query expansion, keyword/summary extraction)

---

## Decision Gates Summary

### NEW Approach (Post-Pivot, 2025-10-18)

| Story | Expected Accuracy | Decision |
|-------|------------------|----------|
| **Baseline (Post-Epic 1)** | 56.0% | PIVOT to element-based approach |
| **2.1 (Hybrid Search)** | 56.0% ❌ | FAILED - whitespace tokenization inadequate → PIVOT |
| **2.2 (Element Chunking)** | 64-68% | IF <65% ESCALATE; IF ≥68% high confidence to 2.3 |
| **2.3 (Query Preprocessing)** | 74-76% | IF ≥70% MAY STOP (Epic 2 target met); else continue to 2.4 |
| **2.4 (Table Summarization)** | 78-80% | Epic 2 COMPLETE (exceeds 70% target) |

**Most Likely Outcome:** STOP after Story 2.3 or 2.4 with 74-80% accuracy ✅

### OLD Approach (Pre-Pivot - ARCHIVED)

The following progression assumed 90%+ baseline and is now DEFERRED:

| Story | Expected Accuracy | Status |
|-------|------------------|--------|
| 2.5 (OLD 2.3 - Table-Aware) | 95-97% | ARCHIVED - see NEW Story 2.2 |
| 2.6 (OLD 2.4 - Cross-Encoder) | 96-98% | DEFERRED to Phase 3+ |
| 2.7 (OLD 2.5 - Query Expansion) | 96-98% | DEFERRED to Phase 3+ |
| 2.8 (OLD 2.6 - Multi-Vector) | 98%+ | DEFERRED to Phase 3+ |

---

## Epic 2 Dependencies

**Prerequisites:**
- ✅ Epic 1 complete (Stories 1.1-1.15B)
- ✅ Story 1.15B baseline validation executed
- ✅ Baseline <90% retrieval OR <95% attribution (triggers Epic 2)

**Blocks:**
- Epic 3 (Intelligence Features) - needs Epic 2 complete if baseline <90%

---

## Rationale

**Why Epic 2 is Conditional:**
- Prevents over-engineering if baseline already meets NFR6/NFR7
- Allows data-driven decision based on Story 1.15B results
- Incremental approach with decision gates maximizes efficiency

**Why Sequential Implementation:**
- Test after EACH enhancement to measure impact
- STOP when 95% achieved (prevent unnecessary work)
- Each story builds on previous improvements

**Why These 6 Stories:**
- Based on RAG best practices and research
- Proven techniques for improving retrieval accuracy
- Incremental complexity (simple → advanced)

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-16 | 1.0 | Epic 2 created from implementation plan Option C Phase 2 | Scrum Master (Bob) |
