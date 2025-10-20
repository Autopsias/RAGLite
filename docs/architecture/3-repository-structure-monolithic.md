# 3. Repository Structure (Monolithic)

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
│   ├── structured/            # ⚠️ CONDITIONAL - Epic 2 Phase 2B/2C ONLY (~150 lines)
│   │   ├── __init__.py        # IF Phase 2A fixed chunking <70% accuracy
│   │   ├── table_extraction.py # Docling → PostgreSQL conversion
│   │   ├── sql_querying.py    # SQL query generation for tables
│   │   └── table_retrieval.py # Table-based retrieval
│   │
│   ├── graph/                 # ⚠️ CONDITIONAL - Epic 2 Phase 2C ONLY (~200 lines)
│   │   ├── __init__.py        # IF Phase 2B structured <75% accuracy
│   │   ├── entity_extraction.py # LLM-based entity extraction
│   │   ├── graph_construction.py # Neo4j graph population
│   │   └── graph_retrieval.py # Graph traversal queries
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

**Total Files:** ~15 Python files (baseline) + 7 conditional files (if Phase 2B/2C triggered)
**Total Lines:** 600-800 lines (baseline) + 350 lines (if Phase 2B/2C triggered)
**Complexity:** LOW (direct function calls, single deployment)

---

## Conditional Layers (Epic 2 Phase 2B/2C)

**⚠️ IMPORTANT**: The `structured/` and `graph/` modules are **CONDITIONAL** - they are ONLY implemented if specific decision gates are triggered during Epic 2 execution.

### Structured Layer (Phase 2B) - 15% Probability

**Trigger**: Phase 2A fixed chunking decision gate (IF retrieval accuracy <70%)

**Purpose**: Add PostgreSQL-based structured table storage for precise financial table queries

**Files Added**:
- `raglite/structured/table_extraction.py` (~50 lines)
- `raglite/structured/sql_querying.py` (~50 lines)
- `raglite/structured/table_retrieval.py` (~50 lines)

**Total Impact**: +150 lines, +PostgreSQL infrastructure

**Decision Authority**: PM (John) approves at Phase 2A decision gate (T+17, Week 3 Day 3)

---

### Graph Layer (Phase 2C) - 5% Probability

**Trigger**: Phase 2B structured multi-index decision gate (IF retrieval accuracy <75%)

**Purpose**: Add Neo4j-based knowledge graph for entity relationships and multi-hop queries

**Files Added**:
- `raglite/graph/entity_extraction.py` (~70 lines)
- `raglite/graph/graph_construction.py` (~70 lines)
- `raglite/graph/graph_retrieval.py` (~60 lines)

**Total Impact**: +200 lines, +Neo4j infrastructure

**Decision Authority**: PM (John) approves at Phase 2B decision gate (IF triggered)

---

### Best Case Scenario (80% Probability)

**Phase 2A succeeds (≥70% accuracy)** → `structured/` and `graph/` layers are **NEVER IMPLEMENTED**

**Repository stays at baseline size**: 600-800 lines across ~15 files

**Infrastructure stays simple**: Qdrant only (no PostgreSQL, no Neo4j)

---
