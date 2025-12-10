# Epic 6 Baseline Accuracy Report (BEFORE Model Enhancement)

**Generated:** 2025-12-10
**Purpose:** Capture baseline metrics BEFORE implementing Stories 6.12-6.14
**Source:** Stories 6.7, 6.10, 6.11 validation results (2025-12-08 to 2025-12-09)

---

## Executive Summary

| Model | MAPE | Status | Notes |
|-------|------|--------|-------|
| **Epic 4 Prophet (univariate)** | 15.0% | Baseline | NFR target |
| **Story 6.7 Prophet (multivariate)** | **9.0%** | ✅ Cement demand | 40% improvement |
| **Story 6.10 Prophet (multivariate)** | **2.05%** | ✅ 8/8 variables | **97% improvement** |
| **Story 6.11 Ensemble (MCP)** | **2.2%** | ✅ 8/8 variables | ~21s per variable |

**Key Result:** Multi-variate Prophet with real external regressors achieves **2.05% average MAPE** across 8 cement industry variables - a **97% improvement** over univariate baseline.

---

## Validated Results - Story 6.10 (2025-12-09)

### 12-Variable Cement Industry Forecasting

**Test Command:**
```bash
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data
```

**Summary:**
- **Passed:** 8/8 DB-backed variables (100%)
- **Skipped:** 4/12 (external-only, no SQL data)
- **Failed:** 0/8

| Variable | Target | Baseline MAPE | Multi-var MAPE | Improvement | Status |
|----------|--------|---------------|----------------|-------------|--------|
| **Revenue** | <5.0% | 51.5% | **2.8%** | 94.6% | ✅ PASS |
| **EBITDA** | <5.0% | 131.6% | **2.5%** | 98.1% | ✅ PASS |
| **Sales Volume** | <5.0% | 119.8% | **0.8%** | 99.3% | ✅ PASS |
| **Electricity Cost** | <8.0% | 85.2% | **3.0%** | 96.5% | ✅ PASS |
| **Thermal Energy Cost** | <10.0% | 54.0% | **2.6%** | 95.2% | ✅ PASS |
| **Variable Cost/Ton** | <8.0% | 72.3% | **0.7%** | 99.0% | ✅ PASS |
| **Avg Selling Price** | <6.0% | 63.6% | **1.6%** | 97.5% | ✅ PASS |
| **Capacity Utilization** | <10.0% | 133.6% | **2.5%** | 98.1% | ✅ PASS |
| Pet Coke Price | <12.0% | N/A | N/A | - | ⏭️ SKIP |
| Natural Gas (TTF) | <12.0% | N/A | N/A | - | ⏭️ SKIP |
| CO2 EUA Price | <15.0% | N/A | N/A | - | ⏭️ SKIP |
| Clinker Factor | <8.0% | N/A | N/A | - | ⏭️ SKIP |

**Aggregate Metrics:**
- **Average Baseline MAPE:** 88.96%
- **Average Multi-var MAPE:** 2.05%
- **Average Improvement:** 97.3%

---

## Validated Results - Story 6.11 MCP Ensemble (2025-12-09)

### MCP Multi-Variate Forecasting Interface

**Test Command:**
```bash
uv run python scripts/validate-mcp-ensemble-forecasting.py
```

**Summary:**
- **Passed:** 8/8 (100%)
- **Total Execution Time:** 751.5s
- **Average per Variable:** ~21s (Prophet mode)

| Variable | Target | Prophet MAPE | Execution Time | Status |
|----------|--------|--------------|----------------|--------|
| **Revenue** | <5.0% | **2.81%** | 21.5s | ✅ PASS |
| **EBITDA** | <5.0% | **3.56%** | 20.5s | ✅ PASS |
| **Sales Volume** | <5.0% | **0.93%** | 19.6s | ✅ PASS |
| **Electricity Cost** | <8.0% | **2.96%** | 29.7s | ✅ PASS |
| **Thermal Energy Cost** | <10.0% | **2.60%** | 17.3s | ✅ PASS |
| **Variable Cost** | <8.0% | **0.66%** | 16.8s | ✅ PASS |
| **Avg Selling Price** | <6.0% | **1.56%** | 19.9s | ✅ PASS |
| **Capacity Utilization** | <10.0% | **2.53%** | 21.6s | ✅ PASS |

**Model Selection Intelligence (Story 6.11.6):**
- Default: Prophet Multi-Variate (~21s, ~2.2% MAPE)
- Ensemble (4 models): ~78s (3.7x slower), similar accuracy
- Ensemble provides robustness through model diversity, not significant accuracy gain

---

## Validated Results - Story 6.7 (2025-12-08)

### Cement Demand Ground Truth Validation

**Test Command:**
```bash
uv run python scripts/validate-epic6-accuracy.py
```

**Ground Truth:**
- **File:** `tests/ground_truth/cement_demand_2020_2024.csv`
- **Period:** Jan 2020 - Dec 2024 (60 months)
- **Split:** 48 months training, 12 months testing

**Results:**
- **MAPE:** 9.0%
- **Baseline:** 15.0% (Epic 4 univariate)
- **Improvement:** 40%
- **Regressors Used:** building_permits (INE indicator 0012096)
- **Model Type:** prophet_multivariate
- **Decision Gate:** ✅ **APPROVED** (MAPE ≤ 10%)

---

## Current Ensemble Configuration

