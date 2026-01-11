# Epic 8: Comprehensive Refactoring Plan
## Technical Debt Reduction - All 170 Violations

**Generated:** 2026-01-01
**Scope:** 64 file violations + 126 function violations
**Target:** Reduce all grandfathered exceptions to zero over 8 phases

---

## Executive Summary

### Current State
- **Total violations:** 170 (64 files + 126 functions, some overlap)
- **Largest file:** `raglite/shared/models.py` (1,432 LOC)
- **Largest function:** `extract_timeseries_from_sql()` (1,322 LOC)
- **Most impacted:** `raglite/shared/models.py` (51 files + 243 tests depend on it)

### Critical Dependencies Discovered
| File | Dependents | Test Impact | Blocker Status |
|------|------------|-------------|----------------|
| `raglite/shared/models.py` | 51 files | 243 tests | 🔴 **CRITICAL BLOCKER** |
| `raglite/retrieval/search.py` | 7 files | 81 tests | 🟠 **HIGH IMPACT** |
| `raglite/ingestion/chunking_strategy.py` | 2 files | 3 tests | 🟡 **MEDIUM IMPACT** |
| `raglite/forecasting/timeseries/sql_extraction.py` | 1 file | 0 tests | 🟢 **ISOLATED** |

### Strategy
**Sequential foundation → Parallel execution → Gradual reduction**

1. **Phase 0:** Foundation infrastructure (BLOCKER - must do first)
2. **Phase 1:** Critical path modules (HIGH impact - serial)
3. **Phase 2:** Forecasting pipeline (LARGEST - parallel batches)
4. **Phase 3:** External data clients (INDEPENDENT - parallel)
5. **Phase 4:** Support modules (INDEPENDENT - parallel)
6. **Phase 5:** Test infrastructure (AFTER production code stable)
7. **Phase 6:** Function-only violations (GRADUAL reduction)
8. **Phase 7:** Final cleanup & validation

---

## Phase 0: Foundation Infrastructure (BLOCKER)
**Duration:** 3-5 days | **Parallelization:** NONE (sequential) | **Risk:** CRITICAL

### Objective
Refactor foundational modules that block all other work.

### Batch 0.1: Shared Models (CRITICAL BLOCKER)
**Files:** 1
**Dependencies:** 51 files + 243 tests
**Strategy:** Split by domain, facade pattern, phased migration

| File | LOC | Target | Strategy |
|------|-----|--------|----------|
| `raglite/shared/models.py` | 1,432 | 8 files × <200 LOC | Domain-based split |

**Proposed structure:**
```
raglite/shared/models/
├── __init__.py          # Re-export all for backward compat
├── base.py              # Base Pydantic classes (~150 LOC)
├── document.py          # DocumentMetadata, Chunk (~180 LOC)
├── query.py             # QueryResult, QueryRequest (~180 LOC)
├── forecast.py          # ForecastResult, TimeSeriesData (~200 LOC)
├── external_data.py     # External data models (~180 LOC)
├── ingestion.py         # Ingestion-specific models (~180 LOC)
└── retrieval.py         # Retrieval-specific models (~180 LOC)
```

**Acceptance Criteria:**
- AC1: Original `models.py` reduced to <200 LOC (facade only)
- AC2: All 8 domain files <200 LOC each
- AC3: Zero test failures (all 243 tests pass)
- AC4: No circular dependencies introduced
- AC5: Facade maintains 100% backward compatibility
- AC6: Coverage maintained at ≥80%

**Migration Strategy:**
1. Create new domain files with moved classes
2. Update `__init__.py` to re-export from new locations
3. Verify all 243 tests pass (facade prevents breakage)
4. Gradual migration: update imports module-by-module (51 files)
5. Remove facade after all imports migrated

**Blocked work:** ALL Phase 1-4 work depends on this

---

### Batch 0.2: Shared Clients (MEDIUM)
**Files:** 1
**Dependencies:** Moderate (used across all modules)

| File | LOC | Target | Strategy |
|------|-----|--------|----------|
| `raglite/shared/clients.py` | 509 | 3 files × <200 LOC | Split by client type |

**Proposed structure:**
```
raglite/shared/clients/
├── __init__.py          # Re-export all
├── database.py          # Qdrant, PostgreSQL (~180 LOC)
├── llm.py               # Claude, Mistral, OpenAI (~180 LOC)
└── embeddings.py        # Fin-E5 embedding model (~150 LOC)
```

**Acceptance Criteria:**
- AC1: Original `clients.py` reduced to <100 LOC (facade)
- AC2: All 3 client files <200 LOC
- AC3: Zero test failures
- AC4: Maintain connection pooling behavior

**Can run in parallel with:** Nothing (blocks some Phase 1 work)

---

## Phase 1: Critical Path Modules (HIGH IMPACT)
**Duration:** 4-6 days | **Parallelization:** SERIAL (shared tests) | **Risk:** HIGH

