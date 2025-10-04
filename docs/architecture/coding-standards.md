# RAGLite Coding Standards

**Version:** 1.1
**Status:** Definitive
**Purpose:** Mandatory coding patterns for all RAGLite development

---

## Overview

RAGLite follows **PEP 8** with specific requirements for type hints, docstrings, error handling, and structured logging. AI agents (Claude Code) and developers MUST follow these patterns for consistency across all modules.

**Reference Implementation:** See `docs/archive/architecture-v1.1-insert.md` for complete 250-line MCP server example.

---

## 1. Type Hints (MANDATORY)

All function signatures MUST include type hints for parameters and return values.

### ✅ Good Examples

```python
from typing import List, Optional, Dict, Any

def process_document(file_path: str, doc_type: DocumentType) -> JobID:
    """Process financial document and return job ID."""
    pass

async def search_documents(
    query: str,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> List[SearchResult]:
    """Search documents with optional filters."""
    pass
```

### ❌ Bad Examples

```python
# NO TYPE HINTS - FORBIDDEN
def process_document(file_path, doc_type):
    pass

# MISSING RETURN TYPE - FORBIDDEN
def calculate_score(x: float, y: float):
    return x + y
```

---

## 2. Docstrings (MANDATORY for Public Functions)

Use **Google-style docstrings** for all public functions. Private functions (prefixed with `_`) may have shorter docstrings.

### Required Sections

1. **Summary** (one-line description)
2. **Args** (if any parameters)
3. **Returns** (if returns value)
4. **Raises** (if raises exceptions)
5. **Example** (optional but recommended)

### Template

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

### Private Function Docstrings (Simplified)

```python
def _calculate_chunk_hash(content: str) -> str:
    """Calculate SHA256 hash of chunk content for deduplication."""
    pass
```

---

## 3. Import Organization

Organize imports in three sections (PEP 8 standard):

```python
# 1. Standard library imports (alphabetical)
import asyncio
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

# 2. Third-party imports (alphabetical)
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

# 3. Local application imports (alphabetical)
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.ingestion.pipeline import ingest_document
```

**Rules:**

- Separate sections with blank lines
- Alphabetize within each section
- Use absolute imports (`from raglite.module import ...`), not relative imports

---

## 4. Error Handling (Specific Exceptions)

Always raise **specific exceptions** with **descriptive messages**. Never use bare `Exception`.

### ✅ Good Examples

```python
# Specific exception with context
if not file_path.exists():
    raise FileNotFoundError(f"Document not found: {file_path}")

# Catch specific exceptions, log with context, re-raise
try:
    result = await risky_operation()
except FileNotFoundError as e:
    logger.error("File not found", extra={"path": file_path}, exc_info=True)
    raise  # Re-raise original exception

except QdrantConnectionError as e:
    logger.error("Qdrant unavailable", extra={"host": settings.qdrant_host})
    raise RuntimeError(f"Database connection failed: {str(e)}")

except Exception as e:
    # Catch-all for unexpected errors (log stack trace)
    logger.error("Unexpected error", exc_info=True)
    raise RuntimeError(f"Operation failed: {str(e)}")
```

### ❌ Bad Examples

```python
# Generic exception - FORBIDDEN
if not file_path.exists():
    raise Exception("Error")

# Bare except - FORBIDDEN
try:
    result = operation()
except:  # Catches everything, including KeyboardInterrupt
    pass

# Swallowing exceptions - FORBIDDEN
try:
    important_operation()
except Exception:
    pass  # Error lost, no logging
```

---

## 5. Structured Logging (MANDATORY)

Use the custom logger from `raglite.shared.logging` with **structured context** via `extra={}`.

### ✅ Good Examples

```python
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Structured logging with context (JSON-serializable)
logger.info(
    "Document ingested",
    extra={
        "doc_id": doc_id,
        "chunks": chunk_count,
        "duration_ms": duration
    }
)

logger.error(
    "Query failed",
    extra={
        "query_id": query_id,
        "error": str(e)
    },
    exc_info=True  # Include stack trace for errors
)
```

### ❌ Bad Examples

```python
# print() statements - FORBIDDEN (except CLI scripts)
print(f"Ingested {doc_id} with {chunk_count} chunks")

# Unstructured logging - FORBIDDEN
logger.info(f"Ingested {doc_id} with {chunk_count} chunks")

# Missing context - BAD
logger.error("Query failed")  # No query_id, no error details
```

### Logging Levels

- **DEBUG:** Detailed diagnostic info (disabled in production)
- **INFO:** Normal operations (ingestion started, query executed)
- **WARNING:** Recoverable issues (slow query, API rate limit)
- **ERROR:** Operation failures (ingestion failed, Qdrant down)
- **CRITICAL:** System-wide failures (server startup failed)

---

## 6. Pydantic Models (Data Validation)

Use **Pydantic models** for all data structures (MCP tool schemas, configuration, internal DTOs).

### Pattern

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class SearchRequest(BaseModel):
    """Request model for document search."""

    query: str = Field(
        ...,  # ... means required
        description="Natural language financial question",
        min_length=1,
        examples=["What drove Q3 revenue variance?"]
    )

    top_k: int = Field(
        default=10,
        ge=1,  # Greater than or equal to 1
        le=50,  # Less than or equal to 50
        description="Number of results to return (1-50)"
    )

    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata filters"
    )
