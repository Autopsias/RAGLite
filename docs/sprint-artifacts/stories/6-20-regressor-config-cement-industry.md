# Story 6.20: Update Regressor Configuration for Cement Industry

**Epic:** 6 - Advanced Forecasting with External Data
**Sprint Change Proposal:** SCP-2025-12-12-001
**Status:** done
**Priority:** P1 (High)
**Estimated Effort:** 4 hours

---

## User Story

As a system, I want to update regressor mappings to use cement-industry-specific indicators instead of generic macro data, so that forecasting uses the most relevant predictors for each variable.

---

## Context

The cement industry has specific drivers for different metrics:
- **Demand-driven** (revenue, sales): Construction activity, building permits
- **Cost-driven** (variable cost, energy): Energy prices, industrial production
- **Pricing-driven** (selling price): Construction confidence, inflation

Previously, generic macro indicators were used. This story updates mappings to use cement-specific indicators from Stories 6.15-6.19.

---

## Acceptance Criteria

### AC1: All 6 New Regressors Registered in AVAILABLE_REGRESSORS
- [x] construction_output - Eurostat construction production index
- [x] industrial_production - Eurostat industrial production index
- [x] gdp_growth - ECB GDP growth rate
- [x] inflation - ECB HICP inflation
- [x] building_permits - INE with Eurostat fallback
- [x] construction_confidence - EC Business Surveys

### AC2: METRIC_REGRESSORS Updated with Optimal Mappings
- [x] Revenue: construction_output, gdp_growth, euribor_3m, building_permits
- [x] Sales Volume: construction_output, building_permits, gdp_growth, industrial_production
- [x] Variable Cost: ttf_gas, api2_coal, industrial_production, diesel
- [x] Electricity Cost: eurostat_electricity, industrial_production
- [x] Thermal Cost: api2_coal, ttf_gas, industrial_production
- [x] Avg Selling Price: construction_confidence, gdp_growth, inflation, diesel
- [x] Capacity Utilization: construction_output, gdp_growth, industrial_production

### AC3: Category-Based Selection Updated
- [x] Financial category: construction_output, gdp_growth, euribor_3m, building_permits
- [x] Energy category: eurostat_electricity, ttf_gas, api2_coal, industrial_production
- [x] Production category: construction_output, building_permits, industrial_production, gdp_growth
- [x] Pricing category: construction_confidence, gdp_growth, inflation, diesel

### AC4: Default Regressors Updated
- [x] Default regressors: construction_output, gdp_growth, euribor_3m

---

## Technical Design

### Updated METRIC_REGRESSORS

```python
METRIC_REGRESSORS: dict[str, list[str]] = {
    # Financial metrics - demand-driven
    "revenue": ["construction_output", "gdp_growth", "euribor_3m", "building_permits"],
    "sales_volume": ["construction_output", "building_permits", "gdp_growth", "industrial_production"],

    # Energy costs - energy price driven
    "electricity_cost": ["eurostat_electricity", "industrial_production"],
    "thermal_cost": ["api2_coal", "ttf_gas", "industrial_production"],

    # Variable cost - comprehensive energy mix
    "variable_cost": ["ttf_gas", "api2_coal", "industrial_production", "diesel"],

    # Pricing metrics - confidence + inflation driven
    "avg_selling_price": ["construction_confidence", "gdp_growth", "inflation", "diesel"],

    # Utilization metrics - construction demand driven
    "capacity_utilization": ["construction_output", "gdp_growth", "industrial_production"],
}
```

---

## Files Modified

| File | Changes |
|------|---------|
| `raglite/forecasting/regressor_config.py` | Updated METRIC_REGRESSORS, METRIC_CATEGORIES, DEFAULT_REGRESSORS |
| `tests/unit/test_regressor_config_cement.py` | 24 unit tests for AC1-AC4 |

---

## Workflow Status

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Create Story | done | This file |
| 2. Validate Story | done | All dependencies complete (6.16-6.19) |
| 3. Generate ATDD Tests | done | 24 unit tests created |
| 4. Implement | done | All mappings updated |
| 5. Code Review | done | Configuration follows patterns |
| 6. Test Expansion | done | Full coverage of ACs |
| 7. Test Review | done | 24/24 tests pass |
| 8. Quality Gate | done | All tests pass |

---

## Dependencies

- Story 6.16: Eurostat Construction & Industrial Indicators ✅
- Story 6.17: ECB Macroeconomic Indicators ✅
- Story 6.18: Fix INE Building Permits API ✅
- Story 6.19: EC Construction Confidence Index ✅
