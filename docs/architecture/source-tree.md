# RAGLite Source Tree Structure

**Version:** 1.1 (Monolithic)
**Status:** Definitive
**Target:** 600-800 lines of Python code across 15 files

---

## Overview

This document defines the **exact repository structure** for RAGLite monolithic MVP. All developers and AI agents MUST follow this structure when creating files.

**Architecture Approach:** Monolithic Python package with modular organization
**File Count:** ~15 Python files (vs 30+ for microservices)
**Total Lines:** 600-800 lines (vs 3000+ for microservices)
**Complexity:** LOW (direct function calls, single deployment)

---

## Complete Directory Tree

```
raglite/
├── pyproject.toml              # UV dependencies (PEP 621 + dependency-groups)
├── uv.lock                     # Locked dependency versions
├── docker-compose.yml          # Qdrant + app containers
├── Dockerfile                  # Container image definition
├── .env.example                # Environment variable template
├── .gitignore                  # Git exclusions
├── README.md                   # Project overview and setup guide
│
├── raglite/                    # Main Python package (~600-800 lines total)
│   ├── __init__.py             # Package initialization
│   ├── main.py                 # MCP server entrypoint (~200 lines)
│   │
│   ├── ingestion/              # Document processing module (~150 lines)
│   │   ├── __init__.py
│   │   ├── pipeline.py         # Docling + chunking + embedding (~100 lines)
│   │   └── contextual.py       # Contextual Retrieval chunking (~50 lines)
│   │
│   ├── retrieval/              # Search & synthesis module (~150 lines)
│   │   ├── __init__.py
│   │   ├── search.py           # Qdrant vector search (~50 lines)
│   │   ├── synthesis.py        # LLM answer synthesis (~70 lines)
│   │   └── attribution.py      # Source citation generation (~30 lines)
│   │
│   ├── forecasting/            # Forecasting module (Phase 3, ~100 lines)
│   │   ├── __init__.py
│   │   └── hybrid.py           # Prophet + LLM adjustment (~90 lines)
│   │
│   ├── insights/               # Insights module (Phase 3, ~100 lines)
│   │   ├── __init__.py
│   │   ├── anomalies.py        # Statistical anomaly detection (~50 lines)
│   │   └── trends.py           # Trend analysis (~50 lines)
│   │
│   ├── shared/                 # Shared utilities (~100 lines)
│   │   ├── __init__.py
│   │   ├── config.py           # Settings (Pydantic BaseSettings) (~30 lines)
│   │   ├── logging.py          # Structured logging setup (~20 lines)
│   │   ├── models.py           # Pydantic data models (~30 lines)
│   │   └── clients.py          # Qdrant, Claude API clients (~20 lines)
│   │
│   └── tests/                  # Tests co-located with code (~200 lines)
│       ├── __init__.py
│       ├── test_ingestion.py   # Ingestion pipeline tests
│       ├── test_retrieval.py   # Retrieval tests
│       ├── test_synthesis.py   # LLM synthesis tests
│       ├── ground_truth.py     # Accuracy validation (50+ queries)
│       └── fixtures/
│           └── sample_financial_report.pdf
│
├── scripts/                    # Utility scripts
│   ├── setup-dev.sh            # One-command local setup
│   ├── init-qdrant.py          # Initialize Qdrant collection
│   └── run-accuracy-tests.py   # Ground truth validation
│
└── docs/                       # Architecture & PRD (sharded)
    ├── README.md               # Documentation guide
    ├── architecture/           # 30 sharded architecture files
    │   ├── 1-introduction-vision.md
    │   ├── 2-executive-summary.md
    │   ├── 3-repository-structure-monolithic.md
    │   ├── 4-research-findings-summary-validated-technologies.md
    │   ├── 5-technology-stack-definitive.md
    │   ├── 6-complete-reference-implementation.md
    │   ├── 7-data-layer.md
    │   ├── 8-phased-implementation-strategy-v11-simplified.md
    │   ├── 9-deployment-strategy-simplified.md
    │   ├── coding-standards.md  # ⭐ BMAD standard file
    │   ├── tech-stack.md        # ⭐ BMAD standard file
    │   ├── source-tree.md       # ⭐ BMAD standard file (this file)
    │   └── ...
    ├── prd/                    # 15 sharded PRD files
    │   ├── index.md
    │   ├── epic-1-foundation-accurate-retrieval.md
    │   ├── epic-2-advanced-document-understanding.md
    │   └── ...
    ├── front-end-spec/         # MCP response format specs
    ├── stories/                # Active user stories
    │   └── 0.1.week-0-integration-spike.md
    ├── qa/                     # Quality assurance
    │   ├── assessments/
    │   └── gates/
    └── archive/                # Historical documents (ignore for development)
```

