# Sprint Change Proposal: Comprehensive File Size Refactoring

**ID:** SCP-2025-12-25-001
**Date:** 2025-12-25
**Author:** Bob (Scrum Master Agent)
**Status:** APPROVED (2025-12-25)
**Approval Note:** Include test adaptation as part of each refactoring story

---

## Section 1: Issue Summary

### Problem Statement

The RAGLite codebase has accumulated significant technical debt in file sizes, with **84 files exceeding the 500 LOC hard limit**. This impacts:

1. **AI Comprehension:** Large files exceed LLM context windows, causing incomplete understanding and inconsistent edits
2. **Maintainability:** Files over 1000 LOC are difficult to navigate and understand
3. **Code Quality:** Violates project coding standards documented in `.claude/rules/file-size-limits.md`

### Discovery Context

- **Triggered by:** `/code_quality` analysis on 2025-12-25
- **Current state:** 84 grandfathered exceptions in `.file-size-exceptions`
- **No new violations** - enforcement is working, but legacy debt remains

### Evidence Summary

| Category | Files | LOC Range | Total Excess LOC |
|----------|-------|-----------|------------------|
| **Production - Critical** | 7 | 1,000-3,178 | ~8,500 |
| **Production - Severe** | 6 | 750-1,000 | ~1,500 |
| **Production - Moderate** | 26 | 500-750 | ~4,000 |
| **Tests - Critical** | 6 | 1,000-1,817 | ~4,500 |
| **Tests - Severe** | 8 | 750-1,000 | ~2,000 |
| **Tests - Moderate** | 31 | 500-750 | ~4,500 |
| **TOTAL** | **84** | - | **~25,000** |

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| Epic 1-4 | DONE | No impact (completed) |
| Epic 5 | BACKLOG | Can incorporate refactoring stories |
| Epic 6-7 | DONE | Main source of debt (forecasting, external data) |

### Artifact Conflicts

| Artifact | Conflict? | Resolution |
|----------|-----------|------------|
| PRD | No | Maintainability is existing NFR |
| Architecture | No | File limits already documented |
| `.file-size-exceptions` | Yes | Must update as files are fixed |
| Test coverage | Caution | Must maintain 80%+ coverage |

### Technical Impact

**Modules with highest debt:**

1. **`raglite/forecasting/`** - 12 files, ~10,000 excess LOC
2. **`raglite/external_data/`** - 9 files, ~4,500 excess LOC
3. **`raglite/ingestion/`** - 6 files, ~3,500 excess LOC
4. **`raglite/retrieval/`** - 2 files, ~1,500 excess LOC
5. **`tests/`** - 45 files, ~11,000 excess LOC

---

## Section 3: Recommended Approach

### Selected Path: **Phased Direct Adjustment**

Break the refactoring into 4 phases, prioritized by impact and risk:

### Phase 1: Critical Production Files (Week 1-2)
**Goal:** Reduce worst 7 production files below 750 LOC

| File | Current | Target | Strategy |
|------|---------|--------|----------|
| `forecasting/timeseries_extract.py` | 3,178 | 500 | Split into 6-7 modules |
| `forecasting/hybrid.py` | 2,780 | 500 | Split into 5-6 modules |
| `external_data/storage.py` | 1,633 | 500 | Extract client-specific storage |
| `shared/models.py` | 1,432 | 500 | Split by domain (forecast, ingestion, external) |
| `ingestion/document_ingestion.py` | 1,343 | 500 | Extract PDF/Excel processors |
| `ingestion/adaptive_table/unit_inference.py` | 1,205 | 500 | Extract inference strategies |
| `retrieval/search.py` | 1,146 | 500 | Split search types |

**Effort:** ~32 hours
**Risk:** Medium (core functionality, needs careful testing)

### Phase 2: Severe Production Files (Week 2-3)
**Goal:** Reduce 6 files in 750-1000 LOC range

