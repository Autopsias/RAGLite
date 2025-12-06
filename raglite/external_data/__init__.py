"""External data integration for RAGLite.

Story 6.1: Tier 1 External Data Source Integration

This module provides async API clients for Portuguese and EU economic data sources
to enhance forecasting models with macro-economic drivers.

Tier 1 Sources:
- INE: Building permits, construction output/cost index
- ATIC: Cement consumption (CSV upload)
- BPstat: Mortgage loans
- OMIE: Electricity prices
- EU Oil Bulletin: Diesel prices
- IPMA: Weather data (temperature, rainfall)
- Base.gov.pt: Public works contracts
- Commodities: Coal, petcoke, CO2 EUA prices

Example:
    >>> from raglite.external_data.clients import INEClient
    >>> client = INEClient()
    >>> permits = await client.fetch_building_permits(
    ...     start_date=date(2024, 1, 1),
    ...     end_date=date(2024, 3, 31)
    ... )
"""

from raglite.external_data.exceptions import (
    ExternalDataError,
    ExternalDataFetchError,
    ExternalDataStaleError,
    ExternalDataValidationError,
)
from raglite.external_data.models import (
    ATICCementConsumption,
    BaseGovContract,
    BPstatMortgageLoans,
    CO2EUAPrice,
    CoalPrice,
    CommodityPrice,
    DataFrequency,
    DataSource,
    EUDieselPrice,
    ExternalDataPoint,
    INEBuildingPermits,
    INEConstructionCostIndex,
    INEConstructionOutput,
    IPMAWeatherData,
    OMIEElectricityPrice,
    PetcokePrice,
)
from raglite.external_data.storage import ExternalDataStorage

__all__ = [
    # Exceptions
    "ExternalDataError",
    "ExternalDataFetchError",
    "ExternalDataValidationError",
    "ExternalDataStaleError",
    # Storage
    "ExternalDataStorage",
    # Enums
    "DataSource",
    "DataFrequency",
    # INE Models
    "INEBuildingPermits",
    "INEConstructionOutput",
    "INEConstructionCostIndex",
    # ATIC Models
    "ATICCementConsumption",
    # BPstat Models
    "BPstatMortgageLoans",
    # OMIE Models
    "OMIEElectricityPrice",
    # EU Oil Bulletin Models
    "EUDieselPrice",
    # IPMA Models
    "IPMAWeatherData",
    # Base.gov.pt Models
    "BaseGovContract",
    # Commodities Models
    "CommodityPrice",
    "CoalPrice",
    "PetcokePrice",
    "CO2EUAPrice",
    # Storage Model
    "ExternalDataPoint",
]
