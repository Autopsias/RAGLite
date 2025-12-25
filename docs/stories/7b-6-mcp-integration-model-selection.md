# Story 7b-6: MCP Integration with Model Selection

Status: Drafted

## Story Header

- **Epic:** 7b - Intelligent Model Selection Framework
- **Priority:** P0
- **Effort:** 1.5 days
- **Status:** drafted
- **Dependencies:** 7b-3 (Per-Variable Model Selection via Cross-Validation), 7b-4 (Model Selection Cache in PostgreSQL), 7b-5 (Model Selection Slash Commands & Subagent)

## User Story

As an end user querying forecasts via MCP,
I want the system to automatically use the optimal model for each variable based on cached selection results,
So that I receive the most accurate forecasts without needing to know about model internals.

## Background

Stories 7b-3 and 7b-4 implement the model selection framework and PostgreSQL caching. Story 7b-5 provides the slash commands to populate the cache. This final story in Epic 7b integrates model selection into the MCP forecast flow, so that when `get_financial_forecast` is called, it automatically looks up the cached best model for each variable and routes to the appropriate forecasting function.

## Acceptance Criteria

### AC-7b.6.1: Check Model Selection Cache First

**Given** the MCP `get_financial_forecast` tool is called for a metric (e.g., "ebitda")
**When** `generate_forecast()` is invoked with `use_model_selection=True` (default)
**Then** the function first queries `get_cached_model_selection()` for the metric
**And** if a valid, non-expired cache entry exists, it uses the cached model configuration

**Verification:**
- `generate_forecast()` accepts `use_model_selection: bool = True` parameter
- Cache lookup performed before model selection
- Valid cache entries are used directly
- Cache TTL (7 days) is respected

### AC-7b.6.2: Route to Correct Model

**Given** a cached model selection result specifies a particular model (e.g., "arima", "ets", "xgboost")
**When** the forecast is generated
**Then** the correct model-specific forecasting function is called:
  - "arima" -> `_generate_arima_forecast()`
  - "ets" -> `_generate_ets_forecast()`
  - "prophet" -> `_generate_prophet_forecast()`
  - "xgboost" -> `_generate_xgboost_forecast()`
  - "lightgbm" -> `_generate_lightgbm_forecast()`
  - "catboost" -> `_generate_catboost_forecast()`
  - "chronos" -> `_generate_chronos_forecast()`
  - "tft" -> `_generate_tft_forecast()`
  - "linear" -> `_generate_linear_forecast()`

**Verification:**
- Router function exists to dispatch to correct model
- Each model type has a corresponding generator function
- Model name from cache is correctly parsed and routed

### AC-7b.6.3: Use Selected Regressor Set

**Given** the cached model selection specifies `use_regressors=True` and a `regressor_set`
**When** the forecast is generated
**Then** only the regressors in the cached `regressor_set` are passed to the model
**And** if `use_regressors=False`, no external regressors are used

**Verification:**
- Regressor set filtered to match cached selection
- Empty regressor handling works correctly
- Regressor availability checked before use

### AC-7b.6.4: Fallback to Prophet on Cache Miss or Model Failure

**Given** no cached model selection exists for a metric OR the selected model fails during forecasting
**When** the forecast is generated
**Then** the system falls back to Prophet as the default model
**And** logs a warning about the fallback reason

**Verification:**
- Cache miss triggers Prophet fallback
- Model execution errors trigger Prophet fallback
- Fallback logged with appropriate severity
- `model_source` in response indicates "default" for fallback

### AC-7b.6.5: Add model_source and model_selection_reason to Response

**Given** a forecast is generated using cached model selection
**When** the MCP response is constructed
**Then** the response includes:
  - `model_source`: "cached" | "default" | "fallback"
  - `model_selection_reason`: Human-readable explanation from data characteristics

**Enhanced Response Example:**
```json
{
  "metric_name": "ebitda",
  "forecast": [...],
  "model_type": "arima_1_1_1",
  "model_source": "cached",
  "model_selection_reason": "ARIMA selected: data is difference-stationary (ADF p=0.02), low seasonality (strength=0.12). CV MAPE: 8.2% vs Prophet 84.7%",
  "regressors_used": null,
  "confidence_reasoning": "..."
}
```

**Verification:**
- `model_source` field present in all forecast responses
- `model_selection_reason` populated for cached selections
- "default" source when using fallback