### Objective
Refactor modules on critical retrieval/ingestion path with high test coverage.

### Batch 1.1: Retrieval Pipeline (SERIAL)
**Files:** 2
**Shared tests:** 81 tests in `tests/integration/test_retrieval*.py`
**Strategy:** Sequential refactoring (shared test dependencies)

#### File 1: raglite/retrieval/search.py (CRITICAL)
**LOC:** 1,146 → Target: 4 files × <300 LOC
**Dependencies:** 7 files + 81 tests

**Proposed structure:**
```
raglite/retrieval/search/
├── __init__.py          # Facade for backward compat
├── semantic.py          # Vector search (~280 LOC)
├── keyword.py           # BM25 search (~250 LOC)
├── hybrid.py            # Fusion logic (~280 LOC)
└── enrichment.py        # Metadata enrichment (~250 LOC)
```

**Functions to extract:**
- `semantic_search()` (158 LOC) → `semantic.py`
- `hybrid_search()` (269 LOC) → `hybrid.py`
- `fuse_search_results()` (175 LOC) → `hybrid.py`
- `enrich_results_with_metadata()` (129 LOC) → `enrichment.py`

**Acceptance Criteria:**
- AC1: Original `search.py` reduced to <200 LOC
- AC2: All 4 modules <300 LOC
- AC3: All 81 retrieval tests pass
- AC4: NFR6 accuracy maintained (≥90%)
- AC5: No performance regression (<5s p50)

---

#### File 2: raglite/retrieval/query_classifier.py (HIGH)
**LOC:** 928 → Target: 3 files × <350 LOC
**Dependencies:** Used by `search.py` + other retrieval modules

**Proposed structure:**
```
raglite/retrieval/query_classifier/
├── __init__.py          # Facade
├── classification.py    # Query type classification (~300 LOC)
├── sql_generation.py    # SQL query generation (~300 LOC)
└── metadata_filter.py   # Metadata filter generation (~250 LOC)
```

**Functions to extract:**
- `classify_query()` (186 LOC) → `classification.py`
- `generate_sql_query()` (298 LOC) → `sql_generation.py`
- `classify_query_metadata()` (149 LOC) → `metadata_filter.py`

**Acceptance Criteria:**
- AC1: Original file reduced to <200 LOC
- AC2: All 3 modules <350 LOC
- AC3: All retrieval tests pass
- AC4: SQL generation accuracy maintained

**CRITICAL:** Must complete `search.py` BEFORE starting this (dependency)

---

### Batch 1.2: Ingestion Pipeline (SERIAL)
**Files:** 5
**Shared tests:** `tests/integration/test_chunking*.py`, `test_*_pipeline.py`
**Strategy:** Sequential (tight coupling in pipeline)

#### File 1: raglite/ingestion/chunking_strategy.py (HIGH)
**LOC:** 826 → Target: 3 files × <300 LOC

**Proposed structure:**
```
raglite/ingestion/chunking/
├── __init__.py          # Facade
├── core.py              # Main chunking logic (~280 LOC)
├── table_splitting.py   # Table-aware splitting (~270 LOC)
└── docling_items.py     # Docling item processing (~270 LOC)
```

**Functions to extract:**
- `chunk_document()` (152 LOC) → `core.py`
- `chunk_by_docling_items()` (360 LOC) → `docling_items.py`
- `split_large_table_by_rows()` (138 LOC) → `table_splitting.py`

**Acceptance Criteria:**
- AC1: Original file reduced to <200 LOC
- AC2: All 3 modules <300 LOC
- AC3: Chunking tests pass (3 test files)
- AC4: Chunk count validation maintained

---

#### File 2: raglite/ingestion/adaptive_table/classification.py (HIGH)
**LOC:** 853 → Target: 3 files × <300 LOC

**Proposed structure:**
```
raglite/ingestion/adaptive_table/classification/
├── __init__.py
├── header.py            # Header classification (~280 LOC)
├── layout.py            # Layout detection (~300 LOC)
└── orientation.py       # Orientation detection (~270 LOC)
```

**Functions to extract:**
- `classify_header()` (172 LOC) → `header.py`
- `detect_table_layout()` (203 LOC) → `layout.py`
- `_detect_table_orientation()` (245 LOC) → `orientation.py`

---

#### File 3: raglite/ingestion/storage_operations.py (HIGH)
**LOC:** 711 → Target: 3 files × <250 LOC

**Proposed structure:**
```
raglite/ingestion/storage/
├── __init__.py
├── vector_store.py      # Qdrant operations (~240 LOC)
├── metadata_store.py    # PostgreSQL metadata (~240 LOC)
└── table_store.py       # PostgreSQL tables (~230 LOC)
```

**Functions to extract:**
- `store_vectors_in_qdrant()` (217 LOC) → `vector_store.py`
- `store_metadata_in_postgresql()` (176 LOC) → `metadata_store.py`
- `store_tables_in_postgresql()` (174 LOC) → `table_store.py`

