# Refactoring Strategy - Story 3.0.1

## Executive Summary

This document defines the refactoring strategy for splitting 2 oversized Python modules (5,411 lines total) into maintainable, focused components to prepare for Epic 3 agentic orchestration features.

**Scope:**
- ❌ **adaptive_table_extraction.py**: 3109 lines → split into 5 focused modules (~600 lines each)
- ❌ **pipeline.py**: 2302 lines → split into 4 focused modules (~500-600 lines each)

**Constraints:**
- Refactor ONLY - no functionality changes
- Maintain 100% test pass rate throughout
- Use compatibility shims to avoid breaking 34 test imports
- Single responsibility principle for all new modules

---

## Module 1: adaptive_table_extraction.py (3109 lines → 5 modules)

### Current Structure
- **Lines:** 3109
- **Functions:** 29 (mix of public APIs and private helpers)
- **Responsibilities:** Table layout detection, header classification, multi-format extraction, unit inference, context analysis

### Epic 3 Impact
**Medium relevance** - Agentic workflows will process extracted tables, but table extraction itself is not in the critical path for agent coordination.

### Logical Boundaries Identified

Based on code analysis, this file has 5 clear domain separations:

1. **Header Classification & Layout Detection** (~400 lines)
   - `HeaderType` enum
   - `TableLayout` enum
   - `classify_header()` - pattern matching for TEMPORAL/ENTITY/METRIC
   - `detect_table_layout()` - layout pattern recognition
   - `_detect_orientation()` - orientation detection
   - `_detect_table_orientation()` - statistical orientation analysis

2. **Multi-Header Extraction** (~600 lines)
   - `_extract_multi_header_metric_entity()` - complex multi-header tables
   - Multi-row header parsing
   - Entity-Metric-Period mapping

3. **Standard Layout Extraction** (~700 lines)
   - `_extract_temporal_cols_metric_rows()` - pivot table: columns=periods
   - `_extract_entity_cols_metric_rows()` - pivot table: columns=entities
   - `_extract_transposed_entity_cols_metric_row_labels()` - transposed tables

4. **Unit Inference & Context Analysis** (~800 lines)
   - `_infer_unit_from_context()` - synchronous unit inference
   - `_infer_unit_from_context_async()` - async unit inference via Mistral
   - `_infer_units_batch_async()` - batch processing
   - `_apply_context_aware_unit_inference()` - application logic
   - `_apply_context_aware_unit_inference_async()` - async application
   - `_extract_units_normal()` - unit extraction from cells
   - `_extract_units_entity_column_junk()` - junk column handling
   - `_detect_unit_column_statistical()` - statistical unit detection
   - `_parse_value_unit()` - value/unit parsing

5. **Core API & Helpers** (~600 lines)
   - `extract_table_data_adaptive()` - main public async API
   - `_extract_fallback()` - fallback extraction
   - `_infer_metric_from_context()` - metric inference
   - `_infer_entity_from_context()` - entity inference
   - `_is_numeric_value()` - numeric validation
   - `_analyze_column()` - column analysis
   - `_extract_year()` - year extraction
   - `_get_table_caption()` - caption extraction
   - `_extract_page_context()` - page context extraction
   - `_get_table_markdown()` - markdown conversion

### Proposed Module Structure

```
raglite/ingestion/table_extraction/
├── __init__.py                     # Re-export public API
├── classification.py               # Header & layout classification (~400 lines)
├── multi_header.py                 # Multi-header table extraction (~600 lines)
├── standard_layouts.py             # Standard pivot extraction (~700 lines)
├── unit_inference.py               # Unit & context inference (~800 lines)
└── core.py                         # Main API & helpers (~600 lines)
```

### Module Responsibilities

**classification.py** (~400 lines)
- `HeaderType` enum
- `TableLayout` enum
- `classify_header()` - PUBLIC
- `detect_table_layout()` - PUBLIC
- `_detect_orientation()` - INTERNAL
- `_detect_table_orientation()` - INTERNAL

**multi_header.py** (~600 lines)
- `_extract_multi_header_metric_entity()` - INTERNAL
- Multi-row header parsing logic
- Entity-Metric-Period tuple mapping

**standard_layouts.py** (~700 lines)
- `_extract_temporal_cols_metric_rows()` - INTERNAL
- `_extract_entity_cols_metric_rows()` - INTERNAL
- `_extract_transposed_entity_cols_metric_row_labels()` - INTERNAL

