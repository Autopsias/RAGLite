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



---



## Executive Summary

### Architectural Vision

RAGLite implements a **microservices-based MCP server architecture** with **phased complexity introduction** to minimize risk and cost while delivering maximum value.

**Key Architectural Decisions:**

1. **Phased Graph Approach**
   - **Phase 1:** Anthropic Contextual Retrieval (98.1% accuracy, $0.82 cost)
   - **Phase 2:** Agentic GraphRAG (only if multi-hop accuracy <95%)
   - **Savings:** 99% cost reduction if Phase 2 proves unnecessary

2. **Multi-LLM Flexibility**
   - **AWS Strands** orchestration (not Claude Agent SDK)
   - Supports Claude, GPT-4, Gemini, Llama, local models
   - No vendor lock-in to single LLM provider

3. **Microservices Pattern**
   - 5 independent services: Ingestion, Retrieval, GraphRAG, Forecasting, Insights
   - MCP Gateway aggregates all services
   - Each service exposes tools via Model Context Protocol

4. **Production-Proven Technologies**
   - Docling (97.9% table accuracy)
   - Fin-E5 embeddings (71.05% financial domain accuracy)
   - AWS Strands (production-validated: Amazon Q, AWS Glue)
   - MCP Python SDK (official, 19k GitHub stars)

### Architecture at a Glance

```
┌──────────────────────────────────────────────────────────┐
│  MCP Clients (Claude Code, Custom Apps)                 │
└────────────────────┬─────────────────────────────────────┘
                     │ Model Context Protocol
┌────────────────────▼─────────────────────────────────────┐
│  MCP Gateway (FastMCP - Aggregator)                      │
│  Exposes unified tool catalog from all microservices     │
└──┬────┬────┬────┬────┬──────────────────────────────────┘
   │    │    │    │    │
   ▼    ▼    ▼    ▼    ▼
┌────┐┌────┐┌────┐┌────┐┌────┐
│ M1 ││ M2 ││ M3 ││ M4 ││ M5 │  Microservices (MCP Servers)
└─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘
  │     │     │     │     │
  └─────┴─────┴─────┴─────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│  AWS Strands Orchestration Layer                        │
│  ├─ Retrieval Agent → calls M2 tools                    │
│  ├─ Analysis Agent → interprets data (LLM reasoning)    │
│  ├─ GraphRAG Agent → calls M3 (Phase 2)                 │
│  └─ Synthesis Agent → combines results                  │
└──────────┬──────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│  Data Layer                                             │
│  ├─ Qdrant (Vector DB)                                  │
│  ├─ Neo4j (GraphRAG - Phase 2 conditional)              │
│  └─ S3/Local Storage (Documents, embeddings)            │
└─────────────────────────────────────────────────────────┘
```

**Legend:**
- M1: Ingestion Service
- M2: Retrieval Service
- M3: GraphRAG Service (Phase 2)
- M4: Forecasting Service
- M5: Insights Service

---

## Research Findings Summary

### Validated Technologies

The architecture is based on **4 comprehensive deep research reports** validating all critical technologies:

#### 1. Document Processing & Retrieval

**Docling PDF Extraction:**
- 97.9% table cell accuracy on complex financial PDFs
- Surpasses AWS Textract (88%) and PyMuPDF (no table models)
- Cost: <$0.005/page (GPU amortized)

**Fin-E5 Embeddings:**
- 71.05% NDCG@10 on financial domain retrieval
- +5.6% improvement over general-purpose models
- Alternative: Voyage-3-large (74.63% commercial)

#### 2. Graph Approach: Contextual Retrieval → GraphRAG

**Phase 1: Anthropic Contextual Retrieval** (VALIDATED)
- **Accuracy:** 96.3-98.1% (vs. 94.3% baseline)
- **Cost:** $0.82 one-time for 100 documents
- **Method:** LLM-generated 50-100 token context per chunk
- **Limitation:** Limited multi-hop reasoning capability

**Phase 2: Agentic GraphRAG** (CONDITIONAL - only if Phase 1 <95%)
- **Accuracy:** +12-18% on multi-hop queries
- **Cost:** $9 construction + $20/month queries (100 docs, 1000 queries)
- **Implementation:** Microsoft Research approach (community detection + agent navigation)

**Decision Gate:** If Contextual Retrieval achieves 95%+ accuracy on multi-hop queries, **skip GraphRAG entirely** (99% cost savings)

#### 3. Orchestration: AWS Strands (Not Claude Agent SDK)

**Why AWS Strands:**
- ✅ **Multi-LLM support:** Claude, GPT-4, Gemini, Llama, Ollama, local models
- ✅ **No vendor lock-in:** Can switch LLM providers without code changes
- ✅ **Production-proven:** Amazon Q Developer, AWS Glue, VPC Reachability Analyzer
- ✅ **Native MCP support:** Built-in MCP client for tool integration
- ✅ **150K+ PyPI downloads:** Established community

**Comparison:**

| Feature | AWS Strands | Claude Agent SDK | LangGraph |
|---------|-------------|------------------|-----------|
| **Multi-LLM** | ✅ 10+ providers | ⚠️ Claude/Bedrock/Vertex | ✅ Any via API |
| **Vendor Lock-in** | **LOW** | MEDIUM | LOW |
| **Production Use** | Amazon Q, Glue | Claude Code | Widespread |
| **MCP Native** | ✅ Yes | ✅ Yes | ⚠️ Adapters |

#### 4. MCP Server: FastMCP (Official Python SDK)

- **Official reference implementation** (19k GitHub stars)
- **Production-ready transports:** Streamable HTTP for scalability
- **Full protocol support:** Tools, resources, prompts, OAuth 2.1
- **ASGI integration:** Can mount into FastAPI if needed

#### 5. Forecasting: Hybrid Approach

- **Statistical core** (Prophet/ARIMA) + **LLM adjustment**
- **±8% forecast error** (beats ±15% PRD target)
- **Cost:** $0.015 per forecast

### Cost Analysis (Year 1)

| Approach | Preprocessing | Monthly Queries | Total Year 1 | Savings |
|----------|--------------|-----------------|--------------|---------|
| **Phase 1 Only** (Contextual Retrieval) | $0.82 | $2/month | **~$25** | - |
| **Phase 2** (Add GraphRAG) | +$9 | +$20/month | **~$274** | -91% vs original |
| **Original Plan** (GraphRAG from start) | $9 | $20/month | **$249** | Baseline |

**Result:** If Contextual Retrieval proves sufficient, **99% cheaper than original plan** ($0.82 vs $249)

---

## High-Level Architecture

### System Overview

RAGLite follows a **layered microservices architecture** with clear separation of concerns:

**Layer 1: Client Layer** (External)
- MCP-compatible clients (Claude Code, Claude Desktop, custom applications)
- Interact via Model Context Protocol
- No custom frontend in MVP

**Layer 2: Gateway Layer** (Aggregation)
- MCP Gateway (FastMCP) aggregates all microservices
- Exposes unified tool catalog to clients
- Handles routing to appropriate service

**Layer 3: Microservices Layer** (Business Logic)
- 5 independent MCP servers, each exposing domain-specific tools
- Services communicate via shared data layer (not direct service-to-service)
- Each service independently scalable

**Layer 4: Orchestration Layer** (Intelligence)
- AWS Strands agents coordinate complex workflows
- Multi-agent patterns: Retrieval Agent, Analysis Agent, GraphRAG Agent, Synthesis Agent
- LLM-based reasoning and interpretation happen here

**Layer 5: Data Layer** (Persistence)
- Qdrant: Vector database for embeddings
- Neo4j: Graph database (Phase 2 conditional)
- S3/Local Storage: Documents, metadata, artifacts

### Architectural Patterns

**1. Microservices Architecture**
- **Pattern:** Domain-driven microservices with MCP interface
- **Rationale:** Independent scaling, clear boundaries, graceful degradation

**2. Model Context Protocol (MCP) Integration**
- **Pattern:** All services expose capabilities via MCP tools
- **Rationale:** Standard protocol, client flexibility, future-proof

**3. Phased Complexity Introduction**
- **Pattern:** Start simple (Contextual Retrieval), add complexity only if proven necessary (GraphRAG)
- **Rationale:** Minimize risk, validate value before investment

**4. Multi-Agent Orchestration**
- **Pattern:** AWS Strands agents coordinate across microservices
- **Rationale:** Complex workflows, multi-step reasoning, LLM flexibility

**5. Graceful Degradation**
- **Pattern:** System continues operating with reduced capabilities if advanced features fail
- **Rationale:** Reliability, user experience continuity

---

## Technology Stack

### Definitive Technology Selection

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **PDF Extraction** | Docling | Latest | Extract text, tables, structure from PDFs | 97.9% table accuracy, DocLayNet-based, surpasses Textract |
| **Excel Processing** | openpyxl + pandas | Latest | Extract tabular data from Excel | Standard Python libraries, formula preservation |
| **Embedding Model** | Fin-E5 (finance-adapted e5-mistral-7b) | Latest | Generate semantic vectors for financial text | 71.05% financial domain NDCG@10, +5.6% vs general models |
| **Chunking Strategy** | Contextual Retrieval | N/A | LLM-generated 50-100 token context per chunk | 98.1% retrieval accuracy, $1.02/M tokens preprocessing |
| **Vector Database** | Qdrant | 1.11+ | Store and search document embeddings | HNSW indexing, sub-5s retrieval, Docker-friendly, swappable |
| **Graph Database** | Neo4j | 5.x | Store knowledge graph (Phase 2) | Cypher queries, Agentic GraphRAG support, managed cloud option |
| **MCP Server Framework** | MCP Python SDK (FastMCP) | 1.x | Expose microservices via MCP protocol | Official SDK, 19k stars, Streamable HTTP, production-ready |
| **Orchestration** | **AWS Strands** | 1.x | Multi-agent workflow coordination | Multi-LLM support, no vendor lock-in, Amazon Q proven |
| **LLM (Primary)** | Claude 3.7 Sonnet | via Bedrock | Reasoning, analysis, contextualization | State-of-art reasoning, 200K context, financial domain strong |
| **LLM (Alternative)** | GPT-4.1, Gemini 2.0 | via APIs | LLM flexibility testing | AWS Strands enables easy model swapping |
| **Forecasting (Statistical)** | Prophet | 1.1+ | Time-series baseline forecasting | Facebook's library, handles seasonality, easy integration |
| **Forecasting (LLM)** | Claude API | N/A | Forecast adjustment and context | LLM-based residual correction for ±8% accuracy |
| **Backend Language** | Python | 3.11+ | All microservices implementation | RAG ecosystem standard, AI/ML library support, async support |
| **API Framework** | FastAPI | 0.115+ | REST endpoints (if needed), ASGI support | High performance, async native, OpenAPI auto-docs |
| **Document Storage** | S3 (cloud) / Local FS (dev) | N/A | Store ingested documents and artifacts | Scalable, versioning, encryption at rest |
| **Secrets Management** | AWS Secrets Manager (cloud) / .env (dev) | N/A | API keys, credentials | Secure, rotatable, audit-logged |
| **Containerization** | Docker + Docker Compose | Latest | Local development environment | Service isolation, reproducible environments |
| **Cloud Platform** | AWS | N/A | Production deployment | ECS/EKS, managed Qdrant/OpenSearch, Bedrock integration |
| **IaC Tool** | Terraform (or CDK) | Latest | Infrastructure as Code | Version-controlled infrastructure, AWS native |
| **CI/CD** | GitHub Actions | N/A | Automated testing and deployment | Git-integrated, Docker support, AWS deployment |
| **Monitoring** | CloudWatch + Prometheus | N/A | Performance tracking, alerting | AWS native + open-source metrics |
| **Logging** | CloudWatch Logs + Structured JSON | N/A | Application logs, query audit trail | Centralized, queryable, compliant (NFR14) |
| **Testing (Unit)** | pytest | Latest | Python unit tests (80%+ coverage target) | Standard Python testing, mocking support |
| **Testing (Integration)** | pytest + Docker | Latest | End-to-end pipeline tests | Docker test containers, real service integration |
| **Testing (Accuracy)** | Custom test harness | N/A | Ground truth query validation (50+ queries) | Measure 90%+ retrieval, 95%+ attribution accuracy |

---

## Microservices Architecture

### Service Overview

RAGLite consists of **5 independent microservices**, each exposing MCP tools:

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Gateway (FastMCP Aggregator)                           │
│  Route: /mcp/tools                                          │
│  Aggregates: M1 + M2 + M3 + M4 + M5 tool catalogs          │
└──┬────┬────┬────┬────┬──────────────────────────────────────┘
   │    │    │    │    │
   │    │    │    │    └─────────────────────┐
   │    │    │    │                           │
   │    │    │    └──────────────┐            │
   │    │    │                   │            │
   │    │    └───────┐           │            │
   │    │            │           │            │
   │    └─────┐      │           │            │
   │          │      │           │            │
┌──▼───┐ ┌───▼──┐ ┌─▼────┐ ┌───▼───┐ ┌─────▼─────┐
│  M1  │ │  M2  │ │  M3  │ │  M4   │ │    M5     │
│Ingest│ │Retrie│ │Graph │ │Foreca │ │ Insights  │
│      │ │val   │ │RAG   │ │st     │ │           │
└──┬───┘ └───┬──┘ └─┬────┘ └───┬───┘ └─────┬─────┘
   │         │      │          │           │
   └─────────┴──────┴──────────┴───────────┘
                    │
         ┌──────────▼──────────────────┐
         │  Shared Data Layer          │
         │  ├─ Qdrant (Vector DB)      │
         │  ├─ Neo4j (Graph - Phase 2) │
         │  └─ S3 (Documents)          │
         └─────────────────────────────┘
```

### Microservice #1: Ingestion Service

**Port:** 5001
**MCP Path:** `/mcp/ingestion`
**Technology:** FastMCP + Docling + Fin-E5

**Responsibilities:**
1. PDF extraction (Docling) with 97.9% table accuracy
2. Excel parsing (openpyxl + pandas)
3. Contextual chunking (LLM-generated context per chunk)
4. Embedding generation (Fin-E5 model)
5. Vector storage (Qdrant)
6. Metadata extraction and indexing

**MCP Tools Exposed:**

```python
@mcp.tool()
async def ingest_document(file_path: str, document_type: str) -> IngestionJobID:
    """
    Trigger document ingestion pipeline.

    Args:
        file_path: Path to PDF or Excel file
        document_type: "financial_report" | "earnings_transcript" | "excel_data"

    Returns:
        job_id for status tracking
    """

@mcp.tool()
async def get_ingestion_status(job_id: str) -> IngestionStatus:
    """
    Check ingestion job progress.

    Returns:
        status, progress_pct, chunks_processed, errors
    """

@mcp.tool()
async def list_indexed_documents() -> List[Document]:
    """
    List all successfully ingested documents with metadata.

    Returns:
        document_id, filename, type, ingestion_date, chunk_count
    """
```

**Architecture Pattern:**

```
┌────────────────────────────────────────────────┐
│  Ingestion Service (FastMCP Server)           │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │  MCP Tool Handler Layer                  │ │
│  │  - ingest_document()                     │ │
│  │  - get_ingestion_status()                │ │
│  │  - list_indexed_documents()              │ │
│  └────────────┬─────────────────────────────┘ │
│               │                                │
│  ┌────────────▼─────────────────────────────┐ │
│  │  Async Worker Pool (Celery/RQ)          │ │
│  │  - Long-running ingestion tasks          │ │
│  │  - Progress reporting via MCP progress() │ │
│  └────────────┬─────────────────────────────┘ │
│               │                                │
│  ┌────────────▼─────────────────────────────┐ │
│  │  Processing Pipeline                     │ │
│  │  1. Docling PDF/Excel extraction         │ │
│  │  2. Contextual chunking (Claude API)     │ │
│  │  3. Fin-E5 embedding generation          │ │
│  │  4. Qdrant vector storage                │ │
│  └────────────┬─────────────────────────────┘ │
└───────────────┼─────────────────────────────┐┘
                │