### AC-7b.6.6: Maintain Less Than 5s Query Time with Cache Hit

**Given** a valid model selection cache entry exists
**When** the MCP forecast is requested
**Then** the total query response time is less than 5 seconds

**Verification:**
- Cache lookup adds <100ms overhead
- Model routing adds negligible overhead
- End-to-end timing test with cache hit
- p50 < 3s, p95 < 5s targets

### AC-7b.6.7: E2E Tests for MCP Integration

**Given** the complete MCP integration is implemented
**When** end-to-end tests are run
**Then** all test scenarios pass:
  - Cache hit with ARIMA model
  - Cache hit with Prophet model
  - Cache hit with XGBoost + regressors
  - Cache miss fallback to Prophet
  - Model failure fallback to Prophet
  - Response includes model_source and model_selection_reason

**Verification:**
- E2E tests exist in `tests/e2e/test_mcp_model_selection.py`
- All scenarios covered with assertions
- Performance assertions for timing
- 80%+ coverage on new code

## Technical Specification

### Modified Flow in generate_forecast()

File: `raglite/forecasting/hybrid.py`

```python
from raglite.external_data.storage import get_cached_model_selection

async def generate_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int = 4,
    external_regressors: dict | None = None,
    use_model_selection: bool = True,  # NEW
) -> ForecastResult:
    """Generate forecast using optimal model from cache.

    Args:
        metric: Name of the metric to forecast
        historical_data: Historical time series data
        periods_ahead: Number of periods to forecast
        external_regressors: Optional external regressors dict
        use_model_selection: If True, use cached model selection (default: True)

    Returns:
        ForecastResult with predictions and metadata
    """
    model_source = "default"
    model_selection_reason = None
    selected_model = "prophet"  # Default
    selected_regressors = None

    # 1. Check model selection cache
    if use_model_selection:
        cached = await get_cached_model_selection(metric)
        if cached and not cached.is_expired:
            selected_model = cached.best_model
            selected_regressors = cached.best_regressor_set if cached.use_regressors else None
            model_source = "cached"
            model_selection_reason = cached.data_characteristics.get("model_rationale")
            logger.info(
                f"Using cached model selection for {metric}",
                extra={"model": selected_model, "source": model_source}
            )
        else:
            logger.info(
                f"No valid cache for {metric}, using default Prophet",
                extra={"cache_status": "miss" if not cached else "expired"}
            )

    # 2. Filter regressors to selected set
    if selected_regressors and external_regressors:
        filtered_regressors = {
            k: v for k, v in external_regressors.items()
            if k in selected_regressors
        }
    else:
        filtered_regressors = None if not selected_regressors else external_regressors

    # 3. Route to appropriate model
    try:
        result = await _route_to_model(
            model_name=selected_model,
            metric=metric,
            historical_data=historical_data,
            periods_ahead=periods_ahead,
            external_regressors=filtered_regressors,
        )
    except Exception as e:
        logger.warning(
            f"Model {selected_model} failed for {metric}, falling back to Prophet: {e}",
            extra={"original_model": selected_model, "error": str(e)}
        )
        model_source = "fallback"
        model_selection_reason = f"Fallback due to {selected_model} failure: {str(e)[:100]}"
        result = await _generate_prophet_forecast(
            metric=metric,
            historical_data=historical_data,
            periods_ahead=periods_ahead,
            external_regressors=None,
        )

    # 4. Add selection metadata to result
    result.model_source = model_source
    result.model_selection_reason = model_selection_reason

    return result


async def _route_to_model(
    model_name: str,
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict | None,
) -> ForecastResult:
    """Route forecast request to appropriate model function.

    Args:
        model_name: Name of the model to use
        metric: Metric being forecast
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from the selected model

    Raises:
        ValueError: If model_name is unknown
    """
    model_routers = {
        "arima": _generate_arima_forecast,
        "ets": _generate_ets_forecast,
        "prophet": _generate_prophet_forecast,
        "xgboost": _generate_xgboost_forecast,
        "lightgbm": _generate_lightgbm_forecast,
        "catboost": _generate_catboost_forecast,
        "chronos": _generate_chronos_forecast,
        "tft": _generate_tft_forecast,
        "linear": _generate_linear_forecast,
    }

    if model_name not in model_routers:
        raise ValueError(f"Unknown model: {model_name}")

    generator = model_routers[model_name]
    return await generator(
        metric=metric,
        historical_data=historical_data,
        periods_ahead=periods_ahead,
        external_regressors=external_regressors,
    )
```

