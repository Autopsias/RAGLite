# Unified Forecasting Improvement Epic

**Date:** 2025-12-12
**Status:** Ready for Story Creation
**Epic:** 7 - Forecasting Accuracy & MCP Integration
**Estimated Effort:** 52 hours
**Expected Outcome:** Variable Cost MAPE from 41% to <8%, all 12 variables passing validation, unified MCP access

---

## Executive Summary

This unified briefing consolidates three related improvement areas into a single coherent epic:

1. **Variable Cost MAPE Reduction** (41.43% → <8%)
2. **External Data Source Expansion** (add 6 new Eurostat/ECB indicators)
3. **Unified Validation & MCP Integration** (single script, all MAPE methods)

**Root Cause:** Variable Cost uses generic macro indicators instead of cement-industry-specific cost drivers, plus broken data sources (INE Building Permits returns death statistics).

**Solution:** Entity-specific data extraction + cement-industry regressors + unified validation framework.

---

## Current State Analysis

### Validation Results (Latest Run)

| Variable | Current MAPE | Target | Status | Issue |
|----------|-------------|--------|--------|-------|
| Revenue | 2.51% | <5% | PASS | - |
| EBITDA | 1.18% | <5% | PASS | - |
| Sales Volume | 4.18% | <5% | PASS | - |
| **Variable Cost** | **41.43%** | <8% | **FAIL** | Entity mixing, wrong regressors |
| Avg Selling Price | N/A | <6% | SKIP | Extraction failed |
| Capacity Utilization | N/A | <10% | SKIP | Extraction failed |
| TTF Gas Price | 5.27% | <12% | PASS | - |
| Diesel Price | 0.12% | <10% | PASS | - |

**Current Pass Rate:** 5/8 variables (target: 10/12)

### Root Cause Analysis (Five Whys)

| Level | Question | Finding |
|-------|----------|---------|
| Why 1 | Why is Variable Cost MAPE at 41%? | Data from multiple entities mixed (Portugal + Tunisia + Brazil) |
| Why 2 | Why are entities mixed? | No entity detection in extraction logic |
| Why 3 | Why no entity detection? | Original design assumed single-entity data |
| Why 4 | Why wrong regressors? | Using generic macro indicators instead of cost drivers |
| Why 5 | Why no construction indicators? | INE Building Permits API broken (wrong indicator ID) |

### Data Quality Issues

| Issue | Impact | Evidence |
|-------|--------|----------|
| Multi-entity mixing | 33% coefficient of variation | Values range -331 to -101 EUR/m³ |
| Mixed currencies | Unit inconsistency | EUR, BRL, TND values combined |
| Mixed units | 10x scale differences | EUR/m³, EUR/ton, thousands |
| Broken INE API | No construction leading indicators | Returns death stats, not permits |
| Wrong regressor set | Low correlation with target | euribor instead of energy costs |

---

## Solution Architecture

### Phase 1: Data Quality (8 hours)

**Goal:** Clean, entity-specific data extraction for Portugal.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Qdrant Chunks │────▶│ Entity Detector │────▶│ Portugal-Only   │
│   (mixed data)  │     │ (PT/TN/BR)      │     │ Time Series     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                        ┌──────┴──────┐
                        ▼             ▼
                   ┌─────────┐   ┌─────────┐
                   │EUR/ton  │   │Validate │
                   │Normalize│   │Range    │
                   └─────────┘   └─────────┘
