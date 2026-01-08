"""Data parsers for BaseGov client.

Story 8.2 Task 4: Extract parsing logic from basegov.py
Handles IMPIC XLSX, OCDS JSON, and TED API response parsing.
"""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Any

import openpyxl

from raglite.external_data.models import BaseGovContract
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


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


def _extract_description(
    row: tuple,
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


def _create_contract_from_row(
    row: tuple,
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
        cpv_code=item_cpv.split("\n")[0] if item_cpv else "",  # First CPV only
        execution_location="Portugal",
    )


def _process_impic_row(
    row: tuple,
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


def parse_impic_xlsx(
    content: bytes,
    start_date: date,
    end_date: date,
    cpv_code: str | None = None,
) -> list[BaseGovContract]:
    """Parse IMPIC XLSX content to BaseGovContract models.

    Story 6.9.5: Parse dados.gov.pt IMPIC format

    XLSX columns (verified 2025-12-08):
    - idcontrato: Contract ID
    - tipoContrato: Contract type
    - tipoprocedimento: Procedure type
    - objectoContrato: Contract object/title
    - descContrato: Description
    - adjudicante: Contracting entity (NIF - Name)
    - adjudicatarios: Contractor/winner (NIF - Name)
    - dataPublicacao: Publication date
    - dataCelebracaoContrato: Contract celebration date
    - precoContratual: Contract value
    - CPV: CPV codes

    Args:
        content: XLSX bytes
        start_date: Filter start date
        end_date: Filter end date
        cpv_code: CPV code filter (prefix match)

    Returns:
        List of contracts matching filters
    """
    results: list[BaseGovContract] = []

    try:
        wb = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
        ws = wb.active

        # Get headers from first row
        headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]

        # Find column indices
        col_map = {h: i for i, h in enumerate(headers) if h}

        id_col = col_map.get("idcontrato", 0)
        obj_col = col_map.get("objectoContrato")
        desc_col = col_map.get("descContrato")
        buyer_col = col_map.get("adjudicante")
        winner_col = col_map.get("adjudicatarios")
        pub_date_col = col_map.get("dataPublicacao")
        contract_date_col = col_map.get("dataCelebracaoContrato")
        value_col = col_map.get("precoContratual")
        cpv_col = col_map.get("CPV")

        # Parse data rows
        for row in ws.iter_rows(min_row=2, values_only=True):
            try:
                contract = _process_impic_row(
                    row=row,
                    start_date=start_date,
                    end_date=end_date,
                    cpv_code=cpv_code,
                    id_col=id_col,
                    obj_col=obj_col,
                    desc_col=desc_col,
                    buyer_col=buyer_col,
                    winner_col=winner_col,
                    pub_date_col=pub_date_col,
                    contract_date_col=contract_date_col,
                    value_col=value_col,
                    cpv_col=cpv_col,
                )
                if contract:
                    results.append(contract)
            except (IndexError, TypeError, ValueError):
                # Skip malformed rows
                continue

        wb.close()

    except Exception as e:
        logger.warning(f"Failed to parse IMPIC XLSX: {e}")
        return []

    return results


def parse_ocds_data(
    ocds_data: dict | list,
    start_date: date,
    end_date: date,
    cpv_code: str | None = None,
) -> list[BaseGovContract]:
    """Parse OCDS format data to BaseGovContract models.

    Story 6.9.5 AC3: OCDS parsing

    OCDS structure:
    - releases[] or records[] array
    - Each has tender, awards, contracts sections
    - Uses ocid as unique identifier

    Args:
        ocds_data: OCDS JSON data
        start_date: Filter start date
        end_date: Filter end date
        cpv_code: CPV code filter

    Returns:
        List of BaseGovContract records
    """
    results: list[BaseGovContract] = []

    # Handle both releases and records format
    items = []
    if isinstance(ocds_data, dict):
        items = ocds_data.get("releases", ocds_data.get("records", []))
    elif isinstance(ocds_data, list):
        items = ocds_data

    for item in items:
        try:
            # Get contract info from awards/contracts section
            awards = item.get("awards", [])
            contracts_list = item.get("contracts", [])
            tender = item.get("tender", {})

            # Extract date from published date or tender period
            pub_date_str = item.get("date", item.get("publishedDate"))
            if not pub_date_str and tender:
                pub_date_str = tender.get("tenderPeriod", {}).get("endDate")

            if not pub_date_str:
                continue

            # Parse date
            pub_date = date.fromisoformat(pub_date_str[:10])

            # Filter by date range
            if not (start_date <= pub_date <= end_date):
                continue

            # Get CPV codes
            item_cpv = None
            tender_items = tender.get("items", [])
            if tender_items:
                classification = tender_items[0].get("classification", {})
                item_cpv = classification.get("id", "")

            # Filter by CPV if specified
            if cpv_code and item_cpv and not item_cpv.startswith(cpv_code[:2]):
                continue

            # Get contract value
            value = 0.0
            if contracts_list:
                value = contracts_list[0].get("value", {}).get("amount", 0)
            elif awards:
                value = awards[0].get("value", {}).get("amount", 0)
            elif tender:
                value = tender.get("value", {}).get("amount", 0)

            # Get parties (buyer and supplier)
            parties = item.get("parties", [])
            buyer = ""
            supplier = ""
            for party in parties:
                roles = party.get("roles", [])
                if "buyer" in roles:
                    buyer = party.get("name", "")
                if "supplier" in roles or "tenderer" in roles:
                    supplier = party.get("name", "")

            results.append(
                BaseGovContract(
                    publication_date=pub_date,
                    contract_id=item.get("ocid", item.get("id", "")),
                    description=tender.get("title", tender.get("description", "")),
                    contract_value_eur=float(value),
                    contracting_entity=buyer,
                    contractor=supplier,
                    cpv_code=item_cpv,
                    execution_location="Portugal",
                )
            )

        except (ValueError, KeyError, TypeError) as e:
            logger.warning(
                "Failed to parse OCDS item",
                extra={"error": str(e)},
            )
            continue

    return results


def parse_ted_notices(data: dict) -> list[BaseGovContract]:
    """Parse TED API response to BaseGovContract models.

    Story 6.9.5 AC6: TED API parsing

    Args:
        data: TED API response

    Returns:
        List of contracts
    """
    results: list[BaseGovContract] = []

    notices = data.get("notices", data.get("results", []))

    for notice in notices:
        try:
            # Get publication date
            pub_date_str = notice.get("publication-date", notice.get("publicationDate"))
            if not pub_date_str:
                continue

            pub_date = date.fromisoformat(pub_date_str[:10])

            # Get value (may be in different formats)
            value = notice.get("total-value", notice.get("totalValue", 0))
            if isinstance(value, dict):
                value = value.get("amount", 0)
            if isinstance(value, str):
                value = float(value.replace(",", ".").replace(" ", ""))

            # Get CPV code
            cpv = notice.get("cpv", notice.get("cpvCode", ""))
            if isinstance(cpv, list):
                cpv = cpv[0] if cpv else ""

            results.append(
                BaseGovContract(
                    publication_date=pub_date,
                    contract_id=str(notice.get("publication-number", notice.get("id", ""))),
                    description=notice.get("notice-title", notice.get("title", "")),
                    contract_value_eur=float(value) if value else 0.0,
                    contracting_entity=notice.get("buyer-name", notice.get("buyer", "")),
                    contractor=notice.get("winner-name", notice.get("winner", "")),
                    cpv_code=cpv,
                    execution_location="Portugal",
                )
            )

        except (ValueError, KeyError, TypeError) as e:
            logger.warning(
                "Failed to parse TED notice",
                extra={"error": str(e)},
            )
            continue

    return results
