# File Size Refactoring Briefing

**Created:** 2025-12-10
**Updated:** 2025-12-10
**Purpose:** Comprehensive reference for BMAD refactoring stories
**Target:** Reduce ALL files to <500 LOC for optimal AI comprehension

---

## Executive Summary

| Category | Files | Total LOC | Target |
|----------|-------|-----------|--------|
| **Production (raglite/)** | 27 | ~24,000+ | All <500 LOC |
| **Tests (tests/)** | 44 | ~35,000+ | All <500 LOC |
| **TOTAL** | **71** | **~59,000+** | **All <500 LOC** |

**Estimated New Modules:** ~120-150 new files after complete refactoring

---

## Research-Backed Best Practices

### Why 500 LOC Limit?

| Source | Finding |
|--------|---------|
| Cursor Forum | ≤300-350 LOC optimal for AI parsing/refactoring |
| Augment Code Research | Beyond 500-800 LOC: more AI mistakes, partial edits |
| Uncle Bob / Clean Code | Average 20-50 LOC, most files <100 LOC |
| Token Economics | 500 LOC ≈ 5,000 tokens (single-prompt comprehension) |

### AI Impact of Large Files

- Chunking breaks global understanding
- Increased risk of inconsistent edits
- Partial context leads to missed side effects
- Slower AI response times

---

## Refactoring Best Practices (Research-Based)

### Core Principles

1. **Tests and Production Code Refactor TOGETHER**
   - When splitting `raglite/module.py`, simultaneously update `tests/test_module.py`
   - Same PR/commit keeps changes atomic and reviewable
   - Never leave tests pointing at old locations

2. **Work Incrementally, Not Big Bang**
   - Extract ONE module at a time
   - Run tests after EACH extraction
   - Each commit must keep tests green
   - If tests break, fix immediately before proceeding

3. **Preserve Import Compatibility (Shim Pattern)**
   ```python
   # old_module.py - Keep as shim temporarily
   from .new_package.new_module import Foo, bar
   __all__ = ["Foo", "bar"]  # Re-export for backward compatibility
   ```
   - Remove shims after all consumers updated
   - Tests validate both old and new imports work during transition

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

### Handling Circular Dependencies

When splitting exposes circular imports:

1. **Extract shared types to low-level module**
   ```
   raglite/
     core/types.py      # Shared interfaces, no dependencies
     service/user.py    # Imports from core.types
     service/billing.py # Imports from core.types, not user.py
   ```

2. **Use local imports as tactical fix**
   ```python
   def compute():
       from raglite.billing import calculate  # Local import breaks cycle
       return calculate()
   ```

3. **Keep `__init__.py` files thin** - avoid heavy imports that create cycles

### Test File Refactoring Strategy

| Test Type | Refactoring Approach |
|-----------|---------------------|
| Unit tests | Split by production module (1:1 mapping) |
| Integration tests | Split by scenario/workflow |
| Fixtures (conftest.py) | Extract to domain-specific fixture modules |
| Factory files | Split by model/entity type |

**Test Structure Mirror Pattern:**
```
raglite/forecasting/hybrid.py     → tests/unit/forecasting/test_hybrid.py
raglite/forecasting/prophet.py    → tests/unit/forecasting/test_prophet.py
raglite/forecasting/ensemble.py   → tests/unit/forecasting/test_ensemble.py
```

### Coverage Preservation

```bash
# Before refactoring - save baseline
pytest --cov=raglite --cov-report=html > coverage_baseline.txt

# After each extraction
pytest --cov=raglite --cov-report=term-missing

# Compare coverage
# Must be >= baseline (ideally equal)
```

**Key Rules:**
- Coverage must NOT drop during refactoring
- New modules should have coverage from moved tests
- Add tests for new public interfaces created during extraction

---

## Complete File Inventory

### Production Code (raglite/) - 27 Files

#### Tier 1: Critical (>1000 LOC) - 8 Files