┌───────────────▼─────────────────────────────┐
│  Data Layer                                 │
│  ├─ Qdrant: Store embeddings + metadata    │
│  └─ S3: Store original documents + chunks  │
└─────────────────────────────────────────────┘
```

**Performance Targets:**
- Ingestion: <5 minutes for 100-page financial report (NFR2)
- Concurrent jobs: 3+ documents simultaneously
- Error rate: <3% for well-formed documents

---

### Microservice #2: Retrieval Service

**Port:** 5002
**MCP Path:** `/mcp/retrieval`
**Technology:** FastMCP + Qdrant + Fin-E5

**Responsibilities:**
1. Vector similarity search (semantic retrieval)
2. Contextual retrieval (leverage pre-generated contexts)
3. BM25 hybrid search (if needed for Phase 1 optimization)
4. Source attribution (document, page, section)
5. Result ranking and reranking

**MCP Tools Exposed:**

```python
@mcp.tool()
async def search_documents(
    query: str,
    top_k: int = 10,
    filters: Optional[Dict] = None,
    rerank: bool = True
) -> SearchResults:
    """
    Semantic search across indexed financial documents.

    Args:
        query: Natural language financial question
        top_k: Number of results to return (default 10)
        filters: Optional metadata filters (date_range, document_type)
        rerank: Apply reranking for improved accuracy

    Returns:
        chunks with content, source attribution, relevance scores
    """

@mcp.tool()
async def get_document_chunks(
    document_id: str,
    section: Optional[str] = None
) -> List[Chunk]:
    """
    Retrieve specific chunks from a document by section.

    Args:
        document_id: Unique document identifier
        section: Optional section filter (e.g., "Revenue Analysis")

    Returns:
        chunks with full context and metadata
    """
```

**Retrieval Flow:**

```
User Query: "What drove Q3 revenue variance?"
            │
            ▼
┌───────────────────────────────────────────────┐
│ 1. Query Embedding (Fin-E5)                  │
│    - Generate 1024-dim vector for query      │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 2. Vector Search (Qdrant)                    │
│    - HNSW similarity search                   │
│    - Apply metadata filters if provided      │
│    - Return top 20 candidates                 │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 3. Contextual Enhancement                    │
│    - Prepend LLM-generated context to chunks │
│    - Improves downstream LLM interpretation  │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 4. Optional Reranking                        │
│    - Cross-encoder reranking for top 20      │
│    - Return top 10 highest relevance         │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 5. Source Attribution                        │
│    - Attach (document, page, section) refs   │
│    - Format citations                        │
└───────────────┬───────────────────────────────┘
                │
                ▼
        Return SearchResults to caller
```

**Performance Targets:**
- Query response: <5 sec (p50), <15 sec (p95) - NFR13
- Retrieval accuracy: 90%+ on ground truth test set (NFR6)
- Source attribution accuracy: 95%+ (NFR7)

---

### Microservice #3: GraphRAG Service (Phase 2 - Conditional)

**Port:** 5003
**MCP Path:** `/mcp/graphrag`
**Technology:** FastMCP + Neo4j + Claude API (for entity extraction & agent navigation)

**⚠️ IMPLEMENTATION CONDITIONAL ON PHASE 1 RESULTS:**
- Only implement if Contextual Retrieval achieves <95% accuracy on multi-hop queries
- Decision gate: Week 4 of development after Contextual Retrieval validation

**Responsibilities (if implemented):**
1. Entity extraction (companies, departments, metrics, KPIs, time periods)
2. Knowledge graph construction (relationships, hierarchies, correlations)
3. Community detection (Microsoft GraphRAG approach)
4. Agentic graph navigation (multi-hop reasoning)
5. Graph updates (incremental when new documents ingested)

**MCP Tools Exposed (if implemented):**

```python
@mcp.tool()
async def navigate_graph(
    query: str,
    max_hops: int = 3,
    entities: Optional[List[str]] = None
) -> GraphNavigationResult:
    """
    Navigate knowledge graph for multi-hop relational queries.

    Args:
        query: Relational question (e.g., "How does marketing correlate with revenue?")
        max_hops: Maximum graph traversal depth
        entities: Optional seed entities to start traversal

    Returns:
        traversal_path, related_entities, relationships, supporting_data
    """

@mcp.tool()
async def find_correlations(
    entity_a: str,
    entity_b: str,
    time_range: Optional[DateRange] = None
) -> CorrelationResult:
    """
    Discover relationships between financial entities.

    Args:
        entity_a: First entity (e.g., "Marketing Spend")
        entity_b: Second entity (e.g., "Revenue Growth")
        time_range: Optional temporal filter

    Returns:
        correlation_strength, causal_indicators, time_series_data
    """

@mcp.tool()
async def build_graph(document_ids: List[str]) -> GraphBuildJobID:
    """
    Trigger knowledge graph construction for documents.

    Args:
        document_ids: Documents to extract entities and build graph from

    Returns:
        job_id for async graph construction tracking
    """
```

**GraphRAG Architecture (if implemented):**

```
┌────────────────────────────────────────────────┐
│  GraphRAG Service (FastMCP Server)            │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │  MCP Tool Handler Layer                  │ │
│  │  - navigate_graph()                      │ │
│  │  - find_correlations()                   │ │
│  │  - build_graph()                         │ │
│  └────────────┬─────────────────────────────┘ │
│               │                                │
│  ┌────────────▼─────────────────────────────┐ │
│  │  Graph Agent Navigator                   │ │
│  │  - LLM-powered traversal planning        │ │
│  │  - Multi-hop query decomposition         │ │
│  │  - Community summary retrieval           │ │
│  └────────────┬─────────────────────────────┘ │
│               │                                │
│  ┌────────────▼─────────────────────────────┐ │
│  │  Graph Construction Pipeline             │ │
│  │  1. Entity extraction (Claude API)       │ │
│  │  2. Relationship extraction               │ │
│  │  3. Community detection (Louvain)        │ │
│  │  4. Hierarchical summarization (LLM)     │ │
│  └────────────┬─────────────────────────────┘ │
└───────────────┼─────────────────────────────┐┘
                │
┌───────────────▼─────────────────────────────┐
│  Data Layer                                 │
│  └─ Neo4j: Knowledge graph storage          │
│     - Nodes: Entities (Company, Metric...)  │
│     - Edges: Relationships (CORRELATES...)  │
│     - Properties: Metadata, temporal data   │
└─────────────────────────────────────────────┘
```

**Cost (if implemented):**
- Graph construction: $9 one-time for 100 documents
- Multi-hop queries: $0.02 per query (2 LLM calls per hop average)

**Fallback Strategy:**
- If graph construction fails → Degrade to Contextual Retrieval (Service M2)
- If graph traversal fails → Return vector search results
- System continues operating without graph functionality (NFR32)

---

### Microservice #4: Forecasting Service

**Port:** 5004
**MCP Path:** `/mcp/forecasting`
**Technology:** FastMCP + Prophet + Claude API

**Responsibilities:**
1. Time-series data extraction from documents
2. Statistical baseline forecasting (Prophet/ARIMA)
3. LLM-based forecast adjustment
4. Confidence interval calculation
5. Forecast accuracy tracking

**MCP Tools Exposed:**

```python
@mcp.tool()
async def forecast_kpi(
    metric: str,
    horizon: int = 4,
    method: str = "hybrid"
) -> ForecastResult:
    """
    Generate financial forecast for specified KPI.

    Args:
        metric: KPI to forecast (e.g., "Revenue", "Cash Flow", "Marketing Spend")
        horizon: Number of periods ahead (quarters or months)
        method: "statistical" | "llm" | "hybrid" (default: hybrid)

    Returns:
        forecast_values, confidence_intervals, accuracy_estimate, rationale
    """

@mcp.tool()
async def update_forecast(
    metric: str,
    new_data: TimeSeriesData
) -> UpdatedForecast:
    """
    Refresh forecast with newly ingested data.

    Args:
        metric: KPI being forecasted
        new_data: Latest time-series data points

    Returns:
        updated_forecast, accuracy_comparison, data_quality_score
    """

@mcp.tool()
async def get_forecast_accuracy(
    metric: str,
    lookback_periods: int = 4
) -> AccuracyMetrics:
    """
    Evaluate historical forecast accuracy.

    Args:
        metric: KPI to analyze
        lookback_periods: How many past forecasts to evaluate

    Returns:
        mae, rmse, mape, forecast_vs_actuals
    """
```

**Hybrid Forecasting Flow:**

```
User Request: "Forecast Q4 2025 revenue"
            │
            ▼
┌───────────────────────────────────────────────┐
│ 1. Extract Time-Series Data                  │
│    - Query documents for historical revenue   │
│    - Normalize to quarterly intervals         │
│    - Validate data quality                    │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 2. Statistical Baseline (Prophet)            │
│    - Fit time-series model                    │
│    - Generate forecast with confidence        │
│    - Handle seasonality, trends               │
│    - Error: ±10-13% typically                 │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 3. LLM Contextual Adjustment (Claude)        │
│    - Provide baseline forecast + context      │
│    - LLM considers qualitative factors        │
│    - Adjust forecast based on reasoning       │
│    - Residual correction approach             │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 4. Hybrid Result                             │
│    - Combined forecast: ±8% error             │
│    - Confidence intervals                     │
│    - Rationale from LLM                       │
│    - Meets NFR10 target (±15%)                │
└───────────────┬───────────────────────────────┘
                │
                ▼
        Return ForecastResult
```

**Performance Targets:**
- Forecast accuracy: ±8% (beats ±15% PRD target)
- Generation time: <10 seconds
- Cost: $0.015 per forecast

---

### Microservice #5: Insights Service

**Port:** 5005
**MCP Path:** `/mcp/insights`
**Technology:** FastMCP + Claude API + Statistical analysis libraries

**Responsibilities:**
1. Anomaly detection (statistical thresholds, outlier identification)
2. Trend analysis (growth patterns, cyclical trends)
3. Strategic recommendations (LLM-powered)
4. Insight priority ranking
5. Proactive alert generation

**MCP Tools Exposed:**

```python
@mcp.tool()
async def generate_insights(
    scope: str = "all",
    priority_threshold: str = "medium"
) -> InsightsList:
    """
    Generate proactive financial insights from indexed data.

    Args:
        scope: "all" | "risks" | "opportunities" | "anomalies" | "trends"
        priority_threshold: "low" | "medium" | "high" | "critical"

    Returns:
        insights with category, priority, evidence, recommendations
    """

@mcp.tool()
async def analyze_anomalies(
    time_range: DateRange,
    sensitivity: float = 2.0
) -> AnomalyReport:
    """
    Detect and explain financial anomalies.

    Args:
        time_range: Period to analyze
        sensitivity: Standard deviations for anomaly threshold (default: 2.0)

    Returns:
        anomalies with magnitude, context, potential causes
    """

@mcp.tool()
async def get_recommendations(
    focus_area: Optional[str] = None
) -> RecommendationList:
    """
    Strategic recommendations based on financial analysis.

    Args:
        focus_area: Optional filter (e.g., "cost_reduction", "revenue_growth")

    Returns:
        recommendations with rationale, impact_estimate, supporting_data
    """
```

**Insight Generation Architecture:**

```
Scheduled Job (Daily) or User Request
            │
            ▼
┌───────────────────────────────────────────────┐
│ 1. Data Aggregation                          │
│    - Query recent financial data              │
│    - Pull forecasts, trends, anomalies        │
│    - Gather external context (if available)   │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 2. Statistical Analysis                      │
│    - Anomaly detection (Z-score, IQR)        │
│    - Trend identification (linear regression)│
│    - Correlation analysis                    │
│    - Variance decomposition                  │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 3. LLM Strategic Reasoning (Claude)          │
│    - Interpret statistical findings           │
│    - Generate strategic insights              │
│    - Provide actionable recommendations      │
│    - Rank by priority and impact              │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 4. Insight Ranking & Filtering               │
│    - Score by priority (critical→low)         │
│    - Filter by user threshold                 │
│    - Attach supporting evidence               │
└───────────────┬───────────────────────────────┘
                │
                ▼
        Return InsightsList
```

**Performance Targets:**
- Insight quality: 75%+ rated useful/actionable by user
- Recommendation alignment: 80%+ match expert analysis
- Generation time: <15 seconds for comprehensive analysis

---

### MCP Gateway (Service Aggregator)

**Port:** 5000
**MCP Path:** `/mcp`
**Technology:** FastMCP

**Purpose:**
Aggregates all 5 microservices into a unified MCP server, exposing a single tool catalog to MCP clients.

**Implementation:**

```python
# mcp_gateway.py
from mcp import FastMCP
from mcp.client import MCPClient

# Initialize gateway
gateway = FastMCP("raglite-gateway")

# Connect to all microservices
ingestion_client = MCPClient("http://localhost:5001/mcp")
retrieval_client = MCPClient("http://localhost:5002/mcp")
graphrag_client = MCPClient("http://localhost:5003/mcp")  # Phase 2
forecast_client = MCPClient("http://localhost:5004/mcp")
insights_client = MCPClient("http://localhost:5005/mcp")

# Discover and aggregate tools
@gateway.on_startup()
async def aggregate_tools():
    """Discover all tools from microservices and expose them."""
    tools = []
    tools.extend(await ingestion_client.list_tools())
    tools.extend(await retrieval_client.list_tools())
    # tools.extend(await graphrag_client.list_tools())  # Conditional
    tools.extend(await forecast_client.list_tools())
    tools.extend(await insights_client.list_tools())

    # Register all tools with gateway
    for tool in tools:
        gateway.register_tool(tool)

# Route tool calls to appropriate service
@gateway.tool_router()
async def route_tool_call(tool_name: str, params: dict):
    """Route tool call to owning microservice."""
    service_map = {
        "ingest_document": ingestion_client,
        "search_documents": retrieval_client,
        "navigate_graph": graphrag_client,
        "forecast_kpi": forecast_client,
        "generate_insights": insights_client,
        # ... map all tools
    }

    client = service_map.get(tool_name)
    if not client:
        raise ValueError(f"Unknown tool: {tool_name}")

    return await client.call_tool(tool_name, params)

# Health check aggregation
@gateway.tool()
async def health_check() -> dict:
    """Check health of all microservices."""
    return {
        "gateway": "healthy",
        "ingestion": await ingestion_client.health(),
        "retrieval": await retrieval_client.health(),
        # "graphrag": await graphrag_client.health(),  # Phase 2
        "forecast": await forecast_client.health(),
        "insights": await insights_client.health(),
    }

# Run gateway server
if __name__ == "__main__":
    gateway.run(transport="streamable-http", host="0.0.0.0", port=5000)
```

**Benefits:**
- **Single endpoint** for MCP clients
- **Service discovery** automated
- **Load balancing** potential for scaled deployments
- **Health aggregation** for monitoring
- **Graceful degradation** if individual services fail

---

## Orchestration Layer

### AWS Strands Multi-Agent Architecture

The orchestration layer uses **AWS Strands** to coordinate complex workflows across microservices. Strands agents call MCP tools exposed by services and use LLM reasoning to interpret results.

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  AWS Strands Agent System                                   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Supervisor Agent (Orchestrator)                       │ │
│  │  - Receives user query via MCP client                  │ │
│  │  - Decomposes into sub-tasks                           │ │
│  │  - Delegates to specialized agents                     │ │
│  │  - Synthesizes final response                          │ │
│  └──┬────────┬────────┬────────┬────────────────────────┬─┘ │
│     │        │        │        │                        │   │
│  ┌──▼───┐ ┌─▼────┐ ┌─▼─────┐ ┌▼────────┐ ┌────────────▼─┐ │
│  │Retrie││Analys││GraphR ││Forecast ││ Synthesis    │ │
│  │val   ││is    ││AG     ││         ││ Agent        │ │
│  │Agent ││Agent ││Agent  ││Agent    ││              │ │
│  └──┬───┘ └─┬────┘ └─┬─────┘ └┬────────┘ └────────────┬─┘ │
│     │       │        │        │                        │   │
│     │       │        │        │                        │   │
│  Calls   Interpre Navigate  Generate               Combine│
│  M2      ts data  s M3      s M4                  results│
│  tools   (LLM)    tools     tools                          │
└─────┴───────┴────────┴────────┴──────────────────────────┴─┘
       │       │        │        │                        │
       ▼       ▼        ▼        ▼                        ▼
    MCP Gateway (calls appropriate microservice tools)
```

