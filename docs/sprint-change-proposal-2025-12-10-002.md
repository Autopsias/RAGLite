# Sprint Change Proposal: Epic 7 - Technical Debt & Code Quality

**Proposal ID:** SCP-2025-12-10-002
**Created:** 2025-12-10
**Author:** Scrum Master (BMAD Workflow)
**Status:** PENDING APPROVAL

---

## Section 1: Issue Summary

### Problem Statement

The RAGLite codebase has grown to **71 files exceeding the 500 LOC research-backed limit** (27 production, 44 test files), totaling ~59,000+ LOC that needs refactoring. The original architecture specified 600-800 total lines across ~15 files, but the system has grown significantly during Epic 1-6 implementation.

### Discovery Context

- **When:** Identified during code quality analysis on 2025-12-10
- **How:** File size audit using `scripts/check_file_sizes.py`
- **Impact:** Degraded AI-assisted development quality, increased maintenance burden

### Evidence

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Production files >500 LOC | 27 | 0 | -27 |
| Test files >500 LOC | 44 | 0 | -44 |
| Largest file (main.py) | 2,998 LOC | <500 LOC | -2,498 |
| Largest test file | 3,025 LOC | <500 LOC | -2,525 |
| Original architecture target | 600-800 LOC | - | Exceeded ~73x |

### Research Backing

| Source | Finding |
|--------|---------|
| Cursor Forum | ≤300-350 LOC optimal for AI parsing/refactoring |
| Augment Code Research | Beyond 500-800 LOC: more AI mistakes, partial edits |
| Uncle Bob / Clean Code | Average 20-50 LOC, most files <100 LOC |
| Token Economics | 500 LOC ≈ 5,000 tokens (single-prompt comprehension) |

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| Epic 0-4 | Done | NONE - Already complete |
| Epic 5 | Backlog | LOW - Refactoring improves deployability |
| Epic 6 | In-Progress | NONE - Can proceed independently |
| **Epic 7 (NEW)** | Proposed | HIGH - This IS the epic |

### Story Impact

- **Current Stories:** No modifications to existing stories
- **New Stories:** ~40+ stories across 5 batches
- **Dependencies:** Batch 1 (test splits) must complete before production refactoring

### Artifact Conflicts

| Artifact | Conflict | Action Required |
|----------|----------|-----------------|
| PRD | Minor | Add NFR33: "Files shall not exceed 500 LOC" |
| Architecture | Yes | Update Section 3 (Repository Structure) |
| CI/CD | None | File size check job already exists |
| .claude/rules/ | None | file-size-limits.md rule already exists |

### Technical Impact

- **Code Changes:** Refactoring only, no behavior changes
- **Test Changes:** Test reorganization to mirror production structure
- **Infrastructure:** No changes to Qdrant/PostgreSQL/deployment
- **Dependencies:** No new libraries required

---

## Section 3: Recommended Approach

### Selected Path: Create New Epic 7 with Phased Implementation

**Decision:** Direct Adjustment via New Epic

### Rationale

1. **Incremental Risk:** 5 batches allow stopping/adjusting if issues arise
2. **Parallel Execution:** Can run alongside Epic 5/6 work
3. **Immediate Value:** Batch 1 (test splits) enables better test maintenance immediately
4. **No Feature Impact:** Orthogonal to feature development
5. **Enforcement Ready:** CI infrastructure already exists

### Effort Estimate

| Phase | Focus | Estimated Effort |
|-------|-------|------------------|
| Batch 1 | Test infrastructure (3 stories) | 2.5 days |
| Batch 2 | P0 production files (2 stories) | 5.5 days |
| Batch 3 | Ingestion module (4 stories) | 6 days |
| Batch 4 | External data module (5 stories) | 8 days |
| Batch 5 | Remaining files (~30 stories) | ~68 days |
| **TOTAL** | 71 files | **~90 days** |

*With 2-3 parallel streams: ~30-45 calendar days*

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Circular dependencies exposed | Medium | Medium | Extract shared types to core/ modules |
| Test failures during split | Low | High | Run tests after EACH extraction |
| Coverage reduction | Low | Medium | Lock baseline, compare after each story |
| Import breakage in consumers | Medium | Low | Use shim pattern for backward compat |

### Timeline Impact

