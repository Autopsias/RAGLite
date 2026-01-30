"""Regressor metadata definitions.

Story 6.22: MCP Validation Tool Integration
Story 7.0: REN electricity regressor
Story 7b-7: Demand-side regressors (housing_transactions, dwelling_completions)

This module provides:
- Available regressors list
- Regressor metadata (display names, sources, units)

NOTE: This module must not import from other forecasting modules to avoid circular dependencies.
"""

# =============================================================================
# Available Regressors
# =============================================================================

AVAILABLE_REGRESSORS: list[str] = [
    # Cost-side regressors (energy, financing)
    "euribor_3m",  # ECB EURIBOR 3-month rate
    "ttf_gas",  # ICE TTF natural gas futures
    "api2_coal",  # ICE API2 coal futures
    "diesel",  # EU Oil Bulletin diesel prices
    "eurostat_electricity",  # Eurostat industrial electricity prices
    "ren_electricity",  # REN Data Hub Portuguese spot electricity (Story 7.0)
    # Economic indicators - Portugal (ECB)
    "gdp_growth",  # ECB GDP growth rate YoY (Story 6.17)
    "inflation",  # ECB HICP inflation index (Story 6.17)
    # Economic indicators - Multi-geography (World Bank)
    "gdp_portugal_wb",  # World Bank GDP growth - Portugal
    "gdp_tunisia",  # World Bank GDP growth - Tunisia
    "gdp_angola",  # World Bank GDP growth - Angola
    "gdp_brazil",  # World Bank GDP growth - Brazil
    "gdp_lebanon",  # World Bank GDP growth - Lebanon
    "gdp_weighted_composite",  # Weighted GDP composite (all Secil geographies)
    # Demand-side regressors (construction activity) - Story 7b-7
    "construction_output",  # Eurostat construction production index (Story 6.16)
    "industrial_production",  # Eurostat industrial production index (Story 6.16)
    "building_permits",  # INE building permits with Eurostat fallback (Story 6.18)
    "construction_confidence",  # EC Business Surveys via Eurostat (Story 6.19)
    "housing_transactions",  # Eurostat prc_hpi_inx quarterly->monthly (Story 7b-7)
    "dwelling_completions",  # Eurostat sts_cobp_m monthly (Story 7b-7)
    # NOTE: The following are currently disabled due to API issues (Story 6.10.5):
    # "hpi",  # INE house price index
    # "omie_spot",  # OMIE spot electricity (too slow - 1000+ HTTP requests)
]


# =============================================================================
# Regressor Metadata (Story 6.22: MCP Validation Tool Integration)
# =============================================================================

# Single source of truth for regressor display names, sources, and units
# Used by list_available_regressors and get_regressor_data MCP tools
REGRESSOR_METADATA: dict[str, dict[str, str]] = {
    "euribor_3m": {
        "display_name": "3-Month EURIBOR Rate",
        "source": "ECB",
        "unit": "%",
    },
    "ttf_gas": {
        "display_name": "TTF Natural Gas Price",
        "source": "ICE",
        "unit": "EUR/MWh",
    },
    "api2_coal": {
        "display_name": "API2 Coal Price",
        "source": "ICE",
        "unit": "USD/ton",
    },
    "diesel": {
        "display_name": "Diesel Price (EU)",
        "source": "EU Oil Bulletin",
        "unit": "EUR/litre",
    },
    "eurostat_electricity": {
        "display_name": "Industrial Electricity Price",
        "source": "Eurostat",
        "unit": "EUR/kWh",
    },
    "construction_output": {
        "display_name": "Construction Production Index (Portugal)",
        "source": "Eurostat",
        "unit": "Index",
    },
    "industrial_production": {
        "display_name": "Industrial Production Index (Portugal)",
        "source": "Eurostat",
        "unit": "Index",
    },
    "gdp_growth": {
        "display_name": "Portugal GDP Growth (YoY)",
        "source": "ECB",
        "unit": "%",
    },
    "inflation": {
        "display_name": "Portugal HICP Inflation",
        "source": "ECB",
        "unit": "%",
    },
    "building_permits": {
        "display_name": "Building Permits (Portugal)",
        "source": "Eurostat/INE",
        "unit": "Count",
    },
    "construction_confidence": {
        "display_name": "Construction Confidence Indicator",
        "source": "EC",
        "unit": "Balance %",
    },
    "ren_electricity": {
        "display_name": "Portuguese Electricity Spot Price",
        "source": "REN",
        "unit": "EUR/MWh",
    },
    # Story 7b-7: Demand-side regressors
    "housing_transactions": {
        "display_name": "Housing Transactions (Portugal)",
        "source": "Eurostat",
        "unit": "Count (quarterly, interpolated to monthly)",
    },
    "dwelling_completions": {
        "display_name": "Dwelling Completions (Portugal)",
        "source": "Eurostat",
        "unit": "Count (monthly)",
    },
    # Multi-geography GDP regressors (World Bank)
    "gdp_portugal_wb": {
        "display_name": "Portugal GDP Growth (World Bank)",
        "source": "World Bank",
        "unit": "%",
        "description": "Annual GDP growth rate, interpolated to monthly",
    },
    "gdp_tunisia": {
        "display_name": "Tunisia GDP Growth",
        "source": "World Bank",
        "unit": "%",
        "description": "Annual GDP growth rate, interpolated to monthly",
    },
    "gdp_angola": {
        "display_name": "Angola GDP Growth",
        "source": "World Bank",
        "unit": "%",
        "description": "Annual GDP growth rate, interpolated to monthly",
    },
    "gdp_brazil": {
        "display_name": "Brazil GDP Growth",
        "source": "World Bank",
        "unit": "%",
        "description": "Annual GDP growth rate, interpolated to monthly",
    },
    "gdp_lebanon": {
        "display_name": "Lebanon GDP Growth",
        "source": "World Bank",
        "unit": "%",
        "description": "Annual GDP growth rate, interpolated to monthly",
    },
    "gdp_weighted_composite": {
        "display_name": "Weighted GDP Composite (All Geographies)",
        "source": "World Bank",
        "unit": "%",
        "description": "72% PT + 10% TN + 8% AO + 7% BR + 3% LB",
    },
}
