# Forecasting Variables Expansion Brief

**Date:** 2025-12-12
**Status:** Ready for Story Creation
**Epic:** 6 - Forecasting Intelligence
**Estimated Effort:** 40 hours (P1: 12h + P2: 28h)
**Expected Outcome:** Variable Cost MAPE reduction from 41% to <8%

---

## Executive Summary

This brief defines the implementation of additional forecasting variables and external data sources to improve MAPE across all 12 cement industry metrics. Focus is on **free/open data sources only** - no commercial subscriptions required.

**Key Metric:** Variable Cost currently at 41.43% MAPE (target: 8%) due to missing cement-industry-specific cost drivers and broken data integrations.

---

## Problem Statement

### Current State
- 12 variables tested in `scripts/validate-cement-forecasting-12vars.py`
- Variable Cost MAPE: **41.43%** (5x above 8% target)
- Root cause: Generic macro indicators (euribor, diesel) used instead of cement-specific drivers
- INE Building Permits API broken (returns death statistics instead of construction data)
- Missing construction demand leading indicators (0.71 correlation with cement sales)

### Why This Matters
1. Variable Cost is foundational to EBITDA and margin forecasting
2. 41% MAPE makes forecasts unreliable for business planning
3. Cement costs are 30-40% energy, 15-25% raw materials - current regressors miss this
4. Construction activity leads cement demand by 3-6 months - we have no leading indicators

---

## Root Cause Analysis (Five Whys)

| Level | Question | Finding |
|-------|----------|---------|
| Why 1 | Why is Variable Cost MAPE at 41%? | Model lacks cement-industry-specific cost drivers |
| Why 2 | Why are cost drivers missing? | Using generic macro indicators (euribor) instead of construction/energy data |
| Why 3 | Why no construction indicators? | INE Building Permits API broken; no Eurostat construction integration |
| Why 4 | Why no better energy drivers? | Only TTF gas and API2 coal; missing industrial production correlation |
| Why 5 | Why haven't we integrated these? | Data sources identified but not prioritized until MAPE analysis |

---

## Current Architecture

### Variables Currently Tested (12)

```python
# From scripts/validate-cement-forecasting-12vars.py
CEMENT_FORECAST_VARIABLES = {
    # Internal Financial (PostgreSQL financial_tables)
    "revenue": VariableConfig(regressors=["euribor_3m", "diesel", "ttf_gas"], target_mape=5.0),
    "ebitda": VariableConfig(regressors=["euribor_3m", "ttf_gas", "diesel", "api2_coal"], target_mape=5.0),
    "sales_volume": VariableConfig(regressors=["euribor_3m", "diesel", "ttf_gas"], target_mape=5.0),
    "electricity_cost": VariableConfig(regressors=["eurostat_electricity"], target_mape=8.0),
    "thermal_cost": VariableConfig(regressors=["api2_coal", "ttf_gas"], target_mape=10.0),
    "variable_cost": VariableConfig(regressors=["ttf_gas", "omie_spot", "diesel"], target_mape=8.0),  # FAILING
    "avg_selling_price": VariableConfig(regressors=["diesel", "euribor_3m", "ttf_gas"], target_mape=6.0),
    "capacity_utilization": VariableConfig(regressors=["euribor_3m", "diesel", "ttf_gas"], target_mape=10.0),
    "clinker_factor": VariableConfig(regressors=[], target_mape=8.0, is_external_only=True),

    # External Commodities (APIs)
    "petcoke_price": VariableConfig(regressors=[], target_mape=12.0, is_external_only=True),
    "ttf_gas_price": VariableConfig(regressors=[], target_mape=12.0, is_external_only=True),
    "co2_eua_price": VariableConfig(regressors=["ttf_gas"], target_mape=15.0, is_external_only=True),
}
```

### External Data Clients Available (11)

