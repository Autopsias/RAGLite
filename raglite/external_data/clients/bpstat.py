"""BPstat (Banco de Portugal Statistics) API client.

Story 6.1: Tier 1 External Data Source Integration

Fetches Portuguese financial data:
- Mortgage loans (Housing loans to households)
- Interest rates
- Credit statistics

API Documentation: https://bpstat.bportugal.pt/data/docs
"""

from __future__ import annotations

import asyncio
import os
from datetime import date

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import BPstatMortgageLoans
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# BPstat API Configuration
BPSTAT_API_BASE = "https://bpstat.bportugal.pt/data/v1"


class BPstatClient:
    """Client for Banco de Portugal Statistics API.

    Provides access to Portuguese financial statistics including mortgage loans.

    Example:
        >>> client = BPstatClient()
        >>> loans = await client.fetch_mortgage_loans(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 3, 31)
        ... )
    """

    # BPstat series codes
    MORTGAGE_LOANS_SERIES = "12532089"  # Housing loans to households
    NEW_MORTGAGE_LOANS_SERIES = "12532090"  # New housing loans
    MORTGAGE_RATE_SERIES = "12532091"  # Average mortgage interest rate

    def __init__(self) -> None:
        self.base_url = BPSTAT_API_BASE
        self.api_key = settings.bpstat_api_key
        # Use test timeout in test environment
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def _fetch_with_retry(
        self,
        series_id: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Fetch data from BPstat API with retry logic.

        Args:
            series_id: BPstat series identifier
            start_date: Start of date range
            end_date: End of date range

        Returns:
            JSON response from API

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [1, 2, 4]

        # BPstat uses YYYY-MM format for date filtering
        url = f"{self.base_url}/series/{series_id}/observations"
        params = {
            "startPeriod": start_date.strftime("%Y-%m"),
            "endPeriod": end_date.strftime("%Y-%m"),
        }

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    return dict(response.json())

                except httpx.TimeoutException as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "BPstat API timeout, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "delay": delay,
                                "series": series_id,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="BPstat",
                            message=f"Timeout after {max_retries} attempts",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    # Retry on server errors (5xx) or rate limit (429)
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "BPstat API error, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "delay": delay,
                                "status": e.response.status_code,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="BPstat",
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(source="BPstat", message="Unexpected retry loop exit")

    async def fetch_mortgage_loans(
        self,
        start_date: date,
        end_date: date,
    ) -> list[BPstatMortgageLoans]:
        """Fetch mortgage loan data.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of mortgage loan records
        """
        logger.info(
            "Fetching BPstat mortgage loans",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        # Fetch all three series
        total_loans_data = await self._fetch_with_retry(
            self.MORTGAGE_LOANS_SERIES,
            start_date,
            end_date,
        )

        # Optional: fetch new loans and interest rates
        try:
            new_loans_data = await self._fetch_with_retry(
                self.NEW_MORTGAGE_LOANS_SERIES,
                start_date,
                end_date,
            )
        except ExternalDataFetchError:
            new_loans_data = {"observations": []}
            logger.warning("Failed to fetch new loans series, continuing without it")

        try:
            rates_data = await self._fetch_with_retry(
                self.MORTGAGE_RATE_SERIES,
                start_date,
                end_date,
            )
        except ExternalDataFetchError:
            rates_data = {"observations": []}
            logger.warning("Failed to fetch rates series, continuing without it")

        return self._merge_loan_data(total_loans_data, new_loans_data, rates_data)

    def _merge_loan_data(
        self,
        total_loans: dict,
        new_loans: dict,
        rates: dict,
    ) -> list[BPstatMortgageLoans]:
        """Merge loan data from multiple series.

        Args:
            total_loans: Total outstanding loans data
            new_loans: New loans data
            rates: Interest rate data

        Returns:
            List of merged loan records
        """
        results = []

        # Index new loans and rates by period for quick lookup
        new_loans_by_period = {}
        for obs in new_loans.get("observations", []):
            period = obs.get("period", obs.get("refPeriod"))
            if period and obs.get("value") is not None:
                new_loans_by_period[period] = float(obs["value"])

        rates_by_period = {}
        for obs in rates.get("observations", []):
            period = obs.get("period", obs.get("refPeriod"))
            if period and obs.get("value") is not None:
                rates_by_period[period] = float(obs["value"])

        # Process total loans as the primary series
        for obs in total_loans.get("observations", []):
            try:
                period = obs.get("period", obs.get("refPeriod"))
                value = obs.get("value")

                if not period or value is None:
                    continue

                # Parse period (format: YYYY-MM)
                year, month = map(int, period.split("-"))
                record_date = date(year, month, 1)

                results.append(
                    BPstatMortgageLoans(
                        date=record_date,
                        total_loans_eur=float(value) * 1_000_000,  # BPstat reports in millions
                        new_loans_eur=(
                            new_loans_by_period.get(period, 0) * 1_000_000
                            if period in new_loans_by_period
                            else None
                        ),
                        avg_interest_rate_pct=rates_by_period.get(period),
                    )
                )
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse BPstat observation",
                    extra={"period": obs.get("period"), "error": str(e)},
                )
                continue

        logger.info(
            "Parsed BPstat mortgage loans",
            extra={"record_count": len(results)},
        )
        return results
