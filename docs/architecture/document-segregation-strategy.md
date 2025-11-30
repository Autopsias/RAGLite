# Document Segregation Strategy

**Story:** 4.0.4 - Document Segregation Architecture
**Last Updated:** 2025-11-25
**Status:** Implemented

## Overview

This document describes how RAGLite tracks document provenance, enables document-scoped queries, and maintains data integrity across the vector (Qdrant) and relational (PostgreSQL) databases.

## Document Identification

### Primary Identifier

Documents are identified by their **filename** (`DocumentMetadata.filename`), which serves as the primary identifier across all storage layers:

| Storage Layer | Field Name | Type | Description |
|--------------|------------|------|-------------|
| Qdrant | `source_document` | string | Original filename stored in payload |
| PostgreSQL (chunks) | `document_id` | VARCHAR | Original filename in financial_chunks |
| PostgreSQL (tables) | `document_id` | VARCHAR | Original filename in financial_tables |

### Metadata Schema

**DocumentMetadata Model** (`raglite/shared/models.py:11-22`):

```python
class DocumentMetadata(BaseModel):
    filename: str           # Primary document identifier
    doc_type: str           # "PDF" or "Excel"
    ingestion_timestamp: str # ISO8601 timestamp
    page_count: int         # Number of pages/sheets
    source_path: str        # Original file path
    chunk_count: int        # Number of chunks created
```

### Document-Level Tracking

Each document ingested into RAGLite receives:

1. **Unique filename** - Used as the primary identifier
2. **Document type** - PDF or Excel classification
3. **Ingestion timestamp** - When the document was processed
4. **Page count** - Total pages/sheets in source
5. **Chunk count** - Number of chunks generated

## Chunk Provenance Tagging

### How Chunks Reference Their Source Document

Every chunk maintains a reference to its parent document through the `metadata` field:

```python
class Chunk(BaseModel):
    chunk_id: str
    content: str
    metadata: DocumentMetadata  # Contains filename
    page_number: int            # Page where chunk appears
    chunk_index: int            # Sequential index (0-based)
    # + 15 rich metadata fields
```

### Qdrant Payload Structure

When chunks are stored in Qdrant (`storage_operations.py:246-271`), the payload includes:

```python
payload = {
    "chunk_id": chunk.chunk_id,
    "text": chunk.content,
    "word_count": word_count,
    "source_document": chunk.metadata.filename,  # DOCUMENT PROVENANCE
    "page_number": chunk.page_number,
    "chunk_index": chunk.chunk_index,

    # Rich Metadata (15 fields)
    # Document-Level (7)
    "document_type": ...,
    "reporting_period": ...,
    "time_granularity": ...,
    "company_name": ...,
    "geographic_jurisdiction": ...,
    "data_source_type": ...,
    "version_date": ...,

    # Section-Level (5)
    "section_type": ...,
    "metric_category": ...,
    "units": ...,
    "department_scope": ...,

    # Table-Specific (3)
    "table_context": ...,
    "table_name": ...,
    "statistical_summary": ...,
}
```

### PostgreSQL Table Schemas

**financial_chunks table:**
```sql
CREATE TABLE financial_chunks (
    chunk_id UUID PRIMARY KEY,
    document_id VARCHAR NOT NULL,    -- Source document filename
    page_number INTEGER,
    chunk_index INTEGER,
    content TEXT,
    -- 15 rich metadata columns...
    embedding_id VARCHAR,            -- Link to Qdrant vector
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**financial_tables table:**
```sql
CREATE TABLE financial_tables (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR NOT NULL,    -- Source document filename
    page_number INTEGER,
    table_index INTEGER,
    table_caption VARCHAR,
    entity VARCHAR,
    metric VARCHAR,
    value NUMERIC,
    unit VARCHAR,
    period VARCHAR,
    fiscal_year INTEGER
);
```

## Query Scoping Capabilities

### Qdrant Vector Search

**Document-scoped queries** are supported via the `filters` parameter in `search_documents()`:

```python
# Search within a specific document
results = await search_documents(
    query="revenue growth",
    top_k=5,
    filters={"source_document": "Q3_2024_Report.pdf"}
)
```

**Supported filter fields** (`search.py:143-163`):

| Category | Fields |
|----------|--------|
| Legacy | `source_document` |
| Document-Level (7) | `document_type`, `reporting_period`, `time_granularity`, `company_name`, `geographic_jurisdiction`, `data_source_type`, `version_date` |
| Section-Level (5) | `section_type`, `metric_category`, `units`, `department_scope` |
| Table-Specific (3) | `table_context`, `table_name`, `statistical_summary` |

### PostgreSQL SQL Queries

**Document-scoped queries** use standard SQL WHERE clauses:

```sql
-- Filter by specific document
SELECT entity, metric, value
FROM financial_tables
WHERE document_id = 'Q3_2024_Report.pdf';

