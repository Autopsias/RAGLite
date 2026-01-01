# Dry-Run: raglite/shared/models.py Refactoring Plan
## Phase 0 - Foundation (CRITICAL BLOCKER)

**Generated:** 2026-01-01
**Current Size:** 1,432 LOC (40 Pydantic models)
**Target:** 8 domain files × <200 LOC each
**Impact:** 50 production files + 243 tests depend on this

---

## Executive Summary

### Current State Analysis

**File:** `raglite/shared/models.py` (1,432 LOC)
- **40 Pydantic models** (BaseModel classes)
- **4 Enums** (str-based)
- **ZERO internal dependencies** (no imports from other raglite modules)
- **High coupling:** Used across all modules (ingestion, retrieval, forecasting, insights)

### Dependency Impact

| Metric | Count | Impact |
|--------|-------|--------|
| **Production files** | 50 | HIGH - All modules depend on this |
| **Test files** | 243 | CRITICAL - Massive test surface |
| **Most imported model** | `TimeSeriesData` | 21 files |
| **Second most** | `DocumentMetadata` | 9 files |
| **Third most** | `QueryResult` | 8 files |

### Risk Assessment: 🔴 **CRITICAL**

**Why this is the blocker:**
1. **Foundation dependency:** All other modules import from this
2. **Test explosion:** 243 tests = highest test coupling in project
3. **Cross-module:** Used in ingestion, retrieval, forecasting, insights, MCP
4. **No internal deps:** Clean split is feasible (no circular dependency risk)

---

## Domain-Based Split Design

### Proposed Structure

```
raglite/shared/models/
├── __init__.py                    # Facade for backward compatibility (100 LOC)
├── base.py                        # Base classes & utilities (80 LOC)
├── document.py                    # Document & ingestion models (180 LOC)
├── chunk.py                       # Chunking models (120 LOC)
├── query.py                       # Query request/response models (200 LOC)
├── timeseries.py                  # Time series & forecast models (220 LOC)
├── insights.py                    # Insights, anomalies, trends (200 LOC)
├── external_data.py               # External data & regressor models (180 LOC)
└── validation.py                  # Validation models (150 LOC)
```

**Total:** 9 files (8 domain + 1 facade) × <220 LOC = 1,430 LOC (same as original)

---

## Detailed File Breakdown

### File 1: base.py (80 LOC)
**Purpose:** Shared base classes and utilities

**Classes:**
- (None - just imports and type aliases if needed)

**Content:**
- Pydantic imports
- Common type aliases
- Shared field validators (if any)

**Reason for separation:** Allows other domain files to import common utilities without circular deps

---

### File 2: document.py (180 LOC)
**Purpose:** Document metadata and ingestion results

**Classes:** (5 models)
1. `DocumentMetadata` (32 LOC)
2. `ExtractedMetadata` (70 LOC) - Story 2.4 rich schema
3. `BatchIngestionResult` (20 LOC)
4. `IngestionResult` (25 LOC)
5. `IngestionJobStatus` (15 LOC)

**Used by:**
- `raglite/ingestion/**` (primary)
- `raglite/mcp/tools/ingestion.py`
- Tests: ~60 test files

**Dependencies:** None (independent)

---

### File 3: chunk.py (120 LOC)
**Purpose:** Chunking and search result models

**Classes:** (3 models)
1. `Chunk` (50 LOC)
2. `SearchResult` (40 LOC)
3. `WorkflowMetrics` (25 LOC)

**Used by:**
- `raglite/ingestion/chunking_strategy.py`
- `raglite/retrieval/search.py`
- `raglite/agentic/**`
- Tests: ~40 test files

**Dependencies:** None (independent)

---

### File 4: query.py (200 LOC)
**Purpose:** Query request/response models for MCP tools

**Classes:** (6 models)
1. `QueryRequest` (25 LOC)
2. `QueryResponse` (30 LOC)
3. `QueryResult` (50 LOC)
4. `AnalyticalQueryRequest` (35 LOC)
5. `AnalyticalQueryResponse` (40 LOC)
6. `ValidationResponse` (20 LOC)

**Used by:**
- `raglite/mcp/tools/query.py` (primary)
- `raglite/retrieval/**`
- Tests: ~70 test files

**Dependencies:** May import `SearchResult` from `chunk.py`

---

### File 5: timeseries.py (220 LOC)
**Purpose:** Time series data and forecasting models

