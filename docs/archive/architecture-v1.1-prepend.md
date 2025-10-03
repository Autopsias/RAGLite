# RAGLite Architecture Document

**Version:** 1.1 (Simplified MVP-First Approach - RECOMMENDED)
**Date:** October 3, 2025
**Status:** Ready for Development
**Recommended Path:** Option A (By The Book)

---

## 📖 How to Read This Document

This architecture document presents **TWO approaches**:

### ⭐ v1.1 MONOLITHIC APPROACH (SECTIONS 1-9) - **START HERE FOR MVP**
**Recommended for:** Solo developer, 4-5 week MVP, Claude Code pair programming
- Sections 1-9 below define the simplified monolithic architecture
- 600-800 lines of code, single deployment
- All PRD features delivered, 80% less complexity
- **Use this for Phase 1-3 development**

### 📚 v1.0 MICROSERVICES REFERENCE (SECTIONS 10+) - **Future Scaling Guide**
**Use when:** Phase 4+ if you have proven scale problems
- Detailed in later sections (Microservices Architecture, Orchestration, etc.)
- Reference architecture for when you need independent service scaling
- **Don't build this until you have REAL scaling needs**

**For MVP Development: Follow v1.1 (Sections 1-9 below)**

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-03 | 1.0 | Initial microservices architecture | Winston (Architect) |
| 2025-10-03 | 1.1 | Added simplified monolithic MVP approach as PRIMARY recommendation | Winston (Architect) |

---

# Part 1: v1.1 MONOLITHIC MVP ARCHITECTURE (RECOMMENDED)

---

## 1. Introduction & Vision

### Purpose

RAGLite is an **AI-powered financial intelligence platform** enabling natural language access to company financial documents through Retrieval-Augmented Generation (RAG).

**v1.1 Architecture Goals:**
- ✅ Achieve 90%+ retrieval accuracy with validated technologies
- ✅ Deliver working MVP in 4-5 weeks (solo developer + Claude Code)
- ✅ Start simple (monolithic), evolve to microservices ONLY if scaling requires
- ✅ Minimize vendor lock-in while using production-proven technologies
- ✅ Support local Docker development → AWS deployment path

### Scope (v1.1 MVP)

**In Scope:**
- Single monolithic MCP server (FastMCP)
- PDF ingestion with Docling (97.9% table accuracy)
- Vector search with Qdrant + Fin-E5 embeddings
- LLM synthesis with Claude 3.7 Sonnet
- Source attribution (document, page, section)
- Contextual Retrieval chunking (98.1% accuracy)
- Optional GraphRAG (Phase 2 - only if accuracy <90%)
- Forecasting & Insights (Phase 3)

**Out of Scope (MVP):**
- Custom frontend UI (users interact via MCP clients: Claude Code, Claude Desktop)
- Microservices architecture (deferred to Phase 4 if needed)
- Real-time collaboration (Phase 5+)
- Multi-tenant architecture (single user MVP)

### Architectural Principles

1. **Simplicity First** - Start with simplest solution that meets requirements
2. **Validated Technologies** - Use research-proven technologies (Docling, Fin-E5, etc.)
3. **Phased Complexity** - Add complexity ONLY when simpler approaches fail
4. **Evolution Over Perfection** - Ship functional MVP, iterate based on real usage
5. **AI-Agent Friendly** - Clear patterns for Claude Code to implement

---

## 2. Executive Summary

### v1.1 Architectural Vision

RAGLite v1.1 implements a **simplified monolithic MCP server** that delivers all PRD features with 80% less code than microservices. The architecture prioritizes:

- **Rapid delivery:** 4-5 weeks (vs 8-10 weeks for microservices)
- **Reduced complexity:** 600-800 lines (vs 3000+ lines)
- **Same features:** All functional requirements met
- **Future-proof:** Can evolve to microservices in Phase 4 if proven necessary

**Key Decision: START MONOLITHIC, evolve to microservices ONLY when you have REAL scale problems.**

### Key Architectural Decisions

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

### Architecture at a Glance (v1.1 Monolithic)

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

## 3. Repository Structure (Monolithic)