| Client | File | Status | Data Provided |
|--------|------|--------|---------------|
| ECBClient | `ecb.py` | Working | EURIBOR rates |
| ICEFuturesClient | `ice_futures.py` | Working | TTF Gas, API2 Coal |
| EUOilBulletinClient | `eu_oil_bulletin.py` | Working | Diesel prices |
| EurostatClient | `eurostat.py` | Working | Industrial electricity (nrg_pc_204 only) |
| INEClient | `ine.py` | **BROKEN** | Building permits (wrong indicator) |
| BPstatClient | `bpstat.py` | Working | Mortgage loans |
| OMIEClient | `omie.py` | Slow | Electricity spot prices |
| IPMAClient | `ipma.py` | Working | Weather data |
| BaseGovClient | `basegov.py` | Working | Government procurement |
| ATICClient | `atic.py` | Working | Construction association data |
| CommoditiesClient | `commodities.py` | Cache fallback | CO2 EUA prices |

### PostgreSQL Metrics Available (84 total)

Key metrics in `financial_tables` table:
- Revenue: `Turnover+VAT`, `Turnover`
- Profitability: `EBITDA`, `EBITDA IFRS`, `Cement Unit Ebitda`
- Volume: `Sales Volumes`, `Volume IM - kton`
- Costs: `Variable Cost`, `Other Variable Costs`, `Fixed Costs`
- Energy: `Electrical Energy`, `Thermal Energy`
- Working Capital: `Trade Working Capital`, `DSO`, `DPO`, `DIO`
- Capacity: `Frequency Ratio` (proxy for utilization)
- Prices: `Sales Price EM - Cement`, `Sales Price IM`, `Sales Price-Transport Cost`
- Raw Materials: `Raw Materials`, `Other Materials`

---

## Proposed Solution

### Priority 1: Quick Wins (12 hours)

#### P1.1: Add Eurostat Construction Output Index
**Effort:** 4 hours
**Impact:** 15-20% MAPE improvement for sales/volume metrics
**Correlation with cement demand:** 0.71

```python
# New method in raglite/external_data/clients/eurostat.py
async def fetch_construction_output(
    self,
    country: str = "PT",
    start_date: date,
    end_date: date,
) -> list[ConstructionOutputData]:
    """Fetch construction production index from Eurostat.

    Dataset: sts_copr_m (Construction production index, monthly)
    API: https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/sts_copr_m

    Args:
        country: ISO 2-letter country code (PT, ES, EU27_2020)
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of construction output index values (base year 2021=100)
    """
```

**Data Model:**
```python
@dataclass
class ConstructionOutputData:
    date: date
    index_value: float  # Index, 2021=100
    country: str
    nace_activity: str  # F (construction), F41 (buildings), F42 (civil engineering)
```

#### P1.2: Add ECB GDP Growth Rate
**Effort:** 2 hours
**Impact:** 10-15% MAPE improvement for demand metrics

```python
# New method in raglite/external_data/clients/ecb.py
async def fetch_gdp_growth(
    self,
    country: str = "PT",
    start_date: date,
    end_date: date,
) -> list[GDPGrowthData]:
    """Fetch quarterly GDP growth rate from ECB SDW.

    Dataset: MNA.Q.Y.{country}.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N
    API: https://sdw-wsrest.ecb.europa.eu/service/data/MNA

    Returns:
        Quarterly GDP growth rate (year-over-year %)
    """
```

**Data Model:**
```python
@dataclass
class GDPGrowthData:
    date: date  # First day of quarter
    growth_rate_yoy: float  # Year-over-year growth %
    country: str
```

#### P1.3: Add ECB HICP Inflation Rate
**Effort:** 2 hours
**Impact:** 5-8% MAPE improvement for pricing metrics

```python
# New method in raglite/external_data/clients/ecb.py
async def fetch_inflation(
    self,
    country: str = "PT",
    start_date: date,
    end_date: date,
) -> list[InflationData]:
    """Fetch monthly HICP inflation from ECB SDW.

    Dataset: ICP.M.{country}.N.000000.4.ANR
    API: https://sdw-wsrest.ecb.europa.eu/service/data/ICP

    Returns:
        Monthly inflation rate (annual rate of change %)
    """
```

#### P1.4: Add Eurostat Industrial Production Index
**Effort:** 4 hours
**Impact:** 8-12% MAPE improvement for volume metrics