### Updated ForecastResult Model

File: `raglite/shared/models.py`

```python
from pydantic import BaseModel, Field
from typing import Literal

class ForecastResult(BaseModel):
    """Result from forecast generation."""
    metric_name: str
    forecast: list[ForecastPoint]
    model_type: str
    confidence_reasoning: str | None = None
    regressors_used: list[str] | None = None

    # NEW: Model selection metadata
    model_source: Literal["cached", "default", "fallback"] = Field(
        default="default",
        description="Source of model selection: cached (from model_selection table), default (no cache), fallback (error recovery)"
    )
    model_selection_reason: str | None = Field(
        default=None,
        description="Human-readable explanation of why this model was selected"
    )
```

### Updated MCP Response

File: `raglite/main.py`

```python
class ForecastQueryResponse(BaseModel):
    """Response from forecast query MCP tool."""
    metric_name: str
    forecast: list[dict]
    model_type: str
    confidence_reasoning: str | None = None
    regressors_used: list[str] | None = None

    # NEW: Model selection metadata
    model_source: str = Field(
        default="default",
        description="Source of model selection"
    )
    model_selection_reason: str | None = Field(
        default=None,
        description="Explanation of model selection"
    )
```

### Model-Specific Forecast Functions

Each model needs a wrapper function that:
1. Prepares data in model-specific format
2. Calls the underlying fit/predict functions from Story 7b-1 and existing hybrid.py
3. Returns standardized ForecastResult

```python
async def _generate_arima_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict | None,
) -> ForecastResult:
    """Generate forecast using ARIMA model.

    Uses fit_arima() from Story 7b-1.
    """
    # Convert to pandas Series
    y_train = historical_data.to_series()
    X_train = _prepare_regressors(external_regressors, historical_data.dates) if external_regressors else None

    # Fit and predict
    model, model_info, predictions, conf_int = await fit_arima(
        y_train=y_train,
        X_train=X_train,
        forecast_horizon=periods_ahead,
        frequency=historical_data.frequency,
    )

    # Build forecast points
    forecast_points = _build_forecast_points(
        predictions=predictions,
        conf_int=conf_int,
        start_date=historical_data.last_date,
        frequency=historical_data.frequency,
    )

    return ForecastResult(
        metric_name=metric,
        forecast=forecast_points,
        model_type=f"arima_{model_info['order']}",
        regressors_used=list(external_regressors.keys()) if external_regressors else None,
    )


async def _generate_ets_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict | None,  # ETS doesn't use regressors
) -> ForecastResult:
    """Generate forecast using ETS model.

    Uses fit_ets() from Story 7b-1.
    Note: ETS does not support exogenous regressors.
    """
    y_train = historical_data.to_series()

    model, model_info, predictions, conf_int = await fit_ets(
        y_train=y_train,
        forecast_horizon=periods_ahead,
        frequency=historical_data.frequency,
    )

    forecast_points = _build_forecast_points(
        predictions=predictions,
        conf_int=conf_int,
        start_date=historical_data.last_date,
        frequency=historical_data.frequency,
    )

    return ForecastResult(
        metric_name=metric,
        forecast=forecast_points,
        model_type="ets",
        regressors_used=None,  # ETS doesn't support regressors
    )


# Similar implementations for other models...
```

### Files to Modify

| File | Action | Lines |
|------|--------|-------|
| raglite/forecasting/hybrid.py | Modify generate_forecast, add model routers | +300 |
| raglite/shared/models.py | Add model_source, model_selection_reason fields | +10 |
| raglite/main.py | Update ForecastQueryResponse schema | +20 |
| tests/e2e/test_mcp_model_selection.py | Create | +150 |

## Tasks

- [ ] Task 1: Update ForecastResult model (AC-7b.6.5)
  - [ ] 1.1 Add `model_source: Literal["cached", "default", "fallback"]` field
  - [ ] 1.2 Add `model_selection_reason: str | None` field
  - [ ] 1.3 Add Field descriptions and defaults
  - [ ] 1.4 Update any serialization logic

- [ ] Task 2: Update ForecastQueryResponse in main.py (AC-7b.6.5)
  - [ ] 2.1 Add `model_source` field to MCP response schema
  - [ ] 2.2 Add `model_selection_reason` field to MCP response schema
  - [ ] 2.3 Map ForecastResult fields to response