```
raglite/
├── pyproject.toml              # Poetry dependencies
├── poetry.lock
├── docker-compose.yml          # Qdrant + app containers
├── Dockerfile
├── .env.example
├── .gitignore
├── README.md
│
├── raglite/                    # Main Python package (600-800 lines total)
│   ├── __init__.py
│   ├── main.py                # MCP server entrypoint (~200 lines)
│   │
│   ├── ingestion/             # Ingestion module (~150 lines)
│   │   ├── __init__.py
│   │   ├── pipeline.py        # Docling + chunking + embedding
│   │   └── contextual.py      # Contextual Retrieval chunking
│   │
│   ├── retrieval/             # Retrieval module (~150 lines)
│   │   ├── __init__.py
│   │   ├── search.py          # Qdrant vector search
│   │   ├── synthesis.py       # LLM answer synthesis
│   │   └── attribution.py     # Source citation
│   │
│   ├── forecasting/           # Forecasting module (Phase 3, ~100 lines)
│   │   ├── __init__.py
│   │   └── hybrid.py          # Prophet + LLM adjustment
│   │
│   ├── insights/              # Insights module (Phase 3, ~100 lines)
│   │   ├── __init__.py
│   │   ├── anomalies.py       # Statistical anomaly detection
│   │   └── trends.py          # Trend analysis
│   │
│   ├── shared/                # Shared utilities (~100 lines)
│   │   ├── __init__.py
│   │   ├── config.py          # Settings (Pydantic BaseSettings)
│   │   ├── logging.py         # Structured logging setup
│   │   ├── models.py          # Pydantic data models
│   │   └── clients.py         # Qdrant, Claude API clients
│   │
│   └── tests/                 # Tests co-located (~200 lines)
│       ├── test_ingestion.py
│       ├── test_retrieval.py
│       ├── test_synthesis.py
│       ├── ground_truth.py    # Accuracy validation (50+ queries)
│       └── fixtures/
│           └── sample_financial_report.pdf
│
├── scripts/
│   ├── setup-dev.sh           # One-command local setup
│   ├── init-qdrant.py         # Initialize Qdrant collection
│   └── run-accuracy-tests.py  # Ground truth validation
│
└── docs/
    ├── architecture.md         # This document
    ├── prd.md                  # Product requirements
    └── front-end-spec.md       # MCP response format spec
```

**Total Files:** ~15 Python files
**Total Lines:** 600-800 lines (vs 3000+ for microservices)
**Complexity:** LOW (direct function calls, single deployment)

---

## 4. Research Findings Summary (Validated Technologies)

All technologies are **research-validated** with quantitative performance data:

### 4.1 Document Processing

**Docling PDF Extraction:**
- ✅ 97.9% table cell accuracy on complex financial PDFs
- ✅ Surpasses AWS Textract (88%) and PyMuPDF (no table models)
- ✅ Cost: <$0.005/page (GPU amortized)

**Fin-E5 Embeddings:**
- ✅ 71.05% NDCG@10 on financial domain retrieval
- ✅ +5.6% improvement over general-purpose models
- ✅ Alternative: Voyage-3-large (74.63% commercial option)

### 4.2 Graph Approach: Contextual Retrieval → GraphRAG

**Phase 1: Contextual Retrieval** (VALIDATED)
- **Accuracy:** 96.3-98.1% (vs. 94.3% baseline)
- **Cost:** $0.82 one-time for 100 documents
- **Method:** LLM-generated 50-100 token context per chunk
- **Limitation:** May struggle with complex multi-hop queries

**Phase 2: GraphRAG** (CONDITIONAL - only if Phase 1 <90%)
- **Accuracy:** +12-18% on multi-hop relational queries
- **Cost:** $9 construction + $20/month queries (100 docs, 1000 queries)
- **Decision Gate:** If Contextual Retrieval achieves ≥90%, SKIP GraphRAG (99% cost savings)

### 4.3 Orchestration: AWS Strands (Optional for Phase 3)

**Why AWS Strands (if needed):**
- ✅ Multi-LLM support (Claude, GPT-4, Gemini, Llama, local models)
- ✅ No vendor lock-in
- ✅ Production-proven (Amazon Q Developer, AWS Glue)
- ✅ Native MCP support

**v1.1 Decision:** Use direct function calls for Phase 1-2, add Strands in Phase 3 ONLY if complex workflows need multi-agent coordination

### 4.4 MCP Server: FastMCP

- ✅ Official Python SDK (19k GitHub stars)
- ✅ Production-ready Streamable HTTP transport
- ✅ Full protocol support (tools, resources, prompts)
- ✅ ASGI integration (can mount in FastAPI if needed)

### 4.5 Forecasting: Hybrid Approach

- ✅ Statistical core (Prophet/ARIMA) + LLM adjustment
- ✅ ±8% forecast error (beats ±15% PRD target)
- ✅ Cost: $0.015 per forecast

---