| Model | Weight | Status |
|-------|--------|--------|
| Prophet (multivariate) | 35-40% | ✅ Active |
| Linear Regression | 30% | ✅ Active |
| XGBoost | 15% | ✅ Active |
| LightGBM | 15% | ✅ Active |

**Total Models:** 4
**Weights:** Static (configured in settings)

---

## External Data Sources Status

| Source | Status | Records | Use Case |
|--------|--------|---------|----------|
| **BPstat EURIBOR** | ✅ OK | 83 | Financial metrics |
| **ICE API2 Coal** | ✅ OK | 751 | Energy costs |
| **ICE TTF Gas** | ✅ OK | 752 | Energy costs |
| **EU Oil Bulletin (Diesel)** | ✅ OK | - | Transport costs |
| **Eurostat Electricity** | ✅ OK | 5 | Energy costs |
| **OMIE Electricity** | ✅ OK | 1071 | Spot prices |
| INE Building Permits | ❌ FAILED | - | Wrong indicator |

**Working Regressors for Validation:**
- `euribor_3m` - ECB 3-month EURIBOR
- `diesel` - EU Oil Bulletin diesel prices
- `ttf_gas` - ICE TTF natural gas
- `api2_coal` - ICE API2 coal prices
- `eurostat_electricity` - Eurostat industrial electricity

---

## Success Criteria for Stories 6.12-6.14

| Metric | Current Baseline | Target | Notes |
|--------|------------------|--------|-------|
| **Average MAPE** | 2.05% | ≤ 2.05% | Must not regress |
| **8-variable pass rate** | 100% | 100% | Must maintain |
| **Cold-start (<6 points)** | FAILS | WORKS | Chronos-2 |
| **Models in Ensemble** | 4 | 6 | +CatBoost, +Chronos-2 |
| **Weight Strategy** | Static | Adaptive | Backtest-driven |
| **TFT** | N/A | Operational | Training workflow |

---

## Testing Methodology (CRITICAL - From Stories 6.10/6.11)

### Why Multi-Variate Works

**Key Discovery:** Entity normalization + correct regressor alignment was critical:
- Story 6.10.1: Integrated `normalize_entity()` into SQL extraction
- Story 6.10.5: Replaced broken INE regressors with working alternatives
- Story 6.11: Exposed multi-variate to MCP interface

### Working Regressors by Variable Type

| Variable Type | Regressors Used |
|--------------|-----------------|
| **Financial** (Revenue, EBITDA) | euribor_3m, diesel, ttf_gas, api2_coal |
| **Energy** (Electricity, Thermal) | eurostat_electricity, ttf_gas, api2_coal |
| **Production** (Volume, Capacity) | euribor_3m, diesel, ttf_gas |
| **Pricing** (Avg Selling Price) | diesel, euribor_3m, ttf_gas |

### APIs with Historical Data (USE FOR VALIDATION)

| API | Historical Range | Use Case |
|-----|------------------|----------|
| **ICE API2 Coal** | 751 days | ✅ Energy costs |
| **ICE TTF Gas** | 752 days | ✅ Energy costs |
| **BPstat EURIBOR** | 2018-2025 | ✅ Financial metrics |
| **Eurostat Electricity** | 2020+ | ✅ Industrial prices |

### Validation Script Reference

```bash
# 12-variable cement forecasting validation
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data

# MCP multi-variate validation
uv run python scripts/validate-mcp-multivariate-forecasting.py

# MCP ensemble validation
uv run python scripts/validate-mcp-ensemble-forecasting.py

# Epic 6 accuracy (cement demand ground truth)
uv run python scripts/validate-epic6-accuracy.py
```

---

## Implementation History

| Date | Story | Change | Result |
|------|-------|--------|--------|
| Epic 4 | 4.2 | Prophet univariate | 15.0% MAPE baseline |
| 2025-12-05 | 6.3 | Prophet multivariate | ~12% initial |
| 2025-12-08 | 6.7 | Validation + fixes | **9.0% MAPE** (40% improvement) |
| 2025-12-09 | 6.10 | Entity normalization + regressor fixes | **2.05% avg MAPE** (97% improvement) |
| 2025-12-09 | 6.11 | MCP multi-variate interface | **8/8 PASS** via MCP |
| 2025-12-10 | 6.12-6.14 | Enhanced ensemble | TBD |

---

## Key Fixes That Enabled 97% Improvement

### Story 6.7 Fixes
1. **Monthly frequency output** - `frequency='M'` returns monthly forecasts directly
2. **YoY% auto-transformation** - Converts YoY% to index values before use as regressors
3. **Pre-selection transformation** - Transforms YoY% before correlation calculation

### Story 6.10 Fixes
1. **Entity normalization** - Integrated `normalize_entity()` into SQL extraction
2. **API timeouts** - Increased test timeouts from 1s to 10s
3. **ECB attribute fix** - `d.rate` → `d.rate_pct`
4. **Alternative regressors** - Replaced broken INE with working ICE/Eurostat
5. **Local file caching** - 24-hour TTL for external data

### Story 6.11 Features
1. **MCP interface** - `use_external_regressors=True` by default
2. **Auto-regressor selection** - Based on metric type
3. **Model selection intelligence** - Prophet vs Ensemble routing

---

*Validated by: Stories 6.7, 6.10, 6.11 (2025-12-08 to 2025-12-09)*
*Sprint Change Proposal: SCP-2025-12-10-001*
