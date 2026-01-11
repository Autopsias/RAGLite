"""External data storage constants.

Story 8.2 Task 3.3: Extract constants from storage.py

Contains:
- Tier 2 source configuration (TIER2_SOURCES)
- Freshness thresholds by refresh frequency
- Model selection cache TTL
"""

from datetime import timedelta

# Freshness thresholds by refresh frequency
FRESHNESS_THRESHOLDS: dict[str, timedelta] = {
    "hourly": timedelta(hours=2),
    "daily": timedelta(days=2),
    "weekly": timedelta(days=10),
    "monthly": timedelta(days=45),
    "quarterly": timedelta(days=120),
    "annual": timedelta(days=400),
}

# Model selection cache TTL (Story 7b-4 AC-7b.4.5)
MODEL_SELECTION_TTL_DAYS = 7

# ===========================================================================
# Tier 2 Source Configuration (Story 6.8 AC3)
# ===========================================================================

# Source name constants for Tier 2 data sources
TIER2_SOURCES = {
    # Energy commodities (AC1.1, AC1.2)
    "ICE_API2_Coal": {
        "api_endpoint": "https://data.nasdaq.com/api/v3/datasets/CHRIS/ICE_ATW1",
        "data_type": "time_series",
        "refresh_frequency": "daily",
        "metrics": ["settlement_price"],
        "unit": "USD/tonne",
        "description": "API2 Coal (CIF ARA) - pet coke proxy (correlation 0.7-0.85)",
    },
    "ICE_TTF_Gas": {
        "api_endpoint": "https://data.nasdaq.com/api/v3/datasets/CHRIS/ICE_TFM1",
        "data_type": "time_series",
        "refresh_frequency": "daily",
        "metrics": ["settlement_price"],
        "unit": "EUR/MWh",
        "description": "TTF Natural Gas - critical for thermal energy forecasting",
    },
    # EU statistics (AC1.3)
    "Eurostat_Electricity": {
        "api_endpoint": "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1",
        "data_type": "time_series",
        "refresh_frequency": "monthly",
        "metrics": ["price_eur_kwh"],
        "unit": "EUR/kWh",
        "description": "EU electricity prices for industrial consumers (nrg_pc_204)",
    },
    # Portuguese indicators (AC2.1, AC2.2)
    "INE_HousePriceIndex": {
        "api_endpoint": "https://www.ine.pt/ine/json_indicador/",
        "data_type": "index",
        "refresh_frequency": "quarterly",
        "metrics": ["index_value", "yoy_change_pct"],
        "unit": "index (base 2015)",
        "description": "Portuguese House Price Index - leading indicator for construction",
    },
    "INE_ConstructionConfidence": {
        "api_endpoint": "https://www.ine.pt/ine/json_indicador/",
        "data_type": "index",
        "refresh_frequency": "monthly",
        "metrics": ["confidence_index"],
        "unit": "index",
        "description": "Construction sector confidence indicator",
    },
    "BPstat_BankAppraisals": {
        "api_endpoint": "https://bpstat.bportugal.pt/api/observations/",
        "data_type": "time_series",
        "refresh_frequency": "monthly",
        "metrics": ["avg_appraisal_eur_m2"],
        "unit": "EUR/m²",
        "description": "Average bank appraisal values for housing",
    },
}