-- Filter by document and page range
SELECT entity, metric, value
FROM financial_tables
WHERE document_id = 'Annual_Report.pdf'
  AND page_number BETWEEN 10 AND 20;
```

### Query Scoping Limitations

| Feature | Supported | Notes |
|---------|-----------|-------|
| Filter by document | ✅ Yes | Via `source_document` / `document_id` |
| Filter by page | ✅ Yes | Via `page_number` |
| Filter by date range | ⚠️ Partial | `reporting_period` metadata (text field) |
| Filter by ingestion date | ❌ No | `ingestion_timestamp` not indexed |
| Wildcard document matching | ❌ No | Exact filename match only |

## Multi-Document Search Behavior

### Default Behavior (No Filters)

When no document filter is specified, searches return results from **all ingested documents**, ranked by relevance:

```python
# Returns chunks from ALL documents
results = await search_documents("financial performance", top_k=10)
# Results may include chunks from multiple PDFs
```

### Filtered Behavior (Single Document)

When a document filter is specified, results are **scoped to that specific document**:

```python
# Returns chunks ONLY from the specified document
results = await search_documents(
    "financial performance",
    top_k=10,
    filters={"source_document": "Q3_2024_Report.pdf"}
)
# All results guaranteed from Q3_2024_Report.pdf
```

### Hybrid Search Behavior

The hybrid search pipeline (`hybrid_search()`) preserves document attribution through:

1. **SQL+Vector Fusion** - SQL results include `document_id` for attribution
2. **BM25+Vector Fusion** - Both rankings use `source_document` for deduplication
3. **Result Merging** - RRF fusion preserves source attribution in final results

## Source Attribution in Results

### QueryResult Model

Search results include full attribution data (`models.py:182-198`):

```python
class QueryResult(BaseModel):
    score: float              # Relevance score
    text: str                 # Chunk content
    source_document: str      # ORIGINAL FILENAME
    page_number: int | None   # Page for citations
    chunk_index: int          # Position in document
    word_count: int           # Content length
```

### Citation Generation

Source citations can be formatted as:

```
"[Source: Q3_2024_Report.pdf, Page 12]"
```

The `_ensure_attribution_columns()` function in `sql_table_search.py` guarantees `document_id` and `page_number` are always present in SQL query results.

## Test Isolation Strategy

This section documents how tests avoid data pollution and maintain isolation.
For full details, see [Story 4.0.5: Test vs Production Database Separation](../stories/4-0-5-test-prod-database-separation.md).

### Environment Separation (Story 4.0.5)

RAGLite uses completely separate database instances for different environments:

| Environment | Qdrant Port | PostgreSQL Port | Collection Name | Use Case |
|-------------|-------------|-----------------|-----------------|----------|
| Production | 6333 | 5432 | `financial_docs` | MCP server, production queries |
| Test (Local) | 6335 | 5433 | `financial_docs_test` | pytest, local development |
| Test (CI) | 6335 | 5433 | `financial_docs_ci` | GitHub Actions workflows |

**Automatic Environment Detection:**

```python
# Settings class auto-adjusts based on APP_ENV
APP_ENV=test       → Uses test ports (6335, 5433)
APP_ENV=production → Uses production ports (6333, 5432)

