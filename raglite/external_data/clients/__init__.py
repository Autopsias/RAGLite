"""External data API clients.

Story 6.1: Tier 1 External Data Source Integration

Provides async clients for all Tier 1 Portuguese and EU data sources.
"""

from raglite.external_data.clients.atic import ATICClient
from raglite.external_data.clients.basegov import BaseGovClient
from raglite.external_data.clients.bpstat import BPstatClient
from raglite.external_data.clients.commodities import CommoditiesClient
from raglite.external_data.clients.eu_oil_bulletin import EUOilBulletinClient
from raglite.external_data.clients.ine import INEClient
from raglite.external_data.clients.ipma import IPMAClient
from raglite.external_data.clients.omie import OMIEClient

__all__ = [
    "INEClient",
    "ATICClient",
    "BPstatClient",
    "OMIEClient",
    "EUOilBulletinClient",
    "IPMAClient",
    "BaseGovClient",
    "CommoditiesClient",
]
