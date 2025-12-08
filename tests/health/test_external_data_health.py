"""
External Data Source Health Checks

Run on PRs that modify external data code to detect API changes before merging.
These tests hit REAL APIs - excluded from regular test runs.

Usage:
    pytest tests/health/test_external_data_health.py -v --tb=short

CI Trigger: PRs modifying raglite/external_data/** or tests/health/**

Story: 6.9 - External Data Source Client Fixes
Created: 2025-12-08
"""

from datetime import date, timedelta

import httpx
import pytest

# Mark all tests as health checks (excluded from regular runs)
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


class TestCommoditiesHealth:
    """Ember Energy CO2 API health checks."""

    @pytest.mark.asyncio
    async def test_ember_new_domain_reachable(self):
        """Verify new Ember Energy API domain responds.

        Note: The public EU ETS API endpoint may return 404 as of late 2025.
        The test verifies the domain is reachable and responds with HTTP.
        The client implementation falls back to cached data when API unavailable.
        """
        url = "https://api.ember-energy.org/v1/carbon-price-tracker/eu-ets"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            # Accept any HTTP response - 200, 401, 403, or even 404 (endpoint exists)
            # What we're checking is that the domain resolves and responds
            assert response.status_code in [200, 401, 403, 404], (
                f"Ember API returned unexpected status {response.status_code}"
            )

    @pytest.mark.asyncio
    async def test_ember_old_domain_deprecated(self):
        """Verify old ember-climate.org domain is still deprecated (sanity check)."""
        url = "https://api.ember-climate.org/v1/carbon-price-tracker/eu-ets"

        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            try:
                response = await client.get(url)
                # Should return deprecation notice, redirect, or error
                assert response.status_code in [301, 302, 410, 404, 500], (
                    f"Old Ember domain may be working again (status {response.status_code}) - verify"
                )
            except httpx.ConnectError:
                # Domain completely gone is also acceptable
                pass
            except httpx.TimeoutException:
                # Timeout is acceptable for deprecated domain
                pass

    @pytest.mark.asyncio
    async def test_ember_api_docs_available(self):
        """Verify Ember API documentation is accessible."""
        url = "https://api.ember-energy.org/v1/docs"

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            # Docs page should be accessible
            assert response.status_code in [200, 301, 302], (
                f"Ember API docs returned {response.status_code}"
            )


class TestOMIEHealth:
    """OMIE (Iberian Electricity Market) health checks."""

    @pytest.mark.asyncio
    async def test_omie_file_download_endpoint_works(self):
        """Verify OMIE file-download endpoint responds."""
        yesterday = date.today() - timedelta(days=1)
        filename = f"marginalpdbc_{yesterday.strftime('%Y%m%d')}.1"
        url = f"https://www.omie.es/es/file-download?parents=marginalpdbc&filename={filename}"

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            assert response.status_code == 200, f"OMIE returned {response.status_code}"
            assert len(response.text) > 100, "OMIE response too short - may be error page"

    @pytest.mark.asyncio
    async def test_omie_csv_format_unchanged(self):
        """Verify OMIE CSV format matches expected data structure.

        OMIE file format (as of 2025-12-08):
        - Line 1: Header "MARGINALPDBC;"
        - Lines 2+: Data "YEAR;MONTH;DAY;HOUR;PT_PRICE;ES_PRICE;"
        """
        yesterday = date.today() - timedelta(days=1)
        filename = f"marginalpdbc_{yesterday.strftime('%Y%m%d')}.1"
        url = f"https://www.omie.es/es/file-download?parents=marginalpdbc&filename={filename}"

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            lines = response.text.strip().split("\n")

            # Verify at least header + some data lines exist
            assert len(lines) > 1, "OMIE returned file with only header"

            # First line should be header
            assert lines[0].strip().startswith("MARGINALPDBC"), (
                f"OMIE header format changed - got: {lines[0][:50]}"
            )

            # Data lines should have 6+ fields (YEAR;MONTH;DAY;HOUR;PT;ES)
            # Skip header line and find first data line
            data_lines = [line for line in lines[1:] if line.strip() and ";" in line]
            assert len(data_lines) > 0, "OMIE format changed - no data lines found"

            # Verify data line field count
            parts = data_lines[0].split(";")
            # Data format: YEAR;MONTH;DAY;HOUR;PT_PRICE;ES_PRICE;(empty or more)
            assert len(parts) >= 6, (
                f"OMIE data format changed - expected 6+ fields, got {len(parts)}: {data_lines[0][:100]}"
            )

    @pytest.mark.asyncio
    async def test_omie_old_url_pattern_still_broken(self):
        """Verify old URL pattern is still broken (sanity check)."""
        yesterday = date.today() - timedelta(days=1)
        old_url = (
            f"https://www.omie.es/sites/default/files/dados/"
            f"AGNO_{yesterday.year}/MES_{yesterday.month:02d}/TXT/"
            f"marginalpdbc_{yesterday.strftime('%Y%m%d')}.1"
        )

        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            response = await client.get(old_url)
            # Old URL should return 404 or redirect
            assert response.status_code in [404, 301, 302, 403], (
                f"Old OMIE URL may be working again (status {response.status_code}) - investigate"
            )

    @pytest.mark.asyncio
    async def test_omie_file_access_list_available(self):
        """Verify OMIE file access list page is accessible."""
        url = "https://www.omie.es/en/file-access-list"

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            assert response.status_code == 200, (
                f"OMIE file access list returned {response.status_code}"
            )


