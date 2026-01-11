"""Time series data quality checks - facade for backward compatibility."""

from collections.abc import Sequence

# Re-export all functions from legacy module
from ._legacy import (
    check_effective_frequency,
    check_missing_data_pattern,
    check_time_index_integrity,
)

__all__: Sequence[str] = [
    "check_effective_frequency",
    "check_time_index_integrity",
    "check_missing_data_pattern",
]
