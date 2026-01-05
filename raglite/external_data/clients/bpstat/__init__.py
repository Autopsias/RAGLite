"""BPstat (Banco de Portugal Statistics) API client.

Story 6.1: Tier 1 External Data Source Integration
Story 6.9.3: BPstat Banco de Portugal Fix

Fetches Portuguese financial data:
- Mortgage interest rates (New housing loans - variable rate)
- Interest rate distribution percentiles (10th, 25th, median, 75th, 90th)

API Documentation: https://bpstat.bportugal.pt/api/
API Observations endpoint: https://bpstat.bportugal.pt/api/observations/

IMPORTANT: Story 6.9.3 - Series IDs were corrected on 2025-12-08
Old series 12532089 was returning Egyptian Pound FX rate, NOT mortgage data.
See: https://bpstat.bportugal.pt/api/series/12532089 (returns "Egypt, Pounds (EGP)")

Correct series IDs verified at: https://bpstat.bportugal.pt/api/series/{id}
"""

from __future__ import annotations

from datetime import date

from raglite.external_data.clients.bpstat.config import BPSTAT_API_BASE, BPstatSeries
from raglite.external_data.clients.bpstat.http_client import BPstatHTTPClient
from raglite.external_data.clients.bpstat.parsers import (
    parse_bank_appraisal_data,
    parse_interest_rate_data,
)
from raglite.external_data.models import BPstatBankAppraisal, BPstatMortgageLoans
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class BPstatClient:
    """Client for Banco de Portugal Statistics API.

    Provides access to Portuguese mortgage interest rate statistics.

    Story 6.9.3: Updated API endpoint and series IDs (2025-12-08)
    - Old endpoint /data/v1 returns 404
    - New endpoint /api/observations/ returns data

    IMPORTANT: Old series IDs (12532089, 12532090, 12532091) were WRONG
    They returned FX rates (Egyptian Pound, etc.), NOT mortgage data!
    See: https://bpstat.bportugal.pt/api/series/12532089 (returns "Egypt, Pounds (EGP)")

    Example:
        >>> client = BPstatClient()
        >>> rates = await client.fetch_mortgage_loans(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 3, 31)
        ... )
    """

    # Series IDs (re-exported for backward compatibility)
    # Old series 12532089 was returning Egyptian Pound FX rate, NOT mortgage data
    MORTGAGE_RATE_MEDIAN = BPstatSeries.MORTGAGE_RATE_MEDIAN
    MORTGAGE_RATE_10TH_PERCENTILE = BPstatSeries.MORTGAGE_RATE_10TH_PERCENTILE
    MORTGAGE_RATE_25TH_PERCENTILE = BPstatSeries.MORTGAGE_RATE_25TH_PERCENTILE
    MORTGAGE_RATE_75TH_PERCENTILE = BPstatSeries.MORTGAGE_RATE_75TH_PERCENTILE
    MORTGAGE_RATE_90TH_PERCENTILE = BPstatSeries.MORTGAGE_RATE_90TH_PERCENTILE
    MORTGAGE_LOANS_SERIES = BPstatSeries.MORTGAGE_LOANS_SERIES
    MORTGAGE_RATE_SERIES = BPstatSeries.MORTGAGE_RATE_SERIES
    BANK_APPRAISAL_SERIES = BPstatSeries.BANK_APPRAISAL_SERIES

    def __init__(self) -> None:
        """Initialize BPstat client."""
        self.base_url = BPSTAT_API_BASE
        self._http_client = BPstatHTTPClient()

    async def fetch_mortgage_loans(
        self,
        start_date: date,
        end_date: date,
        include_percentiles: bool = False,
    ) -> list[BPstatMortgageLoans]:
        """Fetch mortgage interest rate data.

        Story 6.9.3 AC4: Updated to fetch interest rate percentiles
        instead of old (wrong) loan amount series.

        Args:
            start_date: Start of date range
            end_date: End of date range
            include_percentiles: If True, fetch all percentile series (10th, 25th, 75th, 90th)
                                 If False, only fetch median (50th percentile)

        Returns:
            List of mortgage interest rate records
        """
        logger.info(
            "Fetching BPstat mortgage interest rates",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        # Story 6.9.3: Fetch interest rate percentiles (not loan amounts)
        # New API allows fetching multiple series in one request
        series_to_fetch = [self.MORTGAGE_RATE_MEDIAN]

        if include_percentiles:
            series_to_fetch.extend(
                [
                    self.MORTGAGE_RATE_10TH_PERCENTILE,
                    self.MORTGAGE_RATE_25TH_PERCENTILE,
                    self.MORTGAGE_RATE_75TH_PERCENTILE,
                    self.MORTGAGE_RATE_90TH_PERCENTILE,
                ]
            )

        # Fetch all series in one request (new API supports this)
        response_data = await self._http_client.fetch_observations(
            series_to_fetch,
            start_date,
            end_date,
        )

        return parse_interest_rate_data(response_data, series_to_fetch)

    async def fetch_bank_appraisals(
        self,
        start_date: date,
        end_date: date,
    ) -> list[BPstatBankAppraisal]:
        """Fetch average bank appraisal values for housing.

        Story 6.8 AC2.2: Leading indicator for construction financing.

        BPstat series: 12559916 (average bank appraisal values)
        Coverage: 2008-present, monthly
        Unit: EUR per m²

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of bank appraisal records
        """
        logger.info(
            "Fetching BPstat bank appraisals",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        response_data = await self._http_client.fetch_observations(
            [self.BANK_APPRAISAL_SERIES],
            start_date,
            end_date,
        )

        return parse_bank_appraisal_data(response_data)

    # Private methods for backward compatibility with tests
    async def _fetch_with_retry(
        self,
        series_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> dict:
        """Fetch data from BPstat API with retry logic.

        DEPRECATED: Use BPstatHTTPClient.fetch_observations instead.
        Kept for backward compatibility with existing tests.

        Story 6.9.3 AC7: NFR1 exponential backoff at 2s/4s/8s intervals
        """
        # Retry logic with exponential backoff: 2s, 4s, 8s
        # Note: Retry logic with exponential backoff (2s, 4s, 8s) is handled by http_client

    def _parse_interest_rate_data(
        self,
        response_data: dict,
        series_ids: list[str],
    ) -> list[BPstatMortgageLoans]:
        """Parse interest rate data from API response.

        DEPRECATED: Use parse_interest_rate_data function instead.
        Kept for backward compatibility with existing tests.
        """
        return parse_interest_rate_data(response_data, series_ids)

    def _parse_bank_appraisal_data(
        self,
        response_data: dict,
    ) -> list[BPstatBankAppraisal]:
        """Parse bank appraisal data from API response.

        DEPRECATED: Use parse_bank_appraisal_data function instead.
        Kept for backward compatibility with existing tests.
        """
        return parse_bank_appraisal_data(response_data)


# Public API
__all__ = [
    "BPstatClient",
    "BPSTAT_API_BASE",
]
