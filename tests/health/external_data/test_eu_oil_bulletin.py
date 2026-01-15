"""EU Oil Bulletin (diesel prices) health checks."""

import httpx
import pytest

# All health check tests hit real external APIs - exclude from regular CI runs
# Run manually with: pytest tests/health/ -m "" -v
pytestmark = [
    pytest.mark.health_check,
    pytest.mark.external_api,
]


class TestEUOilBulletinHealth:
    """EU Oil Bulletin (diesel prices) health checks."""

    @pytest.mark.asyncio
    async def test_eu_oil_xlsx_historical_available(self):
        """Verify EU Oil Bulletin historical XLSX file is downloadable."""
        url = (
            "https://energy.ec.europa.eu/document/download/906e60ca-8b6a-44e7-8589-652854d2fd3f_en"
        )
        params = {"filename": "Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx"}

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url, params=params)
            assert response.status_code == 200, f"EU Oil XLSX returned {response.status_code}"
            # File should be ~4MB
            assert len(response.content) > 1_000_000, (
                f"EU Oil XLSX file too small ({len(response.content)} bytes) - expected ~4MB"
            )

    @pytest.mark.asyncio
    async def test_eu_oil_xlsx_is_valid_xlsx(self):
        """Verify downloaded file is actually an XLSX (not error page)."""
        url = (
            "https://energy.ec.europa.eu/document/download/906e60ca-8b6a-44e7-8589-652854d2fd3f_en"
        )
        params = {"filename": "Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx"}

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url, params=params)

            # XLSX files start with PK (ZIP signature)
            assert response.content[:2] == b"PK", "Downloaded file is not a valid XLSX (ZIP) file"

    @pytest.mark.asyncio
    async def test_eu_oil_bulletin_page_accessible(self):
        """Verify EU Oil Bulletin main page is accessible."""
        url = "https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en"

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            assert response.status_code == 200, (
                f"EU Oil Bulletin page returned {response.status_code}"
            )

    @pytest.mark.asyncio
    async def test_eu_oil_old_xml_still_broken(self):
        """Verify old XML endpoint is still broken (sanity check)."""
        url = "https://ec.europa.eu/energy/observatory/reports/Oil_Bulletin_Prices_History.xml"

        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            response = await client.get(url)
            # Should redirect to homepage (302) or not exist (404)
            assert response.status_code in [301, 302, 404], (
                f"Old XML endpoint may be working again: {response.status_code}"
            )
