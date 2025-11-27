# Story 4.3: Automated Forecast Updates

Status: ready-for-dev

## Story

As a **system**,
I want **forecasts to update automatically when new financial documents are ingested**,
so that **predictions remain current without manual intervention**.

## Acceptance Criteria

| AC | Criterion | Validation Method |
|----|-----------|-------------------|
| AC1 | Document ingestion triggers forecast refresh for affected metrics (FR20) | Integration test: ingest document → verify forecast refresh invoked |
| AC2 | Incremental updates avoid full recomputation when possible | Unit test: only affected metrics (by document type) are refreshed |
| AC3 | Forecast update completes within 5 minutes of document ingestion | Performance test: measure end-to-end ingestion + forecast time |
| AC4 | Users notified of updated forecasts via MCP response (if applicable) | Unit test: ingestion response includes `forecasts_updated` field |
| AC5 | Integration test validates forecast refresh after new document added | Integration test: ingest → extract time-series → verify forecast updated |

## Tasks / Subtasks

### Task 1: Design post-ingestion hook architecture (AC: 1)
- [ ] 1.1 Define `PostIngestionHook` protocol/interface in `shared/models.py`
- [ ] 1.2 Create `ForecastUpdateHook` implementing the protocol
- [ ] 1.3 Decide trigger location: within `ingest_document()` or via orchestrator callback

### Task 2: Implement forecast refresh trigger (AC: 1, 2)
- [ ] 2.1 Create `raglite/forecasting/auto_update.py` (~50-75 lines)
- [ ] 2.2 Implement `trigger_forecast_refresh(document_metadata: DocumentMetadata)` async function
- [ ] 2.3 Detect affected metrics from document metadata (reporting_period, metric_category)
- [ ] 2.4 Call `extract_timeseries()` for affected document
- [ ] 2.5 Call `generate_forecast()` for affected metrics only (incremental)

### Task 3: Integrate with document ingestion pipeline (AC: 1, 3)
- [ ] 3.1 Add post-ingestion callback in `document_ingestion.py:ingest_document()`
- [ ] 3.2 Configure optional/configurable hook (via Settings or parameter)
- [ ] 3.3 Add timeout guard: 5-minute max for forecast refresh (graceful abort)
- [ ] 3.4 Log forecast refresh success/failure with timing metrics

### Task 4: Implement MCP response enrichment (AC: 4)
- [ ] 4.1 Extend `IngestionResult` model with `forecasts_updated: list[str] | None`
- [ ] 4.2 Update MCP `ingest_financial_document()` to include forecast status
- [ ] 4.3 Add `forecast_refresh_skipped_reason` for cases where refresh not triggered

### Task 5: Unit tests (AC: 2, 4)
- [ ] 5.1 Create `tests/unit/test_auto_update.py`
- [ ] 5.2 Test `trigger_forecast_refresh()` with mocked time-series extraction
- [ ] 5.3 Test incremental updates: only affected metrics refreshed
- [ ] 5.4 Test timeout behavior: graceful abort at 5-minute limit
- [ ] 5.5 Test MCP response includes forecast update status
- [ ] 5.6 Achieve ≥80% coverage on new code (DoD requirement)

### Task 6: Integration tests (AC: 1, 3, 5)
- [ ] 6.1 Create `tests/integration/test_auto_forecast_update.py`
- [ ] 6.2 Test end-to-end: ingest document → time-series extraction → forecast refresh
- [ ] 6.3 Test performance: total time < 5 minutes for standard document
- [ ] 6.4 Test with test database (port 6335/5433 per Story 4.0.5)

### Task 7: Documentation and cleanup (AC: All)
- [ ] 7.1 Add Google-style docstrings to all public functions
- [ ] 7.2 Update story file with Dev Agent Record
- [ ] 7.3 Verify all linting passes (`uv run ruff check .`)
- [ ] 7.4 Update `raglite/forecasting/__init__.py` with new exports

## Dev Notes

### Architecture Patterns

**File Location:** `raglite/forecasting/auto_update.py` (~50-75 lines target)

**Key Function Signatures:**
```python
async def trigger_forecast_refresh(
    document_metadata: DocumentMetadata,
    timeout_seconds: int = 300  # 5 minutes
) -> ForecastRefreshResult:
    """Trigger forecast refresh after document ingestion.

    Args:
        document_metadata: Metadata from ingested document
        timeout_seconds: Maximum time for refresh (default 5 min)

    Returns:
        ForecastRefreshResult with updated metrics and timing

    Process:
        1. Identify affected metrics from document metadata
        2. Extract time-series data for new document
        3. Refresh forecasts for affected metrics only (incremental)
        4. Return summary of updates
    """

async def identify_affected_metrics(
    document_metadata: DocumentMetadata
) -> list[str]:
    """Identify which forecast metrics are affected by this document.

    Args:
        document_metadata: Metadata from ingested document

    Returns:
        List of metric names to refresh (e.g., ["revenue", "expenses"])

    Logic:
        - Revenue documents → refresh "revenue" forecast
        - Expense reports → refresh "expenses" forecast
        - General financial → refresh all applicable forecasts
    """
```

