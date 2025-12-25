# ATDD Checklist: Story 7.4 - Refactor main.py MCP Module

**Story:** 7-4-refactor-main-py-mcp-module
**Epic:** 7 - Technical Debt & Code Quality
**Test File:** `tests/unit/test_story_7_4_mcp_refactor.py`
**TDD Phase:** RED (tests expected to fail until implementation complete)
**Generated:** 2025-12-18

---

## Test Summary

| Category | Tests | Status |
|----------|-------|--------|
| AC1: File Size Reduction | 12 | RED (failing) |
| AC2: Module Structure | 14 | RED (failing) |
| AC3: Functionality Preserved | 5 | GREEN (passing - verifies current state) |
| AC4: Backward Compatibility | 4 | 2 GREEN, 2 RED |
| AC5: CI Compatibility | 4 | 2 GREEN, 2 RED |
| AC6: Documentation | 10 | 1 GREEN, 9 RED |
| Integrity Tests | 2 | RED (failing) |
| **Total** | **49** | **37 RED, 12 GREEN** |

---

## AC1: File Size Reduction

**Status:** RED (12 failing)

| Test ID | Description | Status | Expected Behavior |
|---------|-------------|--------|-------------------|
| TEST-AC-7.4.1.1 | main.py under 300 lines | FAIL | main.py <300 LOC after refactoring |
| TEST-AC-7.4.1.2 | mcp/models.py under 500 lines | FAIL | mcp/models.py must exist and <500 LOC |
| TEST-AC-7.4.1.3 | ingestion.py under 500 lines | FAIL | mcp/tools/ingestion.py must exist |
| TEST-AC-7.4.1.3 | query.py under 500 lines | FAIL | mcp/tools/query.py must exist |
| TEST-AC-7.4.1.3 | forecast.py under 500 lines | FAIL | mcp/tools/forecast.py must exist |
| TEST-AC-7.4.1.3 | insights.py under 500 lines | FAIL | mcp/tools/insights.py must exist |
| TEST-AC-7.4.1.3 | external_data.py under 500 lines | FAIL | mcp/tools/external_data.py must exist |
| TEST-AC-7.4.1.3 | admin.py under 500 lines | FAIL | mcp/tools/admin.py must exist |
| TEST-AC-7.4.1.3 | validation.py under 500 lines | FAIL | mcp/tools/validation.py must exist |
| TEST-AC-7.4.1.3 | health.py under 500 lines | FAIL | mcp/tools/health.py must exist |
| TEST-AC-7.4.1.4 | Ideal target 200-400 LOC | FAIL | 60%+ modules in ideal range |

---

## AC2: New Module Structure

**Status:** RED (14 failing)

| Test ID | Description | Status | Expected Behavior |
|---------|-------------|--------|-------------------|
| TEST-AC-7.4.2.1 | mcp/ package exists | FAIL | raglite/mcp/ directory must exist |
| TEST-AC-7.4.2.2 | mcp/__init__.py exists | FAIL | Package initialization file |
| TEST-AC-7.4.2.3 | mcp/models.py exists | FAIL | Request/response models |
| TEST-AC-7.4.2.4 | mcp/tools/ package exists | FAIL | raglite/mcp/tools/ directory |
| TEST-AC-7.4.2.5 | mcp/tools/__init__.py exists | FAIL | Tools subpackage init |
| TEST-AC-7.4.2.6 | ingestion.py exists | FAIL | 3 ingestion tools |
| TEST-AC-7.4.2.6 | query.py exists | FAIL | 2 query tools |
| TEST-AC-7.4.2.6 | forecast.py exists | FAIL | 1 forecast tool |
| TEST-AC-7.4.2.6 | insights.py exists | FAIL | 1 insights tool |
| TEST-AC-7.4.2.6 | external_data.py exists | FAIL | 2 external data tools |
| TEST-AC-7.4.2.6 | admin.py exists | FAIL | 2 admin tools |
| TEST-AC-7.4.2.6 | validation.py exists | FAIL | 3 validation tools |
| TEST-AC-7.4.2.6 | health.py exists | FAIL | 1 health check tool |

---

## AC3: Functionality Preserved

**Status:** GREEN (5 passing - verifies current functionality)

| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| TEST-AC-7.4.3.1 | MCP server instance available | PASS | Current main.py has mcp instance |
| TEST-AC-7.4.3.2 | All tools importable from main | PASS | Tools currently in main.py |
| TEST-AC-7.4.3.3 | Tools have .fn attribute | PASS | FastMCP decorators working |
| TEST-AC-7.4.3.4 | Tool count preserved (15+) | PASS | Currently 15 tools available |
| TEST-AC-7.4.3.5 | DocumentProcessingError available | PASS | Exception class exists |

**Note:** These tests verify current functionality and will continue passing after refactoring.

---

## AC4: Backward Compatibility

**Status:** 2 GREEN, 2 RED

| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| TEST-AC-7.4.4.1 | DocumentProcessingError re-export | PASS | Currently in main.py |
| TEST-AC-7.4.4.2 | mcp instance from main | PASS | Currently in main.py |
| TEST-AC-7.4.4.3 | Models from mcp package | FAIL | mcp package does not exist |
| TEST-AC-7.4.4.4 | Tools from mcp.tools | FAIL | mcp.tools does not exist |

---

## AC5: CI Compatibility

