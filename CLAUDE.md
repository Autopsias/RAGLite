# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!--
  MODULAR RULES: Critical rules are in .claude/rules/ (highest priority)
  - constraints.md      - Anti-over-engineering rules (CRITICAL)
  - database-safety.md  - Production protection rules
  - testing.md          - Test infrastructure (path-scoped to tests/)
  - coding-standards.md - Code patterns and forbidden patterns
  - quality-gates.md    - NFR validation requirements
  - automation.md       - Slash command automation
  - mcp-tools.md        - MCP ingestion patterns
-->

---

## Project Overview

**RAGLite** is a monolithic MVP for an AI-powered financial document analysis system using Retrieval-Augmented Generation (RAG). The system ingests financial PDFs/Excel files, enables natural language querying via MCP (Model Context Protocol), and provides accurate answers with source citations.

**Current Status:** Epic 2 - Phase 1 (PDF Optimization) ready to start

**Target:** ~600-800 lines of Python code across 15 files

**Strategic Pivot:** Epic 2 redefined following element-aware chunking failure (42% vs 56% baseline). Now implementing staged RAG architecture enhancement with decision gates.

---

## Architecture & Documentation

### Primary Documents (Read First)

1. **Architecture (Sharded):** `docs/architecture/`
   - Start with: `1-introduction-vision.md` -> `2-executive-summary.md`
   - **Critical for coding:** `6-complete-reference-implementation.md`
   - Repository structure: `3-repository-structure-monolithic.md`
   - Tech stack: `5-technology-stack-definitive.md`
   - Implementation phases: `8-phased-implementation-strategy-v11-simplified.md`

2. **PRD (Sharded):** `docs/prd/`
   - Entry point: `docs/prd/index.md`
   - Epics: `epic-1-foundation-accurate-retrieval.md` through `epic-5-production-readiness-real-time-operations.md`

3. **BMAD Configuration:** `bmad/core/config.yaml`

### Documentation Structure

- `docs/README.md` - Documentation guide and navigation
- `docs/architecture/` - 30 sharded architecture files
- `docs/prd/` - 15 sharded PRD files
- `docs/front-end-spec/` - MCP response format specifications
- `docs/stories/` - Active user stories
- `docs/qa/` - Quality assurance reports

---

## Technology Stack

**LOCKED - No additions without user approval**

**Source of Truth:** `docs/architecture/5-technology-stack-definitive.md`

| Component | Technology | Purpose |
|-----------|------------|---------|
| PDF Processing | Docling | Extract text/tables (97.9% accuracy) |
| PDF Backend | pypdfium | Docling backend (1.7-2.5x speedup) |
| Excel Processing | openpyxl + pandas | Tabular data extraction |
| Embeddings | Fin-E5 | Financial domain semantic vectors |
| Vector DB | Qdrant 1.11+ | Vector storage/search |
| MCP Server | FastMCP | Expose tools via MCP protocol |
| LLM | Claude 3.7 Sonnet | Answer synthesis, reasoning |
| Backend | Python 3.11+ | All application code |
| Containerization | Docker Compose | Local development |
| Testing | pytest + pytest-asyncio | Unit/integration tests |

**Conditional (Phase 2+):**
- PostgreSQL (if Phase 2A <70%)
- Neo4j (if Phase 2B <75%)
- LangGraph (if Phase 2 <85%)

---

## Repository Structure

```
raglite/
├── raglite/                    # Main package (~600-800 lines)
│   ├── main.py                # MCP server (~200 lines)
│   ├── ingestion/             # Document processing
│   ├── retrieval/             # Search & synthesis
│   ├── forecasting/           # Phase 3
│   ├── insights/              # Phase 3
│   └── shared/                # Utilities
├── tests/                     # All tests (~372 total)
│   ├── unit/                  # ~200 tests
│   ├── integration/           # ~115 tests
│   ├── e2e/                   # ~28 tests
│   └── fixtures/              # Test data
├── scripts/                   # Dev utilities
├── docs/                      # Architecture & PRD
└── docker-compose.yml
```

---

## Development Commands

```bash
# Install dependencies
uv sync --all-groups

# Start services
docker-compose up -d

# Run tests
uv run pytest tests/

# Run MCP server
uv run python -m raglite.main
```

---

## Database Backup & Restore

**Backup location:** `backups/` directory

### Quick Backup

```bash
./scripts/backup-all.sh           # Backup both databases
./scripts/backup-postgresql.sh    # PostgreSQL only (337MB)
./scripts/backup-qdrant.sh        # Qdrant only (497MB)
```

