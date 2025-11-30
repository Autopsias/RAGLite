# Coverage Analysis & Cleanup Recommendations
**Date:** 2025-11-24
**Overall Coverage:** 57.62% (3576/6206 lines covered)
**Analysis Mode:** Identify 0% coverage files and recommend cleanup actions

---

## Executive Summary

The project currently has **57.62% overall coverage**, which is below the production-ready target of 75%. Analysis identified:

- **4 root Python diagnostic files** that can be safely archived or removed
- **23 scripts with 0% coverage** - many are one-time utilities or obsolete
- **4 core raglite modules with <60% coverage** requiring test improvements

**Key Recommendation:** Remove obsolete files and focus testing effort on the 4 low-coverage core modules in `raglite/` package.

---

## 🧹 Files Recommended for REMOVAL

### Root Python Diagnostic Files (4 files)

#### 1. `test_page_api.py` ✅ **SAFE TO REMOVE**
- **Last Modified:** Oct 4, 2025 (51 days ago)
- **Purpose:** One-time diagnostic for Docling page API exploration
- **Coverage:** Not measured (not in coverage report)
- **Usage:** No imports found in codebase
- **Recommendation:** **DELETE** - Obsolete diagnostic script, no longer needed
- **Impact:** None - not referenced anywhere

#### 2. `test_model_load_diagnostic.py` ✅ **SAFE TO REMOVE**
- **Last Modified:** Nov 5, 2025 (19 days ago)
- **Purpose:** Diagnostic for embedding model reload behavior in Test Explorer
- **Coverage:** Not measured
- **Usage:** No imports found in codebase
- **Recommendation:** **DELETE** - Diagnostic completed, no ongoing use
- **Impact:** None - not referenced anywhere