**unit_inference.py** (~800 lines)
- `_infer_unit_from_context()` - INTERNAL
- `_infer_unit_from_context_async()` - INTERNAL
- `_infer_units_batch_async()` - INTERNAL
- `_apply_context_aware_unit_inference()` - INTERNAL
- `_apply_context_aware_unit_inference_async()` - INTERNAL
- `_extract_units_normal()` - INTERNAL
- `_extract_units_entity_column_junk()` - INTERNAL
- `_detect_unit_column_statistical()` - INTERNAL
- `_parse_value_unit()` - INTERNAL
- `MISTRAL_SEMAPHORE` - shared semaphore

**core.py** (~600 lines)
- `extract_table_data_adaptive()` - PUBLIC ASYNC API
- `_extract_fallback()` - INTERNAL
- `_infer_metric_from_context()` - INTERNAL
- `_infer_entity_from_context()` - INTERNAL
- `_is_numeric_value()` - INTERNAL
- `_analyze_column()` - INTERNAL
- `_extract_year()` - INTERNAL
- `_get_table_caption()` - INTERNAL
- `_extract_page_context()` - INTERNAL
- `_get_table_markdown()` - INTERNAL

### Import Dependencies

**classification.py**
- No dependencies on other table extraction modules
- Base-level module

**multi_header.py**
- Imports: `classification.HeaderType`, `classification.TableLayout`

**standard_layouts.py**
- Imports: `classification.HeaderType`, `classification.TableLayout`

**unit_inference.py**
- Imports: `classification.HeaderType` (for context analysis)

**core.py**
- Imports: `classification.detect_table_layout`, `classification.TableLayout`
- Imports: `multi_header._extract_multi_header_metric_entity`
- Imports: `standard_layouts.*_extract_*` functions
- Imports: `unit_inference.*` functions

**No circular dependencies** - all modules depend only on classification.py and core.py orchestrates.

### Test Impact

**Test Files Affected:**
- `tests/unit/test_transposed_table_extraction.py` - imports `adaptive_table_extraction`

**Mitigation Strategy:**
1. Create `raglite/ingestion/table_extraction/__init__.py` with re-exports:
   ```python
   from .classification import HeaderType, TableLayout, classify_header, detect_table_layout
   from .core import extract_table_data_adaptive

   __all__ = [
       'HeaderType',
       'TableLayout',
       'classify_header',
       'detect_table_layout',
       'extract_table_data_adaptive',
   ]
   ```

2. Keep `adaptive_table_extraction.py` as compatibility shim temporarily:
   ```python
   # Compatibility shim - TEMPORARY
   from .table_extraction import *  # noqa
   ```

3. This allows tests to continue using original imports while we refactor

---

## Module 2: pipeline.py (2302 lines → 4 modules)

### Current Structure
- **Lines:** 2302
- **Functions:** 14 (mix of ingestion stages)
- **Responsibilities:** Document ingestion (PDF/Excel), chunking (text/table-aware), embedding generation, vector/metadata storage

### Epic 3 Impact
**Medium-High relevance** - Agentic workflows need clean chunking APIs but don't modify the ingestion pipeline itself.

### Logical Boundaries Identified

Based on code analysis, this file has 4 clear domain separations:

1. **Document Ingestion** (~500 lines)
   - `ingest_document()` - main entry point (routes by file type)
   - `ingest_pdf()` - PDF ingestion with Docling
   - `extract_excel()` - Excel ingestion with pandas/openpyxl
   - Exception classes: `EmbeddingGenerationError`, `VectorStorageError`

2. **Chunking Strategy** (~800 lines)
   - `chunk_document()` - main chunking orchestrator
   - `chunk_by_docling_items()` - text + table-aware chunking (Story 2.8)
   - `split_large_table_by_rows()` - table row splitting logic
   - Token counting, semantic segmentation

3. **Embedding & Metadata** (~500 lines)
   - `generate_embeddings()` - Fin-E5 embedding generation
   - `extract_chunk_metadata()` - contextual metadata extraction (Story 2.4)
   - Batch processing logic

4. **Storage Operations** (~500 lines)
   - `create_collection()` - Qdrant collection initialization
   - `store_vectors_in_qdrant()` - vector storage
   - `store_metadata_in_postgresql()` - chunk metadata storage
   - `store_tables_in_postgresql()` - SQL table storage

### Proposed Module Structure

```
raglite/ingestion/
├── document_ingestion.py           # PDF/Excel extraction (~500 lines)
├── chunking_strategy.py            # Text + table-aware chunking (~800 lines)
├── embedding_generation.py         # Embeddings + metadata (~500 lines)
├── storage_operations.py           # Qdrant + PostgreSQL storage (~500 lines)
└── pipeline.py                     # COMPATIBILITY SHIM (re-exports)
```

### Module Responsibilities

