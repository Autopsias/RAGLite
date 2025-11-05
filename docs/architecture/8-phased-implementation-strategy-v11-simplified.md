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

---

## Epic 2: Advanced RAG Architecture Enhancement (REVISED - 2025-10-19)

**⚠️ STRATEGIC PIVOT:** Epic 2 has been completely redesigned following Story 2.2 failure (42% accuracy vs 56% baseline). The new approach implements a **staged RAG architecture enhancement** with decision gates to minimize risk and maximize likelihood of achieving minimum 70% retrieval accuracy.

**Current Status**: ACTIVE - Phase 1 ready to start

**Timeline**: 2-3 weeks (best case) to 18 weeks (worst case with all contingencies)

**Goal**: Achieve minimum 70% retrieval accuracy to unblock Epic 3-5

---

### Epic 2 - Phase 1: PDF Ingestion Performance Optimization (IMMEDIATE - 1-2 days)

**Status**: ✅ APPROVED - Ready to start immediately

**Goal**: 1.7-2.5x speedup (8.2 min → 3.3-4.8 min for 160-page PDF)

**Timeline**: 1-2 days

**Strategic Benefit**: Faster ingestion enables quicker RAG testing iterations in Phase 2

**Implementation**:

**Story 2.1: Implement pypdfium Backend for Docling** (4 hours)
- Replace default PDF.js backend with pypdfium in `raglite/ingestion/pipeline.py`
- Configuration:
  ```python
  from docling.backend import PdfiumBackend
  converter = DocumentConverter(pdf_backend=PdfiumBackend())
  ```
- Expected impact: 50-60% memory reduction (6.2GB → 2.4GB)

**Story 2.2: Implement Page-Level Parallelism** (4 hours)
- Add concurrent page processing (4-8 threads) to Docling
- Configuration:
  ```python
  converter = DocumentConverter(
      pdf_backend=PdfiumBackend(),
      max_num_pages_visible=4  # 4 pages concurrent processing
  )
  ```
- Expected impact: 1.7-2.5x speedup

**Success Criteria**:
- ✅ Ingestion speed: 3.3-4.8 min (vs 8.2 min baseline) = 1.7-2.5x speedup
- ✅ Table accuracy: 97.9% maintained (no degradation from baseline)
- ✅ Memory usage: 50-60% reduction validated
- ✅ No race conditions or deadlocks during concurrent processing

**Risk**: LOW (empirically validated by Docling official benchmarks)

**Deliverable**: Optimized PDF ingestion pipeline ready for Phase 2A testing iterations

---

### Epic 2 - Phase 2: RAG Architecture Pivot (1-6 weeks, staged with decision gates)

**Goal**: Achieve minimum 70% retrieval accuracy (unblock Epic 3-5)

**Strategy**: Staged implementation with decision gates - STOP at first phase that achieves ≥70% accuracy

---

#### Phase 2A: Fixed Chunking + Metadata (1-2 weeks) - PRIMARY PATH

**Status**: Pending (starts after Phase 1 complete)

**Probability**: 80% success (research-validated: fixed 512-token achieves 68-72% accuracy)

**Timeline**: 1-2 weeks

**Goal**: Replace failed element-aware chunking with research-validated fixed 512-token approach

**Implementation**:

**Story 2.3: Refactor Chunking Strategy to Fixed 512-Token Approach** (3 days)
- Remove element-aware logic from `raglite/ingestion/pipeline.py`
- Implement fixed 512-token chunking with 50-token overlap
- Preserve table boundaries (no mid-table splits)
- DELETE contaminated Qdrant collection and re-ingest
- Expected chunk count: 250-350 (vs 504 element-aware, 321 baseline)

**Story 2.4: Add LLM-Generated Contextual Metadata Injection** (2 days)
- Implement Claude API-based metadata extraction (fiscal period, company, department)
- Inject metadata into Qdrant chunk payload
- Cache metadata generation (run once per document, not per query)
- Update chunk schema to include metadata fields

**Story 2.5: AC3 Validation and Optimization - DECISION GATE** (2-3 days)
- Run full AC3 ground truth test suite (50 queries)
- Measure retrieval accuracy (target: ≥70%)
- Analyze failure modes and document
- Rebuild BM25 index for new chunks
- Performance validation: <5s p50, <15s p95

