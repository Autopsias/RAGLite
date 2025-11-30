# RAGLite - API Contracts (MCP Tools)

> **Auto-generated:** 2025-11-26 | **Scan Level:** Deep

## Overview

RAGLite exposes 5 MCP tools via FastMCP for Claude clients to ingest and query financial documents.

## MCP Tools

### 1. `ingest_financial_document`

**Purpose:** Synchronous document ingestion for PDF and Excel files

**Input Modes:**

| Mode | Parameters | Use Case |
|------|------------|----------|
| **Mode 1 - Filesystem** | `doc_path` | Claude Code, Claude Desktop with Filesystem MCP |
| **Mode 2 - Base64** | `file_content`, `filename` | Programmatic/API integrations |
| **Mode 3 - URL** | `doc_url` | Claude.ai, cloud-stored documents |

**Parameters:**

```python
async def ingest_financial_document(
    doc_path: str | None = None,       # Absolute/relative file path
    file_content: str | None = None,   # Base64-encoded content (max 25MB)
    filename: str | None = None,       # Original filename (required with file_content)
    doc_url: str | None = None,        # Direct download URL
) -> DocumentMetadata
```

**Response:**

```python
class DocumentMetadata(BaseModel):
    filename: str           # Original document filename
    doc_type: str           # "PDF" or "Excel"
    ingestion_timestamp: str # ISO8601 timestamp
    page_count: int         # Number of pages/sheets
    source_path: str        # Original file path
    chunk_count: int        # Number of chunks created
```

**Example:**

```python
# Mode 1 - Filesystem path
result = await ingest_financial_document(doc_path="/path/to/Q3_Report.pdf")

# Mode 3 - URL download
result = await ingest_financial_document(
    doc_url="https://drive.google.com/uc?id=xxx&export=download"
)
```

---

### 2. `ingest_financial_document_async`

**Purpose:** Asynchronous ingestion for large documents (>50 pages)

**Parameters:** Same as `ingest_financial_document`

**Response:**

```python
class AsyncIngestionResponse(BaseModel):
    job_id: str             # Unique job identifier for polling
    status: str             # "started"
    message: str            # User-friendly message
    estimated_time_s: int | None  # Estimated completion time
```

**Example:**

```python
# Start async ingestion
response = await ingest_financial_document_async(doc_path="/path/to/large-report.pdf")
# response.job_id = "job_abc123"

# Poll for status
status = await get_ingestion_status(job_id="job_abc123")
```

---

### 3. `get_ingestion_status`

**Purpose:** Poll status of async ingestion jobs

**Parameters:**

```python
async def get_ingestion_status(job_id: str) -> IngestionJobStatus
```

**Response:**

```python
class IngestionJobStatus(BaseModel):
    job_id: str             # Job identifier
    status: str             # "pending" | "in_progress" | "completed" | "failed"
    progress: int | None    # 0-100 percentage
    result: DocumentMetadata | None  # Only when status="completed"
    error: str | None       # Only when status="failed"
    started_at: str | None  # ISO8601 timestamp
    completed_at: str | None # ISO8601 timestamp
```

---

### 4. `query_financial_documents`

**Purpose:** Natural language queries using multi-index search

**Parameters:**

```python
class QueryRequest(BaseModel):
    query: str              # Natural language query
    top_k: int = 5          # Results to return (1-50)
```

**Response:**

```python
class QueryResponse(BaseModel):
    results: list[QueryResult]  # Retrieved chunks
    query: str                  # Original query
    retrieval_time_ms: float    # Retrieval latency

class QueryResult(BaseModel):
    score: float            # Relevance score (0-1, or negative for BM25)
    text: str               # Chunk content
    source_document: str    # Source filename
    page_number: int | None # Page number
    chunk_index: int        # Chunk index
    word_count: int         # Word count
```

**Example:**

```python
result = await query_financial_documents(
    QueryRequest(query="What was the EBITDA from Portugal?", top_k=5)
)
# Returns top 5 relevant chunks with source citations
```

---

### 5. `analytical_query_financial_documents`

