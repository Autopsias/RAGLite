# RAGLite - Source Tree Analysis

> **Auto-generated:** 2025-11-26 | **Scan Level:** Deep

## Package Structure

### Main Application (`raglite/`) - 16,806 Lines

```
raglite/
├── __init__.py                 (89 lines)     # Package exports
├── main.py                     (1,383 lines)  # MCP server entrypoint, 5 tools
│
├── ingestion/                  # Document Processing Pipeline
│   ├── __init__.py
│   ├── pipeline.py             (2,095 lines)  # Core ingestion orchestration
│   ├── document_ingestion.py   (892 lines)    # Document loading, temp file handling
│   ├── chunking_strategy.py    (456 lines)    # Table-aware chunking
│   ├── embedding_generation.py (312 lines)    # Fin-E5 vector generation
│   ├── table_extraction.py     (481 lines)    # Table parsing
│   ├── adaptive_table_extraction.py           # Adaptive table handling
│   ├── storage_operations.py   (523 lines)    # Qdrant/PostgreSQL storage
│   ├── job_tracker.py          (287 lines)    # Async job management
│   └── adaptive_table/         # Advanced table processing
│       ├── core.py
│       ├── classification.py
│       ├── multi_header.py
│       ├── standard_layouts.py
│       └── unit_inference.py
│
├── retrieval/                  # Search & Query Processing
│   ├── __init__.py             (12 lines)
│   ├── search.py               (770 lines)    # Vector search
│   ├── multi_index_search.py   (484 lines)    # Hybrid search orchestration
│   ├── query_classifier.py     (663 lines)    # Query type classification
│   ├── query_preprocessing.py  (212 lines)    # Query normalization
│   ├── sql_table_search.py     (344 lines)    # PostgreSQL table queries
│   ├── period_normalizer.py    (213 lines)    # Date/period parsing
│   └── attribution.py          (91 lines)     # Source citation generation
│
├── agentic/                    # AWS Strands Orchestration
│   ├── __init__.py
│   ├── orchestrator.py         (456 lines)    # Workflow coordination
│   ├── planner.py              (523 lines)    # Query decomposition
│   ├── state.py                (187 lines)    # Agent state management
│   ├── fallback.py             (234 lines)    # Graceful degradation
│   ├── error_handler.py        (156 lines)    # Error handling
│   └── agents/                 # Individual Agents
│       ├── retrieval_agent.py  (312 lines)    # Document retrieval
│       ├── analysis_agent.py   (287 lines)    # Financial analysis
│       ├── synthesis_agent.py  (256 lines)    # Answer synthesis
│       ├── mock_retrieval.py                  # Test mocks
│       └── mock_synthesis.py                  # Test mocks
│
├── shared/                     # Cross-Cutting Concerns
│   ├── __init__.py             (0 lines)
│   ├── config.py               (151 lines)    # Pydantic settings
│   ├── clients.py              (438 lines)    # Service clients (Qdrant, PostgreSQL, Mistral)
│   ├── models.py               (397 lines)    # Pydantic data models
│   ├── logging.py              (37 lines)     # Structured logging
│   ├── bm25.py                 (386 lines)    # BM25 index management
│   └── safety.py               (149 lines)    # Input validation
│
├── structured/                 # SQL Table Retrieval
│   ├── __init__.py             (4 lines)
│   └── table_retrieval.py      (318 lines)    # Table query engine
│
└── forecasting/                # Time-Series (Epic 4)
    ├── __init__.py
    └── timeseries_extract.py   (234 lines)    # Time-series extraction
```

## Module Responsibilities

### `main.py` - MCP Server Entry Point (1,383 lines)

**Purpose:** FastMCP server exposing 5 MCP tools to Claude clients

**Key Functions:**
- `ingest_financial_document()` - Sync document ingestion (3 input modes)
- `ingest_financial_document_async()` - Background ingestion for large files
- `get_ingestion_status()` - Async job polling
- `query_financial_documents()` - Natural language queries
- `analytical_query_financial_documents()` - Multi-step analytical queries

**Dependencies:** FastMCP, ingestion pipeline, retrieval modules, agentic orchestrator

### `ingestion/` - Document Processing (5,046 lines)

**Responsibility:** Transform raw documents into searchable chunks with embeddings

**Pipeline Flow:**
1. **Document Loading:** `document_ingestion.py` - File handling, temp files, URL download
2. **Content Extraction:** `pipeline.py` - Docling PDF/openpyxl Excel processing
3. **Table Processing:** `table_extraction.py`, `adaptive_table/` - Financial table handling
4. **Chunking:** `chunking_strategy.py` - Table-aware 4096-token chunks
5. **Embedding:** `embedding_generation.py` - E5-large-v2 vectors
6. **Storage:** `storage_operations.py` - Qdrant + PostgreSQL persistence
7. **Job Tracking:** `job_tracker.py` - Async job management

### `retrieval/` - Search & Query (2,777 lines)

**Responsibility:** Query processing, hybrid search, and result ranking

**Search Strategy:**
1. **Query Classification:** `query_classifier.py` - Determine optimal search path
2. **Preprocessing:** `query_preprocessing.py` - Query normalization
3. **Multi-Index Search:** `multi_index_search.py` - Orchestrate Qdrant + BM25 + SQL
4. **Vector Search:** `search.py` - Qdrant similarity search
5. **SQL Search:** `sql_table_search.py` - PostgreSQL exact matching
6. **Period Normalization:** `period_normalizer.py` - Date parsing
7. **Attribution:** `attribution.py` - Source citation generation

### `agentic/` - Workflow Orchestration (2,411 lines)

**Responsibility:** Multi-step analytical queries using AWS Strands

**Components:**
- **Orchestrator:** Coordinates agent workflows
- **Planner:** Decomposes complex queries into sub-tasks
- **Agents:** Specialized agents for retrieval, analysis, synthesis
- **Fallback:** Graceful degradation when agents fail
- **State:** Workflow state management

### `shared/` - Cross-Cutting (1,558 lines)

**Responsibility:** Configuration, clients, models, utilities

**Components:**
- **Config:** Pydantic settings from environment variables
- **Clients:** Singleton clients for Qdrant, PostgreSQL, Mistral, Claude
- **Models:** 15+ Pydantic models for data validation
- **BM25:** In-memory lexical search index
- **Safety:** Input validation and sanitization

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── unit/                       # ~200 unit tests
│   ├── test_shared_*.py        # Shared module tests
│   ├── test_ac*.py             # Acceptance criteria tests
│   ├── test_query_classifier.py
│   ├── test_table_aware_chunking.py
│   └── agentic/                # Agent-specific tests
├── integration/                # ~115 integration tests
│   ├── test_sql_routing.py
│   ├── test_ac3_ground_truth.py
│   └── test_*.py
├── e2e/                        # ~28 end-to-end tests
├── fixtures/                   # Test data
└── support/                    # Test utilities
```

## Scripts

```
scripts/
├── setup-dev.sh                # Development environment setup
├── init-qdrant.py              # Initialize Qdrant collection
├── clean-test-databases.py     # Database cleanup
├── ingest-production-batch.py  # Batch ingestion
└── archive/                    # Deprecated scripts
```

## Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, dependencies, tool config |
| `pytest.ini` | Pytest configuration |
| `docker-compose.yml` | Service definitions (Qdrant, PostgreSQL) |
| `.env` | Environment variables |
| `.pre-commit-config.yaml` | Pre-commit hooks |

---

*Generated by BMAD Document Project Workflow*
