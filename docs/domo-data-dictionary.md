# Domo Data Lake - Financial Metrics Data Dictionary

**Version:** 1.1
**Last Updated:** 2026-01-30
**Status:** Ready for Implementation
**Contact:** RAGLite Development Team

---

## Purpose

This document defines the schema and data requirements for the `financial_metrics` table in Domo that the RAGLite forecasting system queries for time series analysis and forecasting.

The forecasting module (`raglite/forecasting/`) expects data in this standardized format to:
- Extract time-series data for ARIMA, ETS, XGBoost, and ensemble models
- Perform data quality checks (gap detection, outlier detection, unit validation)
- Generate multi-horizon forecasts with confidence intervals

---

## Table Schema

### `financial_metrics`

| Column | Data Type | Required | Description |
|--------|-----------|----------|-------------|
| **entity** | VARCHAR(50) | YES | Business unit/region (see Entity List below) |
| **metric** | VARCHAR(100) | YES | KPI name (see Metric List below) |
| **period_date** | DATE | YES | First day of period (e.g., 2025-12-01 for Dec 2025) |
| **value** | DECIMAL(15,2) | YES | Numeric value |
| **unit** | VARCHAR(20) | YES | Unit of measurement (see Unit Standards below) |
| **fiscal_year** | INTEGER | YES | Fiscal year (e.g., 2025) |
| **period_label** | VARCHAR(10) | Optional | Display label (e.g., "Dec-25") |

### Primary Key
`(entity, metric, period_date)` - One row per entity-metric-period combination

### Indexes (Recommended)
- `idx_entity_metric` on `(entity, metric)` - For time series extraction
- `idx_period_date` on `(period_date)` - For date range queries
- `idx_fiscal_year` on `(fiscal_year)` - For fiscal year filtering

---

## Entity List (6 entities)

These entities align with the forecasting module constants in `raglite/forecasting/timeseries/metadata.py`.

| Entity Code | Description | ERP Mapping Notes |
|-------------|-------------|-------------------|
| **Group** | Consolidated group total | Map from: "GROUP", "Conso", "CONSO", "Consolidated", "Total Group" |
| **Portugal** | Portugal operations | Map from: "Portugal", "PT", "Secil Portugal" |
| **Brazil** | Brazil operations | Map from: "Brazil", "BR", "Secil Brazil", "Brasil" |
| **Tunisia** | Tunisia operations | Map from: "Tunisia", "TN", "Tunisie" |
| **Lebanon** | Lebanon operations | Map from: "Lebanon", "LB" |
| **Angola** | Angola operations | Map from: "Angola", "AO" |

### Entity Naming Rules
- Use **Title Case** (e.g., "Portugal", not "PORTUGAL" or "portugal")
- The forecasting system normalizes case internally, but consistent casing improves query performance
- "Group" represents consolidated totals; individual entities represent regional breakdowns

---

## Metric List (15 Internal Variables)

### Financial Performance Metrics

| Metric Code | Display Name | Required Entity | Unit | ERP Source Mapping |
|-------------|--------------|-----------------|------|-------------------|
| **ebitda** | EBITDA | All | M EUR | "EBITDA", "EBITDA IFRS", "Cement Unit Ebitda" |
| **revenue** | Revenue | All | M EUR | "Turnover", "Turnover+VAT", "Revenue", "Net Sales" |
| **capex** | Capital Expenditure | All | M EUR | "CAPEX", "Capex", "Capital Expenditure" |
| **cash_flow** | Cash Flow from Operations | All | M EUR | "CF from Operating Activities", "Cash Flow Operations", "Operating Cash Flow" |
| **trade_working_capital** | Trade Working Capital | All | M EUR | "Trade Working Capital", "TWC", "Net Working Capital" |
| **net_interest_expenses** | Net Interest Expenses | All | M EUR | "Net Interest Expenses", "Interest Expense Net", "Financial Costs" |

### Operational Metrics

| Metric Code | Display Name | Required Entity | Unit | ERP Source Mapping |
|-------------|--------------|-----------------|------|-------------------|
| **sales_volume** | Sales Volume | All | kton | "Sales Volumes", "Volume IM - kton", "Sales kton" |
| **avg_selling_price** | Average Selling Price | All | EUR/ton | "Sales Price EM - Cement", "Sales Price IM", "Sales Price-Transport Cost" |
| **capacity_utilization** | Capacity Utilization | All | % | "Frequency Ratio", "Utilization Rate" |
| **headcount** | Headcount | All | FTE | "Headcount", "FTE", "Employees", "Secil Portugal Headcount" |