**Purpose:** Multi-step analytical queries with agentic workflow orchestration

**Parameters:**

```python
class AnalyticalQueryRequest(BaseModel):
    query: str              # Analytical query (max 1000 chars)
    top_k: int = 5          # Results per retrieval step
```

**Response:**

```python
class AnalyticalQueryResponse(BaseModel):
    answer: str             # Synthesized answer
    complexity: str         # "simple" | "analytical"
    workflow_metadata: dict # Execution metadata
    confidence: str         # "high" | "medium" | "low"
    limitations: list[str]  # Caveats about the answer
    reasoning_steps: list[str]  # Workflow steps taken
    sources: list[str]      # Source citations
```

**Example:**

```python
result = await analytical_query_financial_documents(
    AnalyticalQueryRequest(
        query="Calculate the year-over-year growth in revenue for Portugal operations"
    )
)
# Returns synthesized answer with reasoning steps and sources
```

---

## Internal Data Models

### Chunk Model (15 Rich Metadata Fields)

```python
class Chunk(BaseModel):
    # Core fields
    chunk_id: str           # Unique identifier
    content: str            # Text content
    metadata: DocumentMetadata
    page_number: int
    chunk_index: int
    embedding: list[float]  # 1024-dim vector

    # Document-Level Metadata (7 fields)
    document_type: str | None    # Income Statement, Balance Sheet, etc.
    reporting_period: str | None # Q1 2024, FY 2023, etc.
    time_granularity: str | None # Monthly, Quarterly, Annual
    company_name: str | None
    geographic_jurisdiction: str | None
    data_source_type: str | None # Audited, Internal, etc.
    version_date: str | None

    # Section-Level Metadata (5 fields)
    section_type: str | None     # Table, Narrative, Footnote
    metric_category: str | None  # Revenue, EBITDA, etc.
    units: str | None            # EUR, USD, EUR/ton
    department_scope: str | None

    # Table-Specific Metadata (3 fields)
    table_context: str | None    # LLM-generated description
    table_name: str | None
    statistical_summary: str | None
```

### Workflow Metrics

```python
class WorkflowMetrics(BaseModel):
    query_id: str
    query: str
    tier: str               # full_orchestration | partial_analysis | retrieval_only | epic1_fallback
    confidence: str         # high | medium | low | none
    execution_time_ms: int
    agents_invoked: list[str]
    agents_failed: list[str]
    error_type: str | None  # timeout | connection | api_failure | unexpected
    timestamp: str
```

---

## Database Schema

### PostgreSQL - `financial_tables`

```sql
CREATE TABLE financial_tables (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) NOT NULL,
    page_number INT NOT NULL,
    table_index INT NOT NULL,
    table_caption TEXT,

    -- Structured query columns
    entity VARCHAR(255),        -- Company/division name
    metric VARCHAR(255),        -- Cost type, financial measure
    period VARCHAR(100),        -- "Aug-25 YTD", "Q2 2025"
    fiscal_year INT,
    value DECIMAL(15,2),
    unit VARCHAR(50),           -- "EUR/ton", "GJ/ton"

    -- Metadata
    row_index INT,
    column_name VARCHAR(255),
    section_type VARCHAR(100) DEFAULT 'Table',
    created_at TIMESTAMP DEFAULT NOW(),
    chunk_text TEXT             -- Full context for fallback
);

-- Indexes
CREATE INDEX idx_entity ON financial_tables(entity);
CREATE INDEX idx_metric ON financial_tables(metric);
CREATE INDEX idx_period ON financial_tables(period);
CREATE INDEX idx_fiscal_year ON financial_tables(fiscal_year);
```

---

## Error Handling

| Error Class | HTTP Equivalent | Description |
|-------------|-----------------|-------------|
| `DocumentProcessingError` | 400 | Invalid document or processing failure |
| `QueryError` | 400 | Invalid query or search failure |
| `MultiIndexSearchError` | 500 | Search orchestration failure |
| `ConnectionError` | 503 | Database connection failure |
| `ValueError` | 400 | Invalid parameters |

---

*Generated by BMAD Document Project Workflow*
