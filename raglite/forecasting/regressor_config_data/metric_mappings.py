"""Metric-to-regressor mappings for multi-variate forecasting.

Story 6.10.5: Updated to use only working external data sources
Story 6.11.2: Auto-Regressor Selection by Metric Type
Story 6.16: Added construction_output and industrial_production
Story 6.17: Added gdp_growth and inflation for macroeconomic context
Story 6.18: Added building_permits (INE with Eurostat fallback)
Story 6.19: Added construction_confidence (EC Business Surveys)
Story 6.20: Optimized mappings for cement industry variables
Story 6.23: DISABLED all regressors - flat growth Prophet achieves better accuracy
Story 6.25: RE-ENABLED regressors for key metrics based on validation results
Story 7.0: REN electricity replaces eurostat_electricity
Story 7b-7: Added demand-side regressors (housing_transactions, dwelling_completions)
Epic 7: Added sales_volume and capacity_utilization regressors

This module provides:
- Per-metric regressor mappings
- Category-based auto-selection
- Default fallback configuration

NOTE: This module must not import from other forecasting modules to avoid circular dependencies.
"""

# =============================================================================
# Per-Metric Regressor Mappings
# =============================================================================

# Story 6.25: RE-ENABLED regressors for key financial metrics based on validation results
# Story 6.20: Cement industry regressors - construction-focused indicators
# P2 Features: Financial metrics now use appropriate regressors for better forecasting
# Revenue: Core financial metric benefits from construction and macroeconomic indicators
# Story 7b-7: Added housing_transactions as demand-side regressor
METRIC_REGRESSORS: dict[str, list[str]] = {
    # Story 6.25: RE-ENABLED regressors for key financial metrics based on validation results
    # Story 6.20: Cement industry regressors - construction-focused indicators
    # P2 Features: Financial metrics now use appropriate regressors for better forecasting
    # Revenue: Core financial metric benefits from construction and macroeconomic indicators
    # Story 7b-7: Added housing_transactions as demand-side regressor
    "revenue": [
        "construction_output",
        "building_permits",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "gdp_growth",
        "euribor_3m",  # Financial regressor for cost of capital
    ],
    "turnover": [
        "construction_output",
        "building_permits",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "gdp_growth",
    ],
    "turnover+vat": [
        "construction_output",
        "building_permits",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "gdp_growth",
    ],
    # EBITDA: Story 7b-7 fix - Added demand-side regressors for construction revenue
    # Portugal = 72% of Secil EBITDA, so construction demand is critical
    # EBITDA = Revenue - Costs: demand (revenue driver) and cost inputs
    # NOTE: euribor_3m removed per Story 7b-7 AC5 - less relevant to cement EBITDA
    # Epic 7 Enhancement: Added sales_volume and capacity_utilization per McKinsey research
    # Multi-Geography Enhancement: Added gdp_weighted_composite to capture all Secil markets
    # EBITDA forecast fix (2026-02-03): Prioritized construction market indicators per user insight
    # Cement industry EBITDA is highly correlated with construction activity and building licenses
    "ebitda": [
        # PRIMARY: Construction market indicators (highest correlation for cement industry)
        # Building permits = leading indicator (6-12 month lag before construction)
        # Construction output = coincident indicator of market activity
        # Construction confidence = leading sentiment indicator
        "building_permits",  # Priority #1: Leading indicator for cement demand
        "construction_output",  # Priority #2: Coincident construction activity
        "construction_confidence",  # Priority #3: Leading sentiment indicator
        # SECONDARY: Housing market (demand-side)
        "housing_transactions",  # Story 7b-7: Leading indicator (6-12 month lag)
        "dwelling_completions",  # Lagging indicator confirming construction activity
        # TERTIARY: Volume and GDP for context
        "sales_volume",  # Epic 7: Direct demand indicator for Portugal operations
        "gdp_weighted_composite",  # World Bank: weighted GDP for all Secil markets
        # QUATERNARY: Cost-side (energy costs -> margins)
        "ttf_gas",
        "diesel",
        "capacity_utilization",  # Epic 7: Efficiency factor affecting margins
    ],
    # Sales metrics benefit from economic indicators
    # Story 6.16: Added construction_output and industrial_production for sales metrics
    # Story 6.20: Cement industry - building permits for construction volume tracking
    "sales": ["construction_output", "building_permits", "euribor_3m"],
    # Forecasting Quality Enhancement: Added construction_confidence for market sentiment
    # Story 7b-7: Pure demand-side regressors for sales volume (removed euribor_3m)
    "sales_volume": [
        "construction_output",
        "building_permits",
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "dwelling_completions",  # Story 7b-7: Lagging demand indicator
    ],
    "sales volumes": [
        "construction_output",
        "building_permits",
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "dwelling_completions",  # Story 7b-7: Lagging demand indicator
    ],
    "sales volume": [
        "construction_output",
        "building_permits",
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "dwelling_completions",  # Story 7b-7: Lagging demand indicator
    ],
    # Story 7.0: REN electricity replaces eurostat_electricity (9 points → 60+ monthly)
    # Story 6.25: RE-ENABLED energy cost regressors based on validation results
    # Story 6.20: Cement industry - electricity and production activity linked
    "electricity_cost": ["ren_electricity", "ttf_gas"],  # Story 7.0: REN spot prices with gas proxy
    "electrical energy": ["ren_electricity", "ttf_gas"],
    # Thermal cost continues with energy commodity regressors
    # Story 6.20: Cement industry - industrial production drives thermal energy demand
    "thermal_cost": ["api2_coal", "ttf_gas", "industrial_production"],
    "thermal energy": ["api2_coal", "ttf_gas", "industrial_production"],
    # Variable Cost: Story 6.20: Cement industry - energy and industrial activity
    # Story 6.25 fix - re-enabled energy regressors for 66% MAPE improvement
    # Epic 7 Enhancement: Multi-factor approach per manufacturing research
    # Variable costs depend on: raw materials, labor, energy, logistics
    "variable_cost": [
        "api2_coal",
        "ttf_gas",
        "industrial_production",
        "sales_volume",  # Epic 7: Volume affects unit cost (economies of scale)
        "diesel",  # Epic 7: Logistics/transport costs
        "capacity_utilization",  # Epic 7: Efficiency factor
    ],
    "variable cost": [
        "api2_coal",
        "ttf_gas",
        "industrial_production",
        "sales_volume",  # Epic 7: Volume affects unit cost (economies of scale)
        "diesel",  # Epic 7: Logistics/transport costs
        "capacity_utilization",  # Epic 7: Efficiency factor
    ],
    # Pricing metrics benefit from energy and economic indicators
    # Story 6.20: Cement industry - confidence and inflation drive pricing decisions
    # Story 7b-7: Added housing_transactions as demand-side regressor for pricing
    "avg_selling_price": [
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "building_permits",
        "inflation",
    ],
    "sales price em - cement": [
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "building_permits",
        "inflation",
    ],
    "sales price im": [
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "building_permits",
        "inflation",
    ],
    # Utilization metrics benefit from economic indicators
    # Story 6.16: Added industrial_production and construction_output for production metrics
    # Story 7b-7: Added demand-side regressors for capacity utilization
    "capacity_utilization": [
        "construction_output",
        "building_permits",
        "construction_confidence",
        "industrial_production",
    ],
    "frequency ratio": [
        "euribor_3m",
        "diesel",
        "ttf_gas",
        "industrial_production",
        "construction_output",
    ],
    # Story 6.24: CO2 EUA pricing - energy market driven
    # Use exact validation config that achieved 0.20% MAPE (99.6% improvement from 50.01%)
    # 2022 energy crisis showed 0.7-0.9 correlation between CO2 and energy prices
    "co2_eua_price": ["ttf_gas", "api2_coal", "eurostat_electricity"],
    "co2": ["ttf_gas", "api2_coal", "eurostat_electricity"],
    "carbon": ["ttf_gas", "api2_coal", "eurostat_electricity"],
    "eua": ["ttf_gas", "api2_coal", "eurostat_electricity"],
}


