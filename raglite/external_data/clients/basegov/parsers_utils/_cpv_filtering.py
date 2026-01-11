"""Utility functions for BaseGov CPV filtering."""

from __future__ import annotations


def _check_cpv_filter(item_cpv: str, cpv_code: str | None) -> bool:
    """Check if CPV code matches filter.

    Args:
        item_cpv: CPV code from row
        cpv_code: Required CPV prefix (or None for no filter)

    Returns:
        True if CPV matches or no filter specified
    """
    if not cpv_code or not item_cpv:
        return True

    # Extract main CPV code (before dash)
    main_cpv = item_cpv.split("-")[0].split()[0] if item_cpv else ""
    return main_cpv.startswith(cpv_code[:2])
