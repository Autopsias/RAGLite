# Test Design: Epic 8 - Technical Debt Reduction

**Date:** 2025-12-25
**Author:** Ricardo (via Murat - Master Test Architect)
**Status:** Draft
**Epic:** Epic 8 - Technical Debt Reduction (SCP-2025-12-25-001)

---

## Executive Summary

**Scope:** Full test design for Epic 8 - Technical Debt Reduction

**Risk Summary:**

- Total risks identified: 16
- High-priority risks (>=6): 5 + 2 CRITICAL
- Critical categories: TECH (9 including 1 CRITICAL), DATA (3 including 1 CRITICAL), OPS (4)

**Coverage Summary:**

- P0 scenarios: 12 (24 hours)
- P1 scenarios: 18 (18 hours)
- P2/P3 scenarios: 8 (4 hours)
- **Total effort**: 55-60 hours (~7-8 days) *includes fix cycle buffer*

**Epic Context:**

This is a **refactoring epic** focused on reducing file sizes to enable AI comprehension and improve maintainability. The primary risk is **regression** - breaking existing functionality while restructuring code.

**Key Numbers:**
- 84 files exceed 500 LOC limit
- 39 production files to refactor
- 45 test files to refactor
- ~25,000 excess LOC to eliminate

---

## Risk Assessment

### High-Priority Risks (Score >=6)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
|---------|----------|-------------|-------------|--------|-------|------------|-------|----------|
| R-002 | TECH | Import breakage across hybrid.py dependencies (2,780 LOC) during forecasting module split | 2 | 3 | 6 | Use shim pattern with deprecation warnings; incremental extraction with tests after each step | Dev | Per story |
| R-003 | DATA | Test coverage regression during forecasting module split - coverage must remain >=80% | 2 | 3 | 6 | Lock baseline coverage before refactoring; validate after each extraction; automated coverage gate in CI | QA | Per story |
| R-007 | TECH | PDF processing regression during document_ingestion.py split (1,343 LOC) | 2 | 3 | 6 | Sample validation (3 representative PDFs, ~15 min); full 33-PDF corpus validation deferred to post-epic | Dev | Story 8.3 |
| R-013 | TECH | Backward compatibility breaks across refactored modules - affects MCP server and all consumers | 2 | 3 | 6 | Shim pattern for all public exports; deprecation warnings; integration test validation | Dev | All stories |
| R-011 | TECH | Fixture dependency issues during conftest.py refactoring (1,411 LOC) - load-bearing fixtures affect 264 test files | 2 | 3 | 6 | Document fixture dependencies; phased extraction; validate fixture resolution order | QA | Story 8.4 |
| R-015 | DATA | **Production database corruption during testing** - 6,625 vectors + 78K rows at risk | 1 | 3 | **CRITICAL** | SafetyGuard enforcement; test ports only (6335/5433); APP_ENV=test required | ALL | All stories |
| R-016 | TECH | **Test isolation corruption via sys.modules manipulation** - ATDD tests that delete modules from sys.modules cause isinstance() failures across 145+ unrelated tests | 3 | 3 | **CRITICAL** | NEVER use `del sys.modules[...]` in tests; use subprocess for isolated import testing; run full test suite before marking story "done" | ALL | All stories |

### Medium-Priority Risks (Score 3-4)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
|---------|----------|-------------|-------------|--------|-------|------------|-------|
| R-001 | TECH | Circular dependencies when splitting timeseries_extract.py (3,178 LOC) | 2 | 2 | 4 | Extract shared types to low-level module first; use local imports as tactical fix | Dev |
| R-004 | TECH | External API integration breakage during basegov/ecb/eurostat refactoring | 2 | 2 | 4 | Health check tests after each client refactoring; cassette-based regression tests | Dev |
| R-006 | OPS | Health check failures during external data client refactoring | 2 | 2 | 4 | Validate all health endpoints after refactoring; add monitoring alerts | Ops |
| R-009 | TECH | Table extraction accuracy degradation during adaptive_table refactoring | 2 | 2 | 4 | Baseline accuracy validation (97.9%); ground truth comparison | QA |
| R-010 | OPS | CI pipeline breakage from test reorganization | 2 | 2 | 4 | Incremental test moves; validate CI green after each batch | Dev |
| R-014 | OPS | Deployment failures from import path changes | 2 | 2 | 4 | Shim pattern; integration tests; staging deployment validation | Ops |

### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
|---------|----------|-------------|-------------|--------|-------|--------|
| R-005 | DATA | Storage layer data corruption risk during storage.py refactoring | 1 | 3 | 3 | Monitor |
| R-008 | DATA | Vector database indexing issues during storage_operations.py refactoring | 1 | 3 | 3 | Monitor |
| R-012 | OPS | Test count validation failure | 1 | 1 | 1 | Monitor |

### Risk Category Legend

- **TECH**: Technical/Architecture (circular deps, import breakage, compatibility)
- **SEC**: Security (N/A for this epic)
- **PERF**: Performance (N/A for this epic - no perf changes expected)
- **DATA**: Data Integrity (coverage regression, accuracy degradation)
- **BUS**: Business Impact (N/A - internal refactoring)
- **OPS**: Operations (CI pipeline, deployment, health checks)

---

## Test Coverage Plan

### P0 (Critical) - Run on every commit

**Criteria**: Blocks core functionality + High risk (>=6) + No workaround

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
|-------------|------------|-----------|------------|-------|-------|
| Coverage baseline lock (>=80%) | Unit/Integration | R-003 | 1 | QA | `pytest --cov=raglite --cov-fail-under=80` |
| Import compatibility validation | Integration | R-002, R-013 | 3 | Dev | Validate all public imports work |
| Forecasting functionality (hybrid.py split) | Integration | R-002 | 4 | QA | Existing forecast tests must pass |
| PDF ingestion validation (3 sample PDFs) | E2E | R-007 | 2 | QA | Re-ingest 3 representative PDFs (~15 min, not full 33-PDF corpus) |
| MCP server startup | E2E | R-013 | 1 | QA | Server starts with refactored modules |
| Circular dependency check | Unit | R-001 | 1 | Dev | `python -c "import raglite"` |
| **Production database protection** | Unit | R-015 | 1 | QA | SafetyGuard rejects production ports in test context |

**Total P0**: 13 tests, 24 hours

### P1 (High) - Run on PR to main

**Criteria**: Important features + Medium risk (3-4) + Common workflows

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
|-------------|------------|-----------|------------|-------|-------|
| External data client health checks | Integration | R-004, R-006 | 6 | QA | All client health endpoints pass |
| Table extraction accuracy (97.9%) | Integration | R-009 | 2 | QA | Ground truth validation |
| Test fixture dependencies | Unit | R-011 | 3 | QA | Fixtures resolve correctly |
| CI pipeline validation | Integration | R-010 | 2 | Dev | All CI jobs pass |
| Storage operations integrity | Integration | R-005, R-008 | 3 | QA | CRUD operations work |
| Shim deprecation warnings | Unit | R-013 | 2 | Dev | Old imports trigger warnings |

**Total P1**: 18 tests, 18 hours

### P2 (Medium) - Run nightly/weekly

**Criteria**: Secondary features + Low risk (1-2) + Edge cases

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
|-------------|------------|-----------|------------|-------|-------|
| Test count validation | Unit | R-012 | 1 | QA | Test count >= baseline |
| Module boundary validation | Unit | - | 2 | Dev | No cross-layer dependencies |
| File size validation | Unit | - | 1 | Dev | All files <500 LOC |
| Documentation links | Unit | - | 1 | Dev | Architecture docs updated |

**Total P2**: 5 tests, 2.5 hours

### P3 (Low) - Run on-demand

**Criteria**: Nice-to-have + Exploratory + Performance benchmarks

| Requirement | Test Level | Test Count | Owner | Notes |
|-------------|------------|------------|-------|-------|
| Performance baseline comparison | E2E | 2 | QA | No regression from refactoring |
| Memory usage validation | E2E | 1 | Dev | No memory leaks from new modules |

**Total P3**: 3 tests, 1.5 hours

---

## Execution Order

### Smoke Tests (<5 min)

**Purpose**: Fast feedback, catch build-breaking issues

- [ ] `python -c "import raglite"` (5s) - No circular dependencies
- [ ] `pytest tests/unit/test_imports.py` (30s) - All imports resolve
- [ ] MCP server startup test (1 min) - Server initializes

**Total**: 3 scenarios

