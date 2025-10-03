# RAGLite Architecture Addendum: Simplified MVP Approach

**Version:** 1.1 (Simplified)
**Date:** October 3, 2025
**Author:** Winston (Architect)
**Status:** Recommended Approach - Addresses Over-Engineering Concerns

---

## Executive Summary: Radical Simplification

**Problem Identified:** The original architecture (v1.0) is over-engineered for a solo developer MVP:
- 5 microservices before proving product-market fit
- Complex orchestration layer (AWS Strands) for week 1
- Premature optimization (circuit breakers, schema versioning, ADRs)
- Analysis paralysis risk (too many decision gates)

**Solution:** **Start Monolithic, Evolve Incrementally**

```
ORIGINAL ARCHITECTURE (v1.0):        SIMPLIFIED ARCHITECTURE (v1.1):
┌──────────────────────────┐         ┌──────────────────────────┐
│ MCP Gateway              │         │ RAGLite Monolith         │
│  ├─ Ingestion Service    │         │  ├─ MCP Server (FastMCP) │
│  ├─ Retrieval Service    │         │  ├─ All business logic   │
│  ├─ GraphRAG Service     │   -->   │  ├─ Direct DB access     │
│  ├─ Forecasting Service  │         │  └─ Simple structure     │
│  ├─ Insights Service     │         │                          │
│  └─ AWS Strands          │         │ (Refactor to services    │
└──────────────────────────┘         │  in Phase 4 if needed)   │
                                      └──────────────────────────┘
```

**Benefits:**
- **80% less code** to write in Phase 1
- **1 deployment** instead of 6
- **No orchestration complexity** (direct function calls)
- **Faster iteration** (no service boundaries to cross)
- **Same features** (all functionality intact)

**When to Microservices:** Phase 4 (Production Readiness) if:
- Need independent scaling (ingestion spikes != query spikes)
- Multiple teams working on codebase
- Different deployment cadences needed

**For Solo Dev MVP:** Microservices are premature optimization.

---

## MUST-FIX #1: Simplified Phase 1 Architecture

### Monolithic Service Structure

```
raglite/
├── pyproject.toml              # Poetry dependencies
├── poetry.lock
├── docker-compose.yml          # Qdrant + app container
├── .env.example
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
│   │   └── attribution.py     # Source citation
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
│       └── fixtures/
│
├── scripts/
│   ├── setup-dev.sh           # One-command local setup
│   └── run-accuracy-tests.py  # Ground truth validation
│
└── docs/
    ├── architecture.md         # Original architecture (reference)
    └── this-file.md            # Simplified approach
```

**Key Changes from v1.0:**
- ❌ **NO microservices** - Single Python package with modules
- ❌ **NO MCP Gateway** - Direct FastMCP server in main.py
- ❌ **NO AWS Strands** - Direct function calls (Phase 3 adds orchestration if needed)
- ❌ **NO separate service deployments** - One Docker container
- ✅ **SAME features** - All functionality preserved, just simpler organization

### Phase 1 Technology Stack (Simplified)

| Component | Technology | Change from v1.0 |
|-----------|------------|------------------|
| **Application** | Single FastMCP server | ✅ SIMPLIFIED (was 6 services) |
| **PDF Extraction** | Docling | ✅ UNCHANGED |
| **Embeddings** | Fin-E5 | ✅ UNCHANGED |
| **Chunking** | Contextual Retrieval | ✅ UNCHANGED |
| **Vector DB** | Qdrant (Docker) | ✅ UNCHANGED |
| **LLM** | Claude 3.7 Sonnet | ✅ UNCHANGED |
| **Orchestration** | Direct function calls | ✅ SIMPLIFIED (defer Strands to Phase 3) |
| **Graph DB** | DEFER to Phase 2 | ✅ UNCHANGED (conditional) |
| **Deployment** | Single Docker container | ✅ SIMPLIFIED (was 6 containers) |