### Agent Definitions

#### 1. Retrieval Agent

**Purpose:** Retrieve relevant financial data from documents

**Tools Used:**
- `search_documents()` from Retrieval Service (M2)
- `get_document_chunks()` from Retrieval Service (M2)

**System Prompt:**
```
You are a Retrieval Agent specialized in finding relevant financial information.

Your capabilities:
- Semantic search across financial documents
- Understanding financial terminology and context
- Extracting specific data points with source attribution

When given a query:
1. Formulate effective search queries
2. Call search_documents() tool with appropriate parameters
3. Return retrieved chunks with clear source citations
4. If initial results insufficient, refine search strategy

Always prioritize accuracy and source attribution.
```

**Example Flow:**
```
User Query: "What drove Q3 revenue variance?"

Retrieval Agent:
1. Calls search_documents(query="Q3 revenue variance drivers", top_k=10)
2. Receives 10 chunks with financial data
3. Returns results to Supervisor with source citations
```

#### 2. Analysis Agent

**Purpose:** Interpret financial data using LLM reasoning

**Tools Used:**
- No direct tool calls (pure LLM reasoning)
- Receives data from Retrieval Agent or GraphRAG Agent

**System Prompt:**
```
You are a Financial Analysis Agent specialized in interpreting financial data.

Your capabilities:
- Understanding complex financial relationships
- Calculating financial ratios and metrics
- Identifying trends, patterns, and anomalies
- Explaining variance drivers

When given financial data:
1. Analyze the data using financial domain knowledge
2. Identify key insights and drivers
3. Provide clear, actionable interpretations
4. Quantify findings where possible

Use proper financial terminology and provide reasoning steps.
```

**Example Flow:**
```
Input from Retrieval Agent:
- Q3 2024 revenue: $5.2M (down 12% QoQ)
- Q3 2024 marketing spend: $800K (down 30% QoQ)
- Q2 2024 revenue: $5.9M
- Q2 2024 marketing spend: $1.1M

Analysis Agent:
1. Calculates correlation: Revenue drop 12%, Marketing drop 30%
2. Identifies potential causation: Marketing reduction may drive revenue decline
3. Contextualizes: ROI implications (marketing efficiency analysis)
4. Returns interpretation: "Q3 revenue variance primarily driven by 30%
   marketing spend reduction. Revenue declined 12% despite marketing ROI
   remaining stable at ~$6.50 per marketing dollar."
```

#### 3. GraphRAG Agent (Phase 2 - Conditional)

**Purpose:** Navigate knowledge graph for multi-hop relational queries

**Tools Used:**
- `navigate_graph()` from GraphRAG Service (M3)
- `find_correlations()` from GraphRAG Service (M3)

**System Prompt:**
```
You are a GraphRAG Agent specialized in multi-hop relational reasoning.

Your capabilities:
- Navigate knowledge graph to discover relationships
- Answer complex queries requiring multiple entity connections
- Identify correlations and causal patterns
- Synthesize information across graph paths

When given a relational query:
1. Identify key entities and relationships needed
2. Plan graph traversal strategy (which hops, which paths)
3. Call navigate_graph() or find_correlations() tools
4. Interpret graph results in context of user question
5. Return findings with evidence from graph traversal

Prioritize accuracy over speed. Explain traversal logic.
```

**Example Flow (if implemented):**
```
User Query: "How does marketing spend correlate with revenue growth
            across all departments?"

GraphRAG Agent:
1. Identifies entities: "Marketing Spend", "Revenue Growth", [Departments]
2. Calls navigate_graph(
     query="marketing_spend correlation revenue_growth",
     max_hops=3
   )
3. Receives graph path:
   Marketing Spend → Department A → Revenue Growth: +0.73 correlation
   Marketing Spend → Department B → Revenue Growth: +0.45 correlation
   Marketing Spend → Department C → Revenue Growth: -0.12 correlation
4. Interprets: "Strong positive correlation in Dept A (0.73), moderate in
   Dept B (0.45), weak negative in Dept C (-0.12). Suggests marketing
   effectiveness varies significantly by department."
5. Returns analysis to Supervisor
```

#### 4. Forecast Agent

**Purpose:** Generate predictive insights for financial KPIs

**Tools Used:**
- `forecast_kpi()` from Forecasting Service (M4)
- `update_forecast()` from Forecasting Service (M4)

**System Prompt:**
```
You are a Forecast Agent specialized in financial predictions.

Your capabilities:
- Generate forecasts for revenue, expenses, cash flow, KPIs
- Provide confidence intervals and accuracy estimates
- Explain forecast rationale and assumptions
- Update forecasts with new data

When asked to forecast:
1. Identify the specific metric and horizon
2. Call forecast_kpi() tool with appropriate parameters
3. Interpret forecast results with confidence intervals
4. Explain methodology and key assumptions
5. Note any data quality limitations

Always provide context for forecast reliability.
```

**Example Flow:**
```
User Query: "What's the Q4 2025 revenue forecast?"

Forecast Agent:
1. Calls forecast_kpi(metric="Revenue", horizon=1, method="hybrid")
2. Receives:
   - Forecast: $5.8M
   - Confidence Interval: [$5.2M, $6.4M]
   - Accuracy Estimate: ±8%
   - Rationale: "Based on Q1-Q3 trend (12% growth) + qualitative
                 adjustment for seasonal patterns"
3. Returns to user: "Q4 2025 revenue forecast: $5.8M (range: $5.2M-$6.4M,
   ±8% typical error). Forecast assumes continued quarterly growth trend
   observed in first 3 quarters, adjusted for typical Q4 seasonality."
```

#### 5. Synthesis Agent

**Purpose:** Combine results from multiple agents into coherent answer

**Tools Used:**
- No direct tool calls (aggregation and synthesis)

**System Prompt:**
```
You are a Synthesis Agent responsible for combining multi-agent findings.

Your capabilities:
- Integrate results from retrieval, analysis, graph, forecast agents
- Resolve conflicting information
- Create coherent, comprehensive responses
- Maintain source attribution across all findings

When given results from multiple agents:
1. Identify key insights from each agent
2. Synthesize into a unified narrative
3. Preserve all source citations
4. Structure response for clarity (summary → details → sources)
5. Flag any uncertainties or conflicts

Prioritize clarity and completeness.
```

**Example Flow:**
```
Inputs from agents:
- Retrieval Agent: Q3 revenue data with citations
- Analysis Agent: Variance interpretation (marketing driver)
- Forecast Agent: Q4 forecast based on trend

Synthesis Agent:
1. Combines findings:
   "Q3 2024 revenue declined 12% to $5.2M, primarily driven by a 30%
    reduction in marketing spend (Analysis: marketing ROI remained stable
    at $6.50 per dollar). Based on this trend and Q4 seasonality, forecasted
    Q4 revenue is $5.8M (±8% confidence interval: $5.2M-$6.4M)."

2. Adds source attribution:
   "Sources: Q3_Financial_Report.pdf (p.3, Revenue section),
    Q3_Marketing_Analysis.xlsx (Marketing Spend tab)"

3. Returns complete answer to user
```

### Multi-Agent Workflow Example

**Complex User Query:**
```
"Why did Q3 revenue drop, and what should we expect for Q4?"
```

**Orchestration Flow:**

```
User Query → Supervisor Agent (AWS Strands)
    │
    ├─> Task Decomposition:
    │   1. Find Q3 revenue data (Retrieval)
    │   2. Explain variance drivers (Analysis + optional GraphRAG)
    │   3. Generate Q4 forecast (Forecast)
    │   4. Synthesize complete answer (Synthesis)
    │
    ├─> Step 1: Retrieval Agent
    │   ├─ Calls search_documents("Q3 revenue variance")
    │   └─ Returns: Q3 revenue $5.2M (-12% QoQ), marketing $800K (-30% QoQ)
    │
    ├─> Step 2: Analysis Agent
    │   ├─ Receives data from Retrieval Agent
    │   └─ Interprets: "Revenue drop primarily driven by marketing reduction"
    │
    ├─> Step 2b: GraphRAG Agent (OPTIONAL - Phase 2)
    │   ├─ If needed for deeper relational analysis
    │   ├─ Calls navigate_graph("marketing revenue correlation")
    │   └─ Returns: Department-level correlation data
    │
    ├─> Step 3: Forecast Agent
    │   ├─ Calls forecast_kpi(metric="Revenue", horizon=1)
    │   └─ Returns: Q4 forecast $5.8M (±8%)
    │
    └─> Step 4: Synthesis Agent
        ├─ Combines all findings
        ├─ Preserves source citations
        └─ Returns to user:
            "Q3 revenue declined 12% to $5.2M, primarily due to 30%
             marketing spend reduction. Marketing ROI remained stable at
             $6.50 per dollar. Q4 forecast: $5.8M (confidence range:
             $5.2M-$6.4M, ±8%). Suggests recovery if marketing spend
             resumes normal levels.

             Sources: Q3_Financial_Report.pdf (p.3),
             Q3_Marketing_Analysis.xlsx"
```

**Agent Coordination Benefits:**
- **Parallel execution:** Retrieval + GraphRAG can run simultaneously
- **Specialization:** Each agent optimized for specific reasoning type
- **Graceful degradation:** If GraphRAG unavailable, workflow continues with Retrieval + Analysis
- **LLM flexibility:** AWS Strands allows testing Claude, GPT-4, Gemini without code changes

### AWS Strands Configuration

```python
# strands_orchestrator.py
from strands import Agent, Supervisor, MCPTool

# Define MCP tools from RAGLite Gateway
raglite_tools = [
    MCPTool.from_url("http://localhost:5000/mcp/search_documents"),
    MCPTool.from_url("http://localhost:5000/mcp/navigate_graph"),  # Phase 2
    MCPTool.from_url("http://localhost:5000/mcp/forecast_kpi"),
    # ... all RAGLite MCP tools
]

# Create specialized agents
retrieval_agent = Agent(
    name="Retrieval Agent",
    system_prompt="""You are a Retrieval Agent specialized in finding
                     relevant financial information...""",
    tools=[tool for tool in raglite_tools if "search" in tool.name or "get_document" in tool.name],
    model="anthropic/claude-3-7-sonnet-20250219",  # Primary LLM
)

analysis_agent = Agent(
    name="Analysis Agent",
    system_prompt="""You are a Financial Analysis Agent specialized in
                     interpreting financial data...""",
    tools=[],  # Pure reasoning, no tools
    model="anthropic/claude-3-7-sonnet-20250219",
)

graphrag_agent = Agent(
    name="GraphRAG Agent",
    system_prompt="""You are a GraphRAG Agent specialized in multi-hop
                     relational reasoning...""",
    tools=[tool for tool in raglite_tools if "graph" in tool.name],
    model="anthropic/claude-3-7-sonnet-20250219",
    enabled=False,  # Enable in Phase 2
)

forecast_agent = Agent(
    name="Forecast Agent",
    system_prompt="""You are a Forecast Agent specialized in financial
                     predictions...""",
    tools=[tool for tool in raglite_tools if "forecast" in tool.name],
    model="anthropic/claude-3-7-sonnet-20250219",
)

synthesis_agent = Agent(
    name="Synthesis Agent",
    system_prompt="""You are a Synthesis Agent responsible for combining
                     multi-agent findings...""",
    tools=[],  # Aggregation only
    model="anthropic/claude-3-7-sonnet-20250219",
)

# Create supervisor to orchestrate agents
supervisor = Supervisor(
    agents=[retrieval_agent, analysis_agent, graphrag_agent, forecast_agent, synthesis_agent],
    system_prompt="""You are the Supervisor Agent coordinating a team of
                     specialized financial agents. Decompose user queries into
                     sub-tasks and delegate to appropriate agents. Synthesize
                     their results into comprehensive answers.""",
    model="anthropic/claude-3-7-sonnet-20250219",
)

# Expose as MCP tool for Claude Code to call
@mcp.tool()
async def ask_raglite(query: str) -> str:
    """
    Ask RAGLite a financial question (orchestrated multi-agent response).

    Args:
        query: Natural language financial question

    Returns:
        Comprehensive answer with source attribution
    """
    result = await supervisor.run(query)
    return result.final_output

# Run orchestrator
if __name__ == "__main__":
    # Supervisor runs as part of the overall system
    # MCP clients call ask_raglite() tool which triggers orchestration
    supervisor.start()
```

---

## Data Layer

### Overview

The data layer consists of **3 primary storage systems**, each optimized for specific data types:

```
┌─────────────────────────────────────────────────────────┐
│  Data Layer                                             │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Qdrant (Vector Database)                          │ │
│  │  - Embeddings (1024-dim Fin-E5 vectors)            │ │
│  │  - Chunk metadata (doc_id, page, section)          │ │
│  │  - HNSW indexing for sub-5s retrieval              │ │
│  │  - Collections: financial_documents                 │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Neo4j (Graph Database - Phase 2)                  │ │
│  │  - Knowledge graph (entities, relationships)        │ │
│  │  - Nodes: Company, Department, Metric, KPI, Period │ │
│  │  - Edges: CORRELATES, BELONGS_TO, MEASURED_BY      │ │
│  │  - Community summaries for GraphRAG                │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  S3 / Local Storage (Document Store)               │ │
│  │  - Original PDFs and Excel files                    │ │
│  │  - Extracted chunks (text, tables)                  │ │
│  │  - Ingestion artifacts (metadata, logs)            │ │
│  │  - Versioning for document updates                 │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Qdrant (Vector Database)

**Purpose:** Store and search document embeddings for semantic retrieval

**Schema:**

```python
# Qdrant Collection: financial_documents
{
    "collection_name": "financial_documents",
    "vector_config": {
        "size": 1024,  # Fin-E5 embedding dimension
        "distance": "Cosine"  # Similarity metric
    },
    "optimizers_config": {
        "indexing_threshold": 10000,  # HNSW index after 10K vectors
        "memmap_threshold": 50000
    }
}

# Point (Document Chunk) Schema
{
    "id": "uuid-chunk-identifier",
    "vector": [0.123, -0.456, ...],  # 1024-dim Fin-E5 embedding
    "payload": {
        # Document metadata
        "document_id": "doc-12345",
        "document_name": "Q3_2024_Financial_Report.pdf",
        "document_type": "financial_report",
        "ingestion_date": "2025-10-01T10:30:00Z",

        # Chunk metadata
        "chunk_id": "chunk-001",
        "chunk_text": "Q3 revenue increased 12% YoY to $5.2M...",
        "chunk_context": "This chunk discusses Q3 2024 revenue performance...",  # Contextual Retrieval
        "page_number": 3,
        "section": "Revenue Analysis",

        # Temporal metadata
        "fiscal_period": "Q3_2024",
        "report_date": "2024-09-30",

        # Quality metadata
        "extraction_confidence": 0.98,
        "table_content": true,  # Flag if chunk contains table
        "chart_reference": false
    }
}
```

**Deployment:**

- **Local Dev:** Docker container (`qdrant/qdrant:latest`)
- **Production:** Qdrant Cloud (managed) or self-hosted on EKS

**Performance Configuration:**

```yaml
# docker-compose.yml (local dev)
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"  # gRPC
    volumes:
      - ./qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'
```

**Indexing Strategy:**

```python
# Vector indexing configuration
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, HnswConfigDiff

client = QdrantClient(host="localhost", port=6333)

