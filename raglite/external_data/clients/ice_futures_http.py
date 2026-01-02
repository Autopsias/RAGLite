"""HTTP client utilities for ICE Futures data fetching.

Handles:
- Retry logic with exponential backoff
- Quandl API data fetching
- Yahoo Finance data fetching (yfinance)
- EEX API fallback for TTF gas
"""

from __future__ import annotations

import asyncio
from datetime import date

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import API2CoalPrice, TTFGasPrice
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Quandl/Nasdaq Data Link API
QUANDL_API_BASE = "https://data.nasdaq.com/api/v3/datasets"

# Yahoo Finance tickers
YAHOO_TTF_TICKER = "TTF=F"  # TTF Dutch Natural Gas Futures
YAHOO_NG_TICKER = "NG=F"  # Henry Hub Natural Gas (US benchmark, fallback)
YAHOO_API2_TICKER = "MTF=F"  # Coal futures proxy


async def fetch_with_retry(url: str, params: dict | None = None, timeout: float = 30.0) -> dict:
    """Fetch data from URL with retry logic.

    Args:
        url: API URL
        params: Query parameters
        timeout: Request timeout in seconds

    Returns:
        JSON response

    Raises:
        ExternalDataFetchError: If all retries fail
    """
    max_retries = settings.external_data_retry_attempts
    retry_delays = [2, 4, 8]  # NFR1: exponential backoff at 2s/4s/8s intervals

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return dict(response.json())

            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(
                        "ICE Futures API timeout, retrying",
                        extra={"attempt": attempt + 1, "delay": delay},
                    )
                    await asyncio.sleep(delay)
                else:
                    raise ExternalDataFetchError(
                        source="ICE_Futures",
                        message="Timeout after retries",
                        original_error=e,
                    ) from e

            except httpx.HTTPStatusError as e:
                should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                if attempt < max_retries - 1 and should_retry:
                    delay = retry_delays[attempt]
                    await asyncio.sleep(delay)
                else:
                    raise ExternalDataFetchError(
                        source="ICE_Futures",
                        message=f"HTTP {e.response.status_code}",
                        original_error=e,
                    ) from e

    raise ExternalDataFetchError(source="ICE_Futures", message="Unexpected retry loop exit")


async def fetch_quandl_data(
    dataset_code: str,
    start_date: date,
    end_date: date,
    api_key: str | None = None,
    timeout: float = 30.0,
) -> dict:
    """Fetch data from Quandl/Nasdaq Data Link.

    Args:
        dataset_code: Quandl dataset code (e.g., "ODA/PCOALAU_USD")
        start_date: Start of date range
        end_date: End of date range
        api_key: Optional Quandl API key
        timeout: Request timeout in seconds

    Returns:
        JSON response with dataset
    """
    url = f"{QUANDL_API_BASE}/{dataset_code}.json"

    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "order": "desc",
    }

    if api_key:
        params["api_key"] = api_key

    logger.info(
        "Fetching Quandl data",
        extra={"dataset": dataset_code, "start": str(start_date), "end": str(end_date)},
    )

    return await fetch_with_retry(url, params, timeout)


async def fetch_yahoo_coal(
    start_date: date,
    end_date: date,
) -> list[API2CoalPrice]:
    """Fetch coal prices from Yahoo Finance using yfinance.

    Primary source for API2 Coal data since Quandl datasets are withdrawn.
    Uses MTF=F (Coal Futures) ticker which provides daily price data.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of API2 Coal price records
    """
    try:
        import warnings

        import yfinance as yf  # type: ignore[import-untyped,import-not-found]

        warnings.filterwarnings("ignore", category=FutureWarning)

        # Fetch MTF=F (Coal Futures) - working as of 2025
        logger.info("Fetching coal prices from Yahoo Finance", extra={"ticker": YAHOO_API2_TICKER})

        df = yf.download(
            YAHOO_API2_TICKER,
            start=str(start_date),
            end=str(end_date),
            progress=False,
            auto_adjust=True,
        )

        if df.empty:
            raise ExternalDataFetchError(
                source="Yahoo_Finance",
                message=f"No data returned for {YAHOO_API2_TICKER}",
            )

        results: list[API2CoalPrice] = []
        for idx, row in df.iterrows():
            try:
                record_date = idx.date() if hasattr(idx, "date") else idx
                # Handle MultiIndex columns from yfinance
                close_price = float(
                    row["Close"].iloc[0] if hasattr(row["Close"], "iloc") else row["Close"]
                )

                results.append(
                    API2CoalPrice(
                        date=record_date,
                        price=close_price,
                        currency="USD",
                    )
                )
            except (ValueError, KeyError, IndexError) as e:
                logger.warning(
                    "Failed to parse Yahoo coal record",
                    extra={"date": str(idx), "error": str(e)},
                )
                continue

        logger.info(
            "Fetched coal prices from Yahoo Finance",
            extra={"count": len(results)},
        )

        return results

    except ImportError as e:
        raise ExternalDataFetchError(
            source="Yahoo_Finance",
            message="yfinance not installed",
            original_error=e,
        ) from e
    except Exception as e:
        raise ExternalDataFetchError(
            source="Yahoo_Finance",
            message=f"Failed to fetch coal prices: {e}",
            original_error=e,
        ) from e


async def fetch_yahoo_ttf(
    start_date: date,
    end_date: date,
) -> list[TTFGasPrice]:
    """Fetch TTF gas prices from Yahoo Finance using yfinance.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of TTF gas price records
    """
    try:
        import warnings

        import yfinance as yf  # type: ignore[import-untyped,import-not-found]

        warnings.filterwarnings("ignore", category=FutureWarning)

        # Fetch TTF=F (Dutch TTF Natural Gas Futures)
        df = yf.download(
            YAHOO_TTF_TICKER,
            start=str(start_date),
            end=str(end_date),
            progress=False,
            auto_adjust=True,
        )

        if df.empty:
            raise ExternalDataFetchError(
                source="Yahoo_Finance",
                message=f"No data returned for {YAHOO_TTF_TICKER}",
            )

        results: list[TTFGasPrice] = []
        for idx, row in df.iterrows():
            try:
                record_date = idx.date() if hasattr(idx, "date") else idx
                close_price = float(
                    row["Close"].iloc[0] if hasattr(row["Close"], "iloc") else row["Close"]
                )

                results.append(
                    TTFGasPrice(
                        date=record_date,
                        price=close_price,
                        currency="EUR",
                    )
                )
            except (ValueError, KeyError, IndexError) as e:
                logger.warning(
                    "Failed to parse Yahoo TTF record",
                    extra={"date": str(idx), "error": str(e)},
                )
                continue

        logger.info(
            "Fetched TTF gas from Yahoo Finance",
            extra={"count": len(results)},
        )

        return results

    except ImportError as e:
        raise ExternalDataFetchError(
            source="Yahoo_Finance",
            message="yfinance not installed",
            original_error=e,
        ) from e
    except Exception as e:
        raise ExternalDataFetchError(
            source="Yahoo_Finance",
            message=f"Failed to fetch TTF gas: {e}",
            original_error=e,
        ) from e