---

#### File 4: raglite/ingestion/adaptive_table/standard_layouts.py (MEDIUM)
**LOC:** 635 → Target: 2 files × <350 LOC

**Proposed structure:**
```
raglite/ingestion/adaptive_table/layouts/
├── __init__.py
├── entity_metric.py     # Entity-metric layouts (~320 LOC)
└── transposed.py        # Transposed layouts (~315 LOC)
```

**Functions to extract:**
- `_extract_entity_cols_metric_rows()` (101 LOC) → `entity_metric.py`
- `_extract_transposed_entity_cols_metric_row_labels()` (433 LOC) → `transposed.py`

---

#### File 5: raglite/ingestion/table_extraction.py (LOW)
**LOC:** 517 → Target: 2 files × <280 LOC

**Proposed structure:**
```
raglite/ingestion/table_extraction/
├── __init__.py
├── extraction.py        # Core extraction (~260 LOC)
└── parsing.py           # Structure parsing (~250 LOC)
```

**Functions to extract:**
- `_parse_table_structure()` (125 LOC) → `parsing.py`

---

**Batch 1.2 Execution Order:**
1. `chunking_strategy.py` (used by others)
2. `storage_operations.py` (end of pipeline)
3. `classification.py` → `standard_layouts.py` → `table_extraction.py` (parallel after 1-2 complete)

**Total Phase 1 Duration:** 4-6 days (all serial due to shared tests)

---

## Phase 2: Forecasting Pipeline (LARGEST MODULE)
**Duration:** 6-10 days | **Parallelization:** HIGH (mostly independent) | **Risk:** MEDIUM

### Objective
Refactor forecasting module (15 files) using parallel batches for independent components.

### Batch 2.1: Core Forecasting (SERIAL - 3 files)
**Shared dependency:** `ensemble.py` used by others
**Strategy:** Sequential refactoring

#### File 1: raglite/forecasting/timeseries/sql_extraction.py (CRITICAL)
**LOC:** 1,398 → Target: 4 files × <400 LOC
**Dependencies:** 1 file, 0 tests (ISOLATED!)

**Proposed structure:**
```
raglite/forecasting/timeseries/sql_extraction/
├── __init__.py
├── extraction.py        # Main extraction logic (~350 LOC)
├── query_builder.py     # SQL query building (~380 LOC)
├── validation.py        # Data validation (~330 LOC)
└── parsing.py           # Result parsing (~338 LOC)
```

**Functions to extract:**
- `extract_timeseries_from_sql()` (1,322 LOC) → split into 4 steps
- `build_query()` (148 LOC) → `query_builder.py`

**Acceptance Criteria:**
- AC1: Original file reduced to <200 LOC
- AC2: All 4 modules <400 LOC
- AC3: Function extraction reduces monster function to <100 LOC
- AC4: Timeseries extraction accuracy maintained

**Can run in parallel with:** Most other forecasting work (isolated)

---

#### File 2: raglite/forecasting/hybrid/ensemble.py (HIGH)
**LOC:** 884 → Target: 3 files × <350 LOC

**Proposed structure:**
```
raglite/forecasting/hybrid/ensemble/
├── __init__.py
├── forecast_generation.py  # Main forecast logic (~320 LOC)
├── model_selection.py      # Model routing (~280 LOC)
└── aggregation.py          # Result aggregation (~280 LOC)
```

**Functions to extract:**
- `generate_forecast()` (659 LOC) → split into 3 stages:
  - Data prep → `forecast_generation.py`
  - Model selection → `model_selection.py`
  - Aggregation → `aggregation.py`

**Story 8.5 Note:** Already reduced from 891 → 884 LOC

---

#### File 3: raglite/forecasting/report_generator.py (HIGH)
**LOC:** 807 → Target: 3 files × <300 LOC

**Proposed structure:**
```
raglite/forecasting/reports/
├── __init__.py
├── generator.py         # Report generation (~280 LOC)
├── assessment.py        # Variable assessment (~270 LOC)
└── formatting.py        # Output formatting (~250 LOC)
```

**Functions to extract:**
- `generate_variable_assessment()` (105 LOC) → `assessment.py`

---

### Batch 2.2: Hybrid Models (PARALLEL - 2 files)
**Independent:** No shared tests, can run simultaneously

#### File 1: raglite/forecasting/hybrid/preprocessing.py (MEDIUM)
**LOC:** 656 → Target: 2 files × <350 LOC

**Proposed structure:**
```
raglite/forecasting/hybrid/preprocessing/
├── __init__.py
├── data_prep.py         # Data preparation (~330 LOC)
└── regressors.py        # Regressor preparation (~320 LOC)
```

**Functions to extract:**
- `prepare_regressors()` (132 LOC) → `regressors.py`

---

#### File 2: raglite/forecasting/hybrid/model_generators.py (MEDIUM)
**LOC:** 602 → Target: 2 files × <320 LOC

