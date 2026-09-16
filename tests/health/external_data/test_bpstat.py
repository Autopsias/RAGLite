"""BPstat (Banco de Portugal Statistics) health checks."""

import httpx
import pytest

# All health check tests hit real external APIs - exclude from regular CI runs
# Run manually with: pytest tests/health/ -m "" -v
pytestmark = [
    pytest.mark.health_check,
    pytest.mark.external_api,
]


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