### Cost Metrics (per-ton basis)

| Metric Code | Display Name | Required Entity | Unit | ERP Source Mapping |
|-------------|--------------|-----------------|------|-------------------|
| **variable_cost** | Variable Cost | All | EUR/ton | "Variable Cost", "Other Variable Costs" |
| **fixed_costs** | Fixed Costs | All | EUR/ton | "Fixed Costs", "Fixed Cost" |
| **electricity_cost** | Electricity Cost | All | EUR/ton | "Electrical Energy", "Electricity Cost" |
| **thermal_cost** | Thermal Energy Cost | All | EUR/ton | "Thermal Energy", "Fuel Cost" |
| **other_costs** | Other Costs/Income | All | EUR/ton | "Other costs/income", "Other Costs/Income", "Other Income" |

### Metric Naming Rules
- Use **lowercase with underscores** (e.g., "variable_cost", not "Variable Cost" or "variableCost")
- These codes match the constants in `raglite/forecasting/timeseries/metadata.py`

### New Metrics (v1.1)
Three additional financial metrics were added to support comprehensive cash flow and balance sheet analysis:
- **cash_flow**: Operating cash flow for liquidity analysis and forecasting
- **trade_working_capital**: Net working capital for balance sheet health monitoring
- **net_interest_expenses**: Financial costs for debt service analysis

---

## Unit Standards

| Unit Code | Description | Conversion Notes |
|-----------|-------------|------------------|
| **M EUR** | Millions of Euros | Convert kEUR ÷ 1000 |
| **kton** | Thousands of tons | Convert tons ÷ 1000 |
| **EUR/ton** | Euros per ton | Cost per unit metrics |
| **%** | Percentage | Capacity utilization (0-100 range) |
| **FTE** | Full-time equivalent | Headcount |

### Currency Conversion Reference
For non-EUR sources, apply these conversion rates (or use live rates):

| Currency | EUR Rate | Notes |
|----------|----------|-------|
| TND (Tunisian Dinar) | 0.31 | Tunisia operations |
| BRL (Brazilian Real) | 0.18 | Brazil operations |
| EUR | 1.00 | Portugal, Group |

---

## Data Requirements

### Time Range
- **Minimum:** 2020-01-01 (5 years of monthly data = 60 months)
- **Ideal:** 2014-01-01 (10+ years for better forecasting = 120+ months)
- **Current Expectation:** Data through December 2025

### Frequency
- **Primary:** Monthly data (first day of each month)
- **Acceptable:** Quarterly or annual data will be interpolated by the forecasting system

### Minimum Data Points
The forecasting system requires **minimum 8 data points** per entity-metric combination for reliable forecasting (see `MetricValidationError` in `raglite/forecasting/timeseries/metadata.py`).

### Data Quality Rules

1. **One row per entity + metric + period** (no duplicates)
2. **Consistent entity names** (use Entity List above exactly)
3. **Consistent metric names** (use Metric Code from table exactly)
4. **Dates as DATE type** (not strings) - First day of period
5. **Values as DECIMAL** (not strings)
6. **Standardized units** (convert all to standard units listed)
7. **No NULL values** - Exclude periods without data rather than using NULL
8. **Sign conventions** - Costs should be negative (see Sign Conventions section)

---

## Sign Conventions

| Metric | Expected Sign | Notes |
|--------|---------------|-------|
| ebitda | Positive (+) | Can be negative for losses |
| revenue | Positive (+) | Can have negative adjustments |
| capex | Positive (+) | Can be negative for disposals |
| cash_flow | Positive (+) | Can be negative for cash consumption |
| trade_working_capital | Positive (+) | Can be negative if liabilities > receivables |
| net_interest_expenses | **Negative (-)** | Financial costs are negative |
| sales_volume | Positive (+) | Always positive |
| avg_selling_price | Positive (+) | Always positive |
| variable_cost | **Negative (-)** | Costs are negative |
| fixed_costs | **Negative (-)** | Costs are negative |
| electricity_cost | **Negative (-)** | Costs are negative |
| thermal_cost | **Negative (-)** | Costs are negative |
| other_costs | Either | Can be cost (-) or income (+) |
| headcount | Positive (+) | Always positive |
| capacity_utilization | Positive (+) | 0-100% range |

