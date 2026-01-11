"""Utility functions for BaseGov value parsing."""

from __future__ import annotations

from typing import Any


def _parse_contract_value(row_value: Any) -> float:
    """Parse contract value from IMPIC row.

    Args:
        row_value: Value from spreadsheet cell

    Returns:
        Parsed float value or 0.0 if parsing fails
    """
    if not row_value:
        return 0.0

    try:
        if isinstance(row_value, (int, float)):
            return float(row_value)
        elif isinstance(row_value, str):
            return float(row_value.replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        pass

    return 0.0
