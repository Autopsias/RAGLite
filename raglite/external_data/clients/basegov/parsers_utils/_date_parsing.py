"""Utility functions for BaseGov date parsing."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _parse_publication_date(
    pub_date_val: Any,
    contract_date_val: Any,
) -> date | None:
    """Parse publication date from IMPIC row.

    Args:
        pub_date_val: Publication date value
        contract_date_val: Contract date value (fallback)

    Returns:
        Parsed date or None if parsing fails
    """
    # Try publication date first, fallback to contract date
    date_val = pub_date_val if pub_date_val else contract_date_val

    if not date_val:
        return None

    # Parse date based on type
    if isinstance(date_val, datetime):
        return date_val.date()
    elif isinstance(date_val, date):
        return date_val
    elif isinstance(date_val, str):
        return date.fromisoformat(date_val[:10])

    return None
