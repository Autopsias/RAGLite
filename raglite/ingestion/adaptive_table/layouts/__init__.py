"""Standard pivot table layout extraction - Facade for backward compatibility.

This module provides backward-compatible re-exports for all layout extraction functions.
Internal implementation is split across domain modules for maintainability.

Public API (re-exported):
- _extract_temporal_cols_metric_rows
- _extract_entity_cols_metric_rows
- _extract_transposed_entity_cols_metric_row_labels
"""

# Re-export all public functions from domain modules
from .entity_metric import (
    _extract_entity_cols_metric_rows,
    _extract_temporal_cols_metric_rows,
)
from .transposed import _extract_transposed_entity_cols_metric_row_labels

__all__ = [
    "_extract_temporal_cols_metric_rows",
    "_extract_entity_cols_metric_rows",
    "_extract_transposed_entity_cols_metric_row_labels",
]
