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
- Baseline (Option C): 90-92% retrieval accuracy
- After Story 2.1 (Hybrid Search): 92-94% accuracy
- After Story 2.2 (Financial Embeddings): 94-96% accuracy → Likely STOP here ✅
- After Story 2.3 (Table-Aware Chunking): 95-97% accuracy
- After Story 2.4+ (Cross-Encoder, Query Expansion, Multi-Vector): 96-98%+ accuracy

**Technologies Added:**
- sentence-transformers (cross-encoder re-ranking) ✅ Already in requirements
- OpenAI API (optional: embeddings, query expansion)
- FinBERT (optional: financial embeddings)
- Qdrant multi-collection support

---

## Story 2.1: Phase 2A - Hybrid Search (4-6 hours)

**Goal:** Combine semantic vector search with keyword matching for precision

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

## Story 2.2: Phase 2B - Financial Embeddings Evaluation (6-8 hours)

**Goal:** Evaluate financial domain-specific embeddings vs. general E5 embeddings

**As a** system,
**I want** to test if financial domain-specific embeddings improve retrieval accuracy,
**so that** queries with financial terminology find semantically relevant chunks more accurately.

### Acceptance Criteria

1. **Embedding model options researched** (1 hour)
   - Option 1: OpenAI text-embedding-3-large (API, 3072-dim, $0.13/1M tokens)
   - Option 2: FinBERT (local, 768-dim, finance-trained, free)
   - Option 3: Baseline E5-large-v2 (current, 1024-dim, general purpose)
   - Document pros/cons of each

2. **A/B testing setup** (2 hours)
   - Re-ingest PDF with each embedding model (3 separate Qdrant collections)
   - Run accuracy tests on all 50 ground truth queries for each model
   - Compare: Retrieval accuracy, cost, latency

3. **OpenAI embeddings tested** (1 hour)
   - API integration: `openai.embeddings.create()`
   - Measure: Accuracy, cost ($), latency (ms)
   - Store results in comparison table

4. **FinBERT embeddings tested** (1 hour)
   - HuggingFace model: `ProsusAI/finbert`
   - Measure: Accuracy, cost (free), latency (ms)
   - Store results in comparison table

5. **Comparison analysis** (1 hour)
   - Generate report: Accuracy vs. Cost vs. Latency
   - Identify: Best model for financial queries
   - Decision: Adopt new model if improvement >5%

6. **Model adoption (conditional)** (2 hours)
   - IF new model >+5% accuracy: Update pipeline
   - Re-ingest all documents with new embeddings
   - Update configuration to use new model
   - Document migration in completion notes

7. **Validation** (30 min)
   - Run full ground truth test with adopted model
   - Measure: Retrieval accuracy with new embeddings
   - Target: ≥95% (up from 92-94%)

### Expected Impact

- +10-15% accuracy on financial terminology queries
- Better understanding of domain-specific vs. general embeddings
- Cost-benefit analysis for production deployment

### Decision Gate

- **IF ≥95%:** STOP - Phase 2 complete, proceed to Epic 3
- **IF <95%:** Continue to Story 2.3 (Table-Aware Chunking)

**Technologies:** OpenAI API (optional), FinBERT from HuggingFace (optional)

**Files Modified:**
- `raglite/shared/clients.py` (add embedding model selection)
- `raglite/ingestion/pipeline.py` (support multiple embedding models)
- `scripts/embedding-comparison-report.py` (NEW - 200 lines)
- `docs/embedding-comparison-results.md` (NEW - comparison report)

---

## Story 2.3: Phase 2C - Table-Aware Chunking (8-10 hours)

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

| Story | Expected Accuracy | Decision |
|-------|------------------|----------|
| Baseline | 90-92% | Continue to 2.1 |
| **2.1 (Hybrid Search)** | 92-94% | IF ≥95% STOP, else continue to 2.2 |
| **2.2 (Financial Embeddings)** | 94-96% | IF ≥95% STOP, else continue to 2.3 |
| **2.3 (Table-Aware Chunking)** | 95-97% | IF ≥95% STOP, else continue to 2.4 |
| **2.4 (Cross-Encoder)** | 96-98% | IF ≥95% STOP, else continue to 2.5 |
| **2.5 (Query Expansion)** | 96-98% | IF ≥95% STOP, else continue to 2.6 |
| **2.6 (Multi-Vector)** | 98%+ | Phase 2 COMPLETE |

**Most Likely Outcome:** STOP after Story 2.2 (Financial Embeddings) with 94-96% accuracy ✅

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