## 5. Technology Stack (Definitive)

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **PDF Extraction** | Docling | Latest | Extract text/tables from PDFs | 97.9% table accuracy, DocLayNet-based |
| **Excel Processing** | openpyxl + pandas | Latest | Extract tabular data | Standard Python libraries |
| **Embedding Model** | Fin-E5 (finance-adapted) | Latest | Generate semantic vectors | 71.05% financial domain accuracy |
| **Chunking** | Contextual Retrieval | N/A | LLM-generated context per chunk | 98.1% retrieval accuracy |
| **Vector Database** | Qdrant | 1.11+ | Store/search embeddings | HNSW indexing, sub-5s retrieval |
| **Graph Database** | Neo4j | 5.x | Knowledge graph (Phase 2 conditional) | Cypher queries, managed cloud option |
| **MCP Server** | FastMCP (MCP Python SDK) | 1.x | Expose tools via MCP protocol | Official SDK, 19k GitHub stars |
| **LLM (Primary)** | Claude 3.7 Sonnet | via API | Reasoning, analysis, synthesis | State-of-art reasoning, 200K context |
| **Forecasting** | Prophet | 1.1+ | Time-series baseline | Facebook library, seasonal handling |
| **Backend Language** | Python | 3.11+ | All application code | RAG ecosystem standard, async support |
| **API Framework** | FastAPI | 0.115+ (optional) | REST endpoints if needed | High performance, async native |
| **Document Storage** | S3 (cloud) / Local FS (dev) | N/A | Store ingested documents | Scalable, versioning, encryption |
| **Secrets** | AWS Secrets Manager / .env | N/A | API keys, credentials | Secure, rotatable |
| **Containerization** | Docker + Docker Compose | Latest | Local development | Service isolation, reproducible |
| **Cloud Platform** | AWS | N/A | Production deployment (Phase 4) | ECS/Fargate, managed services |
| **IaC** | Terraform | Latest | Infrastructure as Code (Phase 4) | Version-controlled infrastructure |
| **CI/CD** | GitHub Actions | N/A | Testing and deployment | Git-integrated |
| **Monitoring** | CloudWatch + Prometheus | N/A | Performance tracking (Phase 4) | AWS native + open-source |
| **Logging** | Structured JSON | N/A | Application logs, audit trail | CloudWatch-compatible |
| **Testing** | pytest + pytest-asyncio | Latest | Python unit/integration tests | Standard testing stack |

---

## 6. Complete Reference Implementation

### 6.1 MCP Server (raglite/main.py)

**This is the COMPLETE reference implementation.** AI agents should copy these patterns for all modules.

*[See architecture-v1.1-insert.md for the complete 250-line reference implementation]*

**Key file:** `raglite/main.py` (~200 lines)

**Demonstrates:**
- ✅ FastMCP server setup with lifespan management
- ✅ Pydantic model definitions for MCP tools
- ✅ Structured logging with context (`extra={}`)
- ✅ Error handling with specific exceptions
- ✅ Type hints for all functions
- ✅ Google-style docstrings
- ✅ Async patterns for I/O operations

**Pattern Summary:**
```python
# 1. Structured Logging
logger.info("Event", extra={"key": "value"})

# 2. Error Handling
try:
    result = await operation()
except SpecificError as e:
    logger.error("Error", extra={"context": value}, exc_info=True)
    raise ValueError(f"User message: {e}")

# 3. Pydantic Models
class RequestModel(BaseModel):
    field: str = Field(..., description="Description")

# 4. Async Functions
async def my_function(param: str) -> Result:
    return await async_operation()

# 5. Type Hints (Required)
def func(x: str, y: Optional[int] = None) -> Dict[str, Any]:
    pass
```

### 6.2 Coding Standards

**Follow PEP 8 with these requirements:**

1. **Type Hints:** Required for all function signatures
2. **Docstrings:** Google-style for all public functions/classes
3. **Import Organization:** stdlib → third-party → local
4. **Error Handling:** Specific exceptions with context
5. **Logging:** Structured with `extra={}` context
6. **Constants:** UPPER_CASE naming
7. **Functions:** Verb phrases (e.g., `ingest_document`, not `document`)

**Testing Standards:**
- **Organization:** Co-located in `raglite/tests/`
- **Naming:** `test_<module>_<function>_<scenario>.py`
- **Coverage:** 50%+ for MVP (critical paths), 80%+ for Phase 4
- **Tools:** pytest, pytest-asyncio

**Formatting & Linting:**
```bash
# Before commit
poetry run black raglite/
poetry run isort raglite/
poetry run ruff check raglite/
poetry run mypy raglite/
```

---

## 7. Data Layer

### 7.1 Qdrant (Vector Database)

**Purpose:** Store and search document embeddings

**Schema:**
```python
# Collection: financial_documents
{
    "collection_name": "financial_documents",
    "vector_config": {
        "size": 1024,  # Fin-E5 embedding dimension
        "distance": "Cosine"
    }
}

# Point (Document Chunk):
{
    "id": "uuid-chunk-id",
    "vector": [0.123, -0.456, ...],  # 1024-dim
    "payload": {
        "document_id": "doc-12345",
        "document_name": "Q3_2024_Financial_Report.pdf",
        "chunk_text": "Q3 revenue increased 12%...",
        "chunk_context": "This chunk discusses Q3 2024 revenue...",  # Contextual Retrieval
        "page_number": 3,
        "section": "Revenue Analysis",
        "fiscal_period": "Q3_2024"
    }
}
```

