"""Timeseries extraction package.

Story 8.1 refactoring: Split timeseries_extract.py into modules < 500 LOC.
"""

# Re-export public API
from raglite.forecasting.timeseries.core import extract_timeseries
from raglite.forecasting.timeseries.external import (
    extract_external_regressor_timeseries,
    extract_external_timeseries,
)
from raglite.forecasting.timeseries.metadata import (
    CURRENCY_TO_EUR,
    EBITDA_ENTITY_PATTERNS,
    EBITDA_VALUE_THRESHOLDS,
    ENTITY_PATTERNS,
    METRIC_CATEGORY_MAP,
    METRIC_SEARCH_PATTERNS,
    ExtractionError,
    MetricValidationError,
    detect_entity,
)
from raglite.forecasting.timeseries.parsing import (
    normalize_to_interval,
    parse_fiscal_date,
    parse_period_to_date,
)
from raglite.forecasting.timeseries.qdrant_ebitda import (
    extract_ebitda_from_qdrant_chunks,
)
from raglite.forecasting.timeseries.qdrant_metric import (
    extract_metric_from_qdrant_chunks,
)
from raglite.forecasting.timeseries.qdrant_variable_cost import (
    extract_variable_cost_from_qdrant_chunks,
)
from raglite.forecasting.timeseries.sql_extraction import (
    extract_timeseries_from_sql,
    prefer_group_level,
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