- **Epic 6 completion:** NOT affected
- **Epic 5 start:** Can proceed in parallel
- **Overall project:** +30-45 calendar days for full completion

---

## Section 4: Detailed Change Proposals

### Epic 7: Technical Debt & Code Quality

**Epic Goal:** Reduce ALL codebase files to <500 LOC for optimal AI comprehension, improved maintainability, and alignment with research-backed best practices.

---

### Batch 1: Enable Other Refactoring (Week 1)

#### Story 7.1: Split test_external_data_clients.py

| Attribute | Value |
|-----------|-------|
| Current | `tests/unit/test_external_data_clients.py` (3,025 LOC) |
| Target | 6 files + conftest.py, each <500 LOC |
| Priority | P0 - Blocks external client production refactoring |
| Effort | 1.5 days |

**Acceptance Criteria:**
- AC1: Original file split into 6 domain-specific test files
- AC2: Shared fixtures extracted to conftest.py
- AC3: All tests pass unchanged
- AC4: No coverage reduction
- AC5: Original file removed

**Target Structure:**
```
tests/unit/external_data/
├── __init__.py
├── conftest.py                 # Shared fixtures (~150 LOC)
├── test_ine_client.py          # (~500 LOC)
├── test_basegov_client.py      # (~500 LOC)
├── test_ice_futures_client.py  # (~350 LOC)
├── test_commodities_client.py  # (~350 LOC)
├── test_bpstat_client.py       # (~350 LOC)
└── test_oil_bulletin_client.py # (~350 LOC)
```

---

#### Story 7.2: Split Root conftest.py

| Attribute | Value |
|-----------|-------|
| Current | `tests/conftest.py` (844 LOC) |
| Target | 4 fixture modules, each <250 LOC |
| Priority | P0 - Improves fixture management |
| Effort | 0.5 days |

**Acceptance Criteria:**
- AC1: Original file split into fixture modules
- AC2: Root conftest.py becomes thin (~50 LOC)
- AC3: All tests pass unchanged
- AC4: pytest fixture discovery works correctly

**Target Structure:**
```
tests/
├── conftest.py                 # Thin, imports from fixtures/ (~50 LOC)
└── fixtures/
    ├── __init__.py             # Re-exports all fixtures
    ├── database.py             # Qdrant, PostgreSQL (~200 LOC)
    ├── mocks.py                # Mock clients (~250 LOC)
    ├── documents.py            # Sample documents (~200 LOC)
    └── config.py               # Test configuration (~150 LOC)
```

---

#### Story 7.3: Split Integration conftest.py

| Attribute | Value |
|-----------|-------|
| Current | `tests/integration/conftest.py` (1,411 LOC) |
| Target | 3 fixture modules, each <500 LOC |
| Priority | P0 - Improves integration test maintainability |
| Effort | 0.5 days |

**Acceptance Criteria:**
- AC1: Original file split into focused fixture modules
- AC2: Integration conftest.py becomes thin (~50 LOC)
- AC3: All integration tests pass
- AC4: No fixture scope changes

**Target Structure:**
```
tests/integration/
├── conftest.py                 # Thin (~50 LOC)
└── fixtures/
    ├── __init__.py
    ├── services.py             # Running service fixtures (~500 LOC)
    ├── scenarios.py            # E2E scenario fixtures (~500 LOC)
    └── database.py             # DB integration fixtures (~400 LOC)
```

---

### Batch 2: Largest Production Files (Week 2-3)

#### Story 7.4: Refactor main.py into MCP Module Structure

| Attribute | Value |
|-----------|-------|
| Current | `raglite/main.py` (2,998 LOC) |
| Target | 7 files, each <400 LOC |
| Priority | P0 - Largest production file |
| Effort | 2.5 days |

**Acceptance Criteria:**
- AC1: main.py reduced to <300 LOC (entry point only)
- AC2: MCP tools extracted to raglite/mcp/tools/
- AC3: All MCP integration tests pass
- AC4: Backward-compatible imports via shim
- AC5: Update test imports

