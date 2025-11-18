# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**RAGLite** is a monolithic MVP for an AI-powered financial document analysis system using Retrieval-Augmented Generation (RAG). The system ingests financial PDFs/Excel files, enables natural language querying via MCP (Model Context Protocol), and provides accurate answers with source citations.

**Current Status:** Epic 2 - Phase 1 (PDF Optimization) ready to start (Post-Week 0 Integration Spike, Post-Epic 2 Strategic Pivot)

**Target:** ~600-800 lines of Python code across 15 files

**⚠️ STRATEGIC PIVOT (2025-10-19):** Epic 2 redefined following element-aware chunking failure (42% accuracy vs 56% baseline). Now implementing staged RAG architecture enhancement with decision gates. See `story-2.2-pivot-analysis/` for full analysis.

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
| PDF Backend | pypdfium | Docling backend (1.7-2.5x speedup, 50-60% memory reduction) ✅ APPROVED |
| Excel Processing | openpyxl + pandas | Tabular data extraction |
| Embeddings | Fin-E5 | Financial domain semantic vectors |
| Vector DB | Qdrant 1.11+ | Vector storage/search |
| MCP Server | FastMCP (MCP Python SDK) | Expose tools via MCP protocol |
| LLM | Claude 3.7 Sonnet | Answer synthesis, reasoning |
| Backend | Python 3.11+ | All application code |
| Containerization | Docker Compose | Local development |
| Testing | pytest + pytest-asyncio | Unit/integration tests |

**Epic 2 Phase 2B (Conditional - 15% probability):** PostgreSQL (only if Phase 2A fixed chunking <70%)

**Epic 2 Phase 2C (Conditional - 5% probability):** Neo4j + PostgreSQL (only if Phase 2B <75%)

**Epic 2 Phase 3 (Conditional - 20% probability):** LangGraph + AWS Strands (only if Phase 2 <85%)

**Phase 4:** AWS (ECS/Fargate), CloudWatch, Terraform

### NOT Approved (Do Not Use)
- ❌ LangChain (use direct SDK calls instead)
- ❌ LlamaIndex (use Qdrant directly)
- ❌ Haystack (use Qdrant directly)
- ❌ Semantic Kernel (use direct SDK calls)
- ❌ Any ORM beyond Pydantic models
- ❌ Redis/Memcached (not needed until Phase 4)
- ❌ Celery/RQ (not needed for monolith)
- ❌ Custom abstraction libraries (write direct code)

**⚠️ NOTE ON LANGGRAPH:** LangGraph IS conditionally approved for Epic 2 Phase 3 (Agentic Coordination) - ONLY if Phase 2 achieves <85% accuracy. Do NOT use LangGraph for Epic 1 or Phase 2A/2B/2C implementations.

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
├── tests/                     # All tests consolidated here (2025-10-28, organized 2025-10-28)
│   ├── unit/                  # ~200 unit tests (no external dependencies)
│   │   ├── test_shared_*.py   # Core shared module tests
│   │   ├── test_ac*.py        # Epic 2 Phase 2A acceptance criteria tests
│   │   ├── test_query_classifier.py  # Story 2.10 tests
│   │   ├── test_table_aware_chunking.py  # Story 2.8 tests
│   │   └── ... (other unit tests)
│   ├── integration/           # ~115 integration tests (requires Qdrant/PostgreSQL)
│   │   ├── test_sql_routing.py  # Story 2.13 SQL routing tests
│   │   ├── test_ac3_ground_truth.py  # NFR6/NFR7 accuracy validation
│   │   └── ... (other integration tests)
│   ├── e2e/                   # ~28 end-to-end tests
│   ├── fixtures/              # Test fixtures and sample data
│   ├── conftest.py            # Shared pytest configuration
│   └── ground_truth.json      # Accuracy validation test set
├── scripts/
│   ├── setup-dev.sh
│   └── init-qdrant.py
├── docs/                      # Architecture & PRD (sharded)
├── docker-compose.yml
├── pyproject.toml             # UV/pip dependencies (PEP 735)
└── README.md
```

---

## Development Commands

### Environment Setup (When Ready)
```bash
# Install dependencies (UV - recommended, 10-100x faster than pip)
uv sync --all-groups

# Alternative: pip (slower, limited PEP 735 support)
pip install -e ".[dev,test]"

# Start Qdrant + services
docker-compose up -d

# Initialize Qdrant collection
python scripts/init-qdrant.py

# Run tests
uv run pytest