```

### Phase 2: External Regressors (20 hours)

**Goal:** Add cement-industry-specific cost drivers.

```
┌─────────────────────────────────────────────────────────────────┐
│                    REGRESSOR ECOSYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│ TIER 1 (Working)          │ TIER 2 (New)                        │
│ ✓ TTF Gas (ICE)           │ + Eurostat Construction Output      │
│ ✓ API2 Coal (ICE)         │ + ECB GDP Growth                    │
│ ✓ Diesel (EU Oil Bulletin)│ + ECB HICP Inflation                │
│ ✓ EURIBOR (ECB)           │ + Eurostat Industrial Production    │
│ ✓ Electricity (Eurostat)  │ + EC Construction Confidence        │
│ ✗ Building Permits (INE)  │ + Eurostat Building Permits (backup)│
└─────────────────────────────────────────────────────────────────┘
```

### Phase 3: Unified Validation (12 hours)

**Goal:** Single validation script with all MAPE calculation methods.

```
┌─────────────────────────────────────────────────────────────────┐
│              UNIFIED VALIDATION SCRIPT                          │
├─────────────────────────────────────────────────────────────────┤
│ MAPE Methods:                                                   │
│ ├─ Holdout (last N points as test set)                         │
│ ├─ Walk-Forward (expanding window)                             │
│ ├─ Cross-Validation (k-fold on time series)                    │
│ └─ Confidence Interval (fallback estimate)                     │
│                                                                 │
│ Variables: 12 (financial + external)                           │
│ Models: 7 + ensemble                                            │
│ Output: JSON report + MCP-compatible response                  │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 4: MCP Integration (12 hours)

**Goal:** Expose all forecasting functionality via MCP tools.

```
MCP Tools:
├── get_financial_forecast (existing, enhanced)
│   ├── Add: prefer_entity="Portugal" parameter
│   ├── Add: validation_method="holdout|walkforward|cv" parameter
│   └── Add: include_accuracy=True returns MAPE with forecast
│
├── validate_forecasting_accuracy (new)
│   ├── Run validation for specified metrics
│   ├── Return per-model MAPE comparison
│   └── Include recommendations
│
├── list_available_regressors (new)
│   ├── Show all available external indicators
│   ├── Include correlation with target metrics
│   └── Show data availability status
│
└── get_regressor_data (new)
    ├── Fetch specific regressor time series
    ├── Support date range filtering
    └── Return as structured data
```

---

## Story Breakdown

### Story 7.1: Entity-Specific Variable Cost Extraction
**Effort:** 4 hours | **Priority:** P0 (Critical)

**Description:**
Implement entity detection in Variable Cost extraction to filter Portugal-only data and normalize to EUR/ton.

**Acceptance Criteria:**
- [ ] AC1: Entity detection identifies Portugal/Tunisia/Brazil context with >95% accuracy
- [ ] AC2: Portugal-only extraction produces <15% coefficient of variation (vs 33% current)
- [ ] AC3: Values normalized to EUR/ton (range validation: -150 to -350)
- [ ] AC4: Variable Cost MAPE improves to <25% (from 41%)
- [ ] AC5: No regression in other metric extraction

**Files to Modify:**
- `raglite/forecasting/timeseries_extract.py` - Add entity detection and filtering
- `tests/integration/test_variable_cost_extraction.py` - New validation tests

**Entity Detection Patterns:**
```python
ENTITY_PATTERNS = {
    "Portugal": ["Portugal", "PT", "Custos Variáveis", "EUR/ton"],
    "Tunisia": ["Tunisia", "TN", "TND", "Tunisie"],
    "Brazil": ["Brazil", "BR", "BRL", "Brasil"],
}
```

---

### Story 7.2: Add Eurostat Construction & Industrial Indicators
**Effort:** 8 hours | **Priority:** P1 (High)

**Description:**
Extend Eurostat client with construction output index and industrial production index - both high-correlation leading indicators for cement demand.

**Acceptance Criteria:**
- [ ] AC1: `fetch_construction_output()` returns monthly index for Portugal (2020-2025)
- [ ] AC2: `fetch_industrial_production()` returns monthly index for Portugal
- [ ] AC3: Both indicators show >0.3 correlation with sales_volume
- [ ] AC4: Data has <10% missing values over analysis period
- [ ] AC5: Unit tests verify parsing and data quality

**API Reference:**
```
Eurostat SDMX API:
- sts_copr_m: Construction production index
- sts_inpr_m: Industrial production index

Example request:
GET /data/sts_copr_m?geo=PT&unit=I21&s_adj=SCA&nace_r2=F&format=JSON
```

**Data Models:**
```python
@dataclass
class ConstructionOutputData:
    date: date
    index_value: float  # Index, 2021=100
    country: str
    nace_activity: str  # F (construction), F41 (buildings)

@dataclass
class IndustrialProductionData:
    date: date
    index_value: float  # Index, 2021=100
    country: str
    nace_sector: str  # B-D (mining, manufacturing, utilities)
```

