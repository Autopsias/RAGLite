# 8. Phased Implementation Strategy (v1.1 Simplified)

## Phase 1: Monolithic MVP (Week 0 + Weeks 1-5)

**Goal:** Working Q&A system with 90%+ retrieval accuracy

**⚠️ UPDATED TIMELINE: 5 weeks (was 4) + Week 0 Integration Spike - Risk mitigation for solo dev + novel technology integration**

**Week 0: Integration Spike (3-5 days) - MANDATORY**

**Goal:** Validate technology stack before committing to Phase 1

**Tasks:**
- Ingest 1 real financial PDF (100+ pages) with Docling
- Generate Fin-E5 embeddings and store in Qdrant
- Implement minimal FastMCP server with query tool
- Create 15 ground truth Q&A pairs
- Measure baseline retrieval accuracy

**Success Criteria (GO/NO-GO for Phase 1):**
- ✅ **GO:** Baseline accuracy ≥70% (10+ out of 15 queries work)
- ✅ **GO:** End-to-end integration functional
- ⚠️ **REASSESS:** 50-69% accuracy → Debug before proceeding
- 🛑 **NO-GO:** <50% accuracy → Reconsider technology choices

**Deliverable:** Week 0 Spike Report + decision to proceed/pivot

---

**Week 1: Ingestion Pipeline**
- Files to create: `main.py`, `ingestion/pipeline.py`, `config.py`
- Features:
  - ✅ PDF extraction (Docling)
  - ✅ Simple chunking (500 words, 50 overlap)
  - ✅ Fin-E5 embedding generation
  - ✅ Qdrant storage
- Deliverable: `ingest_financial_document()` MCP tool works

**Week 2: Retrieval & Search**
- Files to create: `retrieval/search.py`, `retrieval/attribution.py`
- Features:
  - ✅ Vector similarity search (Qdrant)
  - ✅ Source attribution (document, page, section)
  - ✅ Basic result ranking
- Deliverable: `query_financial_documents()` returns relevant chunks

**Week 3: LLM Synthesis**
- Files to create: `retrieval/synthesis.py`
- Features:
  - ✅ Claude API integration
  - ✅ Answer synthesis from chunks
  - ✅ Citation formatting
  - ✅ OPTIONAL: Contextual Retrieval (upgrade chunking if time permits)
- Deliverable: Natural language answers with source citations

**Week 4: LLM Synthesis & Integration**
- Continue synthesis work from Week 3
- Integration testing across all components
- **Daily accuracy checks:** Run 10-15 test queries, track trend line

**Week 5: Accuracy Validation & Decision Gate**
- Files to create: `tests/ground_truth.py` (if not already done in Week 1)
- Tasks:
  - ✅ Run full ground truth test set (50+ queries)
  - ✅ Manual accuracy validation
  - ✅ Performance measurement (<10s response)
  - ✅ User testing with real documents
  - ✅ Document failure modes and root causes
- Deliverable: Validation report + Phase 2 decision

**Success Criteria:**
- ✅ Can ingest 5 financial PDFs successfully (≥4/5 succeed)
- ✅ 90%+ retrieval accuracy on 50+ query test set (NFR6)
- ✅ 95%+ source attribution accuracy (NFR7)
- ✅ Query response time <10 seconds (≥8/10 queries)
- ✅ All answers include source citations (50/50)

**Decision Gate (End of Story 1.15B - Baseline Validation):**

**IF Retrieval ≥90% AND Attribution ≥95%:**
- ✅ **EPIC 1 VALIDATED** → Proceed to Epic 3/Phase 3 (Intelligence Features)
- ✅ **SKIP Epic 2/Phase 2** (RAG Enhancements)

**IF Retrieval 85-89% OR Attribution 93-94%:**
- ⚠️ **CLOSE TO TARGETS** → Implement Epic 2, Story 2.1 only (Hybrid Search)
- **Expected:** Story 2.1 alone should push accuracy to 92%+, re-validate
- If still <90% after 2.1: Continue to Stories 2.2 → 2.3

