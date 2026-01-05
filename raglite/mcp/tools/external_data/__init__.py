"""External data MCP tools - facade for backward compatibility.

This module provides MCP tools for querying external financial data sources.
All functions are re-exported from submodules for backward compatibility.
"""

from raglite.shared.logging import get_logger

# Re-export from modularized files (all migrated!)
from .date_utils import _parse_date_range
from .query_helpers import (
    _query_all_sources,
    _query_single_source,
)
from .response_formatters import (
    _format_response,
    _get_visualization_hint,
)
from .tools import (
    query_external_data,
    refresh_external_data,
)

logger = get_logger(__name__)

__all__ = [
    "refresh_external_data",
    "query_external_data",
    "_parse_date_range",
    "_get_visualization_hint",
    "_query_single_source",
    "_query_all_sources",
    "_format_response",
]
