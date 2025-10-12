# KEY SECTIONS TO INSERT INTO ARCHITECTURE.MD v1.1

## INSERT AFTER LINE 60 (After Change Log)

### Architecture Approach: v1.1 Simplified Recommendation

**IMPORTANT:** This architecture document presents TWO implementation approaches:

1. **v1.1 MONOLITHIC APPROACH (RECOMMENDED FOR MVP)** ⭐
   - Start with single server, modular codebase
   - 600-800 lines of code, 4-5 weeks delivery
   - Evolve to microservices in Phase 4 if scaling requires
   - **This section (immediately below) describes the recommended approach**

2. **v1.0 MICROSERVICES APPROACH (FUTURE EVOLUTION)**
   - Detailed in sections 6-8 (Microservices Architecture, Orchestration, Data Layer)
   - Use this when/if you need independent scaling or team growth
   - **Consider this a reference architecture for future growth**

**For MVP Development: Follow v1.1 Monolithic Approach (next section)**

---

## RECOMMENDED: Monolithic MVP Architecture (v1.1)

### Why Monolithic First?

**Pragmatic Reality:**
- Solo developer with Claude Code (AI pair programmer)
- 4-5 week MVP timeline
- Need to validate product-market fit before over-engineering
- Same features, 80% less code than microservices

**When to Microservices:**
- Phase 4 (Production Readiness) IF:
  - Independent scaling needed (ingestion load != query load)
  - Multiple teams require service ownership boundaries
  - Different deployment cadences required
- **Don't scale prematurely** - migrate when you have real scale problems

### Monolithic Architecture Diagram

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
│  │  - ingest_financial_document()                     │ │
│  │  - query_financial_documents()                     │ │
│  │  - forecast_kpi() [Phase 3]                        │ │
│  │  - generate_insights() [Phase 3]                   │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Business Logic Modules                            │ │
│  │  ├─ ingestion/  (PDF → chunks → embeddings)        │ │
│  │  ├─ retrieval/  (vector search + synthesis)        │ │
│  │  ├─ forecasting/ [Phase 3]                         │ │
│  │  └─ insights/    [Phase 3]                         │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Shared Utilities                                  │ │
│  │  ├─ config.py    (settings, env vars)              │ │
│  │  ├─ logging.py   (structured logging)              │ │
│  │  ├─ models.py    (Pydantic data models)            │ │
│  │  └─ clients.py   (Qdrant, Claude API)              │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Data Layer                                              │
│  ├─ Qdrant (Vector DB) - Docker container               │
│  ├─ S3/Local Storage (Documents)                         │
│  └─ Neo4j [Phase 2 - conditional]                        │
└──────────────────────────────────────────────────────────┘
```

### Repository Structure (Monolithic)

```
raglite/
├── pyproject.toml              # Poetry dependencies
├── poetry.lock
├── docker-compose.yml          # Qdrant + app container
├── .env.example
├── README.md
│
├── raglite/                    # Single Python package
│   ├── __init__.py
│   ├── main.py                # MCP server entrypoint (FastMCP)
│   │
│   ├── ingestion/             # Ingestion module
│   │   ├── __init__.py
│   │   ├── pipeline.py        # Docling + chunking + embedding
│   │   └── contextual.py      # Contextual Retrieval chunking
│   │
│   ├── retrieval/             # Retrieval module
│   │   ├── __init__.py
│   │   ├── search.py          # Qdrant vector search
│   │   ├── synthesis.py       # LLM answer synthesis
│   │   └─ attribution.py      # Source citation
│   │
│   ├── forecasting/           # Forecasting module (Phase 3)
│   │   ├── __init__.py
│   │   └── hybrid.py          # Prophet + LLM
│   │
│   ├── insights/              # Insights module (Phase 3)
│   │   ├── __init__.py
│   │   ├── anomalies.py
│   │   └── trends.py
│   │
│   ├── shared/                # Shared utilities
│   │   ├── __init__.py
│   │   ├── config.py          # Settings (Pydantic BaseSettings)
│   │   ├── logging.py         # Structured logging setup
│   │   ├── models.py          # Pydantic data models
│   │   └── clients.py         # Qdrant, Claude API clients
│   │
│   └── tests/                 # Tests co-located with code
│       ├── test_ingestion.py
│       ├── test_retrieval.py
│       ├── test_synthesis.py
│       ├── ground_truth.py    # Accuracy validation (50+ queries)
│       └── fixtures/
│           └── sample_financial_report.pdf
│
├── scripts/
│   ├── setup-dev.sh           # One-command local setup
│   └── run-accuracy-tests.py  # Ground truth validation
│
└── docs/
    ├── architecture.md         # This document
    ├── prd.md                 # Product requirements
    └── front-end-spec.md      # MCP response format spec