### Why Negative Costs?
The forecasting system uses negative values for costs to:
- Enable additive calculations (Revenue + Variable_Cost = Contribution)
- Maintain consistent sign conventions across all metrics
- Support EBITDA decomposition analysis

---

## Entity-Metric Matrix

**All 15 metrics for all 6 entities:**

| Metric | Group | Portugal | Brazil | Tunisia | Lebanon | Angola |
|--------|:-----:|:--------:|:------:|:-------:|:-------:|:------:|
| ebitda | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| revenue | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| capex | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| cash_flow | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| trade_working_capital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| net_interest_expenses | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| sales_volume | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| avg_selling_price | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| variable_cost | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| fixed_costs | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| electricity_cost | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| thermal_cost | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| other_costs | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| headcount | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| capacity_utilization | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**Total combinations:** 6 entities × 15 metrics = **90 entity-metric pairs**

---

## Sample Data Format

```csv
entity,metric,period_date,value,unit,fiscal_year,period_label
Group,ebitda,2025-12-01,128.50,M EUR,2025,Dec-25
Group,revenue,2025-12-01,702.15,M EUR,2025,Dec-25
Group,capex,2025-12-01,45.30,M EUR,2025,Dec-25
Group,cash_flow,2025-12-01,95.20,M EUR,2025,Dec-25
Group,trade_working_capital,2025-12-01,145.80,M EUR,2025,Dec-25
Group,net_interest_expenses,2025-12-01,-8.50,M EUR,2025,Dec-25
Group,sales_volume,2025-12-01,850.00,kton,2025,Dec-25
Group,variable_cost,2025-12-01,-25.00,EUR/ton,2025,Dec-25
Group,headcount,2025-12-01,3500.00,FTE,2025,Dec-25
Portugal,ebitda,2025-12-01,55.20,M EUR,2025,Dec-25
Portugal,revenue,2025-12-01,320.00,M EUR,2025,Dec-25
Portugal,cash_flow,2025-12-01,42.30,M EUR,2025,Dec-25
Portugal,trade_working_capital,2025-12-01,68.50,M EUR,2025,Dec-25
Portugal,net_interest_expenses,2025-12-01,-3.20,M EUR,2025,Dec-25
Portugal,sales_volume,2025-12-01,125.40,kton,2025,Dec-25
Portugal,avg_selling_price,2025-12-01,75.60,EUR/ton,2025,Dec-25
Portugal,variable_cost,2025-12-01,-28.50,EUR/ton,2025,Dec-25
Portugal,electricity_cost,2025-12-01,-10.50,EUR/ton,2025,Dec-25
Portugal,thermal_cost,2025-12-01,-12.30,EUR/ton,2025,Dec-25
Portugal,fixed_costs,2025-12-01,-15.80,EUR/ton,2025,Dec-25
Portugal,headcount,2025-12-01,1250.00,FTE,2025,Dec-25
Portugal,capacity_utilization,2025-12-01,78.50,%,2025,Dec-25
Portugal,other_costs,2025-12-01,3.20,EUR/ton,2025,Dec-25
Brazil,ebitda,2025-12-01,25.70,M EUR,2025,Dec-25
Brazil,revenue,2025-12-01,150.00,M EUR,2025,Dec-25
Brazil,cash_flow,2025-12-01,18.90,M EUR,2025,Dec-25
Brazil,trade_working_capital,2025-12-01,32.40,M EUR,2025,Dec-25
Brazil,net_interest_expenses,2025-12-01,-2.10,M EUR,2025,Dec-25
Brazil,sales_volume,2025-12-01,152.00,kton,2025,Dec-25
Brazil,variable_cost,2025-12-01,-23.40,EUR/ton,2025,Dec-25
Tunisia,ebitda,2025-12-01,18.30,M EUR,2025,Dec-25
Tunisia,sales_volume,2025-12-01,95.00,kton,2025,Dec-25
Tunisia,cash_flow,2025-12-01,12.50,M EUR,2025,Dec-25
Lebanon,ebitda,2025-12-01,2.10,M EUR,2025,Dec-25
Lebanon,sales_volume,2025-12-01,48.00,kton,2025,Dec-25
Angola,ebitda,2025-12-01,35.00,M EUR,2025,Dec-25
Angola,revenue,2025-12-01,190.00,M EUR,2025,Dec-25
Angola,cash_flow,2025-12-01,28.40,M EUR,2025,Dec-25
```

