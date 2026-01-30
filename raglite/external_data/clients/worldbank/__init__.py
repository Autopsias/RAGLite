"""World Bank API client for GDP data.

Multi-Geography Enhancement: Provides GDP growth data for all Secil geographies.
"""

from raglite.external_data.clients.worldbank.client import (
    SECIL_COUNTRIES,
    WorldBankClient,
)

__all__ = ["WorldBankClient", "SECIL_COUNTRIES"]