```

**File Count:** ~15 Python files (vs 30+ for microservices)
**Estimated Lines of Code:** 600-800 lines (vs 3000+ for microservices)

---

## INSERT AFTER SECTION 5 (Technology Stack)

## Reference Implementation

### Complete MCP Server (raglite/main.py)

This is the COMPLETE reference implementation showing all patterns used in RAGLite. AI agents should follow these patterns for consistency across all modules.

```python
# raglite/main.py - Complete monolithic MCP server
"""
RAGLite MCP Server - Monolithic implementation for Phase 1-3.

This is a COMPLETE reference implementation showing all patterns:
- FastMCP server setup with lifespan management
- Pydantic model definitions for MCP tools
- Structured logging with context
- Error handling with specific exceptions
- Type hints for all functions
- Google-style docstrings

AI agents should copy these patterns when implementing other modules.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# Import our modules
from raglite.ingestion.pipeline import ingest_document, DocumentType
from raglite.retrieval.search import search_documents, SearchResult
from raglite.retrieval.synthesis import synthesize_answer
from raglite.shared.config import get_settings
from raglite.shared.logging import get_logger, log_query
from raglite.shared.clients import get_qdrant_client, get_claude_client

# Initialize structured logger
logger = get_logger(__name__)

# Initialize settings (loads from .env or environment)
settings = get_settings()

# ============================================================================
# SERVER LIFECYCLE MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app):
    """
    Initialize resources on startup, cleanup on shutdown.

    This pattern ensures:
    - Database connections are established before handling requests
    - Resources are properly cleaned up on shutdown
    - Startup/shutdown events are logged for debugging
    """
    logger.info("RAGLite server starting", extra={"version": "1.1"})

    # Initialize database connections
    qdrant = get_qdrant_client()
    logger.info("Qdrant client initialized", extra={"host": settings.qdrant_host})

    # Validate Qdrant collection exists
    try:
        collections = await qdrant.get_collections()
        logger.info(
            "Qdrant collections found",
            extra={"collections": [c.name for c in collections.collections]}
        )
    except Exception as e:
        logger.error("Failed to connect to Qdrant", extra={"error": str(e)})
        raise

    yield  # Server runs here (handles requests)

    # Cleanup on shutdown
    logger.info("RAGLite server shutting down")
    await qdrant.close()

# Initialize MCP server
mcp = FastMCP("RAGLite Financial Intelligence", lifespan=lifespan)

# ============================================================================
# PYDANTIC MODELS (MCP Tool Schemas)
# ============================================================================

class DocumentIngestionRequest(BaseModel):
    """
    Request model for document ingestion.

    Pydantic models provide:
    - Type validation (FastMCP requirement)
    - Auto-generated MCP tool schemas
    - Clear documentation for MCP clients
    """
    file_path: str = Field(
        ...,
        description="Absolute path to PDF or Excel file",
        examples=["/data/Q3_2024_Financial_Report.pdf"]
    )
    document_type: DocumentType = Field(
        default=DocumentType.FINANCIAL_REPORT,
        description="Type of document: financial_report, earnings_transcript, excel_data"
    )

class DocumentIngestionResponse(BaseModel):
    """Response model for document ingestion."""
    job_id: str = Field(..., description="Unique job ID for tracking ingestion status")
    status: str = Field(..., description="Initial status: 'queued' or 'processing'")
    message: str = Field(..., description="Human-readable status message")
    chunks_count: Optional[int] = Field(
        default=None,
        description="Number of chunks created (if processing complete)"
    )

class SearchRequest(BaseModel):
    """Request model for document search."""
    query: str = Field(
        ...,
        description="Natural language financial question",
        min_length=1,
        examples=["What drove Q3 revenue variance?"]
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of results to return (1-50)"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata filters (e.g., {'fiscal_period': 'Q3_2024'})"
    )
    include_synthesis: bool = Field(
        default=True,
        description="Whether to synthesize LLM answer from chunks (True) or return raw chunks (False)"
    )

class SearchResponse(BaseModel):
    """Response model for search results."""
    answer: Optional[str] = Field(
        default=None,
        description="Synthesized answer with source citations (if include_synthesis=True)"
    )
    chunks: List[SearchResult] = Field(
        ...,
        description="Retrieved chunks with content and metadata"
    )
    query_id: str = Field(..., description="Unique query ID for audit logging")
    duration_ms: int = Field(..., description="Query execution time in milliseconds")

# ============================================================================
# MCP TOOL DEFINITIONS
# ============================================================================

@mcp.tool()
async def ingest_financial_document(
    request: DocumentIngestionRequest
) -> DocumentIngestionResponse:
    """
    Ingest a financial document (PDF or Excel) into RAGLite knowledge base.

    Process:
    1. Validate file path exists
    2. Extract content using Docling (PDF) or openpyxl (Excel)
    3. Apply Contextual Retrieval chunking (LLM-generated context per chunk)
    4. Generate Fin-E5 embeddings
    5. Store in Qdrant vector database

    Args:
        request: DocumentIngestionRequest with file_path and document_type

    Returns:
        DocumentIngestionResponse with job_id for tracking

    Raises:
        ValueError: If file_path doesn't exist or is unsupported format
        RuntimeError: If ingestion pipeline fails

    Example:
        >>> result = await ingest_financial_document(
        ...     DocumentIngestionRequest(
        ...         file_path="/data/Q3_2024_Report.pdf",
        ...         document_type=DocumentType.FINANCIAL_REPORT
        ...     )
        ... )
        >>> result.job_id
        'job-abc123'
    """
    try:
        # Log the request (audit trail per NFR14)
        logger.info(
            "Document ingestion requested",
            extra={
                "file_path": request.file_path,
                "document_type": request.document_type.value
            }
        )

        # Validate file exists
        file_path = Path(request.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {request.file_path}")

        # Call ingestion pipeline (from raglite.ingestion.pipeline)
        job_id = await ingest_document(
            file_path=request.file_path,
            doc_type=request.document_type
        )

        logger.info("Ingestion job created", extra={"job_id": job_id})

        return DocumentIngestionResponse(
            job_id=job_id,
            status="processing",
            message=f"Document ingestion started. Job ID: {job_id}"
        )

    except FileNotFoundError as e:
        logger.error(
            "File not found",
            extra={"file_path": request.file_path, "error": str(e)}
        )
        raise ValueError(f"File not found: {request.file_path}")

    except Exception as e:
        logger.error(
            "Ingestion failed",
            extra={"file_path": request.file_path, "error": str(e)},
            exc_info=True  # Include stack trace in logs
        )
        raise RuntimeError(f"Ingestion failed: {str(e)}")

@mcp.tool()
async def query_financial_documents(
    request: SearchRequest
) -> SearchResponse:
    """
    Search financial documents using natural language query.

    Process:
    1. Generate query embedding using Fin-E5
    2. Perform vector similarity search in Qdrant
    3. Apply Contextual Retrieval enhancement
    4. Rank results by relevance
    5. (Optional) Synthesize LLM answer from top chunks
    6. Attach source citations (document, page, section)
    7. Log query for audit trail (NFR14)

    Args:
        request: SearchRequest with query text and optional parameters

    Returns:
        SearchResponse with results and optional synthesized answer

    Example:
        >>> result = await query_financial_documents(
        ...     SearchRequest(query="What drove Q3 revenue variance?", top_k=5)
        ... )
        >>> result.answer
        'Q3 revenue declined 12% to $5.2M, primarily driven by...'
    """
    start_time = time.time()

    try:
        # Generate unique query ID for tracking
        query_id = f"qry-{int(time.time() * 1000)}"

        # Log query (audit trail per NFR14)
        log_query(
            query_id=query_id,
            query_text=request.query,
            user_id="default",  # Update when multi-user supported
            filters=request.filters
        )

        # Perform semantic search
        chunks = await search_documents(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters
        )

        # Optionally synthesize LLM answer
        answer = None
        if request.include_synthesis and chunks:
            answer = await synthesize_answer(
                query=request.query,
                chunks=chunks
            )

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Query executed successfully",
            extra={
                "query_id": query_id,
                "duration_ms": duration_ms,
                "chunks_count": len(chunks),
                "synthesized": request.include_synthesis
            }
        )

        return SearchResponse(
            answer=answer,
            chunks=chunks,
            query_id=query_id,
            duration_ms=duration_ms
        )

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "Query failed",
            extra={
                "query": request.query,
                "duration_ms": duration_ms,
                "error": str(e)
            },
            exc_info=True
        )
        raise RuntimeError(f"Search failed: {str(e)}")

@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """
    Check health status of RAGLite server and dependencies.

    Returns:
        Health status including server, Qdrant, and dependency availability

    Example:
        >>> status = await health_check()
        >>> status["server"]
        'healthy'
    """
    health_status = {
        "server": "healthy",
        "timestamp": time.time(),
        "version": "1.1"
    }

    # Check Qdrant connection
    try:
        qdrant = get_qdrant_client()
        collections = await qdrant.get_collections()
        health_status["qdrant"] = "healthy"
        health_status["collections"] = [c.name for c in collections.collections]
    except Exception as e:
        health_status["qdrant"] = f"unhealthy: {str(e)}"
        logger.warning("Qdrant health check failed", extra={"error": str(e)})

    return health_status

# ============================================================================
# SERVER ENTRYPOINT
# ============================================================================

def main():
    """
    Run the RAGLite MCP server.

    Usage:
        python -m raglite.main

    Environment Variables:
        QDRANT_HOST: Qdrant server host (default: localhost)
        QDRANT_PORT: Qdrant server port (default: 6333)
        CLAUDE_API_KEY: Anthropic API key (required)
    """
    import uvicorn

    logger.info("Starting RAGLite server", extra={"port": 5000})

    # Run with Uvicorn (ASGI server)
    uvicorn.run(
        mcp.app,  # FastMCP exposes ASGI app
        host="0.0.0.0",
        port=5000,
        log_config=None  # Use our custom logging configuration
    )

if __name__ == "__main__":
    main()
```

### Key Patterns Demonstrated

**1. Structured Logging Pattern:**
```python
# Always use extra={} for structured context
logger.info(
    "Query executed successfully",
    extra={  # Additional context as structured data (JSON-serializable)
        "query_id": query_id,
        "duration_ms": duration_ms,
        "results_count": len(results)
    }
)
```

**2. Error Handling Pattern:**
```python
try:
    # Operation that might fail
    result = await risky_operation()
except SpecificError as e:
    # Log with context, re-raise with user-friendly message
    logger.error("Operation failed", extra={"context": value}, exc_info=True)
    raise ValueError(f"User-friendly message: {str(e)}")
except Exception as e:
    # Catch-all for unexpected errors
    logger.error("Unexpected error", exc_info=True)
    raise RuntimeError(f"Operation failed: {str(e)}")
```

**3. Pydantic Model Pattern:**
```python
class RequestModel(BaseModel):
    """Clear docstring explaining purpose."""
    required_field: str = Field(
        ...,  # ... means required
        description="Field description for MCP clients",
        examples=["example value"]
    )
    optional_field: Optional[int] = Field(
        default=10,
        ge=1,  # Greater than or equal to 1
        le=100,  # Less than or equal to 100
        description="Optional field with constraints"
    )
```

**4. Async Function Pattern:**
```python
async def my_function(param: str) -> Result:
    """
    Always use async for I/O operations (DB, API calls, file I/O).

    Args:
        param: Description

    Returns:
        Description

    Raises:
        ErrorType: When this error occurs
    """
    result = await async_io_operation()
    return result
```

**5. Type Hints Pattern:**
```python
# Required for all function signatures
from typing import List, Optional, Dict, Any

def process_data(
    input_data: List[str],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, int]:
    """Always include type hints for clarity and IDE support."""
    pass
```

---

## Coding Standards

### Python Style Guide

RAGLite follows **PEP 8** with these specific requirements:

#### 1. Type Hints (Required)
```python
# ✅ Good - Type hints on all function signatures
def process_document(file_path: str, doc_type: DocumentType) -> JobID:
    pass

# ❌ Bad - No type hints
def process_document(file_path, doc_type):
    pass
```

#### 2. Docstrings (Google Style, Required for Public Functions)
```python
def search_documents(query: str, top_k: int = 10) -> List[SearchResult]:
    """
    Search financial documents using semantic similarity.

    Args:
        query: Natural language financial question
        top_k: Number of results to return (default: 10)

    Returns:
        List of SearchResult objects with content and citations

    Raises:
        ValueError: If query is empty
        RuntimeError: If Qdrant connection fails

    Example:
        >>> results = search_documents("What was Q3 revenue?")
        >>> len(results)
        10
    """
    pass
```

#### 3. Import Organization
```python
# Standard library imports
import asyncio
import time
from pathlib import Path
from typing import List, Optional, Dict

# Third-party imports
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

# Local application imports
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
```

#### 4. Error Handling (Specific Exceptions)
```python
# ✅ Good - Specific exception with context
if not file_path.exists():
    raise FileNotFoundError(f"Document not found: {file_path}")

# ❌ Bad - Generic exception with no context
if not file_path.exists():
    raise Exception("Error")
```

#### 5. Logging (Structured with Context)
```python
# ✅ Good - Structured logging
logger.info("Document ingested", extra={"doc_id": doc_id, "chunks": chunk_count})

# ❌ Bad - Unstructured print
print(f"Ingested {doc_id} with {chunk_count} chunks")
```

#### 6. Constants (Uppercase)
```python
# ✅ Good
MAX_CHUNK_SIZE = 500
DEFAULT_TOP_K = 10

# ❌ Bad
max_chunk_size = 500
```

#### 7. Function Naming (Verb phrases for functions)
```python
# ✅ Good
def ingest_document(file_path: str) -> JobID:
    pass

def calculate_similarity(query: str, doc: str) -> float:
    pass

# ❌ Bad
def document(file_path: str):  # Noun, not verb
    pass
```

### Testing Standards

#### Test Organization
Co-located with code in `raglite/tests/` directory:

```
raglite/
├── ingestion/
│   ├── pipeline.py
│   └── contextual.py
└── tests/
    ├── test_ingestion_pipeline.py    # Unit tests for ingestion
    ├── test_retrieval_search.py       # Unit tests for retrieval
    ├── ground_truth.py                # Accuracy validation (50+ queries)
    └── fixtures/
        └── sample_financial_report.pdf
```

#### Test Naming Convention
`test_<module>_<function>_<scenario>.py`

#### Test Example
```python
# raglite/tests/test_ingestion_pipeline.py
import pytest
from pathlib import Path
from raglite.ingestion.pipeline import ingest_document, DocumentType

@pytest.fixture
def sample_pdf_path():
    """Fixture providing path to test PDF."""
    return Path(__file__).parent / "fixtures" / "sample_financial_report.pdf"

@pytest.mark.asyncio
async def test_ingest_document_success(sample_pdf_path):
    """Test successful PDF ingestion with valid file."""
    job_id = await ingest_document(
        file_path=str(sample_pdf_path),
        doc_type=DocumentType.FINANCIAL_REPORT
    )

    # Assertions
    assert job_id.startswith("job-")
    assert len(job_id) > 8

@pytest.mark.asyncio
async def test_ingest_document_file_not_found():
    """Test ingestion fails gracefully when file doesn't exist."""
    with pytest.raises(FileNotFoundError, match="not found"):
        await ingest_document(
            file_path="/nonexistent/file.pdf",
            doc_type=DocumentType.FINANCIAL_REPORT
        )
