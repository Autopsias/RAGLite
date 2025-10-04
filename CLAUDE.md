# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**RAGLite** is a monolithic MVP for an AI-powered financial document analysis system using Retrieval-Augmented Generation (RAG). The system ingests financial PDFs/Excel files, enables natural language querying via MCP (Model Context Protocol), and provides accurate answers with source citations.

**Current Status:** Pre-Phase 1 (architecture and planning complete, no code yet)

**Target:** ~600-800 lines of Python code across 15 files

---

## 🚨 CRITICAL DEVELOPMENT CONSTRAINTS 🚨

### Anti-Over-Engineering Rules

**RULE 1: KISS (Keep It Simple, Stupid)**
- This is a ~600-800 line MVP. If you find yourself adding design patterns, abstractions, or "future-proofing," STOP.
- NO custom base classes, factories, builders, or abstract layers unless explicitly specified in architecture docs
- NO "framework" or "engine" abstractions - write simple, direct functions
- ONE level of indirection maximum - if you need a helper function, call it directly

**RULE 2: Technology Stack is LOCKED**
- ONLY use libraries listed in `docs/architecture/5-technology-stack-definitive.md`
- NEVER add SDKs, frameworks, or libraries not documented in the requirements
- NEVER use "improved" or "alternative" libraries (e.g., no LangChain, no LlamaIndex, no custom wrappers)
- If a library isn't in the tech stack table → ASK FIRST, never assume

**RULE 3: No Customization Beyond Standard SDKs**
- Use SDKs EXACTLY as documented in their official documentation
- NO custom wrappers around FastMCP, Qdrant client, or any SDK
- NO "simplified interfaces" or "convenience layers" unless approved
- If SDK documentation says `client.search()`, use `client.search()` - don't wrap it in `MyCustomSearch()`

**RULE 4: User Approval Required For**
- Any dependency not in `docs/architecture/5-technology-stack-definitive.md`
- Any abstraction layer beyond simple utility functions
- Any "framework" or "pattern" not shown in `docs/architecture/6-complete-reference-implementation.md`
- Any deviation from the 15-file repository structure in section 3

**RULE 5: When In Doubt**
- Check: Is this in the reference implementation? NO → Don't add it
- Check: Is this library in the tech stack table? NO → Ask user first
- Check: Am I adding this for "scalability" or "best practices"? YES → Remove it
- Check: Would this work as a simple 20-line function? YES → Do that instead

### Red Flags (STOP and Ask User)
- Adding a new Python package not in requirements
- Creating a `BaseClass` or `AbstractInterface`
- Writing a "config loader framework"
- Adding dependency injection
- Creating a plugin system
- Writing middleware layers
- Using decorators beyond `@mcp.tool()` and `@pytest.fixture`
- Adding caching layers (Redis, etc.) before Phase 4
- Creating custom exception hierarchies beyond what's in reference implementation

---

## Architecture & Documentation

### Primary Documents (Read First)

1. **Architecture (Sharded):** `docs/architecture/` - v1.1 Monolithic approach
   - Start with: `docs/architecture/1-introduction-vision.md` → `2-executive-summary.md`
   - **Critical for coding:** `6-complete-reference-implementation.md` (coding patterns)
   - Repository structure: `3-repository-structure-monolithic.md`
   - Tech stack: `5-technology-stack-definitive.md`
   - Implementation phases: `8-phased-implementation-strategy-v11-simplified.md`

2. **PRD (Sharded):** `docs/prd/` - Product requirements
   - Entry point: `docs/prd/index.md`
   - Epics: `epic-1-foundation-accurate-retrieval.md` through `epic-5-production-readiness-real-time-operations.md`

3. **BMAD Configuration:** `bmad/core/config.yaml`
   - Defines documentation structure and agent workflows
   - References to sharded docs in `docs/architecture/`, `docs/prd/`, `docs/front-end-spec/`

### Documentation Structure

