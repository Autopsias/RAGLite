# ATDD Checklist: Story 7b-6 MCP Integration with Model Selection

**Story:** 7b-6 - MCP Integration with Model Selection
**Epic:** Epic 7 - Intelligent Model Selection
**TDD Phase:** RED (Tests created, implementation pending)
**Created:** 2025-12-21

---

## Overview

This checklist tracks the ATDD (Acceptance Test-Driven Development) progress for Story 7b-6, which integrates the model selection cache with the MCP forecast query tool.

## Acceptance Criteria Mapping

| AC | Description | Test File | Test IDs | Status |
|----|-------------|-----------|----------|--------|
| AC-7b.6.1 | Check Model Selection Cache First | `test_mcp_model_selection_integration.py` | TEST-AC-7b.6.1.1 to TEST-AC-7b.6.1.6 | RED |
| AC-7b.6.2 | Route to Correct Model | `test_mcp_model_selection_integration.py` | TEST-AC-7b.6.2.1 to TEST-AC-7b.6.2.7 | RED |
| AC-7b.6.3 | Use Selected Regressor Set | `test_mcp_model_selection_integration.py` | TEST-AC-7b.6.3.1 to TEST-AC-7b.6.3.3 | RED |
| AC-7b.6.4 | Fallback to Prophet on Failure | `test_mcp_model_selection_integration.py` | TEST-AC-7b.6.4.1 to TEST-AC-7b.6.4.3 | RED |
| AC-7b.6.5 | Response Metadata | `test_mcp_model_selection_integration.py` | TEST-AC-7b.6.5.1 to TEST-AC-7b.6.5.8 | RED |
| AC-7b.6.6 | Performance (<5s query time) | `test_mcp_model_selection.py` (E2E) | TEST-AC-7b.6.6.1 to TEST-AC-7b.6.6.4 | RED |
| AC-7b.6.7 | E2E Integration | `test_mcp_model_selection.py` (E2E) | TEST-AC-7b.6.7.1 to TEST-AC-7b.6.7.6 | RED |

---

## Test Files

### Unit Tests

**File:** `tests/unit/test_mcp_model_selection_integration.py`

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestCacheLookup` | 6 tests | Verify cache lookup behavior and use_model_selection parameter |
| `TestModelRouting` | 7 tests | Verify _route_to_model function supports all models |
| `TestRegressorFiltering` | 3 tests | Verify regressor filtering based on cached selection |
| `TestFallbackHandling` | 3 tests | Verify fallback to Prophet on cache miss or model failure |
| `TestResponseMetadata` | 6 tests | Verify model_source and model_selection_reason fields |
| `TestMCPResponseSchema` | 2 tests | Verify ForecastQueryResponse schema updates |
| `TestPerformance` | 2 tests | Verify cache lookup performance |
| `TestModelGenerators` | 9 tests | Verify model-specific generator functions exist |

**Total Unit Tests:** 38

### E2E Tests

**File:** `tests/e2e/test_mcp_model_selection.py`

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestMCPModelSelectionE2E` | 6 tests | End-to-end integration scenarios |
| `TestMCPPerformance` | 2 tests | Performance validation |
| `TestMCPToolResponse` | 2 tests | MCP tool response format |

**Total E2E Tests:** 10

---

## Implementation Requirements

Based on failing tests, the following must be implemented:

### 1. Modify `generate_forecast()` in `raglite/forecasting/hybrid.py`

```python
async def generate_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int = 4,
    external_regressors: dict[str, pd.Series] | None = None,
    use_model_selection: bool = True,  # NEW PARAMETER
) -> ForecastResult:
```

- Add `use_model_selection` parameter (default: True)
- When True, call `get_cached_model_selection(metric)` first
- If cache hit and not expired, use cached model configuration
- If cache miss or expired, use default Prophet

### 2. Add `_route_to_model()` function

```python
async def _route_to_model(
    model_name: str,
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
```

- Route to correct model generator based on model_name
- Support: arima, ets, prophet, xgboost, lightgbm, catboost, chronos, tft, linear
- Raise ValueError for unknown model names

### 3. Add model-specific generators

Add these functions to `raglite/forecasting/hybrid.py`:

- `_generate_arima_forecast()`
- `_generate_ets_forecast()`
- `_generate_prophet_forecast()`
- `_generate_xgboost_forecast()`
- `_generate_lightgbm_forecast()`
- `_generate_catboost_forecast()`
- `_generate_chronos_forecast()`
- `_generate_tft_forecast()`
- `_generate_linear_forecast()`

### 4. Update `ForecastResult` in `raglite/shared/models.py`

Add fields:
```python
model_source: str = Field(
    default="default",
    description="Source of model selection: 'cached', 'default', or 'fallback'"
)
model_selection_reason: str | None = Field(
    default=None,
    description="Explanation for model selection"
)
```

### 5. Update `ForecastQueryResponse` in `raglite/shared/models.py`

Add fields:
```python
model_source: str = Field(
    default="default",
    description="Source of model selection"
)
```

Update `from_forecast_result()` to pass through model selection fields.

---

## Test Execution Commands

```bash
# Run unit tests only (RED phase - should fail)
uv run pytest tests/unit/test_mcp_model_selection_integration.py -v

# Run E2E tests only (RED phase - should fail)
uv run pytest tests/e2e/test_mcp_model_selection.py -v

# Run all Story 7b-6 tests
uv run pytest tests/unit/test_mcp_model_selection_integration.py tests/e2e/test_mcp_model_selection.py -v

# Run with coverage
uv run pytest tests/unit/test_mcp_model_selection_integration.py --cov=raglite/forecasting/hybrid --cov-report=term-missing
```