| File | Current | Target |
|------|---------|--------|
| `external_data/clients/basegov.py` | 1,066 | 500 |
| `external_data/clients/ecb.py` | 1,033 | 500 |
| `external_data/refresh.py` | 969 | 500 |
| `external_data/clients/eurostat.py` | 957 | 500 |
| `retrieval/query_classifier.py` | 928 | 500 |
| `ingestion/adaptive_table/core.py` | 903 | 500 |

**Effort:** ~18 hours
**Risk:** Low-Medium

### Phase 3: Moderate Production Files (Week 3-4)
**Goal:** Reduce 26 files in 500-750 LOC range

**Strategy:** Batch by module
- `forecasting/` - 8 files (~12 hours)
- `external_data/` - 6 files (~8 hours)
- `ingestion/` - 5 files (~6 hours)
- `agentic/` - 3 files (~4 hours)
- Other - 4 files (~4 hours)

**Effort:** ~34 hours
**Risk:** Low

### Phase 4: Test Files (Week 4-5)
**Goal:** Reduce 45 test files below limits

**Strategy:**
- Split by test category (unit tests per feature)
- Extract shared fixtures to `conftest.py` files
- Group related tests into focused modules

**Effort:** ~30 hours
**Risk:** Low (tests are isolated)

---

## Section 4: Detailed Change Proposals

### Story 8.1: Critical Forecasting Module Refactoring

```
Story: [8.1] Critical Forecasting Module Refactoring
Epic: Epic 8 - Technical Debt Reduction

OLD (current state):
- timeseries_extract.py: 3,178 LOC (single monolithic file)
- hybrid.py: 2,780 LOC (single monolithic file)
- test_timeseries_extract.py: 1,413 LOC (monolithic test file)
- test_hybrid_forecasting.py: 489 LOC

NEW (proposed):
- forecasting/
  ├── timeseries/
  │   ├── __init__.py
  │   ├── extraction.py (~400 LOC) - Core extraction logic
  │   ├── parsing.py (~400 LOC) - Date/period parsing
  │   ├── validation.py (~300 LOC) - Data validation
  │   ├── transformers.py (~400 LOC) - Data transformations
  │   ├── aggregation.py (~300 LOC) - Aggregation methods
  │   └── metadata.py (~300 LOC) - Metadata handling
  ├── hybrid/
  │   ├── __init__.py
  │   ├── core.py (~400 LOC) - Main forecast logic
  │   ├── models.py (~400 LOC) - Model wrappers
  │   ├── selection.py (~350 LOC) - Model selection
  │   ├── ensemble.py (~350 LOC) - Ensemble methods
  │   └── validation.py (~300 LOC) - Validation utilities

- tests/unit/forecasting/
  ├── timeseries/
  │   ├── test_extraction.py - Tests for extraction.py
  │   ├── test_parsing.py - Tests for parsing.py
  │   ├── test_validation.py - Tests for validation.py
  │   └── ... (mirroring production structure)
  ├── hybrid/
  │   ├── test_core.py
  │   ├── test_models.py
  │   └── ...

Rationale: Enable AI comprehension, improve maintainability,
           enable parallel development on forecasting features

Acceptance Criteria:
- [ ] AC1: All production files under 500 LOC
- [ ] AC2: All test files under 500 LOC (mirroring production structure)
- [ ] AC3: 100% test coverage maintained
- [ ] AC4: All imports updated across codebase
- [ ] AC5: No circular dependencies
- [ ] AC6: Performance benchmarks unchanged
- [ ] AC7: Test file structure mirrors production module structure
```

### Story 8.2: External Data Client Refactoring