- [ ] Task 3: Implement cache lookup in generate_forecast() (AC-7b.6.1)
  - [ ] 3.1 Add `use_model_selection: bool = True` parameter
  - [ ] 3.2 Import and call `get_cached_model_selection()`
  - [ ] 3.3 Check for valid, non-expired cache entry
  - [ ] 3.4 Extract model name and regressor set from cache
  - [ ] 3.5 Set `model_source` to "cached" or "default"

- [ ] Task 4: Implement regressor filtering (AC-7b.6.3)
  - [ ] 4.1 If cached selection specifies regressors, filter input regressors
  - [ ] 4.2 Handle empty regressor set case
  - [ ] 4.3 Handle missing regressors gracefully
  - [ ] 4.4 Log regressor filtering decisions

- [ ] Task 5: Implement model router (AC-7b.6.2)
  - [ ] 5.1 Create `_route_to_model()` dispatcher function
  - [ ] 5.2 Define router dict with all 9 model names
  - [ ] 5.3 Route to appropriate generator function
  - [ ] 5.4 Handle unknown model names with ValueError

- [ ] Task 6: Implement model-specific generators (AC-7b.6.2)
  - [ ] 6.1 Create `_generate_arima_forecast()` using fit_arima()
  - [ ] 6.2 Create `_generate_ets_forecast()` using fit_ets()
  - [ ] 6.3 Verify `_generate_prophet_forecast()` exists (should already exist)
  - [ ] 6.4 Verify `_generate_xgboost_forecast()` exists
  - [ ] 6.5 Verify `_generate_lightgbm_forecast()` exists
  - [ ] 6.6 Verify `_generate_catboost_forecast()` exists
  - [ ] 6.7 Create `_generate_chronos_forecast()` wrapper
  - [ ] 6.8 Create `_generate_tft_forecast()` wrapper
  - [ ] 6.9 Create `_generate_linear_forecast()` wrapper

- [ ] Task 7: Implement fallback handling (AC-7b.6.4)
  - [ ] 7.1 Wrap model execution in try/except
  - [ ] 7.2 On exception, log warning with original model info
  - [ ] 7.3 Fall back to Prophet forecast
  - [ ] 7.4 Set `model_source` to "fallback"
  - [ ] 7.5 Set `model_selection_reason` with error context

- [ ] Task 8: Attach selection metadata to result (AC-7b.6.5)
  - [ ] 8.1 Set `result.model_source` from selection logic
  - [ ] 8.2 Set `result.model_selection_reason` from cache or fallback
  - [ ] 8.3 Ensure metadata flows through to MCP response

- [ ] Task 9: Write unit tests
  - [ ] 9.1 Test cache hit routing
  - [ ] 9.2 Test cache miss fallback
  - [ ] 9.3 Test model failure fallback
  - [ ] 9.4 Test regressor filtering
  - [ ] 9.5 Test model router dispatch
  - [ ] 9.6 Test response metadata population

- [ ] Task 10: Write E2E tests (AC-7b.6.7)
  - [ ] 10.1 Create `tests/e2e/test_mcp_model_selection.py`
  - [ ] 10.2 Test cache hit with ARIMA model
  - [ ] 10.3 Test cache hit with Prophet model
  - [ ] 10.4 Test cache hit with XGBoost + regressors
  - [ ] 10.5 Test cache miss fallback to Prophet
  - [ ] 10.6 Test model failure fallback to Prophet
  - [ ] 10.7 Test response includes model_source and model_selection_reason

- [ ] Task 11: Performance testing (AC-7b.6.6)
  - [ ] 11.1 Add timing assertions to E2E tests
  - [ ] 11.2 Verify cache lookup adds <100ms overhead
  - [ ] 11.3 Verify total response time <5s with cache hit
  - [ ] 11.4 Log performance metrics

- [ ] Task 12: Validation (MANDATORY)
  - [ ] 12.1 Run unit tests: `uv run pytest tests/unit/test_*forecast*.py -v`
  - [ ] 12.2 Run E2E tests: `uv run pytest tests/e2e/test_mcp_model_selection.py -v`
  - [ ] 12.3 Populate cache: `/model-selection --all`
  - [ ] 12.4 Test MCP forecast via Claude Desktop
  - [ ] 12.5 Verify response includes model_source: "cached"
  - [ ] 12.6 Verify timing <5s for cache hit scenario
  - [ ] 12.7 Test fallback by corrupting cache entry

