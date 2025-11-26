# RAGLite - Development Guide

> **Auto-generated:** 2025-11-26 | **Scan Level:** Deep

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- uv package manager

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/RAGLite.git
cd RAGLite

# Install dependencies with uv
uv sync --all-groups

# Start databases
docker-compose up -d

# Configure environment
cp .env.example .env
# Edit .env and add API keys:
#   MISTRAL_API_KEY=your_key
#   ANTHROPIC_API_KEY=your_key (optional)

# Initialize Qdrant collection
uv run python scripts/init-qdrant.py

# Run MCP server
uv run python -m raglite.main
```

## Development Commands

### Running the Server

```bash
# Development mode
uv run python -m raglite.main

# With verbose logging
LOG_LEVEL=DEBUG uv run python -m raglite.main
```

### Testing

```bash
# All tests (excludes slow tests)
uv run pytest tests/

# Unit tests only (~200 tests, <2 min)
uv run pytest tests/unit/

# Integration tests (~115 tests, requires Docker)
uv run pytest tests/integration/ -m "not slow"

# E2E tests (~28 tests)
uv run pytest tests/e2e/

# With coverage report
uv run pytest --cov=raglite --cov-report=html

# Specific test file
uv run pytest tests/unit/test_query_classifier.py -v

# Run slow tests (marked with @pytest.mark.slow)
uv run pytest -m slow
```

### Code Quality

```bash
# Format code
uv run black raglite/ tests/

# Lint code
uv run ruff check raglite/ tests/

# Fix linting issues
uv run ruff check --fix raglite/

# Type checking
uv run mypy raglite/

# All quality checks
uv run black raglite/ && uv run ruff check raglite/ && uv run mypy raglite/
```

### Database Management

```bash
# Start all databases (production + test)
docker-compose up -d

# Start only production databases
docker-compose up -d qdrant postgresql

# Start only test databases
docker-compose up -d qdrant-test postgresql-test

# View logs
docker-compose logs -f qdrant

# Reset databases
docker-compose down -v
docker-compose up -d

# Clean test databases
uv run python scripts/clean-test-databases.py
```

### Document Ingestion (CLI)

```bash
# Single document
uv run python -c "
import asyncio
from raglite.ingestion.pipeline import ingest_document

async def ingest():
    result = await ingest_document('/path/to/document.pdf')
    print(f'Ingested {result.page_count} pages, {result.chunk_count} chunks')

asyncio.run(ingest())
"

# Batch ingestion
uv run python scripts/ingest-production-batch.py
```

## Environment Configuration

### Required Variables

```bash
# LLM API Keys
MISTRAL_API_KEY=<your-api-key-here>     # Required for metadata extraction

# Optional
ANTHROPIC_API_KEY=<your-api-key-here>     # For Claude synthesis (fallback)
```

### Optional Variables

```bash
# Environment
APP_ENV=production                        # production | test | development

# Qdrant (defaults shown)
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=financial_docs

# PostgreSQL (defaults shown)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=raglite
POSTGRES_USER=raglite
POSTGRES_PASSWORD=raglite

# Processing
PDF_PROCESSING_THREADS=8                  # 1-16 threads

# AWS Strands
STRANDS_ORCHESTRATION_MODEL=mistral-small-latest
STRANDS_AGENT_TIMEOUT_SECONDS=15
```

### Test Environment

```bash
# Automatic test database switching
APP_ENV=test uv run pytest tests/

# Test databases use:
# - Qdrant: localhost:6335
# - PostgreSQL: localhost:5433, database: raglite_test
```

## Project Structure

```
raglite/
├── raglite/                # Main application
│   ├── main.py             # MCP server entry point
│   ├── ingestion/          # Document processing
│   ├── retrieval/          # Search & queries
│   ├── agentic/            # Workflow orchestration
│   └── shared/             # Config, models, clients
├── tests/
│   ├── unit/               # Fast, no dependencies
│   ├── integration/        # Requires Docker
│   └── e2e/                # Full system tests
├── migrations/             # Database migrations
├── scripts/                # Utility scripts
└── docs/                   # Documentation
```

## Coding Standards

### Type Hints (Required)

```python
async def process_document(doc_path: str, top_k: int = 5) -> DocumentMetadata:
    """Process document and return metadata."""
    ...
```

### Docstrings (Google Style)

```python
def search_documents(query: str, top_k: int = 5) -> list[SearchResult]:
    """Search documents using hybrid retrieval.

    Args:
        query: Natural language search query
        top_k: Number of results to return

    Returns:
        List of SearchResult objects sorted by relevance

    Raises:
        QueryError: If query processing fails
    """
```

### Structured Logging

```python
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

logger.info(
    "Document ingested",
    extra={"doc_id": doc.id, "pages": doc.pages, "chunks": chunk_count}
)
```

### Pydantic Models

```python
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(5, ge=1, le=50, description="Results count")
```

## Testing Guidelines

### Unit Tests

- No external dependencies (mock everything)
- Fast execution (<1s per test)
- Located in `tests/unit/`

```python
def test_query_classifier():
    result = classify_query("What was the EBITDA?")
    assert result.query_type == "financial"
```

### Integration Tests

- Require Docker (Qdrant, PostgreSQL)
- Use test databases (port 6335, 5433)
- Located in `tests/integration/`

```python
@pytest.mark.integration
async def test_multi_index_search(test_qdrant_client):
    results = await multi_index_search("revenue", top_k=5)
    assert len(results) > 0
```

### Fixtures

Shared fixtures in `tests/conftest.py`:

```python
@pytest.fixture
def sample_document():
    return DocumentMetadata(filename="test.pdf", doc_type="PDF", ...)

@pytest.fixture
async def test_qdrant_client():
    # Returns client connected to test Qdrant (port 6335)
    ...
```

## Pre-commit Hooks

```bash
# Install hooks
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

Configured hooks:
- black (formatting)
- ruff (linting)
- mypy (type checking)
- gitleaks (secret detection)

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`):

1. **Lint & Format** - black, ruff
2. **Type Check** - mypy
3. **Unit Tests** - pytest tests/unit/
4. **Integration Tests** - pytest tests/integration/ (with Docker services)
5. **Coverage Report** - 80% minimum

## Troubleshooting

### Common Issues

**Qdrant connection failed:**
```bash
docker-compose ps  # Check if running
docker-compose up -d qdrant
curl http://localhost:6333/collections
```

**PostgreSQL connection failed:**
```bash
docker-compose up -d postgresql
psql -h localhost -U raglite -d raglite
```

**Tests hanging:**
```bash
# Use test environment with shorter timeouts
APP_ENV=test TESTING=true uv run pytest tests/unit/ -v
```

**Import errors:**
```bash
uv sync --all-groups  # Reinstall dependencies
```

---

*Generated by BMAD Document Project Workflow*