| # | File | LOC | Related Tests | Suggested Split |
|---|------|-----|---------------|-----------------|
| 1 | `main.py` | 2,998 | `tests/integration/test_mcp_*.py` | `mcp/tools/`, `mcp/handlers.py`, `mcp/resources.py`, `mcp/prompts.py` |
| 2 | `forecasting/hybrid.py` | 2,804 | `tests/unit/test_hybrid_forecasting.py`, `tests/unit/test_ensemble_forecasting.py` | `models/prophet.py`, `models/xgboost.py`, `ensemble.py`, `evaluation.py` |
| 3 | `ingestion/document_ingestion.py` | 1,343 | `tests/unit/test_ingestion.py`, `tests/integration/test_ingestion_integration.py` | `processors/pdf.py`, `processors/excel.py`, `pipeline.py`, `metadata.py` |
| 4 | `forecasting/timeseries_extract.py` | 1,331 | `tests/unit/test_timeseries_extract.py` | `ts_parser.py`, `ts_validator.py`, `ts_transform.py` |
| 5 | `shared/models.py` | 1,220 | Multiple test files | `models/document.py`, `models/query.py`, `models/response.py`, `models/forecast.py` |
| 6 | `ingestion/adaptive_table/unit_inference.py` | 1,205 | `tests/unit/test_unit_inference.py` | `unit_patterns.py`, `unit_conversion.py`, `unit_validation.py` |
| 7 | `retrieval/search.py` | 1,146 | `tests/unit/test_retrieval.py`, `tests/integration/test_retrieval_integration.py` | `vector_search.py`, `hybrid_search.py`, `reranking.py` |
| 8 | `external_data/clients/basegov.py` | 1,066 | `tests/unit/test_external_data_clients.py` | `basegov/scraper.py`, `basegov/parser.py`, `basegov/models.py` |

#### Tier 2: High Priority (700-1000 LOC) - 8 Files

| # | File | LOC | Related Tests | Suggested Split |
|---|------|-----|---------------|-----------------|
| 9 | `external_data/refresh.py` | 969 | `tests/unit/test_auto_update.py`, `tests/integration/test_scheduler_integration.py` | `refresh/scheduler.py`, `refresh/executor.py`, `refresh/status.py` |
| 10 | `external_data/storage.py` | 959 | `tests/integration/test_external_data_integration.py` | `storage/postgres.py`, `storage/cache.py`, `storage/queries.py` |
| 11 | `retrieval/query_classifier.py` | 928 | `tests/unit/test_query_intelligence.py` | `classifier/rules.py`, `classifier/ml.py`, `classifier/routing.py` |
| 12 | `ingestion/adaptive_table/core.py` | 903 | `tests/unit/test_table_extraction.py` | `table_detector.py`, `table_parser.py`, `table_validator.py` |
| 13 | `ingestion/adaptive_table/classification.py` | 853 | `tests/unit/test_table_extraction.py` | `layout_classifier.py`, `header_detector.py`, `structure_analyzer.py` |
| 14 | `external_data/clients/ine.py` | 767 | `tests/unit/test_external_data_clients.py` | `ine/api.py`, `ine/parser.py`, `ine/datasets.py` |
| 15 | `external_data/clients/ice_futures.py` | 707 | `tests/unit/test_external_data_clients.py` | `ice/api.py`, `ice/parser.py` |
| 16 | `agentic/orchestrator.py` | 705 | `tests/integration/test_workflow_orchestration.py` | `orchestrator/planner.py`, `orchestrator/executor.py`, `orchestrator/router.py` |

#### Tier 3: Medium Priority (500-700 LOC) - 11 Files

