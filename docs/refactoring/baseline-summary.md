# Pre-Refactoring Baseline Summary

**Date:** 2025-11-05
**Story:** 3.0.1 - Refactor Modules to Size Limits
**Purpose:** Establish baseline before splitting 2 oversized modules (5,411 lines)

---

## Test Baseline

**Command:** `uv run pytest tests/ -v --tb=short`
**Duration:** 676.52s (11 minutes 16 seconds)
**Date:** 2025-11-05

### Results

- ✅ **349 passed**
- ⏭️ **32 skipped**
- ❌ **1 failed**
- 🔕 **12 deselected**
- ⚠️ **1 warning**

### Failed Test (PRE-EXISTING)

**Test:** `tests/integration/test_metadata_injection.py::TestMetadataInjectionMocked::test_metadata_filtering_mocked`

**Error:**
```
qdrant_client.http.exceptions.UnexpectedResponse: Unexpected Response: 400 (Bad Request)
Raw response content:
b'{"status":{"error":"Wrong input: Collection requires specified vector name in the request, available names: text-dense, text-sparse"},"time":0.000048875}'
```

**Analysis:**
- This is a **pre-existing failure** (not introduced by refactoring)
- Qdrant API compatibility issue - collection expects vector name specification
- Affects metadata filtering tests only
- Does NOT block refactoring work

**Refactoring Target:**
- Maintain 349 passed tests (no regressions)
- Do NOT introduce new failures
- The 1 pre-existing failure is acceptable baseline

---

## Test Dependencies Mapped

### pipeline.py Dependencies
**File:** `docs/refactoring/test_dependencies_pipeline.txt`
**Total:** 34 imports from pipeline.py across test suite

**Affected Test Files:**
- `tests/unit/test_ingestion.py` - primary unit tests
- `tests/integration/test_ingestion_integration.py` - integration tests
- 12 other test files import pipeline functions

**Mitigation:** Compatibility shim pattern (re-export all functions from new modules)

### adaptive_table_extraction.py Dependencies
**File:** `docs/refactoring/test_dependencies_table.txt`
**Total:** 1 import

**Affected Test Files:**
- `tests/unit/test_transposed_table_extraction.py` - transposed table tests

**Mitigation:** Create `raglite/ingestion/table_extraction/__init__.py` with re-exports

---

## Coverage Baseline

**Command:** `uv run pytest --cov=raglite --cov-report=term --no-cov-on-fail -q`
**Status:** Recording (in progress)
**Output File:** `docs/refactoring/baseline_coverage.txt`

**Target:** Maintain coverage % after refactoring

---

## Oversized Files Identified

### File 1: adaptive_table_extraction.py
- **Lines:** 3109
- **Functions:** 29
- **Over Limit:** 3x (1000 line hard limit)
- **Epic 3 Relevance:** MEDIUM
- **Strategy:** Split into 5 focused modules (~600 lines each)

### File 2: pipeline.py
- **Lines:** 2302
- **Functions:** 14
- **Over Limit:** 2.3x
- **Epic 3 Relevance:** MEDIUM
- **Strategy:** Split into 4 focused modules (~500-600 lines each)

### Total Impact
- **Total Lines:** 5,411 lines to refactor
- **Total Modules Created:** 9 new focused modules
- **Test Impact:** 35 test imports (34 pipeline + 1 table)

---

## Refactoring Strategy

**Document:** `docs/refactoring/refactoring-strategy.md` (9,600 words)

**Key Decisions:**
1. **Compatibility Shims:** Keep original files as re-export shims (zero test changes)
2. **No Circular Dependencies:** All new modules have clean dependency trees
3. **Single Responsibility:** Each new module has focused, clear purpose
4. **Validation Gates:** Run tests after EACH module split
5. **Priority Order:** pipeline.py first (higher test impact), then adaptive_table_extraction.py

**Module Structure:**

```
adaptive_table_extraction.py (3109 lines) →
  raglite/ingestion/table_extraction/
  ├── classification.py      (~400 lines) - Header & layout detection
  ├── multi_header.py        (~600 lines) - Multi-header extraction
  ├── standard_layouts.py    (~700 lines) - Standard pivot extraction
  ├── unit_inference.py      (~800 lines) - Unit & context inference
  └── core.py                (~600 lines) - Main API & helpers

pipeline.py (2302 lines) →
  raglite/ingestion/
  ├── document_ingestion.py   (~500 lines) - PDF/Excel extraction
  ├── chunking_strategy.py    (~800 lines) - Text + table chunking
  ├── embedding_generation.py (~500 lines) - Embeddings + metadata
  └── storage_operations.py   (~500 lines) - Qdrant + PostgreSQL
```

---

## Validation Criteria

### Per-Module Validation (After EACH split)
- [ ] New modules created with correct structure
- [ ] Functions moved to appropriate modules
- [ ] Compatibility shim created (re-exports)
- [ ] Unit tests pass: `pytest tests/unit/test_[module].py -v`
- [ ] Integration tests pass: `pytest tests/integration/ -k [module]`
- [ ] Test discovery works: `pytest --collect-only` (358 tests found)
- [ ] No import errors
- [ ] Git commit created (rollback safety)

### Final Validation (After ALL splits)
- [ ] All files <1000 lines (verify with script)
- [ ] 349 tests passing (no regressions)
- [ ] Coverage ≥ baseline percentage
- [ ] Test timing within ±10% of baseline (676.52s)
- [ ] No circular dependencies
- [ ] Winston architecture approval

---

## Git Checkpoint

**Status:** Staged for commit
**Files:**
- `docs/refactoring/` - All baseline and strategy documents
- `scripts/identify-oversized-files.py` - Identification script

**Next Checkpoint:** After Winston approval, before starting refactoring

---

## Next Steps

1. ⏸️ **BLOCKED:** Await Winston/Ricardo approval of refactoring strategy
2. Once approved: Execute pipeline.py refactoring (Priority 1)
3. Execute adaptive_table_extraction.py refactoring (Priority 2)
4. Final Winston review and Epic 3 readiness sign-off

---

## Timeline Estimate

- **Winston Review:** 2 hours (blocking)
- **Refactoring Execution:** 14 hours (1.75 days)
- **Final Validation:** 2 hours
- **Total:** 2-3 days including approval cycles

---

**Baseline Established:** 2025-11-05
**Next Update:** After Winston approval