---

### Story 7.3: Add ECB Macroeconomic Indicators
**Effort:** 4 hours | **Priority:** P1 (High)

**Description:**
Extend ECB client with GDP growth rate and HICP inflation - macro indicators that affect construction demand and pricing.

**Acceptance Criteria:**
- [ ] AC1: `fetch_gdp_growth()` returns quarterly YoY growth for Portugal
- [ ] AC2: `fetch_inflation()` returns monthly HICP for Portugal
- [ ] AC3: Quarterly GDP interpolated to monthly for regressor alignment
- [ ] AC4: Unit tests verify ECB SDW parsing

**API Reference:**
```
ECB Statistical Data Warehouse:
- MNA: National accounts (GDP growth)
- ICP: HICP inflation

Example request:
GET /data/MNA/Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N?format=jsondata
```

---

### Story 7.4: Fix INE Building Permits API
**Effort:** 4 hours | **Priority:** P1 (High)

**Description:**
Fix the INE Building Permits indicator ID (currently returns death statistics) and add Eurostat backup.

**Current Bug:**
```python
# BROKEN - returns death statistics
BUILDING_PERMITS_INDICATOR = "0008145"

# FIX - correct indicator
BUILDING_PERMITS_INDICATOR = "0010099"  # Licenciamento de obras
```

**Acceptance Criteria:**
- [ ] AC1: INE building permits returns construction data (not death statistics)
- [ ] AC2: Eurostat building permits added as backup source
- [ ] AC3: Fallback logic: try INE first, use Eurostat if INE fails
- [ ] AC4: Validation shows >0.3 correlation with sales_volume

---

### Story 7.5: Add EC Construction Confidence Index
**Effort:** 6 hours | **Priority:** P2 (Medium)

**Description:**
Create new client for European Commission Business Surveys to fetch construction confidence indicator.

**Acceptance Criteria:**
- [ ] AC1: New `ECBusinessSurveysClient` created
- [ ] AC2: `fetch_construction_confidence()` returns monthly indicator for Portugal
- [ ] AC3: Indicator components (order books, employment expectations) available
- [ ] AC4: Integration test verifies data quality

**Data Model:**
```python
@dataclass
class ConstructionConfidenceData:
    date: date
    confidence_index: float  # Balance %, typically -50 to +50
    order_books: float  # Sub-indicator
    employment_expectations: float  # Sub-indicator
    country: str
```

---

### Story 7.6: Update Regressor Configuration for Cement Industry
**Effort:** 4 hours | **Priority:** P1 (High)

**Description:**
Update regressor mappings to use cement-industry-specific indicators instead of generic macro data.

**New Regressor Mappings:**
```python
METRIC_REGRESSORS = {
    # Financial - demand-driven
    "revenue": ["construction_output", "gdp_growth", "euribor_3m"],
    "sales_volume": ["construction_output", "building_permits", "gdp_growth"],

    # Costs - energy-driven
    "variable_cost": ["ttf_gas", "api2_coal", "industrial_production", "diesel"],
    "electricity_cost": ["eurostat_electricity", "industrial_production"],
    "thermal_cost": ["api2_coal", "ttf_gas", "industrial_production"],

    # Pricing - mixed drivers
    "avg_selling_price": ["construction_confidence", "gdp_growth", "inflation"],
    "capacity_utilization": ["construction_output", "gdp_growth", "industrial_production"],
}
```

**Acceptance Criteria:**
- [ ] AC1: All 6 new regressors registered in AVAILABLE_REGRESSORS
- [ ] AC2: METRIC_REGRESSORS updated with optimal mappings per variable
- [ ] AC3: Correlation analysis confirms >0.3 correlation for selected regressors
- [ ] AC4: Variable Cost MAPE improves to <15% with new regressors

---

### Story 7.7: Unified Validation Script
**Effort:** 8 hours | **Priority:** P1 (High)

**Description:**
Create a single unified validation script that consolidates all MAPE calculation methods and supports all 12 variables.

