# Variable Cost Forecasting Improvement Brief

**Date**: 2025-12-12
**Status**: Ready for Story Creation
**Current MAPE**: 41.43% (Target: <8%)

---

## Problem Statement

Variable Cost forecasting currently achieves 41.43% MAPE, significantly above the 8% target. Root cause analysis identified **data quality issues** rather than model limitations:

| Issue | Impact |
|-------|--------|
| Multiple entities mixed (Portugal, Tunisia, Brazil) | Values from different cost structures combined |
| Multiple currencies (EUR, BRL, TND) | Unit inconsistency even after filtering |
| Multiple units (EUR/m³, EUR/ton, thousands) | 10x scale differences in raw data |
| No external cost drivers | Model cannot anticipate cost changes |

**Current extracted data characteristics**:
- 28 data points (after filtering)
- Range: -331 to -101 EUR/m³
- Mean: -192 EUR/m³, Std Dev: 64 EUR/m³
- Coefficient of variation: ~33%

---

## Approach 1: Entity-Specific Data Extraction

### Objective
Extract Variable Cost time series **per entity** with consistent units, eliminating cross-entity contamination.

### Requirements

#### 1.1 Entity Detection in Qdrant Chunks
- Parse chunk text to identify entity context (Portugal, Tunisia, Brazil, Consolidated)
- Use table headers, section titles, or adjacent text as entity indicators
- Store entity as extraction metadata

**Example patterns to detect**:
```
| Portugal | Tunisia | Brazil |     <- Column headers indicate entity
"Portugal Operations"                <- Section title
"Custos Variáveis - Portugal"        <- Portuguese label
```

#### 1.2 Unit Normalization
- Detect unit from table headers or row labels: `EUR/m³`, `EUR/ton`, `BRL/m³`, `TND/m³`
- Convert all values to a standard unit (EUR/ton recommended)
- Apply currency conversion where needed (BRL→EUR, TND→EUR)

**Currency conversion options**:
- Static rates (simpler, less accurate)
- Historical rates from ECB API (more accurate, adds dependency)

#### 1.3 Entity-Specific Extraction Functions
Create dedicated extraction for primary entity (Portugal):

```python
async def extract_variable_cost_portugal(min_points: int = 6) -> TimeSeriesData:
    """Extract Portugal-specific Variable Cost in EUR/ton."""
    # 1. Query Qdrant for Variable Cost chunks
    # 2. Filter to Portugal-only context
    # 3. Normalize to EUR/ton
    # 4. Deduplicate across reporting periods
    # 5. Return consistent time series
```

#### 1.4 Data Validation Rules
- Reject values outside expected range per entity:
  - Portugal: -150 to -350 EUR/ton
  - Tunisia: -80 to -200 TND/m³
  - Brazil: 250 to 450 BRL/m³
- Flag anomalies for manual review

### Acceptance Criteria (Approach 1)
- [ ] AC1: Entity detected with >95% accuracy on test set
- [ ] AC2: Single-entity extraction produces <15% coefficient of variation
- [ ] AC3: Variable Cost MAPE improves to <20%
- [ ] AC4: No regression in other metric extraction

---

## Approach 2: External Regressors for Cost Drivers

### Objective
Add external economic indicators that **drive** Variable Cost changes, enabling the model to anticipate cost movements rather than just extrapolate history.

### Key Cost Drivers for Cement/Construction Industry

| Driver | Relevance | Data Source |
|--------|-----------|-------------|
| **Energy prices** | 30-40% of variable cost | EU Energy Statistics, TTF Gas (already have) |
| **Diesel/fuel prices** | Transport costs | EU Oil Bulletin (already have) |
| **Electricity prices** | Grinding, processing | ENTSO-E, Eurostat |
| **Raw material indices** |Iteite, limestone, gypsum | World Bank Commodities |
| **CO2 emission allowances** | EU ETS compliance | EU ETS Registry |
| **Freight rates** | Import costs | Baltic Dry Index, Freightos |

### Requirements

#### 2.1 Priority External Data Sources

**Tier 1 (High Impact, Already Available)**:
- TTF Gas Price (already integrated)
- Diesel Price (already integrated)
- EURIBOR (already integrated)

**Tier 2 (High Impact, New Integration)**:
- EU Electricity Prices (Portugal wholesale)
- EU ETS Carbon Prices
- Cement Production Cost Index (if available)

**Tier 3 (Medium Impact, Complex Integration)**:
- Raw material commodity prices
- Freight/shipping indices