**Proposed structure:**
```
raglite/forecasting/hybrid/models/
├── __init__.py
├── routing.py           # Model routing logic (~310 LOC)
└── generators.py        # Model generators (~290 LOC)
```

---

### Batch 2.3: Model Selection (PARALLEL - 3 files)
**Independent:** Can run in parallel

#### File 1: raglite/forecasting/model_selection_job.py (MEDIUM)
**LOC:** 601 → Target: 2 files × <320 LOC

**Proposed structure:**
```
raglite/forecasting/model_selection/
├── __init__.py
├── job.py               # Job orchestration (~310 LOC)
└── batch.py             # Batch processing (~290 LOC)
```

**Functions to extract:**
- `run_batch_model_selection()` (105 LOC) → `batch.py`

---

#### File 2: raglite/forecasting/regime_detection.py (LOW)
**LOC:** 600 → Target: 2 files × <320 LOC

**Proposed structure:**
```
raglite/forecasting/regime/
├── __init__.py
├── detection.py         # Regime detection (~310 LOC)
└── analysis.py          # Regime analysis (~290 LOC)
```

**Functions to extract:**
- `detect_regime_changes()` (210 LOC) → `detection.py`

---

#### File 3: raglite/forecasting/ensemble.py (LOW)
**LOC:** 583 → Target: 2 files × <300 LOC

**Proposed structure:**
```
raglite/forecasting/ensemble/
├── __init__.py
├── forecast.py          # Ensemble forecast (~290 LOC)
└── generation.py        # Forecast generation (~290 LOC)
```

**Functions to extract:**
- `generate_ensemble_forecast()` (452 LOC) → split across both files

---

### Batch 2.4: Data Pipeline (PARALLEL - 3 files)

#### File 1: raglite/forecasting/regressor_fetch.py (LOW)
**LOC:** 579 → Target: 2 files × <300 LOC

**Proposed structure:**
```
raglite/forecasting/regressors/
├── __init__.py
├── fetch.py             # Fetching logic (~290 LOC)
└── single_fetch.py      # Single regressor fetch (~285 LOC)
```

**Functions to extract:**
- `fetch_single_regressor()` (351 LOC) → `single_fetch.py`

---

#### File 2: raglite/forecasting/data_quality/config.py (LOW)
**LOC:** 578 → Target: 2 files × <300 LOC

**Proposed structure:**
```
raglite/forecasting/data_quality/config/
├── __init__.py
├── rules.py             # Quality rules (~290 LOC)
└── thresholds.py        # Thresholds config (~285 LOC)
```

---

#### File 3: raglite/forecasting/data_analyzer.py (LOW)
**LOC:** 568 → Target: 2 files × <300 LOC

**Proposed structure:**
```
raglite/forecasting/analysis/
├── __init__.py
├── analyzer.py          # Data analysis (~290 LOC)
└── validation.py        # Data validation (~275 LOC)
```

---

### Batch 2.5: Configuration & Utils (PARALLEL - 4 files)
**Independent LOW-priority files:** Can be done anytime

| File | LOC | Target Structure |
|------|-----|------------------|
| `regressor_config.py` | 550 | 2 files × <300 LOC |
| `model_selection_utils.py` | 541 | 2 files × <300 LOC |
| `model_selection.py` | 533 | 2 files × <300 LOC |
| `tft_training.py` | 512 | 2 files × <280 LOC |

**Proposed structures:** Each splits into `core.py` + `utils.py`

---

**Phase 2 Execution Schedule:**

| Week | Batch | Files | Parallelization |
|------|-------|-------|-----------------|
| **Week 1** | Batch 2.1 | 3 files (serial) | 1 agent at a time |
| **Week 2** | Batch 2.2 + 2.3 | 5 files (parallel) | 5 agents simultaneously |
| **Week 3** | Batch 2.4 + 2.5 | 7 files (parallel) | 6 agents simultaneously |

**Total Phase 2 Duration:** 6-10 days with parallel execution

---

## Phase 3: External Data Clients (INDEPENDENT)
**Duration:** 3-5 days | **Parallelization:** FULL (all independent) | **Risk:** LOW

### Objective
Refactor external data clients (6 files) - all independent, can run in parallel.

### Batch 3.1: Large Clients (PARALLEL - 3 files)

#### File 1: raglite/external_data/refresh.py (HIGH)
**LOC:** 969 → Target: 3 files × <350 LOC

**Proposed structure:**
```
raglite/external_data/refresh/
├── __init__.py
├── orchestrator.py      # Refresh orchestration (~330 LOC)
├── scheduler.py         # Scheduling logic (~320 LOC)
└── validation.py        # Data validation (~315 LOC)
```

---

#### File 2: raglite/external_data/clients/ine.py (HIGH)
**LOC:** 768 → Target: 2 files × <400 LOC

