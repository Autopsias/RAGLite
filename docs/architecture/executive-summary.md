# Executive Summary

## Architectural Vision

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

## Architecture at a Glance

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
