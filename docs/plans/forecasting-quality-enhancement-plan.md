# Forecasting Quality Enhancement Plan

**Created:** 2025-12-17
**Status:** Ready for Implementation
**Estimated Effort:** 7-10 hours

## Overview

Implement Forecast Quality Score (FQS), investigate data issues, add Sales Volume regressors, and expose multi-metric validation via MCP.

**Scope:** 5 work streams in priority order

---

## Work Stream 1: FQS Implementation (Priority: HIGH)

### Goal
Create a single composite metric (0-100 scale) combining MAPE and MASE for actionable quality assessment.

### Research-Based Weighting Decision

**Source:** Rob J. Hyndman (creator of MASE), "Another Look at Measures of Forecast Accuracy" (2006)

**Key finding:** *"We propose that the mean absolute scaled error become the standard measure for comparing forecast accuracy across multiple time series."*

**Why MASE should dominate:**
- MAPE is undefined when actuals are zero (common in financial data)
- MAPE gives misleading results with small values (e.g., EBITDA after YTD conversion)
- MASE is scale-free and comparable across all variables
- MASE answers the key question: "Does model add value vs doing nothing?"

### Formula (Research-Backed)
```python
FQS = 100 × [0.35 × A_MAPE + 0.65 × A_MASE]
Where:
  A_MAPE = max(0, 1 - MAPE/100)  # Accuracy from MAPE (capped at 100%)
  A_MASE = max(0, 1 - MASE/2)    # Accuracy from MASE (naïve baseline = 0)

Weights: 35% MAPE / 65% MASE
  - MASE dominates per Hyndman recommendation
  - MAPE retained for executive-friendly interpretation
```

### Changes Required

**File 1: `raglite/forecasting/validation_methods.py`**
- Add `calculate_fqs(mape, mase, w_mape=0.35, w_mase=0.65) -> float` function after line 348
- Add `calculate_system_fqs(results, exclude_exempt=True) -> dict` for aggregation

**File 2: `raglite/forecasting/validation_schema.py`**
- Add `fqs: float | None = None` to `MultiMetricValues` (line 36)
- Add `average_fqs: float | None = None` to `UnifiedValidationResult` (line 148)
- Add `controllable_fqs: float | None = None` to `QualityGateResult` (line 75)

**File 3: `scripts/validate_forecasting_unified.py`**
- Call `calculate_fqs()` in `run_unified_validation()` loop (line 974)
- Add FQS to summary aggregation (line 1087)

**File 4: `raglite/forecasting/report_generator.py`**
- Add FQS column to variable assessment table (line 250)
- Add FQS ranking section to cross-variable analysis (line 614)
- Add FQS summary to executive summary (line 232)

### Tests
- `tests/unit/test_fqs_calculation.py` - Unit tests for FQS formula
- Update `tests/unit/test_multi_metric_validation.py` with FQS assertions

---

## Work Stream 2: MCP Integration Verification & Enhancement (Priority: HIGH)

### Verification Result: Improvements ARE Automatically Applied

**Confirmed:** When you query "What's the EBITDA for 2026?" via MCP, the improved model IS used.

**Data Flow Verified:**
1. `get_financial_forecast` MCP tool (main.py:1620)
2. → Calls `fetch_regressors_for_metric()` with auto-selection from `regressor_config.py`
3. → Calls `generate_forecast()` from `hybrid.py` (same function as validation)
4. → Returns forecast with `regressors_used`, `model_type`, `accuracy_metrics`

**Key Finding:** Both validation script AND MCP tool call the **same** `generate_forecast()` function with identical parameters. Any improvement to:
- `regressor_config.py` (new regressors) → Auto-applies to MCP
- `hybrid.py` (model improvements) → Auto-applies to MCP
- `validation_methods.py` (metrics) → Auto-applies to MCP
- `timeseries_extract.py` (data quality) → Auto-applies to MCP

### Remaining Gap: Metric Visibility
MASE, SMAPE, Bias, FQS are calculated internally but **NOT exposed in MCP response**. Users only see MAPE.

### Changes Required

**File 1: `raglite/retrieval/models.py`**
- Extend `VariableValidationDetail` with multi-metric fields:
```python
actual_mase: Optional[float] = None
actual_smape: Optional[float] = None
actual_bias: Optional[float] = None
fqs: Optional[float] = None
primary_metric_used: str = "mape"
mase_only_pass: bool = False
```

- Extend `ValidationResponse` summary:
```python
average_mase: Optional[float] = None
average_fqs: Optional[float] = None
controllable_mase: Optional[float] = None
controllable_fqs: Optional[float] = None
```

**File 2: `raglite/main.py`**
- Update `validate_forecasting_accuracy` tool (line 3339)
- Map `UnifiedValidationResult` multi-metrics to `ValidationResponse`
- Include per-variable MASE, SMAPE, Bias, FQS in response

**File 3: `raglite/retrieval/models.py`**
- Extend `ForecastQueryResponse.accuracy_metrics` to include MASE

### Tests
- Update `tests/e2e/test_mcp_forecasting.py` to verify multi-metric response

---

## Work Stream 3: Sales Volume Bias Investigation (Priority: MEDIUM)

### Problem
- MAPE 27.16% vs 10% target (FAIL)
- MASE 0.48 (excellent - beats naïve by 52%)
- Bias -52.2 (systematic under-prediction)

### Root Cause
Model follows correct trend but has systematic bias. Adding construction sentiment regressor should help capture market conditions affecting cement demand.

### User Decision: Add regressor only (keep 10% MAPE target)

### Changes Required