| # | File | LOC | Related Tests | Suggested Split |
|---|------|-----|---------------|-----------------|
| 17 | `ingestion/storage_operations.py` | 687 | `tests/integration/test_ingestion_integration.py` | `storage/qdrant_ops.py`, `storage/postgres_ops.py` |
| 18 | `agentic/fallback.py` | 686 | `tests/integration/test_graceful_degradation_story_3_7.py` | `fallback/strategies.py`, `fallback/recovery.py` |
| 19 | `ingestion/adaptive_table/standard_layouts.py` | 635 | `tests/unit/test_standard_layouts.py` | `layouts/income_statement.py`, `layouts/balance_sheet.py`, `layouts/cash_flow.py` |
| 20 | `ingestion/chunking_strategy.py` | 626 | `tests/integration/test_fixed_chunking.py` | `chunking/fixed.py`, `chunking/semantic.py`, `chunking/table.py` |
| 21 | `external_data/clients/commodities.py` | 594 | `tests/unit/test_external_data_clients.py` | `commodities/coal.py`, `commodities/petcoke.py`, `commodities/co2.py` |
| 22 | `agentic/planner.py` | 539 | `tests/integration/test_agentic_workflow_suite.py` | `planner/analyzer.py`, `planner/strategy.py` |
| 23 | `external_data/clients/eu_oil_bulletin.py` | 536 | `tests/unit/test_external_data_clients.py` | `oil_bulletin/scraper.py`, `oil_bulletin/parser.py` |
| 24 | `ingestion/table_extraction.py` | 517 | `tests/unit/test_table_extraction.py` | `extraction/docling.py`, `extraction/fallback.py` |
| 25 | `insights/proactive.py` | 503 | `tests/unit/test_proactive_insights.py`, `tests/integration/test_proactive_insights_integration.py` | `proactive/detector.py`, `proactive/generator.py` |
| 26 | `external_data/clients/bpstat.py` | 495 | `tests/unit/test_external_data_clients.py` | Near limit - monitor only |
| 27 | `retrieval/multi_index_search.py` | 487 | `tests/unit/test_hybrid_search.py` | Near limit - monitor only |

---

### Test Files (tests/) - 44 Files

#### Tier 1: Critical Test Files (>1000 LOC) - 8 Files

| # | File | LOC | Tests For | Suggested Split |
|---|------|-----|-----------|-----------------|
| 1 | `unit/test_external_data_clients.py` | 3,025 | All external clients | Split by client: `test_ine.py`, `test_basegov.py`, `test_ice.py`, `test_commodities.py`, `test_bpstat.py`, `test_oil_bulletin.py` |
| 2 | `unit/test_ingestion.py` | 1,785 | Document ingestion | Split by processor: `test_pdf_processor.py`, `test_excel_processor.py`, `test_pipeline.py` |
| 3 | `integration/conftest.py` | 1,411 | Integration fixtures | Extract to: `fixtures/database.py`, `fixtures/mcp.py`, `fixtures/documents.py` |
| 4 | `integration/test_forecast_query_integration.py` | 1,224 | Forecast queries | Split by scenario: `test_forecast_basic.py`, `test_forecast_hybrid.py`, `test_forecast_accuracy.py` |
| 5 | `integration/test_ingestion_integration.py` | 1,197 | Ingestion pipeline | Split by stage: `test_ingestion_pdf.py`, `test_ingestion_excel.py`, `test_ingestion_storage.py` |
| 6 | `unit/test_proactive_insights.py` | 1,128 | Proactive insights | Split by type: `test_trend_detection.py`, `test_anomaly_alerts.py`, `test_insight_generation.py` |
| 7 | `unit/test_timeseries_extract.py` | 1,056 | Timeseries extraction | Split by function: `test_ts_parsing.py`, `test_ts_validation.py`, `test_ts_transform.py` |
| 8 | `unit/test_trend_analysis.py` | 1,053 | Trend analysis | Split by trend type: `test_linear_trends.py`, `test_seasonal_trends.py`, `test_correlation.py` |

#### Tier 2: High Priority Test Files (700-1000 LOC) - 12 Files