```

**Benefits:**

- Automatic validation (FastMCP requirement)
- Clear MCP tool schemas for clients
- IDE autocomplete support
- Runtime type checking

---

## 7. Async/Await Patterns

Use `async`/`await` for **ALL I/O operations** (database, API calls, file I/O).

### ✅ Good Examples

```python
# Async for I/O operations
async def ingest_document(file_path: str) -> JobID:
    """Ingest document asynchronously."""
    # File I/O
    content = await read_file_async(file_path)

    # API call
    embeddings = await generate_embeddings(content)

    # Database operation
    await qdrant.upsert(collection_name="docs", points=embeddings)

    return job_id

# Run multiple async operations in parallel
async def process_batch(files: List[str]):
    tasks = [ingest_document(f) for f in files]
    results = await asyncio.gather(*tasks)  # Parallel execution
    return results
```

### ❌ Bad Examples

```python
# Synchronous I/O in async function - BAD (blocks event loop)
async def ingest_document(file_path: str):
    with open(file_path, 'r') as f:  # BLOCKING I/O
        content = f.read()
    return content

# Missing await - RUNTIME ERROR
async def query():
    results = search_documents(query="test")  # Missing await!
    return results
```

---

## 8. Constants and Configuration

### Constants (Module-level, UPPERCASE)

```python
# ✅ Good
MAX_CHUNK_SIZE = 500
DEFAULT_TOP_K = 10
EMBEDDING_DIMENSION = 1024

# ❌ Bad
max_chunk_size = 500  # Should be UPPERCASE
```

### Configuration (Pydantic Settings)

```python
# raglite/shared/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    claude_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()  # Singleton instance
```

---

## 9. Naming Conventions

### Functions (Verb phrases)

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

### Classes (Nouns, PascalCase)

```python
# ✅ Good
class DocumentIngestionRequest(BaseModel):
    pass

class SearchResult(BaseModel):
    pass

# ❌ Bad
class ingest_document_request(BaseModel):  # Should be PascalCase
    pass
```

### Variables (snake_case)

```python
# ✅ Good
chunk_count = 10
query_id = "qry-123"

# ❌ Bad
ChunkCount = 10  # Should be snake_case
queryID = "qry-123"  # Should be query_id
```

---

## 10. Testing Standards

### Test Organization

Co-located in `raglite/tests/` directory:

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

### Test Naming Convention

`test_<module>_<function>_<scenario>.py`

### Test Example

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

### Coverage Targets

- **Phase 1-3 (MVP):** 50%+ for critical paths (ingestion, retrieval)
- **Phase 4 (Production):** 80%+ overall coverage

### Testing Tools

- **Test Framework:** `pytest`
- **Async Testing:** `pytest-asyncio`
- **Coverage:** `pytest-cov` (Phase 4)
- **Mocking:** `pytest-mock` or `unittest.mock`

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest raglite/tests/test_ingestion_pipeline.py

# Run with coverage (Phase 1+)
uv run pytest --cov=raglite --cov-report=html

# Run specific test function
uv run pytest raglite/tests/test_ingestion_pipeline.py::test_ingest_document_success

# Run tests in parallel (faster)
uv run pytest -n 4 --dist worksteal
```

---

## 11. Code Formatting (Automated)

Use **Ruff** for ALL formatting and linting. Ruff replaces Black + isort + multiple flake8 plugins.

### Setup (Story 1.1)

```bash
# Install dev dependencies
uv add --group dev ruff pytest pytest-asyncio pytest-xdist

# Format code (replaces Black)
uv run ruff format raglite/

# Check formatting without modifying
uv run ruff format --check raglite/

# Lint code
uv run ruff check raglite/

# Lint and auto-fix issues
uv run ruff check --fix raglite/
```

**Why Ruff over Black + isort?**
- 10-100× faster than Black
- Single tool for formatting + linting + import sorting
- Written in Rust, zero Python dependencies
- Drop-in replacement for Black (same formatting rules)

### Pre-commit Hook (Recommended)

```yaml
# .pre-commit-config.yaml
repos:
  # Ruff for formatting (replaces Black)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.13.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format  # Formatting (replaces Black)

  # MyPy for type checking (enabled Phase 1)
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-requests]
        args: [--show-error-codes, --ignore-missing-imports]
        files: ^raglite/  # Only check production code

  # Secret scanning
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
```

---

## 12. Forbidden Patterns

### ❌ NEVER DO THIS

1. **No type hints**
2. **No docstrings on public functions**
3. **Bare `except:` clauses**
4. **Generic `Exception` raises**
5. **`print()` statements** (use logger)
6. **Relative imports** (use absolute: `from raglite.module import ...`)
7. **Mutable default arguments** (`def func(items=[]):` is FORBIDDEN)
8. **Global state** (use Pydantic Settings or dependency injection)
9. **Synchronous I/O in async functions**
10. **Swallowing exceptions** without logging

---

## Summary Checklist

Before committing code, verify:

- [ ] All functions have type hints
- [ ] All public functions have Google-style docstrings
- [ ] Imports organized in 3 sections (stdlib, third-party, local)
- [ ] Specific exceptions raised (not generic `Exception`)
- [ ] Structured logging with `extra={}` context
- [ ] Pydantic models for data validation
- [ ] Async/await for all I/O operations
- [ ] Constants are UPPERCASE
- [ ] Functions are verb phrases (snake_case)
- [ ] Classes are nouns (PascalCase)
- [ ] Tests exist for new functionality
- [ ] Code formatted with `black`
- [ ] Linting passes with `ruff`

---

**Questions or Clarifications?**
Refer to the complete reference implementation in `docs/archive/architecture-v1.1-insert.md` (250-line MCP server example).