#### 3. `verify_venv.py` ⚠️ **ARCHIVE RECOMMENDED**
- **Last Modified:** Nov 5, 2025 (19 days ago)
- **Purpose:** Verify virtual environment setup and dependencies
- **Coverage:** 0% (not executed in tests)
- **Usage:** Only imported by `tests/unit/test_verify_venv.py`
- **Recommendation:** **MOVE to scripts/** - CLI utility, not production code
- **Action:**
  ```bash
  git mv verify_venv.py scripts/verify-venv.py
  # Update test imports: tests/unit/test_verify_venv.py
  ```
- **Impact:** Low - only affects development environment setup

#### 4. `strands_poc.py` ⚠️ **DEFER DECISION (Epic 3)**
- **Last Modified:** Nov 18, 2025 (6 days ago - recent)
- **Purpose:** AWS Strands POC for Epic 3 multi-agent orchestration
- **Coverage:** 0% (conditional dependency - skipped if strands not installed)
- **Usage:** Imported by `tests/unit/test_strands_poc.py` and referenced in `docs/archive/`
- **Recommendation:** **KEEP** - Active POC code for Epic 3 implementation
- **Note:** Tests are conditionally skipped when `strands` package not installed
- **Action:** No action needed - coverage will improve when Epic 3 begins

---

## 📊 Scripts with 0% Coverage (23 scripts)

### Category A: One-Time Setup/Migration Scripts ✅ **SAFE TO ARCHIVE**

These scripts were used for initial setup or data migration and are no longer needed:

1. `scripts/init-postgresql.py` - Initial PostgreSQL setup (superseded by docker-compose)
2. `scripts/init-test-postgresql.py` - Test DB setup (superseded by conftest.py fixtures)
3. `scripts/reingest-full-pdf-adaptive.py` - Old adaptive chunking migration
4. `scripts/reingest-full-report.py` - Old full report re-ingestion
5. `scripts/reingest-with-table-aware-chunking.py` - Story 2.8 migration (one-time)

**Recommendation:** Move to `scripts/archive/migrations/`

### Category B: Data Export/Import Utilities ⚠️ **ARCHIVE BUT DOCUMENT**

Utilities for backup/restore operations - low frequency use:

1. `scripts/export-postgres-data.py` - PostgreSQL data export
2. `scripts/import-postgres-data.py` - PostgreSQL data import
3. `scripts/export-qdrant-snapshot.py` - Qdrant snapshot export
4. `scripts/import-qdrant-snapshot.py` - Qdrant snapshot import

**Recommendation:** Move to `scripts/archive/backup-restore/` with README documenting usage

### Category C: Validation Scripts ✅ **CONSOLIDATE OR REMOVE**

Multiple overlapping validation scripts that should be consolidated:

1. `scripts/validate-ground-truth-against-pdf.py` - Ground truth validation
2. `scripts/validate-ground-truth-batch.py` - Batch validation
3. `scripts/validate_ground_truth.py` - Another validation script (duplicate?)
4. `scripts/ground_truth_v2_master.py` - V2 master script (obsolete?)

**Recommendation:**
- Keep ONE validation script: `scripts/run-accuracy-tests.py` (92% coverage ✅)
- Archive the rest to `scripts/archive/validation/`

### Category D: Obsolete Ingestion Scripts ✅ **REMOVE**

Superseded by newer pipeline:

1. `scripts/ingest-pdf.py` - Old single-PDF ingestion
2. `scripts/ingest-whole-pdf.py` - Old whole-PDF ingestion

**Recommendation:** **DELETE** - Superseded by Story 4.1 async ingestion MCP tools

### Category E: Monitoring/Diagnostic Scripts ⚠️ **KEEP BUT ADD TESTS**

Scripts that are still useful but lack test coverage:

1. `scripts/check-postgres-documents.py` - Check PostgreSQL document count
2. `scripts/verify-postgres-data-quality.py` - Data quality checks
3. `scripts/clean-test-databases.py` - Test DB cleanup utility
4. `scripts/rebuild_bm25_index.py` - BM25 index rebuild

**Recommendation:** KEEP but add integration tests (Story 4.3 candidates)

### Category F: CI/Coverage Scripts ⚠️ **NEEDS TESTING**

Important scripts that lack coverage:

1. `scripts/check_coverage_diff.py` - Coverage diff checking
2. `scripts/check_coverage_ratchet.py` - Coverage ratchet enforcement
3. `scripts/universal_test_runner.py` - Test runner wrapper

**Recommendation:** Add unit tests - these are critical CI infrastructure

### Category G: Phase Validation ⚠️ **ARCHIVE AFTER EPIC 2**

1. `scripts/run-phase2a-final-validation.py` - Phase 2A validation (Epic 2 specific)

**Recommendation:** Move to `scripts/archive/epic-2/` after Epic 2 completion

---

## 🎯 Priority Areas for Coverage Improvement

### High Priority: Core raglite Package Files

Focus testing effort on these 4 files with <60% coverage:

#### 1. `raglite/ingestion/table_extraction.py` - **21.5% coverage** ⚠️ CRITICAL
- **Missing:** 113/144 lines uncovered
- **Impact:** HIGH - Core table extraction logic (Story 2.8)
- **Recommendation:**
  - Add unit tests for table extraction functions
  - Test edge cases: empty tables, malformed tables, large tables
  - Target: 80%+ coverage
- **Estimated Effort:** 3-4 hours (15-20 new tests)

#### 2. `raglite/ingestion/adaptive_table/unit_inference.py` - **46.0% coverage**
- **Missing:** 182/337 lines uncovered
- **Impact:** MEDIUM - Adaptive table chunking (Story 2.9)
- **Recommendation:**
  - Add unit tests for unit detection logic
  - Test currency detection, unit conversions
  - Target: 70%+ coverage
- **Estimated Effort:** 4-5 hours (20-25 new tests)

#### 3. `raglite/agentic/agents/synthesis_agent.py` - **52.9% coverage**
- **Missing:** 73/155 lines uncovered
- **Impact:** MEDIUM - Answer synthesis (Story 4.2)
- **Recommendation:**
  - Add tests for citation generation
  - Test synthesis with various chunk counts
  - Target: 75%+ coverage
- **Estimated Effort:** 2-3 hours (10-15 new tests)

#### 4. `raglite/ingestion/adaptive_table/standard_layouts.py` - **54.0% coverage**
- **Missing:** 86/187 lines uncovered
- **Impact:** LOW - Standard table layouts (Story 2.9)
- **Recommendation:**
  - Test layout detection patterns
  - Test P&L, balance sheet, income statement layouts
  - Target: 70%+ coverage
- **Estimated Effort:** 3-4 hours (15-20 new tests)

### Medium Priority: Scripts Directory

Scripts with good coverage (>90%) but need maintenance:

1. ✅ `scripts/accuracy_utils.py` - **100% coverage**
2. ✅ `scripts/init-qdrant.py` - **100% coverage**
3. ✅ `scripts/daily-accuracy-check.py` - **93.8% coverage**
4. ✅ `scripts/run-accuracy-tests.py` - **92.0% coverage**

**Action:** Maintain test coverage as scripts evolve

1. ⚠️ `scripts/generate_failure_report.py` - **23.1% coverage**
   - Add tests for report generation logic
   - Target: 75%+ coverage

---

## 📋 Action Plan

### Immediate Actions (2-3 hours)

1. **Delete obsolete diagnostic files:**
   ```bash
   rm test_page_api.py test_model_load_diagnostic.py
   ```

2. **Move verify_venv.py to scripts:**
   ```bash
   git mv verify_venv.py scripts/verify-venv.py
   # Update test: tests/unit/test_verify_venv.py line 245
   ```

3. **Archive obsolete scripts:**
   ```bash
   mkdir -p scripts/archive/{migrations,backup-restore,validation,epic-2}

   # Migrations
   git mv scripts/reingest-*.py scripts/archive/migrations/
   git mv scripts/init-postgresql.py scripts/init-test-postgresql.py scripts/archive/migrations/

   # Backup/Restore
   git mv scripts/{export,import}-*.py scripts/archive/backup-restore/

   # Validation (keep run-accuracy-tests.py)
   git mv scripts/validate-ground-truth-*.py scripts/archive/validation/
   git mv scripts/ground_truth_v2_master.py scripts/archive/validation/

   # Epic 2
   git mv scripts/run-phase2a-final-validation.py scripts/archive/epic-2/
   ```

4. **Delete obsolete ingestion scripts:**
   ```bash
   git rm scripts/ingest-pdf.py scripts/ingest-whole-pdf.py
   ```

### Short-Term Actions (1-2 weeks)

5. **Add tests for critical low-coverage files:**
   - Priority 1: `table_extraction.py` (21.5% → 80%)
   - Priority 2: `synthesis_agent.py` (52.9% → 75%)
   - Priority 3: `unit_inference.py` (46.0% → 70%)
   - Priority 4: `standard_layouts.py` (54.0% → 70%)

6. **Add integration tests for monitoring scripts:**
   - `check-postgres-documents.py`
   - `verify-postgres-data-quality.py`
   - `rebuild_bm25_index.py`

### Long-Term Actions (Epic 4)

7. **Add unit tests for CI/coverage scripts:**
   - `check_coverage_diff.py`
   - `check_coverage_ratchet.py`
   - `universal_test_runner.py`

8. **Improve generate_failure_report.py coverage (23.1% → 75%)**

---

## 📈 Expected Coverage Improvement

**Current:** 57.62% overall coverage

**After Cleanup (removal of obsolete files):**
- Estimated: 58-59% (slight improvement as 0% files removed from denominator)

**After Test Addition (4 priority files to 70-80%):**
- `table_extraction.py`: +59 lines covered
- `unit_inference.py`: +92 lines covered
- `synthesis_agent.py`: +40 lines covered
- `standard_layouts.py`: +36 lines covered
- **Total:** +227 lines covered
- **New Coverage:** ~61-62%

**After Full Implementation (all recommendations):**
- Target: **70-75% overall coverage** (production-ready)
- Timeline: 2-3 weeks (Epic 4 Story 4.3 candidates)

---

## 🔍 Coverage Analysis Methodology

This analysis used:
- `coverage.json` from latest test run (2025-11-24)
- File modification dates from `ls -lh`
- Import analysis via `grep` searches
- Coverage tier categorization:
  - 0% = No coverage (candidates for removal)
  - <50% = Critical improvement needed
  - 50-75% = Moderate improvement needed
  - 75-90% = Good coverage
  - 90-100% = Excellent coverage

**Coverage Calculation:**
```
Overall Coverage = Covered Lines / Total Statements
57.62% = 3576 / 6206
```

---

## ✅ Next Steps

1. Review this analysis with the team
2. Get approval for file deletions and archival
3. Execute immediate actions (cleanup)
4. Create GitHub issues for test addition work
5. Track progress toward 75% coverage target

---

**Generated by:** `/coverage analyze` workflow
**Report Location:** `workspace/reports/coverage/coverage-analysis-2025-11-24.md`