```
Story: [8.2] External Data Client Refactoring
Epic: Epic 8 - Technical Debt Reduction

Current State (Production):
- basegov.py: 1,066 LOC
- ecb.py: 1,033 LOC
- eurostat.py: 957 LOC
- storage.py: 1,633 LOC

Current State (Tests):
- test_external_data_clients.py: 3,025 LOC (largest test file!)
- test_external_data_integration.py: 612 LOC

Proposed Structure:
- external_data/
  ├── clients/
  │   ├── basegov/
  │   │   ├── __init__.py
  │   │   ├── client.py (~350 LOC)
  │   │   ├── parsers.py (~350 LOC)
  │   │   └── models.py (~200 LOC)
  │   ├── ecb/
  │   │   └── [similar structure]
  │   └── eurostat/
  │       └── [similar structure]
  ├── storage/
  │   ├── __init__.py
  │   ├── core.py (~400 LOC)
  │   ├── cache.py (~300 LOC)
  │   ├── queries.py (~400 LOC)
  │   └── migrations.py (~200 LOC)

- tests/unit/external_data/
  ├── clients/
  │   ├── test_basegov.py (~400 LOC)
  │   ├── test_ecb.py (~400 LOC)
  │   ├── test_eurostat.py (~400 LOC)
  │   └── ...
  ├── test_storage.py (~400 LOC)
  └── conftest.py (shared fixtures)

Acceptance Criteria:
- [ ] AC1: All production files under 500 LOC
- [ ] AC2: All test files under 500 LOC
- [ ] AC3: Shared base class for common patterns
- [ ] AC4: Storage operations isolated and testable
- [ ] AC5: All health checks pass
- [ ] AC6: Test file structure mirrors production module structure
```

### Story 8.3: Ingestion Module Refactoring

```
Story: [8.3] Ingestion Module Refactoring
Epic: Epic 8 - Technical Debt Reduction

Files to refactor (Production):
- document_ingestion.py: 1,343 LOC → 3-4 modules
- unit_inference.py: 1,205 LOC → 3 modules
- core.py: 903 LOC → 2 modules
- classification.py: 853 LOC → 2 modules
- chunking_strategy.py: 826 LOC → 2 modules

Files to refactor (Tests):
- test_ingestion.py: 1,817 LOC → split by ingestion type
- test_table_extraction.py: 921 LOC → split by extraction phase
- test_parallel_ingestion.py: 858 LOC → split by scenario
- test_unit_inference.py: 550 LOC → split by inference type

Acceptance Criteria:
- [ ] AC1: All production files under 500 LOC
- [ ] AC2: All test files under 500 LOC
- [ ] AC3: Ingestion pipeline performance unchanged
- [ ] AC4: All 33 PDFs re-ingestable successfully
- [ ] AC5: Test file structure mirrors production module structure
```

### Story 8.4: Test File Consolidation

```
Story: [8.4] Test File Consolidation and Refactoring
Epic: Epic 8 - Technical Debt Reduction

Strategy:
- Extract common fixtures to module-level conftest.py
- Split tests by feature/behavior rather than file-per-class
- Create test utilities module for shared helpers

Top priorities:
- test_ingestion.py: 1,817 LOC → split by ingestion type
- test_timeseries_extract.py: 1,413 LOC → split by extraction phase
- test_forecast_query_integration.py: 1,231 LOC → split by query type

Acceptance Criteria:
- [ ] AC1: All test files under 800 LOC (softer limit for tests)
- [ ] AC2: Test count unchanged or increased
- [ ] AC3: Coverage maintained at 80%+
- [ ] AC4: CI pipeline runs successfully
```

---

## Section 5: Implementation Handoff

### Scope Classification: **MODERATE**

This requires backlog reorganization and coordination but not fundamental replanning.

### Recommended Approach

**Option A: New Epic (Recommended)**
- Create **Epic 8: Technical Debt Reduction**
- 4 stories (8.1, 8.2, 8.3, 8.4) as defined above
- Can run in parallel with Epic 5 preparation

**Option B: Integrate into Epic 5**
- Add as prep stories (5-0-7 through 5-0-10)
- Complete before production deployment
- Ties debt reduction to production readiness

### Handoff Recipients

| Role | Responsibility |
|------|----------------|
| **Scrum Master** | Create stories, update sprint-status.yaml |
| **Dev Team** | Execute refactoring per story ACs |
| **QA** | Validate test coverage maintained |

### Success Criteria

1. **Zero files over 500 LOC** in production code
2. **Zero files over 500 LOC** in test code (updated from 800)
3. **Test structure mirrors production** - each production module has corresponding test module
4. **80%+ test coverage** maintained
5. **All CI checks passing**
6. **`.file-size-exceptions` reduced to 0 entries**
7. **No orphaned tests** - all tests updated to import from new module locations

