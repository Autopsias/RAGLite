"""Constants for ENTSOE client.

Story 6.29 P3: Phase 2 - Electricity Price Integration for Electricity Cost Regressor
"""

# Ember Energy CSV URLs (Google Cloud Storage - public access)
EMBER_DAILY_CSV_URL = "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/price/outputs/european_wholesale_electricity_price_data_daily.csv"
EMBER_MONTHLY_CSV_URL = "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/price/outputs/european_wholesale_electricity_price_data_monthly.csv"

# Country codes mapping (ISO 2-letter -> ISO 3-letter for Ember CSV)
COUNTRY_CODES = {
    "PT": "PRT",  # Portugal
    "ES": "ESP",  # Spain
    "FR": "FRA",  # France
    "DE": "DEU",  # Germany
    "IT": "ITA",  # Italy
    "UK": "GBR",  # United Kingdom
    "NL": "NLD",  # Netherlands
    "BE": "BEL",  # Belgium
    "PL": "POL",  # Poland
    "CZ": "CZE",  # Czechia
    "AT": "AUT",  # Austria
    "SE": "SWE",  # Sweden
    "DK": "DNK",  # Denmark
    "NO": "NOR",  # Norway
    "FI": "FIN",  # Finland
}