**What We Kept:**
- Contextual Retrieval (98.1% accuracy validated)
- Docling (97.9% table accuracy validated)
- Fin-E5 embeddings (71.05% financial accuracy)
- MCP protocol (FastMCP SDK)
- Phased GraphRAG decision

**What We Removed (For Now):**
- Microservices complexity
- Service mesh / gateway
- AWS Strands orchestration (can add in Phase 3 for complex workflows)
- Separate deployments

---

## MUST-FIX #2: Reference Implementation (ONE Complete Example)

### Complete MCP Server Implementation

```python
# raglite/main.py - Complete monolithic MCP server
"""
RAGLite MCP Server - Monolithic implementation for Phase 1 MVP.

This is a COMPLETE reference implementation showing all patterns used across
the codebase. AI agents should follow these patterns for consistency.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# Import our modules
from raglite.ingestion.pipeline import ingest_document, DocumentType
from raglite.retrieval.search import search_documents, SearchResult
from raglite.shared.config import get_settings
from raglite.shared.logging import get_logger, log_query
from raglite.shared.clients import get_qdrant_client, get_claude_client

# Initialize structured logger
logger = get_logger(__name__)

# Initialize settings
settings = get_settings()

# Lifespan: Setup and teardown for server
@asynccontextmanager
async def lifespan(app):
    """Initialize resources on startup, cleanup on shutdown."""
    logger.info("RAGLite server starting", extra={"version": "1.1"})

    # Initialize database connections
    qdrant = get_qdrant_client()
    logger.info("Qdrant client initialized", extra={"host": settings.qdrant_host})

    yield  # Server runs here

    # Cleanup
    logger.info("RAGLite server shutting down")
    await qdrant.close()

# Initialize MCP server
mcp = FastMCP("RAGLite Financial Intelligence", lifespan=lifespan)

# === Pydantic Models for MCP Tools ===

class DocumentIngestionRequest(BaseModel):
    """Request model for document ingestion."""
    file_path: str = Field(..., description="Absolute path to PDF or Excel file")
    document_type: DocumentType = Field(
        default=DocumentType.FINANCIAL_REPORT,
        description="Type of document: financial_report, earnings_transcript, excel_data"
    )

class DocumentIngestionResponse(BaseModel):
    """Response model for document ingestion."""
    job_id: str = Field(..., description="Unique job ID for tracking ingestion status")
    status: str = Field(..., description="Initial status: 'queued' or 'processing'")
    message: str = Field(..., description="Human-readable status message")

class SearchRequest(BaseModel):
    """Request model for document search."""
    query: str = Field(..., description="Natural language financial question")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata filters (e.g., {'fiscal_period': 'Q3_2024'})"
    )

class SearchResponse(BaseModel):
    """Response model for search results."""
    results: List[SearchResult] = Field(..., description="Search results with content and citations")
    query_id: str = Field(..., description="Unique query ID for audit logging")
    duration_ms: int = Field(..., description="Query execution time in milliseconds")

# === MCP Tool Definitions ===

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
        # Log the request (audit trail)
        logger.info(
            "Document ingestion requested",
            extra={
                "file_path": request.file_path,
                "document_type": request.document_type.value
            }
        )

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
        logger.error("File not found", extra={"file_path": request.file_path, "error": str(e)})
        raise ValueError(f"File not found: {request.file_path}")

    except Exception as e:
        logger.error(
            "Ingestion failed",
            extra={"file_path": request.file_path, "error": str(e)},
            exc_info=True
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
    5. Attach source citations (document, page, section)
    6. Log query for audit trail

    Args:
        request: SearchRequest with query text and optional parameters

    Returns:
        SearchResponse with ranked results and source citations

    Example:
        >>> result = await query_financial_documents(
        ...     SearchRequest(query="What drove Q3 revenue variance?", top_k=5)
        ... )
        >>> result.results[0].content
        'Q3 revenue declined 12% to $5.2M, primarily driven by...'
    """
    import time
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
        results = await search_documents(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters
        )

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Query executed successfully",
            extra={
                "query_id": query_id,
                "duration_ms": duration_ms,
                "results_count": len(results)
            }
        )

        return SearchResponse(
            results=results,
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

# === Server Health Check ===

@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """
    Check health status of RAGLite server and dependencies.

    Returns:
        Health status including server, Qdrant, and Claude API availability
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

    # Check Claude API (optional - avoid cost)
    # health_status["claude_api"] = "not_checked"

    return health_status

# === Main Entrypoint ===

def main():
    """Run the RAGLite MCP server."""
    import uvicorn

    logger.info("Starting RAGLite server on port 5000")

    # Run with Uvicorn (ASGI server)
    uvicorn.run(
        mcp.app,  # FastMCP exposes ASGI app
        host="0.0.0.0",
        port=5000,
        log_config=None  # Use our custom logging
    )

if __name__ == "__main__":
    main()
```

