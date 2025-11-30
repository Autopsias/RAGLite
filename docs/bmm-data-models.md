# RAGLite - Data Models

> **Auto-generated:** 2025-11-26 | **Scan Level:** Deep

## Overview

RAGLite uses Pydantic models for type-safe data validation across the application. This document covers all core data models.

## Core Models (`raglite/shared/models.py`)

### DocumentMetadata

Tracks document provenance and ingestion details.

```python
class DocumentMetadata(BaseModel):
    filename: str           # Original document filename
    doc_type: str           # "PDF" or "Excel"
    ingestion_timestamp: str # ISO8601 timestamp
    page_count: int = 0     # Number of pages/sheets
    source_path: str = ""   # Original file path
    chunk_count: int = 0    # Number of chunks created
```

### ExtractedMetadata

LLM-extracted business context metadata (15 rich fields).

```python
class ExtractedMetadata(BaseModel):
    # Document-Level Metadata (7 fields)
    document_type: str | None       # Income Statement, Balance Sheet, etc.
    reporting_period: str | None    # Q1 2024, Aug-25 YTD, FY 2023
    time_granularity: str | None    # Daily, Weekly, Monthly, Quarterly, YTD, Annual
    company_name: str | None        # Portugal Cement, CIMPOR, etc.
    geographic_jurisdiction: str | None  # Portugal, EU, APAC, Americas
    data_source_type: str | None    # Audited, Internal Report, Regulatory Filing
    version_date: str | None        # 2025-08-15, 2024-Q3-Final

    # Section-Level Metadata (5 fields)
    section_type: str | None        # Narrative, Table, Footnote, Chart Caption
    metric_category: str | None     # Revenue, EBITDA, Operating Expenses, etc.
    units: str | None               # EUR, USD, GBP, EUR/ton, Percentage
    department_scope: str | None    # Operations, Finance, Production, Sales

    # Table-Specific Metadata (3 fields)
    table_context: str | None       # LLM-generated description
    table_name: str | None          # Table title
    statistical_summary: str | None # Mean, StdDev, Min, Max, Trend
```

### Chunk

Document chunk with content, embedding, and metadata.

```python
class Chunk(BaseModel):
    chunk_id: str           # Unique identifier
    content: str            # Chunk text content
    metadata: DocumentMetadata
    page_number: int = 0
    chunk_index: int = 0
    embedding: list[float] = []  # 1024-dim vector
    parent_chunk_id: str | None = None
    word_count: int = 0

    # All 15 ExtractedMetadata fields replicated here
    document_type: str | None = None
    reporting_period: str | None = None
    # ... (all 15 fields)
```

### SearchResult / QueryResult

Search results with relevance scoring.

```python
class SearchResult(BaseModel):
    score: float            # Similarity score (0-1)
    chunk: Chunk            # Retrieved chunk
    source_citation: str = ""

class QueryResult(BaseModel):
    score: float            # Relevance score
    text: str               # Chunk content
    source_document: str    # Source filename
    page_number: int | None
    chunk_index: int
    word_count: int
```

### Query Request/Response

```python
class QueryRequest(BaseModel):
    query: str              # Natural language query
    top_k: int = 5          # Range: 1-50

class QueryResponse(BaseModel):
    results: list[QueryResult]
    query: str
    retrieval_time_ms: float
```

### Analytical Query Request/Response

```python
class AnalyticalQueryRequest(BaseModel):
    query: str              # Max 1000 characters
    top_k: int = 5

class AnalyticalQueryResponse(BaseModel):
    answer: str             # Synthesized answer
    complexity: str         # "simple" or "analytical"
    workflow_metadata: dict # Execution details
    confidence: str         # "high", "medium", "low"
    limitations: list[str] = []
    reasoning_steps: list[str] = []
    sources: list[str] = []
```

### WorkflowMetrics

Workflow execution metrics for monitoring.