**Classes:** (10 models + 2 enums)
1. `TimeSeriesPoint` (20 LOC)
2. `TimeSeriesData` (40 LOC)
3. `ForecastPoint` (25 LOC)
4. `ForecastResult` (60 LOC)
5. `ForecastRefreshResult` (20 LOC)
6. `ForecastQueryRequest` (25 LOC)
7. `ForecastQueryResponse` (30 LOC)
8. `ModelPerformanceDetail` (15 LOC)
9. `VariableValidationDetail` (15 LOC)
10. `RegressorDataPoint` (15 LOC)

**Used by:**
- `raglite/forecasting/**` (21 files!)
- `raglite/mcp/tools/forecast.py`
- Tests: ~80 test files

**Dependencies:** None (independent)

---

### File 6: insights.py (200 LOC)
**Purpose:** Insights, anomalies, trends, recommendations

**Classes:** (10 models + 4 enums)
1. `AnomalySeverity` (Enum, 10 LOC)
2. `Anomaly` (25 LOC)
3. `AnomalyDetectionResult` (20 LOC)
4. `TrendDirection` (Enum, 10 LOC)
5. `Trend` (25 LOC)
6. `TrendAnalysisResult` (20 LOC)
7. `CorrelationResult` (20 LOC)
8. `InsightCategory` (Enum, 10 LOC)
9. `Insight` (30 LOC)
10. `InsightGenerationResult` (20 LOC)
11. `RecommendationCategory` (Enum, 10 LOC)
12. `Recommendation` (30 LOC)
13. `InsightsQueryRequest` (25 LOC)
14. `InsightsQueryResponse` (25 LOC)

**Used by:**
- `raglite/insights/**`
- `raglite/mcp/tools/insights.py`
- Tests: ~30 test files

**Dependencies:** May import `Trend`, `Anomaly` from self

---

### File 7: external_data.py (180 LOC)
**Purpose:** External data sources and regressor models

**Classes:** (4 models)
1. `RegressorInfo` (40 LOC)
2. `RegressorListResponse` (30 LOC)
3. `RegressorDataResponse` (50 LOC)
4. `AsyncIngestionRequest` (30 LOC)
5. `AsyncIngestionResponse` (30 LOC)

**Used by:**
- `raglite/external_data/**`
- `raglite/forecasting/regressor_fetch.py`
- Tests: ~20 test files

**Dependencies:** May import `TimeSeriesData` from `timeseries.py`

---

### File 8: validation.py (150 LOC)
**Purpose:** Validation and recommendation result models

**Classes:** (2 models)
1. `RecommendationResult` (70 LOC)
2. `ValidationResponse` (80 LOC) - If not already in query.py

**Used by:**
- `raglite/mcp/tools/validation.py`
- Tests: ~15 test files

**Dependencies:** May import `ForecastResult` from `timeseries.py`

---

### File 9: __init__.py (100 LOC - FACADE)
**Purpose:** Maintain 100% backward compatibility

**Strategy:** Re-export ALL models from domain files

