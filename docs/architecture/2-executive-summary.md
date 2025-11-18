# 2. Executive Summary

## v1.1 Architectural Vision

RAGLite v1.1 implements a **simplified monolithic MCP server** that delivers all PRD features with 80% less code than microservices. The architecture prioritizes:

- **Rapid delivery:** 4-5 weeks (vs 8-10 weeks for microservices)
- **Reduced complexity:** 600-800 lines (vs 3000+ lines)
- **Same features:** All functional requirements met
- **Future-proof:** Can evolve to microservices in Phase 4 if proven necessary

**Key Decision: START MONOLITHIC, evolve to microservices ONLY when you have REAL scale problems.**

## Key Architectural Decisions

1. **Monolithic MVP First** ⭐ **PRIMARY RECOMMENDATION**
   - Single FastMCP server with modular codebase
   - Direct function calls (no service boundaries)
   - One deployment (app + Qdrant containers)
   - **When to microservices:** Phase 4, IF independent scaling needed

2. **Phased Graph Approach** (Research-Validated)
   - **Phase 1:** Contextual Retrieval (98.1% accuracy, $0.82/100 docs)
   - **Phase 2 (conditional):** GraphRAG IF Phase 1 accuracy <90%
   - **Cost savings:** 99% if GraphRAG unnecessary ($0.82 vs $249/year)

3. **Simplified Orchestration**
   - **Phase 1-2:** Direct function calls (no AWS Strands complexity)
   - **Phase 3 (optional):** Add AWS Strands IF complex multi-agent workflows needed
   - **Default:** Keep it simple with direct calls

4. **Production-Proven Technologies** (Research-Validated)
   - Docling: 97.9% table accuracy (surpasses AWS Textract 88%)
   - Fin-E5: 71.05% financial domain accuracy (+5.6% vs general models)
   - MCP Python SDK: Official, 19k GitHub stars
   - Qdrant: Sub-5s retrieval with HNSW indexing

---

## Architectural Decision Summary

**Complete decision matrix consolidating all architectural choices:**

| Category | Decision | Version/Details | Rationale | Status |
|----------|----------|-----------------|-----------|--------|
| **Architecture Pattern** | Monolithic MVP | Single FastMCP server | 600-800 lines vs 3000+ for microservices, 4-5 weeks delivery | ✅ APPROVED |
| **API Protocol** | Model Context Protocol (MCP) | Official MCP SDK 1.20.0 | Official Anthropic protocol, native Claude integration | ✅ APPROVED |
| **MCP Implementation** | FastMCP 2.0 (optional) | 2.0 | Advanced patterns, enterprise auth, testing (optional enhancement) | ✅ APPROVED |
| **Vector Database** | Qdrant | 1.15.5+ | HNSW indexing, sub-5s retrieval, production-proven | ✅ APPROVED |
| **SQL Database** | PostgreSQL | 16.10 LTS | Structured table storage for financial data | ⚠️ CONDITIONAL (Phase 2B) |
| **Graph Database** | Neo4j | 5.26 LTS | Knowledge graph for entity relationships | ⚠️ CONDITIONAL (Phase 2C) |
| **LLM Provider** | Claude 3.7 Sonnet | Anthropic SDK 0.72.0 | State-of-art reasoning, 200K context window | ✅ APPROVED |
| **Embeddings** | FinanceMTEB/Fin-E5 | sentence-transformers 5.1+ | 71.05% financial domain accuracy (+5.6% vs general) | ✅ APPROVED |
| **PDF Processing** | Docling | 2.0.0 | 97.9% table accuracy, surpasses AWS Textract (88%) | ✅ APPROVED |
| **PDF Backend** | pypdfium | Latest | 1.7-2.5x speedup, 50-60% memory reduction | ✅ APPROVED |
| **Time Series** | Prophet | 1.2.1 | Facebook library, seasonal handling, ±8% error | ✅ APPROVED |
| **Backend Language** | Python | 3.11-3.13 | RAG ecosystem standard, async support, 3.13.5 latest | ✅ APPROVED |
| **Data Validation** | Pydantic | 2.12.4 | Type-safe models, runtime validation, Python 3.14 support | ✅ APPROVED |
| **Testing Framework** | pytest | 8.4.2 | Standard Python testing, async support | ✅ APPROVED |
| **Code Quality** | Ruff | 0.14.3 | 10-100x faster than Black, replaces Black+isort+Flake8 | ✅ APPROVED |
| **Authentication** | Deferred to Phase 5 | N/A | Single-user MVP, multi-tenant auth out of scope | ➖ DEFERRED |
| **Deployment (Dev)** | Docker Compose | Latest | Local development, service isolation | ✅ APPROVED |
| **Deployment (Prod)** | AWS ECS/Fargate | Phase 4 | Managed containers, auto-scaling | ✅ PLANNED (Phase 4) |
| **Infrastructure as Code** | Terraform | Phase 4 | Version-controlled infrastructure | ✅ PLANNED (Phase 4) |
| **CI/CD** | GitHub Actions | Current | Git-integrated, free for public repos | ✅ APPROVED |
| **Monitoring** | CloudWatch + Prometheus | Phase 4 | AWS native + open-source metrics | ✅ PLANNED (Phase 4) |
| **Agent Orchestration** | LangGraph + AWS Strands | Phase 3 (optional) | Multi-agent coordination for complex workflows | ⚠️ CONDITIONAL (Phase 3) |