```python
class WorkflowMetrics(BaseModel):
    query_id: str
    query: str
    tier: str               # full_orchestration | partial_analysis | retrieval_only | epic1_fallback
    confidence: str         # high | medium | low | none
    execution_time_ms: int
    agents_invoked: list[str] = []
    agents_failed: list[str] = []
    error_type: str | None = None
    timestamp: str
```

### Time-Series Models (Epic 4)

```python
class TimeSeriesPoint(BaseModel):
    date: datetime          # Data point timestamp
    value: float            # Numeric value
    label: str | None = None # Optional label

class TimeSeriesData(BaseModel):
    metric_name: str        # revenue, expenses, ebitda
    points: list[TimeSeriesPoint] = []
    interval: str = "raw"   # raw | monthly | quarterly | yearly
    source_documents: list[str] = []
```

### Async Ingestion Models

```python
class AsyncIngestionResponse(BaseModel):
    job_id: str
    status: str = "started"
    message: str
    estimated_time_s: int | None = None

class IngestionJobStatus(BaseModel):
    job_id: str
    status: str             # pending | in_progress | completed | failed
    progress: int | None = None
    result: DocumentMetadata | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
```

---

## Configuration Model (`raglite/shared/config.py`)

```python
class Settings(BaseSettings):
    # Environment
    app_env: str = "production"  # production | test | development

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "financial_docs"

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "raglite"
    postgres_user: str = "raglite"
    postgres_password: str = "raglite"

    # LLM APIs
    anthropic_api_key: str | None = None
    mistral_api_key: str | None = None
    metadata_extraction_model: str = "mistral-small-latest"

    # AWS Strands
    strands_orchestration_model: str = "mistral-small-latest"
    strands_agent_timeout_seconds: int = 15
    strands_enable_opentelemetry: bool = False

    # Embedding
    embedding_model: str = "intfloat/e5-large-v2"
    embedding_dimension: int = 1024

    # MCP
    mcp_server_port: int = 8000

    # PDF Processing
    pdf_processing_threads: int = 8

    class Config:
        env_file = ".env"
```

---

## Database Schema

### PostgreSQL Tables

#### `financial_tables`

Stores extracted financial table data for SQL queries.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `document_id` | VARCHAR(255) | Source document ID |
| `page_number` | INT | Page number |
| `table_index` | INT | Table index on page |
| `table_caption` | TEXT | Table caption |
| `entity` | VARCHAR(255) | Company/division name |
| `metric` | VARCHAR(255) | Financial metric |
| `period` | VARCHAR(100) | Time period |
| `fiscal_year` | INT | Fiscal year |
| `value` | DECIMAL(15,2) | Numeric value |
| `unit` | VARCHAR(50) | Unit of measure |
| `row_index` | INT | Row index |
| `column_name` | VARCHAR(255) | Column name |
| `section_type` | VARCHAR(100) | Section type |
| `created_at` | TIMESTAMP | Creation timestamp |
| `chunk_text` | TEXT | Original context |

### Qdrant Collections

#### `financial_docs` / `financial_docs_test`

Vector collection storing document chunks with embeddings.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Point ID |
| `vector` | Float[1024] | E5-large-v2 embedding |
| `payload.chunk_id` | String | Chunk identifier |
| `payload.content` | String | Chunk text |
| `payload.page_number` | Integer | Page number |
| `payload.document_type` | String | Document type |
| `payload.reporting_period` | String | Reporting period |
| `payload.*` | Various | All 15 metadata fields |

---

## Type Aliases

```python
JobID = str  # Job identifier for async operations
```

---

## Validation Rules

| Model | Field | Validation |
|-------|-------|------------|
| QueryRequest | `top_k` | 1 ≤ value ≤ 50 |
| SearchResult | `score` | 0.0 ≤ value ≤ 1.0 |
| AnalyticalQueryRequest | `query` | max_length=1000 |

---

*Generated by BMAD Document Project Workflow*