**Target Structure:**
```
raglite/
├── main.py                     # Entry point only (~300 LOC)
└── mcp/
    ├── __init__.py             # Re-exports
    ├── tools/
    │   ├── __init__.py
    │   ├── query.py            # query_financial_documents (~400 LOC)
    │   ├── ingest.py           # ingest_financial_document (~400 LOC)
    │   ├── forecast.py         # forecast tools (~400 LOC)
    │   └── external.py         # external data tools (~400 LOC)
    ├── handlers.py             # Request processing (~400 LOC)
    ├── resources.py            # Resource management (~300 LOC)
    └── prompts.py              # Prompt templates (~200 LOC)
```

---

#### Story 7.5: Refactor hybrid.py into Forecasting Modules

| Attribute | Value |
|-----------|-------|
| Current | `raglite/forecasting/hybrid.py` (2,804 LOC) |
| Target | 5 files, each <500 LOC |
| Priority | P0 - Second largest file |
| Effort | 3 days |

**Acceptance Criteria:**
- AC1: hybrid.py reduced to <400 LOC (orchestration only)
- AC2: Model implementations extracted to models/
- AC3: All forecasting tests pass
- AC4: Split test files accordingly
- AC5: Coverage maintained

**Target Structure:**
```
raglite/forecasting/
├── hybrid.py                   # Orchestration only (~400 LOC)
├── models/
│   ├── __init__.py
│   ├── prophet.py              # Prophet-specific (~500 LOC)
│   ├── xgboost.py              # XGBoost-specific (~400 LOC)
│   └── base.py                 # Common interface (~100 LOC)
├── ensemble.py                 # Model combination (~300 LOC)
└── evaluation.py               # Accuracy metrics (~300 LOC)
```

---

### Batch 3-5: Remaining Files (Week 3-10)

| Batch | Files | Stories | Effort |
|-------|-------|---------|--------|
| Batch 3 | Ingestion module (4 files) | 7.6-7.9 | 6 days |
| Batch 4 | External data module (5 files) | 7.10-7.14 | 8 days |
| Batch 5 | Remaining Tier 2-3 files | 7.15-7.45 | ~68 days |

*Detailed stories for Batches 3-5 to be drafted when Batch 2 is near completion.*

---

## Section 5: Implementation Handoff

### Change Scope Classification

**Scope: MODERATE**

- Requires backlog reorganization (new Epic 7)
- Does NOT require fundamental replan
- Can proceed in parallel with existing work

### Handoff Plan

| Role | Responsibility |
|------|----------------|
| **Scrum Master** | Create Epic 7 in sprint-status.yaml, draft stories as needed |
| **Developer** | Implement stories following refactoring guidelines |
| **Dev (Code Review)** | Verify each story maintains test coverage and no regressions |

### Success Criteria

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Files >500 LOC (prod) | 27 | 0 | `check_file_sizes.py` |
| Files >500 LOC (tests) | 44 | 0 | `check_file_sizes.py` |
| Test coverage | 82% | ≥82% | `pytest --cov` |
| CI pass rate | - | 100% | GitHub Actions |
| New violations | 0 | 0 | CI enforced |

### Recommended Execution Order

1. **Immediate:** Add Epic 7 to sprint-status.yaml with status `backlog`
2. **Batch 1 First:** Stories 7.1-7.3 (test infrastructure) - unblocks everything
3. **Batch 2 Next:** Stories 7.4-7.5 (largest files) - highest impact
4. **Parallel with Epic 5/6:** Batches 3-5 can run alongside other work

### Documentation Updates Required

| Document | Update |
|----------|--------|
| `docs/sprint-artifacts/sprint-status.yaml` | Add Epic 7 and stories |
| `docs/architecture/` | Update Section 3 (Repository Structure) |
| `docs/prd/` | Add NFR33 (file size limit) |
| `.file-size-exceptions` | Remove entries as files are refactored |

---

## Appendix A: Complete File Inventory

### Production Files (27 exceeding 500 LOC)

