"""Configuration and constants for BaseGov client.

Story 8.2 Task 4: Extract constants from basegov.py
"""

from __future__ import annotations

from pathlib import Path

# API Configuration
# Story 6.9.5: Multiple data sources with fallback

# PRIMARY: dados.gov.pt IMPIC XLSX dataset (ALL Portuguese contracts)
DADOS_GOV_API_BASE = "https://dados.gov.pt/api/1"
IMPIC_CONTRACTS_DATASET = "contratos-publicos-portal-base-impic-contratos-de-2012-a-2025"

# FALLBACK: TED API v3 (EU public procurement, Portugal contracts above EU thresholds)
TED_API_BASE = "https://tedweb.api.ted.europa.eu/v3"

# DEPRECATED: dados.gov.pt OCDS dataset (empty resources as of 2025-12-08)
OCDS_DATASET_ID = "ocds-portal-base-www-base-gov-pt"

# Deprecated: Base.gov.pt (NO public API - HTML only)
BASEGOV_API_BASE = "https://www.base.gov.pt/Base4/pt/pesquisa"  # Does NOT work

# CPV codes for construction-related contracts
CPV_CONSTRUCTION = "45000000"  # Construction works
CPV_BUILDING = "45210000"  # Building construction
CPV_CIVIL_ENGINEERING = "45220000"  # Civil engineering
CPV_ROAD = "45233000"  # Highway construction

# EU procurement thresholds (approximate, as of 2024)
# Contracts below these thresholds are NOT in TED (but ARE in IMPIC dataset)
EU_THRESHOLD_WORKS = 5_382_000  # EUR for works
EU_THRESHOLD_SUPPLIES = 221_000  # EUR for supplies/services (central govt)
EU_THRESHOLD_SERVICES = 221_000  # EUR for services

# Cache configuration
CACHE_DIR = Path(".cache/external_data")
CACHE_TTL_HOURS = 24  # XLSX files are updated daily/weekly
