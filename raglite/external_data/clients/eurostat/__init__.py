"""Eurostat client package for EU statistics.

Story 8.2 Task 6: Refactored from monolithic eurostat.py

Package structure:
- client.py: Main EurostatClient class
- config.py: API constants and dataset codes
- fetchers.py: API fetch methods with retry logic
- parsers.py: Response parsing functions
- utils.py: Utility functions (period parsing)

Public exports:
- EurostatClient: Main client class
- Dataset constants: For backward compatibility
"""

from raglite.external_data.clients.eurostat.client import EurostatClient
from raglite.external_data.clients.eurostat.config import (
    BUILDING_PERMITS_DATASET,
    CONSTRUCTION_CONFIDENCE_DATASET,
    CONSTRUCTION_DATASET,
    CONSUMPTION_BANDS,
    ELECTRICITY_DATASET,
    INDUSTRIAL_PRODUCTION_DATASET,
)

__all__ = [
    "EurostatClient",
    # Config constants for backward compatibility
    "ELECTRICITY_DATASET",
    "CONSTRUCTION_DATASET",
    "INDUSTRIAL_PRODUCTION_DATASET",
    "BUILDING_PERMITS_DATASET",
    "CONSTRUCTION_CONFIDENCE_DATASET",
    "CONSUMPTION_BANDS",
]