# Run MCP server (local testing)
uv run python -m raglite.main
```

### Testing

**Test Suite:** ~358 tests consolidated in `tests/` directory (updated 2025-10-28, organized 2025-10-28)

**Structure:** Clean directory hierarchy matching VS Code Test Explorer and CI workflow

**Slow Tests:** 12 tests marked with `@pytest.mark.slow` (excluded from VS Code by default, included in CI)

```bash
# All tests (fast - excludes slow tests marked with @pytest.mark.slow)
uv run pytest tests/

# Unit tests only (~200 tests, <2 min)
uv run pytest tests/unit/

# Integration tests (~115 tests, 5-10 min with 10-page PDF)
uv run pytest tests/integration/ -m "not slow"

# E2E tests (~28 tests)
uv run pytest tests/e2e/

# Ground truth accuracy validation (NFR6/NFR7)
uv run python scripts/run-accuracy-tests.py

# With coverage
uv run pytest --cov=raglite --cov-report=html
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

### ✅ Completed: Week 0 - Integration Spike

**Story:** `docs/stories/0.1.week-0-integration-spike.md` - **COMPLETE**

**Result:** Technology stack validated ✅
- Docling + Fin-E5 + Qdrant + FastMCP integration successful
- Baseline accuracy established
- **Decision:** GO to Epic 2 implementation

---

### Current Phase: Epic 2 - Advanced RAG Architecture Enhancement

**⚠️ STRATEGIC PIVOT:** Epic 2 redefined following element-aware chunking failure (42% vs 56% baseline). New staged approach with decision gates.

**Timeline:** 2-3 weeks (best case) to 18 weeks (worst case)

**Goal:** Achieve minimum 70% retrieval accuracy to unblock Epic 3-5

---

#### Epic 2 - Phase 1: PDF Ingestion Performance Optimization (STARTING NOW - 1-2 days)

**Status:** ✅ APPROVED - Ready to implement

**Stories:**
- Story 2.1: Implement pypdfium Backend (4 hours)
- Story 2.2: Implement Page-Level Parallelism (4 hours)

**Goal:** 1.7-2.5x speedup (8.2 min → 3.3-4.8 min for 160-page PDF)

**Success Criteria:**
- ✅ 1.7-2.5x speedup validated
- ✅ 97.9% table accuracy maintained
- ✅ 50-60% memory reduction

---

#### Epic 2 - Phase 2A: Fixed Chunking + Metadata (1-2 weeks) - PRIMARY PATH

**Status:** Pending (starts after Phase 1)

**Probability:** 80% success (research-validated: 68-72% accuracy)

**Stories:**
- Story 2.3: Refactor Chunking to Fixed 512-Token (3 days)
- Story 2.4: Add LLM Contextual Metadata (2 days)
- Story 2.5: AC3 Validation ≥70% - DECISION GATE (2-3 days)

**Decision Gate (T+17, Week 3 Day 3):**
- IF ≥70% accuracy → Epic 2 COMPLETE ✅
- IF <70% accuracy → Phase 2B (Structured Multi-Index)

---

#### Epic 2 - Phase 2B: Structured Multi-Index (3-4 weeks) - CONTINGENCY

**Trigger:** ONLY if Phase 2A <70% (15% probability)

**Goal:** 70-80% accuracy via PostgreSQL + Qdrant + cross-encoder

**Decision Gate:** IF ≥75% → Epic 2 complete, IF <70% → Phase 2C

---

#### Epic 2 - Phase 2C: Hybrid Architecture (6 weeks) - CONTINGENCY

**Trigger:** ONLY if Phase 2B <75% (5% probability)

**Goal:** 75-92% accuracy via Neo4j + PostgreSQL + Qdrant

**Decision Gate:** Epic 2 complete when ≥80%

---

#### Epic 2 - Phase 3: Agentic Coordination (2-16 weeks, staged) - OPTIONAL

**Trigger:** ONLY if Phase 2 <85% (20% probability)

**Goal:** 90-95% accuracy via LangGraph + AWS Strands multi-agent orchestration

**Decision Gate:** Epic 2 complete when ≥90%

---

### Epic 3: Intelligence Features (Future)
- Forecasting (Prophet + LLM)
- Anomaly detection
- Trend analysis
- **Prerequisites:** Epic 2 complete (≥70% accuracy)

### Epic 4-5: Production & Real-Time Operations (Future)
- AWS deployment (ECS/Fargate)
- Monitoring (CloudWatch)
- Performance optimization
- **Prerequisites:** Epic 3 complete

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

## Automated Slash Command Usage

### Proactive Command Invocation Rules

