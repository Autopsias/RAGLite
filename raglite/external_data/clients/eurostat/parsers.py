"""Eurostat response parsers.

This module provides a facade for backward compatibility, re-exporting all
parser functions from the internal implementation modules.

Story 8.2 Task 6: Eurostat client refactoring
"""

# Re-export all parser functions from internal modules
from raglite.external_data.clients.eurostat.parsers_internal.sdmx_parsers import (
    parse_construction_data,
    parse_industrial_data,
    parse_sdmx_index_data,
)
from raglite.external_data.clients.eurostat.parsers_internal.simple_parsers import (
    parse_building_permits_data,
    parse_construction_confidence_data,
    parse_electricity_data,
)

# Public API
__all__ = [
    "parse_electricity_data",
    "parse_construction_data",
    "parse_industrial_data",
    "parse_building_permits_data",
    "parse_construction_confidence_data",
    "parse_sdmx_index_data",  # Used internally by client.py
]