### P0 Tests (<10 min)

**Purpose**: Critical path validation

- [ ] Coverage validation (`pytest --cov=raglite --cov-fail-under=80`)
- [ ] Forecasting regression tests (existing hybrid forecast tests)
- [ ] PDF ingestion validation (sample PDF re-ingest)
- [ ] Import compatibility tests

**Total**: 12 scenarios

### P1 Tests (<30 min)

**Purpose**: Important feature coverage

- [ ] External data client health checks (INE, BaseGov, ECB, Eurostat, ICE, Commodities)
- [ ] Table extraction accuracy validation
- [ ] Test fixture dependency validation
- [ ] Storage operations integrity tests

**Total**: 18 scenarios

### P2/P3 Tests (<60 min)

**Purpose**: Full regression coverage

- [ ] File size compliance validation
- [ ] Test count validation
- [ ] Performance baseline comparison

**Total**: 8 scenarios

---

## Resource Estimates

### Test Development Effort

| Priority | Count | Hours/Test | Total Hours | Notes |
|----------|-------|------------|-------------|-------|
| P0 | 13 | 2.0 | 24 | Complex validation, multiple modules, DB protection |
| P1 | 18 | 1.0 | 18 | Standard coverage |
| P2 | 5 | 0.5 | 2.5 | Simple scenarios |
| P3 | 3 | 0.5 | 1.5 | Exploratory |
| **Total** | **39** | **-** | **46** | **~6 days base** |
| **Buffer** | - | - | **+10-14** | **Fix cycle (~20-30%)** |
| **Realistic** | **39** | **-** | **55-60** | **~7-8 days** |

### Prerequisites

**Test Data:**

- Existing ground truth fixtures (802 LOC)
- PDF sample files (33 documents)
- External data cassettes (API response mocks)

**Tooling:**

- pytest with coverage plugin for coverage tracking
- check_file_sizes.py for LOC validation
- CI pipeline (GitHub Actions) for automation

**Environment:**

- Docker containers (Qdrant, PostgreSQL) for integration tests
- Local development environment for unit tests

---

## Quality Gate Criteria

### Pass/Fail Thresholds

- **P0 pass rate**: 100% (no exceptions)
- **P1 pass rate**: >=95% (waivers required for failures)
- **P2/P3 pass rate**: >=90% (informational)
- **High-risk mitigations**: 100% complete or approved waivers

### Coverage Targets

- **Overall coverage**: >=80% (enforced in CI)
- **Refactored modules**: >=80% (no regression allowed)
- **Critical paths (forecasting, ingestion)**: >=85%

### Non-Negotiable Requirements

- [ ] All P0 tests pass
- [ ] No high-risk (>=6) items unmitigated
- [ ] Coverage >= 80% maintained
- [ ] All files <500 LOC after refactoring
- [ ] No circular dependencies
- [ ] Shim pattern for backward compatibility
- [ ] **CRITICAL: Production database protection** (see below)

### CRITICAL: Production Database Protection

**THIS IS NON-NEGOTIABLE.**

| Database | Production Port | Test Port | Protection |
|----------|-----------------|-----------|------------|
| Qdrant | 6333 | **6335** | SafetyGuard validates |
| PostgreSQL | 5432 | **5433** | SafetyGuard validates |

**Rules:**
1. **ALL ingestion tests MUST use test ports (6335/5433)**
2. **Production databases (6333/5432) are READ-ONLY during Epic 8**
3. **Any test attempting write/delete on production ports MUST fail immediately**
4. **`APP_ENV=test` REQUIRED for all test runs**

**Enforcement:**
```python
# REQUIRED in every ingestion/storage test
from raglite.shared.safety import SafetyGuard

guard = SafetyGuard()
guard.validate_test_environment("my_test")  # Raises ProductionProtectionError if on prod ports
```

**Production Data (DO NOT TOUCH):**
- Qdrant `financial_docs`: 6,625 vectors (33 PDFs)
- PostgreSQL `financial_tables`: 78,759 rows
- PostgreSQL `financial_chunks`: 14 rows

**Rationale:** Production data represents ~12 hours of ingestion work. Accidental deletion or corruption during testing is unrecoverable without backup restore.

---

## Mitigation Plans

### R-002: Import breakage across hybrid.py dependencies (Score: 6)