**Legend:**
- ✅ APPROVED - Decision finalized, ready for implementation
- ⚠️ CONDITIONAL - Decision gated behind accuracy thresholds (Phase 2B/2C/3)
- ✅ PLANNED - Decision made, implementation scheduled for future phase
- ➖ DEFERRED - Explicitly out of scope for MVP, scheduled for Phase 5+

---

## Novel Patterns & Custom Solutions

**RAGLite implements several custom patterns unique to financial document RAG systems:**

### 1. Table-Aware Chunking (Section 6)

**Problem:** Fixed-size chunking fragments financial tables across 8.6 chunks on average, destroying semantic coherence for retrieval.

**Solution:** Hybrid chunking strategy:
- Tables <4096 tokens → Keep intact as single chunk
- Tables ≥4096 tokens → Split by rows with header duplication
- Non-table text → Standard fixed 512-token chunking

**Impact:**
- Fragmentation: 8.6 → 1.2 chunks/table (-86%)
- Expected accuracy gain: +10-15pp

**Implementability:** Complete 200+ line reference implementation with Mermaid sequence diagram (Section 6)

---

### 2. Conditional Multi-Index Architecture (Phase 2B/2C)

**Problem:** Unknown if vector-only search suffices for 70% accuracy target. Over-engineering risks wasted effort; under-engineering risks failure.

**Solution:** Staged architecture with decision gates:
- **Phase 2A:** Vector search only (80% probability suffices)
- **Phase 2B:** IF <70% → Add PostgreSQL structured index (15% probability)
- **Phase 2C:** IF <75% → Add Neo4j graph index (5% probability)

**Impact:**
- Best case: 600-800 lines, single Qdrant index
- Worst case: 950-1000 lines, three-index hybrid

**Implementability:** Clear trigger conditions, decision gates at T+17 (Phase 2A), separate PRD stories for each phase

---

### 3. Strangler Fig Microservices Migration (Section 8)

**Problem:** Monolithic → microservices "big bang" rewrites fail 70% of the time. Need zero-downtime gradual extraction.

**Solution:** API Gateway-based traffic shifting:
- Stage 1: Introduce API Gateway (100% → monolith)
- Stage 2: Data partitioning (separate Qdrant collections)
- Stage 3: Extract services one-by-one (gradual traffic shift 10% → 50% → 100%)
- Stage 4: Decommission monolith