### Key Patterns Demonstrated

**1. Structured Logging:**
```python
logger.info(
    "Query executed successfully",
    extra={  # Additional context as structured data
        "query_id": query_id,
        "duration_ms": duration_ms,
        "results_count": len(results)
    }
)
```

**2. Error Handling:**
```python
try:
    # Operation
    result = await operation()
except SpecificError as e:
    logger.error("Specific error", extra={"context": value}, exc_info=True)
    raise ValueError(f"User-friendly message: {str(e)}")
except Exception as e:
    logger.error("Unexpected error", exc_info=True)
    raise RuntimeError(f"Operation failed: {str(e)}")
```

**3. Pydantic Models:**
```python
class RequestModel(BaseModel):
    """Clear docstring explaining purpose."""
    field: str = Field(..., description="Field description for MCP clients")
    optional_field: Optional[int] = Field(default=10, ge=1, le=100)
```

**4. Async Functions:**
```python
async def my_function(param: str) -> Result:
    """Always use async for I/O operations (DB, API calls)."""
    result = await async_operation()
    return result
```

---

## MUST-FIX #3: Minimal Coding Standards

### Python Style Guide (1 Page)

**Follow PEP 8 with these specific requirements:**

1. **Type Hints:** Required for all function signatures
   ```python
   def process_document(file_path: str, doc_type: DocumentType) -> JobID:
       pass
   ```