```python
# New method in raglite/external_data/clients/eurostat.py
async def fetch_industrial_production(
    self,
    country: str = "PT",
    start_date: date,
    end_date: date,
    nace: str = "B-D",  # Mining, manufacturing, utilities
) -> list[IndustrialProductionData]:
    """Fetch industrial production index from Eurostat.

    Dataset: sts_inpr_m (Short-term business statistics - industrial production)

    Returns:
        Monthly industrial production index (2021=100)
    """
```

### Priority 2: Medium Effort (28 hours)

#### P2.1: Fix INE Building Permits
**Effort:** 4 hours
**Impact:** 15-20% MAPE improvement for PT sales forecasting
**Issue:** Currently returns indicator `0008145` (deaths) instead of `0010099` (building permits)

```python
# Fix in raglite/external_data/clients/ine.py

# CURRENT (BROKEN):
BUILDING_PERMITS_INDICATOR = "0008145"  # Wrong - returns death statistics

# FIXED:
BUILDING_PERMITS_INDICATOR = "0010099"  # Correct - Licenciamento de obras
# Alternative: "0010094" for housing permits specifically
```

**Validation Required:**
- Verify indicator ID against INE API documentation
- Test with date range 2020-2025
- Confirm data structure matches existing parser

#### P2.2: Add European Commission Construction Confidence
**Effort:** 8 hours
**Impact:** 10-15% MAPE improvement for demand forecasting
**Data Source:** Business and Consumer Surveys (BCS)

```python
# New client: raglite/external_data/clients/ec_surveys.py

class ECBusinessSurveysClient:
    """European Commission Business and Consumer Surveys.

    API: https://ec.europa.eu/info/business-economy-euro/indicators-statistics/
    Dataset: Construction confidence indicator
    """

    BASE_URL = "https://ec.europa.eu/economy_finance/db_indicators/surveys/time_series"

    async def fetch_construction_confidence(
        self,
        country: str = "PT",
        start_date: date,
        end_date: date,
    ) -> list[ConstructionConfidenceData]:
        """Fetch monthly construction confidence indicator.

        The indicator is the arithmetic average of:
        - Assessment of order books
        - Employment expectations for the months ahead

        Returns:
            Monthly confidence index (balance %, seasonally adjusted)
        """
```

**Data Model:**
```python
@dataclass
class ConstructionConfidenceData:
    date: date
    confidence_index: float  # Balance %, range typically -50 to +50
    order_books: float  # Sub-indicator
    employment_expectations: float  # Sub-indicator
    country: str
```

#### P2.3: Add Eurostat Housing Statistics
**Effort:** 8 hours
**Impact:** 10-15% MAPE improvement for demand forecasting

```python
# New method in raglite/external_data/clients/eurostat.py

async def fetch_building_permits_eu(
    self,
    country: str = "PT",
    start_date: date,
    end_date: date,
    building_type: str = "RES",  # Residential
) -> list[BuildingPermitData]:
    """Fetch building permits from Eurostat (backup for INE).

    Dataset: sts_cobp_m (Building permits - number of dwellings)

    Returns:
        Monthly building permits count
    """

async def fetch_housing_completions(
    self,
    country: str = "PT",
    start_date: date,
    end_date: date,
) -> list[HousingCompletionData]:
    """Fetch housing completions from Eurostat.

    Dataset: sts_cobp_m with different filter

    Returns:
        Monthly/quarterly housing completions
    """
```

#### P2.4: Update Regressor Configuration
**Effort:** 8 hours
**Impact:** Enables all new data sources for forecasting

