# Coding Standards

**CRITICAL:** Follow patterns from `docs/architecture/6-complete-reference-implementation.md`

**SIMPLICITY FIRST:** No abstractions, no frameworks, no custom wrappers. Direct SDK usage only.

---

## Required Patterns

### 1. Type Hints
All functions must have type annotations:
```python
async def process_document(doc_path: str) -> DocumentMetadata:
```

### 2. Docstrings
Google-style for all public functions:
```python
"""Process financial document and extract metadata.

Args:
    doc_path: Path to the document file

Returns:
    DocumentMetadata with extracted information

Raises:
    DocumentProcessingError: If extraction fails
"""
```

### 3. Structured Logging
Use `extra={}` for context:
```python
logger.info("Document ingested", extra={"doc_id": doc.id, "pages": doc.pages})
```

### 4. Error Handling
Specific exceptions with context:
```python
raise DocumentProcessingError(f"Failed to process {doc_path}: {e}")
```

### 5. Async/Await
For all I/O operations:
```python
async def fetch_embeddings(text: str) -> np.ndarray:
```

### 6. Pydantic Models
For all data structures:
```python
class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
```

---

## Forbidden Patterns (Over-Engineering)

### NO Custom Wrappers
```python
# WRONG - Don't create wrapper classes
class QdrantManager:
    def __init__(self):
        self.client = QdrantClient(...)
    def custom_search(self, query):
        return self.client.search(...)

# CORRECT - Use SDK directly
from qdrant_client import QdrantClient
qdrant = QdrantClient(url=settings.qdrant_url)
results = qdrant.search(collection_name="docs", query_vector=embedding)
```

### NO Abstract Base Classes
```python
# WRONG - Don't create abstract interfaces for a 600-line MVP
from abc import ABC, abstractmethod
class BaseRetriever(ABC):
    @abstractmethod
    def retrieve(self, query: str) -> List[Document]:
        pass

# CORRECT - Just write the function
async def retrieve_documents(query: str, top_k: int = 5) -> List[Document]:
    """Retrieve relevant documents from Qdrant."""
    # Direct implementation here
```

### NO Configuration Frameworks
```python
# WRONG - Don't build config loaders
class ConfigLoader:
    def load_from_yaml(self, path): ...
    def validate(self): ...

# CORRECT - Use Pydantic Settings (already in tech stack)
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    qdrant_url: str
    claude_api_key: str
    class Config:
        env_file = ".env"
settings = Settings()
```

### NO Custom Decorators
```python
# WRONG - Don't create custom decorators
def with_logging(func):
    def wrapper(*args, **kwargs):
        logger.info(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

# CORRECT - Use explicit logging calls
async def ingest_document(doc_path: str):
    logger.info("Ingesting document", extra={"path": doc_path})
    # Implementation here
```

---

## File Size Limits

**See:** `.claude/rules/file-size-limits.md` for full documentation.

### Quick Reference

| Threshold | LOC | Action Required |
|-----------|-----|-----------------|
| Ideal | 100-250 | None (target range) |
| Warning | >400 | Consider splitting |
| Hard Limit | >500 | Must refactor or add exception |

### When Creating New Files

1. **Plan module boundaries BEFORE writing** - Target <250 LOC for new modules
2. **Split proactively** - If file will exceed 400 LOC, split before it grows
3. **Never commit new files >500 LOC** without exception approval

### When Modifying Existing Files

1. **Check current size:** `wc -l raglite/path/to/file.py`
2. **If approaching 400 LOC:** Consider extracting functionality to new module
3. **If exceeds 500 LOC:** Either refactor or file must be in `.file-size-exceptions`

### Validation

```bash
# Check all file sizes
python scripts/check_file_sizes.py --verbose

# Quick check for specific file
wc -l raglite/path/to/file.py
```

---

## MCP Tool Pattern

```python
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    top_k: int = Field(5, description="Number of results")

mcp = FastMCP("RAGLite")

@mcp.tool()
async def query_financial_documents(request: QueryRequest) -> str:
    """Query financial documents using natural language.

    Args:
        request: Query parameters

    Returns:
        Synthesized answer with citations
    """
    logger.info("Query received", extra={"query": request.query})
    # Implementation here
```

---

## When Implementing New Features

### BEFORE writing ANY code:
1. **Check tech stack:** Is every library in `docs/architecture/5-technology-stack-definitive.md`?
   - YES -> Proceed
   - NO -> STOP and ask user for approval

2. **Check simplicity:** Am I adding abstractions, wrappers, or patterns?
   - YES -> STOP, rewrite as simple functions
   - NO -> Proceed

### DURING implementation:
3. **Read the story:** Check `docs/stories/` for active user story
4. **Review architecture:** Reference `docs/architecture/` for patterns
5. **Follow reference implementation:** Copy patterns from section 6 of architecture docs
6. **Use type hints & docstrings:** Match reference code style
7. **Add tests:** Co-locate in `tests/`
8. **Structured logging:** Always include context via `extra={}`

### AFTER writing code:
9. **Simplicity check:** Could this be 30% fewer lines with direct SDK calls?
   - YES -> Refactor to remove abstractions
   - NO -> Proceed

10. **Dependency check:** Did I add any imports not in the tech stack table?
    - YES -> REMOVE and ask user first
    - NO -> Proceed