| # | File | LOC | Tests For | Suggested Split |
|---|------|-----|-----------|-----------------|
| 9 | `unit/test_strategic_recommendations.py` | 949 | Strategic recs | Split by domain: `test_cost_recs.py`, `test_efficiency_recs.py`, `test_risk_recs.py` |
| 10 | `unit/test_table_extraction.py` | 921 | Table extraction | Split by table type: `test_income_tables.py`, `test_balance_tables.py`, `test_cashflow_tables.py` |
| 11 | `unit/test_forecast_query_tool.py` | 864 | Forecast MCP tool | Split by query type: `test_forecast_queries.py`, `test_historical_queries.py` |
| 12 | `unit/test_parallel_ingestion.py` | 858 | Parallel processing | Split by concern: `test_parallel_pdf.py`, `test_parallel_coordination.py` |
| 13 | `conftest.py` (root) | 844 | Shared fixtures | Extract to: `fixtures/mocks.py`, `fixtures/data.py`, `fixtures/config.py` |
| 14 | `validation/test_recommendation_alignment.py` | 825 | Recommendation QA | Split by validation: `test_rec_accuracy.py`, `test_rec_relevance.py` |
| 15 | `unit/test_anomaly_detection.py` | 811 | Anomaly detection | Split by type: `test_statistical_anomalies.py`, `test_threshold_anomalies.py` |
| 16 | `fixtures/ground_truth.py` | 802 | Ground truth data | Extract by domain: `ground_truth_forecasts.py`, `ground_truth_retrieval.py` |
| 17 | `integration/test_epic3_p0_scenarios.py` | 780 | Epic 3 validation | Split by scenario |
| 18 | `fixtures/ground_truth_old_backup.py` | 762 | Legacy ground truth | Consider deletion or archive |
| 19 | `validation/test_insight_quality.py` | 738 | Insight QA | Split by metric |
| 20 | `validation/test_epic4_e2e_validation.py` | 728 | Epic 4 validation | Split by scenario |

#### Tier 3: Medium Priority Test Files (500-700 LOC) - 24 Files

| # | File | LOC | Tests For | Suggested Split |
|---|------|-----|-----------|-----------------|
| 21 | `validation/test_forecast_accuracy.py` | 662 | Forecast QA | Split by metric |
| 22 | `unit/test_retrieval.py` | 653 | Retrieval search | Split: `test_vector_search.py`, `test_reranking.py` |
| 23 | `integration/test_fixed_chunking.py` | 647 | Chunking | Split by chunk type |
| 24 | `integration/test_metadata_injection.py` | 637 | Metadata | Keep or minor split |
| 25 | `integration/test_epic6_accuracy_regression.py` | 634 | Epic 6 QA | Keep as cohesive |
| 26 | `integration/test_analytical_query_tool.py` | 633 | Analytics | Split by query type |
| 27 | `unit/test_safety_guard.py` | 624 | Safety utils | Keep as cohesive |
| 28 | `integration/test_external_data_integration.py` | 606 | External data | Split by source |
| 29 | `integration/test_proactive_insights_integration.py` | 605 | Insights e2e | Split by insight type |
| 30 | `health/test_external_data_health.py` | 587 | Health checks | Keep as cohesive |
| 31 | `unit/test_auto_update.py` | 568 | Auto updates | Keep or minor split |
| 32 | `integration/test_story_2_14_excerpt_validation.py` | 563 | Story validation | Keep as cohesive |
| 33 | `unit/test_standard_layouts.py` | 560 | Table layouts | Split by layout type |
| 34 | `integration/test_strategic_recommendations_integration.py` | 557 | Recs e2e | Split by domain |
| 35 | `unit/test_phase2_centralized_validation.py` | 554 | Phase 2 QA | Keep as cohesive |
| 36 | `unit/test_hybrid_search.py` | 553 | Hybrid search | Keep or minor split |
| 37 | `unit/test_proactive_insights_mcp.py` | 551 | Insights MCP | Keep as cohesive |
| 38 | `unit/test_unit_inference.py` | 550 | Unit inference | Keep as cohesive |
| 39 | `integration/test_retrieval_integration.py` | 549 | Retrieval e2e | Split by scenario |
| 40 | `support/factories.py` | 544 | Test factories | Split by model type |
| 41 | `unit/test_scripts_accuracy_utils.py` | 533 | Script utils | Keep as cohesive |
| 42 | `unit/test_synthesis_agent.py` | 518 | Synthesis agent | Keep or minor split |
| 43 | `integration/test_workflow_orchestration.py` | 516 | Workflow e2e | Split by workflow |
| 44 | `unit/test_base64_ingestion.py` | 510 | Base64 input | Keep as cohesive |