# =============================================================================
# Category-Based Regressor Selection
# =============================================================================

# Story 6.11.2: Auto-select regressors based on metric category
# Story 6.17: Added gdp_growth and inflation to relevant categories
# Story 6.20: Optimized for cement industry with construction indicators
METRIC_CATEGORIES: dict[str, dict[str, list[str]]] = {
    "financial": {
        # Revenue, EBITDA, sales, costs - construction demand driven
        # Story 7b-7: Added housing_transactions as demand-side regressor
        "keywords": ["revenue", "turnover", "ebitda", "sales", "cost", "expense", "profit"],
        "regressors": [
            "construction_output",
            "building_permits",
            "housing_transactions",  # Story 7b-7
            "gdp_growth",
            "euribor_3m",  # Financial regressor for cost of capital
        ],
    },
    "energy": {
        # Electricity, thermal costs, fuel - energy prices + production
        # Story 7.0: Use ren_electricity (60+ points) instead of eurostat_electricity (9 points)
        "keywords": ["electricity", "thermal", "energy", "fuel", "power"],
        "regressors": ["ren_electricity", "ttf_gas", "api2_coal", "industrial_production"],
    },
    "production": {
        # Volume, utilization, capacity - construction indicators
        # Story 7b-7: Added housing_transactions as demand-side regressor
        "keywords": [
            "volume",
            "capacity",
            "utilization",
            "production",
            "output",
            "frequency",
            "ratio",
        ],
        "regressors": [
            "construction_output",
            "building_permits",
            "construction_confidence",
            "housing_transactions",  # Story 7b-7
            "industrial_production",
            "euribor_3m",  # Financial regressor for financing-driven demand
        ],
    },
    "pricing": {
        # Selling prices - confidence + inflation driven
        # Story 7b-7: Added housing_transactions as demand-side regressor
        "keywords": ["price", "selling", "asp", "unit price"],
        "regressors": [
            "construction_confidence",
            "housing_transactions",  # Story 7b-7
            "building_permits",
            "inflation",
        ],
    },
    "commodity": {
        # Commodity prices - energy inputs
        "keywords": ["coal", "gas", "petcoke", "co2", "carbon"],
        "regressors": ["ttf_gas", "api2_coal", "industrial_production"],
    },
}

# Default regressors when no match is found (Story 6.20: Cement industry construction focus)
DEFAULT_REGRESSORS: list[str] = ["construction_output", "euribor_3m", "gdp_growth"]
