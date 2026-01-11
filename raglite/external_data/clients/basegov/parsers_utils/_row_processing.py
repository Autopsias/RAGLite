"""Utility functions for BaseGov row processing."""

from __future__ import annotations

from datetime import date
from typing import Any

from raglite.external_data.models import BaseGovContract

from ._contract_creation import _create_contract_from_row
from ._cpv_filtering import _check_cpv_filter
from ._date_parsing import _parse_publication_date
from ._description_parsing import _extract_description
from ._value_parsing import _parse_contract_value


def _process_impic_row(
    row: tuple[Any, ...],
    start_date: date,
    end_date: date,
    cpv_code: str | None,
    id_col: int,
    obj_col: int | None,
    desc_col: int | None,
    buyer_col: int | None,
    winner_col: int | None,
    pub_date_col: int | None,
    contract_date_col: int | None,
    value_col: int | None,
    cpv_col: int | None,
) -> BaseGovContract | None:
    """Process a single IMPIC spreadsheet row.

    Args:
        row: Spreadsheet row data
        start_date: Filter start date
        end_date: Filter end date
        cpv_code: CPV code filter (prefix match)
        id_col: Contract ID column index
        obj_col: Object/title column index
        desc_col: Description column index
        buyer_col: Buyer column index
        winner_col: Winner column index
        pub_date_col: Publication date column index
        contract_date_col: Contract date column index
        value_col: Value column index
        cpv_col: CPV column index

    Returns:
        BaseGovContract or None if row should be skipped
    """
    # Get and parse publication date
    pub_date_val = row[pub_date_col] if pub_date_col is not None else None
    contract_date_val = row[contract_date_col] if contract_date_col is not None else None
    pub_date = _parse_publication_date(pub_date_val, contract_date_val)

    if not pub_date:
        return None

    # Filter by date range
    if not (start_date <= pub_date <= end_date):
        return None

    # Get CPV code
    item_cpv = str(row[cpv_col]) if cpv_col is not None and row[cpv_col] else ""

    # Filter by CPV if specified (prefix match)
    if not _check_cpv_filter(item_cpv, cpv_code):
        return None

    # Parse contract value
    value = _parse_contract_value(row[value_col] if value_col is not None else None)

    # Extract description
    description = _extract_description(row, obj_col, desc_col)

    # Parse buyer/winner (format: "NIF - Name")
    buyer = str(row[buyer_col]) if buyer_col is not None and row[buyer_col] else ""
    winner = str(row[winner_col]) if winner_col is not None and row[winner_col] else ""

    # Create contract object
    return _create_contract_from_row(
        row=row,
        pub_date=pub_date,
        description=description,
        value=value,
        buyer=buyer,
        winner=winner,
        item_cpv=item_cpv,
        id_col=id_col,
    )