---

## Module-by-Module Analysis

### Production: Core (`main.py`) - 2,998 LOC

**Current Responsibilities:**
- MCP server initialization
- Tool definitions (@mcp.tool decorators)
- Request handlers
- Resource management
- Prompt templates

**Related Test Files:**
- `tests/integration/test_mcp_response_validation.py` (426 LOC)
- `tests/integration/test_e2e_query_validation.py` (472 LOC)
- Various tool-specific integration tests

**Refactoring Strategy:**
```
raglite/
├── main.py              # Entry point only (~300 LOC)
└── mcp/
    ├── __init__.py      # Re-exports for backward compat
    ├── tools/
    │   ├── __init__.py
    │   ├── query.py     # query_financial_documents tool
    │   ├── ingest.py    # ingest_financial_document tool
    │   ├── forecast.py  # forecast tools
    │   └── external.py  # external data tools
    ├── handlers.py      # Request processing (~400 LOC)
    ├── resources.py     # Resource management (~300 LOC)
    └── prompts.py       # Prompt templates (~200 LOC)
```

**Test Refactoring:**
- Keep integration tests at same level
- Update imports from `raglite.main` to `raglite.mcp.tools.X`
- Add shim in `main.py` for backward compatibility during transition

**Dependencies to Consider:**
- FastMCP initialization must stay in main.py
- Tool decorators need access to shared state
- Circular import risk with handlers

**Estimated Effort:** 2 days (production) + 0.5 days (test updates)

---

### Production: Forecasting (`hybrid.py`) - 2,804 LOC

**Current Responsibilities:**
- Prophet model implementation
- XGBoost model implementation
- Ensemble combination logic
- Accuracy evaluation
- Model selection

**Related Test Files:**
- `tests/unit/test_hybrid_forecasting.py` (474 LOC)
- `tests/unit/test_ensemble_forecasting.py` (483 LOC)
- `tests/integration/test_forecast_query_integration.py` (1,224 LOC) - SPLIT NEEDED

**Refactoring Strategy:**
```
raglite/forecasting/
├── hybrid.py           # Orchestration only (~400 LOC)
├── models/
│   ├── __init__.py
│   ├── prophet.py      # Prophet-specific (~500 LOC)
│   ├── xgboost.py      # XGBoost-specific (~400 LOC)
│   └── base.py         # Common interface (~100 LOC)
├── ensemble.py         # Model combination (~300 LOC)
└── evaluation.py       # Accuracy metrics (~300 LOC)

tests/unit/forecasting/
├── test_hybrid.py          # Orchestration tests
├── test_prophet.py         # Prophet unit tests
├── test_xgboost.py         # XGBoost unit tests
├── test_ensemble.py        # Ensemble tests
└── test_evaluation.py      # Metric tests

tests/integration/forecasting/
├── test_forecast_basic.py
├── test_forecast_hybrid.py
└── test_forecast_accuracy.py
```

**Estimated Effort:** 2 days (production) + 1 day (test reorganization)

---

### Production: Ingestion (`document_ingestion.py`) - 1,343 LOC

**Current Responsibilities:**
- PDF processing via Docling
- Excel processing via openpyxl
- Metadata extraction
- Pipeline orchestration

**Related Test Files:**
- `tests/unit/test_ingestion.py` (1,785 LOC) - MUST SPLIT
- `tests/integration/test_ingestion_integration.py` (1,197 LOC) - MUST SPLIT

