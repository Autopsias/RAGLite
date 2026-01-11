"""OMIE (Iberian Electricity Market) health checks."""

from datetime import date, timedelta

import httpx
import pytest


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
