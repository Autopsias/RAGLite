# Story 7.4: Refactor main.py MCP Module (3,741 LOC -> <500 LOC per file)

**Epic:** 7 - Technical Debt & Code Quality
**Sprint Change Proposal:** SCP-2025-12-10-002
**Status:** Done
**Priority:** P0 (Critical - Largest Production File in Codebase)
**Estimated Effort:** 2.5 days (production) + 0.5 days (test updates)
**Actual Effort:** TBD

---

## User Story

As a developer, I want `raglite/main.py` to be split into organized modules under 500 LOC each, so that AI assistants can comprehend the full file context, provide better suggestions, and make refactoring safer.

---

## Context

The `raglite/main.py` file is currently **3,741 lines** - the **LARGEST PRODUCTION FILE IN THE CODEBASE**. This is 7.5x the 500 LOC limit established for optimal AI comprehension.

### Why This File?

Per the File Size Refactoring Briefing (`docs/analysis/file-size-refactoring-briefing.md`):

1. **Largest production file** - At 3,741 LOC, it's the single biggest file and primary entry point
2. **High change frequency** - New MCP tools and features are added to this file regularly
3. **Clear split boundaries** - 16 MCP tools with distinct responsibilities make natural module boundaries
4. **Critical path** - All MCP client interactions flow through this file

### Current Structure Analysis (3,741 LOC)

| Component | Lines | Purpose |
|-----------|-------|---------|
| **Imports/Setup** | ~90 | Module imports, FastMCP initialization |
| **Request/Response Models** | ~50 | ExternalDataQueryRequest, ExternalDataPoint, etc. |
| **Ingestion Tools** | ~680 | ingest_financial_document, ingest_financial_document_async, get_ingestion_status |
| **Query Tools** | ~500 | query_financial_documents, analytical_query_financial_documents |
| **Forecast Tools** | ~720 | get_financial_forecast, parse_forecast_query, helpers |
| **Insights Tools** | ~550 | get_financial_insights, parse_insights_query, format_insights_for_display |
| **External Data Tools** | ~400 | query_external_data, refresh_external_data, helpers |
| **Admin Tools** | ~370 | manage_model_weights, retrain_forecasting_models |
| **Validation Tools** | ~270 | validate_forecasting_accuracy, list_available_regressors, get_regressor_data |
| **Health Check** | ~60 | check_database_health |
| **Server Entry Point** | ~50 | main(), scheduler helpers |

### MCP Tools Inventory (16 Tools)

| Tool Name | Estimated LOC | Category |
|-----------|---------------|----------|
| `ingest_financial_document` | ~330 | Ingestion |
| `ingest_financial_document_async` | ~340 | Ingestion |
| `get_ingestion_status` | ~65 | Ingestion |
| `query_financial_documents` | ~130 | Query |
| `analytical_query_financial_documents` | ~470 | Query |
| `get_financial_forecast` | ~450 | Forecast |
| `get_financial_insights` | ~275 | Insights |
| `refresh_external_data` | ~125 | External Data |
| `query_external_data` | ~85 | External Data |
| `check_database_health` | ~60 | Health |
| `manage_model_weights` | ~125 | Admin |
| `retrain_forecasting_models` | ~240 | Admin |
| `validate_forecasting_accuracy` | ~170 | Validation |
| `list_available_regressors` | ~70 | Validation |
| `get_regressor_data` | ~90 | Validation |

---

## Acceptance Criteria

### AC1: File Size Reduction
**Given** the `raglite/main.py` file exceeds 500 LOC (currently 3,741)
**When** the refactoring is complete
**Then**:
- [ ] `raglite/main.py` reduced to <300 LOC (entry point only)
- [ ] All new modules are <500 LOC each
- [ ] Ideal target: 200-400 LOC per module

### AC2: New Module Structure
**Given** MCP tools are currently monolithic in main.py
**When** creating the new modular structure
**Then** create `raglite/mcp/` package with organized modules:
- [ ] `raglite/main.py` (~200 LOC) - Entry point, FastMCP init, server startup
- [ ] `raglite/mcp/__init__.py` - Package exports
- [ ] `raglite/mcp/models.py` (~100 LOC) - Request/response models (ExternalDataQueryRequest, etc.)
- [ ] `raglite/mcp/tools/__init__.py` - Tool registration
- [ ] `raglite/mcp/tools/ingestion.py` (~450 LOC) - 3 ingestion tools
- [ ] `raglite/mcp/tools/query.py` (~450 LOC) - 2 query tools
- [ ] `raglite/mcp/tools/forecast.py` (~500 LOC) - 1 forecast tool + helpers
- [ ] `raglite/mcp/tools/insights.py` (~400 LOC) - 1 insights tool + helpers
- [ ] `raglite/mcp/tools/external_data.py` (~350 LOC) - 2 external data tools + helpers
- [ ] `raglite/mcp/tools/admin.py` (~380 LOC) - 2 admin tools
- [ ] `raglite/mcp/tools/validation.py` (~350 LOC) - 3 validation tools
- [ ] `raglite/mcp/tools/health.py` (~100 LOC) - 1 health check tool

