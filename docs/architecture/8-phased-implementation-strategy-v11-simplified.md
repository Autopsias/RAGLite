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

**Decision Gate (End of Week 5):**

**IF Success Criteria Met (90%+ accuracy):**
- ✅ **MVP SUCCESS** → Proceed to Phase 3 (Forecasting/Insights)
- ✅ **SKIP Phase 2** (GraphRAG)

**IF Accuracy 80-89%:**
- ⚠️ **ACCEPTABLE for MVP** → Proceed to Phase 3 (defer GraphRAG improvements)
- Document known limitations, plan Phase 2 improvements if needed

**IF Accuracy <80%:**
- 🛑 **HALT** → Analyze failures:
  - **IF relational/multi-hop queries fail** → Consider Phase 2 (GraphRAG)
  - **IF general retrieval quality issues** → Fix chunking/embeddings/prompts → Extend to Week 6

**Technologies:**
- FastMCP, Docling, Fin-E5, Qdrant, Claude 3.7 Sonnet
- Docker Compose (Qdrant + app)
- pytest for basic testing

## Phase 2: GraphRAG (Weeks 5-8) - CONDITIONAL

**⚠️ ONLY IMPLEMENT IF PHASE 1 DECISION GATE TRIGGERS**

*(Detailed in v1.0 reference sections below)*

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