---

## Module Breakdown

### Core Package: `raglite/`

| Module | Files | Lines | Responsibility |
|--------|-------|-------|----------------|
| `main.py` | 1 | ~200 | MCP server, tool definitions, lifespan management |
| `ingestion/` | 2 | ~150 | PDF/Excel extraction, chunking, embedding generation |
| `retrieval/` | 3 | ~150 | Vector search, LLM synthesis, source attribution |
| `forecasting/` | 1 | ~100 | Time-series forecasting (Phase 3) |
| `insights/` | 2 | ~100 | Anomaly detection, trend analysis (Phase 3) |
| `shared/` | 4 | ~100 | Config, logging, models, API clients |
| `tests/` | 5 | ~200 | Unit, integration, ground truth tests |
| **TOTAL** | **18** | **~1000** | **Includes Phase 3 (~200 lines)** |

**Phase 1 Target:** ~600-800 lines (excludes `forecasting/` and `insights/`)

---

## File-by-File Purpose

### Root Level

#### `pyproject.toml`

**Purpose:** UV dependency management (PEP 621 standard, replaces Poetry)
**Created:** Story 0.0 (Production Repository Setup)
**Size:** ~230 lines (includes tool configs for Black, Ruff, pytest, mypy)
**Example:**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "raglite"
version = "1.1.0"
requires-python = ">=3.11,<4.0"

dependencies = [
    "fastmcp==2.12.4",
    "docling==2.55.1",
    "qdrant-client==1.15.1",
    # ... see actual pyproject.toml for full list
]

[dependency-groups]
dev = [
    "pytest==8.4.2",
    "ruff>=0.0.270,<1.0.0",
    # ...
]
```

#### `docker-compose.yml`

**Purpose:** Local Qdrant + app container orchestration
**Created:** Story 1.1
**Size:** ~30 lines
**Example:**

```yaml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:v1.11.0
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_storage:/qdrant/storage
```

#### `README.md`

**Purpose:** Project overview, setup instructions, quick start
**Created:** **MUST CREATE before Story 1.1**
**Size:** ~100-150 lines
**Sections:**

- Project overview
- Prerequisites (Python 3.11+, Docker, UV)
- Installation (UV sync, Docker Compose)
- Quick start guide
- Architecture reference (link to docs/architecture/)
- Contributing guidelines

#### `.env.example`

**Purpose:** Environment variable template (API keys, config)
**Created:** Story 0.2 (API Setup)
**Example:**

```bash
# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Anthropic Claude API
ANTHROPIC_API_KEY=your_key_here

# AWS (Phase 4)
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
```

---

### `raglite/` Package

#### `raglite/main.py` (~200 lines)

**Purpose:** MCP server entrypoint, tool definitions
**Created:** Story 1.9 (MCP Server Foundation)
**Key Components:**

- FastMCP server initialization
- Lifespan management (startup/shutdown)
- MCP tool definitions:
  - `ingest_financial_document()`
  - `query_financial_documents()`
  - `health_check()`
- Pydantic request/response models
**Reference:** See `docs/archive/architecture-v1.1-insert.md` for complete 250-line example

#### `raglite/ingestion/pipeline.py` (~100 lines)

**Purpose:** Document ingestion orchestration
**Created:** Story 1.2 (PDF), 1.3 (Excel), 1.4 (Chunking), 1.5 (Embeddings)
**Functions:**

- `ingest_document(file_path: str, doc_type: DocumentType) -> JobID`
- `extract_pdf(file_path: str) -> str` (Docling)
- `extract_excel(file_path: str) -> List[Dict]` (openpyxl)
- `chunk_document(content: str) -> List[Chunk]`
- `generate_embeddings(chunks: List[Chunk]) -> List[np.ndarray]`

#### `raglite/ingestion/contextual.py` (~50 lines)

**Purpose:** Contextual Retrieval chunking (LLM-generated context)
**Created:** Story 1.4 or Week 3 (optional enhancement)
**Functions:**

- `add_contextual_metadata(chunk: Chunk) -> Chunk`

#### `raglite/retrieval/search.py` (~50 lines)

**Purpose:** Qdrant vector similarity search
**Created:** Story 1.7 (Vector Search)
**Functions:**

- `search_documents(query: str, top_k: int, filters: Dict) -> List[SearchResult]`
- `generate_query_embedding(query: str) -> np.ndarray`

#### `raglite/retrieval/synthesis.py` (~70 lines)

**Purpose:** LLM answer synthesis from retrieved chunks
**Created:** Story 1.11 (Answer Synthesis)
**Functions:**

- `synthesize_answer(query: str, chunks: List[SearchResult]) -> str`
- `build_synthesis_prompt(query: str, chunks: List) -> str`

#### `raglite/retrieval/attribution.py` (~30 lines)

**Purpose:** Source citation generation
**Created:** Story 1.8 (Source Attribution)
**Functions:**

- `generate_citations(chunks: List[SearchResult]) -> str`
- `format_citation(chunk: SearchResult) -> str`

#### `raglite/shared/config.py` (~30 lines)

**Purpose:** Application settings (Pydantic BaseSettings)
**Created:** Story 1.1 (Project Setup)
**Example:**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    anthropic_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()  # Singleton
```

