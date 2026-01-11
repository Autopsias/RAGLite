"""BaseGov (Portuguese public procurement) health checks."""

import httpx
import pytest


class TestBaseGovHealth:
    """BaseGov (Portuguese public procurement) health checks."""

    @pytest.mark.asyncio
    async def test_dados_gov_ocds_dataset_exists(self):
        """Verify OCDS dataset exists on dados.gov.pt."""
        url = "https://dados.gov.pt/api/1/datasets/ocds-portal-base-www-base-gov-pt/"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            assert response.status_code == 200, f"OCDS dataset not found: {response.status_code}"

            data = response.json()
            assert "resources" in data, "OCDS dataset has no resources field"

    @pytest.mark.asyncio
    async def test_dados_gov_impic_dataset_has_resources(self):
        """Verify IMPIC XLSX dataset has downloadable resources.

        Note: OCDS dataset has 0 resources as of 2025-12-08.
        IMPIC dataset is the primary source with yearly XLSX files (2012-2025).
        """
        url = "https://dados.gov.pt/api/1/datasets/contratos-publicos-portal-base-impic-contratos-de-2012-a-2025/"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            assert response.status_code == 200, f"IMPIC dataset not found: {response.status_code}"

            data = response.json()
            resources = data.get("resources", [])
            assert len(resources) > 0, "IMPIC dataset has no resources available"

            # Check for XLSX resources with yearly contract files
            xlsx_resources = [r for r in resources if r.get("format", "").lower() == "xlsx"]
            assert len(xlsx_resources) >= 10, (
                f"IMPIC dataset should have 10+ yearly XLSX files, found {len(xlsx_resources)}"
            )

            # Verify recent year file exists
            titles = [r.get("title", "") for r in xlsx_resources]
            has_2024 = any("2024" in t for t in titles)
            assert has_2024, f"IMPIC dataset missing 2024 contracts file: {titles[:5]}"

    @pytest.mark.asyncio
    async def test_basegov_no_json_api_pesquisa(self):
        """Verify Base.gov.pt /pesquisa/resultados has no JSON API (sanity check)."""
        url = "https://www.base.gov.pt/Base4/pt/pesquisa/resultados"

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    assert "application/json" not in content_type, (
                        "Base.gov.pt may have JSON API now at /pesquisa/resultados"
                    )
            except httpx.ConnectError:
                pass  # Endpoint doesn't exist, which is expected

    @pytest.mark.asyncio
    async def test_basegov_no_json_api_direct(self):
        """Verify Base.gov.pt /api/contratos doesn't exist (sanity check)."""
        urls_to_check = [
            "https://www.base.gov.pt/Base4/api/contratos",
            "https://www.base.gov.pt/api/contratos",
            "https://www.base.gov.pt/Base4/pt/api/contratos",
        ]

        async with httpx.AsyncClient(timeout=30) as client:
            for url in urls_to_check:
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "")
                        assert "application/json" not in content_type, (
                            f"Base.gov.pt may have JSON API now at {url}"
                        )
                except httpx.ConnectError:
                    pass  # Endpoint doesn't exist, which is expected

    @pytest.mark.asyncio
    async def test_ted_api_available(self):
        """Verify TED (Tenders Electronic Daily) API is accessible as backup."""
        # TED API v3 endpoint (must match basegov.py TED_API_BASE)
        url = "https://tedweb.api.ted.europa.eu/v3/notices/search"

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                # POST endpoint - GET may not be supported
                response = await client.post(
                    url, json={"query": "(place-of-performance = PT)", "limit": 1}
                )
                # API should respond (may require auth or return error, but should be reachable)
                assert response.status_code in [200, 400, 401, 403], (
                    f"TED API returned unexpected {response.status_code}"
                )
            except httpx.ConnectError:
                pytest.fail("TED API is not reachable")