```python
"""Pydantic data models for RAGLite.

This module maintains backward compatibility by re-exporting all models
from domain-specific submodules. Import from here as usual:

    from raglite.shared.models import DocumentMetadata, QueryResult

Internal architecture: Models are organized by domain in submodules
(document.py, query.py, timeseries.py, etc.) but all are available
via this __init__.py for compatibility.
"""

# Document & Ingestion
from raglite.shared.models.document import (
    BatchIngestionResult,
    DocumentMetadata,
    ExtractedMetadata,
    IngestionJobStatus,
    IngestionResult,
)

# Chunking & Search
from raglite.shared.models.chunk import (
    Chunk,
    SearchResult,
    WorkflowMetrics,
)

# Query Models
from raglite.shared.models.query import (
    AnalyticalQueryRequest,
    AnalyticalQueryResponse,
    QueryRequest,
    QueryResponse,
    QueryResult,
)

# Time Series & Forecasting
from raglite.shared.models.timeseries import (
    ForecastPoint,
    ForecastQueryRequest,
    ForecastQueryResponse,
    ForecastRefreshResult,
    ForecastResult,
    ModelPerformanceDetail,
    RegressorDataPoint,
    TimeSeriesData,
    TimeSeriesPoint,
    VariableValidationDetail,
)

# Insights, Anomalies, Trends
from raglite.shared.models.insights import (
    Anomaly,
    AnomalyDetectionResult,
    AnomalySeverity,
    CorrelationResult,
    Insight,
    InsightCategory,
    InsightGenerationResult,
    InsightsQueryRequest,
    InsightsQueryResponse,
    Recommendation,
    RecommendationCategory,
    Trend,
    TrendAnalysisResult,
    TrendDirection,
)

# External Data & Regressors
from raglite.shared.models.external_data import (
    AsyncIngestionRequest,
    AsyncIngestionResponse,
    RegressorDataResponse,
    RegressorInfo,
    RegressorListResponse,
)

# Validation
from raglite.shared.models.validation import (
    RecommendationResult,
    ValidationResponse,
)

# Re-export all for backward compatibility
__all__ = [
    # Document & Ingestion
    "DocumentMetadata",
    "ExtractedMetadata",
    "BatchIngestionResult",
    "IngestionResult",
    "IngestionJobStatus",
    # Chunking & Search
    "Chunk",
    "SearchResult",
    "WorkflowMetrics",
    # Query Models
    "QueryRequest",
    "QueryResponse",
    "QueryResult",
    "AnalyticalQueryRequest",
    "AnalyticalQueryResponse",
    # Time Series & Forecasting
    "TimeSeriesPoint",
    "TimeSeriesData",
    "ForecastPoint",
    "ForecastResult",
    "ForecastRefreshResult",
    "ForecastQueryRequest",
    "ForecastQueryResponse",
    "ModelPerformanceDetail",
    "VariableValidationDetail",
    "RegressorDataPoint",
    # Insights
    "AnomalySeverity",
    "Anomaly",
    "AnomalyDetectionResult",
    "TrendDirection",
    "Trend",
    "TrendAnalysisResult",
    "CorrelationResult",
    "InsightCategory",
    "Insight",
    "InsightGenerationResult",
    "RecommendationCategory",
    "Recommendation",
    "InsightsQueryRequest",
    "InsightsQueryResponse",
    # External Data
    "RegressorInfo",
    "RegressorListResponse",
    "RegressorDataResponse",
    "AsyncIngestionRequest",
    "AsyncIngestionResponse",
    # Validation
    "RecommendationResult",
    "ValidationResponse",
]
```

**Key Features:**
- ✅ All existing imports continue to work: `from raglite.shared.models import DocumentMetadata`
- ✅ No changes required to any of the 50 production files or 243 tests
- ✅ Enables gradual migration if desired (can update imports later)
- ✅ Clear documentation of internal organization

---

## Migration Strategy: ZERO-IMPACT FACADE

### Phase 1: Create Domain Files (NO BREAKING CHANGES)

**Steps:**
1. Create `raglite/shared/models/` directory
2. Create 8 domain files with model definitions
3. Copy models from original `models.py` to domain files
4. Add necessary imports to each domain file

**Result after Phase 1:**
- ✅ New structure exists
- ✅ Original `models.py` still in place (untouched)
- ✅ No breaking changes yet

---

### Phase 2: Create Facade (MAINTAIN COMPATIBILITY)

**Steps:**
1. Rename `raglite/shared/models.py` → `raglite/shared/models_BACKUP.py`
2. Create `raglite/shared/models/__init__.py` with re-exports (shown above)
3. Run full test suite (all 243 tests)

**Result after Phase 2:**
- ✅ All imports still work (`from raglite.shared.models import X`)
- ✅ Internal organization changed (9 files instead of 1)
- ✅ Zero code changes required in dependent files
- ✅ Backward compatibility = 100%

**Critical Test:** Run pytest to verify 243 tests still pass

---

### Phase 3: Validation (SAFETY CHECKPOINT)

**Steps:**
1. Run full test suite: `pytest tests/ -v`
2. Verify all 243 tests pass
3. Run NFR validation (accuracy, performance)
4. Check mypy type checking: `mypy raglite/ --strict`
5. Verify no circular imports: `python -c "from raglite.shared.models import *"`

**Success Criteria:**
- ✅ All 372 tests pass (not just 243 model tests)
- ✅ NFR6 accuracy ≥90%
- ✅ No mypy errors introduced
- ✅ No circular import errors
- ✅ Coverage ≥80% maintained

**If ANY test fails:**
- ❌ Revert: `git checkout raglite/shared/models.py && rm -rf raglite/shared/models/`
- ❌ Investigate failure
- ❌ Fix and retry

---

### Phase 4: Cleanup (OPTIONAL)

**Only after Phase 3 succeeds:**
1. Delete `raglite/shared/models_BACKUP.py`
2. Update `.file-size-exceptions` to remove `shared/models.py` entry
3. Commit changes

**Future Migration (OPTIONAL):**
- Gradually update imports to use domain-specific paths:
  - `from raglite.shared.models.document import DocumentMetadata`
  - Benefits: Clearer dependencies, faster imports
  - No urgency: Facade ensures backward compat indefinitely