**document_ingestion.py** (~500 lines)
- `EmbeddingGenerationError` exception
- `VectorStorageError` exception
- `ingest_document()` - PUBLIC API (routes by file type)
- `ingest_pdf()` - PUBLIC API (PDF processing)
- `extract_excel()` - PUBLIC API (Excel processing)

**chunking_strategy.py** (~800 lines)
- `chunk_document()` - PUBLIC API (main orchestrator)
- `chunk_by_docling_items()` - INTERNAL (Docling-based chunking)
- `split_large_table_by_rows()` - INTERNAL (table row splitting)
- Token counting helpers
- Semantic segmentation logic

**embedding_generation.py** (~500 lines)
- `generate_embeddings()` - PUBLIC API (Fin-E5 batch processing)
- `extract_chunk_metadata()` - PUBLIC API (contextual metadata)
- Batch processing logic
- Embedding model management

**storage_operations.py** (~500 lines)
- `create_collection()` - PUBLIC API (Qdrant setup)
- `store_vectors_in_qdrant()` - PUBLIC API (vector storage)
- `store_metadata_in_postgresql()` - PUBLIC API (chunk metadata)
- `store_tables_in_postgresql()` - PUBLIC API (SQL table storage)

### Import Dependencies

**document_ingestion.py**
- No dependencies on other ingestion modules
- Base-level module

**chunking_strategy.py**
- No dependencies on other ingestion modules
- Base-level module

**embedding_generation.py**
- No dependencies on other ingestion modules
- Base-level module

**storage_operations.py**
- No dependencies on other ingestion modules
- Base-level module

**No circular dependencies** - all modules are independent.

### Test Impact

**Test Files Affected (34 imports):**
- `tests/unit/test_ingestion.py` - imports multiple functions
- `tests/integration/test_ingestion_integration.py` - imports pipeline functions
- 12 other test files import from pipeline.py (per grep analysis)

**Mitigation Strategy:**
1. Keep `pipeline.py` as compatibility shim with re-exports:
   ```python
   # Compatibility shim for existing imports
   from .document_ingestion import (
       EmbeddingGenerationError,
       VectorStorageError,
       ingest_document,
       ingest_pdf,
       extract_excel,
   )
   from .chunking_strategy import (
       chunk_document,
       chunk_by_docling_items,
       split_large_table_by_rows,
   )
   from .embedding_generation import (
       generate_embeddings,
       extract_chunk_metadata,
   )
   from .storage_operations import (
       create_collection,
       store_vectors_in_qdrant,
       store_metadata_in_postgresql,
       store_tables_in_postgresql,
   )

   __all__ = [
       # Exceptions
       'EmbeddingGenerationError',
       'VectorStorageError',
       # Ingestion
       'ingest_document',
       'ingest_pdf',
       'extract_excel',
       # Chunking
       'chunk_document',
       'chunk_by_docling_items',
       'split_large_table_by_rows',
       # Embeddings
       'generate_embeddings',
       'extract_chunk_metadata',
       # Storage
       'create_collection',
       'store_vectors_in_qdrant',
       'store_metadata_in_postgresql',
       'store_tables_in_postgresql',
   ]
   ```

2. This allows ALL existing tests to continue working without modification

---

## Implementation Order

### Priority 1: pipeline.py (Higher Test Impact)
- **Rationale:** 34 test imports, more test dependencies
- **Risk:** Higher regression risk due to test coupling
- **Strategy:** Implement compatibility shim first, validate all tests pass

### Priority 2: adaptive_table_extraction.py (Lower Test Impact)
- **Rationale:** Only 1 test import
- **Risk:** Lower regression risk
- **Strategy:** Can refactor more aggressively after pipeline.py success

---

## Refactoring Protocol (Per Module)

### Phase 1: Pre-Refactoring Checklist
- [ ] Baseline tests recorded (pytest results, coverage, timing)
- [ ] Test dependencies mapped (grep analysis complete)
- [ ] Git checkpoint created (`git commit -m "checkpoint: pre-refactoring baseline"`)

### Phase 2: Module Split (Per File)
1. Create new focused modules in target structure
2. Move functions/classes to appropriate modules
3. Add type hints and docstrings if missing
4. Create compatibility shim with re-exports in original file
5. Run affected unit tests: `pytest tests/unit/test_[module].py -v`
6. STOP if failures - fix before continuing

### Phase 3: Import Validation
1. Test discovery: `pytest --collect-only` (verify 358 tests found)
2. Run affected integration tests: `pytest tests/integration/ -k [module]`
3. Run full suite: `pytest tests/`
4. Check coverage: `pytest --cov=raglite.[module]`

### Phase 4: Commit
1. `git add -A`
2. `git commit -m "refactor: split [module] into focused modules"`