**Proposed structure:**
```
raglite/external_data/clients/ine/
├── __init__.py
├── client.py            # API client (~380 LOC)
└── parser.py            # Response parsing (~385 LOC)
```

**Functions to extract:**
- `_fetch_with_retry()` (134 LOC) → `client.py`

---

#### File 3: raglite/external_data/clients/ice_futures.py (HIGH)
**LOC:** 707 → Target: 2 files × <370 LOC

**Proposed structure:**
```
raglite/external_data/clients/ice_futures/
├── __init__.py
├── client.py            # API client (~360 LOC)
└── parser.py            # Data parsing (~345 LOC)
```

---

### Batch 3.2: Medium Clients (PARALLEL - 2 files)

#### File 1: raglite/external_data/models.py (MEDIUM)
**LOC:** 666 → Target: 3 files × <250 LOC

**Proposed structure:**
```
raglite/external_data/models/
├── __init__.py
├── base.py              # Base models (~220 LOC)
├── clients.py           # Client models (~220 LOC)
└── timeseries.py        # Timeseries models (~220 LOC)
```

---

#### File 2: raglite/external_data/clients/commodities.py (MEDIUM)
**LOC:** 607 → Target: 2 files × <320 LOC

**Proposed structure:**
```
raglite/external_data/clients/commodities/
├── __init__.py
├── client.py            # API client (~310 LOC)
└── parser.py            # Data parsing (~295 LOC)
```

---

### Batch 3.3: Small Clients (PARALLEL - 1 file)

#### File 1: raglite/external_data/clients/eu_oil_bulletin.py (LOW)
**LOC:** 536 → Target: 2 files × <280 LOC

**Proposed structure:**
```
raglite/external_data/clients/eu_oil_bulletin/
├── __init__.py
├── client.py            # API client (~270 LOC)
└── xlsx_parser.py       # XLSX parsing (~265 LOC)
```

**Functions to extract:**
- `_parse_xlsx()` (186 LOC) → `xlsx_parser.py`

---

**Phase 3 Execution:** All 6 files can run in parallel (6 agents simultaneously)

**Total Phase 3 Duration:** 3-5 days

---

## Phase 4: Support Modules (INDEPENDENT)
**Duration:** 2-3 days | **Parallelization:** FULL | **Risk:** LOW

### Batch 4.1: Agentic Orchestration (PARALLEL - 3 files)

#### File 1: raglite/agentic/orchestrator.py (HIGH)
**LOC:** 705 → Target: 2 files × <370 LOC

**Proposed structure:**
```
raglite/agentic/orchestrator/
├── __init__.py
├── core.py              # Orchestration logic (~360 LOC)
└── execution.py         # Task execution (~340 LOC)
```

**Functions to extract:**
- `_execute_task()` (131 LOC) → `execution.py`
- `execute_workflow()` (119 LOC) → `execution.py`

---

#### File 2: raglite/agentic/fallback.py (MEDIUM)
**LOC:** 686 → Target: 2 files × <360 LOC

**Proposed structure:**
```
raglite/agentic/fallback/
├── __init__.py
├── handlers.py          # Fallback handlers (~350 LOC)
└── recovery.py          # Recovery logic (~335 LOC)
```

**Functions to extract:**
- `handle_workflow_failure()` (114 LOC) → `handlers.py`

---

#### File 3: raglite/agentic/planner.py (LOW)
**LOC:** 543 → Target: 2 files × <290 LOC

**Proposed structure:**
```
raglite/agentic/planner/
├── __init__.py
├── decomposition.py     # Query decomposition (~280 LOC)
└── classification.py    # Complexity classification (~260 LOC)
```

**Functions to extract:**
- `decompose_query()` (302 LOC) → `decomposition.py`
- `classify_query_complexity()` (139 LOC) → `classification.py`

---

### Batch 4.2: Insights (PARALLEL - 1 file)

#### File 1: raglite/insights/proactive.py (LOW)
**LOC:** 503 → Target: 2 files × <270 LOC

**Proposed structure:**
```
raglite/insights/proactive/
├── __init__.py
├── generation.py        # Insight generation (~260 LOC)
└── synthesis.py         # Insight synthesis (~240 LOC)
```

**Functions to extract:**
- `generate_insights()` (212 LOC) → `generation.py`
- `synthesize_insight()` (119 LOC) → `synthesis.py`

---

**Phase 4 Execution:** All 4 files can run in parallel (4 agents simultaneously)

**Total Phase 4 Duration:** 2-3 days

---

## Phase 5: Test Infrastructure (AFTER PRODUCTION STABLE)
**Duration:** 4-6 days | **Parallelization:** MEDIUM | **Risk:** MEDIUM