**Data Models (add to `shared/models.py`):**
```python
class ForecastRefreshResult(BaseModel):
    """Result of automatic forecast refresh after document ingestion."""
    document_id: str
    metrics_refreshed: list[str]
    metrics_skipped: list[str]
    refresh_duration_ms: int
    success: bool
    error_message: str | None = None
```

### Incremental Update Strategy (AC2)

Per Tech Spec Risk 3 and NFR requirements:

1. **Identify affected metrics** from document metadata:
   - `metric_category` field indicates primary metric type
   - `reporting_period` helps scope the time range
   - Document type (quarterly/annual) affects granularity

2. **Skip unaffected metrics**: If document is expense-focused, don't refresh revenue forecast

3. **Merge time-series data**: Combine new document's extracted data with existing historical data

4. **Incremental Prophet update**: Use existing model if available, retrain only with new data points

### Integration with Ingestion Pipeline

**Option A: Direct callback in `ingest_document()` (RECOMMENDED)**
```python
# In document_ingestion.py
async def ingest_document(file_path: str, auto_forecast: bool = True) -> DocumentMetadata:
    # ... existing ingestion logic ...

    if auto_forecast and settings.enable_forecast_auto_update:
        try:
            refresh_result = await trigger_forecast_refresh(metadata, timeout_seconds=300)
            logger.info("Forecast refreshed", extra={"metrics": refresh_result.metrics_refreshed})
        except asyncio.TimeoutError:
            logger.warning("Forecast refresh timed out after 5 minutes")

    return metadata
```

**Option B: Via orchestrator event (deferred to Story 4.5+)**
- More flexible but adds complexity
- Better for multi-agent workflows
- Can be added later without breaking changes

### Configuration

Add to `shared/config.py` (Settings class):
```python
enable_forecast_auto_update: bool = True  # Can be disabled for batch ingestion
forecast_refresh_timeout: int = 300  # 5 minutes
```

### NFR Requirements

- **FR20:** Document ingestion triggers forecast refresh
- **Processing time:** <5 minutes total (AC3)
- **Graceful degradation:** Timeout doesn't block ingestion success

### Testing Strategy

Per `docs/process/definition-of-done.md`:
- New code must have ≥80% test coverage
- Unit tests mock time-series extraction and forecast generation
- Integration tests use test database (port 6335/5433 per Story 4.0.5)
- Performance tests validate 5-minute timeout constraint

### Project Structure Notes

- Forecasting module exists from Stories 4.1 and 4.2 (`raglite/forecasting/`)
- This story adds `auto_update.py` alongside existing `timeseries_extract.py` and `hybrid.py`
- Story 4.4 will add MCP tool `get_financial_forecast()`
- Story 4.5 will add anomaly detection (can use similar post-ingestion hooks)

### Learnings from Previous Story

**From Story 4-2-forecasting-engine-implementation (Status: done)**

- **Forecasting Module Structure:** `raglite/forecasting/` now contains `__init__.py`, `timeseries_extract.py`, `hybrid.py`
- **Core Functions Available:**
  - `generate_forecast()`: Use this for forecast refresh (already implemented)
  - `extract_timeseries()`: Use this to extract data from new documents
  - `explain_forecast()`: Use for LLM reasoning on updated forecasts
- **Pydantic Models Available:**
  - `ForecastPoint`, `ForecastResult` in `raglite/shared/models.py` (lines 347-399)
  - `TimeSeriesPoint`, `TimeSeriesData` for input data
- **LLM Pattern:** Uses Mistral Large (`mistral-large-latest`) - maintain consistency
- **Prophet Minimum Data:** 8 quarters required - auto_update should validate before refresh
- **Coverage Target:** 92.18% achieved on existing code - maintain or exceed
- **ForecastingAgent:** Integrated with orchestrator - can invoke for complex refreshes
- **Integration Tests Deferred:** AC4/AC7 backtesting tests deferred from Story 4.2 - this story can include them if test DB available

[Source: docs/sprint-artifacts/4-2-forecasting-engine-implementation.md#Dev-Agent-Record]

### Dependencies

- **Existing:** `raglite/forecasting/hybrid.py` (`generate_forecast`)
- **Existing:** `raglite/forecasting/timeseries_extract.py` (`extract_timeseries`)
- **Existing:** `raglite/ingestion/document_ingestion.py` (ingestion pipeline)
- **No new libraries required** - uses existing Prophet and Mistral Large

### References

- [Tech Spec: Epic 4 Section 6](docs/archive/tech-spec-epic-4.md#6-implementation-timeline) - Story 4.3 in Week 9-10
- [Epic 4 PRD: Story 4.3](docs/prd/epic-4-forecasting-proactive-insights.md#story-43-automated-forecast-updates)
- [Architecture: Document Segregation](docs/architecture/document-segregation-strategy.md) - Document metadata patterns
- [Definition of Done](docs/process/definition-of-done.md)
- [Previous Story: 4-2](docs/sprint-artifacts/4-2-forecasting-engine-implementation.md)

## Dev Agent Record

### Context Reference

- `docs/sprint-artifacts/4-3-automated-forecast-updates.context.xml` (Generated 2025-11-26)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-11-26 | SM (Bob) | Story drafted from Epic 4 PRD and Tech Spec in YOLO mode |