- `docs/README.md` - Documentation guide and navigation
- `docs/architecture/` - 30 sharded architecture files
- `docs/prd/` - 15 sharded PRD files
- `docs/front-end-spec/` - MCP response format specifications
- `docs/stories/` - Active user stories (currently Story 0.1)
- `docs/qa/` - Quality assurance reports
- `docs/archive/` - Historical documents (ignore for development)

---

## Technology Stack

**🔒 LOCKED - No additions without user approval**

**Source of Truth:** `docs/architecture/5-technology-stack-definitive.md`

| Component | Technology | Purpose |
|-----------|------------|---------|
| PDF Processing | Docling | Extract text/tables (97.9% accuracy) |
| Excel Processing | openpyxl + pandas | Tabular data extraction |
| Embeddings | Fin-E5 | Financial domain semantic vectors |
| Vector DB | Qdrant 1.11+ | Vector storage/search |
| MCP Server | FastMCP (MCP Python SDK) | Expose tools via MCP protocol |
| LLM | Claude 3.7 Sonnet | Answer synthesis, reasoning |
| Backend | Python 3.11+ | All application code |
| Containerization | Docker Compose | Local development |
| Testing | pytest + pytest-asyncio | Unit/integration tests |

**Phase 2 (Conditional):** Neo4j for Knowledge Graph (only if Phase 1 accuracy <80%)

**Phase 4:** AWS (ECS/Fargate), CloudWatch, Terraform

### NOT Approved (Do Not Use)
- ❌ LangChain / LangGraph (use direct SDK calls instead)
- ❌ LlamaIndex (use Qdrant directly)
- ❌ Haystack (use Qdrant directly)
- ❌ Semantic Kernel (use direct SDK calls)
- ❌ Any ORM beyond Pydantic models
- ❌ Redis/Memcached (not needed until Phase 4)
- ❌ Celery/RQ (not needed for monolith)
- ❌ Custom abstraction libraries (write direct code)

---

## Repository Structure (Target)

```
raglite/
├── raglite/                    # Main package (~600-800 lines)
│   ├── main.py                # MCP server (~200 lines)
│   ├── ingestion/             # Document processing (~150 lines)
│   │   ├── pipeline.py
│   │   └── contextual.py
│   ├── retrieval/             # Search & synthesis (~150 lines)
│   │   ├── search.py
│   │   ├── synthesis.py
│   │   └── attribution.py
│   ├── forecasting/           # Phase 3 (~100 lines)
│   │   └── hybrid.py
│   ├── insights/              # Phase 3 (~100 lines)
│   │   ├── anomalies.py
│   │   └── trends.py
│   ├── shared/                # Utilities (~100 lines)
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── models.py
│   │   └── clients.py
│   └── tests/
│       ├── test_ingestion.py
│       ├── test_retrieval.py
│       └── ground_truth.py
├── scripts/
│   ├── setup-dev.sh
│   └── init-qdrant.py
├── docs/                      # Architecture & PRD (sharded)
├── docker-compose.yml
├── pyproject.toml             # Poetry dependencies
└── README.md
```

---

## Development Commands

### Environment Setup (When Ready)
```bash
# Install dependencies (Poetry)
poetry install

# Start Qdrant + services
docker-compose up -d

# Initialize Qdrant collection
python scripts/init-qdrant.py

# Run tests
poetry run pytest

# Run MCP server (local testing)
poetry run python -m raglite.main
```

### Testing
```bash
# Unit tests
poetry run pytest raglite/tests/

# Ground truth accuracy validation
poetry run python scripts/run-accuracy-tests.py

# With coverage
poetry run pytest --cov=raglite --cov-report=html
```

---

## Coding Standards

**CRITICAL:** Follow patterns from `docs/architecture/6-complete-reference-implementation.md`

**SIMPLICITY FIRST:** No abstractions, no frameworks, no custom wrappers. Direct SDK usage only.

### Required Patterns

1. **Type Hints:** All functions must have type annotations
   ```python
   async def process_document(doc_path: str) -> DocumentMetadata:
   ```