### Objective
Refactor test files AFTER production code is stable (tests won't need constant updates).

### Batch 5.1: Large Test Files (SERIAL - 10 files)
**Shared fixtures:** Many tests share fixtures from `tests/fixtures/`

**Top 10 test files to refactor:**

| File | LOC | Target | Strategy |
|------|-----|--------|----------|
| `tests/integration/test_model_selection.py` | 855 | Split by test scenario | 3 files × <300 LOC |
| `tests/integration/test_story_6_23_final_validation.py` | 837 | Split by story AC | 2 files × <450 LOC |
| `tests/validation/test_recommendation_alignment.py` | 825 | Split by validation type | 2 files × <450 LOC |
| `tests/fixtures/ground_truth.py` | 802 | Split by domain | 3 files × <280 LOC |
| `tests/integration/test_epic3_p0_scenarios.py` | 780 | Split by epic scenario | 2 files × <400 LOC |
| `tests/fixtures/ground_truth_old_backup.py` | 762 | Archive or split | TBD |
| `tests/validation/test_insight_quality.py` | 738 | Split by insight type | 2 files × <380 LOC |
| `tests/integration/test_catboost_adaptive_weights.py` | 732 | Split by weight type | 2 files × <380 LOC |
| `tests/validation/test_epic4_e2e_validation.py` | 728 | Split by epic AC | 2 files × <380 LOC |
| `tests/integration/test_ecb_macroeconomic_integration.py` | 698 | Split by integration area | 2 files × <360 LOC |

**Strategy:**
- Tests share fixtures → must refactor serially to avoid conflicts
- Split tests by behavior/scenario, not arbitrarily
- Maintain pytest discovery (keep `test_` prefix)

---

### Batch 5.2: Medium Test Files (PARALLEL - 16 files)
**Files 500-700 LOC:** Can split independently

**Execution:** 16 files split into 4 parallel batches of 4 files each

**Total Phase 5 Duration:** 4-6 days

---

## Phase 6: Function-Only Violations (GRADUAL)
**Duration:** 6-10 days | **Parallelization:** MEDIUM | **Risk:** LOW

### Objective
Reduce 126 function violations where file size is compliant but individual functions are too long.

### Strategy
**Co-locate with file refactoring:** Many function violations are in files we're already refactoring in Phases 0-4. Extract functions during file splits.

### Batch 6.1: Monster Functions (CRITICAL - 15 functions >200 LOC)
**Priority:** Extract during parent file refactoring

| Function | File | LOC | Phase Addressed |
|----------|------|-----|-----------------|
| `extract_timeseries_from_sql` | `sql_extraction.py` | 1,322 | Phase 2.1 (Batch 2.1) |
| `generate_forecast` | `hybrid/ensemble.py` | 659 | Phase 2.1 (Batch 2.1) |
| `get_financial_forecast` | `mcp/tools/forecast.py` | 456 | Phase 6.1 (standalone) |
| `generate_ensemble_forecast` | `ensemble.py` | 452 | Phase 2.3 (Batch 2.3) |
| `_extract_transposed_entity_cols_metric_row_labels` | `standard_layouts.py` | 433 | Phase 1.2 (Batch 1.2) |
| `extract_metric_from_qdrant_chunks` | `qdrant_metric.py` | 416 | Phase 6.1 (standalone) |
| `chunk_by_docling_items` | `chunking_strategy.py` | 360 | Phase 1.2 (Batch 1.2) |
| `fetch_single_regressor` | `regressor_fetch.py` | 351 | Phase 2.4 (Batch 2.4) |
| `ingest_pdf` | `pdf_processing.py` | 334 | Phase 6.1 (standalone) |
| `extract_fallback` | `adaptive_table/core/fallback.py` | 318 | Phase 6.1 (standalone) |
| `decompose_query` | `agentic/planner.py` | 302 | Phase 4.1 (Batch 4.1) |
| `generate_sql_query` | `query_classifier.py` | 298 | Phase 1.1 (Batch 1.1) |
| `extract_ebitda_from_qdrant_chunks` | `qdrant_ebitda.py` | 291 | Phase 6.1 (standalone) |
| `session_ingested_collection` | `session_fixtures.py` | 275 | Phase 5 (test refactor) |
| `hybrid_search` | `retrieval/search.py` | 269 | Phase 1.1 (Batch 1.1) |

**Standalone files to refactor in Phase 6.1:**
- `raglite/mcp/tools/forecast.py` (484 LOC) - Near threshold, has 456 LOC function
- `raglite/forecasting/timeseries/qdrant_metric.py` - Extract 416 LOC function
- `raglite/ingestion/document_ingestion/pdf_processing.py` - Extract 334 LOC function
- `raglite/ingestion/adaptive_table/core/fallback.py` - Extract 318 LOC function
- `raglite/forecasting/timeseries/qdrant_ebitda.py` - Extract 291 LOC function

---

### Batch 6.2: Large Functions (25 functions 150-200 LOC)
**Priority:** Extract as encountered during file refactoring

**Strategy:** Handle during parent file refactoring phases

---

### Batch 6.3: Medium Functions (28 functions 120-150 LOC)
**Priority:** Gradual reduction, opportunistic refactoring

**Strategy:** Address when modifying files for other reasons

---

### Batch 6.4: Small Functions (58 functions 100-120 LOC)
**Priority:** LOW - These are close to threshold

**Strategy:** Leave as-is unless modifying for other reasons

---

**Phase 6 Execution:**
- Weeks 1-2: Standalone monster functions (5 files)
- Weeks 3-4: Large functions as part of other refactoring

**Total Phase 6 Duration:** 6-10 days (mostly parallel with other phases)

---

## Phase 7: Final Cleanup & Validation
**Duration:** 2-3 days | **Parallelization:** NONE | **Risk:** LOW

### Objective
Verify all refactoring complete, remove exception files, validate quality gates.

### Tasks
1. **Re-run quality checks:** Verify 0 violations
2. **Remove exception files:**
   - Archive `.file-size-exceptions` to `docs/analysis/`
   - Archive `.function-length-exceptions` to `docs/analysis/`
3. **Full test suite:** Run all 372 tests
4. **NFR validation:**
   - NFR6: Retrieval accuracy ≥90%
   - NFR7: Source attribution ≥95%
   - NFR13: Query response <5s p50
5. **Coverage validation:** Maintain ≥80% coverage
6. **Documentation update:**
   - Update `CLAUDE.md` with new module structure
   - Update architecture docs with new file organization
7. **Create Epic 8 completion report**

---

## Execution Timeline Summary

| Phase | Duration | Parallelization | Files | Functions | Risk |
|-------|----------|-----------------|-------|-----------|------|
| **Phase 0** | 3-5 days | NONE (sequential) | 2 | N/A | 🔴 CRITICAL |
| **Phase 1** | 4-6 days | SERIAL (shared tests) | 7 | 15+ | 🟠 HIGH |
| **Phase 2** | 6-10 days | HIGH (5-6 agents) | 15 | 30+ | 🟡 MEDIUM |
| **Phase 3** | 3-5 days | FULL (6 agents) | 6 | 10+ | 🟢 LOW |
| **Phase 4** | 2-3 days | FULL (4 agents) | 4 | 8+ | 🟢 LOW |
| **Phase 5** | 4-6 days | MEDIUM (4 agents) | 26 | N/A | 🟡 MEDIUM |
| **Phase 6** | 6-10 days | MEDIUM (co-located) | 5 | 126 | 🟢 LOW |
| **Phase 7** | 2-3 days | NONE (validation) | N/A | N/A | 🟢 LOW |

**Total Duration:** 30-48 days (6-10 weeks)

**With optimal parallelization:** 20-30 days (4-6 weeks)

---

## Critical Path Analysis

### Blocking Dependencies
```
Phase 0 (Foundation)
├─ BLOCKS → Phase 1 (retrieval/search.py uses shared/models.py)
└─ BLOCKS → Phase 2 (forecasting uses shared/models.py)

Phase 1.1 (Retrieval)
└─ BLOCKS → Phase 1.2 (ingestion uses retrieval for validation)

Phase 1-4 (Production Code)
└─ BLOCKS → Phase 5 (test refactoring after production stable)
```

### Parallel Opportunities
```
Phase 2: Up to 6 agents in parallel (Batches 2.2-2.5)
Phase 3: 6 agents in parallel (all external clients)
Phase 4: 4 agents in parallel (all independent)
Phase 5: 4 agents in parallel (test batches)
```

---

## Risk Mitigation

### High-Risk Refactorings
1. **`raglite/shared/models.py`** (51 files depend on it)
   - **Mitigation:** Facade pattern, phased migration, extensive testing
   - **Rollback:** Keep facade indefinitely if migration fails

2. **`raglite/retrieval/search.py`** (81 tests)
   - **Mitigation:** Incremental extraction, test after each function move
   - **Rollback:** Git revert if tests fail

3. **Test refactoring** (shared fixtures)
   - **Mitigation:** Serial execution, verify fixture imports
   - **Rollback:** Tests are less critical than production code

### Success Criteria Per Phase
- ✅ All tests pass (372 tests)
- ✅ Coverage ≥80% maintained
- ✅ NFR6/NFR7/NFR13 maintained
- ✅ Zero new violations introduced
- ✅ Gradual reduction in exception count

---

## Execution Commands

### For Each File Refactoring
```bash
# Use code_quality orchestrator for automated refactoring
/code_quality --fix --path=raglite/shared/

# Or use safe-refactor agent directly
claude agent safe-refactor "Refactor raglite/shared/models.py using TEST-SAFE workflow"
```

### For Parallel Batches
```bash
# Example: Phase 2 Batch 2.2 (2 files in parallel)
/parallelize --strategy=refactor --files="raglite/forecasting/hybrid/preprocessing.py,raglite/forecasting/hybrid/model_generators.py"
```

### Progress Tracking
```bash
# Check current status
python scripts/check_file_sizes.py --verbose
python scripts/check_function_lengths.py --verbose

# Generate exception baseline after each phase
python scripts/check_file_sizes.py --generate-baseline
```

---

## Appendix A: Complete File List by Phase

### Phase 0: Foundation (2 files)
1. `raglite/shared/models.py` (1,432 LOC)
2. `raglite/shared/clients.py` (509 LOC)

### Phase 1: Critical Path (7 files)
**Retrieval:**
3. `raglite/retrieval/search.py` (1,146 LOC)
4. `raglite/retrieval/query_classifier.py` (928 LOC)

**Ingestion:**
5. `raglite/ingestion/chunking_strategy.py` (826 LOC)
6. `raglite/ingestion/adaptive_table/classification.py` (853 LOC)
7. `raglite/ingestion/storage_operations.py` (711 LOC)
8. `raglite/ingestion/adaptive_table/standard_layouts.py` (635 LOC)
9. `raglite/ingestion/table_extraction.py` (517 LOC)

### Phase 2: Forecasting (15 files)
**Core:**
10. `raglite/forecasting/timeseries/sql_extraction.py` (1,398 LOC)
11. `raglite/forecasting/hybrid/ensemble.py` (884 LOC)
12. `raglite/forecasting/report_generator.py` (807 LOC)

**Hybrid:**
13. `raglite/forecasting/hybrid/preprocessing.py` (656 LOC)
14. `raglite/forecasting/hybrid/model_generators.py` (602 LOC)

**Model Selection:**
15. `raglite/forecasting/model_selection_job.py` (601 LOC)
16. `raglite/forecasting/regime_detection.py` (600 LOC)
17. `raglite/forecasting/ensemble.py` (583 LOC)

**Data Pipeline:**
18. `raglite/forecasting/regressor_fetch.py` (579 LOC)
19. `raglite/forecasting/data_quality/config.py` (578 LOC)
20. `raglite/forecasting/data_analyzer.py` (568 LOC)

**Config/Utils:**
21. `raglite/forecasting/regressor_config.py` (550 LOC)
22. `raglite/forecasting/model_selection_utils.py` (541 LOC)
23. `raglite/forecasting/model_selection.py` (533 LOC)
24. `raglite/forecasting/tft_training.py` (512 LOC)

### Phase 3: External Data (6 files)
25. `raglite/external_data/refresh.py` (969 LOC)
26. `raglite/external_data/clients/ine.py` (768 LOC)
27. `raglite/external_data/clients/ice_futures.py` (707 LOC)
28. `raglite/external_data/models.py` (666 LOC)
29. `raglite/external_data/clients/commodities.py` (607 LOC)
30. `raglite/external_data/clients/eu_oil_bulletin.py` (536 LOC)

### Phase 4: Support (4 files)
31. `raglite/agentic/orchestrator.py` (705 LOC)
32. `raglite/agentic/fallback.py` (686 LOC)
33. `raglite/agentic/planner.py` (543 LOC)
34. `raglite/insights/proactive.py` (503 LOC)

### Phase 5: Tests (26 files)
35-60. [26 test files 500-855 LOC]

### Phase 6: Function-Only (5 standalone files)
61. `raglite/mcp/tools/forecast.py` (484 LOC, 456 LOC function)
62. `raglite/forecasting/timeseries/qdrant_metric.py` (416 LOC function)
63. `raglite/ingestion/document_ingestion/pdf_processing.py` (334 LOC function)
64. `raglite/ingestion/adaptive_table/core/fallback.py` (318 LOC function)
65. `raglite/forecasting/timeseries/qdrant_ebitda.py` (291 LOC function)

**Plus 121 additional function violations addressed during file refactoring**

---

## Appendix B: Quality Gates Per Phase

### Phase 0 Quality Gates
- [ ] Zero test failures (243 tests for models.py)
- [ ] 100% backward compatibility via facade
- [ ] No circular dependencies
- [ ] Coverage ≥80%

### Phase 1 Quality Gates
- [ ] NFR6 accuracy ≥90%
- [ ] 81 retrieval tests pass
- [ ] Ingestion pipeline tests pass
- [ ] No performance regression

### Phase 2 Quality Gates
- [ ] Forecasting accuracy maintained
- [ ] Model selection tests pass
- [ ] Timeseries extraction validates

### Phase 3 Quality Gates
- [ ] External data refresh works
- [ ] Client tests pass
- [ ] Data validation maintained

### Phase 4 Quality Gates
- [ ] Agentic workflows function
- [ ] Insights generation works
- [ ] Orchestration tests pass

### Phase 5 Quality Gates
- [ ] All 372 tests pass
- [ ] Test discovery works
- [ ] Fixtures load correctly

### Phase 6 Quality Gates
- [ ] Monster functions <100 LOC
- [ ] No new violations
- [ ] Existing tests pass

### Phase 7 Quality Gates
- [ ] **ZERO violations remaining**
- [ ] Exception files archived
- [ ] All NFRs validated
- [ ] Documentation updated

---

**END OF PLAN**
