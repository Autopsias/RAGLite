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