```

#### Coverage Target
- **Phase 1-3 (MVP):** 50%+ for critical paths (ingestion, retrieval)
- **Phase 4 (Production):** 80%+ overall coverage

#### Testing Tools
- **Test Framework:** `pytest`
- **Async Testing:** `pytest-asyncio`
- **Coverage:** `pytest-cov` (Phase 4)
- **Mocking:** `pytest-mock` or `unittest.mock`

#### Running Tests
```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest raglite/tests/test_ingestion_pipeline.py

# Run with coverage (Phase 4)
poetry run pytest --cov=raglite --cov-report=html
```

### Code Formatting & Linting

#### Auto-Formatting (Required Before Commit)
```bash
# Format code with Black
poetry run black raglite/

# Sort imports with isort
poetry run isort raglite/
```

#### Linting (Fix Issues Before PR)
```bash
# Lint with ruff
poetry run ruff check raglite/

# Type check with mypy
poetry run mypy raglite/
```

#### Pre-Commit Hook (Phase 4)
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black

  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
```

---

## INSERT BEFORE SECTION 9 (Replace "Phased Implementation Strategy")

## Phased Implementation Strategy (v1.1 Simplified)

### Overview

RAGLite follows a **simplified phased approach** optimized for solo developer with AI pair programming (Claude Code). Focus: **Ship fast, validate early, iterate based on real feedback.**