**Mitigation Strategy:**
1. Use shim pattern: keep old imports working via re-exports
2. Add deprecation warnings to old import paths
3. Incremental extraction: move one module at a time, run tests after each
4. Document new import paths in module docstrings

**Owner:** Dev Team
**Timeline:** Throughout Story 8.1
**Status:** Planned
**Verification:** All existing import statements in tests continue to work

### R-003: Test coverage regression (Score: 6)

**Mitigation Strategy:**
1. Lock baseline coverage before starting: `pytest --cov=raglite --cov-report=html > coverage_baseline.txt`
2. Run coverage after EACH module extraction
3. Add coverage check to CI gate: `--cov-fail-under=80`
4. Track coverage per module in sprint status

**Owner:** QA
**Timeline:** Continuous during all stories
**Status:** Planned
**Verification:** Coverage >= baseline after each refactoring PR

### R-007: PDF processing regression (Score: 6)

**Mitigation Strategy:**
1. **Sample validation (3 PDFs, ~15 min):**
   - 1 small PDF (<10 pages) - smoke test
   - 1 complex PDF with tables - validates table extraction
   - 1 medium PDF - integration sanity
2. Baseline accuracy check using ground truth
3. Rollback plan: git revert if accuracy drops >1%
4. **Post-epic validation:** Full 33-PDF corpus re-ingestion (manual, not in test suite)

**Owner:** Dev Team
**Timeline:** Story 8.3 completion
**Status:** Planned
**Verification:** 3 sample PDFs re-ingestable with same accuracy; full corpus deferred

**Rationale:** Full 33-PDF re-ingestion takes ~12 hours - impractical for test suite. Sample validation provides confidence without blocking CI.

### R-011: Fixture dependency issues (Score: 6) - ADDED

**Mitigation Strategy:**
1. **Document fixture dependency graph** before refactoring
2. Phased extraction: move one fixture group at a time
3. Validate fixture resolution order after each extraction
4. Test with `pytest --collect-only` to verify all 264 test files still discover correctly

**Owner:** QA
**Timeline:** Story 8.4
**Status:** Planned
**Verification:** All tests discover and run; no fixture resolution errors

**Rationale:** conftest.py (1,411 LOC) contains load-bearing fixtures. Breaking fixture resolution cascades failures across 264 test files.

### R-013: Backward compatibility breaks (Score: 6)

**Mitigation Strategy:**
1. Shim pattern for ALL public exports in refactored modules
2. Deprecation warnings with clear migration path
3. Integration test suite validates all MCP tools work
4. Document migration guide for consumers

**Owner:** Dev Team
**Timeline:** All stories
**Status:** Planned
**Verification:** MCP server starts and all tools callable

---

## Story-Specific Test Focus

### Story 8.1: Critical Forecasting Module Refactoring

**Files to refactor:**
- `raglite/forecasting/timeseries_extract.py` (3,178 LOC -> 6-7 modules)
- `raglite/forecasting/hybrid.py` (2,780 LOC -> 5-6 modules)
- `tests/unit/test_timeseries_extract.py` (1,413 LOC)

**Test Focus:**
- Forecast accuracy validation (no regression)
- Import compatibility for forecasting module
- Coverage >= 80% for forecasting package

**Acceptance Criteria Validation:**
- [ ] AC1: All production files under 500 LOC
- [ ] AC2: All test files under 500 LOC
- [ ] AC3: 100% test coverage maintained
- [ ] AC4: All imports updated across codebase
- [ ] AC5: No circular dependencies
- [ ] AC6: Performance benchmarks unchanged
- [ ] AC7: Test file structure mirrors production module structure

### Story 8.2: External Data Client Refactoring

**Files to refactor:**
- `raglite/external_data/clients/basegov.py` (1,066 LOC)
- `raglite/external_data/clients/ecb.py` (1,033 LOC)
- `raglite/external_data/clients/eurostat.py` (957 LOC)
- `raglite/external_data/storage.py` (1,633 LOC)

**Test Focus:**
- All 6 external data client health checks pass
- Storage operations CRUD tests
- Cassette-based API mocking for regression