**Refactoring Strategy:**
```
raglite/ingestion/
├── document_ingestion.py  # Orchestration (~300 LOC)
├── processors/
│   ├── __init__.py
│   ├── pdf.py            # Docling integration (~400 LOC)
│   ├── excel.py          # openpyxl integration (~300 LOC)
│   └── base.py           # Common interface (~100 LOC)
└── metadata.py           # Metadata extraction (~200 LOC)

tests/unit/ingestion/
├── test_pipeline.py        # Orchestration tests
├── test_pdf_processor.py   # PDF tests
├── test_excel_processor.py # Excel tests
└── test_metadata.py        # Metadata tests

tests/integration/ingestion/
├── test_pdf_ingestion.py
├── test_excel_ingestion.py
└── test_storage_integration.py
```

**Estimated Effort:** 1.5 days (production) + 1.5 days (test reorganization)

---

### Test: External Data Clients (`test_external_data_clients.py`) - 3,025 LOC

**LARGEST FILE IN CODEBASE** - Must be split first to enable production refactoring

**Current Tests Cover:**
- INE client
- BaseGov client
- ICE Futures client
- Commodities clients
- BPStat client
- EU Oil Bulletin client

**Refactoring Strategy:**
```
tests/unit/external_data/
├── __init__.py
├── test_ine_client.py          # ~500 LOC
├── test_basegov_client.py      # ~500 LOC
├── test_ice_futures_client.py  # ~350 LOC
├── test_commodities_client.py  # ~350 LOC
├── test_bpstat_client.py       # ~350 LOC
├── test_oil_bulletin_client.py # ~350 LOC
└── conftest.py                 # Shared fixtures (~150 LOC)
```

**Dependencies:**
- Shared mocking patterns for HTTP requests
- Common fixture data for API responses
- Mock client factories

**Estimated Effort:** 1.5 days

---

### Test: Fixtures (`conftest.py` files) - 2,255 LOC combined

**Problem:** Large conftest files make fixture discovery hard

**Files:**
- `tests/conftest.py` (844 LOC)
- `tests/integration/conftest.py` (1,411 LOC)

**Refactoring Strategy:**
```
tests/
├── conftest.py              # Minimal, imports from fixtures/
└── fixtures/
    ├── __init__.py          # Exports all fixtures
    ├── database.py          # Qdrant, PostgreSQL fixtures
    ├── mcp.py               # MCP server fixtures
    ├── documents.py         # Sample document fixtures
    ├── mocks.py             # Mock clients, responses
    └── config.py            # Test configuration fixtures

tests/integration/
├── conftest.py              # Minimal, imports from fixtures/
└── fixtures/
    ├── __init__.py
    ├── services.py          # Running service fixtures
    └── scenarios.py         # E2E scenario fixtures
```

**Estimated Effort:** 1 day

---

## Acceptance Criteria Template

For each refactoring story, use these standard ACs:

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

## Priority Matrix (Complete)

### Production Code Priority

| Priority | Criteria | Files | Est. Production | Est. Tests | Total |
|----------|----------|-------|-----------------|------------|-------|
| **P0** | >2000 LOC | main.py, hybrid.py | 4 days | 2 days | 6 days |
| **P1** | >1000 LOC | 6 files | 9 days | 4.5 days | 13.5 days |
| **P2** | 700-1000 LOC | 8 files | 12 days | 6 days | 18 days |
| **P3** | 500-700 LOC | 11 files | 11 days | 5.5 days | 16.5 days |
| **Total Prod** | | **27 files** | **36 days** | **18 days** | **54 days** |

### Test Code Priority

| Priority | Criteria | Files | Est. Effort |
|----------|----------|-------|-------------|
| **T0** | >1000 LOC, blocks prod refactoring | 8 files | 12 days |
| **T1** | 700-1000 LOC | 12 files | 12 days |
| **T2** | 500-700 LOC | 24 files | 12 days |
| **Total Test** | | **44 files** | **36 days** |

### Combined Effort

| Phase | Focus | Estimated Effort |
|-------|-------|------------------|
| Phase 1 | P0 production + T0 tests | 18 days |
| Phase 2 | P1 production + related tests | 13.5 days |
| Phase 3 | P2 production + T1 tests | 30 days |
| Phase 4 | P3 production + T2 tests | 28.5 days |
| **TOTAL** | All 71 files | **~90 days** |

