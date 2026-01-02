"""Pydantic models for external data sources.

Story 6.1: Tier 1 External Data Source Integration
Epic 8: Technical Debt Reduction - Refactored from monolithic file

This module serves as a facade that re-exports all models from specialized modules:
- models_base.py: Base enums and types
- models_tier1.py: Tier 1 data sources (INE, ATIC, BPstat, OMIE, EU Oil, IPMA, BaseGov, Commodities)
- models_tier2.py: Tier 2 data sources (Eurostat, ENTSO-E, REN, API2Coal, TTFGas)
- models_forecasting.py: Forecasting models (ModelWeight, ModelRegistry, RetrainResult)
- models_storage.py: Storage models (ExternalDataPoint)

All imports are preserved for backward compatibility.
"""

from __future__ import annotations

# Base types and enums
from .models_base import DataFrequency, DataSource

# Forecasting models
from .models_forecasting import ModelRegistry, ModelWeight, RetrainResult

# Storage models
from .models_storage import ExternalDataPoint

# Tier 1 data sources
from .models_tier1 import (
    ATICCementConsumption,
    BaseGovContract,
    BPstatMortgageLoans,
    CO2EUAPrice,
    CoalPrice,
    CommodityPrice,
    EUDieselPrice,
    INEBuildingPermits,
    INEConstructionCostIndex,
    INEConstructionOutput,
    IPMAWeatherData,
    OMIEElectricityPrice,
    PetcokePrice,
)

# Tier 2 data sources and demand-side regressors
from .models_tier2 import (
    API2CoalPrice,
    BPstatBankAppraisal,
    ECConstructionConfidence,
    ENTSOEElectricityPrice,
    EurostatBuildingPermits,
    EurostatConstructionOutput,
    EurostatDwellingCompletions,
    EurostatElectricityPrice,
    EurostatHousingTransactions,
    EurostatIndustrialProduction,
    INEConstructionConfidence,
    INEHousePriceIndex,
    RENElectricityPrice,
    TTFGasPrice,
)

__all__ = [
    # Base types
    "DataFrequency",
    "DataSource",
    # Tier 1 models
    "INEBuildingPermits",
    "INEConstructionOutput",
    "INEConstructionCostIndex",
    "ATICCementConsumption",
    "BPstatMortgageLoans",
    "OMIEElectricityPrice",
    "EUDieselPrice",
    "IPMAWeatherData",
    "BaseGovContract",
    "CommodityPrice",
    "CoalPrice",
    "PetcokePrice",
    "CO2EUAPrice",
    # Tier 2 models
    "API2CoalPrice",
    "TTFGasPrice",
    "EurostatElectricityPrice",
    "ENTSOEElectricityPrice",
    "RENElectricityPrice",
    "EurostatConstructionOutput",
    "EurostatIndustrialProduction",
    "EurostatBuildingPermits",
    "ECConstructionConfidence",
    "INEHousePriceIndex",
    "INEConstructionConfidence",
    "BPstatBankAppraisal",
    "EurostatHousingTransactions",
    "EurostatDwellingCompletions",
    # Storage models
    "ExternalDataPoint",
    # Forecasting models
    "ModelWeight",
    "ModelRegistry",
    "RetrainResult",
]
