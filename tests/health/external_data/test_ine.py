"""INE (Instituto Nacional de Estatistica) API health checks."""

import httpx
import pytest

# All health check tests hit real external APIs - exclude from regular CI runs
# Run manually with: pytest tests/health/ -m "" -v
pytestmark = [
    pytest.mark.health_check,
    pytest.mark.external_api,
]


class TestINEHealth:
    """INE (Instituto Nacional de Estatistica) API health checks."""

    @pytest.mark.asyncio
    async def test_ine_api_reachable(self):
        """Verify INE API endpoint responds."""
        url = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
        params = {"indession": "0012096", "op": "2"}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
            assert response.status_code == 200, f"INE API returned {response.status_code}"

    @pytest.mark.asyncio
    async def test_ine_building_permits_indicator(self):
        """Verify Building Permits indicator (0012096) returns data."""
        url = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
        params = {"indession": "0012096", "op": "2"}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list), "INE response should be a list"
            assert len(data) > 0, "INE returned no data for Building Permits"

    @pytest.mark.asyncio
    async def test_ine_construction_output_indicator(self):
        """Verify Construction Output indicator (0011845) returns data."""
        url = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
        params = {"indession": "0011845", "op": "2"}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
            assert response.status_code == 200
            data = response.json()
            assert len(data) > 0, "INE returned no data for Construction Output"

    @pytest.mark.asyncio
    async def test_ine_construction_cost_index_indicator(self):
        """Verify Construction Cost Index indicator (0011750) returns data."""
        url = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
        params = {"indession": "0011750", "op": "2"}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
            assert response.status_code == 200
            data = response.json()
            assert len(data) > 0, "INE returned no data for Construction Cost Index"

    @pytest.mark.asyncio
    async def test_ine_data_format_unchanged(self):
        """Verify INE response format matches expected structure."""
        url = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
        # Use varcd (not indession) for indicator requests
        params = {"varcd": "0012096", "op": "2", "lang": "PT"}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
            data = response.json()

            # Verify expected structure exists
            assert isinstance(data, list), "INE response should be a list"
            if len(data) > 0:
                record = data[0]
                # Check for response structure (Sucesso or data fields)
                record_str = str(record).lower()
                # INE returns either "sucesso" (success/error), "dim" (dimensions), or "dados" (data)
                assert any(
                    key in record_str for key in ["sucesso", "dim", "dados", "indicadorcod"]
                ), f"INE response structure changed - unexpected format: {record_str[:200]}"
