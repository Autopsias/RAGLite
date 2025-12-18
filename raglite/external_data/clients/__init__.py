"""External data API clients.

Story 6.1: Tier 1 External Data Source Integration
Story 6.8: Tier 2 Data Sources & ML Enhancements (Conditional)
Story 6.9.6: Add ECB EURIBOR client for multivariate forecasting

Provides async clients for all Tier 1 and Tier 2 Portuguese and EU data sources.
"""

from raglite.external_data.clients.atic import ATICClient
from raglite.external_data.clients.basegov import BaseGovClient
from raglite.external_data.clients.bpstat import BPstatClient
from raglite.external_data.clients.commodities import CommoditiesClient
from raglite.external_data.clients.ecb import ECBClient
from raglite.external_data.clients.entsoe import ENTSOEClient
from raglite.external_data.clients.eu_oil_bulletin import EUOilBulletinClient
from raglite.external_data.clients.eurostat import EurostatClient
from raglite.external_data.clients.ice_futures import ICEFuturesClient
from raglite.external_data.clients.ine import INEClient
from raglite.external_data.clients.ipma import IPMAClient
from raglite.external_data.clients.omie import OMIEClient
from raglite.external_data.clients.ren import RENClient

__all__ = [
    # Tier 1 clients
    "INEClient",
    "ATICClient",
    "BPstatClient",
    "OMIEClient",
    "EUOilBulletinClient",
    "IPMAClient",
    "BaseGovClient",
    "CommoditiesClient",
    "ECBClient",
    # Tier 2 clients (Story 6.8)
    "ICEFuturesClient",
    "EurostatClient",
    # Story 6.29 P3 Phase 2
    "ENTSOEClient",
    # Story 7.0: REN Data Hub for electricity cost
    "RENClient",
]