**File 1: `raglite/forecasting/regressor_config.py`**
- Update `METRIC_REGRESSORS["sales_volume"]` (line 135):
```python
"sales_volume": [
    "construction_output",      # Existing - production activity
    "building_permits",         # Existing - leading indicator
    "construction_confidence",  # NEW - market sentiment indicator
    "euribor_3m",              # Existing - financing cost
    "industrial_production",    # Existing - economic activity
],
```

**Rationale for construction_confidence:**
- EC Business Survey indicator (balance %)
- Leading indicator of construction market sentiment
- Already fetched via Eurostat in `regressor_fetch.py`
- Correlates with cement demand decisions

### Validation
- Run `uv run python scripts/validate_forecasting_unified.py`
- Verify Sales Volume bias improves (currently -52.2)
- Target: Reduce bias to < -30, improve MAPE toward 15%

---

## Work Stream 4: Electricity Cost Data Audit (Priority: HIGH - RUN FIRST)

### Problem
- MAPE 121.57%, MASE 6.11 (worst performer)
- Only 19 data points with 38.6-month max gap
- Marked as data_quality_exempt

### User Decision: Run audit FIRST before any implementation

### Investigation Steps (Database Audit - Execute Immediately)

```sql
-- 1. Count all electricity-related rows by metric name
SELECT metric, COUNT(*) as row_count FROM financial_tables
WHERE metric ILIKE '%electr%' GROUP BY metric ORDER BY row_count DESC;

-- 2. Check entity distribution
SELECT entity, COUNT(*) as row_count FROM financial_tables
WHERE metric ILIKE '%electr%' GROUP BY entity ORDER BY row_count DESC;

-- 3. Check period coverage
SELECT MIN(period), MAX(period), COUNT(DISTINCT period) FROM financial_tables
WHERE metric ILIKE '%electr%';

-- 4. Sample actual data
SELECT metric, entity, period, value FROM financial_tables
WHERE metric ILIKE '%electr%' ORDER BY period DESC LIMIT 50;
```

### Potential Fixes (Based on Audit Results)

**If more data exists with different metric names:**
- Update `db_metric_aliases` in `raglite/forecasting/data_quality/config.py` (line 236)

**If data exists for other entities:**
- Relax entity filter from `portugal` exact match to ILIKE

**File: `raglite/forecasting/timeseries_extract.py`**
- Lines 1569-1571: Review entity filters for electricity

---

## Work Stream 5: EBITDA Documentation (Priority: LOW)

### Finding
The DigDeep investigation revealed: **There is no regression.** The Dec 16 "2.72% MAPE" was a BUG that showed incorrect value. The current 84.77% MAPE with MASE 0.58 is CORRECT behavior for YTD-converted volatile data.

### Rationale
- MASE 0.58 = model beats naïve by 42% (excellent skill)
- High MAPE is mathematical artifact of small monthly values after YTD conversion
- System correctly uses `allow_mase_only_pass=True` and `primary_metric="mase"`
- Variable PASSES validation via MASE-only criteria

### No Code Changes Required
- EBITDA is working correctly
- Documentation update only (optional)

---

## Implementation Order

| Phase | Work Stream | Effort | Dependencies |
|-------|-------------|--------|--------------|
| **0** | **Electricity Cost Data Audit** | 30 min | **RUN FIRST - inform fixes** |
| 1 | FQS Implementation | 2-3 hours | None |
| 2 | MCP Multi-Metric Exposure | 2-3 hours | Phase 1 (FQS) |
| 3 | Sales Volume Regressors | 1 hour | None |
| 4 | Electricity Cost Fixes (if needed) | 1-2 hours | Phase 0 audit results |
| 5 | EBITDA Documentation | 30 min | None |

**Total Estimated Effort:** 7-10 hours

### Phase 0: Electricity Audit (FIRST)
Run SQL queries immediately to determine:
1. How many total electricity rows exist
2. What metric names are used (for alias expansion)
3. What entities contain data (for filter tuning)
4. Whether more data exists that we're not capturing

---

## Critical Files Summary

| File | Changes |
|------|---------|
| `raglite/forecasting/validation_methods.py` | Add FQS calculation |
| `raglite/forecasting/validation_schema.py` | Add FQS fields to schemas |
| `raglite/forecasting/report_generator.py` | Add FQS to reports |
| `raglite/retrieval/models.py` | Extend MCP response schemas |
| `raglite/main.py` | Expose multi-metrics via MCP |
| `raglite/forecasting/regressor_config.py` | Add construction_confidence to sales_volume |
| `scripts/validate_forecasting_unified.py` | Integrate FQS into validation |

---

## Success Criteria

1. **FQS Available:** New composite metric calculated for all variables
2. **MCP Exposure:** MASE, FQS, Bias visible in MCP validation responses
3. **MCP Forecasts:** Improvements auto-apply when querying forecasts
4. **Sales Volume:** Bias reduced with construction_confidence regressor
5. **Electricity Cost:** Data audit completed, root cause documented
6. **All Tests Pass:** Unit, integration, and E2E tests green

---

## Validation Commands

```bash
# Run validation after changes
uv run python scripts/validate_forecasting_unified.py

# Check FQS in report
cat reports/validation-report-*.md | grep -A5 "FQS"

# Test MCP endpoint
# Use Claude.ai or MCP client to call validate_forecasting_accuracy

# Test forecast query
# Query: "What is the EBITDA forecast for 2026?"
# Verify regressors_used and accuracy_metrics in response
```

---

## Quick Start for New Session

```bash
# 1. Start with Electricity Audit
docker exec raglite-postgresql psql -U raglite -d raglite -c "
SELECT metric, COUNT(*) as row_count FROM financial_tables
WHERE metric ILIKE '%electr%' GROUP BY metric ORDER BY row_count DESC;"

# 2. Then implement FQS
# Edit: raglite/forecasting/validation_methods.py

# 3. Run validation to verify
uv run python scripts/validate_forecasting_unified.py
```