**Key Principle:** Start with monolithic MVP, add complexity ONLY when proven necessary by real user problems.

### Phase 1: Monolithic MVP with Contextual Retrieval (Weeks 1-4)

**Goal:** Working Q&A system with 90%+ retrieval accuracy using Contextual Retrieval

**Architecture:** Monolithic FastMCP server (9 files, 600-800 lines total)

**Scope:**

**Week 1: Ingestion Pipeline**
- ✅ PDF extraction (Docling)
- ✅ Simple chunking (500 words, 50 overlap) - NO Contextual Retrieval yet
- ✅ Fin-E5 embedding generation
- ✅ Qdrant storage
- ✅ Basic MCP server setup

**Deliverable:** `ingest_financial_document()` tool works with test PDF

**Week 2: Retrieval & Search**
- ✅ Vector similarity search (Qdrant)
- ✅ Source attribution (document, page, section)
- ✅ Basic result ranking
- ✅ MCP search tool

**Deliverable:** `query_financial_documents()` returns relevant chunks with citations

**Week 3: LLM Synthesis**
- ✅ Claude API integration
- ✅ Answer synthesis from chunks
- ✅ Citation formatting
- ✅ **OPTIONAL:** Contextual Retrieval (upgrade chunking if time permits)

**Deliverable:** Natural language answers with source citations