**Success Criteria**:
- ✅ **Retrieval accuracy ≥70%** (MANDATORY - This is the DECISION GATE)
- ✅ Attribution accuracy ≥95%
- ✅ Query response time <5s p50, <15s p95
- ✅ Chunk size consistency: 512 tokens ±50 variance

**Decision Gate (T+17, Week 3 Day 3)**:
- **IF ≥70% accuracy**: ✅ **EPIC 2 COMPLETE** → Proceed to Epic 3 planning
- **IF <70% accuracy**: ⚠️ **PROCEED TO PHASE 2B** → PM (John) approval required

**Technologies**: Existing stack (Qdrant, Claude API, Docling)

**Risk**: LOW (research shows 68-72% accuracy for fixed chunking approach)

---

#### Phase 2B: Structured Multi-Index (3-4 weeks) - CONTINGENCY

**Status**: Conditional (triggered only if Phase 2A <70%)

**Probability**: 15% trigger (if Phase 2A achieves 65-69% accuracy)

**Timeline**: 3-4 weeks

**Goal**: Achieve 70-80% accuracy through SQL tables + vector search + re-ranking (FinSage pattern)

**Trigger**: Phase 2A decision gate (IF retrieval accuracy <70%)

**Implementation**:
1. **PostgreSQL Table Storage**:
   - Extract Docling TableItem objects to structured SQL schema
   - Store financial tables with proper column typing
   - Enable precise SQL queries for table lookups

2. **Dual-Index Architecture**:
   - Index 1: PostgreSQL for structured table queries
   - Index 2: Qdrant for semantic vector search (existing)
   - Intelligent query routing based on query type

3. **Cross-Encoder Re-ranking**:
   - Two-stage retrieval: Vector search top-20 → Re-rank to top-5
   - Use cross-encoder model for improved precision
   - Expected: +3-5% accuracy improvement

**Expected Accuracy**: 70-80% (based on FinSage production results)

**Success Criteria**:
- ✅ Retrieval accuracy ≥75% (stretch goal)
- ✅ Table-specific queries achieve ≥85% accuracy
- ✅ Query response time <10s p95

**Decision Gate**:
- **IF ≥75% accuracy**: ✅ **EPIC 2 COMPLETE** → Proceed to Epic 3
- **IF 70-74% accuracy**: ⚠️ **EPIC 2 COMPLETE** (minimum threshold met) → Proceed to Epic 3
- **IF <70% accuracy**: 🛑 **PROCEED TO PHASE 2C** → PM (John) approval required (5% probability)

**Technologies Added**: PostgreSQL 16+, cross-encoder re-ranking

**Risk**: MEDIUM (requires new infrastructure, but FinSage validates approach)

---

#### Phase 2C: Hybrid Architecture (GraphRAG + Structured + Vector) (6 weeks) - CONTINGENCY

**Status**: Conditional (triggered only if Phase 2B <75%)

**See section below for full Phase 2C details** (already documented)

---

### Epic 2 - Phase 3: Agentic Coordination (2-16 weeks, staged) - OPTIONAL

**Status**: Conditional (triggered only if Phase 2 <85% accuracy)

**Probability**: 20% trigger (Phase 2 paths expected to achieve 70-92% accuracy)

**Timeline**: 2-16 weeks (staged implementation)

**Goal**: Achieve 90-95% retrieval accuracy through multi-agent orchestration

**Trigger**: Phase 2 completion decision gate (IF any Phase 2 path <85% accuracy)

**Implementation** (Staged):

**Phase 3A: Query Planning Agent** (2 weeks)
- LLM-based query classifier and decomposer
- Break complex queries into sub-queries
- Route queries to appropriate specialists
- Expected: +5-8% accuracy on complex multi-hop queries

**Phase 3B: Specialist Retrieval Agents** (4-6 weeks)
- Table Specialist: SQL-focused retrieval for tabular data
- Semantic Specialist: Vector search for conceptual queries
- Graph Specialist: Entity relationship traversal (if Phase 2C active)
- Metadata Specialist: Fiscal period, company, department filters
- Expected: +3-5% accuracy from specialized retrieval

