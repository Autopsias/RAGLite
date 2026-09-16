"""Integration tests for Eurostat construction indicators (Story 6.16 AC1)."""

from __future__ import annotations

from datetime import date

import pytest

from raglite.external_data.clients.eurostat import EurostatClient

try:
    from raglite.external_data.models import EurostatConstructionOutput
except ImportError:
    EurostatConstructionOutput = None

# Task 0.4: Added external_api marker + 60s timeout for API tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.preserve_collection,
    pytest.mark.external_api,
    pytest.mark.timeout(60),
]


class TestEurostatConstructionOutputIntegration:
    """Integration tests for Eurostat construction output index.

    AC1: fetch_construction_output() returns monthly index for Portugal (2020-2025)
    AC4: Data has <10% missing values over analysis period

    These tests hit the real Eurostat SDMX API.
    """

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    # =========================================================================
    # AC1: Construction Output Index API
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ac1_construction_output_monthly_portugal(self, client: EurostatClient) -> None:
        """
        AC1: Fetch construction output for Portugal returns monthly data.

        Given: A request for Portugal construction output data
        When: fetch_construction_output() is called with date range 2020-2025
        Then: Returns monthly index values for Portugal (geo=PT)
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Need at least 4 years of monthly data (48 months)
        assert len(data) >= 48, f"Expected 48+ months, got {len(data)}"

    @pytest.mark.asyncio
    async def test_ac1_construction_output_country_portugal(self, client: EurostatClient) -> None:
        """
        AC1: All construction output records are for Portugal.

        Given: A request for Portugal construction output
        When: fetch_construction_output() is called with country="PT"
        Then: All returned records have country="PT"
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert all(d.country == "PT" for d in data), "All records should be for Portugal"

    @pytest.mark.asyncio
    async def test_ac1_construction_output_index_values_positive(
        self, client: EurostatClient
    ) -> None:
        """
        AC1: Construction output index values are positive.

        Given: Valid construction output data
        When: Examining index values
        Then: All index values are > 0
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert all(d.index_value > 0 for d in data), "Index values must be positive"

    @pytest.mark.asyncio
    async def test_ac1_construction_output_date_range_respected(
        self, client: EurostatClient
    ) -> None:
        """
        AC1: Date range filters are applied correctly.

        Given: A request with specific date range
        When: fetch_construction_output() is called
        Then: Returned data is within the specified range
        """
        start = date(2022, 1, 1)
        end = date(2023, 12, 31)

        data = await client.fetch_construction_output(
            country="PT",
            start_date=start,
            end_date=end,
        )

        assert len(data) > 0, "Should return data for date range"
        assert data[0].date >= start, f"First date {data[0].date} should be >= {start}"
        assert data[-1].date <= end, f"Last date {data[-1].date} should be <= {end}"

    @pytest.mark.asyncio
    async def test_ac1_construction_output_returns_correct_model_type(
        self, client: EurostatClient
    ) -> None:
        """
        AC1: fetch_construction_output returns EurostatConstructionOutput instances.

        Given: A successful API call
        When: Examining returned data
        Then: All items are EurostatConstructionOutput instances
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert all(d.__class__.__name__ == "EurostatConstructionOutput" for d in data)

    @pytest.mark.asyncio
    async def test_ac1_construction_output_nace_sector_construction(
        self, client: EurostatClient
    ) -> None:
        """
        AC1: Construction data uses NACE sector F (Construction).

        Given: A request for construction output
        When: fetch_construction_output() is called
        Then: All records have nace_sector="F"
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert all(d.nace_sector == "F" for d in data), "Construction sector should be NACE F"