**CRITICAL:** Use these slash commands AUTOMATICALLY when their trigger conditions are met. Do NOT wait for explicit user requests.

#### Development Workflow Automation

**When CI/CD Pipeline Fails:**
- Trigger: GitHub Actions failures, quality gate violations, CI errors mentioned
- Action: Automatically invoke `/ci_orchestrate` or suggest it prominently
- Example: "CI is failing" → Use `/ci_orchestrate --fix-all`

**When Tests Fail:**
- Trigger: pytest failures, test errors, unit/integration/API test issues mentioned
- Action: Automatically invoke `/test_orchestrate` or suggest it prominently
- Example: "Fix the failing tests" → Use `/test_orchestrate --run-first`

**When Creating Pull Requests:**
- Trigger: User mentions "create PR", "pull request", "ready to merge"
- Action: Automatically invoke `/pr create [story-id]` if applicable
- Example: "Create a PR for story 2.1" → Use `/pr create story 2.1`

**When Making Commits:**
- Trigger: User says "commit these changes", "ready to commit", multiple files modified
- Action: Automatically invoke `/commit_orchestrate` with quality checks
- Example: "Commit the changes" → Use `/commit_orchestrate --quality-first`

**When Session Needs Continuation:**
- Trigger: Long task completion, end of work session, context handoff needed
- Action: Automatically invoke `/nextsession` to generate continuation prompt
- Example: Near token limit or work pause → Use `/nextsession`

**When Parallelizing Work:**
- Trigger: Multiple independent tasks, batch operations, parallel fixes needed
- Action: Automatically invoke `/parallelize` or `/parallelize_agents`
- Example: "Fix all linting issues" → Use `/parallelize_agents --strategy=lint`

#### Recognition Patterns

**CI Failure Indicators:**
- "CI failing", "GitHub Actions failing", "quality gates"
- "linting errors", "type errors", "security scan failed"
- "pipeline broken", "checks failing"

**Test Failure Indicators:**
- "tests failing", "pytest errors", "test suite broken"
- "API tests failing", "database tests failing"
- "coverage dropping", "test errors"

**PR Workflow Indicators:**
- "create PR", "pull request", "merge to main"
- "PR status", "ready to merge", "PR for story X"

**Commit Workflow Indicators:**
- "commit changes", "git commit", "ready to commit"
- "save changes", "checkpoint", "create commit"

**Parallelization Indicators:**
- "fix all", "batch fix", "multiple files"
- "parallel", "at once", "all errors"

### Command Selection Logic

**Decision Tree:**
1. Is there a CI/CD failure? → `/ci_orchestrate`
2. Are there test failures (without CI context)? → `/test_orchestrate`
3. Is user creating/managing PRs? → `/pr [action]`
4. Is user ready to commit? → `/commit_orchestrate`
5. Is work parallelizable? → `/parallelize_agents`
6. Does session need continuation? → `/nextsession`

**Priority Order (if multiple applicable):**
1. CI failures (most critical - blocks merges)
2. Test failures (blocks development)
3. PR operations (workflow progression)
4. Commit operations (save work)
5. Parallelization (efficiency gains)

### Guardrails

**Do NOT auto-invoke commands when:**
- User explicitly specifies a different approach
- User says "--no-chain" or "don't automate"
- Command was just used in last 3 messages (avoid loops)
- Uncertainty about user intent (ask first)
- User is exploring/debugging manually

**DO auto-invoke commands when:**
- Failure patterns clearly match command purpose
- User intent is unambiguous
- Efficiency gain is significant (>5 minutes saved)
- User has used similar commands before in session
- Pattern matches 2+ indicators from recognition list

### Chain Invocation Intelligence

**Automatic Command Chaining:**
- `/ci_orchestrate` detects test failures → auto-chain to `/test_orchestrate`
- `/test_orchestrate` succeeds with changes → auto-chain to `/commit_orchestrate`
- `/commit_orchestrate` succeeds → optionally suggest `/pr create`

**Chain Prevention:**
- Respect `--no-chain` flag in any command
- Stop after 3-level depth (prevent infinite loops)
- Stop if user interrupts or provides new direction

---

## Quality Gates & Testing

**Test Suite (Updated 2025-10-28):** ~372 tests consolidated in `tests/` directory

### Test Organization

- **Unit Tests** (`tests/unit/`): ~200 tests, no external dependencies
  - Core functionality: ingestion, retrieval, search, MCP server
  - Epic 2 features: table-aware chunking, query classification, SQL routing
  - Story-specific validation: Stories 2.8-2.14 (SQL table search, fuzzy matching)

