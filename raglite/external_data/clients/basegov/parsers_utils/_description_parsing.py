"""Utility functions for BaseGov description parsing."""

from __future__ import annotations

from typing import Any


def _extract_description(
    row: tuple[Any, ...],
    obj_col: int | None,
    desc_col: int | None,
) -> str:
    """Extract contract description from IMPIC row.

    Args:
        row: Spreadsheet row data
        obj_col: Object/title column index
        desc_col: Description column index

    Returns:
        Description string (max 500 chars)
    """
    if obj_col is not None and row[obj_col]:
        return str(row[obj_col])[:500]
    elif desc_col is not None and row[desc_col]:
        return str(row[desc_col])[:500]

    return ""
