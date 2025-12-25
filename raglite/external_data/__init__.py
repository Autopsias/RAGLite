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
    ENTSOEElectricityPrice,
    EUDieselPrice,
    EurostatConstructionOutput,
    EurostatIndustrialProduction,
    ExternalDataPoint,
    INEBuildingPermits,
    INEConstructionCostIndex,
    INEConstructionOutput,
    IPMAWeatherData,
    OMIEElectricityPrice,
    PetcokePrice,
)
from raglite.external_data.refresh import (
    BulkRefreshResult,
    RefreshResult,
    get_staleness_report,
    refresh_all_sources,
    refresh_source,
)
from raglite.external_data.scheduler import (
    RefreshFrequency,
    get_job_info,
    get_next_run_times,
    get_scheduler,
    shutdown_scheduler,
    start_scheduler,
)
from raglite.external_data.storage import (
    CachedModelSelection,
    ExternalDataStorage,
    cache_model_selection,
    cleanup_expired_model_selections,
    get_cached_model_selection,
    invalidate_all_model_selections,
    invalidate_model_selection,
)

__all__ = [
    # Exceptions
    "ExternalDataError",
    "ExternalDataFetchError",
    "ExternalDataValidationError",
    "ExternalDataStaleError",
    # Storage
    "ExternalDataStorage",
    # Model Selection Cache (Story 7b-4)
    "CachedModelSelection",
    "cache_model_selection",
    "get_cached_model_selection",
    "invalidate_model_selection",
    "invalidate_all_model_selections",
    "cleanup_expired_model_selections",
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
    # ENTSO-E Models (Story 6.29 P3)
    "ENTSOEElectricityPrice",
    # EU Oil Bulletin Models
    "EUDieselPrice",
    # Eurostat Models
    "EurostatConstructionOutput",
    "EurostatIndustrialProduction",
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
    # Scheduler (Story 6.5)
    "RefreshFrequency",
    "get_scheduler",
    "start_scheduler",
    "shutdown_scheduler",
    "get_job_info",
    "get_next_run_times",
    # Refresh (Story 6.5)
    "RefreshResult",
    "BulkRefreshResult",
    "refresh_source",
    "refresh_all_sources",
    "get_staleness_report",
]
