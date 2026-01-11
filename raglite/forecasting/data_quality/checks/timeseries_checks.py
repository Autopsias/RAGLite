"""Time series data quality checks.

Facade for backward compatibility - re-exports from refactored modules.

Checks for frequency patterns, time index integrity, and missing data.
"""

from raglite.forecasting.data_quality.checks.timeseries import (
    check_effective_frequency,
    check_missing_data_pattern,
    check_time_index_integrity,
)

__all__ = [
    "check_effective_frequency",
    "check_time_index_integrity",
    "check_missing_data_pattern",
]