*Note: Can be parallelized - actual calendar time ~30-45 days with 2-3 parallel streams*

---

## Recommended Refactoring Order

### Batch 1: Enable Other Refactoring (Week 1-2)

**Do these FIRST** - they unblock other work:

1. `tests/unit/test_external_data_clients.py` (3,025 LOC) - Unblocks external client refactoring
2. `tests/conftest.py` + `tests/integration/conftest.py` (2,255 LOC) - Cleaner fixtures for all tests
3. `tests/fixtures/ground_truth.py` (802 LOC) - Shared test data

### Batch 2: Largest Production Files (Week 2-4)

4. `raglite/main.py` (2,998 LOC) + related tests
5. `raglite/forecasting/hybrid.py` (2,804 LOC) + `tests/integration/test_forecast_query_integration.py` (1,224 LOC)

### Batch 3: Ingestion Module (Week 4-5)

6. `raglite/ingestion/document_ingestion.py` (1,343 LOC) + `tests/unit/test_ingestion.py` (1,785 LOC)
7. `raglite/ingestion/adaptive_table/unit_inference.py` (1,205 LOC)
8. `raglite/ingestion/adaptive_table/core.py` (903 LOC)
9. `raglite/ingestion/adaptive_table/classification.py` (853 LOC)

### Batch 4: External Data Module (Week 5-7)

10. `raglite/external_data/clients/basegov.py` (1,066 LOC)
11. `raglite/external_data/refresh.py` (969 LOC)
12. `raglite/external_data/storage.py` (959 LOC)
13. `raglite/external_data/clients/ine.py` (767 LOC)
14. `raglite/external_data/clients/ice_futures.py` (707 LOC)

### Batch 5: Remaining Files (Week 7-10)

15-71. Remaining 57 files in priority order

---

## Story Template

```markdown
# Story X.Y: Refactor [filename] ([current LOC] → <500 LOC)

**Epic:** Epic 7 - Technical Debt & Code Quality
**Priority:** P[0-3] / T[0-2]
**Estimated Effort:** [N] days (production) + [M] days (tests)
**Status:** BACKLOG

---

## User Story

As a developer, I want [filename] to be under 500 LOC, so that AI assistants can comprehend the full file and provide better suggestions.

---

## Acceptance Criteria

### AC1: File Size Reduction
- `[filename]` reduced from [current] to <500 LOC
- All new modules <500 LOC each

### AC2: Test Alignment
- Related test files also <500 LOC each:
  - `[test_file_1]` reduced from [current] to <500 LOC
  - `[test_file_2]` (if applicable)
- Test structure mirrors production structure

### AC3: Functionality Preserved
- All existing tests pass unchanged
- No behavior changes
- Coverage >= baseline ([XX]%)

### AC4: Clean Architecture
- No circular dependencies
- Backward-compatible imports via shims
- Clear module responsibilities

---

## Technical Design

### Current Structure (Production)
[Describe current responsibilities]

### Target Structure (Production)
[Show new file layout]

### Current Structure (Tests)
[Describe current test organization]

### Target Structure (Tests)
[Show new test file layout]

---

## Refactoring Steps

1. [ ] Lock coverage baseline
2. [ ] Create new module structure (empty files)
3. [ ] Extract first cohesive group → run tests
4. [ ] Extract second cohesive group → run tests
5. [ ] ... repeat for each group
6. [ ] Add backward-compat shims
7. [ ] Update test imports
8. [ ] Split test file if needed
9. [ ] Verify coverage unchanged
10. [ ] Remove shims (follow-up PR or later story)

---

## Dev Notes
- Extract one module at a time, test after each
- Do NOT batch test updates - update alongside each production change
- Run full test suite, not just affected tests
```

---

## Commands for Analysis

