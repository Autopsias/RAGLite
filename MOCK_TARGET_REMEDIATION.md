# Mock Target Remediation Plan - Epic 8 Technical Debt

**Created:** 2025-01-06
**Session:** Follow-up to batch 4/4 completion
**Status:** Ready for next session
**Total Issues:** 1,107 invalid mock targets across 140 test files

---

## Summary

Fixed 61 invalid mock targets in batch 4/4. **Remaining: 1,107 issues in 140 test files** need remediation from Epic 8 module reorganization.

This document provides a complete remediation plan for parallel execution in the next session.

---

## Quick Start Command

```bash
# In next session, run:
/code_quality --fix --focus=mock-targets

# Or manually:
python3 scripts/validate-mock-targets.py --verbose > /tmp/mock-issues.txt
# Then process file by file
```

---

## Problem Analysis

### Root Cause
Epic 8 (Stories 8.1-8.4) reorganized module structure:
- `document_ingestion.py` → `document_ingestion/` package
- `forecasting/model_selection.py` → Multiple new modules
- `embedding_generation/` moved to `ingestion/embedding_generation/`
- `shared/` module consolidated client classes

Tests still mock OLD module paths that no longer exist.

### Impact
- **140 test files** affected
- **1,107 invalid mock targets**
- **Pre-commit hook blocks commits** to these files
- **Tests may pass in isolation** but fail in CI due to stale mocks

---

## Module Migration Map

### 1. Document Ingestion (Story 8.3)

| Old Path | New Path | Pattern |
|----------|----------|----------|
| `raglite.ingestion.document_ingestion.pdf_processing.*` | `raglite.ingestion.document_ingestion.pdf_processing.*` | No change (same name) |
| `raglite.ingestion.document_ingestion.core.*` | `raglite.ingestion.document_ingestion.*` | Removed `core.` |
| `raglite.ingestion.storage.*` | `raglite.ingestion.storage.*` | No change |
| `raglite.ingestion.embedding_generation.*` | `raglite.ingestion.embedding_generation.*` | No change |

### 2. Model Selection (Stories 8.1, 8.2)

| Old Path | New Path | Pattern |
|----------|----------|----------|
| `raglite.forecasting.model_selection.select_model_type` | `raglite.forecasting.regressor_config.select_model_type` | Moved to regressor_config |
| `raglite.forecasting.model_selection.fetch_regressors_with_date_range` | `raglite.forecasting.regressor_fetch.fetch_regressors_with_date_range` | Moved to regressor_fetch |
| `raglite.forecasting.model_selection.fetch_historical_data` | `raglite.external_data.clients.atic.ATIClient.fetch_historical_data` | Moved to ATIClient class |
| `raglite.forecasting.model_selection.cache_model_selection` | `raglite.external_data.storage.model_selection.cache_model_selection` | Moved to storage module |
| `raglite.forecasting.model_selection.get_cached_model_selection` | `raglite.external_data.storage.model_selection.get_cached_model_selection` | Moved to storage module |
| `raglite.forecasting.model_selection.select_best_model` | `raglite.forecasting.mixed_selection.select_best_model` | Moved to mixed_selection |

### 3. Hybrid Forecasting

| Old Path | New Path | Pattern |
|----------|----------|----------|
| `raglite.forecasting.hybrid.ensemble.*` | `raglite.forecasting.hybrid.*` | Removed `ensemble.` submodule |
| `raglite.forecasting.hybrid.preprocessing_data.*` | `raglite.forecasting.hybrid.*` | Removed `preprocessing_data.` submodule |
| `raglite.forecasting.hybrid.model_generators.*` | `raglite.forecasting.hybrid.*` | Removed `model_generators.` submodule |
| `raglite.forecasting.hybrid.lazy_imports.*` | `raglite.forecasting.hybrid.*` | Removed `lazy_imports.` submodule |

### 4. Settings/Config

| Old Path | New Path | Pattern |
|----------|----------|----------|
| `raglite.ingestion.embedding_generation.settings` | `raglite.shared.config.settings` | Consolidated in shared |
| `raglite.shared.clients.*` | `raglite.shared.config.settings` | Clients removed, use settings |

### 5. External Data Refresh

| Old Path | New Path | Pattern |
|----------|----------|----------|
| `raglite.external_data.refresh._refresh_ipma` | `raglite.external_data.refresh.SOURCE_REFRESH_FUNCTIONS["IPMA"]` | Private → public dict |
| `raglite.external_data.refresh._refresh_omie` | `raglite.external_data.refresh.SOURCE_REFRESH_FUNCTIONS["OMIE"]` | Private → public dict |
| `raglite.external_data.refresh._refresh_*` | `raglite.external_data.refresh.SOURCE_REFRESH_FUNCTIONS` | Private → public dict |

---

## Files Requiring Fixes