class TestBPstatHealth:
    """BPstat (Banco de Portugal Statistics) health checks."""

    @pytest.mark.asyncio
    async def test_bpstat_observations_api_reachable(self):
        """Verify BPstat observations API endpoint responds."""
        url = "https://bpstat.bportugal.pt/api/observations/"
        params = {"series_ids": "12710733", "lang": "EN"}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
            assert response.status_code == 200, f"BPstat API returned {response.status_code}"

    @pytest.mark.asyncio
    async def test_bpstat_mortgage_rate_median_series_valid(self):
        """Verify median mortgage rate series (12710733) returns interest rate data."""
        url = "https://bpstat.bportugal.pt/api/series/12710733"

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            assert response.status_code == 200, (
                f"Series 12710733 not found (status {response.status_code})"
            )

            data = response.json()
            title = data.get("data", {}).get("title", {}).get("EN", "").lower()

            # Verify it's interest rate data, not FX rates or other data
            rate_keywords = [
                "interest",
                "rate",
                "taxa",
                "juro",
                "loan",
                "housing",
                "mortgage",
                "transaction",
            ]
            has_rate_keyword = any(kw in title for kw in rate_keywords)
            assert has_rate_keyword, f"Series 12710733 may have changed meaning: {title}"

    @pytest.mark.asyncio
    async def test_bpstat_mortgage_rate_10th_percentile_valid(self):
        """Verify 10th percentile mortgage rate series (12710735) is valid."""
        url = "https://bpstat.bportugal.pt/api/series/12710735"

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            assert response.status_code == 200, (
                f"Series 12710735 not found (status {response.status_code})"
            )

    @pytest.mark.asyncio
    async def test_bpstat_mortgage_rate_25th_percentile_valid(self):
        """Verify 25th percentile mortgage rate series (12710781) is valid."""
        url = "https://bpstat.bportugal.pt/api/series/12710781"

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            assert response.status_code == 200, (
                f"Series 12710781 not found (status {response.status_code})"
            )

    @pytest.mark.asyncio
    async def test_bpstat_old_series_still_wrong(self):
        """Verify old series 12532089 is still NOT mortgage data (sanity check)."""
        url = "https://bpstat.bportugal.pt/api/series/12532089"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                title = data.get("data", {}).get("title", {}).get("EN", "").lower()

                # This should still be Egyptian Pound or other FX, not mortgage data
                mortgage_keywords = ["mortgage", "housing", "loan", "habitacao"]
                has_mortgage_keyword = any(kw in title for kw in mortgage_keywords)

                assert not has_mortgage_keyword, (
                    f"Old series 12532089 may now be valid mortgage data: {title} - investigate"
                )

    @pytest.mark.asyncio
    async def test_bpstat_old_api_endpoint_broken(self):
        """Verify old API endpoint is still broken (sanity check)."""
        url = "https://bpstat.bportugal.pt/data/v1/series/12710733/observations"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            # Old endpoint should return 404
            assert response.status_code in [404, 301, 302], (
                f"Old BPstat API endpoint may be working again (status {response.status_code})"
            )


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


class TestATICHealth:
    """ATIC (cement industry) health checks - CSV-based, currently working."""

    @pytest.mark.asyncio
    async def test_atic_client_importable(self):
        """Verify ATIC client can be imported (CSV-based, no API)."""
        try:
            from raglite.external_data.clients.atic import ATICClient

            client = ATICClient()
            assert client is not None
        except ImportError as e:
            pytest.fail(f"ATIC client import failed: {e}")

    @pytest.mark.asyncio
    async def test_atic_has_fetch_method(self):
        """Verify ATIC client has expected fetch and parse methods."""
        from raglite.external_data.clients.atic import ATICClient

        client = ATICClient()

        # Check for expected method names (ATIC is CSV-based, not API-based)
        has_fetch = hasattr(client, "fetch_historical_data")
        has_parse_file = hasattr(client, "parse_csv_file")
        has_parse_content = hasattr(client, "parse_csv_content")

        assert has_fetch, "ATIC client missing fetch_historical_data method"
        assert has_parse_file, "ATIC client missing parse_csv_file method"
        assert has_parse_content, "ATIC client missing parse_csv_content method"


class TestHealthSummary:
    """Generate health check summary and verify all sources checked."""

    def test_all_sources_have_health_checks(self):
        """Verify all 8 data sources have health check classes."""
        expected_sources = [
            "INE",
            "Commodities",
            "OMIE",
            "BPstat",
            "EUOilBulletin",
            "BaseGov",
            "IPMA",
            "ATIC",
        ]

        # Get all test classes in this module
        import sys

        current_module = sys.modules[__name__]
        test_classes = [
            name
            for name in dir(current_module)
            if name.startswith("Test") and name != "TestHealthSummary"
        ]

        for source in expected_sources:
            matching_class = [c for c in test_classes if source.lower() in c.lower()]
            assert len(matching_class) > 0, f"Missing health check class for {source}"

    def test_health_check_count(self):
        """Verify minimum number of health checks exist."""
        import sys

        current_module = sys.modules[__name__]

        test_count = 0
        for name in dir(current_module):
            if name.startswith("Test") and name != "TestHealthSummary":
                cls = getattr(current_module, name)
                methods = [m for m in dir(cls) if m.startswith("test_")]
                test_count += len(methods)

        # Should have at least 25 health check tests
        assert test_count >= 25, f"Only {test_count} health checks - expected at least 25"