2. **Docstrings:** Google-style for all public functions
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

3. **Structured Logging:** Use `extra={}` for context
   ```python
   logger.info("Document ingested", extra={"doc_id": doc.id, "pages": doc.pages})
   ```

4. **Error Handling:** Specific exceptions with context
   ```python
   raise DocumentProcessingError(f"Failed to process {doc_path}: {e}")
   ```

5. **Async/Await:** For all I/O operations
   ```python
   async def fetch_embeddings(text: str) -> np.ndarray:
   ```

6. **Pydantic Models:** For all data structures
   ```python
   class QueryRequest(BaseModel):
       query: str
       top_k: int = 5
   ```

### Forbidden Patterns (Over-Engineering)

❌ **NO Custom Wrappers**
```python
# WRONG - Don't create wrapper classes
class QdrantManager:
    def __init__(self):
        self.client = QdrantClient(...)

    def custom_search(self, query):
        # Custom logic here
        return self.client.search(...)

# CORRECT - Use SDK directly
from qdrant_client import QdrantClient
qdrant = QdrantClient(url=settings.qdrant_url)
results = qdrant.search(collection_name="docs", query_vector=embedding)
```

❌ **NO Abstract Base Classes**
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

❌ **NO Configuration Frameworks**
```python
# WRONG - Don't build config loaders
class ConfigLoader:
    def load_from_yaml(self, path): ...
    def validate(self): ...
    def merge_sources(self): ...

# CORRECT - Use Pydantic Settings (already in tech stack)
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    qdrant_url: str
    claude_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()
```

❌ **NO Custom Decorators (except SDK-provided)**
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

## Implementation Phases

### Current Phase: Week 0 - Integration Spike (Pre-Phase 1)

**Active Story:** `docs/stories/0.1.week-0-integration-spike.md`

**Goals:**
- Validate technology stack (Docling + Fin-E5 + Qdrant + FastMCP)
- Ingest 1 real financial PDF
- Create 15 ground truth Q&A pairs
- Measure baseline accuracy (target: ≥70%)

**Success = GO to Phase 1 | Failure (<50%) = Reassess tech stack**

### Phase 1: Monolithic MVP (Weeks 1-5)
- Week 1: Ingestion pipeline
- Week 2: Retrieval & search
- Week 3-4: LLM synthesis
- Week 5: Accuracy validation (target: 90%+)

**Phase 1 Success Criteria:**
- 90%+ retrieval accuracy (50+ queries)
- 95%+ source attribution accuracy
- <10s query response time
- All answers cite sources

### Phase 2: GraphRAG (Conditional, Weeks 5-8)
**ONLY if Phase 1 accuracy <80% due to multi-hop query failures**

### Phase 3: Intelligence Features (Weeks 9-12 or 5-8)
- Forecasting (Prophet + LLM)
- Anomaly detection
- Trend analysis

### Phase 4: Production (Weeks 13-16)
- AWS deployment (ECS/Fargate)
- Monitoring (CloudWatch)
- Performance optimization

---

## BMAD Workflow Integration

This project uses **BMAD-METHOD** for agile workflow and agent-based development.

### Available Agents (via BMAD)

Reference agents by role in prompts (e.g., "As dev, implement Story 1.1"):

- **dev** (Full Stack Developer) - Code implementation, debugging, refactoring
- **sm** (Scrum Master) - Story creation, epic management
- **qa** (Test Architect) - Test strategy, quality gates
- **architect** - System design, architecture decisions
- **pm** (Product Manager) - PRD, feature prioritization
- **analyst** (Business Analyst) - Research, competitive analysis
- **ux-expert** - UI/UX design, front-end specs
- **bmad-master** - General-purpose expert for ad-hoc tasks
- **bmad-orchestrator** - Multi-agent coordination

### BMAD Commands & Workflows

BMAD now uses a workflow-based structure:
- Core workflows: `bmad/core/workflows/` (bmad-init, brainstorming, party-mode)
- BMM workflows: `bmad/bmm/workflows/` (analysis, plan, solutioning, implementation, testarch)
- Agent customizations: `bmad/_cfg/agents/`