### AC3: Functionality Preserved
**Given** the existing MCP tools serve production traffic
**When** tool extraction is complete
**Then**:
- [ ] All 16 MCP tools remain functional
- [ ] All existing tests pass unchanged
- [ ] No behavior changes to tool logic
- [ ] MCP protocol compliance maintained

### AC4: Backward Compatibility
**Given** other modules may import from `raglite.main`
**When** refactoring the module structure
**Then**:
- [ ] Add backward-compatible re-exports in main.py
- [ ] Document deprecation path for direct main.py imports
- [ ] No breaking changes to external consumers

### AC5: CI Compatibility
**Given** CI pipeline tests MCP server functionality
**When** running in GitHub Actions
**Then**:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] MCP server starts correctly
- [ ] Test coverage unchanged or improved

### AC6: Documentation
**Given** the refactored structure changes module organization
**When** updating documentation
**Then**:
- [ ] Module docstrings explain tool purposes
- [ ] Update architecture docs referencing old structure
- [ ] Developer notes document new structure

---

## Technical Design

### Target Directory Structure

```
raglite/
  main.py                           # ~200 LOC - Entry point, FastMCP init
  mcp/
    __init__.py                     # ~50 LOC - Package exports, tool registration
    models.py                       # ~100 LOC - Request/Response Pydantic models
    tools/
      __init__.py                   # ~30 LOC - Tool module exports
      ingestion.py                  # ~450 LOC - ingest_*, get_ingestion_status
      query.py                      # ~450 LOC - query_*, analytical_query_*
      forecast.py                   # ~500 LOC - get_financial_forecast + helpers
      insights.py                   # ~400 LOC - get_financial_insights + helpers
      external_data.py              # ~350 LOC - query_external_data, refresh_external_data
      admin.py                      # ~380 LOC - manage_model_weights, retrain_*
      validation.py                 # ~350 LOC - validate_*, list_*, get_regressor_*
      health.py                     # ~100 LOC - check_database_health
```

### Module Responsibilities

| Module | Responsibility | Tools |
|--------|---------------|-------|
| `main.py` | Entry point, FastMCP server init, scheduler lifecycle | None (orchestration only) |
| `mcp/models.py` | Request/response Pydantic models for tools | N/A |
| `mcp/tools/ingestion.py` | Document ingestion (sync, async, status) | 3 tools |
| `mcp/tools/query.py` | Document retrieval queries | 2 tools |
| `mcp/tools/forecast.py` | Financial forecasting with parsing helpers | 1 tool |
| `mcp/tools/insights.py` | Proactive insights with formatting helpers | 1 tool |
| `mcp/tools/external_data.py` | External macro data queries and refresh | 2 tools |
| `mcp/tools/admin.py` | Model weight management, retraining | 2 tools |
| `mcp/tools/validation.py` | Accuracy validation, regressor listing | 3 tools |
| `mcp/tools/health.py` | Database health checks | 1 tool |

### Tool Registration Pattern

```python
# raglite/mcp/__init__.py
"""MCP tools package for RAGLite.

Tools are registered via FastMCP decorators and exported for main.py.
"""
from raglite.mcp.tools.ingestion import (
    ingest_financial_document,
    ingest_financial_document_async,
    get_ingestion_status,
)
from raglite.mcp.tools.query import (
    query_financial_documents,
    analytical_query_financial_documents,
)
from raglite.mcp.tools.forecast import get_financial_forecast
from raglite.mcp.tools.insights import get_financial_insights
from raglite.mcp.tools.external_data import (
    query_external_data,
    refresh_external_data,
)
from raglite.mcp.tools.admin import (
    manage_model_weights,
    retrain_forecasting_models,
)
from raglite.mcp.tools.validation import (
    validate_forecasting_accuracy,
    list_available_regressors,
    get_regressor_data,
)
from raglite.mcp.tools.health import check_database_health

__all__ = [
    "ingest_financial_document",
    "ingest_financial_document_async",
    "get_ingestion_status",
    "query_financial_documents",
    "analytical_query_financial_documents",
    "get_financial_forecast",
    "get_financial_insights",
    "query_external_data",
    "refresh_external_data",
    "manage_model_weights",
    "retrain_forecasting_models",
    "validate_forecasting_accuracy",
    "list_available_regressors",
    "get_regressor_data",
    "check_database_health",
]
```