### High Priority (30+ issues each)
1. **tests/unit/test_ingestion_pdf.py** - 60 issues
2. **tests/unit/ingestion/test_pdf_ingestion.py** - 60 issues
3. **tests/unit/services/test_attachment_extractor_expanded.py** - 39 issues
4. **tests/unit/ingestion/document_ingestion/test_pdf_processing_edge_cases.py** - 33 issues

### Medium Priority (20-29 issues)
5. **tests/integration/test_scheduler_integration.py** - 30 issues (partial - we fixed some)
6. **tests/unit/forecasting/test_mcp_model_routing_core.py** - 28 issues
7. **tests/unit/ingestion/test_module_integration.py** - 27 issues
8. **tests/unit/test_mcp_edge_cases.py** - 25 issues
9. **tests/e2e/test_mcp_e2e_integration.py** - 25 issues
10. **tests/unit/test_mcp_cache_exceptions.py** - 24 issues
11. **tests/unit/test_ingestion_excel.py** - 23 issues
12. **tests/integration/test_auto_forecast_update.py** - 23 issues
13. **tests/unit/ingestion/test_excel_processing.py** - 22 issues
14. **tests/unit/ingestion/test_unit_inference_context.py** - 21 issues

### Lower Priority (1-19 issues)
**Remaining 126 files** with 1-19 issues each.

---

## Remediation Strategy

### Phase 1: High-Value Files (Parallel Batch 1)

**Target:** Top 14 files with 20+ issues (~520 issues total)

**Parallel execution:** 6 agents at a time

**Agent delegation:**
```python
# Batch 1a (Files 1-6)
Task(import-error-fixer, "Fix test_ingestion_pdf.py (60 issues)", ...)
Task(import-error-fixer, "Fix test_pdf_ingestion.py (60 issues)", ...)
Task(import-error-fixer, "Fix test_attachment_extractor_expanded.py (39 issues)", ...)
Task(import-error-fixer, "Fix test_pdf_processing_edge_cases.py (33 issues)", ...)
Task(import-error-fixer, "Fix test_scheduler_integration.py (30 issues)", ...)
Task(import-error-fixer, "Fix test_mcp_model_routing_core.py (28 issues)", ...)

# Batch 1b (Files 7-12)
Task(import-error-fixer, "Fix test_module_integration.py (27 issues)", ...)
Task(import-error-fixer, "Fix test_mcp_edge_cases.py (25 issues)", ...)
Task(import-error-fixer, "Fix test_mcp_e2e_integration.py (25 issues)", ...)
Task(import-error-fixer, "Fix test_mcp_cache_exceptions.py (24 issues)", ...)
Task(import-error-fixer, "Fix test_ingestion_excel.py (23 issues)", ...)
Task(import-error-fixer, "Fix test_auto_forecast_update.py (23 issues)", ...)
```

### Phase 2: Medium-Value Files (Parallel Batch 2)

**Target:** Files with 10-19 issues (~400 issues)

**Parallel execution:** 6 agents at a time

### Phase 3: Low-Priority Files (Parallel Batch 3)

**Target:** Files with 1-9 issues (~187 issues)

**Parallel execution:** 6 agents at a time

---

## Agent Prompt Template

Each agent should receive:

```
Fix invalid mock targets in TEST_FILE from Epic 8 refactoring.

**Context:**
Epic 8 reorganized modules. Mock targets must be updated to new locations.

**Module Mappings:**
[Use the migration map from this document]

**File:** TEST_FILE
**Issues:** N invalid mock targets

**Rules:**
1. Patch where the function is IMPORTED and USED, not where it's defined
2. Use string-based patch() for class methods to avoid ruff errors
3. Update all mock targets according to the migration map
4. Don't modify test logic - only fix mock targets

**Output:**
Return JSON: {"status": "fixed|partial|failed", "issues_fixed": N, "files_modified": ["..."]}

Execute autonomously and report JSON summary only.
```

---

## Validation

After each batch:

```bash
# Re-run validation
python3 scripts/validate-mock-targets.py

# Check progress
python3 scripts/validate-mock-targets.py 2>&1 | grep "Found.*invalid"

# Commit batch
git add tests/
git commit -m "fix(tests): mock target remediation batch X - N files fixed"
```

---

## Success Criteria

- ✅ All 1,107 invalid mock targets fixed
- ✅ `python3 scripts/validate-mock-targets.py` returns 0 errors
- ✅ Pre-commit hook passes on all test files
- ✅ All tests still pass (no logic changes, only mock paths)

---

## Estimated Time

- **Phase 1 (520 issues):** ~90 minutes with 6 parallel agents
- **Phase 2 (400 issues):** ~60 minutes with 6 parallel agents
- **Phase 3 (187 issues):** ~30 minutes with 6 parallel agents
- **Total:** ~3 hours of parallel execution

---

## References

- Original fix: Commit `4be25a9` (61 issues in 16 files)
- Epic 8 migration notes: `docs/sprint-artifacts/epic-8-migration-notes.md`
- Validation script: `scripts/validate-mock-targets.py`
- Test rules: `.claude/rules/testing.md`
