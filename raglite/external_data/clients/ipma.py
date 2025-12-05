"""IPMA (Instituto Português do Mar e da Atmosfera) API client.

Story 6.1: Tier 1 External Data Source Integration

Fetches Portuguese weather data:
- Temperature (min, max, average)
- Precipitation
- Wind speed
- Humidity

API Documentation: https://api.ipma.pt/open-data/
"""

from __future__ import annotations

import asyncio
import os
from datetime import date, timedelta

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import IPMAWeatherData
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# IPMA Open Data API
IPMA_API_BASE = "https://api.ipma.pt/open-data"


class IPMAClient:
    """Client for IPMA weather data API.

    IPMA provides open access to Portuguese weather observations and forecasts.

    Example:
        >>> client = IPMAClient()
        >>> weather = await client.fetch_observations(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 1, 31),
        ...     station_id="1200535"  # Lisboa
        ... )
    """

    # Major weather station IDs in Portugal
    STATIONS = {
        "Lisboa": "1200535",
        "Porto": "1131200",
        "Faro": "1080500",
        "Coimbra": "1061203",
        "Beja": "1021201",
        "Braganca": "1041200",
        "Evora": "1070500",
        "Leiria": "1100535",
    }

    def __init__(self) -> None:
        self.base_url = IPMA_API_BASE
        self.api_key = settings.ipma_api_key  # Public API, usually not needed
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def _fetch_with_retry(self, url: str) -> dict:
        """Fetch data from IPMA API with retry logic.

        Args:
            url: Full API URL

        Returns:
            JSON response

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [1, 2, 4]

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["api-key"] = self.api_key

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    return response.json()

                except httpx.TimeoutException as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "IPMA API timeout, retrying",
                            extra={"attempt": attempt + 1, "delay": delay, "url": url},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="IPMA",
                            message="Timeout after retries",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    # Retry on server errors (5xx) or rate limit (429)
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="IPMA",
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(source="IPMA", message="Unexpected retry loop exit")

    async def fetch_observations(
        self,
        start_date: date,
        end_date: date,
        station_id: str | None = None,
    ) -> list[IPMAWeatherData]:
        """Fetch weather observations for date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            station_id: Weather station ID (default: Lisboa)

        Returns:
            List of weather observation records
        """
        if station_id is None:
            station_id = self.STATIONS["Lisboa"]

        logger.info(
            "Fetching IPMA observations",
            extra={
                "start": str(start_date),
                "end": str(end_date),
                "station": station_id,
            },
        )

        results = []
        current_date = start_date

        while current_date <= end_date:
            try:
                url = (
                    f"{self.base_url}/observation/climate/daily/"
                    f"{current_date.strftime('%Y%m%d')}/{station_id}"
                )
                data = await self._fetch_with_retry(url)
                observation = self._parse_observation(data, current_date, station_id)
                if observation:
                    results.append(observation)
            except ExternalDataFetchError:
                # Skip days with no data
                pass

            current_date += timedelta(days=1)

        logger.info(
            "Fetched IPMA observations",
            extra={"record_count": len(results), "station": station_id},
        )
        return results

    async def fetch_forecast(
        self,
        location_id: str | None = None,
        days: int = 5,
    ) -> list[IPMAWeatherData]:
        """Fetch weather forecast.

        Args:
            location_id: Location ID (default: Lisboa)
            days: Number of days to forecast (max 10)

        Returns:
            List of forecast records
        """
        if location_id is None:
            location_id = "1110600"  # Lisboa district

        logger.info(
            "Fetching IPMA forecast",
            extra={"location": location_id, "days": days},
        )

        url = f"{self.base_url}/forecast/meteorology/cities/daily/{location_id}.json"
        data = await self._fetch_with_retry(url)

        results = []
        for day_data in data.get("data", [])[:days]:
            try:
                forecast = self._parse_forecast_day(day_data, location_id)
                if forecast:
                    results.append(forecast)
            except (KeyError, ValueError) as e:
                logger.warning(
                    "Failed to parse IPMA forecast day",
                    extra={"error": str(e)},
                )

        return results

    async def fetch_all_stations(
        self,
        target_date: date,
    ) -> list[IPMAWeatherData]:
        """Fetch weather data from all major stations for a date.

        Args:
            target_date: Date to fetch

        Returns:
            List of observations from all stations
        """
        results = []

        for station_name, station_id in self.STATIONS.items():
            try:
                obs = await self.fetch_observations(
                    start_date=target_date,
                    end_date=target_date,
                    station_id=station_id,
                )
                if obs:
                    obs[0].station_name = station_name
                    results.extend(obs)
            except ExternalDataFetchError as e:
                logger.warning(
                    "Failed to fetch IPMA station data",
                    extra={"station": station_name, "error": str(e)},
                )

        return results

    def _parse_observation(
        self,
        data: dict,
        obs_date: date,
        station_id: str,
    ) -> IPMAWeatherData | None:
        """Parse observation data.

        Args:
            data: API response
            obs_date: Observation date
            station_id: Weather station ID

        Returns:
            Weather observation or None
        """
        if not data:
            return None

        try:
            return IPMAWeatherData(
                date=obs_date,
                station_id=station_id,
                temperature_c=data.get("tMed"),
                temperature_max_c=data.get("tMax"),
                temperature_min_c=data.get("tMin"),
                precipitation_mm=data.get("prec"),
                humidity_pct=data.get("humidade"),
                wind_speed_kmh=data.get("vento"),
            )
        except Exception as e:
            logger.warning(
                "Failed to parse IPMA observation",
                extra={"date": str(obs_date), "error": str(e)},
            )
            return None

    def _parse_forecast_day(
        self,
        data: dict,
        location_id: str,
    ) -> IPMAWeatherData | None:
        """Parse forecast day data.

        Args:
            data: Forecast day data
            location_id: Location identifier

        Returns:
            Weather forecast or None
        """
        try:
            forecast_date = date.fromisoformat(data["forecastDate"])

            return IPMAWeatherData(
                date=forecast_date,
                station_id=location_id,
                temperature_max_c=float(data.get("tMax", 0)) if data.get("tMax") else None,
                temperature_min_c=float(data.get("tMin", 0)) if data.get("tMin") else None,
                precipitation_mm=float(data.get("precipitaProb", 0))
                if data.get("precipitaProb")
                else None,
            )
        except (KeyError, ValueError) as e:
            logger.warning(
                "Failed to parse IPMA forecast",
                extra={"error": str(e)},
            )
            return None