Access workflows through the BMAD CLI or custom slash commands.

See `AGENTS.md` for full agent definitions and capabilities.

---

## Quality Gates & Testing

### Accuracy Validation (Critical NFR)

**NFR6:** 90%+ retrieval accuracy on test set
**NFR7:** 95%+ source attribution accuracy

**Ground Truth Testing:**
- Maintain 50+ Q&A pairs in `raglite/tests/ground_truth.py`
- Run daily during Phase 1 development
- Track accuracy trend line
- Document failure modes

### Test Coverage
- Target: 80%+ unit test coverage
- Integration tests for end-to-end flows
- Accuracy regression tests in CI/CD

---

## Key Files & Patterns

### When Implementing New Features

**BEFORE writing ANY code:**
1. **Check tech stack:** Is every library I need in `docs/architecture/5-technology-stack-definitive.md`?
   - YES → Proceed
   - NO → STOP and ask user for approval

2. **Check simplicity:** Am I adding abstractions, wrappers, or patterns?
   - YES → STOP, rewrite as simple functions
   - NO → Proceed

**DURING implementation:**
3. **Read the story:** Check `docs/stories/` for active user story
4. **Review architecture:** Reference `docs/architecture/` for patterns
5. **Follow reference implementation:** Copy patterns from section 6 of architecture docs
6. **Use type hints & docstrings:** Match reference code style
7. **Add tests:** Co-locate in `raglite/tests/`
8. **Structured logging:** Always include context via `extra={}`

**AFTER writing code:**
9. **Simplicity check:** Could this be 30% fewer lines with direct SDK calls?
   - YES → Refactor to remove abstractions
   - NO → Proceed

10. **Dependency check:** Did I add any imports not in the tech stack table?
    - YES → REMOVE and ask user first
    - NO → Proceed

### MCP Tool Pattern (from Reference Implementation)

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

## Important Notes

### Development Discipline
- **Target is 600-800 lines TOTAL:** If module exceeds target lines from section 3, you're over-engineering
- **MVP means MINIMAL:** Every line of code must justify its existence
- **No "nice to have" features:** Only implement what's in the current story
- **No premature optimization:** Get it working first, optimize in Phase 4 if needed

### File & Documentation Guidelines
- **Prefer editing over creating:** Always edit existing files rather than creating new documentation
- **No proactive documentation:** Only create .md files if explicitly requested
- **Architecture is sharded:** Use `docs/architecture/` and `docs/prd/` subdirectories, not monolithic files
- **BMAD integration:** Agent personas and tasks are in `bmad/` (auto-generated in `AGENTS.md`)
- **Week 0 first:** Do NOT start Phase 1 implementation until Week 0 spike validates the stack

### Strict SDK Usage
- **Official docs ONLY:** Use SDK examples from official documentation, not blog posts or tutorials
- **No customization:** If SDK has a `search()` method, use it as-is - don't wrap or extend
- **Ask before adding:** ANY new dependency requires explicit user approval
- **Standard library preferred:** If Python stdlib can do it, use that instead of a package

---

## References

- **MCP Protocol:** https://modelcontextprotocol.io/
- **FastMCP Docs:** https://github.com/jlowin/fastmcp
- **Docling:** https://github.com/DS4SD/docling
- **Qdrant:** https://qdrant.tech/documentation/
- **Claude API:** https://docs.anthropic.com/

---

## Current Next Steps

1. Complete **Story 0.1: Week 0 Integration Spike** (`docs/stories/0.1.week-0-integration-spike.md`)
2. Set up API accounts (Claude, AWS if needed)
3. Run integration spike with 1 PDF + 15 test queries
4. Generate Week 0 Spike Report
5. **Decision Gate:** GO/NO-GO for Phase 1 based on accuracy (≥70% = GO)

**DO NOT** begin Phase 1 implementation until Week 0 validates the technology stack.
