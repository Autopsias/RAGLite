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

import asyncio
import os
from datetime import date

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import BPstatBankAppraisal, BPstatMortgageLoans
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# BPstat API Configuration
# Story 6.9.3 AC2: Updated from /data/v1 (404) to /api (working)
BPSTAT_API_BASE = "https://bpstat.bportugal.pt/api"


class BPstatClient:
    """Client for Banco de Portugal Statistics API.

    Provides access to Portuguese mortgage interest rate statistics.

    Story 6.9.3: Updated API endpoint and series IDs (2025-12-08)
    - Old endpoint /data/v1 returns 404
    - New endpoint /api/observations/ returns data

    Example:
        >>> client = BPstatClient()
        >>> rates = await client.fetch_mortgage_loans(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 3, 31)
        ... )
    """

    # BPstat series codes for mortgage interest rates (Variable rate - New housing loans)
    # Story 6.9.3 AC1/AC6: Correct series IDs (verified 2025-12-08)
    # Source: https://bpstat.bportugal.pt/api/series/{id}
    #
    # IMPORTANT: Old series IDs (12532089, 12532090, 12532091) were WRONG
    # They returned FX rates (Egyptian Pound, etc.), NOT mortgage data!
    #
    # Interest rate distribution for new housing loans (variable rate):
    MORTGAGE_RATE_MEDIAN = "12710733"  # 50th percentile (median) - PRIMARY
    MORTGAGE_RATE_10TH_PERCENTILE = "12710735"  # 10th percentile
    MORTGAGE_RATE_25TH_PERCENTILE = "12710781"  # 25th percentile
    MORTGAGE_RATE_75TH_PERCENTILE = "12710734"  # 75th percentile
    MORTGAGE_RATE_90TH_PERCENTILE = "12710736"  # 90th percentile

    # Backward compatibility aliases (deprecated - use new names)
    MORTGAGE_LOANS_SERIES = MORTGAGE_RATE_MEDIAN  # Alias for backward compat
    MORTGAGE_RATE_SERIES = MORTGAGE_RATE_MEDIAN  # Alias for backward compat

    # Story 6.8 AC2.2: Bank appraisal values for housing
    BANK_APPRAISAL_SERIES = "12559916"  # Average bank appraisal values (EUR/m²)

    def __init__(self) -> None:
        self.base_url = BPSTAT_API_BASE
        self.api_key = settings.bpstat_api_key
        # Use test timeout in test environment
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def _fetch_with_retry(
        self,
        series_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> dict:
        """Fetch data from BPstat API with retry logic.

        Story 6.9.3 AC2/AC3/AC7: Updated for new API structure

        Args:
            series_ids: List of BPstat series identifiers (can fetch multiple in one request)
            start_date: Start of date range
            end_date: End of date range

        Returns:
            JSON response from API with observations data

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        max_retries = settings.external_data_retry_attempts
        # Story 6.9.3 AC7: NFR1 exponential backoff at 2s/4s/8s intervals
        retry_delays = [2, 4, 8]

        # Story 6.9.3 AC2: New API endpoint structure
        # Old (broken): /data/v1/series/{id}/observations
        # New (working): /api/observations/?series_ids={ids}&lang=EN
        url = f"{self.base_url}/observations/"
        params = {
            "series_ids": ",".join(series_ids),
            "lang": "EN",
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
                                "series_ids": series_ids,
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
        response_data = await self._fetch_with_retry(
            series_to_fetch,
            start_date,
            end_date,
        )

        return self._parse_interest_rate_data(response_data, series_to_fetch)

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

        response_data = await self._fetch_with_retry(
            [self.BANK_APPRAISAL_SERIES],
            start_date,
            end_date,
        )

        return self._parse_bank_appraisal_data(response_data)

    def _parse_bank_appraisal_data(
        self,
        response_data: dict,
    ) -> list[BPstatBankAppraisal]:
        """Parse bank appraisal data from API response.

        Args:
            response_data: JSON response from BPstat API

        Returns:
            List of bank appraisal records
        """
        results = []

        # Same API structure as interest rates
        raw_observations = response_data.get("data", response_data.get("observations", []))

        for obs in raw_observations:
            try:
                # Handle both old and new date formats
                period = obs.get("period", obs.get("refPeriod"))
                if not period:
                    ref_date = obs.get("reference_date")
                    if ref_date:
                        period = ref_date[:7]

                value = obs.get("value")

                if not period or value is None:
                    continue

                # Parse period (format: YYYY-MM)
                year, month = map(int, period.split("-"))
                record_date = date(year, month, 1)

                results.append(
                    BPstatBankAppraisal(
                        date=record_date,
                        avg_appraisal_eur_m2=float(value),
                        region="Portugal",
                    )
                )

            except (ValueError, TypeError, KeyError) as e:
                logger.warning(
                    "Failed to parse BPstat appraisal observation",
                    extra={"obs": obs, "error": str(e)},
                )
                continue

        logger.info(
            "Parsed BPstat bank appraisals",
            extra={"record_count": len(results)},
        )
        return results

    def _extract_period_from_observation(self, obs: dict) -> str | None:
        """Extract period from observation dict.

        Handles both old ("period": "2024-01") and new ("reference_date": "2024-01-31") formats.

        Args:
            obs: Single observation from API response

        Returns:
            Period string (YYYY-MM) or None if not found
        """
        period: str | None = obs.get("period", obs.get("refPeriod"))
        if not period:
            ref_date = obs.get("reference_date")
            if ref_date:
                # Convert "2024-01-31" to "2024-01"
                period = ref_date[:7]
        return period

    def _build_observations_lookup(
        self, raw_observations: list[dict]
    ) -> dict[str, dict[str, float]]:
        """Build lookup dict for observations by period and series.

        Args:
            raw_observations: List of observation dicts from API

        Returns:
            Nested dict: {period: {series_id: value}}
        """
        observations_by_period: dict[str, dict[str, float]] = {}

        for obs in raw_observations:
            try:
                period = self._extract_period_from_observation(obs)
                series_id = str(obs.get("series_id", obs.get("seriesId", "")))
                value = obs.get("value")

                if not period or value is None:
                    continue

                if period not in observations_by_period:
                    observations_by_period[period] = {}

                observations_by_period[period][series_id] = float(value)

            except (ValueError, TypeError) as e:
                logger.warning(
                    "Failed to parse BPstat observation",
                    extra={"obs": obs, "error": str(e)},
                )
                continue

        return observations_by_period

    def _create_mortgage_records(
        self, observations_by_period: dict[str, dict[str, float]]
    ) -> list[BPstatMortgageLoans]:
        """Create mortgage loan records from observations lookup.

        Args:
            observations_by_period: Nested dict from _build_observations_lookup

        Returns:
            List of BPstatMortgageLoans records
        """
        results = []

        for period, series_values in sorted(observations_by_period.items()):
            try:
                # Parse period (format: YYYY-MM)
                year, month = map(int, period.split("-"))
                record_date = date(year, month, 1)

                # Get median rate (primary series) - required
                median_rate = series_values.get(self.MORTGAGE_RATE_MEDIAN)
                if median_rate is None:
                    # Try old alias for backward compatibility
                    median_rate = series_values.get(self.MORTGAGE_LOANS_SERIES)

                if median_rate is None:
                    logger.warning(
                        "Missing median rate for period",
                        extra={"period": period},
                    )
                    continue

                results.append(
                    BPstatMortgageLoans(
                        date=record_date,
                        # Story 6.9.3: Now returns interest rates, not loan amounts
                        # total_loans_eur is kept for backward compatibility but
                        # will be 0 since we no longer fetch loan amount series
                        total_loans_eur=0.0,
                        new_loans_eur=None,
                        avg_interest_rate_pct=median_rate,
                    )
                )

            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to create BPstat record",
                    extra={"period": period, "error": str(e)},
                )
                continue

        return results

    def _parse_interest_rate_data(
        self,
        response_data: dict,
        series_ids: list[str],
    ) -> list[BPstatMortgageLoans]:
        """Parse interest rate data from new API response.

        Story 6.9.3 AC3: Updated parser for new API structure

        Args:
            response_data: JSON response from BPstat API
            series_ids: List of series IDs that were requested

        Returns:
            List of mortgage interest rate records
        """
        # New API response structure:
        # {
        #   "data": {
        #     "series_id": { ... series metadata ... },
        #     ...
        #   },
        #   "observations": [
        #     { "period": "2024-01", "value": 3.45, "series_id": "12710733" },
        #     ...
        #   ]
        # }

        # Story 6.9.4: BPstat API returns data in "data" array (not "observations")
        # Each item has "reference_date" (YYYY-MM-DD format) instead of "period"
        raw_observations = response_data.get("data", response_data.get("observations", []))

        # Build lookup and create records
        observations_by_period = self._build_observations_lookup(raw_observations)
        results = self._create_mortgage_records(observations_by_period)

        logger.info(
            "Parsed BPstat mortgage interest rates",
            extra={"record_count": len(results)},
        )
        return results

    # Legacy method kept for backward compatibility
    def _merge_loan_data(
        self,
        total_loans: dict,
        new_loans: dict,
        rates: dict,
    ) -> list[BPstatMortgageLoans]:
        """Merge loan data from multiple series (DEPRECATED).

        Story 6.9.3: This method is deprecated. Use _parse_interest_rate_data instead.
        Kept for backward compatibility only.

        Args:
            total_loans: Total outstanding loans data
            new_loans: New loans data
            rates: Interest rate data

        Returns:
            List of merged loan records
        """
        logger.warning(
            "Using deprecated _merge_loan_data method - "
            "update caller to use _parse_interest_rate_data"
        )

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