**Impact:**
- 4-8 week migration timeline (vs 12-16 weeks big bang)
- Rollback capability at each stage (<15 minutes)
- Cost increase: 75% (+$120/month) for operational flexibility

**Implementability:** Concrete steps with success criteria, API versioning strategy (v1/v2 coexistence), cost analysis

---

### 4. Financial Domain Embeddings (Fin-E5)

**Problem:** General-purpose embedding models (E5-base) achieve only 65.4% accuracy on financial terminology. Need domain-specific optimization.

**Solution:** FinanceMTEB/FinE5 model:
- Fine-tuned e5-Mistral-7B on financial corpus
- Persona-based synthetic dataset for diverse financial tasks
- Covers: financial news, corporate reports, ESG, regulatory filings, earnings calls

**Impact:**
- Accuracy: 65.4% (general E5) → 71.05% (Fin-E5) (+5.6pp)
- Zero additional cost (local inference via sentence-transformers)

**Implementability:** Drop-in replacement for E5-base, requires Qdrant collection recreation (different dimensions)

---

### 5. Phased Accuracy Validation with Decision Gates (Section 8)

**Problem:** RAG accuracy improvements are unpredictable. Committing to full Epic 2 scope (6 stories, 4-6 weeks) risks implementing unnecessary features.

**Solution:** Incremental validation with STOP conditions:
- Story 2.1 (Hybrid Search): IF ≥92% → STOP, Phase 2 complete
- Story 2.2 (Embeddings): IF ≥95% → STOP
- Story 2.3 (Table Chunking): IF ≥95% → STOP
- Continue stories sequentially until 95% threshold

**Impact:**
- Best case: 1 story (Hybrid Search) achieves 92% → 4-6 hours vs 4-6 weeks
- Worst case: All 6 stories required → Original timeline unchanged

**Implementability:** Automated AC3 ground truth test suite (50 queries), clear accuracy thresholds per story

---

**Pattern Design Philosophy:**
1. **Simplicity First** - Use standard solutions unless proven insufficient
2. **Gated Complexity** - Add complexity ONLY when simpler approaches fail (decision gates)
3. **Incremental Validation** - Measure impact of each change before proceeding
4. **Clear Boundaries** - Each pattern has explicit trigger conditions and success criteria
5. **AI-Agent Friendly** - Unambiguous implementation guidance prevents agent conflicts

---

## Architecture at a Glance (v1.1 Monolithic)

```
┌──────────────────────────────────────────────────────────┐
│  MCP Clients (Claude Code, Claude Desktop)              │
└────────────────────┬─────────────────────────────────────┘
                     │ Model Context Protocol
┌────────────────────▼─────────────────────────────────────┐
│  RAGLite Monolithic Server (FastMCP)                    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  MCP Tools Layer                                   │ │
│  │  • ingest_financial_document()                     │ │
│  │  • query_financial_documents()                     │ │
│  │  • forecast_kpi() [Phase 3]                        │ │
│  │  • generate_insights() [Phase 3]                   │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Business Logic Modules (Direct Function Calls)    │ │
│  │  ├─ ingestion/  → PDF extraction, chunking, embed  │ │
│  │  ├─ retrieval/  → Vector search, synthesis         │ │
│  │  ├─ forecasting/ [Phase 3]                         │ │
│  │  └─ insights/    [Phase 3]                         │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Shared Utilities                                  │ │
│  │  ├─ config.py    → Settings, environment vars      │ │
│  │  ├─ logging.py   → Structured logging              │ │
│  │  ├─ models.py    → Pydantic data models            │ │
│  │  └─ clients.py   → Qdrant, Claude API clients      │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Data Layer                                              │
│  ├─ Qdrant (Vector DB) → Docker container               │
│  ├─ S3/Local Storage → Documents                         │
│  └─ Neo4j [Phase 2 conditional] → Graph (if needed)      │
└──────────────────────────────────────────────────────────┘
```

**Deployment:** 2 Docker containers (app + Qdrant) vs 6 for microservices

---