---

## Progress Tracking

### Phase Status

| Phase | Status | Date |
|-------|--------|------|
| RED (Tests Created) | COMPLETE | 2025-12-21 |
| GREEN (Implementation) | PENDING | - |
| REFACTOR | PENDING | - |

### Test Results

| Execution | Unit Pass | Unit Fail | E2E Pass | E2E Fail | Notes |
|-----------|-----------|-----------|----------|----------|-------|
| Initial (RED) | 0 | 38 | 0 | 10 | Expected - TDD RED phase |

---

## Dependencies

### From Story 7b-4 (Model Selection Cache)

- `CachedModelSelection` dataclass
- `get_cached_model_selection()` function
- `MODEL_SELECTION_TTL_DAYS` constant

### From Story 7b-3 (Per-Variable Model Selection CV)

- `ModelSelectionResult` dataclass
- `run_model_selection()` function

### From Story 7b-2 (Expanded Model Candidates)

- ARIMA model wrapper
- ETS model wrapper

---

## Acceptance Criteria Details

### AC-7b.6.1: Check Model Selection Cache First (P0)

**Given** a forecast query request
**When** `use_model_selection=True` (default)
**Then** `get_cached_model_selection(variable_name)` is called
**And** if cache hit with valid TTL, cached model configuration is used
**And** if cache miss or expired, default Prophet is used

**Tests:**
- TEST-AC-7b.6.1.1: generate_forecast accepts use_model_selection parameter
- TEST-AC-7b.6.1.2: use_model_selection defaults to True
- TEST-AC-7b.6.1.3: Cache lookup called when enabled
- TEST-AC-7b.6.1.4: Cache lookup skipped when disabled
- TEST-AC-7b.6.1.5: Uses cached model when valid
- TEST-AC-7b.6.1.6: Ignores expired cache

### AC-7b.6.2: Route to Correct Model (P0)

**Given** a cached model selection result
**When** generating forecast
**Then** the specified model is used (ARIMA, ETS, Prophet, XGBoost, etc.)

**Tests:**
- TEST-AC-7b.6.2.1: _route_to_model function exists
- TEST-AC-7b.6.2.2: Supports all 9 model types
- TEST-AC-7b.6.2.3: Routes to ARIMA
- TEST-AC-7b.6.2.4: Routes to ETS
- TEST-AC-7b.6.2.5: Routes to Prophet
- TEST-AC-7b.6.2.6: Routes to XGBoost
- TEST-AC-7b.6.2.7: Raises error for unknown model

### AC-7b.6.3: Use Selected Regressor Set (P0)

**Given** a cached model selection with regressor_list
**When** generating forecast with external_regressors
**Then** only the cached regressor set is passed to the model

**Tests:**
- TEST-AC-7b.6.3.1: Filters regressors to cached set
- TEST-AC-7b.6.3.2: No regressors when use_regressors=False
- TEST-AC-7b.6.3.3: Handles missing regressors gracefully

### AC-7b.6.4: Fallback to Prophet on Failure (P0)

**Given** a model selection cache entry
**When** the selected model fails to generate a forecast
**Then** Prophet is used as fallback
**And** model_source is set to "fallback"

**Tests:**
- TEST-AC-7b.6.4.1: Fallback on cache miss
- TEST-AC-7b.6.4.2: Fallback on model failure
- TEST-AC-7b.6.4.3: Fallback includes error context

### AC-7b.6.5: Response Metadata (P0)

**Given** a forecast query response
**Then** it includes `model_source` and `model_selection_reason` fields

**Tests:**
- TEST-AC-7b.6.5.1: ForecastResult has model_source field
- TEST-AC-7b.6.5.2: ForecastResult has model_selection_reason field
- TEST-AC-7b.6.5.3: model_source accepts valid values
- TEST-AC-7b.6.5.4: model_source defaults to "default"
- TEST-AC-7b.6.5.5: model_selection_reason can be None
- TEST-AC-7b.6.5.6: Cached selection populates reason
- TEST-AC-7b.6.5.7: ForecastQueryResponse has model_source
- TEST-AC-7b.6.5.8: ForecastQueryResponse has model_selection_reason

### AC-7b.6.6: Performance (P1)

**Given** a forecast query with cache hit
**Then** response time is <5s (p50 <3s)

**Tests:**
- TEST-AC-7b.6.6.1: Cache lookup under 100ms
- TEST-AC-7b.6.6.2: Model routing negligible overhead
- TEST-AC-7b.6.6.3: E2E response under 5s
- TEST-AC-7b.6.6.4: p50 under 3s

### AC-7b.6.7: E2E Integration (P0)

**Given** the full integration
**Then** cache lookup, model routing, and response formatting work correctly

**Tests:**
- TEST-AC-7b.6.7.1: Cache hit with ARIMA model
- TEST-AC-7b.6.7.2: Cache hit with Prophet model
- TEST-AC-7b.6.7.3: Cache hit with XGBoost + regressors
- TEST-AC-7b.6.7.4: Cache miss fallback to Prophet
- TEST-AC-7b.6.7.5: Model failure fallback to Prophet
- TEST-AC-7b.6.7.6: Response includes all metadata

---

## Notes

- All tests are in RED phase (expected to fail) until implementation
- Integration tests require PostgreSQL and Qdrant test containers
- E2E tests are marked with `@pytest.mark.slow` for CI optimization
- Model generators may need to import from `raglite.forecasting.model_wrappers`