**Phase 3C: Answer Synthesis Coordinator** (2-4 weeks)
- Multi-agent result fusion with conflict resolution
- Cross-reference validation across specialists
- Comprehensive answer assembly with citations
- Expected: +2-5% accuracy from better synthesis

**Phase 3D: Adaptive Learning** (4-6 weeks, optional)
- Track query patterns and specialist performance
- Adaptive routing based on historical accuracy
- Query rewriting based on failure analysis
- Expected: +5-10% accuracy from optimization

**Technologies Added**:
- LangGraph (multi-agent orchestration framework)
- AWS Strands (agent deployment and scaling)
- Agent state management and coordination logic

**Expected Accuracy**: 90-95% (research-validated for agentic RAG systems)

**Success Criteria**:
- ✅ Retrieval accuracy ≥90% (NFR6 compliance)
- ✅ Complex multi-hop queries working correctly
- ✅ Agent coordination latency <8s p95

**Decision Gate**: Epic 2 complete when ≥90% accuracy validated

**Risk**: HIGH (significant complexity, requires agent framework, 2-16 week timeline variability)

---

### Epic 2 Overall Timeline Visualization

```
CURRENT → Week 1-2: Phase 1 - PDF Optimization ⏳ STARTING
  Timeline: 1-2 days
  Outcome: 1.7-2.5x speedup validated
  Risk: LOW

Week 2-4: Phase 2A - Fixed Chunking + Metadata (PRIMARY PATH)
  Timeline: 1-2 weeks
  Outcome: 68-72% accuracy (80% probability)
  Decision Gate: T+17 (Week 3, Day 3)
  IF ≥70% → EPIC 2 COMPLETE ✅

IF Phase 2A <70% → Week 5-8: Phase 2B - Structured Multi-Index (15% probability)
  Timeline: 3-4 weeks
  Outcome: 70-80% accuracy
  Decision Gate: Week 8
  IF ≥70% → EPIC 2 COMPLETE ✅

IF Phase 2B <70% → Week 9-14: Phase 2C - Hybrid Architecture (5% probability)
  Timeline: 6 weeks
  Outcome: 75-92% accuracy
  Decision Gate: Week 14
  IF ≥75% → EPIC 2 COMPLETE ✅

IF Phase 2 <85% → Week 15-30: Phase 3 - Agentic Coordination (20% probability)
  Timeline: 2-16 weeks (staged)
  Outcome: 90-95% accuracy
  Decision Gate: Week 30 (latest)
  EPIC 2 COMPLETE ✅
```

**Best Case**: Weeks 1-4 (Phase 1 + 2A) → 70-72% accuracy → Epic 2 complete → Proceed to Epic 3

**Likely Case**: Weeks 1-4 (Phase 1 + 2A) or Weeks 1-8 (Phase 1 + 2A + 2B) → 70-80% accuracy → Epic 2 complete

**Worst Case**: Weeks 1-30 (all phases) → 90-95% accuracy → Epic 2 complete

---

## DEPRECATED: Original Phase 2 Advanced RAG Enhancements

**⚠️ The following section is DEPRECATED as of 2025-10-19 following Epic 2 strategic pivot.**

**Reason**: Element-aware chunking approach (Story 2.2) FAILED catastrophically with 42% accuracy vs 56% baseline. New staged approach above replaces this entire section.

**For historical reference only - DO NOT IMPLEMENT:**

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

## Phase 2C (Contingency): Hybrid Architecture (GraphRAG + Structured + Vector)

**⚠️ NOTE:** Phase 2C is a **CONTINGENCY PATH** - ONLY triggered if Phase 2B Structured Multi-Index achieves <75% accuracy.

**Trigger**: Phase 2B decision gate (IF Phase 2B retrieval accuracy <75%)

**Probability**: 5% (Phase 2B expected to achieve 70-80% accuracy, making Phase 2C unlikely)

**Timeline**: 6 weeks

**Goal**: Achieve 75-92% retrieval accuracy through multi-index architecture with graph-based entity relationships