# CI detection (GITHUB_ACTIONS, CI, CONTINUOUS_INTEGRATION)
CI=true + APP_ENV=test → Uses _ci collection suffix
```

### Test Database Configuration

Tests configure the environment at module level BEFORE any imports:

```python
# tests/conftest.py (lines 20-35)
import os

# CRITICAL: Set before raglite imports
os.environ["APP_ENV"] = "test"
os.environ["TESTING"] = "true"
os.environ["POSTGRES_PORT"] = "5433"
os.environ["POSTGRES_DB"] = "raglite_ci"
os.environ["POSTGRES_USER"] = "raglite_ci"
os.environ["POSTGRES_PASSWORD"] = "raglite_ci"
```

### Fixture Isolation Patterns

**Session-scoped fixtures** (run once per test session):
- `configure_test_environment` - Sets environment variables
- `session_ingested_collection` - Ingests test data once
- `mock_mistral_api_globally` - Prevents real API calls

**Module-scoped fixtures** (shared across test class):
- `mock_qdrant_client` - Mock for unit tests
- `sample_document_metadata` - Immutable test data

**Function-scoped fixtures** (isolated per test):
- `test_settings` - For tests that modify settings
- `sample_chunk` - For tests that modify chunk data

### Test Markers for Collection Behavior

Integration tests MUST declare their collection behavior:

```python
# Read-only tests (skip expensive cleanup)
@pytest.mark.preserve_collection
async def test_search_returns_results():
    ...

# Tests that modify data (may need cleanup)
@pytest.mark.manages_collection_state
async def test_ingestion_stores_chunks():
    ...
```

**Enforcement:** Enable with `pytest --enforce-isolation-markers`

### Test Fixture Best Practices

**For Future Test Authors:**

1. **Use small fixtures** - `tests/fixtures/sample-small-3-pages.pdf` (228 KB, 4 pages)
   - 15-18x faster than full 160-page PDF
   - Sufficient for validating document attribution

2. **Lazy imports** - Import raglite modules inside test functions
   ```python
   async def test_something():
       from raglite.retrieval.search import search_documents  # Lazy import
   ```

3. **Use session fixtures** - For expensive operations (embedding model, ingestion)
   ```python
   @pytest.fixture(scope="session")
   def expensive_resource():
       ...
   ```

4. **Mock external APIs** - Use `mock_mistral_api_globally` session fixture
   - Prevents real Mistral API calls
   - Eliminates 660-1100s API latency

5. **xdist grouping** - Force all integration tests to same worker
   ```python
   @pytest.mark.xdist_group(name="embedding_model")
   ```

### Preventing Data Pollution

| Scenario | Prevention Mechanism |
|----------|---------------------|
| Tests deleting production data | Separate database ports (6335 vs 6333) |
| Test data leaking to production | `APP_ENV=test` auto-configured in conftest.py |
| Parallel test conflicts | `@pytest.mark.xdist_group` forces single worker |
| API calls during tests | Session-scoped Mistral mock blocks all calls |
| CI/local conflicts | `_ci` vs `_test` collection suffixes |

## Code References

| Component | File | Lines |
|-----------|------|-------|
| DocumentMetadata model | `raglite/shared/models.py` | 11-22 |
| Chunk model | `raglite/shared/models.py` | 109-168 |
| QueryResult model | `raglite/shared/models.py` | 182-198 |
| Qdrant storage | `raglite/ingestion/storage_operations.py` | 130-338 |
| PostgreSQL storage | `raglite/ingestion/storage_operations.py` | 341-661 |
| Search with filters | `raglite/retrieval/search.py` | 82-240 |
| SQL table search | `raglite/retrieval/sql_table_search.py` | 128-277 |
| Test environment config | `tests/conftest.py` | 20-99 |

## Related Documentation

- [Story 4.0.5: Test vs Production Database Separation](../stories/4-0-5-test-prod-database-separation.md)
- [Data Layer Architecture](7-data-layer.md)
- [Integration Tests](../../tests/integration/test_document_segregation.py)
