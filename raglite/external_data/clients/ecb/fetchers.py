"""ECB API fetch methods with retry logic.

Story 8.2 Task 5: ECB client refactoring
"""

from datetime import date

from raglite.external_data.clients.base import BaseExternalClient
from raglite.external_data.clients.ecb.config import ECB_API_BASE
from raglite.external_data.clients.ecb.parsers import convert_eurostat_json_to_ecb_format
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Shared client instance for retry infrastructure
_client = BaseExternalClient()


async def fetch_series(
    series_key: str,
    start_date: date,
    end_date: date,
    timeout: float,
) -> str:
    """Fetch data series from ECB SDMX API.

    Args:
        series_key: ECB SDMX series key
        start_date: Start of date range
        end_date: End of date range
        timeout: Request timeout in seconds

    Returns:
        CSV data as string

    Raises:
        ExternalDataFetchError: If fetch fails
    """
    # ECB SDMX API URL
    url = f"{ECB_API_BASE}/FM/{series_key}"
    params = {
        "startPeriod": start_date.strftime("%Y-%m"),
        "endPeriod": end_date.strftime("%Y-%m"),
        "format": "csvdata",
    }

    # Use base class retry infrastructure
    _client.timeout = timeout
    response = await _client._fetch_with_retry(url, params=params)
    return response.text


async def fetch_gdp_series(
    series_key: str,
    start_date: date | None,
    end_date: date | None,
    timeout: float,
) -> str:
    """Fetch GDP series from ECB SDMX API (MNA dataset).

    Args:
        series_key: ECB SDMX series key for GDP
        start_date: Start of date range
        end_date: End of date range
        timeout: Request timeout in seconds

    Returns:
        CSV data as string
    """
    # ECB SDMX API URL for MNA dataset
    url = f"{ECB_API_BASE}/MNA/{series_key}"
    params = {"format": "csvdata"}

    if start_date:
        params["startPeriod"] = f"{start_date.year}-Q{(start_date.month - 1) // 3 + 1}"
    if end_date:
        params["endPeriod"] = f"{end_date.year}-Q{(end_date.month - 1) // 3 + 1}"

    # Use base class retry infrastructure with 404 fallback handling
    _client.timeout = timeout
    try:
        response = await _client._fetch_with_retry(url, params=params)
        return response.text
    except Exception as e:
        # Story 6.24: ECB GDP endpoint discontinued, fallback to Eurostat
        # Check if error was 404 by inspecting the original error
        if hasattr(e, "original_error") and hasattr(e.original_error, "response"):
            if e.original_error.response.status_code == 404:
                # Extract country from series_key (format: Q.Y.PT.W2...)
                country = series_key.split(".")[2] if "." in series_key else "PT"
                logger.warning(
                    "ECB GDP endpoint not found (404), falling back to Eurostat",
                    extra={"series_key": series_key, "country": country},
                )
                return await fetch_gdp_from_eurostat(start_date, end_date, country, timeout)
        raise


async def fetch_gdp_from_eurostat(
    start_date: date | None,
    end_date: date | None,
    country: str,
    timeout: float,
) -> str:
    """Fetch GDP growth data from Eurostat API as fallback for ECB.

    Story 6.24: ECB discontinued GDP endpoint, use Eurostat replacement.

    Eurostat Dataset: namq_10_gdp (National accounts aggregates)
    Endpoint: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/namq_10_gdp

    Args:
        start_date: Start of date range
        end_date: End of date range
        country: ISO 2-letter country code (default: PT)
        timeout: Request timeout in seconds

    Returns:
        CSV data in ECB-compatible format for parse_gdp_csv()

    Raises:
        ExternalDataFetchError: If fetch fails
    """
    # Eurostat API URL for GDP data
    url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/namq_10_gdp"
    params = {
        "geo": country,
        "na_item": "B1GQ",  # GDP at market prices
        "unit": "CLV_I10",  # Chain-linked volumes, index 2010=100
        "s_adj": "SCA",  # Seasonally and calendar adjusted
    }

    # Add date range filters if provided
    if start_date:
        params["startPeriod"] = f"{start_date.year}-Q{(start_date.month - 1) // 3 + 1}"
    if end_date:
        params["endPeriod"] = f"{end_date.year}-Q{(end_date.month - 1) // 3 + 1}"

    # Use base class retry infrastructure
    _client.timeout = timeout
    response = await _client._fetch_with_retry(url, params=params)

    # Parse JSON response and convert to ECB-compatible CSV format
    eurostat_json = response.json()
    return convert_eurostat_json_to_ecb_format(eurostat_json)


async def fetch_hicp_series(
    series_key: str,
    start_date: date | None,
    end_date: date | None,
    timeout: float,
) -> str:
    """Fetch HICP series from ECB SDMX API (ICP dataset).

    Args:
        series_key: ECB SDMX series key for HICP
        start_date: Start of date range
        end_date: End of date range
        timeout: Request timeout in seconds

    Returns:
        CSV data as string
    """
    # ECB SDMX API URL for ICP dataset
    url = f"{ECB_API_BASE}/ICP/{series_key}"
    params = {"format": "csvdata"}

    if start_date:
        params["startPeriod"] = start_date.strftime("%Y-%m")
    if end_date:
        params["endPeriod"] = end_date.strftime("%Y-%m")

    # Use base class retry infrastructure
    _client.timeout = timeout
    response = await _client._fetch_with_retry(url, params=params)
    return response.text
