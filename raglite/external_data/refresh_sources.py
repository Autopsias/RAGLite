"""Individual source refresh functions for external data sources.

Each function fetches data from a specific external API and stores it in the database.
All functions use retry_with_backoff for resilient operation.

This module acts as a facade, re-exporting refresh functions from domain-specific modules:
- refresh_sources_energy: Energy and commodities (IPMA, OMIE, CO2, Diesel)
- refresh_sources_economic: Economic indicators (INE, BPstat, ATIC)
"""

from __future__ import annotations

from dataclasses import dataclass

# Import all refresh functions from domain modules
from raglite.external_data.refresh_sources_economic import (
    refresh_atic_cement,
    refresh_bpstat_mortgage,
    refresh_ine_building_permits,
    refresh_ine_construction,
    refresh_ine_cost_index,
)
from raglite.external_data.refresh_sources_energy import (
    refresh_commodities_co2,
    refresh_diesel_prices,
    refresh_ipma,
    refresh_omie,
)


@dataclass
class RefreshResult:
    """Result of a single source refresh operation."""

    source_name: str
    success: bool
    records_updated: int = 0
    duration_seconds: float = 0.0
    error_message: str | None = None
    attempts: int = 1


# Re-export all refresh functions for backward compatibility
__all__ = [
    "RefreshResult",
    "refresh_ipma",
    "refresh_omie",
    "refresh_commodities_co2",
    "refresh_ine_building_permits",
    "refresh_bpstat_mortgage",
    "refresh_diesel_prices",
    "refresh_ine_construction",
    "refresh_ine_cost_index",
    "refresh_atic_cement",
    "SOURCE_REFRESH_FUNCTIONS",
]


# Source name to refresh function mapping
SOURCE_REFRESH_FUNCTIONS = {
    "IPMA": refresh_ipma,
    "OMIE": refresh_omie,
    "CO2_EUA": refresh_commodities_co2,
    "INE_BuildingPermits": refresh_ine_building_permits,
    "BPstat_MortgageLoans": refresh_bpstat_mortgage,
    "EUOil_Diesel": refresh_diesel_prices,
    "INE_ConstructionOutput": refresh_ine_construction,
    "INE_ConstructionCostIndex": refresh_ine_cost_index,
    "ATIC_CementConsumption": refresh_atic_cement,
}