# Create collection with HNSW indexing
client.create_collection(
    collection_name="financial_documents",
    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE
    ),
    hnsw_config=HnswConfigDiff(
        m=16,  # Number of edges per node
        ef_construct=100,  # Construction-time accuracy
    ),
    optimizers_config={
        "indexing_threshold": 10000,  # Build index after 10K vectors
    }
)
```

**Expected Performance:**
- **Query latency:** <100ms (p50), <500ms (p95)
- **Throughput:** 100+ queries/sec
- **Accuracy:** 90%+ retrieval on financial test set

---

### Neo4j (Graph Database - Phase 2)

**⚠️ IMPLEMENTATION CONDITIONAL ON PHASE 1 RESULTS**

**Purpose:** Store knowledge graph for multi-hop relational queries

**Schema (if implemented):**

```cypher
// Node Types

// Company/Entity nodes
(:Company {
    id: "company-123",
    name: "ACME Corp",
    industry: "Technology"
})

// Department nodes
(:Department {
    id: "dept-456",
    name: "Marketing",
    company_id: "company-123"
})

// Metric/KPI nodes
(:Metric {
    id: "metric-789",
    name: "Revenue",
    type: "financial",
    unit: "USD"
})

// Time Period nodes
(:Period {
    id: "period-q3-2024",
    quarter: "Q3",
    year: 2024,
    start_date: "2024-07-01",
    end_date: "2024-09-30"
})

// Value/Measurement nodes (link metrics to periods)
(:Measurement {
    id: "measurement-001",
    value: 5200000,  // $5.2M
    unit: "USD",
    confidence: 0.95
})

// Community Summary nodes (for GraphRAG)
(:CommunitySummary {
    id: "community-001",
    summary: "Marketing and Revenue entities in Q3 2024 show strong correlation...",
    level: 1,  // Hierarchical level
    member_count: 15
})

// Relationship Types

// Hierarchical relationships
(:Company)-[:HAS_DEPARTMENT]->(:Department)
(:Department)-[:TRACKS_METRIC]->(:Metric)

// Temporal relationships
(:Metric)-[:MEASURED_IN]->(:Period)
(:Measurement)-[:FOR_METRIC]->(:Metric)
(:Measurement)-[:IN_PERIOD]->(:Period)

// Correlations (with strength property)
(:Metric)-[:CORRELATES_WITH {strength: 0.73, p_value: 0.001}]->(:Metric)

// Community relationships (for GraphRAG)
(:Entity)-[:BELONGS_TO_COMMUNITY]->(:CommunitySummary)
(:CommunitySummary)-[:PARENT_COMMUNITY]->(:CommunitySummary)  // Hierarchical

// Causality (if detected)
(:Metric)-[:INFLUENCES {confidence: 0.65, lag_quarters: 1}]->(:Metric)
```

**Example Graph Query:**

```cypher
// Find correlation between Marketing Spend and Revenue across departments
MATCH (m1:Metric {name: "Marketing Spend"})-[:MEASURED_IN]->(p:Period),
      (m1)-[:TRACKED_BY]->(d:Department),
      (m2:Metric {name: "Revenue"})-[:MEASURED_IN]->(p),
      (m2)-[:TRACKED_BY]->(d)
WHERE p.year = 2024
MATCH (m1)-[c:CORRELATES_WITH]->(m2)
RETURN d.name AS department,
       c.strength AS correlation,
       c.p_value AS significance
ORDER BY c.strength DESC
```

**Deployment (if implemented):**

- **Local Dev:** Docker container (`neo4j:5-community`)
- **Production:** Neo4j Aura (managed) or self-hosted on EKS

**Performance Configuration:**

```yaml
# docker-compose.yml (local dev)
services:
  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/raglite-password
      - NEO4J_PLUGINS=["graph-data-science", "apoc"]
      - NEO4J_dbms_memory_heap_max__size=2G
    volumes:
      - ./neo4j_data:/data
```

**Cost (if implemented):**
- Graph construction: $9 one-time for 100 documents
- Ongoing queries: $20/month for 1000 multi-hop queries

---

### S3 / Local Storage (Document Store)

**Purpose:** Store original documents, extracted chunks, and artifacts

**Structure:**

```
raglite-documents/
├── raw/                           # Original uploaded files
│   ├── Q3_2024_Financial_Report.pdf
│   ├── Q3_2024_Marketing_Analysis.xlsx
│   └── ...
├── processed/                     # Extracted and chunked data
│   ├── doc-12345/
│   │   ├── metadata.json          # Document metadata
│   │   ├── chunks/
│   │   │   ├── chunk-001.json     # Chunk text + context
│   │   │   ├── chunk-002.json
│   │   │   └── ...
│   │   ├── tables/
│   │   │   ├── table-001.json     # Extracted tables
│   │   │   └── ...
│   │   └── embeddings/
│   │       └── embeddings.npy     # Numpy array of Fin-E5 vectors
│   └── ...
├── versions/                      # Document version history
│   └── doc-12345/
│       ├── v1_2024-09-01.pdf
│       ├── v2_2024-10-01.pdf      # Updated version
│       └── version_log.json
└── artifacts/                     # Ingestion logs and artifacts
    └── ingestion_jobs/
        ├── job-789-log.json
        └── ...
```

**Metadata Example:**

```json
// processed/doc-12345/metadata.json
{
  "document_id": "doc-12345",
  "original_filename": "Q3_2024_Financial_Report.pdf",
  "document_type": "financial_report",
  "ingestion_job_id": "job-789",
  "ingestion_timestamp": "2025-10-01T10:30:00Z",
  "version": 2,
  "previous_version_id": "doc-12345-v1",

  "extraction_stats": {
    "total_pages": 45,
    "chunks_created": 128,
    "tables_extracted": 23,
    "charts_detected": 8,
    "extraction_time_sec": 142,
    "extraction_confidence": 0.97
  },

  "chunk_ids": ["chunk-001", "chunk-002", ...],

  "fiscal_metadata": {
    "fiscal_period": "Q3_2024",
    "report_date": "2024-09-30",
    "company": "ACME Corp",
    "department": "Finance"
  }
}
```

**Deployment:**

- **Local Dev:** Local filesystem (`./data/documents/`)
- **Production:** AWS S3 with versioning, encryption at rest

**S3 Configuration (Production):**

```python
# Terraform S3 bucket configuration
resource "aws_s3_bucket" "raglite_documents" {
  bucket = "raglite-documents-prod"

  versioning {
    enabled = true  # Document version history (FR28)
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"  # Encryption at rest (NFR12)
      }
    }
  }

  lifecycle_rule {
    id      = "archive-old-versions"
    enabled = true

    noncurrent_version_transition {
      days          = 90
      storage_class = "GLACIER"  # Archive old versions
    }
  }

  tags = {
    Project = "RAGLite"
    Purpose = "Document Storage"
  }
}
```

**Access Patterns:**

```python
# Document storage service
import boto3
from pathlib import Path

class DocumentStore:
    def __init__(self, bucket_name: str):
        self.s3 = boto3.client('s3')
        self.bucket = bucket_name

    def store_document(self, doc_id: str, file_path: Path, metadata: dict):
        """Store original document with metadata."""
        # Upload original file
        key = f"raw/{doc_id}/{file_path.name}"
        self.s3.upload_file(str(file_path), self.bucket, key)

        # Store metadata
        metadata_key = f"processed/{doc_id}/metadata.json"
        self.s3.put_object(
            Bucket=self.bucket,
            Key=metadata_key,
            Body=json.dumps(metadata),
            ContentType="application/json"
        )

    def store_chunks(self, doc_id: str, chunks: List[dict]):
        """Store extracted chunks."""
        for i, chunk in enumerate(chunks):
            chunk_key = f"processed/{doc_id}/chunks/chunk-{i:03d}.json"
            self.s3.put_object(
                Bucket=self.bucket,
                Key=chunk_key,
                Body=json.dumps(chunk),
                ContentType="application/json"
            )

    def get_document(self, doc_id: str, version: Optional[str] = None) -> bytes:
        """Retrieve document (optionally specific version)."""
        if version:
            key = f"versions/{doc_id}/{version}.pdf"
        else:
            key = f"raw/{doc_id}/"  # Get latest

        response = self.s3.get_object(Bucket=self.bucket, Key=key)
        return response['Body'].read()
```

---

## Phased Implementation Strategy

### Overview

RAGLite follows a **phased approach** to minimize risk, validate value incrementally, and avoid over-engineering.

**Key Principle:** **Start simple, add complexity only when proven necessary.**

### Phase 1: Foundation with Contextual Retrieval (Weeks 1-4)

**Goal:** Deliver working Q&A system with 95%+ retrieval accuracy using Contextual Retrieval (no GraphRAG).

**Scope:**

**Microservices to Implement:**
1. ✅ **Ingestion Service (M1)**
   - Docling PDF extraction
   - Excel parsing
   - **Contextual chunking** (LLM-generated context)
   - Fin-E5 embedding generation
   - Qdrant storage

2. ✅ **Retrieval Service (M2)**
   - Vector similarity search
   - Contextual retrieval (with LLM context)
   - Source attribution
   - BM25 hybrid (optional enhancement)

3. ✅ **MCP Gateway**
   - Aggregate M1 + M2 tools
   - Expose unified MCP server

**Orchestration:**
- ✅ **AWS Strands basic setup**
  - Retrieval Agent (calls M2 tools)
  - Analysis Agent (LLM reasoning)
  - Synthesis Agent (combine results)

**Data Layer:**
- ✅ Qdrant (vector database)
- ✅ S3 / Local Storage (documents)
- ❌ Neo4j (NOT implemented in Phase 1)

**Testing:**
- ✅ Ground truth query set (50+ financial questions)
- ✅ Retrieval accuracy validation (target: 90%+)
- ✅ Source attribution validation (target: 95%+)
- ✅ Performance benchmarks (query <5s p50)

**Success Criteria:**
- Retrieval accuracy ≥90% on test set
- Source attribution ≥95%
- Query response <5 sec (p50)
- 10+ real-world queries successfully answered
- User satisfaction 8/10+

**Decision Gate (End of Week 4):**

**IF** Contextual Retrieval achieves ≥95% accuracy on multi-hop relational queries:
- ✅ **SKIP Phase 2 (GraphRAG)** entirely
- 💰 **Save $249/year** (99% cost reduction)
- 🚀 **Proceed directly to Phase 3** (Intelligence Features)

**ELSE IF** Contextual Retrieval <95% on multi-hop queries:
- ⚠️ **Proceed to Phase 2** (implement GraphRAG)
- Justify additional complexity with quantitative gap analysis

**Deliverable:** Working MVP with accurate retrieval, ready for user validation

---

### Phase 2: GraphRAG Integration (Weeks 5-8) - CONDITIONAL

**⚠️ ONLY IMPLEMENT IF PHASE 1 DECISION GATE TRIGGERS**

**Goal:** Add multi-hop relational reasoning capability to close accuracy gap.

**Scope:**

**New Microservice:**
3. ✅ **GraphRAG Service (M3)**
   - Entity extraction (Claude API)
   - Knowledge graph construction (Neo4j)
   - Community detection (Louvain algorithm)
   - Agentic graph navigation
   - Incremental graph updates

**Orchestration Enhancement:**
- ✅ **GraphRAG Agent** (calls M3 tools)
- ✅ **Supervisor coordination** between Retrieval + GraphRAG

**Data Layer Addition:**
- ✅ Neo4j (graph database)

**Testing:**
- ✅ Multi-hop query test set (15+ relational questions)
- ✅ GraphRAG accuracy validation (target: vector+graph ≥95%)
- ✅ Graph construction quality checks
- ✅ Agent navigation success rate (target: 75%+)

**Success Criteria:**
- Multi-hop query accuracy ≥95% (combined vector + graph)
- Graph construction <10 min per 100 pages
- Agent navigation success ≥75%
- System maintains <15 sec query response (p95)

**Cost Validation:**
- Confirm graph construction: ~$9 for 100 docs
- Confirm query cost: ~$20/month for 1000 queries
- Total: ~$249/year (still 10x cheaper than alternatives)

**Deliverable:** Enhanced RAG system with proven multi-hop capability

---

### Phase 3: Intelligence Features (Weeks 9-12)

**Goal:** Add forecasting and proactive insights to demonstrate full RAGLite vision.

**Scope:**

**New Microservices:**
4. ✅ **Forecasting Service (M4)**
   - Time-series extraction
   - Hybrid forecasting (Prophet + LLM)
   - Confidence intervals
   - Forecast updates

5. ✅ **Insights Service (M5)**
   - Anomaly detection
   - Trend analysis
   - Strategic recommendations
   - Insight ranking

**Orchestration Enhancement:**
- ✅ **Forecast Agent** (calls M4 tools)
- ✅ **Insights integration** (proactive insight generation)

**Testing:**
- ✅ Forecast accuracy validation (target: ±8%)
- ✅ Insight quality assessment (target: 75%+ useful)
- ✅ Recommendation alignment (target: 80%+ vs expert)

**Success Criteria:**
- Forecast accuracy ±8% (beats ±15% target)
- 75%+ of insights rated useful/actionable
- 80%+ recommendation alignment with expert analysis
- Intelligence validation in 3+ real scenarios

**Deliverable:** Complete RAGLite intelligence platform (retrieval + analysis + forecasting + insights)

---

### Phase 4: Production Readiness (Weeks 13-16)

**Goal:** Deploy production-ready cloud infrastructure with monitoring and team access.

**Scope:**

**Infrastructure:**
- ✅ AWS deployment (ECS/EKS containerization)
- ✅ Managed Qdrant (or OpenSearch)
- ✅ Managed Neo4j Aura (if Phase 2 implemented)
- ✅ S3 document storage with encryption
- ✅ Secrets Manager for API keys

**Monitoring & Observability:**
- ✅ CloudWatch metrics and alarms
- ✅ Structured logging (JSON)
- ✅ Audit trail for queries (NFR14)
- ✅ Performance dashboards

**Scalability Validation:**
- ✅ Load testing (10+ concurrent users)
- ✅ Auto-scaling configuration
- ✅ Disaster recovery procedures

**Security:**
- ✅ Encryption at rest (NFR12)
- ✅ VPC network isolation
- ✅ IAM roles and policies
- ✅ API rate limiting

**Success Criteria:**
- 99%+ uptime (NFR1 production)
- <5 sec query response under load
- Successful multi-user testing (10+ users)
- Security audit passed
- Backup/restore tested

**Deliverable:** Production-ready system for team rollout

---

### Timeline Summary

| Phase | Duration | Deliverable | Decision Gate |
|-------|----------|-------------|---------------|
| **Phase 1** | Weeks 1-4 | MVP with Contextual Retrieval (M1+M2) | ≥95% accuracy? → Skip Phase 2 |
| **Phase 2** | Weeks 5-8 | GraphRAG integration (M3) | CONDITIONAL |
| **Phase 3** | Weeks 9-12 | Intelligence features (M4+M5) | - |
| **Phase 4** | Weeks 13-16 | Production deployment (AWS) | - |

**Total: 12-16 weeks depending on Phase 2 decision**

**Fastest Path (Phase 2 skipped):** 12 weeks
**Full Implementation:** 16 weeks

---

## Deployment Architecture

### Overview

RAGLite supports **two deployment modes**:
1. **Local Development** (Docker Compose)
2. **Production Cloud** (AWS ECS/EKS)

### Local Development Deployment

**Target:** Developer workstations for local testing and development

**Architecture:**

```
┌──────────────────────────────────────────────────────┐
│  Docker Compose Network: raglite-network            │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  MCP Gateway Container                       │   │
│  │  Port: 5000 → localhost:5000                 │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
│  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐            │
│  │ M1 │  │ M2 │  │ M3 │  │ M4 │  │ M5 │            │
│  │5001│  │5002│  │5003│  │5004│  │5005│            │
│  └────┘  └────┘  └────┘  └────┘  └────┘            │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  Qdrant Container                            │   │
│  │  Port: 6333 → localhost:6333                 │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  Neo4j Container (Phase 2)                   │   │
│  │  Ports: 7474, 7687 → localhost               │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  AWS Strands Orchestrator (Host Process)     │   │
│  │  Calls MCP Gateway at localhost:5000         │   │
│  └──────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
```

**Docker Compose Configuration:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    container_name: raglite-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./data/qdrant:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    networks:
      - raglite-network
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'

  # Graph Database (Phase 2)
  neo4j:
    image: neo4j:5-community
    container_name: raglite-neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - ./data/neo4j:/data
    environment:
      - NEO4J_AUTH=neo4j/raglite-dev-password
      - NEO4J_PLUGINS=["graph-data-science", "apoc"]
      - NEO4J_dbms_memory_heap_max__size=2G
    networks:
      - raglite-network
    profiles:
      - phase2  # Only start if Phase 2 implemented

  # Microservice M1: Ingestion
  ingestion-service:
    build:
      context: ./services/ingestion
      dockerfile: Dockerfile
    container_name: raglite-ingestion
    ports:
      - "5001:5001"
    volumes:
      - ./data/documents:/app/documents
      - ./data/uploads:/app/uploads
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - FIN_E5_MODEL_PATH=/app/models/fin-e5
    env_file:
      - .env
    networks:
      - raglite-network
    depends_on:
      - qdrant

  # Microservice M2: Retrieval
  retrieval-service:
    build:
      context: ./services/retrieval
      dockerfile: Dockerfile
    container_name: raglite-retrieval
    ports:
      - "5002:5002"
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    env_file:
      - .env
    networks:
      - raglite-network
    depends_on:
      - qdrant

  # Microservice M3: GraphRAG (Phase 2)
  graphrag-service:
    build:
      context: ./services/graphrag
      dockerfile: Dockerfile
    container_name: raglite-graphrag
    ports:
      - "5003:5003"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=raglite-dev-password
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    env_file:
      - .env
    networks:
      - raglite-network
    depends_on:
      - neo4j
    profiles:
      - phase2

  # Microservice M4: Forecasting
  forecast-service:
    build:
      context: ./services/forecasting
      dockerfile: Dockerfile
    container_name: raglite-forecast
    ports:
      - "5004:5004"
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    env_file:
      - .env
    networks:
      - raglite-network
    depends_on:
      - qdrant

  # Microservice M5: Insights
  insights-service:
    build:
      context: ./services/insights
      dockerfile: Dockerfile
    container_name: raglite-insights
    ports:
      - "5005:5005"
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    env_file:
      - .env
    networks:
      - raglite-network
    depends_on:
      - qdrant

  # MCP Gateway
  mcp-gateway:
    build:
      context: ./services/gateway
      dockerfile: Dockerfile
    container_name: raglite-gateway
    ports:
      - "5000:5000"
    environment:
      - INGESTION_URL=http://ingestion-service:5001
      - RETRIEVAL_URL=http://retrieval-service:5002
      - GRAPHRAG_URL=http://graphrag-service:5003
      - FORECAST_URL=http://forecast-service:5004
      - INSIGHTS_URL=http://insights-service:5005
    networks:
      - raglite-network
    depends_on:
      - ingestion-service
      - retrieval-service
      - forecast-service
      - insights-service

networks:
  raglite-network:
    driver: bridge

volumes:
  qdrant-data:
  neo4j-data:
```