### Timeline Estimate

| Phase | Duration | Parallel? |
|-------|----------|-----------|
| Phase 1 (Critical) | 1-2 weeks | No - sequential |
| Phase 2 (Severe) | 1 week | Partial |
| Phase 3 (Moderate) | 1-2 weeks | Yes - by module |
| Phase 4 (Tests) | 1-2 weeks | Yes - independent |
| **Total** | **4-7 weeks** | - |

---

## Section 6: Approval

### Decision Required

- [ ] **APPROVE** - Proceed with Epic 8 creation
- [ ] **APPROVE with modifications** - Specify changes
- [ ] **DEFER** - Schedule for later
- [ ] **REJECT** - Technical debt is acceptable

### Approval Signature

**User:** _________________________ **Date:** 2025-12-25

---

## Appendix: Complete File Inventory

### Production Files (39 total)

#### Critical (>1000 LOC) - 7 files
1. `raglite/forecasting/timeseries_extract.py` - 3,178 LOC
2. `raglite/forecasting/hybrid.py` - 2,780 LOC
3. `raglite/external_data/storage.py` - 1,633 LOC
4. `raglite/shared/models.py` - 1,432 LOC
5. `raglite/ingestion/document_ingestion.py` - 1,343 LOC
6. `raglite/ingestion/adaptive_table/unit_inference.py` - 1,205 LOC
7. `raglite/retrieval/search.py` - 1,146 LOC

#### Severe (750-1000 LOC) - 6 files
8. `raglite/external_data/clients/basegov.py` - 1,066 LOC
9. `raglite/external_data/clients/ecb.py` - 1,033 LOC
10. `raglite/external_data/refresh.py` - 969 LOC
11. `raglite/external_data/clients/eurostat.py` - 957 LOC
12. `raglite/retrieval/query_classifier.py` - 928 LOC
13. `raglite/ingestion/adaptive_table/core.py` - 903 LOC

#### Moderate (500-750 LOC) - 26 files
14. `raglite/ingestion/adaptive_table/classification.py` - 853 LOC
15. `raglite/ingestion/chunking_strategy.py` - 826 LOC
16. `raglite/forecasting/report_generator.py` - 807 LOC
17. `raglite/external_data/clients/ine.py` - 768 LOC
18. `raglite/ingestion/storage_operations.py` - 711 LOC
19. `raglite/external_data/clients/ice_futures.py` - 707 LOC
20. `raglite/agentic/orchestrator.py` - 705 LOC
21. `raglite/agentic/fallback.py` - 686 LOC
22. `raglite/external_data/models.py` - 666 LOC
23. `raglite/ingestion/adaptive_table/standard_layouts.py` - 635 LOC
24. `raglite/external_data/clients/commodities.py` - 607 LOC
25. `raglite/forecasting/model_selection_job.py` - 601 LOC
26. `raglite/forecasting/regime_detection.py` - 600 LOC
27. `raglite/forecasting/ensemble.py` - 583 LOC
28. `raglite/forecasting/regressor_fetch.py` - 579 LOC
29. `raglite/forecasting/data_quality/config.py` - 578 LOC
30. `raglite/forecasting/data_analyzer.py` - 568 LOC
31. `raglite/forecasting/regressor_config.py` - 550 LOC
32. `raglite/agentic/planner.py` - 543 LOC
33. `raglite/external_data/clients/eu_oil_bulletin.py` - 536 LOC
34. `raglite/forecasting/model_selection_utils.py` - 535 LOC
35. `raglite/forecasting/model_selection.py` - 533 LOC
36. `raglite/ingestion/table_extraction.py` - 517 LOC
37. `raglite/forecasting/tft_training.py` - 512 LOC
38. `raglite/shared/clients.py` - 509 LOC
39. `raglite/insights/proactive.py` - 503 LOC

### Test Files (45 total) - See full output from check_file_sizes.py
