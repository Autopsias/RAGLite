"""Unit tests for IPMA (Portuguese Weather Institute) client.

Story 7.1: Split test_external_data_clients.py
This module contains tests for: TestIPMAClient, TestIPMAClientAdditional, TestIPMAClientCoverage
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from raglite.external_data.clients.ipma import IPMAClient


class TestIPMAClient:
    """Tests for IPMA weather client."""

    @pytest.fixture
    def client(self) -> IPMAClient:
        """Create IPMA client instance."""
        return IPMAClient()

    @pytest.mark.asyncio
    async def test_fetch_observations_success(self, client: IPMAClient) -> None:
        """Test successful weather observations fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tMed": 15.5,
            "tMax": 20.0,
            "tMin": 10.0,
            "prec": 2.5,
            "humidade": 75.0,
            "vento": 15.0,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_observations(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
                station_id="1200535",
            )

            assert len(result) == 1
            assert result[0].__class__.__name__ == "IPMAWeatherData"
            assert result[0].temperature_c == 15.5
            assert result[0].temperature_max_c == 20.0
            assert result[0].precipitation_mm == 2.5

    @pytest.mark.asyncio
    async def test_fetch_forecast_success(self, client: IPMAClient) -> None:
        """Test successful forecast fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"forecastDate": "2024-01-01", "tMax": 18, "tMin": 10, "precipitaProb": 20},
                {"forecastDate": "2024-01-02", "tMax": 19, "tMin": 11, "precipitaProb": 10},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_forecast(location_id="1110600", days=2)

            assert len(result) == 2
            assert result[0].temperature_max_c == 18.0

    def test_stations_dict(self, client: IPMAClient) -> None:
        """Test station ID mapping."""
        assert "Lisboa" in client.STATIONS
        assert "Porto" in client.STATIONS
        assert client.STATIONS["Lisboa"] == "1200535"


# =============================================================================
# IPMA Client Additional Tests
# =============================================================================


class TestIPMAClientAdditional:
    """Additional tests for IPMA client coverage."""

    @pytest.fixture
    def client(self) -> IPMAClient:
        return IPMAClient()

    @pytest.mark.asyncio
    async def test_fetch_all_stations(self, client: IPMAClient) -> None:
        """Test fetching from all weather stations."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"tMed": 15.0}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_all_stations(date(2024, 1, 1))

        # Should fetch from multiple stations
        assert len(result) >= 1

    def test_parse_forecast_day_missing_fields(self, client: IPMAClient) -> None:
        """Test parsing forecast with missing optional fields."""
        data = {"forecastDate": "2024-01-01"}  # Missing temperature fields

        result = client._parse_forecast_day(data, "1110600")

        assert result is not None
        assert result.temperature_max_c is None


class TestIPMAClientCoverage:
    """Additional tests for IPMA client coverage."""

    @pytest.fixture
    def client(self) -> IPMAClient:
        return IPMAClient()

    @pytest.mark.asyncio
    async def test_fetch_observations_no_data(self, client: IPMAClient) -> None:
        """Test handling of empty observation response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # Empty response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_observations(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
            )

        # No valid observation data
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_fetch_observations_fetch_error(self, client: IPMAClient) -> None:
        """Test handling of fetch error during observations."""
        error_response = MagicMock()
        error_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found", request=MagicMock(), response=error_response
                )
            )

            # Should not raise - fetch errors are caught and result is empty
            result = await client.fetch_observations(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_forecast_parse_error(self, client: IPMAClient) -> None:
        """Test handling of parse error in forecast."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"forecastDate": "invalid-date"},  # Will fail to parse
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_forecast(location_id="1110600", days=1)

        # Invalid date causes parse failure, result is empty
        assert result == []

    def test_parse_observation_exception(self, client: IPMAClient) -> None:
        """Test parse observation with malformed data."""
        # Data that causes exception during parsing
        data = {"tMed": "not-a-number"}  # Will fail float conversion
        result = client._parse_observation(data, date(2024, 1, 1), "1200535")
        # Should return None on exception
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_observations_timeout_retry(self, client: IPMAClient) -> None:
        """Test timeout retry logic."""
        success_response = MagicMock()
        success_response.json.return_value = {"tMed": 15.0}
        success_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(
                side_effect=[
                    httpx.TimeoutException("timeout"),
                    success_response,
                ]
            )
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.fetch_observations(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 1),
                )

        # Retried and succeeded
        assert mock_get.call_count == 2


# =============================================================================
# Additional Coverage Tests for basegov.py
# =============================================================================
