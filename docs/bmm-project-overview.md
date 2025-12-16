# RAGLite - Project Overview

> **Auto-generated:** 2025-11-26 | **Scan Level:** Deep | **Workflow:** document-project v1.2.0

## Executive Summary

**RAGLite** is a monolithic Python application providing AI-powered financial document analysis using Retrieval-Augmented Generation (RAG). The system ingests financial PDFs and Excel files, enables natural language querying via the Model Context Protocol (MCP), and delivers accurate answers with source citations.

| Attribute | Value |
|-----------|-------|
| **Project Type** | Python Backend (RAG/MCP Server) |
| **Repository Type** | Monolith |
| **Language** | Python 3.11+ |
| **Version** | 1.1.0 |
| **Total Lines of Code** | ~16,800 (raglite package) |
| **License** | MIT |

## Project Goals

1. **Accurate Financial Document Retrieval:** 90%+ retrieval accuracy on financial queries
2. **Source Attribution:** 95%+ citation accuracy with document, page, and section references
3. **Natural Language Interface:** MCP-based querying via Claude Desktop/Claude Code
4. **Multi-Step Analysis:** Agentic workflow orchestration for complex analytical queries
5. **Time-Series Forecasting:** Extract and analyze financial trends (Epic 4)

## Technology Stack

### Core Technologies

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Language** | Python | 3.11+ | Application code |
| **Package Manager** | uv (Hatchling) | Latest | Dependency management |
| **MCP Server** | FastMCP | 2.12.4 | Model Context Protocol server |
| **Vector Database** | Qdrant | 1.15.1 | Embedding storage and similarity search |
| **Relational Database** | PostgreSQL | 16 | Structured metadata and SQL table search |
| **PDF Extraction** | Docling | 2.55.1 | PDF text and table extraction |
| **Embeddings** | sentence-transformers (E5-large-v2) | 5.1.1 | 1024-dim semantic embeddings |
| **Primary LLM** | Mistral AI | 1.9.11+ | Metadata extraction, query classification, synthesis |
| **Agentic Framework** | AWS Strands | POC/Active | Multi-agent workflow orchestration |
| **BM25 Search** | rank-bm25 | 0.2.2 | Hybrid search (semantic + lexical) |
| **Token Counting** | tiktoken | 0.5.1+ | Chunking strategy |
| **Data Validation** | Pydantic | 2.0+ | Type-safe models |

### Infrastructure

| Category | Technology | Purpose |
|----------|------------|---------|
| **Container Orchestration** | Docker Compose | Local development services |
| **Testing** | pytest + pytest-asyncio | Test framework |
| **Code Quality** | black, ruff, mypy | Formatting, linting, type checking |
| **CI/CD** | GitHub Actions | Automated testing and deployment |

## Architecture Overview

```
┌──────────────────────────────────────────────┐
│  MCP Clients (Claude Desktop, Claude Code)  │
└────────────────┬─────────────────────────────┘
                 │ Model Context Protocol
┌────────────────▼─────────────────────────────┐
│  RAGLite Server (FastMCP)                    │
│  ├─ 5 MCP Tools (ingest, query, status)      │
│  ├─ Agentic Orchestration (Strands+Mistral)  │
│  └─ Multi-Index Search (Qdrant+BM25+SQL)     │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────┐
│  Data Layer                                  │
│  ├─ Qdrant (Vectors) - Port 6333/6335        │
│  ├─ PostgreSQL (Metadata) - Port 5432/5433   │
│  └─ BM25 Index (In-memory)                   │
└──────────────────────────────────────────────┘
```

## Key Features

### Implemented (Epics 1-3)

- **Document Ingestion:** PDF and Excel file processing with Docling
- **Multi-Index Search:** Hybrid retrieval combining Qdrant vectors, BM25, and SQL
- **Rich Metadata:** 15-field LLM-extracted metadata schema per chunk
- **Query Classification:** Route queries to optimal search strategy
- **Agentic Workflows:** Multi-step analytical queries with AWS Strands
- **Source Attribution:** Accurate citations with page and section references
- **Async Ingestion:** Background processing for large documents (>50 pages)

### Planned (Epics 4-5)

- **Time-Series Extraction:** Financial trend analysis
- **Forecasting:** Prophet + LLM hybrid predictions
- **Production Deployment:** AWS ECS/Fargate
- **Monitoring:** CloudWatch integration

## MCP Tools

| Tool | Purpose | Input Mode |
|------|---------|------------|
| `ingest_financial_document` | Sync document ingestion | Path, Base64, URL |
| `ingest_financial_document_async` | Async ingestion for large files | Path, Base64, URL |
| `get_ingestion_status` | Poll async job status | Job ID |
| `query_financial_documents` | Natural language queries | Query string |
| `analytical_query_financial_documents` | Multi-step analytical queries | Query string |

## Directory Structure

```
raglite/
├── raglite/                    # Main package (~16,800 lines)
│   ├── main.py                 # MCP server entrypoint (1,383 lines)
│   ├── ingestion/              # Document processing pipeline
│   ├── retrieval/              # Search and query processing
│   ├── agentic/                # AWS Strands orchestration
│   ├── shared/                 # Config, models, clients
│   ├── structured/             # Table retrieval
│   └── forecasting/            # Time-series extraction
├── tests/                      # Test suite (~358 tests)
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
├── migrations/                 # PostgreSQL migrations
├── scripts/                    # Utility scripts
└── docs/                       # Documentation (100+ files)
```

## Related Documentation

- [Architecture Documentation](docs/architecture/index.md)
- [API Contracts (MCP Tools)](./bmm-api-contracts.md)
- [Data Models](./bmm-data-models.md)
- [Source Tree Analysis](./bmm-source-tree.md)
- [Development Guide](./bmm-development-guide.md)
- [PRD](./prd/index.md)

---

*Generated by BMAD Document Project Workflow*
