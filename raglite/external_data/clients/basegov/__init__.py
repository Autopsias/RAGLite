"""BaseGov client package for Portuguese public procurement data.

Story 8.2 Task 4: Refactored from monolithic basegov.py

Package structure:
- client.py: Main BaseGovClient class
- config.py: Constants and configuration
- impic.py: IMPIC XLSX data source
- ted_api.py: TED API data source
- ocds.py: OCDS data source (UNAVAILABLE - no resources)
- parsers.py: Response parsing functions

Data Sources:
1. dados.gov.pt IMPIC XLSX - ALL Portuguese contracts (2012-2025)
2. TED API v3 - Fallback for EU-threshold contracts only
3. dados.gov.pt OCDS dataset - UNAVAILABLE (no resources as of 2025-12-08)

Important Limitations:
- OCDS dataset has no resources - only IMPIC and TED API are functional
- Contracts below EU thresholds are NOT in TED (but ARE in IMPIC dataset)
- TED API only includes contracts above EU_THRESHOLD values

Public exports:
- BaseGovClient: Main client class
- API configuration constants (for backward compatibility)
"""

from raglite.external_data.clients.basegov.client import BaseGovClient
from raglite.external_data.clients.basegov.config import (
    BASEGOV_API_BASE,
    DADOS_GOV_API_BASE,
    OCDS_DATASET_ID,
    TED_API_BASE,
)

__all__ = [
    "BaseGovClient",
    "BASEGOV_API_BASE",
    "DADOS_GOV_API_BASE",
    "OCDS_DATASET_ID",
    "TED_API_BASE",
]
