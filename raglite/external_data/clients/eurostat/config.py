"""Eurostat API configuration and constants.

Story 8.2 Task 6: Eurostat client refactoring
"""

# Eurostat API Configuration
EUROSTAT_API_BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"

# Dataset codes
ELECTRICITY_DATASET = "nrg_pc_204"  # Electricity prices for industry
CONSTRUCTION_DATASET = "sts_copr_m"  # Construction production index
INDUSTRIAL_PRODUCTION_DATASET = "sts_inpr_m"  # Industrial production index
BUILDING_PERMITS_DATASET = "sts_cobp_m"  # Building permits (Story 6.18)
CONSTRUCTION_CONFIDENCE_DATASET = "ei_bsbu_m_r2"  # EC Business Surveys construction (Story 6.19)

# Consumption bands for industrial consumers
# https://ec.europa.eu/eurostat/statistics-explained/index.php/Glossary:Electricity_consumption_bands
CONSUMPTION_BANDS = {
    "IA": "< 20 MWh",
    "IB": "20-500 MWh",
    "IC": "500-2000 MWh",  # Default
    "ID": "2000-20000 MWh",
    "IE": "20000-70000 MWh",
    "IF": "70000-150000 MWh",
    "IG": "> 150000 MWh",
}
