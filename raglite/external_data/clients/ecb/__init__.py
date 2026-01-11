"""ECB client package for European Central Bank statistical data.

Story 8.2 Task 5: Refactored from monolithic ecb.py

Package structure:
- client.py: Main ECBClient class
- config.py: API constants and series keys
- models.py: Data models (EuriborRate, ECBGDPGrowth, ECBInflation)
- fetchers.py: API fetch methods with retry logic
- parsers.py: CSV response parsing functions
- utils.py: Utility functions (period parsing, interpolation)

Public exports:
- ECBClient: Main client class
- EuriborRate, ECBGDPGrowth, ECBInflation: Data models
- interpolate_quarterly_to_monthly: Utility function
"""

from raglite.external_data.clients.ecb.client import ECBClient
from raglite.external_data.clients.ecb.models import ECBGDPGrowth, ECBInflation, EuriborRate
from raglite.external_data.clients.ecb.utils import interpolate_quarterly_to_monthly

__all__ = [
    "ECBClient",
    "EuriborRate",
    "ECBGDPGrowth",
    "ECBInflation",
    "interpolate_quarterly_to_monthly",
]
