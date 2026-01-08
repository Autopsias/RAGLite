"""European electricity price client using Ember Energy data.

Story 6.29 P3: Phase 2 - Electricity Price Integration for Electricity Cost Regressor

Fetches European electricity market data from Ember Energy's cleaned datasets:
- Daily electricity prices (2015-present)
- Monthly electricity prices
- Sourced from ENTSO-E Transparency Platform (cleaned by Ember)

Data Source: https://ember-energy.org/data/european-wholesale-electricity-price-data/
License: Creative Commons (CC-BY-4.0)
Updates: Monthly

IMPORTANT: This client uses Ember Energy's free CSV data instead of ENTSO-E API
because the ENTSO-E registration system is currently broken (Dec 2024).
Ember sources their data directly from ENTSO-E, so it's the same data, just pre-cleaned.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date, timedelta
from io import StringIO

import httpx
import pandas as pd

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import ENTSOEElectricityPrice
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Ember Energy CSV URLs (Google Cloud Storage - public access)
EMBER_DAILY_CSV_URL = "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/price/outputs/european_wholesale_electricity_price_data_daily.csv"
EMBER_MONTHLY_CSV_URL = "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/price/outputs/european_wholesale_electricity_price_data_monthly.csv"

# Country codes mapping (ISO 2-letter -> ISO 3-letter for Ember CSV)
COUNTRY_CODES = {
    "PT": "PRT",  # Portugal
    "ES": "ESP",  # Spain
    "FR": "FRA",  # France
    "DE": "DEU",  # Germany
    "IT": "ITA",  # Italy
    "UK": "GBR",  # United Kingdom
    "NL": "NLD",  # Netherlands
    "BE": "BEL",  # Belgium
    "PL": "POL",  # Poland
    "CZ": "CZE",  # Czechia
    "AT": "AUT",  # Austria
    "SE": "SWE",  # Sweden
    "DK": "DNK",  # Denmark
    "NO": "NOR",  # Norway
    "FI": "FIN",  # Finland
}


class ENTSOEClient:
    """Client for European electricity prices via Ember Energy.

    Ember Energy provides cleaned European electricity price data sourced from
    ENTSO-E Transparency Platform. No API token required - uses public CSV files.

    Data coverage: 2015-present, updated monthly
    License: Creative Commons (CC-BY-4.0)

    Example:
        >>> client = ENTSOEClient()
        >>> prices = await client.fetch_day_ahead_prices(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 1, 31),
        ...     country="PT"
        ... )
    """

    def __init__(self) -> None:
        """Initialize Ember-based electricity client.

        No API token required - uses public CSV files.
        """
        self.daily_csv_url = EMBER_DAILY_CSV_URL
        self.monthly_csv_url = EMBER_MONTHLY_CSV_URL

        # Use external data timeout settings
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 10.0 if is_test else float(settings.external_data_timeout)

        # Cache for CSV data (avoid re-downloading on each call)
        self._daily_cache: pd.DataFrame | None = None
        self._monthly_cache: pd.DataFrame | None = None

    async def fetch_day_ahead_prices(
        self,
        start_date: date,
        end_date: date,
        country: str = "PT",
        include_hourly: bool = False,
    ) -> list[ENTSOEElectricityPrice]:
        """Fetch day-ahead electricity prices for date range.

        Note: Ember provides daily averages, not hourly data.
        If include_hourly=True, returns daily data with hour=None.

        Args:
            start_date: Start of date range
            end_date: End of date range
            country: ISO 2-letter country code (PT, ES, FR, DE, etc.)
            include_hourly: Ignored (Ember only provides daily data)

        Returns:
            List of daily electricity price records

        Raises:
            ExternalDataFetchError: If fetch fails
        """
        logger.info(
            "Fetching Ember electricity prices",
            extra={
                "start": str(start_date),
                "end": str(end_date),
                "country": country,
            },
        )

        # Validate country code
        if country not in COUNTRY_CODES:
            raise ExternalDataFetchError(
                source="Ember/ENTSO-E",
                message=f"Unsupported country: {country}. Supported: {list(COUNTRY_CODES.keys())}",
            )

        # Fetch and filter daily CSV data
        df = await self._fetch_daily_csv()

        # Filter by country (ISO3) and date range
        iso3_code = COUNTRY_CODES[country]
        mask = (
            (df["iso3_code"] == iso3_code) & (df["date"] >= start_date) & (df["date"] <= end_date)
        )
        filtered_df = df[mask]

        if filtered_df.empty:
            logger.warning(
                "No Ember data found for date range",
                extra={"country": country, "start": str(start_date), "end": str(end_date)},
            )
            return []

        # Convert to ENTSOEElectricityPrice objects
        prices = []
        for _, row in filtered_df.iterrows():
            prices.append(
                ENTSOEElectricityPrice(
                    date=row["date"],
                    hour=None,  # Ember provides daily averages
                    price_eur_mwh=row["price_eur_mwh"],
                    bidding_zone=country,
                    price_type="spot_daily_avg",
                )
            )

        logger.info(
            "Fetched Ember electricity prices",
            extra={"record_count": len(prices)},
        )

        return prices

    async def _fetch_daily_csv(self) -> pd.DataFrame:
        """Fetch and parse Ember daily electricity price CSV.

        CSV columns: date, country, price_eur_mwh

        Returns:
            DataFrame with parsed data

        Raises:
            ExternalDataFetchError: If download or parsing fails
        """
        # Return cached data if available
        if self._daily_cache is not None:
            return self._daily_cache

        # Retry logic per NFR1 (exponential backoff)
        max_retries = settings.external_data_retry_attempts
        retry_delays = [2, 4, 8]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            df = await self._fetch_with_retry(client, max_retries, retry_delays)

        # Cache and return
        self._daily_cache = df
        self._log_fetch_success(df)
        return df

    async def _fetch_with_retry(
        self, client: httpx.AsyncClient, max_retries: int, retry_delays: list[int]
    ) -> pd.DataFrame:
        """Fetch CSV with retry logic.

        Args:
            client: HTTP client
            max_retries: Maximum retry attempts
            retry_delays: Exponential backoff delays

        Returns:
            Parsed DataFrame

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = await client.get(self.daily_csv_url)
                response.raise_for_status()
                return self._parse_daily_csv(response.text)

            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                should_retry = await self._handle_fetch_error(e, attempt, max_retries, retry_delays)
                if should_retry:
                    continue
                raise

            except Exception as e:
                raise ExternalDataFetchError(
                    source="Ember",
                    message=f"Failed to parse CSV: {e}",
                ) from e

        raise ExternalDataFetchError(
            source="Ember",
            message="Failed to fetch CSV after retries",
        )

    def _parse_daily_csv(self, csv_text: str) -> pd.DataFrame:
        """Parse and normalize Ember daily CSV data.

        Args:
            csv_text: Raw CSV text from API

        Returns:
            Normalized DataFrame with columns: country, iso3_code, date, price_eur_mwh

        Raises:
            ExternalDataFetchError: If required columns are missing
        """
        df = pd.read_csv(StringIO(csv_text))

        # Normalize column names: 'Country', 'ISO3 Code', 'Date', 'Price (EUR/MWhe)'
        # to: country, iso3_code, date, price_eur_mwhe
        df.columns = (
            df.columns.str.lower()
            .str.replace(" ", "_")
            .str.replace("(", "")
            .str.replace(")", "")
            .str.replace("/", "_")
        )

        # Validate required columns
        required_cols = ["iso3_code", "date", "price_eur_mwhe"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ExternalDataFetchError(
                source="Ember",
                message=f"Missing columns: {missing}. Found: {df.columns.tolist()}",
            )

        # Normalize price column name
        df = df.rename(columns={"price_eur_mwhe": "price_eur_mwh"})

        # Parse dates and filter null prices
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df[df["price_eur_mwh"].notna()]

        return df

    def _log_fetch_success(self, df: pd.DataFrame) -> None:
        """Log successful CSV fetch with summary statistics.

        Args:
            df: Parsed DataFrame
        """
        logger.info(
            "Fetched Ember daily CSV",
            extra={
                "total_records": len(df),
                "countries": df["country"].nunique(),
                "date_range": f"{df['date'].min()} to {df['date'].max()}",
            },
        )

    async def _handle_fetch_error(
        self,
        error: httpx.TimeoutException | httpx.HTTPStatusError,
        attempt: int,
        max_retries: int,
        retry_delays: list[int],
    ) -> bool:
        """Handle fetch errors with retry logic.

        Args:
            error: The HTTP error that occurred
            attempt: Current attempt number (0-indexed)
            max_retries: Maximum number of retry attempts
            retry_delays: List of delay seconds for each retry

        Returns:
            True if should retry, False if should raise

        Raises:
            ExternalDataFetchError: If error is not retryable or retries exhausted
        """
        is_timeout = isinstance(error, httpx.TimeoutException)
        is_http_error = isinstance(error, httpx.HTTPStatusError)

        # Determine if error is retryable
        should_retry_error = is_timeout or self._is_retryable_http_error(is_http_error, error)

        if attempt < max_retries - 1 and should_retry_error:
            await self._retry_with_backoff(is_timeout, error, attempt, retry_delays)
            return True

        # Retries exhausted or non-retryable error - raise
        self._raise_fetch_error(is_timeout, error, max_retries)
        # Never returns (always raises)
        return False  # Type checker hint (unreachable)

    def _is_retryable_http_error(
        self, is_http_error: bool, error: httpx.TimeoutException | httpx.HTTPStatusError
    ) -> bool:
        """Check if HTTP error is retryable (5xx or 429).

        Args:
            is_http_error: Whether error is HTTPStatusError
            error: The error object

        Returns:
            True if error is retryable
        """
        if not is_http_error:
            return False
        # Type narrowing: error is HTTPStatusError here
        assert isinstance(error, httpx.HTTPStatusError)
        return error.response.status_code >= 500 or error.response.status_code == 429

    async def _retry_with_backoff(
        self,
        is_timeout: bool,
        error: httpx.TimeoutException | httpx.HTTPStatusError,
        attempt: int,
        retry_delays: list[int],
    ) -> None:
        """Log retry and wait with exponential backoff.

        Args:
            is_timeout: Whether error was a timeout
            error: The error that occurred
            attempt: Current attempt number (0-indexed)
            retry_delays: List of delay seconds
        """
        delay = retry_delays[min(attempt, len(retry_delays) - 1)]
        if is_timeout:
            logger.warning(
                "Ember CSV download timeout, retrying",
                extra={"attempt": attempt + 1, "delay": delay},
            )
        else:
            # Type narrowing: error is HTTPStatusError when not timeout
            assert isinstance(error, httpx.HTTPStatusError)
            logger.warning(
                "Ember CSV download failed, retrying",
                extra={
                    "status": error.response.status_code,
                    "attempt": attempt + 1,
                    "delay": delay,
                },
            )
        await asyncio.sleep(delay)

    def _raise_fetch_error(
        self,
        is_timeout: bool,
        error: httpx.TimeoutException | httpx.HTTPStatusError,
        max_retries: int,
    ) -> None:
        """Raise appropriate ExternalDataFetchError for exhausted retries.

        Args:
            is_timeout: Whether error was a timeout
            error: The error that occurred
            max_retries: Maximum number of retry attempts

        Raises:
            ExternalDataFetchError: Always raises
        """
        if is_timeout:
            message = f"CSV download timeout after {max_retries} attempts"
        else:
            # Type narrowing: error is HTTPStatusError when not timeout
            assert isinstance(error, httpx.HTTPStatusError)
            message = f"HTTP error: {error.response.status_code}"
        raise ExternalDataFetchError(source="Ember", message=message) from error

    async def fetch_monthly_average(
        self,
        year: int,
        month: int,
        country: str = "PT",
    ) -> ENTSOEElectricityPrice | None:
        """Fetch monthly average electricity price.

        Args:
            year: Year
            month: Month (1-12)
            country: ISO 2-letter country code (PT, ES, etc.)

        Returns:
            Monthly average price or None if not available
        """
        # Use daily data to calculate monthly average
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)

        daily_prices = await self.fetch_day_ahead_prices(start, end, country=country)

        if not daily_prices:
            return None

        avg_price = sum(p.price_eur_mwh for p in daily_prices) / len(daily_prices)

        return ENTSOEElectricityPrice(
            date=start,
            hour=None,
            price_eur_mwh=round(avg_price, 2),
            bidding_zone=country,
            price_type="monthly_avg",
        )

    def clear_cache(self) -> None:
        """Clear cached CSV data.

        Useful for forcing a fresh download of the latest data.
        """
        self._daily_cache = None
        self._monthly_cache = None
        logger.info("Cleared Ember CSV cache")
