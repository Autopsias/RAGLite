# Sprint Change Proposal: SCP-2025-12-24-001

## Demand-Side Regressors for Cement Industry Forecasting

**Status:** APPROVED
**Date:** 2025-12-24
**Requested By:** Ricardo Carvalho
**Approved By:** Ricardo Carvalho
**SM Facilitator:** Bob (Scrum Master Agent)

---

## Change Summary

| Aspect | Details |
|--------|---------|
| **Change Type** | Direct Adjustment (Option 1) |
| **Affected Epic** | Epic 7b - Intelligent Model Selection Framework |
| **New Story** | 7b-7: Demand-Side Regressors for Cement Industry |
| **Priority** | P0 |
| **Effort** | 2 days |
| **Impact** | Critical accuracy fix for EBITDA and sales forecasts |

---

## Trigger Event

During MCP interaction (2025-12-24), user requested EBITDA forecast for 2026. The model returned:
- **Forecast:** -2% growth for 2026
- **Market Reality:** Portugal construction +2.5%, building permits +14% YoY
- **Contradiction:** Portugal represents 72% of Secil Group EBITDA

Upon investigation, the root cause was identified:

> "The ensemble forecast uses only cost-side regressors: Euribor 3M, TTF gas, diesel, API2 coal. It has zero demand-side inputs."

---

## Problem Statement

### Current State

```python
# raglite/forecasting/regressor_config.py:136
"ebitda": ["euribor_3m", "ttf_gas", "diesel", "api2_coal"]  # ALL COST-SIDE
```

### Impact

| Metric | Current MAPE | Forecast Direction | Market Direction |
|--------|--------------|-------------------|------------------|
| EBITDA | 487% | -2% growth | +2.5% growth |
| sales_volume | 27% | Flat | Growing |

The model is **blind to demand signals** that drive the majority of the business.

---

## Approved Solution

### Story 7b-7: Demand-Side Regressors

**Acceptance Criteria:**
1. Add `fetch_housing_transactions()` to EurostatClient (prc_hpi_inx)
2. Add `fetch_dwelling_completions()` to EurostatClient
3. Implement quarterly-to-monthly interpolation
4. Add regressors to `AVAILABLE_REGRESSORS`
5. **Update EBITDA mapping** to include demand indicators
6. Update sales_volume, revenue, turnover mappings
7. Backfill historical data (2018-present)
8. Unit tests with >80% coverage
9. Validation shows improved MAPE

### Key Code Change

```python
# BEFORE (cost-only):
"ebitda": ["euribor_3m", "ttf_gas", "diesel", "api2_coal"]

# AFTER (cost + demand):
"ebitda": [
    "construction_output",
    "building_permits",
    "construction_confidence",
    "housing_transactions",  # NEW
    "ttf_gas",
    "diesel",
]
```

---

## Files Affected

| File | Action | Lines |
|------|--------|-------|
| `raglite/external_data/clients/eurostat.py` | Add fetchers | +120 |
| `raglite/external_data/models.py` | Add models | +30 |
| `raglite/forecasting/regressor_config.py` | Update mappings | +20 |
| `raglite/forecasting/regressor_fetch.py` | Add interpolation | +60 |
| `tests/unit/test_housing_transactions.py` | Create | +100 |
| `tests/integration/test_demand_regressors.py` | Create | +80 |
| `docs/stories/7b-7-demand-side-regressors.md` | Create | +600 |
| `docs/sprint-status.yaml` | Update | +2 |

**Total New Code:** ~410 lines

---

## Expected Outcomes

| Metric | Before | After (Expected) |
|--------|--------|------------------|
| EBITDA MAPE | 487% | <50% |
| EBITDA Direction | -2% | +1-3% |
| sales_volume MAPE | 27% | <15% |
| Demand Signal Coverage | 0% | 60%+ |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Eurostat API changes | Low | Medium | Fallback to cached data |
| Interpolation artifacts | Low | Low | Validate against quarterly values |
| Overfitting with new regressors | Medium | Medium | CV validation in model selection |

---

## Timeline

| Day | Tasks |
|-----|-------|
| Day 1 | Tasks 1-4: Data models, fetchers, interpolation |
| Day 2 | Tasks 5-10: Configuration updates, tests, validation |

---

## Approval Chain

- [x] SM Analysis (Bob) - 2025-12-24
- [x] User Approval (Ricardo) - 2025-12-24
- [ ] Implementation - Pending
- [ ] Validation - Pending
- [ ] MCP Re-test - Pending

---

## Artifacts Created

1. **Story File:** `docs/stories/7b-7-demand-side-regressors.md`
2. **Sprint Status:** Updated with `7b-7-demand-side-regressors: drafted`
3. **This SCP:** `docs/sprint-artifacts/scp-2025-12-24-demand-regressors.md`

---

## Post-Implementation Validation

```bash
# 1. Verify EBITDA forecast direction
uv run python -c "
import asyncio
from raglite.forecasting.hybrid import generate_forecast
result = asyncio.run(generate_forecast('ebitda', periods_ahead=12))
print(f'EBITDA trend: {result}')
"

# 2. Run full validation
uv run python scripts/validate_forecasting_unified.py --full

# 3. Re-test via MCP
# Ask Claude Desktop: "Forecast EBITDA for 2026 for Secil"
# Expected: +1-3% growth (aligned with Portugal construction market)
```

---

## Change Log

| Date | Action | Actor |
|------|--------|-------|
| 2025-12-24 10:00 | Issue identified via MCP interaction | Ricardo |
| 2025-12-24 10:15 | Correct-course workflow initiated | Bob (SM) |
| 2025-12-24 10:30 | Root cause analysis completed | Bob (SM) |
| 2025-12-24 10:45 | Change proposal drafted | Bob (SM) |
| 2025-12-24 11:00 | **APPROVED** | Ricardo |
| 2025-12-24 11:05 | Story 7b-7 created | Bob (SM) |