```bash
# Check current file sizes
python scripts/check_file_sizes.py --verbose

# Find specific file's dependencies (who imports from it)
grep -r "from raglite.main import" raglite/

# Find what a file imports (its dependencies)
grep "^from raglite\|^import raglite" raglite/main.py

# Count functions in a file
grep -c "^def \|^async def " raglite/main.py

# Check test coverage for specific module
uv run pytest tests/ --cov=raglite/main --cov-report=term-missing

# Run tests for specific module only
uv run pytest tests/unit/test_ingestion.py -v

# Find test files related to a production file
grep -l "from raglite.main" tests/**/*.py

# List all files over 500 LOC
find . -name "*.py" -exec wc -l {} \; | awk '$1 > 500 {print}' | sort -rn

# Check for circular imports (will error if present)
python -c "import raglite.main"
```

---

## Progress Tracking

Track progress by monitoring `.file-size-exceptions`:

```bash
# Count current exceptions
cat .file-size-exceptions | jq '.exceptions | length'

# Count production code exceptions only
cat .file-size-exceptions | jq '.exceptions | to_entries | map(select(.key | startswith("raglite/"))) | length'

# Count test exceptions only
cat .file-size-exceptions | jq '.exceptions | to_entries | map(select(.key | startswith("tests/"))) | length'
```

**Current State:**
- Production exceptions: 27
- Test exceptions: 44
- Total: 71

**Goal:** Reduce ALL to 0 over time.

---

## Anti-Patterns to Avoid

### DON'T: Big Bang Refactoring
```
# WRONG: Move everything at once
git commit -m "Refactor entire module"  # 50 files changed, 10k lines
```

### DO: Incremental Extraction
```
# CORRECT: One module at a time
git commit -m "Extract prophet.py from hybrid.py"  # 2 files, 600 lines
git commit -m "Extract xgboost.py from hybrid.py"  # 2 files, 500 lines
```

### DON'T: Update Tests Later
```
# WRONG: Refactor production, defer test updates
git commit -m "Refactor forecasting module"
# ...later...
git commit -m "Fix all the broken tests"  # Pain!
```

### DO: Tests With Each Change
```
# CORRECT: Production + tests together
git commit -m "Extract prophet.py and update test_prophet.py"
```

### DON'T: Remove Old Imports Immediately
```python
# WRONG: Break all consumers at once
# old_module.py - deleted
```

### DO: Deprecate Then Remove
```python
# CORRECT: Shim with deprecation warning
# old_module.py
import warnings
from .new_package.new_module import Foo
warnings.warn("Import from new_package.new_module instead", DeprecationWarning)
```

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Files >500 LOC (prod) | 27 | 0 | `check_file_sizes.py` |
| Files >500 LOC (tests) | 44 | 0 | `check_file_sizes.py` |
| Test coverage | 82% | >=82% | `pytest --cov` |
| CI pass rate | - | 100% | GitHub Actions |
| New violations | 0 | 0 | CI enforced |

---

## Next Steps

1. **Enforcement infrastructure** - COMPLETED
2. Use this briefing to create individual BMAD stories as capacity allows
3. Start with Batch 1 (test files that unblock others)
4. Track progress via `.file-size-exceptions` count
5. Update this briefing as refactoring progresses

---

## Appendix: Shim Pattern Example

When splitting `raglite/main.py` into `raglite/mcp/tools/`:

```python
# raglite/main.py (after refactoring)
"""RAGLite MCP Server - Entry Point.

Note: Tools have been moved to raglite.mcp.tools.
Import from there for new code. Imports from main.py
are deprecated and will be removed in v2.0.
"""
import warnings

from raglite.mcp.server import create_mcp_server, run_server

# Backward compatibility - deprecated
def _deprecated_import(name: str):
    warnings.warn(
        f"Importing {name} from raglite.main is deprecated. "
        f"Import from raglite.mcp.tools instead.",
        DeprecationWarning,
        stacklevel=3
    )

# Re-export tools for backward compatibility
from raglite.mcp.tools.query import query_financial_documents
from raglite.mcp.tools.ingest import ingest_financial_document
# ... etc

# Main entry point
if __name__ == "__main__":
    run_server()
```

This pattern ensures:
1. Old imports continue to work (with warning)
2. Tests can be updated incrementally
3. Clear migration path for consumers