#### 2.2 Data Integration Pattern

```python
# Extend existing external_data module
class ElectricityPriceClient:
    """Fetch Portugal electricity prices from ENTSO-E."""

    async def get_monthly_prices(
        self,
        start_date: date,
        end_date: date
    ) -> list[ExternalDataPoint]:
        # 1. Query ENTSO-E Transparency Platform API
        # 2. Aggregate hourly to monthly average
        # 3. Return standardized ExternalDataPoint list


class CarbonPriceClient:
    """Fetch EU ETS carbon allowance prices."""

    async def get_monthly_prices(
        self,
        start_date: date,
        end_date: date
    ) -> list[ExternalDataPoint]:
        # 1. Query EU ETS or financial data provider
        # 2. Return EUR/tCO2 monthly series
```

#### 2.3 Regressor Selection for Variable Cost

Update forecasting to use cost-relevant regressors:

```python
VARIABLE_COST_REGRESSORS = [
    "ttf_gas_price",      # Already available
    "diesel_price",       # Already available
    "electricity_price",  # New - Tier 2
    "carbon_price",       # New - Tier 2
]

async def forecast_variable_cost(
    historical_data: TimeSeriesData,
    periods_ahead: int = 6,
) -> ForecastResult:
    # Use cost-specific regressors instead of generic set
    return await generate_ensemble_forecast(
        metric="variable_cost",
        historical_data=historical_data,
        external_regressors=VARIABLE_COST_REGRESSORS,
        periods_ahead=periods_ahead,
    )
```

#### 2.4 Correlation Analysis
Before integration, validate regressor relevance:
- Calculate Pearson correlation between each external variable and Variable Cost
- Require |r| > 0.3 for inclusion
- Test for lead/lag relationships (cost drivers may lead Variable Cost by 1-3 months)

### Acceptance Criteria (Approach 2)
- [ ] AC1: At least 2 new Tier 2 data sources integrated
- [ ] AC2: Correlation analysis shows |r| > 0.3 for new regressors
- [ ] AC3: Variable Cost MAPE improves to <15% with regressors
- [ ] AC4: Regressor data has <5% missing values over analysis period

---

## Implementation Recommendation

### Phased Approach

**Phase 1: Quick Wins (1-2 days)**
- Implement entity detection heuristics in Variable Cost extraction
- Filter strictly to Portugal-only data
- Expected improvement: 41% → ~25% MAPE

**Phase 2: External Regressors (3-5 days)**
- Integrate EU Electricity Prices (ENTSO-E API)
- Integrate EU ETS Carbon Prices
- Add to Variable Cost forecasting pipeline
- Expected improvement: 25% → ~12% MAPE

**Phase 3: Full Entity Support (5-7 days)**
- Complete entity-specific extraction for all regions
- Currency normalization
- Entity-aware forecasting
- Expected improvement: 12% → <8% MAPE

### Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| ENTSO-E API access | Required | Free registration, rate limited |
| EU ETS data source | Required | Multiple options (ICE, EEX, Ember) |
| Historical currency rates | Optional | For multi-entity support |
| Ground truth Variable Cost data | Required | For validation |

### Risks

| Risk | Mitigation |
|------|------------|
| External APIs rate limited | Implement caching, batch requests |
| Data source discontinuation | Abstract behind interface, have fallbacks |
| Regressor correlation spurious | Validate with holdout testing |
| Entity detection errors | Conservative filtering, manual review |

---

## Success Metrics

| Metric | Current | Phase 1 | Phase 2 | Phase 3 |
|--------|---------|---------|---------|---------|
| Variable Cost MAPE | 41.43% | <25% | <15% | <8% |
| Data points extracted | 28 | 20+ | 20+ | 50+ |
| Coefficient of variation | 33% | <20% | <15% | <12% |
| External regressors used | 0 | 0 | 2+ | 3+ |

---

## Files to Modify

1. `raglite/forecasting/timeseries_extract.py` - Entity-specific extraction
2. `raglite/external_data/clients/` - New data source clients
3. `raglite/forecasting/hybrid.py` - Metric-specific regressor selection
4. `tests/integration/test_variable_cost.py` - New validation tests

---

## References

- [ENTSO-E Transparency Platform API](https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html)
- [EU ETS Data](https://www.eex.com/en/market-data/environmental-markets)
- [World Bank Commodity Prices](https://www.worldbank.org/en/research/commodity-markets)
- Current extraction: `raglite/forecasting/timeseries_extract.py:381-558`
