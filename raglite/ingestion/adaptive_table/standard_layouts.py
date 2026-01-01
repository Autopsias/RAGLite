"""
Standard pivot table layout extraction.

This module handles common financial table layouts:
1. Temporal columns + Metric rows (periods in columns, metrics in rows)
2. Entity columns + Metric rows (entities in columns, metrics in rows)
3. Transposed tables (metrics as row labels, entities as column headers)

All extraction functions produce (entity, metric, period, value, unit) tuples.
"""

# FACADE: Re-export all functions from layouts subpackage for backward compatibility
from .layouts import (
    _extract_entity_cols_metric_rows,
    _extract_temporal_cols_metric_rows,
    _extract_transposed_entity_cols_metric_row_labels,
)

__all__ = [
    "_extract_temporal_cols_metric_rows",
    "_extract_entity_cols_metric_rows",
    "_extract_transposed_entity_cols_metric_row_labels",
]
