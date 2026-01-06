"""CSV parsing utilities for Ember Energy data.

Story 6.29 P3: Phase 2 - Electricity Price Integration for Electricity Cost Regressor
"""

from __future__ import annotations

import asyncio
from io import StringIO

import httpx
import pandas as pd

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def _normalize_csv_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Ember CSV column names to lowercase with underscores.

    Args:
        df: DataFrame with original Ember column names

    Returns:
        DataFrame with normalized column names
    """
    # Ember CSV actual columns: 'Country', 'ISO3 Code', 'Date', 'Price (EUR/MWhe)'
    # Normalize column names to lowercase with underscores
    df.columns = (
        df.columns.str.lower()
        .str.replace(" ", "_")
        .str.replace("(", "")
        .str.replace(")", "")
        .str.replace("/", "_")
    )
    return df


def _validate_csv_columns(df: pd.DataFrame) -> None:
    """Validate that required columns exist in normalized DataFrame.

    Args:
        df: DataFrame with normalized columns

    Raises:
        ExternalDataFetchError: If required columns are missing
    """
    # Expected normalized: country, iso3_code, date, price_eur_mwhe
    required_cols = ["iso3_code", "date", "price_eur_mwhe"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ExternalDataFetchError(
            source="Ember",
            message=f"Missing columns: {missing}. Found: {df.columns.tolist()}",
        )


def _transform_csv_data(df: pd.DataFrame) -> pd.DataFrame:
    """Transform parsed CSV data to standard format.

    Args:
        df: DataFrame with normalized columns

    Returns:
        Transformed DataFrame ready for use
    """
    # Rename price column for consistency
    df = df.rename(columns={"price_eur_mwhe": "price_eur_mwh"})

    # Parse dates
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Filter out null prices
    df = df[df["price_eur_mwh"].notna()]

    logger.info(
        "Fetched Ember daily CSV",
        extra={
            "total_records": len(df),
            "countries": df["country"].nunique(),
            "date_range": f"{df['date'].min()} to {df['date'].max()}",
        },
    )

    return df


async def fetch_daily_csv(
    daily_csv_url: str,
    timeout: float,
    retry_attempts: int,
    existing_cache: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Fetch and parse Ember daily electricity price CSV.

    CSV columns: date, country, price_eur_mwh

    Args:
        daily_csv_url: URL to daily CSV file
        timeout: Request timeout in seconds
        retry_attempts: Number of retry attempts
        existing_cache: Cached DataFrame if available

    Returns:
        DataFrame with parsed data

    Raises:
        ExternalDataFetchError: If download or parsing fails
    """
    # Return cached data if available
    if existing_cache is not None:
        return existing_cache

    # Retry logic per NFR1 (exponential backoff)
    retry_delays = [2, 4, 8]

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(retry_attempts):
            try:
                response = await client.get(daily_csv_url)
                response.raise_for_status()

                # Parse CSV
                csv_text = response.text
                df = pd.read_csv(StringIO(csv_text))

                # Normalize, validate, and transform data
                df = _normalize_csv_columns(df)
                _validate_csv_columns(df)
                df = _transform_csv_data(df)

                return df

            except httpx.TimeoutException as e:
                if attempt < retry_attempts - 1:
                    delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                    logger.warning(
                        "Ember CSV download timeout, retrying",
                        extra={"attempt": attempt + 1, "delay": delay},
                    )
                    await asyncio.sleep(delay)
                    continue
                raise ExternalDataFetchError(
                    source="Ember",
                    message=f"CSV download timeout after {retry_attempts} attempts",
                ) from e

            except httpx.HTTPStatusError as e:
                # Retry on server errors (5xx) or rate limit (429)
                should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                if attempt < retry_attempts - 1 and should_retry:
                    delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                    logger.warning(
                        "Ember CSV download failed, retrying",
                        extra={
                            "status": e.response.status_code,
                            "attempt": attempt + 1,
                            "delay": delay,
                        },
                    )
                    await asyncio.sleep(delay)
                    continue
                raise ExternalDataFetchError(
                    source="Ember",
                    message=f"HTTP error: {e.response.status_code}",
                ) from e

            except Exception as e:
                raise ExternalDataFetchError(
                    source="Ember",
                    message=f"Failed to parse CSV: {e}",
                ) from e

    raise ExternalDataFetchError(
        source="Ember",
        message="Failed to fetch CSV after retries",
    )