#### `raglite/shared/logging.py` (~20 lines)

**Purpose:** Structured logging setup
**Created:** Story 1.1
**Functions:**

- `get_logger(name: str) -> logging.Logger`
- `log_query(query_id: str, query_text: str, user_id: str, filters: Dict)`

#### `raglite/shared/models.py` (~30 lines)

**Purpose:** Pydantic data models (DTOs)
**Created:** Story 1.1
**Models:**

- `DocumentMetadata`
- `Chunk`
- `SearchResult`
- `JobID` (type alias)

#### `raglite/shared/clients.py` (~20 lines)

**Purpose:** API client factories (Qdrant, Claude)
**Created:** Story 1.1
**Functions:**

- `get_qdrant_client() -> QdrantClient`
- `get_claude_client() -> Anthropic`

---

### `raglite/tests/` Package

#### `raglite/tests/test_ingestion.py`

**Purpose:** Unit tests for ingestion pipeline
**Created:** Story 1.2-1.5
**Test Cases:**

- `test_ingest_pdf_success()`
- `test_ingest_pdf_file_not_found()`
- `test_chunk_document()`
- `test_generate_embeddings()`

#### `raglite/tests/ground_truth.py`

**Purpose:** Accuracy validation with 50+ Q&A pairs
**Created:** Story 1.12 (Ground Truth Validation)
**Test Cases:**

- 50+ financial queries with expected answers
- Automated accuracy measurement
- Failure analysis reporting

---

### `scripts/` Directory

#### `scripts/setup-dev.sh`

**Purpose:** One-command local development setup
**Created:** Story 1.1
**Actions:**

- Install Python dependencies (uv sync --frozen)
- Start Docker Compose (Qdrant)
- Initialize Qdrant collection
- Validate environment

#### `scripts/init-qdrant.py`

**Purpose:** Initialize Qdrant collection with schema
**Created:** Story 1.6
**Actions:**

- Create collection with vector dimensions (1024 for Fin-E5)
- Configure distance metric (Cosine)
- Set up HNSW indexing

---

## File Creation Sequence (Story Order)

### Week 1: Story 1.1 (Project Setup)

**Files Created:**

1. `pyproject.toml`
2. `docker-compose.yml`
3. `README.md` (**BLOCKER - must create**)
4. `.env.example`
5. `.gitignore`
6. `raglite/__init__.py`
7. `raglite/shared/config.py`
8. `raglite/shared/logging.py`
9. `raglite/shared/models.py`
10. `raglite/shared/clients.py`
11. `scripts/setup-dev.sh`

### Week 1: Story 1.2-1.6 (Ingestion)

**Files Created:**
12. `raglite/ingestion/__init__.py`
13. `raglite/ingestion/pipeline.py`
14. `raglite/tests/test_ingestion.py`
15. `scripts/init-qdrant.py`

### Week 2: Story 1.7-1.8 (Retrieval)

**Files Created:**
16. `raglite/retrieval/__init__.py`
17. `raglite/retrieval/search.py`
18. `raglite/retrieval/attribution.py`
19. `raglite/tests/test_retrieval.py`

### Week 2: Story 1.9-1.10 (MCP Server)

**Files Created:**
20. `raglite/main.py` (**PRIMARY - 200 lines**)