**Features:**
- All MAPE calculation methods (holdout, walk-forward, confidence interval)
- All 12 cement industry variables
- All 7 models + ensemble
- JSON export for programmatic access
- MCP-compatible output format

**Command Interface:**
```bash
# Full validation
python scripts/validate-forecasting-unified.py --full

# Single variable
python scripts/validate-forecasting-unified.py --variable variable_cost

# Specific MAPE method
python scripts/validate-forecasting-unified.py --mape-method walkforward

# Model comparison
python scripts/validate-forecasting-unified.py --model-comparison

# Export for MCP
python scripts/validate-forecasting-unified.py --export-json --mcp-format
```

**Acceptance Criteria:**
- [ ] AC1: Single script validates all 12 variables
- [ ] AC2: Supports holdout, walk-forward, and CV MAPE methods
- [ ] AC3: JSON output includes per-model breakdown
- [ ] AC4: MCP-format output ready for tool integration
- [ ] AC5: Runtime <10 minutes for full validation

---

### Story 7.8: MCP Validation Tool Integration
**Effort:** 6 hours | **Priority:** P2 (Medium)

**Description:**
Add new MCP tools for forecasting validation and regressor management.

**New MCP Tools:**

```python
@mcp.tool()
async def validate_forecasting_accuracy(
    metrics: list[str] | None = None,
    mape_method: str = "holdout",
    include_model_breakdown: bool = True,
) -> ValidationResponse:
    """Run forecasting validation and return accuracy metrics.

    Args:
        metrics: Specific metrics to validate (None = all 12)
        mape_method: "holdout", "walkforward", or "cv"
        include_model_breakdown: Include per-model MAPE comparison

    Returns:
        ValidationResponse with MAPE results and recommendations
    """

@mcp.tool()
async def list_available_regressors(
    metric: str | None = None,
    include_correlation: bool = True,
) -> RegressorListResponse:
    """List external regressors available for forecasting.

    Args:
        metric: Filter regressors by target metric
        include_correlation: Include correlation with target

    Returns:
        List of regressors with availability and correlation info
    """

@mcp.tool()
async def get_regressor_data(
    regressor: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> RegressorDataResponse:
    """Fetch specific regressor time series data.

    Args:
        regressor: Name of regressor (e.g., "construction_output")
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Time series data with dates and values
    """
```

**Acceptance Criteria:**
- [ ] AC1: `validate_forecasting_accuracy` tool works via MCP
- [ ] AC2: `list_available_regressors` returns all 11 regressors with status
- [ ] AC3: `get_regressor_data` fetches live data from APIs
- [ ] AC4: Enhanced `get_financial_forecast` includes validation metrics

---

### Story 7.9: Variable Cost MAPE Final Validation
**Effort:** 4 hours | **Priority:** P0 (Critical)

**Description:**
Final validation story to confirm Variable Cost MAPE meets target after all improvements.

**Acceptance Criteria:**
- [ ] AC1: Variable Cost MAPE <8% (from 41.43%)
- [ ] AC2: Data coefficient of variation <15% (from 33%)
- [ ] AC3: At least 10/12 variables meet their MAPE targets
- [ ] AC4: Validation script completes in <10 minutes
- [ ] AC5: All MCP tools functional with new data sources

**Validation Command:**
```bash
python scripts/validate-forecasting-unified.py --full --export-json
```

**Expected Results:**
| Variable | Before | After | Target | Status |
|----------|--------|-------|--------|--------|
| Variable Cost | 41.43% | <8% | <8% | PASS |
| All others | varies | maintains | varies | PASS |

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `raglite/external_data/clients/ec_surveys.py` | European Commission Business Surveys client |
| `scripts/validate-forecasting-unified.py` | Unified validation script |
| `tests/integration/test_new_regressors.py` | Integration tests for new indicators |
| `tests/integration/test_variable_cost_extraction.py` | Entity-specific extraction tests |

### Modified Files