**Implementation**:
1. **Neo4j 5.x Graph Database** for entity relationships:
   - Extract entities: Companies, Departments, Metrics, KPIs, Time Periods
   - Construct knowledge graph capturing relationships
   - Enable graph traversal queries for multi-hop reasoning

2. **PostgreSQL for Structured Tables**:
   - Store financial tables with structured schema
   - Enable SQL queries for precise table lookups
   - Link table rows to entities in graph

3. **Qdrant for Semantic Vector Search** (existing):
   - Continue vector-based semantic retrieval
   - Link chunks to graph entities for cross-index querying

4. **Intelligent Query Routing**:
   - LLM-based query classifier determines which index to use
   - Hybrid queries use multiple indexes with result fusion
   - Cross-index linking for comprehensive answers

**Production Evidence**:
- BlackRock/NVIDIA HybridRAG: 0.96 answer relevancy (SOTA)
- BNP Paribas GraphRAG: 6% hallucination reduction, 80% token savings
- Morgan Stanley GraphRAG: Improved multi-hop reasoning for relationship queries

**Technologies Added**:
- Neo4j 5.x (graph database)
- PostgreSQL 16+ (SQL database)
- Graph query logic (Cypher queries)
- Multi-index fusion algorithms

**Success Criteria**:
- ✅ Retrieval accuracy ≥80% (target for Epic 2 completion)
- ✅ Multi-hop relationship queries working correctly
- ✅ Entity extraction accuracy ≥85%
- ✅ Cross-index queries return comprehensive results

**Decision Gate**: Epic 2 complete when ≥80% accuracy validated on AC3 ground truth test suite

**Deliverable**: Full multi-index RAG system with graph, structured, and vector search capabilities

## Phase 3: Intelligence Features (Weeks 9-12 or 5-8)

**Goal:** Add forecasting and proactive insights

*(Detailed in v1.0 reference sections below)*

## Phase 4: Production Readiness (Weeks 13-16)

**Goal:** AWS deployment, monitoring, performance optimization

*(Detailed in v1.0 reference sections below)*

**Microservices Decision (End of Week 16):**
- Refactor to microservices ONLY IF proven scale problems exist
- See "Monolithic → Microservices Migration Strategy" section below for detailed migration approach

---

## Monolithic → Microservices Migration Strategy

**⚠️ IMPORTANT:** Only execute this migration IF Phase 4 production validation reveals actual scaling bottlenecks (independent service scaling needed, team size >3, or deployment frequency >10/week).

### Migration Decision Criteria

**Trigger Migration IF:**
- ✅ Ingestion and retrieval need independent scaling (different load patterns validated)
- ✅ Team size ≥3 developers (independent teams for separate services)
- ✅ Deployment frequency >10/week (monolith deployment coupling becomes bottleneck)
- ✅ Service-specific SLAs required (different availability/latency targets per component)

**DO NOT Migrate IF:**
- ❌ No proven scaling bottleneck (premature optimization)
- ❌ Solo developer or 2-person team (coordination overhead outweighs benefits)
- ❌ Deployment frequency <5/week (monolith deployment is manageable)
- ❌ Similar resource usage across components (no independent scaling benefit)

---

### Migration Approach: Strangler Fig Pattern

**Strategy:** Gradually extract services from the monolith while maintaining system functionality. Do NOT attempt "big bang" rewrite.

**Timeline:** 4-8 weeks (staged extraction, one service at a time)

---

### Stage 1: API Gateway Introduction (Week 1)

**Goal:** Add routing layer to enable gradual service extraction

**Implementation:**

1. **Deploy API Gateway (AWS API Gateway or Kong)**
   - Route all MCP requests through gateway initially
   - Gateway forwards 100% of traffic to existing monolith
   - No application code changes required
   - Validate: All existing functionality works through gateway

2. **Update Client Configuration**
   - MCP clients point to API Gateway URL instead of direct monolith
   - Gateway URL: `https://api.raglite.com/v1/`
   - Monolith runs behind gateway: `http://internal-monolith:5000/`

3. **Add Request/Response Logging**
   - Log all requests at gateway for traffic analysis
   - Identify service boundaries based on real usage patterns

