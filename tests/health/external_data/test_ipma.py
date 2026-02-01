"""IPMA (Portuguese weather) API health checks - currently working."""

import httpx
import pytest

# All health check tests hit real external APIs - exclude from regular CI runs
# Run manually with: pytest tests/health/ -m "" -v
pytestmark = [
    pytest.mark.health_check,
    pytest.mark.external_api,
]


class TestIPMAHealth:
    """IPMA (Portuguese weather) API health checks - currently working."""

    @pytest.mark.asyncio
    async def test_ipma_forecast_api_reachable(self):
        """Verify IPMA forecast API responds."""
        # IPMA public API for weather forecasts
        url = "https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/1110600.json"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            assert response.status_code == 200, f"IPMA API returned {response.status_code}"

    @pytest.mark.asyncio
    async def test_ipma_returns_forecast_data(self):
        """Verify IPMA returns actual forecast data."""
        url = "https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/1110600.json"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            data = response.json()

            assert "data" in data, "IPMA response missing 'data' field"
            assert len(data["data"]) > 0, "IPMA returned no forecast data"