- **Integration Tests** (`tests/integration/`): ~115 tests, requires Qdrant/PostgreSQL
  - End-to-end pipelines with real dependencies
  - Multi-index search, hybrid search, SQL table retrieval
  - Epic 2 Phase 2A validation

- **E2E Tests** (`tests/e2e/`): ~28 tests
  - Full system validation with ground truth queries
  - MCP protocol compliance

### NFR Validation (Automated in CI)

**NFR6:** 90%+ retrieval accuracy on test set
- Validated in: `tests/integration/test_ac3_ground_truth.py`
- Ground truth: `tests/ground_truth.json` (50+ Q&A pairs)

**NFR7:** 95%+ source attribution accuracy
- Validated in: `tests/integration/test_accuracy_validation.py`

**NFR13:** Query response time <5s p50, <15s p95
- Validated in: `tests/performance/` (when implemented)

### Test Coverage
- Target: 80%+ unit test coverage (enforced in CI)
- Integration tests for end-to-end flows
- Accuracy regression tests in CI/CD
- Test count validation (prevents shadow test suites)

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

## Implementation Notes

### Table-Aware Chunking Strategy (Story 2.8)

**Status:** ✅ IMPLEMENTED (2025-10-25)

**Problem:** Fixed 512-token chunking splits tables across 8.6 chunks on average, destroying semantic coherence and causing 40% table query accuracy.

**Solution:** Table-aware chunking with 4096-token threshold

**Implementation:**
- **File:** `raglite/ingestion/pipeline.py`
- **Function:** `split_large_table_by_rows()` (lines 1605-1738)
- **Function:** `chunk_by_docling_items()` modified (lines 1741-1936)

**Key Decisions:**
1. **4096 Token Threshold** (AC1):
   - Tables <4096 tokens kept intact as single chunks
   - Significantly reduces fragmentation (8.6 → 1.2 chunks per table)

2. **Row-Based Splitting** (AC2):
   - Large tables >4096 tokens split by logical rows
   - Column headers duplicated in each chunk
   - Table context prefix: "Table {index} (Part {n} of {total}): {caption}"

3. **Metadata Preservation** (AC1):
   - All table chunks marked with `section_type='Table'`
   - Enables table-specific retrieval and filtering

**Expected Impact:**
- Chunks per table: 8.6 → 1.2 (-86%)
- Table query accuracy: 40% → 75% (+35pp)
- Overall accuracy: 52% → 65% (+13pp)

**Validation:**
- Unit tests: `raglite/tests/unit/test_table_aware_chunking.py`
- Validation script: `scripts/test-table-aware-chunking.py`
- Re-ingestion script: `scripts/reingest-with-table-aware-chunking.py`
- Dilution analysis: `scripts/analyze-semantic-dilution.py`

**Trade-Offs:**
- Larger table chunks may exhibit semantic dilution
- Monitoring via AC5 dilution detection script
- Threshold tunable via Story 2.8.1 if needed

---

## Current Next Steps

**IMMEDIATE (T+0 to T+2):**

1. ✅ **Week 0 Integration Spike COMPLETE** - Technology stack validated
2. ✅ **Sprint Change Proposal APPROVED** - Epic 2 strategic pivot approved by PM + User
3. ✅ **Documentation Updates COMPLETE** - PRD, Architecture, Tech Stack all updated
4. **START Epic 2 Phase 1 Implementation** (T+1):
   - Story 2.1: Implement pypdfium Backend (4 hours)
   - Story 2.2: Implement Page-Level Parallelism (4 hours)
   - Validate 1.7-2.5x speedup

**SHORT-TERM (T+3 to T+17 - Weeks 2-3):**

5. **Epic 2 Phase 2A Implementation** (1-2 weeks):
   - Story 2.3: Fixed 512-token chunking (3 days)
   - Story 2.4: LLM contextual metadata (2 days)
   - Story 2.5: AC3 validation ≥70% (2-3 days)

6. **DECISION GATE (T+17, Week 3 Day 3)**:
   - IF ≥70% accuracy → **Epic 2 COMPLETE** → Proceed to Epic 3 planning
   - IF <70% accuracy → Phase 2B (Structured Multi-Index) - PM approval required

**For full implementation details, see:**
- `docs/prd/epic-2-advanced-rag-enhancements.md` - Epic 2 stories and acceptance criteria
- `docs/architecture/8-phased-implementation-strategy-v11-simplified.md` - Phased approach
- `story-2.2-pivot-analysis/` - Complete strategic pivot analysis and Sprint Change Proposal