### Phase 5: Validation Gates
- ✅ All tests pass (100% pass rate)
- ✅ Coverage maintained (≥ baseline)
- ✅ No circular dependencies (verify with `import` tests)
- ✅ Test timing within ±10% of baseline

---

## Test Safety Protocol

### Compatibility Shim Pattern

**Purpose:** Allow existing tests to work unchanged during transition

**Implementation:**
```python
# raglite/ingestion/pipeline.py (compatibility shim)
"""
COMPATIBILITY SHIM - Re-exports for backward compatibility.

This file temporarily re-exports all functions from the new focused modules
to maintain compatibility with existing tests and imports.

TODO: Remove this shim after test imports are updated (can be separate PR).
"""

from .document_ingestion import (
    ingest_document,
    ingest_pdf,
    extract_excel,
    EmbeddingGenerationError,
    VectorStorageError,
)
from .chunking_strategy import (
    chunk_document,
    chunk_by_docling_items,
    split_large_table_by_rows,
)
from .embedding_generation import (
    generate_embeddings,
    extract_chunk_metadata,
)
from .storage_operations import (
    create_collection,
    store_vectors_in_qdrant,
    store_metadata_in_postgresql,
    store_tables_in_postgresql,
)

__all__ = [
    # ... (all exports listed)
]
```

**Benefits:**
- Zero test changes required during refactoring
- Rollback safety (tests continue to pass)
- Can update test imports in separate PR later

### Automated Import Update (Optional - Deferred)

**Script:** `scripts/update_test_imports.py`

**Purpose:** Update test imports to use new modules directly (can be deferred)

**Usage:**
```bash
# Dry run (preview changes)
python scripts/update_test_imports.py --dry-run

# Apply changes
python scripts/update_test_imports.py --apply

# Verify
pytest tests/ --collect-only
pytest tests/ -x
```

**Note:** This step is OPTIONAL and can be deferred to a separate PR after refactoring is complete and validated.

---

## Success Criteria (AC1-AC4)

### AC1: Identify Oversized Files ✅
- [x] Report generated: `docs/refactoring/oversized-files-report.txt`
- [x] 2 files identified (adaptive_table_extraction.py, pipeline.py)
- [x] Prioritized by Epic 3 relevance

### AC2: Define Refactoring Strategy ✅
- [x] Strategy documented: `docs/refactoring/refactoring-strategy.md` (this file)
- [x] Module boundaries defined (single responsibility)
- [ ] **Winston architecture review approval pending**

### AC3: Execute Refactoring (Pending)
- [ ] pipeline.py split (4 modules)
- [ ] adaptive_table_extraction.py split (5 modules)
- [ ] All files <1000 lines
- [ ] 100% test pass rate maintained
- [ ] Coverage ≥ baseline

### AC4: Architecture Review (Pending)
- [ ] Winston final approval
- [ ] No circular dependencies
- [ ] Epic 3 Stories 3.1+ unblocked

---

## Risk Assessment

### Low Risk
- **Test compatibility shims:** Proven pattern, minimal regression risk
- **Independent modules:** No circular dependencies in proposed structure
- **Baseline established:** Can rollback to any checkpoint

### Medium Risk
- **34 test imports from pipeline.py:** Compatibility shim required
- **Large module splits:** Potential for missed edge cases during refactoring

### Mitigation Strategies
- Use compatibility shims (zero test changes required)
- One module at a time (rollback safety)
- Run full test suite after each module split
- Commit after each successful refactor

---

## Timeline Estimate

### Phase 1: Pre-Refactoring (Complete)
- ✅ Baseline established
- ✅ Strategy documented
- ⏳ Winston review: **2 hours** (blocking next phase)

### Phase 2: Execute Refactoring
- pipeline.py split: **8 hours** (4 modules, compatibility shim, testing)
- adaptive_table_extraction.py split: **6 hours** (5 modules, less test impact)
- **Total: 14 hours (1.75 days)**

### Phase 3: Final Validation
- Winston review: **1 hour**
- Final testing: **1 hour**
- **Total: 2 hours**

**Overall Timeline: 2-3 days** (including Winston review cycles)

---

## Next Steps

1. **Ricardo/Winston:** Review and approve this refactoring strategy ✅
2. **Dev (Amelia):** Execute pipeline.py refactoring (Priority 1)
3. **Dev (Amelia):** Execute adaptive_table_extraction.py refactoring (Priority 2)
4. **Winston:** Final architecture review and Epic 3 readiness sign-off

---

**Strategy Version:** 1.0
**Date:** 2025-11-05
**Author:** Amelia (Dev Agent)
**Status:** Pending Winston Approval