**Status:** 2 GREEN, 2 RED

| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| TEST-AC-7.4.5.1 | main module imports | PASS | Current main.py imports fine |
| TEST-AC-7.4.5.2 | mcp package imports | FAIL | Package does not exist |
| TEST-AC-7.4.5.3 | No circular imports | FAIL | Cannot import non-existent modules |
| TEST-AC-7.4.5.4 | main() function exists | PASS | Current main.py has main() |

---

## AC6: Documentation

**Status:** 1 GREEN, 9 RED

| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| TEST-AC-7.4.6.1 | main.py has docstring | PASS | Current main.py documented |
| TEST-AC-7.4.6.2 | mcp/__init__.py has docstring | FAIL | File does not exist |
| TEST-AC-7.4.6.3 | ingestion.py has docstring | FAIL | File does not exist |
| TEST-AC-7.4.6.3 | query.py has docstring | FAIL | File does not exist |
| TEST-AC-7.4.6.3 | forecast.py has docstring | FAIL | File does not exist |
| TEST-AC-7.4.6.3 | insights.py has docstring | FAIL | File does not exist |
| TEST-AC-7.4.6.3 | external_data.py has docstring | FAIL | File does not exist |
| TEST-AC-7.4.6.3 | admin.py has docstring | FAIL | File does not exist |
| TEST-AC-7.4.6.3 | validation.py has docstring | FAIL | File does not exist |
| TEST-AC-7.4.6.3 | health.py has docstring | FAIL | File does not exist |

---

## Integrity Tests

**Status:** RED (2 failing)

| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| TEST-INTEGRITY-7.4.1 | All tools registered to mcp | FAIL | Cannot import tool modules |
| TEST-INTEGRITY-7.4.2 | Models have correct fields | FAIL | mcp.models does not exist |

---

## Implementation Guidance

### Files to Create

1. **raglite/mcp/__init__.py** (~50 LOC)
   - Package exports
   - Tool registration

2. **raglite/mcp/models.py** (~100 LOC)
   - ExternalDataQueryRequest
   - ExternalDataPoint
   - ExternalDataQueryResponse
   - ModelWeightAdminRequest
   - ModelWeightAdminResponse

3. **raglite/mcp/tools/__init__.py** (~30 LOC)
   - Tool module exports

4. **raglite/mcp/tools/ingestion.py** (~450 LOC)
   - ingest_financial_document
   - ingest_financial_document_async
   - get_ingestion_status
   - _perform_forecast_refresh helper

5. **raglite/mcp/tools/query.py** (~450 LOC)
   - query_financial_documents
   - analytical_query_financial_documents

6. **raglite/mcp/tools/forecast.py** (~500 LOC)
   - get_financial_forecast
   - parse_forecast_query helper

7. **raglite/mcp/tools/insights.py** (~400 LOC)
   - get_financial_insights
   - parse_insights_query helper
   - format_insights_for_display helper

8. **raglite/mcp/tools/external_data.py** (~350 LOC)
   - query_external_data
   - refresh_external_data
   - Helper functions

9. **raglite/mcp/tools/admin.py** (~380 LOC)
   - manage_model_weights
   - retrain_forecasting_models

10. **raglite/mcp/tools/validation.py** (~350 LOC)
    - validate_forecasting_accuracy
    - list_available_regressors
    - get_regressor_data

11. **raglite/mcp/tools/health.py** (~100 LOC)
    - check_database_health

### Files to Modify

1. **raglite/main.py** (3,741 -> ~200 LOC)
   - Keep: FastMCP initialization, main() function
   - Keep: Scheduler helpers
   - Add: Backward-compatible re-exports
   - Remove: All tool implementations (move to mcp/tools/)

---

## Test Execution

```bash
# Run all Story 7.4 tests
uv run pytest tests/unit/test_story_7_4_mcp_refactor.py -v

# Run specific AC tests
uv run pytest tests/unit/test_story_7_4_mcp_refactor.py -v -k "AC1"
uv run pytest tests/unit/test_story_7_4_mcp_refactor.py -v -k "AC2"
uv run pytest tests/unit/test_story_7_4_mcp_refactor.py -v -k "AC3"
uv run pytest tests/unit/test_story_7_4_mcp_refactor.py -v -k "AC4"
uv run pytest tests/unit/test_story_7_4_mcp_refactor.py -v -k "AC5"
uv run pytest tests/unit/test_story_7_4_mcp_refactor.py -v -k "AC6"

# Quick summary
uv run pytest tests/unit/test_story_7_4_mcp_refactor.py -v --tb=no
```

---

## Success Criteria

All 49 tests must pass (GREEN) for the story to be considered complete:

- [ ] AC1: All 12 file size tests pass
- [ ] AC2: All 14 module structure tests pass
- [ ] AC3: All 5 functionality preservation tests pass (already passing)
- [ ] AC4: All 4 backward compatibility tests pass
- [ ] AC5: All 4 CI compatibility tests pass
- [ ] AC6: All 10 documentation tests pass
- [ ] Integrity: All 2 integrity tests pass

---

## Notes

- **RED Phase Complete:** Tests are failing as expected
- **Current State:** main.py is 3,741 LOC (7.5x over limit)
- **Target State:** main.py <300 LOC, all modules <500 LOC
- **Passing Tests:** 12 tests verify current functionality that must be preserved