**Week 4: Accuracy Validation**
- ✅ Ground truth test set (20-50 queries with expected answers)
- ✅ Manual accuracy validation
- ✅ Performance measurement (<10s query response)
- ✅ User testing with real financial documents

**Deliverable:** Validation report + decision on Phase 2

**Success Criteria:**
- ✅ Can ingest 5 financial PDFs successfully
- ✅ 80%+ of test queries return useful answers (manual judgment)
- ✅ Query response time <10 seconds (p50)
- ✅ All answers include source citations

**Decision Gate (End of Week 4):**

**IF Success Criteria Met:**
- ✅ MVP SUCCESS
- ✅ SKIP Phase 2 (GraphRAG) - proceed to Phase 3 (Forecasting)
- ✅ **OPTIONAL:** Add Contextual Retrieval if not yet implemented

**IF Accuracy <80%:**
- Analyze failure modes:
  - **IF** failures are relational queries (multi-entity correlations) → Consider Phase 2 (GraphRAG)
  - **ELSE** failures are retrieval quality → Improve chunking/embeddings → Retry Week 4

**Technologies:**
- FastMCP, Docling, Fin-E5, Qdrant, Claude 3.7 Sonnet
- Docker Compose (Qdrant + app)
- pytest for basic testing

**NOT in Phase 1:**
- ❌ Microservices architecture
- ❌ AWS Strands orchestration
- ❌ GraphRAG
- ❌ Forecasting
- ❌ Insights
- ❌ Excel support (PDFs only)
- ❌ Production deployment (local Docker only)

