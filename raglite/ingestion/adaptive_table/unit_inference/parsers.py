"""Value and unit parsing utilities.

This module provides utilities for parsing numeric values and units from cell text.
"""

from __future__ import annotations

import re


def _parse_value_unit(text: str) -> tuple[float | None, str | None]:
    """Parse numeric value and unit from cell text.

    Args:
        text: Cell text to parse (e.g., "123.45 EUR", "42%", "100M")

    Returns:
        Tuple of (value, unit) where:
        - value: Parsed numeric value or None if parsing fails
        - unit: Extracted unit string or None if not found

    Example:
        >>> _parse_value_unit("123.45 EUR")
        (123.45, 'EUR')
        >>> _parse_value_unit("42%")
        (42.0, '%')
        >>> _parse_value_unit("invalid")
        (None, None)
    """
    if not text:
        return None, None

    text = text.strip().replace(",", ".")

    # Try to extract number
    number_match = re.search(r"[-+]?\d*\.?\d+", text)
    if number_match:
        try:
            value = float(number_match.group())
            # Extract unit (anything after the number)
            unit_text = text[number_match.end() :].strip()
            unit = unit_text if unit_text else None
            return value, unit
        except ValueError:
            return None, None

    return None, None