**IF Retrieval <85% OR Attribution <93%:**
- ✗ **NEEDS EPIC 2** → Implement Stories 2.1 → 2.2 → 2.3 sequentially
- **Analyze:** Failure patterns guide priority (hybrid search? embeddings? table chunking?)
- **STOP when 95% achieved** (don't implement all 6 stories if not needed)

**Technologies:**
- FastMCP, Docling, Fin-E5, Qdrant, Claude 3.7 Sonnet
- Docker Compose (Qdrant + app)
- pytest for basic testing

**Phase 2 (Conditional Technologies):**
- sentence-transformers (cross-encoder re-ranking) ✅ Already in requirements
- OpenAI API (optional: text-embedding-3-large for financial embeddings, query expansion)
- FinBERT (optional: HuggingFace financial domain embeddings)
- Qdrant multi-collection support (multi-vector representations)

## Phase 2: Advanced RAG Enhancements (Weeks 6-10) - CONDITIONAL

**⚠️ ONLY IMPLEMENT IF STORY 1.15B DECISION GATE TRIGGERS (Baseline <90% retrieval or <95% attribution)**

**Goal:** Achieve 95-98% retrieval accuracy through incremental RAG improvements

**Strategy:** Implement stories **sequentially**, test after **EACH** enhancement, **STOP when 95% achieved**

**For detailed story definitions:** See `docs/prd/epic-2-advanced-rag-enhancements.md`

---

### Story 2.1: Phase 2A - Hybrid Search (4-6 hours)

**Goal:** Combine semantic vector search with keyword matching for precision

**Implementation:**
- Post-search keyword re-ranking (retrieve top-20, re-rank to top-5)
- Extract keywords from query (financial terms, numbers, units)
- Score documents by keyword presence + semantic similarity
- Combine scores: 70% semantic + 30% keyword (configurable)

**Expected Impact:** +5-10% retrieval accuracy (better for queries with specific numbers/terms)

**Technologies:** Qdrant SDK (no new dependencies)

**Success Criteria:**
- Queries with exact numbers (e.g., "23.2 EUR/ton") retrieve correct chunks in top 3
- Financial terms (EBITDA, CAPEX, YTD) boost relevant documents
- Accuracy tests show ≥92% retrieval accuracy (up from 85-89% baseline)

**Decision Gate:** If ≥92% → Continue to Story 2.2 | If ≥95% → STOP, Phase 2 complete

---

### Story 2.2: Phase 2B - Financial Embeddings Evaluation (6-8 hours)

**Goal:** Evaluate financial domain-specific embeddings vs. general E5 embeddings

**Options to Test:**
1. **OpenAI text-embedding-3-large** (API, 3072-dim, SOTA quality, $0.13/1M tokens)
2. **FinBERT** (local, 768-dim, finance-trained, free)
3. **Baseline E5-large-v2** (current, 1024-dim, general purpose)

**Implementation:**
- A/B test: Re-ingest with each embedding model
- Run accuracy tests on all 50 ground truth queries
- Compare: Retrieval accuracy, cost, latency
- **Decision:** Adopt best-performing model (if improvement >5%)

**Expected Impact:** +10-15% accuracy on financial terminology queries

**Technologies:** OpenAI API (optional), FinBERT from HuggingFace (optional)

**Success Criteria:**
- Embedding comparison report completed
- If OpenAI/FinBERT >+5% accuracy → Adopt new model, re-ingest all docs
- Accuracy ≥95% → STOP, Phase 2 complete

**Decision Gate:** If ≥95% → STOP | If <95% → Continue to Story 2.3

---

### Story 2.3: Phase 2C - Table-Aware Chunking (8-10 hours)

**Goal:** Preserve financial tables intact during chunking (prevent mid-table splits)

**Implementation:**
- Detect Docling TableItem objects during ingestion
- Keep entire table in single chunk (even if >500 words)
- Include 2 sentences before/after table for context
- Mark table chunks with metadata (`chunk_type="table"`)
- Optional: Boost table chunks in search (1.2x score multiplier)

**Expected Impact:** +5-8% accuracy on tabular queries, +15-20% on table-specific questions

**Technologies:** Docling TableItem API (already available)

**Success Criteria:**
- Tables no longer split mid-row/mid-column
- Table chunks include surrounding narrative context
- Queries for table data (e.g., "variable costs 23.2") retrieve table chunks
- Accuracy ≥95% → STOP, Phase 2 complete

**Decision Gate:** If ≥95% → STOP | If <95% → Continue to Story 2.4

---

### Story 2.4: Phase 2D - Cross-Encoder Re-ranking (6-8 hours)

**Goal:** Add second-stage re-ranking with cross-encoder for improved precision

**Implementation:**
- Two-stage retrieval:
  1. **Stage 1 (Fast):** Vector search → retrieve top-20 candidates
  2. **Stage 2 (Slow):** Cross-encoder → re-rank to top-5
- Use `cross-encoder/ms-marco-MiniLM-L-6-v2` model
- Process query+document pairs through BERT-based classifier
- More accurate than bi-encoder (cosine similarity)

**Expected Impact:** +3-5% precision improvement, +150ms latency

**Technologies:** sentence-transformers (cross-encoder)

**Success Criteria:**
- Top-5 results more relevant than vector search alone
- Precision@5 improved by ≥3%
- Latency <10s still maintained (NFR5)
- Accuracy ≥95% → STOP, Phase 2 complete

**Decision Gate:** If ≥95% → STOP | If <95% → Continue to Story 2.5 (advanced)

---

### Story 2.5: Phase 2E - Query Expansion (4-6 hours, OPTIONAL)

**Goal:** Expand queries with synonyms and related terms for better recall

**Implementation:**
- Use Claude API to generate 3-5 query variations
- Search with each variation (parallel)
- Fuse results using Reciprocal Rank Fusion (RRF)
- Example: "variable costs" → ["variable expenses", "variable costs EUR/ton", "cost per ton"]

**Expected Impact:** +2-5% recall improvement, +500-800ms latency

**Technologies:** Anthropic API (Claude for query expansion)

**Success Criteria:**
- Queries with synonyms/paraphrases find relevant content
- Recall improved (more relevant docs retrieved in top-20)
- Accuracy ≥95% → STOP

**Decision Gate:** If ≥95% → STOP | If still <95% → Continue to Story 2.6

---

### Story 2.6: Phase 2F - Multi-Vector Representations (12-16 hours, OPTIONAL)

**Goal:** Store multiple embeddings per chunk (content, keywords, summary) for robustness

**Implementation:**
- Generate 3 representations per chunk:
  1. **Content vector:** Full chunk text (current approach)
  2. **Keyword vector:** LLM-extracted keywords only
  3. **Summary vector:** LLM-generated 2-3 sentence summary
- Store in 3 separate Qdrant collections
- Search all 3 collections, fuse with RRF
- More robust to different query styles (keyword, semantic, conceptual)

**Expected Impact:** +5-10% accuracy, +3x storage, +3x ingestion time

**Technologies:** Qdrant multi-collection, Claude API (keyword/summary extraction)

**Success Criteria:**
- Different query styles all achieve high accuracy
- Accuracy ≥98% (exceeds NFR6/NFR7)
- System robust to varied query phrasing

**Decision Gate:** If ≥98% → Phase 2 complete (advanced optimization)

---

### Phase 2 Summary

**Timeline:** Weeks 6-10 (conditional, depends on how many stories needed)

**Expected Progression:**
- **Baseline (Option C):** 90-92% retrieval accuracy
- **After Story 2.1 (Hybrid):** 92-94% accuracy
- **After Story 2.2 (Embeddings):** 94-96% accuracy → Likely STOP here
- **After Story 2.3 (Tables):** 95-97% accuracy
- **After Story 2.4 (Re-ranking):** 96-98% accuracy
- **After Story 2.5-2.6 (Advanced):** 98%+ accuracy (if needed)

**Technologies Added:**
- sentence-transformers (cross-encoder re-ranking)
- OpenAI API (optional: embeddings, query expansion)
- FinBERT (optional: financial embeddings)
- Qdrant multi-collection support

**Deliverable:** RAGLite system achieving 95%+ retrieval accuracy (NFR6 exceeded)

---

## Phase 2 (Alternative): GraphRAG - DEPRECATED

**⚠️ NOTE:** The original Phase 2 (Knowledge Graph with Neo4j) has been **DEPRECATED** in favor of incremental RAG enhancements above.

**Rationale:**
- RAG enhancements are **simpler** (no new infrastructure like Neo4j)
- RAG enhancements are **incremental** (can stop when target achieved)
- RAG enhancements are **lower risk** (proven techniques)
- GraphRAG may still be considered in **future phases** if:
  - Multi-hop relational queries remain unsolved after Phase 2
  - Graph-based reasoning proves necessary for specific use cases

**If GraphRAG is needed later:** See v1.0 architecture reference for Neo4j integration approach.

## Phase 3: Intelligence Features (Weeks 9-12 or 5-8)

**Goal:** Add forecasting and proactive insights

*(Detailed in v1.0 reference sections below)*

## Phase 4: Production Readiness (Weeks 13-16)

**Goal:** AWS deployment, monitoring, performance optimization

*(Detailed in v1.0 reference sections below)*

**Microservices Decision (End of Week 16):**
- Refactor to microservices ONLY IF proven scale problems exist
- See "Evolution Path" section below for migration strategy

---