```python
# Update raglite/forecasting/regressor_config.py (or create if doesn't exist)

# New regressors to register
NEW_REGRESSORS = [
    "construction_output",      # Eurostat sts_copr_m
    "gdp_growth",               # ECB SDW MNA
    "inflation",                # ECB SDW ICP
    "industrial_production",    # Eurostat sts_inpr_m
    "construction_confidence",  # EC BCS
    "building_permits_eu",      # Eurostat sts_cobp_m
    "housing_completions",      # Eurostat sts_cobp_m
]

# Optimal regressor mappings per variable type
METRIC_REGRESSORS = {
    "revenue": ["construction_output", "gdp_growth", "euribor_3m"],
    "ebitda": ["ttf_gas", "api2_coal", "construction_output", "gdp_growth"],
    "sales_volume": ["construction_output", "building_permits", "gdp_growth"],
    "variable_cost": ["ttf_gas", "api2_coal", "industrial_production", "diesel"],
    "electricity_cost": ["eurostat_electricity", "industrial_production"],
    "thermal_cost": ["api2_coal", "ttf_gas", "industrial_production"],
    "avg_selling_price": ["construction_confidence", "gdp_growth", "inflation"],
    "capacity_utilization": ["construction_output", "gdp_growth", "industrial_production"],
}
```

#### P2.5: Update Regressor Fetch Logic
**Effort:** Included in P2.4

```python
# Update fetch_external_regressors() in validation script or create centralized fetcher

async def fetch_external_regressors(
    regressor_names: list[str],
    start_date: date,
    end_date: date,
) -> dict[str, pd.Series]:
    """Fetch all requested external regressors.

    New regressors to add:
    - construction_output: EurostatClient.fetch_construction_output()
    - gdp_growth: ECBClient.fetch_gdp_growth()
    - inflation: ECBClient.fetch_inflation()
    - industrial_production: EurostatClient.fetch_industrial_production()
    - construction_confidence: ECBusinessSurveysClient.fetch_construction_confidence()
    - building_permits_eu: EurostatClient.fetch_building_permits_eu()
    """
```

---

## Data Source APIs Reference

### Eurostat SDMX API
```
Base URL: https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1
Format: JSON-stat or SDMX-JSON

Datasets needed:
- sts_copr_m: Construction production index
- sts_inpr_m: Industrial production index
- sts_cobp_m: Building permits

Example request:
GET /data/sts_copr_m?geo=PT&unit=I21&s_adj=SCA&nace_r2=F&format=JSON
```

### ECB Statistical Data Warehouse (SDW)
```
Base URL: https://sdw-wsrest.ecb.europa.eu/service
Format: SDMX-JSON

Datasets needed:
- MNA: National accounts (GDP)
- ICP: HICP inflation

Example request:
GET /data/MNA/Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N?format=jsondata
```

### European Commission Business Surveys
```
Base URL: https://ec.europa.eu/economy_finance/db_indicators/surveys
Format: CSV/JSON

Indicators needed:
- BUIL.PT.TOT.COF.BS.M: Construction confidence (monthly, SA)
```

### INE Portugal API
```
Base URL: https://www.ine.pt/ine/json_indicador/pindica.jsp
Format: JSON

Correct indicator IDs:
- 0010099: Licenciamento de obras (building permits total)
- 0010094: Licenciamento de fogos (housing permits)
- 0010100: Licenciamento de obras - área (building permits by area)
```

---

## File Changes Summary

### New Files to Create
| File | Purpose |
|------|---------|
| `raglite/external_data/clients/ec_surveys.py` | European Commission Business Surveys client |
| `raglite/external_data/models.py` | Add new data models (if not exists, extend) |
| `raglite/forecasting/regressor_config.py` | Centralized regressor configuration |

### Files to Modify
| File | Changes |
|------|---------|
| `raglite/external_data/clients/eurostat.py` | Add `fetch_construction_output()`, `fetch_industrial_production()`, `fetch_building_permits_eu()` |
| `raglite/external_data/clients/ecb.py` | Add `fetch_gdp_growth()`, `fetch_inflation()` |
| `raglite/external_data/clients/ine.py` | Fix `BUILDING_PERMITS_INDICATOR` constant |
| `raglite/external_data/clients/__init__.py` | Export new client |
| `scripts/validate-cement-forecasting-12vars.py` | Update regressor mappings, add new fetch logic |

---

## Acceptance Criteria