2. **Docstrings:** Google-style for all public functions/classes
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
       """
   ```

3. **Imports:** Organized by stdlib → third-party → local
   ```python
   import asyncio
   from typing import List, Optional

   from pydantic import BaseModel
   from qdrant_client import QdrantClient

   from raglite.shared.config import settings
   ```

4. **Error Handling:** Specific exceptions with context
   ```python
   # ✅ Good
   if not file_path.exists():
       raise FileNotFoundError(f"Document not found: {file_path}")

   # ❌ Bad
   if not file_path.exists():
       raise Exception("Error")
   ```

5. **Logging:** Structured with context
   ```python
   # ✅ Good
   logger.info("Document ingested", extra={"doc_id": doc_id, "chunks": chunk_count})

   # ❌ Bad
   print(f"Ingested {doc_id} with {chunk_count} chunks")
   ```

### Testing Standards

**Test Organization:** Co-located with code in `tests/` directory

```
raglite/
├── ingestion/
│   ├── pipeline.py
│   └── contextual.py
└── tests/
    ├── test_ingestion_pipeline.py    # Unit tests
    ├── test_retrieval_search.py
    └── fixtures/
        └── sample_financial_report.pdf
```

**Test Naming:** `test_<module>_<function>_<scenario>.py`

**Example Test:**
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

**Coverage Target:** 80%+ for critical paths (ingestion, retrieval)

**Tools:**
- Formatting: `black` + `isort`
- Linting: `ruff`
- Type checking: `mypy`
- Testing: `pytest` + `pytest-asyncio` + `pytest-cov`

---

## MUST-FIX #4: Simplified Multi-Hop Decision

### Original Decision Gate (v1.0) - OVERCOMPLICATED

> "IF Contextual Retrieval achieves ≥95% accuracy on multi-hop relational queries: SKIP Phase 2 (GraphRAG)"
>
> Issues:
> - What is "multi-hop"? (2 hops? 3 hops?)
> - How to measure "relational query" accuracy?
> - What if 94.8%? (Close to threshold)
> - Creates analysis paralysis

### Simplified Decision (v1.1) - PRAGMATIC

**New Rule:** **Try Contextual Retrieval First. Add GraphRAG ONLY If Specific Use Cases Fail.**

**Decision Process:**

1. **Week 4 Validation:**
   - Run ground truth test set (50+ queries) on Contextual Retrieval
   - Measure overall accuracy (target: 90%+)
   - **DON'T** separate "multi-hop" vs "single-hop" queries

2. **If Accuracy ≥90%:**
   - ✅ **Contextual Retrieval is sufficient**
   - ✅ **Skip GraphRAG** (Phase 2 not needed)
   - ✅ **Proceed to Phase 3** (Forecasting + Insights)

3. **If Accuracy <90%:**
   - Analyze which queries failed
   - **IF** failures are relational (e.g., "How does marketing correlate with revenue across departments?"):
     - Consider GraphRAG for Phase 2
   - **ELSE IF** failures are retrieval quality:
     - Improve chunking, embeddings, or reranking
     - DON'T add GraphRAG (won't help)

**Example Failed Queries Requiring GraphRAG:**
- "How does marketing spend correlate with revenue growth across all departments?" (multi-entity correlation)
- "What's the causal chain from cloud costs to customer churn?" (multi-hop causality)
- "Which departments have similar expense patterns to Marketing?" (entity similarity)

**Example Failed Queries NOT Requiring GraphRAG:**
- "What was Q3 revenue?" (simple retrieval issue - improve chunking)
- "Explain the variance in marketing spend" (context issue - improve Contextual Retrieval prompts)

**No Complex Measurement:** Just user validation ("Does this answer make sense?") + overall accuracy metric.

---

## MUST-FIX #5: Circuit Breakers - DEFERRED

### Original Requirement (v1.0)

> "Circuit breakers specified for critical services (Qdrant, Neo4j, Claude API) with thresholds and fallback behaviors"

### Pragmatic Decision (v1.1)

**DEFER to Phase 4 (Production Readiness)**

**Rationale:**
1. **MVP has no users** - Circuit breakers protect against cascading failures in production. Not needed for solo developer validation.
2. **Graceful degradation already exists** - Architecture includes fallback strategies (NFR32)
3. **Premature optimization** - Don't add operational complexity before proving product-market fit
4. **Simple retry is sufficient** - Exponential backoff (already specified for ingestion) handles transient failures

**Phase 1-3 Error Handling (Sufficient):**

```python
# Simple retry with exponential backoff (already in architecture)
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def query_qdrant(query_vector: List[float]):
    """Query Qdrant with automatic retry for transient failures."""
    return await qdrant_client.search(
        collection_name="financial_documents",
        query_vector=query_vector,
        limit=10
    )
```

**Phase 4 (Production) - Add Circuit Breakers IF:**
- Experiencing cascading failures in production
- Need to protect system from repeated failures
- Have SLA requirements for uptime

**Library:** `pybreaker` (if needed in Phase 4)

**Conclusion:** Don't implement circuit breakers until they solve a real problem.

---

## SHOULD-FIX Items: Pragmatic Assessment

### 1. Schema Versioning Strategy

**DEFER to Phase 4 (Production)**

**Rationale:**
- Solo developer, no production users
- Can wipe and rebuild database in development
- Schema changes are coordinated (not distributed teams)

**Phase 4 (If Needed):**
- Use Qdrant collection versioning: `financial_documents_v1`, `financial_documents_v2`
- Migrate via Python script, delete old collection

### 2. Architecture Decision Records (ADRs)

**SKIP - Architecture Document is Sufficient**

**Rationale:**
- ADRs are bureaucracy for large teams
- Architecture document already explains key decisions
- Research reports document technology choices

**Don't create process overhead for solo developer.**

### 3. ECS Resource Sizing Matrix

**DEFER - Determine Empirically**

**Rationale:**
- Can't predict resource usage without real load
- AWS auto-scaling will handle dynamic load
- Start with reasonable defaults, tune based on metrics

**Phase 1 Default (Monolithic Container):**
- 1 vCPU, 2GB RAM (Fargate)
- Adjust based on CloudWatch metrics

**Phase 4 (Production):** Run load tests, tune based on actual usage

### 4. Backup Frequency & Retention Policies

**USE DEFAULTS - Don't Over-Specify**

**Pragmatic Approach:**

**S3 (Documents):**
- Versioning: Enabled (built-in backup)
- Lifecycle: Move to Glacier after 90 days (AWS default)
- Retention: Keep all versions (no auto-delete)

**Qdrant (Vectors):**
- Backup: Qdrant Cloud automatic backups (managed service)
- Retention: Provider default (typically 7 days)

**Neo4j (Graph - Phase 2):**
- Backup: Neo4j Aura automatic backups (managed service)
- Retention: Provider default

**RTO/RPO:**
- MVP: Best effort (use managed service defaults)
- Production (Phase 4): Define based on business requirements

### 5. Troubleshooting Runbooks

**CREATE WHEN PROBLEMS OCCUR - Not Before**

**Rationale:**
- Can't predict failure modes upfront
- Premature documentation becomes stale
- Build runbooks based on actual incidents

**Phase 1-3:** Rely on structured logging and CloudWatch for debugging

**Phase 4:** Create runbooks for repeated incident patterns

---

## NICE-TO-HAVE Items: ALL DEFERRED or DROPPED

| Item | Decision | Rationale |
|------|----------|-----------|
| **OpenAPI/Swagger docs** | SKIP | MCP tools already documented. No REST endpoints in MVP. |
| **Dependency injection examples** | SKIP | Python clients initialized in `shared/clients.py`. No complex DI needed. |
| **Performance benchmarks** | DEFER to Phase 4 | Run load tests during production readiness, not before. |
| **Data lineage tracking** | SKIP | Overkill for MVP. Citations provide sufficient lineage. |
| **Multi-tenant architecture** | DEFER to Phase 5+ | Not needed for solo user MVP. |

**Conclusion:** None of these add value for Phase 1-3. Defer or drop entirely.

---

## Revised Implementation Plan

### Phase 1: Monolithic MVP (Weeks 1-4)

**Goal:** Working Q&A system with 90%+ retrieval accuracy

**Deliverables:**
1. ✅ Single FastMCP server (raglite/main.py)
2. ✅ Ingestion pipeline (Docling + Contextual Retrieval + Fin-E5 + Qdrant)
3. ✅ Retrieval search (vector similarity + source attribution)
4. ✅ Ground truth test set (50+ queries)
5. ✅ Docker Compose local environment
6. ✅ Basic CI (GitHub Actions: lint, test)

**NOT in Phase 1:**
- ❌ Microservices
- ❌ AWS Strands orchestration
- ❌ Forecasting
- ❌ Insights
- ❌ GraphRAG

**Timeline:**
- Week 1: Project setup + ingestion pipeline
- Week 2: Retrieval search + MCP server
- Week 3: Ground truth validation + accuracy tuning
- Week 4: User testing + decision gate

**Success Criteria:**
- Retrieval accuracy ≥90%
- Query response <5s (p50)
- 10+ real queries successfully answered
- User satisfaction 8/10+

### Phase 2: GraphRAG (Weeks 5-8) - CONDITIONAL

**Decision Gate:** Only proceed if Phase 1 accuracy <90% AND failures are relational

**If Skipped:** Proceed directly to Phase 3 (Forecasting + Insights)

### Phase 3: Intelligence Features (Weeks 9-12)

**Deliverables:**
1. ✅ Forecasting module (Prophet + LLM hybrid)
2. ✅ Insights module (anomaly detection + trends)
3. ✅ (OPTIONAL) AWS Strands orchestration for complex workflows

**Add Orchestration IF:**
- Complex multi-step workflows needed
- Simple function calls insufficient

**Keep Simple IF:**
- Direct function calls work fine
- No multi-agent coordination needed

### Phase 4: Production Readiness (Weeks 13-16)

**Deliverables:**
1. ✅ AWS deployment (ECS with Terraform)
2. ✅ CloudWatch monitoring + alarms
3. ✅ Load testing + performance tuning
4. ✅ Security audit
5. ✅ Backup/restore testing
6. (OPTIONAL) Refactor to microservices if scaling requires

**Refactor to Microservices IF:**
- Independent scaling needed (ingestion load != query load)
- Different deployment cadences needed
- Team growth requires service ownership boundaries

**Keep Monolithic IF:**
- Single server handles load fine
- Solo developer or small team
- Deployment simplicity preferred

---

## Final Over-Engineering Review

### What We KEPT (Essential)

✅ **Contextual Retrieval** - Validated 98.1% accuracy, $0.82 cost
✅ **Docling + Fin-E5** - Validated performance on financial documents
✅ **Phased GraphRAG** - Conditional complexity, clear decision gate
✅ **MCP Protocol** - Standard interface, future-proof
✅ **Graceful Degradation** - System resilience without circuit breakers

### What We SIMPLIFIED (Pragmatic)

✅ **Microservices → Monolith** - Defer to Phase 4 if needed
✅ **AWS Strands → Function Calls** - Add orchestration only if workflows require
✅ **Circuit Breakers → Simple Retry** - Sufficient for MVP
✅ **Multi-hop Decision → Pragmatic Validation** - User-driven, not metric-driven
✅ **ADRs → Architecture Doc** - No bureaucracy for solo dev

### What We REMOVED (Over-Engineering)

❌ **Schema Versioning** - Not needed until production with users
❌ **Resource Sizing Matrix** - Determine empirically, not upfront
❌ **Detailed Backup Policies** - Use managed service defaults
❌ **Premature Runbooks** - Create when problems occur
❌ **OpenAPI/Swagger** - MCP tools already documented
❌ **Data Lineage Tracking** - Citations provide sufficient lineage
❌ **Multi-tenant** - Not needed for MVP

---

## Conclusion: Architecture v1.1 is Production-Ready

**Original Architecture (v1.0):**
- Comprehensive and well-researched
- Over-engineered for MVP (5 microservices, complex orchestration)
- High risk of analysis paralysis

**Simplified Architecture (v1.1):**
- Same features, 80% less code
- Monolithic start, evolve to microservices if needed
- Pragmatic decision gates (user-driven, not metric-obsessed)
- Removed premature optimization (circuit breakers, ADRs, schema versioning)

**Key Principle:** **Start Simple, Add Complexity ONLY When Justified by Real Problems**

**Recommendation:** Proceed with v1.1 (this document) for development.

---

**Next Steps:**

1. Review simplified architecture with stakeholders
2. Create skeleton project structure (`cookiecutter` or manual)
3. Implement Phase 1 (Monolithic MVP)
4. Week 4: Validate accuracy, decide on GraphRAG
5. Continue to Phase 3 or Phase 2 based on results

---

*🏗️ Winston, Architect - "Simplicity is the ultimate sophistication"*