---

### Phase 2: GraphRAG Integration (Weeks 5-8) - CONDITIONAL

**⚠️ ONLY IMPLEMENT IF PHASE 1 DECISION GATE TRIGGERS**

**Goal:** Add multi-hop relational reasoning to close accuracy gap

**Scope:**

**Week 5: Graph Construction**
- ✅ Entity extraction (Claude API)
- ✅ Relationship extraction
- ✅ Neo4j schema design
- ✅ Graph construction pipeline

**Week 6: Agentic Navigation**
- ✅ Community detection (Louvain algorithm)
- ✅ Graph traversal logic
- ✅ Multi-hop query decomposition

**Week 7: Integration**
- ✅ Integrate graph search with vector search
- ✅ Hybrid retrieval (vector + graph)
- ✅ Update synthesis to use both sources

**Week 8: Validation**
- ✅ Multi-hop query test set (15+ queries)
- ✅ Accuracy validation (target: 90%+)
- ✅ Performance tuning

**Success Criteria:**
- ✅ Multi-hop query accuracy ≥90% (combined vector + graph)
- ✅ Graph construction <10 min per 100 pages
- ✅ Query response <15s (p95) including graph traversal

**Cost Validation:**
- Graph construction: ~$9 for 100 documents
- Query cost: ~$20/month for 1000 queries