**Development Commands:**

```bash
# Start all services (Phase 1)
docker-compose up -d

# Start with GraphRAG (Phase 2)
docker-compose --profile phase2 up -d

# View logs
docker-compose logs -f

# Restart specific service
docker-compose restart ingestion-service

# Stop all services
docker-compose down

# Reset all data (WARNING: deletes volumes)
docker-compose down -v
```

**Environment Variables (.env):**

```bash
# .env (local development)
CLAUDE_API_KEY=sk-ant-api03-...
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=raglite-dev-password
AWS_STRANDS_MODEL=anthropic/claude-3-7-sonnet-20250219
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

---

### Production Cloud Deployment (AWS)

**Target:** Production environment with scalability, high availability, monitoring

**Architecture:**

```
┌───────────────────────────────────────────────────────────────┐
│  AWS Cloud (VPC: raglite-vpc)                                │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Application Load Balancer (ALB)                        │ │
│  │  Exposes: MCP Gateway endpoint (HTTPS)                  │ │
│  └──────────────────┬──────────────────────────────────────┘ │
│                     │                                          │
│  ┌──────────────────▼──────────────────────────────────────┐ │
│  │  ECS/EKS Cluster (Auto-scaling)                         │ │
│  │                                                           │ │
│  │  ┌──────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │ │
│  │  │ Gateway  │  │  M1-M5 │  │  M1-M5 │  │ Strands│      │ │
│  │  │ Service  │  │ Services│  │Services│  │Orchestr│      │ │
│  │  │ (2 tasks)│  │(1 task  │  │(replica │  │ator    │      │ │
│  │  │          │  │ each)   │  │ if load)│  │(2 tasks│      │ │
│  │  └──────────┘  └────────┘  └────────┘  └────────┘      │ │
│  └──────────────────┬──────────────────────────────────────┘ │
│                     │                                          │
│  ┌──────────────────▼──────────────────────────────────────┐ │
│  │  Data Layer (Managed Services)                          │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────┐    │ │
│  │  │  Qdrant Cloud / OpenSearch Service              │    │ │
│  │  │  - Multi-AZ deployment                           │    │ │
│  │  │  - Automated backups                             │    │ │
│  │  └─────────────────────────────────────────────────┘    │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────┐    │ │
│  │  │  Neo4j Aura (if Phase 2)                         │    │ │
│  │  │  - Managed graph database                        │    │ │
│  │  │  - Automated backups                             │    │ │
│  │  └─────────────────────────────────────────────────┘    │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────┐    │ │
│  │  │  S3 Bucket (raglite-documents-prod)              │    │ │
│  │  │  - Versioning enabled                            │    │ │
│  │  │  - Encryption at rest (AES256)                   │    │ │
│  │  │  - Lifecycle policies (archive to Glacier)       │    │ │
│  │  └─────────────────────────────────────────────────┘    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Monitoring & Logging                                    │ │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────────┐   │ │
│  │  │ CloudWatch │  │ Prometheus │  │ CloudWatch Logs │   │ │
│  │  │  Metrics   │  │  (Custom)  │  │  (Structured)   │   │ │
│  │  └────────────┘  └────────────┘  └─────────────────┘   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Security & Secrets                                       │ │
│  │  ┌──────────────────┐  ┌────────────────────────────┐   │ │
│  │  │ Secrets Manager  │  │ IAM Roles & Policies       │   │ │
│  │  │ (API Keys)       │  │ (Least Privilege)          │   │ │
│  │  └──────────────────┘  └────────────────────────────┘   │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

**Terraform Infrastructure:**

```hcl
# terraform/main.tf (excerpt)

# VPC Configuration
resource "aws_vpc" "raglite_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name    = "raglite-vpc"
    Project = "RAGLite"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "raglite_cluster" {
  name = "raglite-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Project = "RAGLite"
  }
}

# ECS Task Definition (MCP Gateway)
resource "aws_ecs_task_definition" "gateway" {
  family                   = "raglite-gateway"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"

  container_definitions = jsonencode([
    {
      name      = "gateway"
      image     = "${aws_ecr_repository.raglite.repository_url}:gateway-latest"
      essential = true
      portMappings = [
        {
          containerPort = 5000
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "ENVIRONMENT"
          value = "production"
        },
        {
          name  = "INGESTION_URL"
          value = "http://ingestion-service.local:5001"
        }
      ]
      secrets = [
        {
          name      = "CLAUDE_API_KEY"
          valueFrom = aws_secretsmanager_secret.claude_api_key.arn
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/raglite/gateway"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  task_role_arn      = aws_iam_role.ecs_task_role.arn
  execution_role_arn = aws_iam_role.ecs_execution_role.arn
}

# ECS Service with Auto-scaling
resource "aws_ecs_service" "gateway" {
  name            = "raglite-gateway"
  cluster         = aws_ecs_cluster.raglite_cluster.id
  task_definition = aws_ecs_task_definition.gateway.arn
  desired_count   = 2  # High availability

  launch_type = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.gateway.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.gateway.arn
    container_name   = "gateway"
    container_port   = 5000
  }

  depends_on = [aws_lb_listener.gateway]
}

# Auto-scaling Policy
resource "aws_appautoscaling_target" "gateway" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.raglite_cluster.name}/${aws_ecs_service.gateway.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "gateway_cpu" {
  name               = "gateway-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.gateway.resource_id
  scalable_dimension = aws_appautoscaling_target.gateway.scalable_dimension
  service_namespace  = aws_appautoscaling_target.gateway.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# S3 Bucket (Document Storage)
resource "aws_s3_bucket" "documents" {
  bucket = "raglite-documents-prod"

  tags = {
    Project = "RAGLite"
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Secrets Manager (API Keys)
resource "aws_secretsmanager_secret" "claude_api_key" {
  name        = "raglite/claude-api-key"
  description = "Claude API key for RAGLite services"
}

# IAM Role (ECS Task Execution)
resource "aws_iam_role" "ecs_execution_role" {
  name = "raglite-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role (ECS Task - Service Runtime)
resource "aws_iam_role" "ecs_task_role" {
  name = "raglite-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy (S3 Access for Services)
resource "aws_iam_role_policy" "task_s3_access" {
  name = "raglite-s3-access"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      }
    ]
  })
}

# IAM Policy (Secrets Manager Access)
resource "aws_iam_role_policy" "task_secrets_access" {
  name = "raglite-secrets-access"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.claude_api_key.arn
        ]
      }
    ]
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "gateway" {
  name              = "/ecs/raglite/gateway"
  retention_in_days = 30
}

# Application Load Balancer
resource "aws_lb" "raglite_alb" {
  name               = "raglite-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = true

  tags = {
    Project = "RAGLite"
  }
}

resource "aws_lb_target_group" "gateway" {
  name        = "raglite-gateway-tg"
  port        = 5000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.raglite_vpc.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "gateway" {
  load_balancer_arn = aws_lb.raglite_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = aws_acm_certificate.raglite.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.gateway.arn
  }
}
```

**Deployment Commands:**

```bash
# Build and push Docker images
./scripts/build-and-push.sh

# Deploy infrastructure
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# Deploy service updates (CI/CD)
aws ecs update-service \
  --cluster raglite-cluster \
  --service raglite-gateway \
  --force-new-deployment
```

**Cost Estimation (Production - Month 1):**

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| **ECS Fargate** | 6 services × 2 tasks × 0.5 vCPU × 1GB | ~$100 |
| **ALB** | 1 load balancer | ~$20 |
| **Qdrant Cloud** | 4GB RAM, 2 vCPU | ~$50-100 |
| **Neo4j Aura** (Phase 2) | Starter tier | ~$65 |
| **S3 Storage** | 100GB + requests | ~$5 |
| **CloudWatch** | Logs + metrics | ~$10 |
| **Secrets Manager** | 5 secrets | ~$2 |
| **Data Transfer** | Moderate usage | ~$10 |
| **Total (Phase 1)** | Without GraphRAG | **~$200/month** |
| **Total (Phase 2)** | With GraphRAG | **~$270/month** |

---

## Security & Compliance

### Security Architecture

RAGLite implements **defense-in-depth** security to protect sensitive financial data.

### Security Layers

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Network Security                             │
│  ├─ VPC isolation (AWS)                                │
│  ├─ Private subnets for services                       │
│  ├─ Security groups (least privilege)                  │
│  └─ HTTPS/TLS encryption in transit                    │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Layer 2: Application Security                         │
│  ├─ API rate limiting (prevent abuse)                  │
│  ├─ Input validation (prevent injection)               │
│  ├─ Output sanitization (prevent XSS)                  │
│  └─ MCP protocol security (tool authorization)         │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Layer 3: Authentication & Authorization               │
│  ├─ IAM roles (AWS services)                           │
│  ├─ MCP client authentication (API keys)               │
│  ├─ Service-to-service auth (internal)                 │
│  └─ Principle of least privilege                       │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Layer 4: Data Security                                │
│  ├─ Encryption at rest (S3 AES256, NFR12)             │
│  ├─ Encryption in transit (TLS 1.2+)                   │
│  ├─ Secrets management (AWS Secrets Manager)           │
│  └─ Data sanitization (PII detection)                  │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Layer 5: Audit & Monitoring                           │
│  ├─ Query audit trail (NFR14)                          │
│  ├─ Access logs (CloudWatch)                           │
│  ├─ Anomaly detection (suspicious queries)             │
│  └─ Security alerts (CloudWatch Alarms)                │
└─────────────────────────────────────────────────────────┘
```

### Security Requirements (from PRD)

**NFR12: Encryption at Rest**
- ✅ S3 bucket server-side encryption (AES256)
- ✅ Qdrant data encryption (if supported by managed service)
- ✅ Neo4j encryption (Aura managed encryption)

**NFR13: Encryption in Transit**
- ✅ HTTPS/TLS 1.2+ for all external communications
- ✅ Service-to-service encrypted connections within VPC
- ✅ MCP protocol over HTTPS (Streamable HTTP transport)

**NFR14: Audit Logging**
- ✅ Query audit trail (who asked what, when)
- ✅ Document access logs (who accessed which documents)
- ✅ Admin action logs (ingestion, configuration changes)
- ✅ Structured JSON logging for queryability

**NFR15: Secrets Management**
- ✅ AWS Secrets Manager for API keys (production)
- ✅ Environment variables with .env (local dev only)
- ✅ Automated secret rotation (90-day policy)
- ✅ No secrets in code or version control

### Threat Modeling

**Threat: Unauthorized Access to Financial Data**
- **Mitigation:**
  - IAM roles with least privilege
  - VPC network isolation
  - MCP client API key authentication
  - Query audit trail for detection

**Threat: Data Exfiltration**
- **Mitigation:**
  - Encryption at rest and in transit
  - Rate limiting on queries
  - Anomaly detection for unusual query patterns
  - CloudWatch alarms for excessive data access

**Threat: Injection Attacks (Prompt Injection, SQL Injection)**
- **Mitigation:**
  - Input validation and sanitization
  - Parameterized queries (Qdrant, Neo4j)
  - LLM output filtering
  - Cypher query sanitization (Neo4j)

**Threat: API Key Compromise**
- **Mitigation:**
  - Secrets Manager with rotation
  - API rate limiting
  - Key scoping (per-client keys)
  - Immediate revocation capability

**Threat: Denial of Service (DoS)**
- **Mitigation:**
  - ALB rate limiting
  - WAF rules (if needed)
  - Auto-scaling (handle legitimate load spikes)
  - Circuit breakers for service protection

### Compliance Considerations

**Data Residency:**
- All data stored in single AWS region (configurable)
- Document retention policies (S3 lifecycle rules)
- GDPR/CCPA deletion capabilities (if required)

**Access Controls:**
- Role-based access (future: multi-user support)
- Audit trail for compliance reporting
- Data lineage tracking (document → chunks → responses)

---

## Performance & Scalability

### Performance Targets (from PRD)

| Metric | Target (NFR) | Architecture Strategy |
|--------|--------------|----------------------|
| **Retrieval Accuracy** | 90%+ (NFR6) | Contextual Retrieval (98.1%) or GraphRAG |
| **Source Attribution** | 95%+ (NFR7) | Metadata tracking, citation system |
| **Table Extraction** | 95%+ (NFR8) | Docling (97.9% accuracy) |
| **Query Response (p50)** | <5 sec (NFR13) | HNSW indexing, caching, async |
| **Query Response (p95)** | <15 sec (NFR13) | Load balancing, auto-scaling |
| **Complex Workflow** | <30 sec (NFR13) | Multi-agent parallelization |
| **Forecast Accuracy** | ±15% (NFR10) | Hybrid approach (±8% achieved) |
| **Uptime (Production)** | 99%+ (NFR1) | Multi-AZ, health checks, auto-recovery |
| **Concurrent Users** | 10+ (NFR3) | Horizontal scaling, connection pooling |

### Scalability Architecture

**Horizontal Scaling:**

```
Single User:
┌────────┐
│Gateway │ → 5 Microservices (1 task each)
└────────┘

10 Users:
┌────────┐ ┌────────┐
│Gateway │ │Gateway │ → 5 Microservices (2 tasks each)
└────────┘ └────────┘

50 Users (Auto-scaled):
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Gateway │ │Gateway │ │Gateway │ │Gateway │
└────────┘ └────────┘ └────────┘ └────────┘
    │
    └─> 5 Microservices (5-10 tasks each)
    └─> Qdrant Cloud (scaled instance)
```

**Performance Optimizations:**

1. **Vector Search Optimization:**
   - HNSW indexing (sub-100ms queries)
   - Embedding caching for repeated queries
   - Qdrant gRPC for lower latency

2. **Multi-Agent Parallelization:**
   - Retrieval + GraphRAG agents run concurrently
   - AWS Strands async task execution
   - Reduces complex workflow time by 40-60%

3. **Caching Strategy:**
   - LRU cache for frequently asked queries
   - Embedding cache (avoid re-embedding same text)
   - TTL: 1 hour for query results

4. **Connection Pooling:**
   - Qdrant client connection pool (20 connections)
   - Neo4j driver connection pool (10 connections)
   - Reduces connection overhead by 70%

### Load Testing Strategy

**Test Scenarios:**

1. **Baseline Performance:**
   - 1 concurrent user
   - 10 queries (varied complexity)
   - Measure: p50, p95, p99 latency

2. **Concurrent User Load:**
   - Ramp up: 1 → 10 → 25 → 50 users
   - Sustained load: 5 minutes per level
   - Measure: Response time degradation, error rate

3. **Stress Test:**
   - 100 concurrent users
   - Find breaking point
   - Validate graceful degradation

4. **Spike Test:**
   - Sudden spike: 5 → 50 users in 10 seconds
   - Measure: Auto-scaling response time
   - Validate: No dropped requests

**Load Testing Tools:**
- Locust (Python-based load testing)
- k6 (performance testing)
- CloudWatch Metrics (production monitoring)

---

## Monitoring & Observability

### Observability Stack

```
┌─────────────────────────────────────────────────────────┐
│  Metrics Layer (CloudWatch + Prometheus)               │
│  ├─ Service health (up/down, errors)                   │
│  ├─ Query latency (p50, p95, p99)                      │
│  ├─ Retrieval accuracy (ongoing validation)            │
│  ├─ Resource utilization (CPU, memory, disk)           │
│  └─ Cost tracking (LLM API usage)                      │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Logging Layer (CloudWatch Logs)                       │
│  ├─ Structured JSON logs (queryable)                   │
│  ├─ Query audit trail (NFR14)                          │
│  ├─ Error logs with stack traces                       │
│  ├─ Performance logs (slow queries)                    │
│  └─ Security logs (auth failures, anomalies)           │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Alerting Layer (CloudWatch Alarms + SNS)              │
│  ├─ Service down alerts (critical)                     │
│  ├─ High error rate alerts (warning)                   │
│  ├─ Slow query alerts (p95 > 15s)                      │
│  ├─ Cost anomaly alerts (LLM overuse)                  │
│  └─ Security alerts (auth failures, injection)         │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Dashboards (CloudWatch Dashboards)                    │
│  ├─ Service health overview                            │
│  ├─ Query performance trends                           │
│  ├─ Accuracy metrics (retrieval, attribution)          │
│  ├─ Cost breakdown (LLM usage, infrastructure)         │
│  └─ User activity (queries/day, users)                 │
└─────────────────────────────────────────────────────────┘
```

### Key Metrics to Monitor

**Service Health Metrics:**
```python
# Prometheus metrics (example)
raglite_service_up{service="gateway"} = 1  # 1 = up, 0 = down
raglite_service_errors_total{service="retrieval", error_type="timeout"} = 3
raglite_service_requests_total{service="ingestion", status="success"} = 127
```

**Query Performance Metrics:**
```python
raglite_query_duration_seconds{quantile="0.5"} = 2.3  # p50
raglite_query_duration_seconds{quantile="0.95"} = 8.7  # p95
raglite_query_duration_seconds{quantile="0.99"} = 14.2  # p99
raglite_retrieval_accuracy = 0.94  # 94%
raglite_source_attribution_accuracy = 0.97  # 97%
```

**Cost Metrics:**
```python
raglite_llm_tokens_total{model="claude-3-7-sonnet", type="input"} = 125000
raglite_llm_tokens_total{model="claude-3-7-sonnet", type="output"} = 18000
raglite_llm_cost_usd{model="claude-3-7-sonnet"} = 12.50
```

**Resource Utilization:**
```python
raglite_cpu_usage_percent{service="retrieval"} = 45
raglite_memory_usage_bytes{service="ingestion"} = 1073741824  # 1GB
raglite_qdrant_collection_size_vectors = 125000
```

### Structured Logging Format

```python
# Structured JSON log example
{
  "timestamp": "2025-10-03T14:32:15.123Z",
  "level": "INFO",
  "service": "retrieval",
  "event": "query_executed",
  "query_id": "qry-abc123",
  "user_id": "user-456",
  "query": "What drove Q3 revenue variance?",
  "duration_ms": 2340,
  "results_count": 10,
  "accuracy_score": 0.96,
  "sources": ["doc-12345", "doc-12346"],
  "trace_id": "trace-xyz789"
}
```

### CloudWatch Alarms

**Critical Alarms (PagerDuty/SMS):**
```hcl
# terraform/alarms.tf
resource "aws_cloudwatch_metric_alarm" "service_down" {
  alarm_name          = "raglite-gateway-down"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Average"
  threshold           = "1"
  alarm_description   = "Gateway service has no healthy hosts"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "raglite-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "High 5XX error rate detected"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]
}
```

**Warning Alarms (Email):**
```hcl
resource "aws_cloudwatch_metric_alarm" "slow_queries" {
  alarm_name          = "raglite-slow-queries"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "query_duration_p95"
  namespace           = "RAGLite"
  period              = "300"
  statistic           = "Average"
  threshold           = "15000"  # 15 seconds
  alarm_description   = "p95 query latency exceeds 15s"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "cost_anomaly" {
  alarm_name          = "raglite-llm-cost-spike"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "llm_cost_usd_daily"
  namespace           = "RAGLite"
  period              = "86400"  # 1 day
  statistic           = "Sum"
  threshold           = "50"  # $50/day
  alarm_description   = "LLM costs exceed $50/day"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
}
```

---

## Development Workflow

### Repository Structure

```
raglite/
├── README.md
├── docker-compose.yml              # Local dev environment
├── .env.example                    # Environment template
├── .gitignore
├── pyproject.toml                  # Python dependencies (Poetry)
├── poetry.lock
│
├── services/                       # Microservices
│   ├── ingestion/
│   │   ├── Dockerfile
│   │   ├── main.py                # MCP server entrypoint
│   │   ├── ingestion_pipeline.py
│   │   ├── chunking.py
│   │   ├── embedding.py
│   │   └── tests/
│   ├── retrieval/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── search.py
│   │   ├── reranking.py
│   │   └── tests/
│   ├── graphrag/                  # Phase 2
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── graph_builder.py
│   │   ├── agent_navigator.py
│   │   └── tests/
│   ├── forecasting/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── hybrid_forecaster.py
│   │   └── tests/
│   ├── insights/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── anomaly_detector.py
│   │   └── tests/
│   └── gateway/
│       ├── Dockerfile
│       ├── main.py
│       ├── router.py
│       └── tests/
│
├── orchestrator/                   # AWS Strands orchestration
│   ├── main.py
│   ├── agents/
│   │   ├── retrieval_agent.py
│   │   ├── analysis_agent.py
│   │   ├── graphrag_agent.py
│   │   ├── forecast_agent.py
│   │   └── synthesis_agent.py
│   └── tests/
│
├── shared/                         # Shared utilities
│   ├── __init__.py
│   ├── models.py                  # Pydantic data models
│   ├── config.py                  # Configuration management
│   ├── logging.py                 # Structured logging
│   └── monitoring.py              # Metrics helpers
│
├── tests/                          # Integration tests
│   ├── integration/
│   │   ├── test_end_to_end.py
│   │   ├── test_accuracy.py
│   │   └── fixtures/
│   └── load/
│       └── locustfile.py          # Load testing
│
├── terraform/                      # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── modules/
│   │   ├── ecs/
│   │   ├── networking/
│   │   └── monitoring/
│   └── environments/
│       ├── dev/
│       └── prod/
│
├── scripts/
│   ├── setup-local-dev.sh         # Local setup automation
│   ├── build-and-push.sh          # Docker build + ECR push
│   ├── run-accuracy-tests.sh      # Ground truth validation
│   └── deploy-prod.sh             # Production deployment
│
└── docs/
    ├── architecture.md            # This document
    ├── prd.md                     # Product requirements
    ├── api.md                     # MCP API documentation
    └── runbooks/
        ├── incident-response.md
        └── troubleshooting.md
```

### Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/yourorg/raglite.git
cd raglite

# 2. Install dependencies (Poetry)
poetry install

# 3. Copy environment template
cp .env.example .env
# Edit .env and add CLAUDE_API_KEY=...

# 4. Start local services (Docker Compose)
docker-compose up -d

# 5. Run database migrations (if needed)
poetry run python scripts/init-qdrant.py

# 6. Run tests
poetry run pytest

# 7. Start orchestrator (local Python process)
poetry run python orchestrator/main.py

# MCP Gateway now available at: http://localhost:5000/mcp
```

### Development Commands

```bash
# Run specific service locally
cd services/retrieval
poetry run python main.py

# Run unit tests
poetry run pytest services/retrieval/tests/

# Run integration tests
poetry run pytest tests/integration/

# Run accuracy validation
poetry run python scripts/run-accuracy-tests.sh

# Run load tests
cd tests/load
poetry run locust -f locustfile.py --host=http://localhost:5000

# Format code
poetry run black .
poetry run isort .

# Lint code
poetry run ruff check .
poetry run mypy services/
```

### CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: RAGLite CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: poetry install

      - name: Run linters
        run: |
          poetry run black --check .
          poetry run ruff check .
          poetry run mypy services/

      - name: Run unit tests
        run: poetry run pytest --cov=services --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build and push Docker images
        run: ./scripts/build-and-push.sh

  deploy:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster raglite-cluster \
            --service raglite-gateway \
            --force-new-deployment

  accuracy-validation:
    runs-on: ubuntu-latest
    needs: deploy
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Run accuracy tests
        run: ./scripts/run-accuracy-tests.sh
        env:
          RAGLITE_URL: ${{ secrets.PROD_RAGLITE_URL }}
          CLAUDE_API_KEY: ${{ secrets.CLAUDE_API_KEY }}

      - name: Validate accuracy thresholds
        run: |
          # Fail deployment if accuracy < 90%
          python scripts/validate-accuracy.py --threshold 0.90
```

---

## Testing Strategy

### Testing Pyramid

```
                  ┌───────────────┐
                  │  E2E Tests    │  ← 5% (Accuracy validation)
                  │  (Accuracy)   │
                  └───────────────┘
               ┌────────────────────┐
               │ Integration Tests  │  ← 15% (Service integration)
               │  (Microservices)   │
               └────────────────────┘
         ┌──────────────────────────────┐
         │      Unit Tests              │  ← 80% (Code coverage)
         │   (Functions, Classes)       │
         └──────────────────────────────┘
```

### Unit Tests (80%+ Coverage Target)

**Scope:**
- Individual functions and classes
- Mocked external dependencies (Qdrant, Neo4j, Claude API)
- Fast execution (<5 min for full suite)

**Example:**

```python
# services/retrieval/tests/test_search.py
import pytest
from unittest.mock import Mock, patch
from services.retrieval.search import SemanticSearch

@pytest.fixture
def mock_qdrant_client():
    client = Mock()
    client.search.return_value = [
        Mock(id="chunk-1", score=0.95, payload={"text": "Q3 revenue..."}),
        Mock(id="chunk-2", score=0.87, payload={"text": "Marketing spend..."}),
    ]
    return client

def test_semantic_search_returns_top_k(mock_qdrant_client):
    searcher = SemanticSearch(qdrant_client=mock_qdrant_client)
    results = searcher.search(query="Q3 revenue", top_k=2)

    assert len(results) == 2
    assert results[0].score == 0.95
    assert "Q3 revenue" in results[0].text
    mock_qdrant_client.search.assert_called_once()

def test_semantic_search_with_filters(mock_qdrant_client):
    searcher = SemanticSearch(qdrant_client=mock_qdrant_client)
    filters = {"document_type": "financial_report", "fiscal_period": "Q3_2024"}
    results = searcher.search(query="revenue", top_k=5, filters=filters)

    # Verify filters passed to Qdrant
    call_args = mock_qdrant_client.search.call_args
    assert call_args.kwargs['filter'] == filters

@patch('services.retrieval.embedding.FinE5Embedder.embed')
def test_search_embedding_generation(mock_embed, mock_qdrant_client):
    mock_embed.return_value = [0.1, 0.2, 0.3]  # Mock embedding
    searcher = SemanticSearch(qdrant_client=mock_qdrant_client)
    searcher.search(query="test query", top_k=10)

    mock_embed.assert_called_once_with("test query")
```

**Coverage Goal:**
- 80%+ line coverage
- 90%+ branch coverage for critical paths (ingestion, retrieval)
- Run on every commit via CI/CD

### Integration Tests (Service-to-Service)

**Scope:**
- Multi-service interactions
- Real database connections (Docker test containers)
- End-to-end workflows without mocks

**Example:**

```python
# tests/integration/test_ingestion_to_retrieval.py
import pytest
from testcontainers.core.container import DockerContainer
from services.ingestion.main import ingest_document
from services.retrieval.main import search_documents

@pytest.fixture(scope="module")
def qdrant_container():
    """Spin up real Qdrant container for testing."""
    container = DockerContainer("qdrant/qdrant:latest")
    container.with_exposed_ports(6333)
    container.start()
    yield container
    container.stop()

@pytest.mark.integration
async def test_ingest_then_retrieve(qdrant_container):
    """Test full pipeline: ingest PDF → retrieve via search."""

    # 1. Ingest test document
    job_id = await ingest_document(
        file_path="tests/fixtures/Q3_2024_Report.pdf",
        document_type="financial_report"
    )

    # Wait for ingestion to complete
    status = await wait_for_job(job_id, timeout=60)
    assert status.state == "completed"
    assert status.chunks_processed > 0

    # 2. Search for content from ingested document
    results = await search_documents(
        query="Q3 revenue growth",
        top_k=5
    )

    # 3. Validate retrieval
    assert len(results) > 0
    assert results[0].relevance_score > 0.8
    assert "Q3" in results[0].text
    assert results[0].source_document == "Q3_2024_Report.pdf"
```

**Test Scenarios:**
- Ingestion → Retrieval pipeline
- Retrieval → Forecast pipeline (time-series data)
- GraphRAG construction → Navigation (Phase 2)
- Multi-agent orchestration (Retrieval + Analysis + Synthesis)

### Accuracy Validation Tests (Ground Truth)

**Scope:**
- Validate 90%+ retrieval accuracy (NFR6)
- Validate 95%+ source attribution (NFR7)
- Real-world financial questions with known correct answers

**Test Set:**

```python
# tests/integration/ground_truth.py
GROUND_TRUTH_QUERIES = [
    {
        "query": "What was Q3 2024 revenue?",
        "expected_answer": "$5.2M",
        "expected_sources": ["Q3_2024_Financial_Report.pdf:3"],
        "category": "factual_retrieval"
    },
    {
        "query": "What drove Q3 revenue variance?",
        "expected_answer_contains": ["marketing spend", "30% reduction", "12% decline"],
        "expected_sources": ["Q3_2024_Financial_Report.pdf:3", "Q3_Marketing_Analysis.xlsx"],
        "category": "analytical_query"
    },
    {
        "query": "How does marketing correlate with revenue across departments?",
        "expected_answer_contains": ["Department A: 0.73", "Department B: 0.45"],
        "expected_sources": ["Multiple documents"],
        "category": "multi_hop_relational",
        "requires_graphrag": True  # Only test if Phase 2 implemented
    },
    # ... 50+ total queries
]

@pytest.mark.accuracy
async def test_retrieval_accuracy():
    """Validate retrieval accuracy on ground truth set."""
    correct = 0
    total = 0

    for test_case in GROUND_TRUTH_QUERIES:
        if test_case.get("requires_graphrag") and not GRAPHRAG_ENABLED:
            continue  # Skip GraphRAG tests in Phase 1

        results = await search_documents(query=test_case["query"], top_k=10)

        # Check if correct answer found in top results
        is_correct = validate_answer(results, test_case)
        if is_correct:
            correct += 1
        total += 1

    accuracy = correct / total
    print(f"Retrieval Accuracy: {accuracy:.2%}")
    assert accuracy >= 0.90, f"Accuracy {accuracy:.2%} below 90% threshold"

@pytest.mark.accuracy
async def test_source_attribution_accuracy():
    """Validate source attribution accuracy."""
    correct_attributions = 0
    total = 0

    for test_case in GROUND_TRUTH_QUERIES:
        results = await search_documents(query=test_case["query"], top_k=5)

        # Check if sources match expected
        for expected_source in test_case["expected_sources"]:
            if any(expected_source in r.source for r in results):
                correct_attributions += 1
        total += len(test_case["expected_sources"])

    attribution_accuracy = correct_attributions / total
    print(f"Source Attribution Accuracy: {attribution_accuracy:.2%}")
    assert attribution_accuracy >= 0.95, f"Attribution {attribution_accuracy:.2%} below 95%"
```

**Accuracy Testing Schedule:**
- **Pre-commit:** Fast subset (10 queries)
- **CI/CD:** Full suite (50+ queries) on main branch
- **Weekly:** Automated accuracy regression tests
- **Post-deployment:** Production validation (subset)

### Load Testing

**Tool:** Locust (Python-based)

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class RAGLiteUser(HttpUser):
    wait_time = between(1, 3)  # 1-3 seconds between requests

    @task(3)  # Weight: 3x more common
    def search_documents(self):
        """Simulate typical search query."""
        self.client.post("/mcp/search_documents", json={
            "query": "What was Q3 revenue?",
            "top_k": 10
        })

    @task(1)
    def forecast_kpi(self):
        """Simulate forecast request."""
        self.client.post("/mcp/forecast_kpi", json={
            "metric": "Revenue",
            "horizon": 4
        })

    @task(1)
    def generate_insights(self):
        """Simulate insights generation."""
        self.client.post("/mcp/generate_insights", json={
            "scope": "all",
            "priority_threshold": "medium"
        })

# Run: locust -f locustfile.py --host=http://localhost:5000 --users 10 --spawn-rate 2
```

**Load Test Goals:**
- Validate <5 sec p50 response under 10 concurrent users
- Validate <15 sec p95 response under 25 concurrent users
- Identify breaking point (max concurrent users before degradation)
- Validate auto-scaling triggers correctly

---

## CI/CD Pipeline Architecture

### Overview

RAGLite implements a **production-grade CI/CD pipeline** following 2025 best practices for Python microservices, AI/ML systems, and AWS ECS deployments. The pipeline enforces quality gates, security scanning, accuracy regression testing, and zero-downtime deployments.

**⚠️ Pragmatic Implementation Note:**

The CI/CD workflow described below represents the **complete, mature state** of the pipeline. **Start simple and add complexity incrementally:**

**Phase 1 (MVP - Week 1):**
- Basic linting (Black, Ruff)
- Unit tests with coverage
- Manual deployment to dev

**Phase 2 (Weeks 2-3):**
- Add integration tests
- Automated dev deployment
- Docker builds

**Phase 3 (Weeks 4-6):**
- Security scanning (Bandit, Trivy)
- Accuracy regression tests
- Staging environment

**Phase 4 (Production-Ready):**
- Full 5-stage pipeline
- Canary deployments
- Auto-rollback
- Cost tracking

**Anti-pattern:** Implementing all stages upfront delays first deployment and adds maintenance burden before product-market fit.

### CI/CD Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Developer Push/PR                                               │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 1: Code Quality & Security (Parallel)                    │
│  ├─ Linting (Black, Ruff, isort)                                │
│  ├─ Type Checking (mypy)                                        │
│  ├─ Security Scan (Bandit SAST)                                 │
│  ├─ Secret Detection (truffleHog)                               │
│  └─ Dependency Scan (Safety, pip-audit)                         │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 2: Multi-Layer Testing (Parallel Matrix)                 │
│  ├─ Unit Tests (pytest, 80%+ coverage)                          │
│  ├─ Integration Tests (Testcontainers)                          │
│  ├─ Accuracy Regression Tests (Ground truth validation)         │
│  ├─ RAG Pipeline Tests (Retrieval + generation)                 │
│  └─ LLM Cost Tracking (OpenAI usage API)                        │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 3: Docker Build & Scan (Per Service)                     │
│  ├─ Multi-stage build (builder + runtime)                       │
│  ├─ Layer caching (Poetry cache, pip wheels)                    │
│  ├─ Trivy vulnerability scan                                    │
│  ├─ Push to ECR with semantic tags                              │
│  └─ Image size validation (<500MB runtime)                      │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 4: Deployment (Environment-Specific)                     │
│  ├─ Dev: Auto-deploy on merge to main                           │
│  ├─ Staging: Manual approval + smoke tests                      │
│  ├─ Prod: Approval + canary deployment (10% → 50% → 100%)       │
│  └─ Health check validation (30s timeout)                       │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 5: Post-Deployment Validation                            │
│  ├─ Smoke tests (critical endpoints)                            │
│  ├─ Accuracy validation (subset of ground truth)                │
│  ├─ Performance benchmarks (p50, p95 latency)                   │
│  ├─ Cost anomaly detection (LLM spend)                          │
│  └─ Auto-rollback on SLO breach                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

### Complete GitHub Actions Workflows

#### Primary CI Workflow

**File:** `.github/workflows/ci.yml`

```yaml
name: RAGLite CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"
  POETRY_VERSION: "1.8.2"
  AWS_REGION: us-east-1

jobs:
  # ============================================================
  # STAGE 1: Code Quality & Security
  # ============================================================
  code-quality:
    name: Code Quality & Linting
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: ${{ env.POETRY_VERSION }}
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Cache Poetry dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/pypoetry
            .venv
          key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}
          restore-keys: |
            ${{ runner.os }}-poetry-

      - name: Install dependencies
        run: poetry install --no-interaction --no-ansi --with dev

      - name: Format check (Black)
        run: poetry run black --check .

      - name: Import sort check (isort)
        run: poetry run isort --check-only .

      - name: Lint (Ruff)
        run: poetry run ruff check .

      - name: Type check (mypy)
        run: poetry run mypy services/ orchestrator/ shared/
        continue-on-error: true  # Warn but don't fail on type errors initially

  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    permissions:
      security-events: write  # For uploading to Security tab
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1

      - name: Install dependencies
        run: poetry install --no-interaction --with dev

      - name: SAST with Bandit
        run: |
          poetry run bandit -r services/ orchestrator/ shared/ -f json -o bandit-report.json
        continue-on-error: true

      - name: Upload Bandit results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: bandit-security-report
          path: bandit-report.json

      - name: Dependency vulnerability scan (Safety)
        run: |
          poetry run safety check --json > safety-report.json
        continue-on-error: true

      - name: Secret detection (truffleHog)
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD

      - name: Python dependency audit (pip-audit)
        run: |
          poetry run pip-audit --format json > pip-audit-report.json
        continue-on-error: true

  # ============================================================
  # STAGE 2: Multi-Layer Testing
  # ============================================================
  unit-tests:
    name: Unit Tests (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install Poetry
        uses: snok/install-poetry@v1

      - name: Cache Poetry dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/pypoetry
            .venv
          key: ${{ runner.os }}-poetry-${{ matrix.python-version }}-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        run: poetry install --no-interaction --with dev,test

      - name: Run unit tests with coverage
        run: |
          poetry run pytest \
            --cov=services \
            --cov=orchestrator \
            --cov=shared \
            --cov-report=xml \
            --cov-report=term \
            --cov-branch \
            --junitxml=pytest-report.xml \
            -v \
            services/*/tests/ \
            orchestrator/tests/ \
            shared/tests/

      - name: Coverage threshold enforcement (80%)
        run: |
          poetry run coverage report --fail-under=80

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
          flags: unit-tests-py${{ matrix.python-version }}
          name: unit-coverage

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: pytest-results-${{ matrix.python-version }}
          path: pytest-report.xml

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    services:
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333
      neo4j:
        image: neo4j:5-community
        env:
          NEO4J_AUTH: neo4j/test-password
        ports:
          - 7687:7687
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1

      - name: Install dependencies
        run: poetry install --no-interaction --with dev,test

      - name: Run integration tests
        env:
          QDRANT_HOST: localhost
          QDRANT_PORT: 6333
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          NEO4J_PASSWORD: test-password
        run: |
          poetry run pytest \
            --cov=services \
            --cov-append \
            --cov-report=xml \
            -v \
            -m integration \
            tests/integration/

      - name: Upload integration coverage
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
          flags: integration-tests

  accuracy-regression:
    name: Accuracy Regression Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1

      - name: Install dependencies
        run: poetry install --no-interaction --with test

      - name: Run accuracy validation (ground truth)
        env:
          CLAUDE_API_KEY: ${{ secrets.CLAUDE_API_KEY }}
        run: |
          poetry run python scripts/run-accuracy-tests.py \
            --threshold 0.90 \
            --output accuracy-report.json

      - name: Validate accuracy threshold
        run: |
          poetry run python scripts/validate-accuracy.py \
            --input accuracy-report.json \
            --retrieval-threshold 0.90 \
            --attribution-threshold 0.95

      - name: Upload accuracy report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: accuracy-regression-report
          path: accuracy-report.json

  llm-cost-tracking:
    name: LLM Cost Tracking
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4

      - name: Track LLM API usage
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          # Run test suite and capture API call metrics
          poetry run python scripts/track-llm-costs.py \
            --output llm-cost-report.json

      - name: Comment cost estimate on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('llm-cost-report.json', 'utf8'));
            const body = `## 💰 LLM Cost Estimate

            **Total estimated cost for this PR:** $${report.total_cost.toFixed(4)}

            | Service | Tokens (Input) | Tokens (Output) | Cost |
            |---------|----------------|-----------------|------|
            | Claude 3.7 Sonnet | ${report.claude.input_tokens.toLocaleString()} | ${report.claude.output_tokens.toLocaleString()} | $${report.claude.cost.toFixed(4)} |
            | Embeddings (Fin-E5) | ${report.embeddings.tokens.toLocaleString()} | - | $${report.embeddings.cost.toFixed(4)} |

            **Warning threshold:** $5.00 per PR
            ${report.total_cost > 5.0 ? '⚠️ **Cost exceeds threshold!**' : '✅ Within budget'}
            `;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });

  # ============================================================
  # STAGE 3: Docker Build & Security Scan
  # ============================================================
  docker-build:
    name: Build Docker Images
    runs-on: ubuntu-latest
    needs: [code-quality, security-scan, unit-tests]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    strategy:
      matrix:
        service:
          - ingestion
          - retrieval
          - graphrag
          - forecasting
          - insights
          - gateway
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Extract metadata (tags, labels)
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ steps.login-ecr.outputs.registry }}/raglite-${{ matrix.service }}
          tags: |
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=ref,event=branch
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Cache Docker layers
        uses: actions/cache@v4
        with:
          path: /tmp/.buildx-cache
          key: ${{ runner.os }}-buildx-${{ matrix.service }}-${{ github.sha }}
          restore-keys: |
            ${{ runner.os }}-buildx-${{ matrix.service }}-

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: ./services/${{ matrix.service }}
          file: ./services/${{ matrix.service }}/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=local,src=/tmp/.buildx-cache
          cache-to: type=local,dest=/tmp/.buildx-cache-new,mode=max
          build-args: |
            PYTHON_VERSION=${{ env.PYTHON_VERSION }}
            POETRY_VERSION=${{ env.POETRY_VERSION }}

      - name: Move cache
        run: |
          rm -rf /tmp/.buildx-cache
          mv /tmp/.buildx-cache-new /tmp/.buildx-cache

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.login-ecr.outputs.registry }}/raglite-${{ matrix.service }}:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results-${{ matrix.service }}.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results-${{ matrix.service }}.sarif'
          category: 'trivy-${{ matrix.service }}'

      - name: Validate image size
        run: |
          IMAGE_SIZE=$(docker image inspect ${{ steps.login-ecr.outputs.registry }}/raglite-${{ matrix.service }}:${{ github.sha }} --format='{{.Size}}')
          MAX_SIZE=524288000  # 500MB
          if [ $IMAGE_SIZE -gt $MAX_SIZE ]; then
            echo "Error: Image size ${IMAGE_SIZE} bytes exceeds maximum ${MAX_SIZE} bytes"
            exit 1
          fi
          echo "✅ Image size: $(($IMAGE_SIZE / 1024 / 1024))MB (within limit)"

  # ============================================================
  # STAGE 4: Deployment
  # ============================================================
  deploy-dev:
    name: Deploy to Development
    runs-on: ubuntu-latest
    needs: [docker-build, integration-tests, accuracy-regression]
    if: github.ref == 'refs/heads/main'
    environment:
      name: development
      url: https://dev.raglite.internal
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy to ECS (Development)
        run: |
          for service in gateway ingestion retrieval forecasting insights; do
            aws ecs update-service \
              --cluster raglite-dev-cluster \
              --service raglite-dev-${service} \
              --force-new-deployment \
              --region ${{ env.AWS_REGION }}
          done

      - name: Wait for deployment stabilization
        run: |
          for service in gateway ingestion retrieval forecasting insights; do
            aws ecs wait services-stable \
              --cluster raglite-dev-cluster \
              --services raglite-dev-${service} \
              --region ${{ env.AWS_REGION }}
          done

      - name: Run smoke tests
        run: |
          poetry run python scripts/smoke-tests.py \
            --env development \
            --endpoint https://dev.raglite.internal

  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [deploy-dev]
    if: github.ref == 'refs/heads/main'
    environment:
      name: staging
      url: https://staging.raglite.internal
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy to ECS (Staging) with canary
        run: |
          # Canary deployment: 10% → 50% → 100%
          ./scripts/canary-deploy.sh staging 10 50 100

      - name: Validate staging deployment
        run: |
          poetry run pytest tests/e2e/ \
            --env staging \
            --endpoint https://staging.raglite.internal

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://raglite.production
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Blue/Green deployment (Production)
        run: |
          # Use AWS CodeDeploy for blue/green deployment
          aws deploy create-deployment \
            --application-name raglite-prod \
            --deployment-group-name raglite-prod-dg \
            --deployment-config-name CodeDeployDefault.ECSCanary10Percent5Minutes \
            --region ${{ env.AWS_REGION }}

      - name: Monitor deployment health
        run: |
          ./scripts/monitor-deployment.sh production 300

      - name: Run production smoke tests
        run: |
          poetry run python scripts/smoke-tests.py \
            --env production \
            --endpoint https://raglite.production

  # ============================================================
  # STAGE 5: Post-Deployment Validation
  # ============================================================
  post-deploy-validation:
    name: Post-Deployment Validation
    runs-on: ubuntu-latest
    needs: [deploy-production]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Run accuracy validation (production subset)
        env:
          CLAUDE_API_KEY: ${{ secrets.CLAUDE_API_KEY }}
        run: |
          poetry run python scripts/run-accuracy-tests.py \
            --env production \
            --subset critical \
            --threshold 0.90

      - name: Performance benchmark
        run: |
          poetry run python scripts/performance-benchmark.py \
            --env production \
            --duration 300 \
            --concurrent-users 10

      - name: Cost anomaly check
        env:
          AWS_COST_EXPLORER_ENABLED: true
        run: |
          poetry run python scripts/check-cost-anomalies.py \
            --lookback-days 7 \
            --threshold-increase 50

      - name: Notify deployment status
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: ${{ secrets.SLACK_CHANNEL_ID }}
          slack-message: |
            ✅ RAGLite deployed to production successfully!

            **Commit:** ${{ github.sha }}
            **Author:** ${{ github.actor }}
            **Accuracy:** Validated ✓
            **Performance:** Within SLO ✓
            **Cost:** No anomalies ✓
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```

---

### Multi-Stage Dockerfile Example

**File:** `services/retrieval/Dockerfile`

```dockerfile
# ============================================================
# Stage 1: Builder - Install dependencies and compile
# ============================================================
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files first (maximize cache reuse)
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev dependencies)
RUN poetry install --no-dev --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Install the application
RUN poetry install --no-dev --no-interaction --no-ansi

# ============================================================
# Stage 2: Runtime - Minimal production image
# ============================================================
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r raglite && useradd -r -g raglite raglite

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code from builder
COPY --from=builder /app /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Change ownership to non-root user
RUN chown -R raglite:raglite /app

# Switch to non-root user
USER raglite

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5002/health').raise_for_status()"

# Expose port
EXPOSE 5002

# Run the MCP server
CMD ["python", "main.py"]
```

**.dockerignore Example:**

```
# Git
.git
.gitignore
.gitattributes

# Python
__pycache__
*.py[cod]
*$py.class
*.so
.Python
.venv
venv/
ENV/
env/

# Testing
.pytest_cache
.coverage
htmlcov/
.tox/
*.cover

# IDE
.vscode/
.idea/
*.swp
*.swo

# CI/CD
.github/
*.md
README*

# Docker
Dockerfile
.dockerignore
docker-compose.yml

# Documentation
docs/
tests/
```

---

### Deployment Automation Scripts

**File:** `scripts/canary-deploy.sh`

```bash
#!/bin/bash
# Canary deployment script for progressive rollout

set -euo pipefail

ENVIRONMENT=$1
shift
PERCENTAGES=("$@")

CLUSTER="raglite-${ENVIRONMENT}-cluster"
SERVICES=("gateway" "ingestion" "retrieval" "forecasting" "insights")

echo "🚀 Starting canary deployment to ${ENVIRONMENT}"
echo "📊 Rollout plan: ${PERCENTAGES[*]}%"

for PERCENTAGE in "${PERCENTAGES[@]}"; do
  echo ""
  echo "─────────────────────────────────────────"
  echo "📈 Deploying ${PERCENTAGE}% traffic..."
  echo "─────────────────────────────────────────"

  for SERVICE in "${SERVICES[@]}"; do
    SERVICE_NAME="raglite-${ENVIRONMENT}-${SERVICE}"

    # Get current task definition
    TASK_DEF=$(aws ecs describe-services \
      --cluster "${CLUSTER}" \
      --services "${SERVICE_NAME}" \
      --query 'services[0].taskDefinition' \
      --output text)

    # Update service with new task definition (latest image)
    aws ecs update-service \
      --cluster "${CLUSTER}" \
      --service "${SERVICE_NAME}" \
      --task-definition "${TASK_DEF}" \
      --force-new-deployment \
      --deployment-configuration "maximumPercent=${PERCENTAGE},minimumHealthyPercent=$((PERCENTAGE - 10))" \
      --region us-east-1 \
      > /dev/null

    echo "✓ Updated ${SERVICE_NAME}"
  done

  # Wait for services to stabilize
  echo "⏳ Waiting for services to stabilize..."
  for SERVICE in "${SERVICES[@]}"; do
    SERVICE_NAME="raglite-${ENVIRONMENT}-${SERVICE}"
    aws ecs wait services-stable \
      --cluster "${CLUSTER}" \
      --services "${SERVICE_NAME}" \
      --region us-east-1
  done

  # Health check validation
  echo "🏥 Running health checks..."
  python scripts/validate-health.py --env "${ENVIRONMENT}" --percentage "${PERCENTAGE}"

  # Canary metrics analysis
  if [ "${PERCENTAGE}" -lt 100 ]; then
    echo "📊 Analyzing canary metrics (2 min observation)..."
    sleep 120

    python scripts/canary-analysis.py \
      --env "${ENVIRONMENT}" \
      --percentage "${PERCENTAGE}" \
      --baseline main \
      --metrics "error_rate,latency_p95,llm_cost" \
      --threshold-error-rate 0.05 \
      --threshold-latency-increase 20

    if [ $? -ne 0 ]; then
      echo "❌ Canary analysis failed! Rolling back..."
      ./scripts/rollback.sh "${ENVIRONMENT}"
      exit 1
    fi

    echo "✅ Canary analysis passed for ${PERCENTAGE}%"
  fi
done

echo ""
echo "🎉 Deployment to ${ENVIRONMENT} completed successfully!"
```

**File:** `scripts/monitor-deployment.sh`

```bash
#!/bin/bash
# Monitor deployment health and auto-rollback on failure

set -euo pipefail

ENVIRONMENT=$1
TIMEOUT=${2:-300}  # Default 5 minutes

CLUSTER="raglite-${ENVIRONMENT}-cluster"
SERVICES=("gateway" "ingestion" "retrieval" "forecasting" "insights")

echo "🔍 Monitoring ${ENVIRONMENT} deployment health for ${TIMEOUT}s"

START_TIME=$(date +%s)
FAILURE_COUNT=0
MAX_FAILURES=3

while true; do
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))

  if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "✅ Monitoring period completed successfully"
    exit 0
  fi

  # Check all services are healthy
  ALL_HEALTHY=true
  for SERVICE in "${SERVICES[@]}"; do
    SERVICE_NAME="raglite-${ENVIRONMENT}-${SERVICE}"

    RUNNING_COUNT=$(aws ecs describe-services \
      --cluster "${CLUSTER}" \
      --services "${SERVICE_NAME}" \
      --query 'services[0].runningCount' \
      --output text)

    DESIRED_COUNT=$(aws ecs describe-services \
      --cluster "${CLUSTER}" \
      --services "${SERVICE_NAME}" \
      --query 'services[0].desiredCount' \
      --output text)

    if [ "$RUNNING_COUNT" -ne "$DESIRED_COUNT" ]; then
      echo "⚠️  ${SERVICE_NAME}: ${RUNNING_COUNT}/${DESIRED_COUNT} tasks running"
      ALL_HEALTHY=false
    fi
  done

  # Check CloudWatch alarms
  ALARMS=$(aws cloudwatch describe-alarms \
    --alarm-name-prefix "raglite-${ENVIRONMENT}" \
    --state-value ALARM \
    --query 'MetricAlarms[].AlarmName' \
    --output text)

  if [ -n "$ALARMS" ]; then
    echo "🚨 CloudWatch alarms triggered: ${ALARMS}"
    FAILURE_COUNT=$((FAILURE_COUNT + 1))
  fi

  if [ "$ALL_HEALTHY" = false ]; then
    FAILURE_COUNT=$((FAILURE_COUNT + 1))
  fi

  # Auto-rollback on repeated failures
  if [ $FAILURE_COUNT -ge $MAX_FAILURES ]; then
    echo "❌ Deployment failed ${FAILURE_COUNT} consecutive health checks"
    echo "🔄 Initiating automatic rollback..."
    ./scripts/rollback.sh "${ENVIRONMENT}"
    exit 1
  fi

  # Reset failure count if all healthy
  if [ "$ALL_HEALTHY" = true ] && [ -z "$ALARMS" ]; then
    FAILURE_COUNT=0
  fi

  # Wait before next check
  sleep 30
done
```

---

### Accuracy Regression Testing

**File:** `scripts/run-accuracy-tests.py`

```python
#!/usr/bin/env python3
"""
Accuracy regression testing against ground truth dataset.
Ensures retrieval accuracy ≥90% and source attribution ≥95%.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

import requests
from tqdm import tqdm

GROUND_TRUTH_QUERIES = [
    {
        "query": "What was Q3 2024 revenue?",
        "expected_answer": "$5.2M",
        "expected_sources": ["Q3_2024_Financial_Report.pdf:3"],
        "category": "factual_retrieval",
    },
    {
        "query": "What drove Q3 revenue variance?",
        "expected_answer_contains": ["marketing spend", "30% reduction", "12% decline"],
        "expected_sources": ["Q3_2024_Financial_Report.pdf:3", "Q3_Marketing_Analysis.xlsx"],
        "category": "analytical_query",
    },
    # ... 50+ total queries
]


def run_accuracy_tests(
    endpoint: str,
    threshold: float,
    subset: str = "all",
    output_file: str = "accuracy-report.json",
) -> Dict:
    """Run accuracy validation tests."""

    results = {
        "total": 0,
        "correct": 0,
        "accuracy": 0.0,
        "attribution_correct": 0,
        "attribution_total": 0,
        "attribution_accuracy": 0.0,
        "failures": [],
    }

    queries = GROUND_TRUTH_QUERIES
    if subset == "critical":
        queries = [q for q in queries if q.get("critical", False)]

    print(f"🧪 Running {len(queries)} accuracy tests against {endpoint}")

    for test_case in tqdm(queries, desc="Testing"):
        results["total"] += 1

        # Call RAGLite endpoint
        response = requests.post(
            f"{endpoint}/mcp/search_documents",
            json={"query": test_case["query"], "top_k": 10},
            timeout=30,
        )

        if response.status_code != 200:
            results["failures"].append({
                "query": test_case["query"],
                "error": f"HTTP {response.status_code}",
            })
            continue

        retrieved_docs = response.json()["results"]

        # Validate answer correctness
        is_correct = validate_answer(retrieved_docs, test_case)
        if is_correct:
            results["correct"] += 1
        else:
            results["failures"].append({
                "query": test_case["query"],
                "category": test_case["category"],
                "expected": test_case.get("expected_answer") or test_case.get("expected_answer_contains"),
                "retrieved": [doc["text"][:100] for doc in retrieved_docs[:3]],
            })

        # Validate source attribution
        for expected_source in test_case["expected_sources"]:
            results["attribution_total"] += 1
            if any(expected_source in doc.get("source", "") for doc in retrieved_docs):
                results["attribution_correct"] += 1

    # Calculate metrics
    results["accuracy"] = results["correct"] / results["total"] if results["total"] > 0 else 0.0
    results["attribution_accuracy"] = (
        results["attribution_correct"] / results["attribution_total"]
        if results["attribution_total"] > 0
        else 0.0
    )

    # Save report
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 Accuracy Test Results")
    print("=" * 60)
    print(f"Retrieval Accuracy:      {results['accuracy']:.1%} ({results['correct']}/{results['total']})")
    print(f"Attribution Accuracy:    {results['attribution_accuracy']:.1%}")
    print(f"Threshold:               {threshold:.1%}")

    if results["accuracy"] >= threshold and results["attribution_accuracy"] >= 0.95:
        print("✅ PASSED: Accuracy requirements met")
        return results
    else:
        print("❌ FAILED: Accuracy below threshold")
        print(f"\nTop failures:")
        for failure in results["failures"][:5]:
            print(f"  • {failure['query']}")
        return results


def validate_answer(docs: List[Dict], test_case: Dict) -> bool:
    """Validate if retrieved documents contain expected answer."""
    # Implementation details for answer validation
    # Check if expected_answer or expected_answer_contains matches
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://localhost:5000")
    parser.add_argument("--threshold", type=float, default=0.90)
    parser.add_argument("--subset", choices=["all", "critical"], default="all")
    parser.add_argument("--output", default="accuracy-report.json")

    args = parser.parse_args()

    results = run_accuracy_tests(
        args.endpoint,
        args.threshold,
        args.subset,
        args.output,
    )

    # Exit with error code if tests failed
    if results["accuracy"] < args.threshold:
        sys.exit(1)
```

---

### Security & Compliance Integration

**Bandit Configuration:** `.bandit`

```yaml
exclude_dirs:
  - /tests
  - /docs

tests:
  - B101  # assert_used
  - B102  # exec_used
  - B103  # set_bad_file_permissions
  - B104  # hardcoded_bind_all_interfaces
  - B105  # hardcoded_password_string
  - B106  # hardcoded_password_funcarg
  - B107  # hardcoded_password_default
  - B108  # hardcoded_tmp_directory
  - B110  # try_except_pass
  - B201  # flask_debug_true
  - B301  # pickle
  - B302  # marshal
  - B303  # md5
  - B304  # ciphers
  - B305  # cipher_modes
  - B306  # mktemp_q
  - B307  # eval
  - B308  # mark_safe
  - B309  # httpsconnection
  - B310  # urllib_urlopen
  - B311  # random
  - B312  # telnetlib
  - B313  # xml_bad_cElementTree
  - B314  # xml_bad_ElementTree
  - B315  # xml_bad_expatreader
  - B316  # xml_bad_expatbuilder
  - B317  # xml_bad_sax
  - B318  # xml_bad_minidom
  - B319  # xml_bad_pulldom
  - B320  # xml_bad_etree
  - B321  # ftplib
  - B322  # input
  - B323  # unverified_context
  - B324  # hashlib_new_insecure_functions
  - B325  # tempnam
  - B401  # import_telnetlib
  - B402  # import_ftplib
  - B403  # import_pickle
  - B404  # import_subprocess
  - B405  # import_xml_etree
  - B406  # import_xml_sax
  - B407  # import_xml_expat
  - B408  # import_xml_minidom
  - B409  # import_xml_pulldom
  - B410  # import_lxml
  - B411  # import_xmlrpclib
  - B412  # import_httpoxy
  - B413  # import_pycrypto
  - B501  # request_with_no_cert_validation
  - B502  # ssl_with_bad_version
  - B503  # ssl_with_bad_defaults
  - B504  # ssl_with_no_version
  - B505  # weak_cryptographic_key
  - B506  # yaml_load
  - B507  # ssh_no_host_key_verification
  - B601  # paramiko_calls
  - B602  # shell_injection
  - B603  # subprocess_without_shell_equals_true
  - B604  # any_other_function_with_shell_equals_true
  - B605  # start_process_with_a_shell
  - B606  # start_process_with_no_shell
  - B607  # start_process_with_partial_path
  - B608  # hardcoded_sql_expressions
  - B609  # linux_commands_wildcard_injection
  - B610  # django_extra_used
  - B611  # django_rawsql_used
  - B701  # jinja2_autoescape_false
  - B702  # use_of_mako_templates
  - B703  # django_mark_safe

severity:
  - medium
  - high

confidence:
  - medium
  - high
```

---

## Conclusion

This architecture document defines a **production-ready, research-validated RAGLite system** that delivers:

✅ **90%+ retrieval accuracy** (Contextual Retrieval: 98.1%)
✅ **95%+ source attribution** (metadata tracking + citation)
✅ **Phased complexity** (start simple, add GraphRAG only if needed)
✅ **Multi-LLM flexibility** (AWS Strands: no vendor lock-in)
✅ **Microservices architecture** (5 services + MCP Gateway)
✅ **Cloud-native deployment** (AWS ECS/EKS with auto-scaling)
✅ **Security & compliance** (encryption, audit trails, least privilege)
✅ **Cost optimization** (potential 99% savings if Phase 2 skipped)

**Next Steps:**
1. Review and approve architecture
2. Begin Phase 1 implementation (Weeks 1-4)
3. Validate Contextual Retrieval accuracy (Decision Gate)
4. Proceed to Phase 2 (GraphRAG) or Phase 3 (Intelligence) based on results

---

**Document Version:** 1.0
**Author:** Winston (Architect Agent)
**Date:** October 3, 2025
**Status:** Complete - Ready for Implementation