### FastMCP Server Pattern

```python
# raglite/main.py (after refactoring)
"""RAGLite MCP Server - Model Context Protocol entry point.

Note: Tools have been moved to raglite.mcp.tools.
Import from there for new code.
"""
from fastmcp import FastMCP

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

# Initialize FastMCP server - must be in main for decorator access
mcp = FastMCP("RAGLite")

# Import and register all tools (decorators execute on import)
from raglite.mcp.tools import (  # noqa: E402, F401
    ingestion,
    query,
    forecast,
    insights,
    external_data,
    admin,
    validation,
    health,
)

logger = get_logger(__name__)


def main() -> None:
    """Start the RAGLite MCP server."""
    logger.info("Starting RAGLite MCP server", extra={"version": "1.0"})
    mcp.run()


if __name__ == "__main__":
    main()
```

### Shared MCP Instance Pattern

The FastMCP instance must be created in main.py and imported by tool modules:

```python
# raglite/mcp/tools/ingestion.py
"""Document ingestion MCP tools."""
from raglite.main import mcp  # Import shared MCP instance
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@mcp.tool()
async def ingest_financial_document(...) -> IngestionResult:
    """Ingest a financial document..."""
    ...
```

**Alternative:** Pass mcp instance during tool registration (cleaner dependency injection).

---

## Implementation Tasks

### Task 1: Create Package Structure (AC2)
- [ ] Create `raglite/mcp/` directory
- [ ] Create `raglite/mcp/__init__.py`
- [ ] Create `raglite/mcp/tools/` directory
- [ ] Create `raglite/mcp/tools/__init__.py`
- [ ] Verify imports work: `python -c "import raglite.mcp"`

### Task 2: Extract Models (AC1, AC2)
- [ ] Create `raglite/mcp/models.py`
- [ ] Move ExternalDataQueryRequest, ExternalDataPoint, ExternalDataQueryResponse
- [ ] Move ModelWeightAdminRequest, ModelWeightAdminResponse
- [ ] Update imports in main.py
- [ ] Verify tests pass

### Task 3: Extract Ingestion Tools (AC1, AC2)
- [ ] Create `raglite/mcp/tools/ingestion.py`
- [ ] Move ingest_financial_document tool
- [ ] Move ingest_financial_document_async tool
- [ ] Move get_ingestion_status tool
- [ ] Move _perform_forecast_refresh helper
- [ ] Update imports
- [ ] Verify tests pass: `pytest tests/unit/test_base64_ingestion.py tests/integration/test_mcp_async_ingestion.py -v`

### Task 4: Extract Query Tools (AC1, AC2)
- [ ] Create `raglite/mcp/tools/query.py`
- [ ] Move query_financial_documents tool
- [ ] Move analytical_query_financial_documents tool
- [ ] Update imports
- [ ] Verify tests pass: `pytest tests/unit/test_mcp_analytical_tool.py tests/integration/test_analytical_query_tool.py -v`

### Task 5: Extract Forecast Tool (AC1, AC2)
- [ ] Create `raglite/mcp/tools/forecast.py`
- [ ] Move get_financial_forecast tool
- [ ] Move parse_forecast_query helper function
- [ ] Update imports
- [ ] Verify tests pass: `pytest tests/unit/test_forecast_query_tool.py tests/integration/test_forecast_query_integration.py -v`

### Task 6: Extract Insights Tool (AC1, AC2)
- [ ] Create `raglite/mcp/tools/insights.py`
- [ ] Move get_financial_insights tool
- [ ] Move parse_insights_query helper function
- [ ] Move format_insights_for_display helper function
- [ ] Update imports
- [ ] Verify tests pass: `pytest tests/unit/test_proactive_insights_mcp.py tests/integration/test_proactive_insights_mcp_integration.py -v`