### Week 3: Story 1.11 (LLM Synthesis)

**Files Created:**
21. `raglite/retrieval/synthesis.py`
22. `raglite/tests/test_synthesis.py`

### Week 3-4: Story 1.4 Enhancement (Optional)

**Files Created:**
23. `raglite/ingestion/contextual.py`

### Week 5: Story 1.12 (Validation)

**Files Created:**
24. `raglite/tests/ground_truth.py`
25. `scripts/run-accuracy-tests.py`

---

## Phase 3 Files (Deferred)

**NOT created in Phase 1 (Weeks 1-5):**

- `raglite/forecasting/__init__.py`
- `raglite/forecasting/hybrid.py`
- `raglite/insights/__init__.py`
- `raglite/insights/anomalies.py`
- `raglite/insights/trends.py`

**Created in Phase 3 (Weeks 9-12 or 5-8 if Phase 2 skipped)**

---

## Documentation Structure (Sharded)

### `docs/architecture/` (30 files)

**BMAD Standard Files (Required):**

- `coding-standards.md` ⭐
- `tech-stack.md` ⭐
- `source-tree.md` ⭐ (this file)

**Sharded Architecture:**

- `1-introduction-vision.md` through `9-deployment-strategy-simplified.md`
- Plus additional topic-specific files

### `docs/prd/` (15 files)

- `index.md` (table of contents)
- `epic-1-foundation-accurate-retrieval.md` through `epic-5-production-readiness-real-time-operations.md`
- Supporting files (goals, requirements, technical-assumptions, etc.)

### `docs/stories/` (Active user stories)

- `0.1.week-0-integration-spike.md` (DONE)
- Future stories added as development progresses

---

## Dependency Graph (File Dependencies)

```
main.py
├─ depends on → ingestion/pipeline.py
├─ depends on → retrieval/search.py
├─ depends on → retrieval/synthesis.py
├─ depends on → shared/config.py
├─ depends on → shared/logging.py
└─ depends on → shared/clients.py

ingestion/pipeline.py
├─ depends on → shared/config.py
├─ depends on → shared/logging.py
├─ depends on → shared/models.py
└─ optionally → ingestion/contextual.py

retrieval/search.py
├─ depends on → shared/config.py
├─ depends on → shared/logging.py
├─ depends on → shared/clients.py (Qdrant)
└─ depends on → shared/models.py

retrieval/synthesis.py
├─ depends on → shared/config.py
├─ depends on → shared/logging.py
├─ depends on → shared/clients.py (Claude API)
└─ depends on → retrieval/attribution.py

shared/* modules
└─ No internal dependencies (foundation layer)
```

**Dependency Rule:** `shared/` modules MUST NOT import from `ingestion/`, `retrieval/`, or `main.py` to avoid circular dependencies.

---

## Anti-Pattern: What NOT to Create

### ❌ DO NOT Create These Files

1. **Abstract base classes** (e.g., `base_retriever.py`)
   - Rationale: 600-line MVP doesn't need abstractions

2. **Custom wrapper modules** (e.g., `qdrant_wrapper.py`)
   - Rationale: Use SDK directly per coding standards

3. **Configuration frameworks** (e.g., `config_loader.py`)
   - Rationale: Pydantic Settings is sufficient

4. **Middleware layers** (e.g., `middleware/auth.py`)
   - Rationale: No auth in Phase 1, add in Phase 4 if needed

5. **Utility kitchen sink** (e.g., `utils.py`)
   - Rationale: Use specific modules (shared/logging.py, shared/models.py)

---

## File Creation Checklist

Before creating a new file, verify:

- [ ] File is listed in this source tree document
- [ ] File is required for current story (not future phase)
- [ ] File follows naming convention (snake_case.py)
- [ ] File location matches directory structure above
- [ ] No duplicate functionality with existing files
- [ ] No abstraction layers being added unnecessarily
- [ ] User approval obtained if deviating from structure

---

## Summary

- **Total Files (Phase 1):** ~20 Python files + 5 config/docs
- **Total Lines (Phase 1):** 600-800 lines of code
- **Total Files (Phase 3):** ~25 Python files
- **Total Lines (Phase 3):** ~1000 lines of code

**Key Principle:** SIMPLICITY FIRST. Every file must justify its existence. No files created "for future extensibility."

**Source of Truth:** This document (source-tree.md) defines EXACTLY what files exist and where.