---

## Test Impact Analysis

### Test Files Importing from models.py (243 total)

**By module:**
| Module | Test Count | Models Used |
|--------|-----------|-------------|
| **Forecasting tests** | ~80 | `TimeSeriesData`, `ForecastResult` |
| **Retrieval tests** | ~70 | `QueryResult`, `SearchResult` |
| **Ingestion tests** | ~60 | `DocumentMetadata`, `Chunk` |
| **Insights tests** | ~30 | `Anomaly`, `Trend`, `Insight` |
| **MCP tests** | ~25 | All query/response models |
| **External data tests** | ~20 | `RegressorInfo`, `RegressorDataResponse` |

**Critical test files to monitor:**
1. `tests/integration/test_ac3_ground_truth.py` (uses `QueryResult`, `DocumentMetadata`)
2. `tests/integration/test_model_selection.py` (uses `TimeSeriesData`, `ForecastResult`)
3. `tests/integration/test_retrieval_*.py` (uses `QueryResult`, `SearchResult`)
4. `tests/validation/test_recommendation_alignment.py` (uses `Recommendation`)

**Test Strategy:**
- Run full test suite BEFORE and AFTER migration
- Compare results: MUST be identical
- Zero tolerance for new failures

---

## Execution Commands

### Automated Refactoring (Recommended)

```bash
# Launch safe-refactor agent with this dry-run plan
Task(
    subagent_type="safe-refactor",
    description="Refactor shared/models.py to domain files",
    prompt="Execute raglite/shared/models.py refactoring using ZERO-IMPACT FACADE strategy:

    CONTEXT:
    - File: raglite/shared/models.py (1,432 LOC, 40 models)
    - Impact: 50 prod files + 243 tests depend on this
    - Strategy: Create 8 domain files + facade __init__.py
    - Goal: 100% backward compatibility, ZERO test failures

    DETAILED PLAN:
    Follow the plan in docs/analysis/models-py-refactoring-dryrun.md

    PHASE 1: Create Domain Files
    1. Create raglite/shared/models/ directory
    2. Create 8 domain files (document.py, chunk.py, query.py, timeseries.py, insights.py, external_data.py, validation.py, base.py)
    3. Move models from original models.py to domain files per categorization
    4. Add imports to each domain file

    PHASE 2: Create Facade
    1. Rename models.py to models_BACKUP.py
    2. Create __init__.py with re-exports of ALL models
    3. Run pytest to verify 243 tests pass

    PHASE 3: Validation
    1. Run full test suite: pytest tests/ -v
    2. Verify NFR6 accuracy maintained
    3. Check mypy: mypy raglite/ --strict
    4. If ANY failure -> REVERT and report

    CRITICAL RULES:
    - If tests fail at ANY phase, REVERT with: git checkout raglite/shared/models.py && rm -rf raglite/shared/models/
    - Use facade pattern to preserve public API
    - Never proceed with broken tests
    - All 243 tests MUST pass identically

    SUCCESS CRITERIA:
    - Zero test failures (all 243 tests pass)
    - 100% backward compatibility
    - No mypy errors
    - Coverage ≥80%
    - NFR6 accuracy ≥90%"
)
```

### Manual Execution (Step-by-Step)

```bash
# Step 1: Create domain files
mkdir -p raglite/shared/models

# Step 2: Create each domain file (manually or with script)
# ... create document.py, chunk.py, query.py, timeseries.py, insights.py, external_data.py, validation.py, base.py

# Step 3: Create facade __init__.py
# ... create __init__.py with re-exports

# Step 4: Backup original
mv raglite/shared/models.py raglite/shared/models_BACKUP.py

# Step 5: Run tests
pytest tests/ -v --tb=short

# Step 6: Verify
mypy raglite/ --strict
python -c "from raglite.shared.models import *; print('Import test: PASS')"

# Step 7: If all pass, cleanup
rm raglite/shared/models_BACKUP.py
```

---

## Risk Mitigation

### Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Test failures** | MEDIUM | HIGH | Facade pattern ensures imports work; revert if fails |
| **Circular imports** | LOW | HIGH | No internal deps = no circular risk; validate with import test |
| **Mypy errors** | LOW | MEDIUM | Domain files are simple Pydantic models; test with mypy |
| **Performance regression** | VERY LOW | LOW | Facade adds negligible overhead (just re-exports) |
| **Merge conflicts** | MEDIUM | MEDIUM | Do this refactoring in isolation; merge quickly |

### Rollback Plan