**Success Criteria:**
- ✅ Zero downtime migration to API Gateway
- ✅ All MCP tools function correctly through gateway
- ✅ Latency increase <50ms (gateway overhead)

---

### Stage 2: Data Partitioning (Week 2-3)

**Goal:** Separate data stores to enable independent service deployment

**Qdrant Collections:**
- **Monolith (current):** Single collection `documents`
- **Microservices (target):** Separate collections per document type or domain
  - `financial_reports` - PDF ingestion service owns this
  - `spreadsheets` - Excel ingestion service owns this
  - Retrieval service reads from all collections

**PostgreSQL/Neo4j (if Phase 2B/2C active):**
- **Monolith:** Single database `raglite`
- **Microservices:** Separate databases per service
  - `ingestion_db` - Ingestion metadata (job status, document registry)
  - `retrieval_db` - Query logs, cached results
  - `graph_db` (Neo4j) - Shared graph, accessed via graph service only

**Migration Steps:**

1. **Create new Qdrant collections**
   ```python
   # Dual-write during migration
   await qdrant.upsert(collection_name="documents", points=chunks)  # Old
   await qdrant.upsert(collection_name="financial_reports", points=chunks)  # New
   ```

2. **Copy existing data to new collections**
   - Background job migrates all chunks from `documents` → domain-specific collections
   - Validate data integrity (chunk count, embedding dimensions)

3. **Update monolith to read from new collections**
   - Retrieval logic searches new collections: `["financial_reports", "spreadsheets"]`
   - Validate: Query results unchanged after migration

4. **Remove old collection (after validation window)**
   - Wait 1 week for rollback safety
   - Delete `documents` collection

**Success Criteria:**
- ✅ All data migrated to new collections with zero data loss
- ✅ Query results identical before/after migration
- ✅ Rollback plan validated (restore from backup)

---

### Stage 3: Service Extraction (Week 4-6)

**Extraction Order:** Least coupled → Most coupled

**Priority 1: Ingestion Service (Week 4)**

**Why First?** Clear boundaries, asynchronous, no tight coupling to retrieval

**Steps:**

1. **Extract Code**
   - Create new `ingestion-service/` repository
   - Copy `raglite/ingestion/` → `ingestion-service/src/`
   - Add service-specific dependencies (FastAPI, Celery if async jobs needed)
   - Package as Docker container

2. **Deploy Service**
   - Deploy ingestion service to ECS: `ingestion-service:5001`
   - Keep monolith running: `monolith:5000`
   - API Gateway routes ingestion MCP tools → ingestion service
   - API Gateway routes all other tools → monolith

3. **Gateway Routing Rules**
   ```yaml
   routes:
     - path: /v1/tools/ingest_financial_document
       target: http://ingestion-service:5001
     - path: /v1/tools/query_financial_documents
       target: http://monolith:5000  # Still in monolith
     - path: /v1/tools/*
       target: http://monolith:5000  # Default to monolith
   ```

4. **Dark Launch (1 week)**
   - Ingestion service deployed but receives 0% traffic
   - Monolith still handles 100% of ingestion requests
   - Test ingestion service independently (staging environment)

5. **Gradual Traffic Shift**
   - Week 1: 10% → ingestion service, 90% → monolith
   - Week 2: 50% → ingestion service, 50% → monolith
   - Week 3: 100% → ingestion service, monolith ingestion code removed

**Success Criteria:**
- ✅ Ingestion service independently deployable
- ✅ Zero downtime during traffic shift
- ✅ Ingestion latency unchanged (<5% variance)
- ✅ Error rate unchanged

---

**Priority 2: Retrieval Service (Week 5)**

**Why Second?** Core functionality, depends on ingestion data (loose coupling via Qdrant)

**Steps:** Similar to Ingestion Service extraction

**Gateway Routing:**
```yaml
routes:
  - path: /v1/tools/query_financial_documents
    target: http://retrieval-service:5002
  - path: /v1/tools/ingest_financial_document
    target: http://ingestion-service:5001
  - path: /v1/tools/*
    target: http://monolith:5000  # Remaining tools (forecasting, insights)
```