## Dev Notes

### Architecture References

- [Source: docs/prd/epic-7-intelligent-model-selection.md#Story 7.6]
- [Source: docs/architecture/5-technology-stack-definitive.md]
- [Source: raglite/forecasting/hybrid.py] - Existing forecast generation
- [Source: raglite/external_data/storage.py] - Story 7b-4 get_cached_model_selection()
- [Source: raglite/forecasting/model_wrappers.py] - Story 7b-1 fit_arima(), fit_ets()

### Existing Patterns to Follow

**Forecast Generation Pattern:**
```python
async def generate_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int = 4,
    external_regressors: dict | None = None,
) -> ForecastResult:
    # Existing pattern - extend with model selection
```

**Cache Lookup Pattern (from Story 7b-4):**
```python
async def get_cached_model_selection(variable_name: str) -> ModelSelectionCache | None:
    """Get cached model selection if valid."""
    # Returns None if no cache or expired
```

**Error Handling Pattern:**
```python
try:
    result = await risky_operation()
except Exception as e:
    logger.warning(f"Operation failed: {e}", extra={"error_type": type(e).__name__})
    result = await fallback_operation()
```

### Key Technical Details

1. **Cache Lookup Performance:**
   - PostgreSQL lookup should be <100ms
   - Use connection pooling for efficiency
   - Consider caching in memory for repeated calls

2. **Model Router Design:**
   - Simple dict-based dispatch for clarity
   - Raise ValueError for unknown models
   - Each generator has consistent signature

3. **Regressor Handling:**
   - Filter to cached regressor set
   - Log which regressors are used vs available
   - ETS doesn't support regressors (ignore for ETS)

4. **Fallback Strategy:**
   - Prophet is reliable default
   - Log original model and error
   - Preserve context in model_selection_reason

### Model Generator Availability

| Model | Generator | Status | Notes |
|-------|-----------|--------|-------|
| arima | `_generate_arima_forecast` | New | Use fit_arima() from 7b-1 |
| ets | `_generate_ets_forecast` | New | Use fit_ets() from 7b-1 |
| prophet | `_generate_prophet_forecast` | Existing | Already in hybrid.py |
| xgboost | `_generate_xgboost_forecast` | Existing | Already in hybrid.py |
| lightgbm | `_generate_lightgbm_forecast` | Existing | Already in hybrid.py |
| catboost | `_generate_catboost_forecast` | Existing | From Story 6.12 |
| chronos | `_generate_chronos_forecast` | Existing | From Story 6.13 |
| tft | `_generate_tft_forecast` | Existing | From Story 6.14 |
| linear | `_generate_linear_forecast` | New/Existing | Ridge/Lasso in hybrid.py |

### Performance Budget

| Operation | Target Time |
|-----------|-------------|
| Cache lookup | <100ms |
| Model routing | <10ms |
| Forecast generation | <4s |
| Total response | <5s |

### NFRs

- **Response Time:** <5s for cache hit scenario (p95)
- **Cache Overhead:** <100ms added by cache lookup
- **Fallback Rate:** <5% of requests should need fallback
- **Test Coverage:** 80%+ on new code
- **Error Handling:** Graceful degradation, no user-facing errors

## Testing Requirements

### Unit Tests

Location: `tests/unit/test_hybrid_model_selection.py` (or extend existing)

- Test `_route_to_model()` with all 9 model types
- Test cache hit routing logic
- Test cache miss fallback
- Test regressor filtering
- Test model failure fallback
- Test metadata attachment to ForecastResult
- Mock dependencies (storage, model functions)

### E2E Tests

Location: `tests/e2e/test_mcp_model_selection.py`

```python
"""E2E tests for MCP integration with model selection."""

import pytest
from unittest.mock import patch, AsyncMock

from raglite.forecasting.hybrid import generate_forecast
from raglite.external_data.storage import get_cached_model_selection


class TestMCPModelSelectionIntegration:
    """E2E tests for model selection in MCP forecasts."""

    @pytest.mark.asyncio
    async def test_cache_hit_arima_model(self, populated_cache, sample_data):
        """Test forecast uses cached ARIMA selection."""
        result = await generate_forecast(
            metric="ebitda",
            historical_data=sample_data,
            periods_ahead=4,
        )

        assert result.model_source == "cached"
        assert "arima" in result.model_type.lower()
        assert result.model_selection_reason is not None

    @pytest.mark.asyncio
    async def test_cache_hit_with_regressors(self, populated_cache, sample_data, regressors):
        """Test forecast uses cached regressor selection."""
        result = await generate_forecast(
            metric="revenue",
            historical_data=sample_data,
            periods_ahead=4,
            external_regressors=regressors,
        )

        assert result.model_source == "cached"
        assert result.regressors_used is not None
        # Only selected regressors should be used
        assert all(r in cached_regressor_set for r in result.regressors_used)

    @pytest.mark.asyncio
    async def test_cache_miss_fallback(self, empty_cache, sample_data):
        """Test fallback to Prophet when cache is empty."""
        result = await generate_forecast(
            metric="unknown_metric",
            historical_data=sample_data,
            periods_ahead=4,
        )

        assert result.model_source == "default"
        assert "prophet" in result.model_type.lower()

    @pytest.mark.asyncio
    async def test_model_failure_fallback(self, populated_cache, sample_data):
        """Test fallback when selected model fails."""
        with patch("raglite.forecasting.hybrid._generate_arima_forecast") as mock:
            mock.side_effect = Exception("ARIMA convergence failed")

            result = await generate_forecast(
                metric="ebitda",
                historical_data=sample_data,
                periods_ahead=4,
            )

            assert result.model_source == "fallback"
            assert "prophet" in result.model_type.lower()
            assert "ARIMA" in result.model_selection_reason

    @pytest.mark.asyncio
    async def test_response_time_cache_hit(self, populated_cache, sample_data):
        """Test response time is <5s with cache hit."""
        import time

        start = time.time()
        result = await generate_forecast(
            metric="ebitda",
            historical_data=sample_data,
            periods_ahead=4,
        )
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Response took {elapsed:.2f}s, expected <5s"
        assert result.model_source == "cached"
```

### Validation Checklist

```bash
# Unit tests
uv run pytest tests/unit/test_hybrid_model_selection.py -v

# E2E tests
APP_ENV=test uv run pytest tests/e2e/test_mcp_model_selection.py -v

# Populate cache first
# /model-selection --all

# Verify cache has entries
docker exec raglite-postgresql psql -U raglite -d raglite \
  -c "SELECT variable_name, best_model FROM model_selection LIMIT 5"

# Manual MCP test via Claude Desktop
# "Forecast EBITDA for Q1 2026"
# Verify response includes:
# - model_source: "cached"
# - model_selection_reason: "ARIMA selected: ..."

# Performance test
uv run pytest tests/e2e/test_mcp_model_selection.py::test_response_time_cache_hit -v
```

## Definition of Done

- [ ] All 7 acceptance criteria verified with passing tests
- [ ] `generate_forecast()` modified to check cache and route to models
- [ ] `ForecastResult` includes model_source and model_selection_reason
- [ ] `ForecastQueryResponse` MCP schema updated
- [ ] All 9 model generators implemented or verified existing
- [ ] Fallback to Prophet works for cache miss and model failure
- [ ] E2E tests passing in `tests/e2e/test_mcp_model_selection.py`
- [ ] Performance test confirms <5s with cache hit
- [ ] Unit tests passing with 80%+ coverage on new code
- [ ] Docstrings added to all new/modified functions
- [ ] Epic 7b complete - all stories validated

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

(To be filled during implementation)

### Debug Log References

N/A

### Completion Notes List

(To be filled during implementation)

### File List

**To Modify:**
- `raglite/forecasting/hybrid.py` - Add cache lookup, model router, generators (+300 lines)
- `raglite/shared/models.py` - Add model_source, model_selection_reason fields (+10 lines)
- `raglite/main.py` - Update ForecastQueryResponse (+20 lines)

**To Create:**
- `tests/e2e/test_mcp_model_selection.py` - E2E tests (+150 lines)

**To Reference:**
- `raglite/forecasting/model_wrappers.py` - Story 7b-1 fit_arima(), fit_ets()
- `raglite/external_data/storage.py` - Story 7b-4 get_cached_model_selection()
- `raglite/forecasting/model_selection.py` - Story 7b-3 ModelSelectionResult

### Change Log

- 2025-12-21: Story drafted with all 7 acceptance criteria in BDD format