| File | Changes |
|------|---------|
| `raglite/forecasting/timeseries_extract.py` | Add entity detection for Portugal |
| `raglite/forecasting/regressor_config.py` | Add new regressors, update mappings |
| `raglite/forecasting/regressor_fetch.py` | Add fetch logic for new regressors |
| `raglite/external_data/clients/eurostat.py` | Add construction_output, industrial_production |
| `raglite/external_data/clients/ecb.py` | Add gdp_growth, inflation |
| `raglite/external_data/clients/ine.py` | Fix building permits indicator ID |
| `raglite/main.py` | Add new MCP tools |

---

## Expected MAPE Improvements

| Phase | Variable Cost | Avg MAPE | Variables Passing |
|-------|---------------|----------|-------------------|
| Current | 41.43% | ~10% | 5/8 |
| Phase 1 (Entity fix) | ~25% | ~8% | 6/12 |
| Phase 2 (Regressors) | ~12% | ~5% | 9/12 |
| Phase 3 (Validation) | ~12% | ~5% | 10/12 |
| Phase 4 (MCP) | <8% | <4% | 11/12 |

---

## Dependencies

### Technical Dependencies
- Python 3.11+
- httpx (existing)
- pandas (existing)
- No new pip packages required

### External Service Dependencies
- Eurostat SDMX API (public, no auth, rate limited)
- ECB SDW API (public, no auth)
- European Commission BCS (public, no auth)
- INE Portugal API (public, no auth)
- ICE Futures (existing - TTF, API2)
- EU Oil Bulletin (existing - diesel)

### Internal Dependencies
- Story 6.8: Tier 2 Data Sources (completed)
- Story 6.11: MCP Multi-variate forecasting (completed)
- Story 6.12: Adaptive weights (completed)

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Eurostat API rate limiting | Medium | Medium | Implement caching, batch requests |
| Entity detection errors | Medium | High | Conservative filtering, manual review fallback |
| Low correlation with targets | Medium | Medium | A/B test regressors, keep fallback |
| Data gaps in historical series | Medium | Low | Interpolation, exclude if >10% missing |
| INE indicator still wrong | Low | High | Validate against web interface first |

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Variable Cost MAPE | 41.43% | <8% | Holdout validation |
| Variables passing target | 5/8 | 10/12 | Unified validation script |
| Data coefficient of variation | 33% | <15% | Standard deviation analysis |
| External regressors available | 5 | 11 | regressor_config.py count |
| MCP tools for forecasting | 1 | 4 | main.py tool count |
| Validation runtime | N/A | <10 min | Script execution time |

---

## Implementation Schedule

| Story | Effort | Dependencies | Priority |
|-------|--------|--------------|----------|
| 7.1: Entity-Specific Extraction | 4h | None | P0 |
| 7.2: Eurostat Indicators | 8h | None | P1 |
| 7.3: ECB Indicators | 4h | None | P1 |
| 7.4: Fix INE API | 4h | None | P1 |
| 7.5: EC Confidence | 6h | None | P2 |
| 7.6: Regressor Config | 4h | 7.2, 7.3, 7.4, 7.5 | P1 |
| 7.7: Unified Validation | 8h | 7.1, 7.6 | P1 |
| 7.8: MCP Integration | 6h | 7.7 | P2 |
| 7.9: Final Validation | 4h | All above | P0 |

**Critical Path:** 7.1 → 7.6 → 7.7 → 7.9

**Parallel Tracks:**
- Track A: 7.2, 7.3, 7.4, 7.5 (external data sources)
- Track B: 7.1 (entity extraction)
- Both merge at 7.6

---

## References

- Current validation script: `scripts/validate-cement-forecasting-12vars.py`
- Current regressor config: `raglite/forecasting/regressor_config.py`
- Variable Cost improvement brief: `docs/briefings/variable-cost-forecasting-improvement.md`
- Validation methodology guide: `docs/briefings/validation-methodology-guide.md`
- Variables expansion brief: `docs/briefings/forecasting-variables-expansion-brief.md`

### External API Documentation
- [Eurostat SDMX API](https://ec.europa.eu/eurostat/web/json-and-unicode-web-services)
- [ECB SDW REST API](https://sdw-wsrest.ecb.europa.eu/web/help)
- [EC Business Surveys](https://ec.europa.eu/economy_finance/db_indicators/surveys/documents/)
- [INE Portugal API](https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_api)