---

**Priority 3: Forecasting Service (Week 6, optional)**

**Why Third?** Phase 3 feature, lowest traffic, can remain in monolith if minimal usage

**Decision Gate:** Extract ONLY if forecasting workload requires independent scaling

---

### Stage 4: Monolith Decommission (Week 7-8)

**Goal:** Remove monolith after all services extracted

**Steps:**

1. **Verify all traffic routed to services**
   - API Gateway logs show 0 requests to monolith
   - Monolith logs show zero activity for 1 week

2. **Decommission monolith**
   - Stop monolith ECS task
   - Delete monolith container image
   - Remove monolith deployment from Terraform

3. **Update Architecture Diagrams**
   - Document final microservices architecture
   - Update deployment docs: "Deployment Architecture (Microservices)"

**Success Criteria:**
- ✅ All services independently deployable
- ✅ No monolith dependencies remaining
- ✅ API Gateway routes 100% to microservices
- ✅ Documentation updated

---

### Migration Rollback Strategy

**At Each Stage:**

1. **API Gateway Rollback (Stage 1)**
   - Revert client configuration to direct monolith URL
   - Remove API Gateway from request path
   - Rollback time: <15 minutes

2. **Data Partitioning Rollback (Stage 2)**
   - Revert monolith to read from old `documents` collection
   - New collections remain (no data loss)
   - Rollback time: <30 minutes (config change + restart)

3. **Service Extraction Rollback (Stage 3)**
   - API Gateway shifts traffic back to monolith (0% → service, 100% → monolith)
   - Service remains deployed (dark launch)
   - Rollback time: <5 minutes (gateway config change)

---

### API Versioning Strategy

**Problem:** Service extraction may require API changes (breaking changes to MCP tool signatures)

**Solution:** API Gateway supports multiple versions simultaneously

**Versioning Scheme:**

- **v1:** Current monolith API (e.g., `ingest_financial_document(file_path: str)`)
- **v2:** Microservices API (e.g., `ingest_financial_document(file_url: str, metadata: dict)`)

**Gateway Routes:**
```yaml
routes:
  # v1 API (legacy monolith)
  - path: /v1/tools/ingest_financial_document
    target: http://monolith:5000

  # v2 API (microservices)
  - path: /v2/tools/ingest_financial_document
    target: http://ingestion-service:5001
```

**Deprecation Timeline:**
- v1 supported for 6 months after v2 launch (grace period)
- v1 deprecated warning added to responses (month 4-6)
- v1 sunset date announced (month 6)
- v1 removed (month 7)

---

### Cost Implications

**Monolith (Current):**
- 1 ECS task (2 vCPU, 4GB RAM): ~$60/month
- 1 Qdrant instance: ~$100/month
- **Total:** ~$160/month

**Microservices (Post-Migration):**
- API Gateway: ~$3.50/million requests + $0.09/GB data transfer
- 3 ECS tasks (Ingestion, Retrieval, Forecasting): ~$180/month
- 1 Qdrant instance (shared): ~$100/month
- **Total:** ~$280/month + API Gateway usage

**Cost Increase:** ~75% (+$120/month) for operational flexibility

**Breakeven Analysis:**
- Migration cost: 4-8 weeks development time (~$20k-40k)
- Ongoing cost increase: $120/month (~$1,440/year)
- **ROI:** Justified IF team size ≥3 (deployment flexibility) OR independent scaling validated

---

### Key Takeaways

1. **Do NOT migrate unless you have proven scale problems** (solo dev = stay monolithic)
2. **Use Strangler Fig pattern** (gradual extraction, not big bang rewrite)
3. **API Gateway is critical** (enables traffic shifting and rollback)
4. **Data partitioning first** (enables independent service deployment)
5. **Extract least coupled services first** (Ingestion → Retrieval → Forecasting)
6. **API versioning enables zero-downtime migration** (v1 and v2 coexist)
7. **Cost increases 75%** (operational flexibility vs. infrastructure cost trade-off)

**Recommended Decision:** Stay monolithic until Phase 4 production metrics prove scaling bottleneck (1-2 years for typical RAG workload).

---
