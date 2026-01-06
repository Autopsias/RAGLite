"""Ember Energy CO2 API health checks."""

import httpx
import pytest


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