| Priority | File | LOC | Target Split |
|----------|------|-----|--------------|
| P0 | main.py | 2,998 | 7 files |
| P0 | forecasting/hybrid.py | 2,804 | 5 files |
| P1 | ingestion/document_ingestion.py | 1,343 | 4 files |
| P1 | forecasting/timeseries_extract.py | 1,331 | 3 files |
| P1 | shared/models.py | 1,220 | 4 files |
| P1 | ingestion/adaptive_table/unit_inference.py | 1,205 | 3 files |
| P1 | retrieval/search.py | 1,146 | 3 files |
| P1 | external_data/clients/basegov.py | 1,066 | 3 files |
| P2 | external_data/refresh.py | 969 | 3 files |
| P2 | external_data/storage.py | 959 | 3 files |
| P2 | retrieval/query_classifier.py | 928 | 3 files |
| P2 | ingestion/adaptive_table/core.py | 903 | 3 files |
| P2 | ingestion/adaptive_table/classification.py | 853 | 3 files |
| P2 | external_data/clients/ine.py | 767 | 2 files |
| P2 | external_data/clients/ice_futures.py | 707 | 2 files |
| P2 | agentic/orchestrator.py | 705 | 3 files |
| P3 | ingestion/storage_operations.py | 687 | 2 files |
| P3 | agentic/fallback.py | 686 | 2 files |
| P3 | ingestion/adaptive_table/standard_layouts.py | 635 | 3 files |
| P3 | ingestion/chunking_strategy.py | 626 | 3 files |
| P3 | external_data/clients/commodities.py | 594 | 2 files |
| P3 | agentic/planner.py | 539 | 2 files |
| P3 | external_data/clients/eu_oil_bulletin.py | 536 | 2 files |
| P3 | ingestion/table_extraction.py | 517 | 2 files |
| P3 | insights/proactive.py | 503 | 2 files |
| Monitor | external_data/clients/bpstat.py | 495 | Near limit |
| Monitor | retrieval/multi_index_search.py | 487 | Near limit |

### Test Files (44 exceeding 500 LOC)

| Priority | File | LOC |
|----------|------|-----|
| T0 | unit/test_external_data_clients.py | 3,025 |
| T0 | unit/test_ingestion.py | 1,785 |
| T0 | integration/conftest.py | 1,411 |
| T0 | integration/test_forecast_query_integration.py | 1,224 |
| T0 | integration/test_ingestion_integration.py | 1,197 |
| T0 | unit/test_proactive_insights.py | 1,128 |
| T0 | unit/test_timeseries_extract.py | 1,056 |
| T0 | unit/test_trend_analysis.py | 1,053 |
| T1 | (12 files 700-1000 LOC) | - |
| T2 | (24 files 500-700 LOC) | - |

*Full inventory in docs/analysis/file-size-refactoring-briefing.md*

---

## Appendix B: Standard Acceptance Criteria Template

For each refactoring story:

### AC1: File Size Reduction
- Original file reduced to <500 LOC
- All new modules <500 LOC each
- Related test file(s) also <500 LOC each

### AC2: Functionality Preserved
- All existing tests pass unchanged
- No behavior changes
- Coverage unchanged or improved

### AC3: Clean Architecture
- No circular dependencies
- Clear module responsibilities
- Proper `__init__.py` exports with backward compatibility

### AC4: Test Structure Alignment
- Test files mirror production structure (1:1 mapping)
- Shared fixtures extracted to fixtures/ modules
- No orphaned or duplicated test code

### AC5: Documentation
- Update module docstrings
- Update any architecture docs referencing old structure

---

## Appendix C: Refactoring Best Practices

### Core Principles

1. **Tests and Production Refactor TOGETHER** - Same PR keeps changes atomic
2. **Work Incrementally** - Extract ONE module at a time, run tests after each
3. **Preserve Import Compatibility** - Use shim pattern during transition

### Test-Aware Refactoring Checklist

| Step | Action | Validation |
|------|--------|------------|
| 1 | Lock baseline coverage | `pytest --cov=raglite --cov-report=term` |
| 2 | Copy code to new location | All tests still pass |
| 3 | Update production imports | All tests still pass |
| 4 | Update test imports | All tests still pass |
| 5 | Add shim deprecation warning | Warning visible in logs |
| 6 | Remove old code/shim | All tests still pass |
| 7 | Verify coverage unchanged | Compare to baseline |

### Shim Pattern Example

```python
# old_module.py - Keep as shim temporarily
import warnings
from .new_package.new_module import Foo, bar

warnings.warn(
    "Import from new_package.new_module instead",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["Foo", "bar"]  # Re-export for backward compatibility
```

---

**END OF SPRINT CHANGE PROPOSAL**

---

*Generated by BMAD Correct Course Workflow*
*Scrum Master Agent - 2025-12-10*
