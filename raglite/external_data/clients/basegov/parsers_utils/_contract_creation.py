"""Utility functions for BaseGov contract creation."""

from __future__ import annotations

from datetime import date
from typing import Any

from raglite.external_data.models import BaseGovContract


def _create_contract_from_row(
    row: tuple[Any, ...],
    pub_date: date,
    description: str,
    value: float,
    buyer: str,
    winner: str,
    item_cpv: str,
    id_col: int,
) -> BaseGovContract:
    """Create BaseGovContract from parsed IMPIC row data.

    Args:
        row: Spreadsheet row data
        pub_date: Parsed publication date
        description: Contract description
        value: Contract value in EUR
        buyer: Contracting entity
        winner: Contractor
        item_cpv: CPV code
        id_col: Contract ID column index

    Returns:
        BaseGovContract instance
    """
    return BaseGovContract(
        publication_date=pub_date,
        contract_id=str(row[id_col]) if row[id_col] else "",
        description=description,
        contract_value_eur=value,
        contracting_entity=buyer,
        contractor=winner,
        cpv_code=item_cpv.split("\\n")[0] if item_cpv else "",  # First CPV only
        execution_location="Portugal",
    )