**Deployment:**
- **Local:** Docker container (`qdrant/qdrant:latest`)
- **Production:** Qdrant Cloud (managed) or self-hosted EKS

**Performance:**
- Query latency: <100ms (p50), <500ms (p95)
- Throughput: 100+ queries/sec
- Accuracy: 90%+ retrieval on financial test set

### 7.2 S3 / Local Storage (Documents)

**Structure:**
```
raglite-documents/
├── raw/                        # Original PDFs/Excel
│   └── Q3_2024_Financial_Report.pdf
├── processed/
│   └── doc-12345/
│       ├── metadata.json       # Document metadata
│       ├── chunks/             # Extracted chunks
│       │   ├── chunk-001.json
│       │   └── chunk-002.json
│       └── embeddings/
│           └── embeddings.npy  # Numpy array of vectors
└── versions/                   # Document version history
    └── doc-12345/
        ├── v1_2024-09-01.pdf
        └── v2_2024-10-01.pdf
```

**Deployment:**
- **Local:** `./data/documents/` directory
- **Production:** AWS S3 with versioning + encryption

### 7.3 Neo4j (Graph Database - Phase 2 Conditional)

**⚠️ ONLY IMPLEMENT IF PHASE 1 ACCURACY <90% AND FAILURES ARE RELATIONAL**

**Schema:** (See v1.0 reference sections for detailed Neo4j schema)

---

## 8. Phased Implementation Strategy (v1.1 Simplified)

### Phase 1: Monolithic MVP (Weeks 1-4)

**Goal:** Working Q&A system with 90%+ retrieval accuracy

**Week-by-Week Breakdown:**

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

**Week 4: Accuracy Validation**
- Files to create: `tests/ground_truth.py`
- Tasks:
  - ✅ Create ground truth test set (20-50 queries)
  - ✅ Manual accuracy validation
  - ✅ Performance measurement (<10s response)
  - ✅ User testing with real documents
- Deliverable: Validation report + Phase 2 decision

**Success Criteria:**
- ✅ Can ingest 5 financial PDFs successfully (≥4/5 succeed)
- ✅ 80%+ of test queries return useful answers (≥16/20)
- ✅ Query response time <10 seconds (≥8/10 queries)
- ✅ All answers include source citations (20/20)

**Decision Gate (End of Week 4):**

**IF Success Criteria Met:**
- ✅ MVP SUCCESS → Proceed to Phase 3 (Forecasting/Insights)
- ✅ SKIP Phase 2 (GraphRAG)

**IF Accuracy <80%:**
- Analyze failures:
  - **IF relational queries** (multi-entity correlations) → Consider Phase 2
  - **ELSE retrieval quality** → Improve chunking/embeddings → Retry

**Technologies:**
- FastMCP, Docling, Fin-E5, Qdrant, Claude 3.7 Sonnet
- Docker Compose (Qdrant + app)
- pytest for basic testing

### Phase 2: GraphRAG (Weeks 5-8) - CONDITIONAL

**⚠️ ONLY IMPLEMENT IF PHASE 1 DECISION GATE TRIGGERS**

*(Detailed in v1.0 reference sections below)*

### Phase 3: Intelligence Features (Weeks 9-12 or 5-8)

**Goal:** Add forecasting and proactive insights

*(Detailed in v1.0 reference sections below)*

### Phase 4: Production Readiness (Weeks 13-16)

**Goal:** AWS deployment, monitoring, performance optimization

*(Detailed in v1.0 reference sections below)*

**Microservices Decision (End of Week 16):**
- Refactor to microservices ONLY IF proven scale problems exist
- See "Evolution Path" section below for migration strategy

---

## 9. Deployment Strategy (Simplified)

### Phase 1-3: Local Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_data:/qdrant/storage

  raglite:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/data
      - ./.env:/app/.env
    environment:
      - QDRANT_HOST=qdrant
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    depends_on:
      - qdrant
```

**Setup:**
```bash
# One-command setup
./scripts/setup-dev.sh

# Starts Qdrant + RAGLite on http://localhost:5000
```

### Phase 4: AWS Production

*(See v1.0 reference sections for detailed AWS deployment with Terraform)*

**Simplified Production:**
- ECS Fargate: 1 task (monolithic container)
- Qdrant Cloud: Managed vector DB
- S3: Document storage
- CloudWatch: Monitoring

**Cost (Monolithic):** ~$115-165/month

---

# Part 2: v1.0 MICROSERVICES REFERENCE (Future Scaling)

**Use this section when you have proven scale problems requiring independent service scaling.**

---

*[The rest of the original architecture.md content follows here, serving as detailed reference for when you need to scale to microservices in Phase 4+]*

