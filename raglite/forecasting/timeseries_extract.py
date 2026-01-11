"""Time-series data extraction from financial documents.

DEPRECATED: This module is a backward-compatibility shim.

Story 8.1: This file has been refactored into the `timeseries` package.
Import from `raglite.forecasting.timeseries` instead.

Example:
    # Old (deprecated)
    from raglite.forecasting.timeseries_extract import extract_timeseries

    # New (recommended)
    from raglite.forecasting.timeseries import extract_timeseries
"""

import warnings

# Re-export all public APIs from the new package
from raglite.forecasting.timeseries import (  # noqa: F401
    CURRENCY_TO_EUR,
    EBITDA_ENTITY_PATTERNS,
    EBITDA_VALUE_THRESHOLDS,
    ENTITY_PATTERNS,
    METRIC_CATEGORY_MAP,
    METRIC_SEARCH_PATTERNS,
    ExtractionError,
    MetricValidationError,
    detect_entity,
    extract_ebitda_from_qdrant_chunks,
    extract_external_regressor_timeseries,
    extract_external_timeseries,
    extract_metric_from_qdrant_chunks,
    extract_timeseries,
    extract_timeseries_from_sql,
    extract_variable_cost_from_qdrant_chunks,
    normalize_to_interval,
    parse_fiscal_date,
    parse_period_to_date,
    prefer_group_level,
)

# Emit deprecation warning when this module is imported
warnings.warn(
    "Importing from raglite.forecasting.timeseries_extract is deprecated. "
    "Import from raglite.forecasting.timeseries instead. "
    "This shim will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "extract_timeseries",
    "extract_external_timeseries",
    "extract_external_regressor_timeseries",
    "ExtractionError",
    "MetricValidationError",
    "extract_timeseries_from_sql",
    "prefer_group_level",
    "extract_ebitda_from_qdrant_chunks",
    "extract_variable_cost_from_qdrant_chunks",
    "extract_metric_from_qdrant_chunks",
    "parse_fiscal_date",
    "normalize_to_interval",
    "parse_period_to_date",
    "detect_entity",
    "EBITDA_ENTITY_PATTERNS",
    "EBITDA_VALUE_THRESHOLDS",
    "METRIC_CATEGORY_MAP",
    "METRIC_SEARCH_PATTERNS",
    "ENTITY_PATTERNS",
    "CURRENCY_TO_EUR",
]