### Restore

```bash
# PostgreSQL
docker exec -i raglite-postgresql psql -U raglite -d raglite < backups/postgresql_backup_YYYYMMDD_HHMMSS.sql

# Qdrant - See backups/README.md for snapshot recovery procedures
```

### When to Backup

- **Before migrations** - Always run `./scripts/backup-all.sh`
- **Before re-ingestion** - Preserve current state
- **Before data cleanup** - Safety checkpoint

See `backups/README.md` for detailed restore instructions and backup inventory.

---

## Implementation Phases

### Completed: Week 0 - Integration Spike
Technology stack validated. Baseline accuracy established.

### Current: Epic 2 - RAG Architecture Enhancement

**Phase 1: PDF Performance** (1-2 days)
- Story 2.1: pypdfium Backend
- Story 2.2: Page-Level Parallelism
- Goal: 1.7-2.5x speedup

**Phase 2A: Fixed Chunking + Metadata** (1-2 weeks)
- Story 2.3: Fixed 512-token chunking
- Story 2.4: LLM contextual metadata
- Story 2.5: AC3 validation >= 70%
- Decision Gate: If >=70% -> Epic 2 complete

**Phase 2B/2C:** Contingency paths (if Phase 2A <70%)

**Phase 3:** Agentic coordination (if Phase 2 <85%)

### Future: Epic 3-5
- Intelligence features (forecasting, anomaly detection)
- AWS deployment (ECS/Fargate)
- Production optimization

---

## BMAD Workflow Integration

Reference agents by role (e.g., "As dev, implement Story 1.1"):

- **dev** - Code implementation
- **sm** - Story/epic management
- **qa** - Test strategy
- **architect** - System design
- **pm** - PRD, prioritization
- **analyst** - Research
- **bmad-master** - General expert

Workflows: `bmad/core/workflows/`, `bmad/bmm/workflows/`

---

## Implementation Notes

### Table-Aware Chunking (Story 2.8) - IMPLEMENTED
- 4096 token threshold for tables
- Row-based splitting with header duplication
- Expected: 8.6 -> 1.2 chunks per table (-86%)

---

## Test Reliability Rules

These rules prevent recurring test failures. Follow them for ALL test-related changes.

### Import Patterns
- **ALWAYS** use lazy-load wrapper functions for external ML libraries (statsmodels, pmdarima, etc.)
- **NEVER** define dataclasses in large utility modules; use dedicated `models.py` files
- **ALWAYS** use `TYPE_CHECKING` guards for cross-module type hints that could cause circular imports

### Mock Patterns
- **ALWAYS** patch wrapper functions, not direct class imports
- **NEVER** patch at the definition location; patch where the object is USED
- **ALWAYS** verify mock call counts match expected behavior

### Test Isolation
- **ALWAYS** use explicit `@pytest.mark.integration` for integration tests
- **NEVER** rely on file path heuristics for fixture activation
- **ALWAYS** ensure session fixtures have explicit skip conditions for unit-only runs

### Docker/Infrastructure
- **ALWAYS** verify Docker container volume mounts before running tests
- **NEVER** assume containers have correct mounts after CI runs (may have stale paths)
- Run `docker inspect <container> --format='{{json .Mounts}}'` to verify

### File Size
- **NEVER** add code to a file already at 450+ LOC without splitting first
- **ALWAYS** split before adding new functionality to large files
- **NEVER** commit new files exceeding 500 LOC without approved exception

### pytest-xdist Type Checks
- **NEVER** use `isinstance()` for custom class identity checks in tests (fails with `-n auto`)
- **ALWAYS** use `__class__.__name__` or `hasattr()` for duck-typing validation
- **NEVER** use `in Enum` checks; use `.name` or `.value` instead

**CI Failure Runbook:** `docs/ci-failure-runbook.md` - Detailed diagnosis and resolution for all CI failure patterns.

---

## Current Next Steps

1. **Epic 2 Phase 1:** pypdfium backend + page parallelism
2. **Epic 2 Phase 2A:** Fixed chunking + metadata
3. **Decision Gate:** Validate >=70% accuracy

**Full details:** `docs/prd/epic-2-advanced-rag-enhancements.md`

---

## References

- **MCP Protocol:** https://modelcontextprotocol.io/
- **FastMCP:** https://github.com/jlowin/fastmcp
- **Docling:** https://github.com/DS4SD/docling
- **Qdrant:** https://qdrant.tech/documentation/
- **Claude API:** https://docs.anthropic.com/