**Technologies Added:**
- Neo4j (Docker or Aura managed)
- Community detection libraries

**Deliverable:** Enhanced RAG system with proven multi-hop capability

---

### Phase 3: Intelligence Features (Weeks 9-12 or Weeks 5-8 if Phase 2 skipped)

**Goal:** Add forecasting and proactive insights

**Scope:**

**Week 9 (or 5): Forecasting Module**
- ✅ Time-series data extraction from documents
- ✅ Prophet baseline forecasting
- ✅ LLM forecast adjustment
- ✅ MCP tool: `forecast_kpi()`

**Week 10 (or 6): Insights Module**
- ✅ Anomaly detection (statistical)
- ✅ Trend analysis
- ✅ LLM strategic recommendations
- ✅ MCP tool: `generate_insights()`

**Week 11 (or 7): Orchestration (OPTIONAL)**
- ✅ **IF** complex workflows needed: Add AWS Strands for multi-agent coordination
- ✅ **ELSE** keep direct function calls (simpler)

**Week 12 (or 8): Integration & Polish**
- ✅ End-to-end testing with all features
- ✅ Documentation updates
- ✅ User acceptance testing

**Success Criteria:**
- ✅ Forecast accuracy ±10% (target: ±15%)
- ✅ 75%+ of insights rated useful/actionable
- ✅ All features work together seamlessly

**Technologies Added:**
- Prophet (forecasting)
- AWS Strands (if needed for orchestration)

**Deliverable:** Complete RAGLite with all intelligence features

---

### Phase 4: Production Readiness (Weeks 13-16)

**Goal:** Deploy to AWS, add monitoring, optimize performance

**Scope:**

**Week 13: AWS Deployment**
- ✅ Terraform infrastructure (ECS, VPC, ALB)
- ✅ S3 document storage
- ✅ Managed Qdrant (or OpenSearch)
- ✅ Secrets Manager

**Week 14: Monitoring & Observability**
- ✅ CloudWatch metrics & alarms
- ✅ Structured logging (already implemented)
- ✅ Performance dashboards
- ✅ Audit trail validation

**Week 15: Performance & Scalability**
- ✅ Load testing (10+ concurrent users)
- ✅ Auto-scaling configuration
- ✅ Performance optimization
- ✅ Cost analysis

**Week 16: Security & Reliability**
- ✅ Security audit
- ✅ Backup/restore testing
- ✅ Disaster recovery procedures
- ✅ **OPTIONAL:** Refactor to microservices IF scaling requires

**Success Criteria:**
- ✅ 99%+ uptime
- ✅ <5s query response under load (p50)
- ✅ Successful multi-user testing (10+ users)
- ✅ Security audit passed

**Microservices Decision (End of Week 16):**

**Refactor to Microservices IF:**
- Independent scaling needed (ingestion spikes != query spikes)
- Multiple teams working on codebase
- Different deployment cadences needed

**Keep Monolithic IF:**
- Single server handles load fine
- Solo developer or small team
- Deployment simplicity preferred

**Deliverable:** Production-ready system for team rollout

---

### Timeline Summary

| Phase | Duration | Cumulative | Deliverable |
|-------|----------|------------|-------------|
| **Phase 1: MVP** | 4 weeks | 4 weeks | Q&A system with 80%+ accuracy |
| **Phase 2: GraphRAG** | 4 weeks (conditional) | 8 weeks | Multi-hop reasoning capability |
| **Phase 3: Intelligence** | 4 weeks | 8-12 weeks | Forecasting + Insights |
| **Phase 4: Production** | 4 weeks | 12-16 weeks | AWS deployment + monitoring |