**If anything fails:**
```bash
# Instant rollback (< 5 seconds)
git checkout raglite/shared/models.py
rm -rf raglite/shared/models/
pytest tests/ -k "test_ac3_ground_truth"  # Verify rollback worked
```

**Rollback triggers:**
- ANY test failure (even 1 of 372)
- ANY mypy error introduced
- NFR6 accuracy drops below 90%
- Coverage drops below 80%
- Import errors on `from raglite.shared.models import *`

---

## Success Criteria Checklist

### Phase 1: Domain Files Created
- [ ] 8 domain files created in `raglite/shared/models/`
- [ ] All 40 models moved to appropriate domain files
- [ ] Each file <220 LOC
- [ ] Imports added to each file

### Phase 2: Facade Created
- [ ] `__init__.py` created with all re-exports
- [ ] Original `models.py` renamed to `_BACKUP.py`
- [ ] No syntax errors in new structure

### Phase 3: Validation Passed
- [ ] All 372 tests pass (100% pass rate)
- [ ] Specifically: All 243 model-importing tests pass
- [ ] NFR6 accuracy ≥90%
- [ ] NFR7 source attribution ≥95%
- [ ] Coverage ≥80%
- [ ] Mypy strict mode: ZERO errors
- [ ] Import test passes: `from raglite.shared.models import *`
- [ ] No circular import errors

### Phase 4: Cleanup Complete
- [ ] Backup file deleted
- [ ] `.file-size-exceptions` updated (remove `shared/models.py` entry)
- [ ] Git commit created
- [ ] Documentation updated

---

## Time Estimate

| Phase | Duration | Description |
|-------|----------|-------------|
| **Phase 1** | 30-45 min | Create 8 domain files, move models |
| **Phase 2** | 15-20 min | Create facade __init__.py |
| **Phase 3** | 45-90 min | Run all tests, validate (243 tests take time) |
| **Phase 4** | 10 min | Cleanup and commit |

**Total:** 100-165 minutes (1.5-2.75 hours)

**With automation:** 60-90 minutes (agent executes faster)

---

## Next Steps

### Option A: Execute Automated Refactoring
```bash
# Launch safe-refactor agent
/code_quality --fix --path=raglite/shared/models.py
```

### Option B: Execute Manual Step-by-Step
```bash
# Follow manual execution commands above
# Recommended for first-time or if you want hands-on control
```

### Option C: Iterate on Dry-Run Plan
- Review this plan
- Request adjustments (different domain split, different file names, etc.)
- Re-generate dry-run with changes

---

## Appendix A: Model Categorization Reference

### Document & Ingestion (5 models)
- `DocumentMetadata`
- `ExtractedMetadata`
- `BatchIngestionResult`
- `IngestionResult`
- `IngestionJobStatus`

### Chunking & Search (3 models)
- `Chunk`
- `SearchResult`
- `WorkflowMetrics`

### Query Models (6 models)
- `QueryRequest`
- `QueryResponse`
- `QueryResult`
- `AnalyticalQueryRequest`
- `AnalyticalQueryResponse`
- `ValidationResponse`

### Time Series & Forecasting (10 models)
- `TimeSeriesPoint`
- `TimeSeriesData`
- `ForecastPoint`
- `ForecastResult`
- `ForecastRefreshResult`
- `ForecastQueryRequest`
- `ForecastQueryResponse`
- `ModelPerformanceDetail`
- `VariableValidationDetail`
- `RegressorDataPoint`

### Insights (14 models + 4 enums)
- `AnomalySeverity` (Enum)
- `Anomaly`
- `AnomalyDetectionResult`
- `TrendDirection` (Enum)
- `Trend`
- `TrendAnalysisResult`
- `CorrelationResult`
- `InsightCategory` (Enum)
- `Insight`
- `InsightGenerationResult`
- `RecommendationCategory` (Enum)
- `Recommendation`
- `InsightsQueryRequest`
- `InsightsQueryResponse`

### External Data & Regressors (5 models)
- `RegressorInfo`
- `RegressorListResponse`
- `RegressorDataResponse`
- `AsyncIngestionRequest`
- `AsyncIngestionResponse`

### Validation (2 models)
- `RecommendationResult`
- `ValidationResponse`

---

## Appendix B: Import Pattern Analysis

### Current Import Pattern (will continue to work)
```python
from raglite.shared.models import DocumentMetadata, QueryResult
```

### Future Optional Pattern (after migration)
```python
from raglite.shared.models.document import DocumentMetadata
from raglite.shared.models.query import QueryResult
```

**Both patterns supported indefinitely via facade**

---

**END OF DRY-RUN PLAN**
