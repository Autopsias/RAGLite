"""TED API workflow functions.

Story 8.2 Task 4: Extract high-level workflow functions from ted_api.
"""

from __future__ import annotations

from datetime import date

from raglite.external_data.clients.basegov.parsers import parse_ted_notices
from raglite.external_data.clients.basegov.ted.client import fetch_ted_notices
from raglite.external_data.models import BaseGovContract


async def fetch_ted_contracts(
    start_date: date,
    end_date: date,
    cpv_code: str | None = None,
    page: int = 1,
    page_size: int = 100,
    timeout: float = 30.0,
) -> list[BaseGovContract]:
    """Fetch contracts from TED API (fallback source).

    Args:
        start_date: Start of date range
        end_date: End of date range
        cpv_code: CPV code filter
        page: Page number
        page_size: Results per page
        timeout: Request timeout

    Returns:
        List of BaseGovContract records
    """
    ted_data = await fetch_ted_notices(
        start_date=start_date,
        end_date=end_date,
        cpv_code=cpv_code,
        page=page,
        limit=page_size,
        timeout=timeout,
    )
    return parse_ted_notices(ted_data)