**Fastest Path (If GraphRAG Skipped):** 12 weeks (Phase 1 + 3 + 4)
**Full Path (If GraphRAG Needed):** 16 weeks (All phases)

---

## INSERT AT END (Before existing Testing Strategy section)

## Evolution Path: Monolithic → Microservices

### When to Refactor

**Keep Monolithic IF:**
- ✅ Single server handles all load
- ✅ Solo developer or small team (2-3 people)
- ✅ Simple deployment preferred
- ✅ No independent scaling requirements

**Refactor to Microservices IF:**
- ⚠️ Ingestion load spikes != query load (need independent scaling)
- ⚠️ Multiple teams need service ownership boundaries
- ⚠️ Different deployment cadences needed (deploy ingestion without affecting queries)
- ⚠️ Team size >5 engineers

**Rule of Thumb:** Don't refactor until you have a REAL scaling problem, not a hypothetical one.

### Refactoring Strategy

**Step 1: Extract First Service (Ingestion)**
```
Monolithic Server
    ├─ Ingestion module → Extract to Ingestion Service (first)
    ├─ Retrieval module
    ├─ Forecasting module
    └─ Insights module
```

**Why Ingestion First:**
- Independent workload (batch processing)
- Can scale independently
- Lowest coupling with other modules

**Step 2: Extract Second Service (Forecasting/Insights)**
```
Remaining Monolith         Ingestion Service
    ├─ Retrieval module
    ├─ Forecasting module → Extract to Forecast/Insights Service
    └─ Insights module
```

**Step 3: Extract Final Services**
```
Core Retrieval Service     Ingestion Service     Forecast/Insights Service
```

**Step 4: Add Orchestration (AWS Strands)**
```
MCP Gateway → AWS Strands → All Services
```

### Migration Timeline

**Estimate:** 2-3 weeks per service extraction

**Total Refactor:** 6-10 weeks to go from monolith to full microservices

**Cost:** Opportunity cost of 6-10 weeks NOT building new features

**Decision:** Only pay this cost if you have proven scale problems.

---

## Deployment Strategy (Simplified for v1.1)

### Phase 1-3: Local Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  # Qdrant vector database
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"    # HTTP
      - "6334:6334"    # gRPC
    volumes:
      - ./qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    networks:
      - raglite-network

  # RAGLite monolithic server
  raglite:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "5000:5000"    # MCP server
    volumes:
      - ./data:/data   # Document storage
      - ./.env:/app/.env
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    depends_on:
      - qdrant
    networks:
      - raglite-network

networks:
  raglite-network:
    driver: bridge
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY raglite/ ./raglite/

# Expose MCP server port
EXPOSE 5000

# Run server
CMD ["python", "-m", "raglite.main"]
```

**Setup Script:**
```bash
#!/bin/bash
# scripts/setup-dev.sh

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker required but not installed."; exit 1; }
command -v poetry >/dev/null 2>&1 || { echo "Poetry required but not installed."; exit 1; }

# Install dependencies
echo "Installing Python dependencies..."
poetry install

# Copy environment template
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file - please add your CLAUDE_API_KEY"
    exit 1
fi

# Start Docker Compose
echo "Starting Qdrant and RAGLite..."
docker-compose up -d

# Wait for Qdrant to be ready
echo "Waiting for Qdrant to start..."
sleep 5

# Initialize Qdrant collection
echo "Initializing Qdrant collection..."
poetry run python scripts/init-qdrant.py

echo "Setup complete! RAGLite is running on http://localhost:5000"
```

### Phase 4: AWS Production Deployment

**See sections 10-13 in original architecture for detailed AWS deployment.**

**Simplified Deployment:**
- Use ECS Fargate with 1 task (monolithic container)
- Managed Qdrant Cloud (or OpenSearch)
- S3 for document storage
- CloudWatch for monitoring

**Cost (Phase 4 Monolithic):**
- ECS Fargate: ~$50/month (1 task, 1 vCPU, 2GB RAM)
- Qdrant Cloud: ~$50-100/month (4GB RAM tier)
- S3 + CloudWatch: ~$15/month
- **Total:** ~$115-165/month (vs $200-270 for microservices)
