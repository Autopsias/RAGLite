"""Integration tests for Eurostat industrial indicators (Story 6.16 AC2)."""

from __future__ import annotations

from datetime import date

import pytest

from raglite.external_data.clients.eurostat import EurostatClient

try:
    from raglite.external_data.models import EurostatIndustrialProduction
except ImportError:
    EurostatIndustrialProduction = None

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.preserve_collection]


class TestEurostatIndustrialProductionIntegration:
    """Integration tests for Eurostat industrial production index.

    AC2: fetch_industrial_production() returns monthly index for Portugal
    AC4: Data has <10% missing values over analysis period

    These tests hit the real Eurostat SDMX API.
    """

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    # =========================================================================
    # AC2: Industrial Production Index API
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_monthly_portugal(self, client: EurostatClient) -> None:
        """
        AC2: Fetch industrial production for Portugal returns monthly data.

        Given: A request for Portugal industrial production data
        When: fetch_industrial_production() is called with date range 2020-2025
        Then: Returns monthly index values for Portugal (geo=PT)
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Need at least 4 years of monthly data (48 months)
        assert len(data) >= 48, f"Expected 48+ months, got {len(data)}"

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_country_portugal(self, client: EurostatClient) -> None:
        """
        AC2: All industrial production records are for Portugal.

        Given: A request for Portugal industrial production
        When: fetch_industrial_production() is called with country="PT"
        Then: All returned records have country="PT"
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert all(d.country == "PT" for d in data), "All records should be for Portugal"

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_index_values_positive(
        self, client: EurostatClient
    ) -> None:
        """
        AC2: Industrial production index values are positive.

        Given: Valid industrial production data
        When: Examining index values
        Then: All index values are > 0
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert all(d.index_value > 0 for d in data), "Index values must be positive"

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_date_range_respected(
        self, client: EurostatClient
    ) -> None:
        """
        AC2: Date range filters are applied correctly.

        Given: A request with specific date range
        When: fetch_industrial_production() is called
        Then: Returned data is within the specified range
        """
        start = date(2022, 1, 1)
        end = date(2023, 12, 31)

        data = await client.fetch_industrial_production(
            country="PT",
            start_date=start,
            end_date=end,
        )

        assert len(data) > 0, "Should return data for date range"
        assert data[0].date >= start
        assert data[-1].date <= end

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_returns_correct_model_type(
        self, client: EurostatClient
    ) -> None:
        """
        AC2: fetch_industrial_production returns EurostatIndustrialProduction instances.

        Given: A successful API call
        When: Examining returned data
        Then: All items are EurostatIndustrialProduction instances
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert all(d.__class__.__name__ == "EurostatIndustrialProduction" for d in data)

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_nace_sector_industry(
        self, client: EurostatClient
    ) -> None:
        """
        AC2: Industrial data uses NACE sector B-D (Mining, Manufacturing, Energy).

        Given: A request for industrial production
        When: fetch_industrial_production() is called
        Then: All records have nace_sector="B-D"
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert all(d.nace_sector == "B-D" for d in data), "Industrial sector should be NACE B-D"