### P1 Acceptance Criteria
- [ ] **AC1.1:** Eurostat construction output index fetches successfully for PT (2020-2025)
- [ ] **AC1.2:** ECB GDP growth rate fetches quarterly data for PT
- [ ] **AC1.3:** ECB HICP inflation fetches monthly data for PT
- [ ] **AC1.4:** Eurostat industrial production index fetches for PT
- [ ] **AC1.5:** All new regressors show >0.3 correlation with target variables
- [ ] **AC1.6:** No new external dependencies added (uses existing httpx)
- [ ] **AC1.7:** Unit tests pass for all new client methods
- [ ] **AC1.8:** Integration tests verify data quality (no >10% missing values)

### P2 Acceptance Criteria
- [ ] **AC2.1:** INE building permits returns construction data (not death statistics)
- [ ] **AC2.2:** EC construction confidence fetches monthly for PT
- [ ] **AC2.3:** Eurostat housing statistics integrate correctly
- [ ] **AC2.4:** Regressor configuration applies correct mappings per variable type
- [ ] **AC2.5:** Variable Cost MAPE reduces to <20% with new regressors
- [ ] **AC2.6:** All 12 variables use optimized regressor sets
- [ ] **AC2.7:** Validation script runs successfully with --real-data flag
- [ ] **AC2.8:** No regression in other metric MAPE values

### Final Validation Criteria
- [ ] **AC3.1:** Variable Cost MAPE <15% (interim target)
- [ ] **AC3.2:** At least 10 of 12 variables meet their MAPE targets
- [ ] **AC3.3:** Validation script completes in <10 minutes
- [ ] **AC3.4:** All external API calls have retry logic and fallback caching

---

## Expected MAPE Improvements

| Variable | Current MAPE | After P1 | After P1+P2 | Target |
|----------|-------------|----------|-------------|--------|
| Variable Cost | **41.43%** | ~25% | ~12% | 8% |
| Revenue | 2.8% | 2.2% | 1.8% | 5% |
| EBITDA | 2.5% | 2.0% | 1.6% | 5% |
| Sales Volume | 0.8% | 0.6% | 0.5% | 5% |
| Electricity Cost | 3.0% | 2.5% | 2.2% | 8% |
| Thermal Energy | 2.6% | 2.0% | 1.6% | 10% |
| Avg Selling Price | 1.6% | 1.3% | 1.0% | 6% |
| Capacity Utilization | 2.5% | 2.0% | 1.6% | 10% |

**Aggregate Improvement:** 15-25% average MAPE reduction across all variables

---

## Dependencies

### Technical Dependencies
- Python 3.11+
- httpx (already installed)
- pandas (already installed)
- No new pip packages required

### External Service Dependencies
- Eurostat API (public, no auth required, rate limited)
- ECB SDW API (public, no auth required)
- European Commission surveys (public, no auth required)
- INE Portugal API (public, no auth required)

### Internal Dependencies
- Story 6.8: Tier 2 Data Sources (completed - provides client patterns)
- Story 6.11: MCP Multi-variate forecasting (completed - provides regressor integration)

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Eurostat API rate limiting | Medium | Medium | Implement caching, batch requests |
| ECB SDW format changes | Low | High | Abstract parser, add format versioning |
| INE indicator ID still wrong | Medium | High | Validate against web interface before implementation |
| Low correlation with targets | Medium | Medium | A/B test regressors, keep fallback to current |
| Data gaps in historical series | Medium | Low | Interpolation, exclude from training if >10% missing |

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/external_data/test_eurostat.py
async def test_fetch_construction_output_returns_valid_data():
    """Test construction output fetches correctly."""

async def test_fetch_industrial_production_returns_valid_data():
    """Test industrial production fetches correctly."""

# tests/unit/external_data/test_ecb.py
async def test_fetch_gdp_growth_returns_quarterly_data():
    """Test GDP growth returns quarterly periods."""

async def test_fetch_inflation_returns_monthly_data():
    """Test inflation returns monthly HICP."""
```

### Integration Tests
```python
# tests/integration/test_new_regressors.py
async def test_construction_output_correlates_with_sales():
    """Verify construction output has >0.3 correlation with sales volume."""

async def test_regressor_config_applies_correctly():
    """Verify correct regressors used per variable type."""
```

### Validation Tests
```bash
# Run full validation with new regressors
python scripts/validate-cement-forecasting-12vars.py --real-data --verbose