---

## Expected Row Counts

Approximate expected data (all metrics for all entities):

| Entity | Metrics | Months (5 yrs) | Expected Rows |
|--------|---------|----------------|---------------|
| Group | 15 | 60 | ~900 |
| Portugal | 15 | 60 | ~900 |
| Brazil | 15 | 60 | ~900 |
| Tunisia | 15 | 60 | ~900 |
| Lebanon | 15 | 60 | ~900 |
| Angola | 15 | 60 | ~900 |
| **Total** | **90 pairs** | **60 months** | **~5,400 rows** |

**Note:** Some entity-metric combinations may have sparse data (e.g., Angola headcount). Include rows only where data is available - do not include NULL or placeholder values.

---

## Data Quality Validation

Before publishing to Domo, verify:

- [ ] All 6 entities present with correct naming (Title Case)
- [ ] All 15 metrics mapped from ERP sources for **each entity** (lowercase_with_underscores)
- [ ] 90 entity-metric combinations populated (6 × 15)
- [ ] Date range covers at least 2020-2025 (60 months minimum)
- [ ] Units standardized (no kEUR, use M EUR)
- [ ] No duplicate rows (entity + metric + period)
- [ ] Sign conventions correct (costs negative, net_interest_expenses negative)
- [ ] Missing data documented (which entity-metric pairs have gaps)
- [ ] Each entity-metric pair has minimum 8 data points
- [ ] New metrics (cash_flow, trade_working_capital, net_interest_expenses) populated

---

## Integration with RAGLite

### Query Pattern

The RAGLite forecasting system queries Domo using SQL-like syntax:

```sql
SELECT entity, metric, period_date, value, unit
FROM financial_metrics
WHERE entity = 'Portugal'
  AND metric = 'ebitda'
  AND period_date >= '2020-01-01'
ORDER BY period_date ASC
```

### MCP Tool Integration

The `get_financial_forecast` MCP tool (defined in `raglite/mcp/tools/`) accepts requests like:

```json
{
  "metric": "ebitda",
  "entity": "Portugal",
  "horizon_months": 12,
  "include_confidence_intervals": true
}
```

The tool fetches historical data from Domo, validates quality, and generates forecasts.

### Data Quality Checks

The forecasting system automatically runs these checks (see `raglite/forecasting/data_quality/`):

1. **Gap Detection** - Identifies missing months in time series
2. **Outlier Detection** - Flags values > 3 standard deviations from mean
3. **Unit Mixing Detection** - Detects when kEUR vs M EUR may be mixed
4. **Trend Breaks** - Identifies sudden structural changes

---

## Troubleshooting

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Entity not found | `Entity 'PORTUGAL' not recognized` | Use Title Case: "Portugal" |
| Metric not found | `Metric 'Variable Cost' not found` | Use lowercase: "variable_cost" |
| Insufficient data | `MetricValidationError: 5 data points (min 8)` | Add more historical months |
| Unit mixing | `UnitMixingError: swing=1000x` | Verify kEUR vs M EUR conversion |
| Sign convention | Positive costs causing calculation errors | Make costs negative |

### Support

For questions about:
- **Metric definitions or ERP mappings** → Contact RAGLite Development Team
- **Data quality issues** → Check `raglite/forecasting/data_quality/` modules
- **Forecasting accuracy** → Review `docs/FORECASTING-VALIDATION-GUIDE.md`

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-01-30 | Added 3 new metrics: cash_flow, trade_working_capital, net_interest_expenses. Updated metric count from 12 to 15, entity-metric pairs from 72 to 90, expected rows from ~4,320 to ~5,400. |
| 1.0 | 2026-01-30 | Initial data dictionary specification |

---

## References

- RAGLite Forecasting Module: `raglite/forecasting/`
- Entity Patterns: `raglite/forecasting/timeseries/metadata.py`
- Data Quality Checks: `raglite/forecasting/data_quality/`
- MCP Tools: `raglite/mcp/tools/`
- Epic 4 PRD: `docs/prd/epic-4-forecasting-proactive-insights.md`