### Task 7: Extract External Data Tools (AC1, AC2)
- [ ] Create `raglite/mcp/tools/external_data.py`
- [ ] Move query_external_data tool
- [ ] Move refresh_external_data tool
- [ ] Move _parse_date_range, _get_visualization_hint, _query_single_source, _query_all_sources, _format_response helpers
- [ ] Update imports
- [ ] Verify tests pass: `pytest tests/unit/test_external_data_mcp.py tests/integration/test_external_data_mcp.py -v`

### Task 8: Extract Admin Tools (AC1, AC2)
- [ ] Create `raglite/mcp/tools/admin.py`
- [ ] Move manage_model_weights tool
- [ ] Move retrain_forecasting_models tool
- [ ] Update imports
- [ ] Verify tests pass

### Task 9: Extract Validation Tools (AC1, AC2)
- [ ] Create `raglite/mcp/tools/validation.py`
- [ ] Move validate_forecasting_accuracy tool
- [ ] Move list_available_regressors tool
- [ ] Move get_regressor_data tool
- [ ] Update imports
- [ ] Verify tests pass: `pytest tests/unit/test_mcp_validation_tools.py tests/integration/test_mcp_validation_integration.py -v`

### Task 10: Extract Health Tool (AC1, AC2)
- [ ] Create `raglite/mcp/tools/health.py`
- [ ] Move check_database_health tool
- [ ] Update imports
- [ ] Verify tests pass

### Task 11: Update Main Entry Point (AC1, AC4)
- [ ] Reduce main.py to entry point only (~200 LOC)
- [ ] Keep FastMCP initialization
- [ ] Keep main() function
- [ ] Keep scheduler helpers (_start_scheduler_sync, _shutdown_scheduler_sync)
- [ ] Add backward-compatible re-exports for DocumentProcessingError
- [ ] Verify MCP server starts: `uv run python -m raglite.main --help`

### Task 12: Update Test Imports (AC3, AC5)
- [ ] Update imports in test files that import from main.py
- [ ] Prefer importing from new module locations
- [ ] Add shim imports in main.py for backward compatibility
- [ ] Verify all tests pass: `pytest tests/ -v`

### Task 13: File Size Validation (AC1)
- [ ] Run: `wc -l raglite/main.py raglite/mcp/*.py raglite/mcp/tools/*.py`
- [ ] Verify all files <500 LOC
- [ ] Document final line counts in completion notes

---

## Dev Notes

### Refactoring Rules

Per [File Size Refactoring Briefing](../../analysis/file-size-refactoring-briefing.md):

1. **Extract one tool module at a time** - Run tests after each extraction
2. **Do NOT batch changes** - Incremental commits keep changes reviewable
3. **Run full test suite** - Prevent hidden regressions
4. **Preserve FastMCP decorators** - @mcp.tool() must work with shared instance

### MCP Instance Sharing

The FastMCP `mcp` instance must be accessible to all tool modules. Options:

**Option A (Recommended):** Create mcp in main.py, import in tool modules
```python
# raglite/main.py
mcp = FastMCP("RAGLite")

# raglite/mcp/tools/query.py
from raglite.main import mcp
@mcp.tool()
async def query_financial_documents(...):
```

**Option B:** Create mcp in mcp/__init__.py, import in main.py
```python
# raglite/mcp/__init__.py
from fastmcp import FastMCP
mcp = FastMCP("RAGLite")

# raglite/main.py
from raglite.mcp import mcp
```

### Circular Import Prevention

- Create mcp instance at package level (either main.py or mcp/__init__.py)
- Tool modules import mcp from central location
- Main.py imports tool modules AFTER mcp is created
- Use `from raglite.main import mcp` pattern with care for import order

### Test Files Affected

Related test files importing from main.py (~1,430 LOC total):
- `tests/unit/test_main.py` (320 LOC)
- `tests/integration/test_main_integration.py` (201 LOC)
- `tests/integration/test_mcp_response_validation.py` (426 LOC)
- `tests/integration/test_mcp_server.py` (167 LOC)
- `tests/integration/test_mcp_async_ingestion.py` (316 LOC)

All test files are under 500 LOC - no test splitting required.

### Commands for Validation

```bash
# Count lines in all new modules
wc -l raglite/main.py raglite/mcp/*.py raglite/mcp/tools/*.py

# Verify MCP server starts
uv run python -c "from raglite.main import mcp; print(f'Tools: {len(mcp._tools)}')"

# Verify tool registration
uv run python -c "from raglite.main import mcp; print([t.name for t in mcp._tools])"

# Run specific tool tests
pytest tests/unit/test_main.py -v
pytest tests/integration/test_mcp_server.py -v

# Run full test suite
pytest tests/ -v

# Check coverage
pytest tests/ --cov=raglite/main --cov=raglite/mcp --cov-report=term-missing
```