# Expected output: Variable Cost MAPE < 20%
```

---

## Story Breakdown Recommendation

### Story 6.X.1: Add Eurostat Construction & Industrial Indicators (P1.1 + P1.4)
- Effort: 8 hours
- Add construction output + industrial production to Eurostat client
- Update validation script with new regressors
- AC: Both indicators fetch successfully, >0.3 correlation verified

### Story 6.X.2: Add ECB Macroeconomic Indicators (P1.2 + P1.3)
- Effort: 4 hours
- Add GDP growth + inflation to ECB client
- Update validation script with new regressors
- AC: Both indicators fetch successfully

### Story 6.X.3: Fix INE Building Permits (P2.1)
- Effort: 4 hours
- Fix indicator ID
- Validate against INE web interface
- AC: Returns construction permits, not death statistics

### Story 6.X.4: Add EC Construction Confidence (P2.2)
- Effort: 8 hours
- New client for European Commission surveys
- AC: Monthly confidence data fetches for PT

### Story 6.X.5: Add Eurostat Housing Statistics (P2.3)
- Effort: 8 hours
- Building permits and housing completions from Eurostat
- AC: Backup data source for INE, successful fetch

### Story 6.X.6: Integrate New Regressors (P2.4 + P2.5)
- Effort: 8 hours
- Create centralized regressor configuration
- Update all variable configurations
- AC: Variable Cost MAPE < 20%, all variables use optimal regressors

---

## References

- Current validation script: `scripts/validate-cement-forecasting-12vars.py`
- Current external data clients: `raglite/external_data/clients/`
- Variable Cost improvement brief: `docs/briefings/variable-cost-forecasting-improvement.md`
- Eurostat API docs: https://ec.europa.eu/eurostat/web/json-and-unicode-web-services
- ECB SDW docs: https://sdw-wsrest.ecb.europa.eu/web/help
- EC Survey docs: https://ec.europa.eu/economy_finance/db_indicators/surveys/documents/

---

## Appendix A: PostgreSQL Metrics Available

Full list of 84 metrics in `financial_tables` for reference:

```
Accounts payable, Accounts receivable, Advances from customers, Advances to suppliers,
All-in cost Bank Debt, Angola currency impacts, Asset sales (cash), Average cost of debt,
Brazil currency impacts, CAPEX Development, CAPEX Replacement, Capital Employed,
Cash, Cement Unit Ebitda, Customers receivables, DIO, DPO, DSO, Dividends,
EBITDA IFRS, Electrical Energy, Employee costs, FCF metrics, Financial costs,
Financial Investments, Fixed Costs, Frequency Ratio (capacity), Income Tax,
Inventories, Lost Time Injury, Net Cash Flow, Net debt, Net interest expenses,
Operational costs, Other Variable Costs, Portugal currency impacts,
Raw Materials, Revenue (M EUR), Sales & Distribution Fixed Costs, Sales Prices (EM/IM),
Sales Volumes, Subsidiaries costs, Suppliers, Thermal Energy, Trade Working Capital,
Tunisia currency impacts, Turnover, Turnover+VAT, Variable Cost, Volume IM - kton
```

---

## Appendix B: Correlation Matrix (Expected)

Based on cement industry research:

| Regressor | Revenue | Sales Vol | Var Cost | Capacity |
|-----------|---------|-----------|----------|----------|
| construction_output | 0.71 | 0.75 | 0.45 | 0.68 |
| gdp_growth | 0.65 | 0.60 | 0.35 | 0.55 |
| building_permits | 0.68 | 0.72 | 0.40 | 0.62 |
| industrial_production | 0.55 | 0.58 | 0.52 | 0.60 |
| construction_confidence | 0.58 | 0.55 | 0.30 | 0.50 |
| inflation | 0.40 | 0.25 | 0.45 | 0.20 |
| ttf_gas | 0.35 | 0.30 | 0.65 | 0.28 |
| api2_coal | 0.30 | 0.25 | 0.60 | 0.22 |

*Note: Values are estimates based on industry research. Actual correlation to be validated during implementation.*