**Acceptance Criteria Validation:**
- [ ] AC1: All production files under 500 LOC
- [ ] AC2: All test files under 500 LOC
- [ ] AC3: Shared base class for common patterns
- [ ] AC4: Storage operations isolated and testable
- [ ] AC5: All health checks pass
- [ ] AC6: Test file structure mirrors production module structure

### Story 8.3: Ingestion Module Refactoring

**Files to refactor:**
- `raglite/ingestion/document_ingestion.py` (1,343 LOC)
- `raglite/ingestion/adaptive_table/unit_inference.py` (1,205 LOC)
- `raglite/ingestion/adaptive_table/core.py` (903 LOC)

**Test Focus:**
- PDF ingestion validation (3 sample PDFs, ~15 min)
- Table extraction accuracy (97.9% baseline)
- Chunking strategy validation

**Acceptance Criteria Validation:**
- [ ] AC1: All production files under 500 LOC
- [ ] AC2: All test files under 500 LOC
- [ ] AC3: Ingestion pipeline performance unchanged
- [ ] AC4: Sample PDFs (3) re-ingestable successfully; full 33-PDF corpus validation deferred to post-epic
- [ ] AC5: Test file structure mirrors production module structure

### Story 8.4: Test File Consolidation

**Files to refactor:**
- `tests/unit/test_ingestion.py` (1,817 LOC)
- `tests/integration/conftest.py` (1,411 LOC)
- Large test files (45 files >500 LOC)

**Test Focus:**
- Test count validation (>= baseline)
- Fixture dependency resolution
- CI pipeline passes

**Acceptance Criteria Validation:**
- [ ] AC1: All test files under 500 LOC
- [ ] AC2: Test count unchanged or increased
- [ ] AC3: Coverage maintained at 80%+
- [ ] AC4: CI pipeline runs successfully

---

## Assumptions and Dependencies

### Assumptions

1. Shim pattern will be accepted for backward compatibility
2. Test files can follow production structure (1:1 mapping)
3. CI pipeline can handle incremental refactoring PRs
4. No concurrent feature work on refactored modules during refactoring

### Dependencies

1. `.file-size-exceptions` baseline exists - Required now (EXISTS)
2. check_file_sizes.py script available - Required now (EXISTS)
3. Ground truth fixtures stable - Required for validation

### Risks to Plan

- **Risk**: Concurrent feature work on modules being refactored
  - **Impact**: Merge conflicts, test instability
  - **Contingency**: Coordinate with team, lock modules during refactoring

- **Risk**: Shim pattern adds maintenance burden
  - **Impact**: Extra code to maintain during transition
  - **Contingency**: Schedule shim removal in follow-up story

---

## Follow-on Workflows (Manual)

- Run `*atdd` to generate failing P0 tests before implementation (TDD approach)
- Run `*automate` for broader coverage once implementation exists
- Run `*trace` after completion for traceability matrix update

---

## Approval

**Test Design Approved By:**

- [ ] Product Manager: _________________ Date: _________
- [ ] Tech Lead: _________________ Date: _________
- [ ] QA Lead: _________________ Date: _________

**Comments:**

---

## Appendix

### Knowledge Base References

- `risk-governance.md` - Risk classification framework (6 categories)
- `test-levels-framework.md` - Test level selection (Unit/Integration/E2E)
- `test-priorities-matrix.md` - P0-P3 prioritization criteria

### Related Documents

- PRD: `docs/prd/epic-list.md`
- Sprint Change Proposal: `docs/implementation-artifacts/sprint-change-proposal-2025-12-25.md`
- File Size Briefing: `docs/analysis/file-size-refactoring-briefing.md`
- Coding Standards: `.claude/rules/file-size-limits.md`

### Current Test Infrastructure

| Suite | Location | Count | Purpose |
|-------|----------|-------|---------|
| Unit | `tests/unit/` | ~150+ | Isolated function testing |
| Integration | `tests/integration/` | ~80+ | Component interaction |
| Validation | `tests/validation/` | ~20+ | Accuracy validation |
| E2E | `tests/e2e/` | ~10+ | Full workflow testing |
| Health | `tests/health/` | ~10+ | External service health |

**Total test files:** 264
**Total test LOC:** 98,469

---

**Generated by**: BMad TEA Agent - Test Architect Module
**Workflow**: `_bmad/bmm/testarch/test-design`
**Version**: 4.0 (BMad v6)