### Incremental Commit Strategy

```bash
# Commit after each module extraction
git commit -m "refactor(mcp): create mcp package structure"
git commit -m "refactor(mcp): extract models to mcp/models.py"
git commit -m "refactor(mcp): extract ingestion tools to mcp/tools/ingestion.py"
git commit -m "refactor(mcp): extract query tools to mcp/tools/query.py"
git commit -m "refactor(mcp): extract forecast tool to mcp/tools/forecast.py"
git commit -m "refactor(mcp): extract insights tool to mcp/tools/insights.py"
git commit -m "refactor(mcp): extract external_data tools to mcp/tools/external_data.py"
git commit -m "refactor(mcp): extract admin tools to mcp/tools/admin.py"
git commit -m "refactor(mcp): extract validation tools to mcp/tools/validation.py"
git commit -m "refactor(mcp): extract health tool to mcp/tools/health.py"
git commit -m "refactor(mcp): update main.py to entry point only"
```

### Risk Mitigation

- **FastMCP decorator registration**: Verify tools are registered by checking `mcp._tools` after imports
- **Import order**: FastMCP instance must exist before tool imports
- **Circular imports**: Test imports work with `python -c "import raglite.main"`
- **MCP protocol compliance**: Verify server responds correctly to MCP requests
- **Scheduler lifecycle**: Keep scheduler helpers in main.py for lifecycle management

---

## Testing Requirements

### Before Refactoring
- Run: `pytest tests/ --collect-only -q | tail -5`
- Record: Total test count (expected: ~372 tests)
- Record: `wc -l raglite/main.py` (expected: 3,741 LOC)

### After Each Extraction
- Run: `pytest tests/unit/ -v --tb=short`
- Run: `pytest tests/integration/ --skip-ingestion -v --tb=short`
- Verify: No failures, no import errors
- Verify: MCP tools still registered

### Final Validation
- Run: `pytest tests/ -v`
- Run: `uv run python -m raglite.main` (verify server starts)
- Verify: Full test suite green
- Verify: CI pipeline passes
- Verify: `wc -l raglite/main.py` < 300 LOC

---

## Dependencies

- **Story 7.1** (split_test_external_data_clients) - COMPLETE
- **Story 7.2** (split_root_conftest) - COMPLETE
- **Story 7.3** (split_integration_conftest) - COMPLETE

This story has no blockers and can proceed immediately.

---

## Success Metrics

1. **File size compliance**: main.py <300 LOC, all new files <500 LOC
2. **Tool count preservation**: All 16 MCP tools remain functional
3. **Test count preservation**: Same number of tests before/after (~372)
4. **Coverage maintained**: No coverage regression
5. **CI green**: All pipelines pass
6. **Server operational**: MCP server starts and responds correctly

---

## References

- [File Size Refactoring Briefing](../../analysis/file-size-refactoring-briefing.md)
- [File Size Limits Rule](../../.claude/rules/file-size-limits.md)
- [Complete Reference Implementation](../../architecture/6-complete-reference-implementation.md)
- [Sprint Status](../sprint-status.yaml)

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

TBD

### Debug Log References

N/A

### Completion Notes List

TBD

### File List

**Files to Modify:**
- `raglite/main.py` (3,741 LOC -> ~200 LOC)

**Files to Create:**
- `raglite/mcp/__init__.py` (~50 LOC)
- `raglite/mcp/models.py` (~100 LOC)
- `raglite/mcp/tools/__init__.py` (~30 LOC)
- `raglite/mcp/tools/ingestion.py` (~450 LOC)
- `raglite/mcp/tools/query.py` (~450 LOC)
- `raglite/mcp/tools/forecast.py` (~500 LOC)
- `raglite/mcp/tools/insights.py` (~400 LOC)
- `raglite/mcp/tools/external_data.py` (~350 LOC)
- `raglite/mcp/tools/admin.py` (~380 LOC)
- `raglite/mcp/tools/validation.py` (~350 LOC)
- `raglite/mcp/tools/health.py` (~100 LOC)

**Test Files to Update (imports only):**
- `tests/unit/test_main.py` (320 LOC)
- `tests/integration/test_main_integration.py` (201 LOC)
- Other test files importing from `raglite.main`

### Change Log

TBD
