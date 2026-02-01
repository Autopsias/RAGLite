"""Integration tests for ECB HICP inflation fetching (Story 6.17 AC2)."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.external_data.clients.ecb import ECBClient

from .conftest import SAMPLE_HICP_CSV

# Task 0.4: Added external_api marker + 60s timeout for API tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.external_api,
    pytest.mark.timeout(60),
]


@pytest.mark.asyncio
class TestECBInflationIntegration:
    """Integration tests for ECB HICP inflation fetching."""

    async def test_ac2_fetch_inflation_portugal_four_years(self) -> None:
        """
        Given: Request for Portugal HICP inflation data from 2020-2024
        When: fetch_inflation() is called
        Then: Returns at least 48 months of HICP index values for Portugal

        AC2: HICP inflation API returns monthly index for Portugal
        """
        client = ECBClient()

        mock_response = MagicMock()
        mock_response.text = SAMPLE_HICP_CSV
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            data = await client.fetch_inflation(
                country="PT",
                start_date=date(2020, 1, 1),
                end_date=date(2024, 12, 31),
            )

        assert len(data) >= 48, f"Expected at least 48 months, got {len(data)}"
        assert all(d.country == "PT" for d in data)

    async def test_ac2_fetch_inflation_index_in_reasonable_range(self) -> None:
        """
        Given: HICP inflation data for Portugal
        When: Data is fetched
        Then: Index values are in reasonable range (80-150)

        AC2: HICP index values are realistic (2015=100 base)
        """
        client = ECBClient()

        mock_response = MagicMock()
        mock_response.text = SAMPLE_HICP_CSV
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            data = await client.fetch_inflation(
                country="PT",
                start_date=date(2020, 1, 1),
                end_date=date(2024, 12, 31),
            )

        # HICP index 2015=100, so values should be around 100-120 for recent years
        assert all(80.0 <= d.index_value <= 150.0 for d in data)

    async def test_ac2_fetch_inflation_monthly_frequency(self) -> None:
        """
        Given: HICP inflation data fetched from ECB
        When: Examining the dates
        Then: All dates are first day of month (monthly data)

        AC2: HICP is monthly data
        """
        client = ECBClient()

        mock_response = MagicMock()
        mock_response.text = SAMPLE_HICP_CSV
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            data = await client.fetch_inflation(
                country="PT",
                start_date=date(2020, 1, 1),
                end_date=date(2024, 12, 31),
            )

        for record in data:
            assert record.date.day == 1, f"Date {record.date} is not first of month"

    async def test_ac2_fetch_inflation_yoy_calculation(self) -> None:
        """
        Given: HICP data spanning more than 12 months
        When: Data is parsed
        Then: YoY change percentage is calculated for records after first 12 months

        AC2: YoY inflation rate calculated from index values
        """
        client = ECBClient()

        mock_response = MagicMock()
        mock_response.text = SAMPLE_HICP_CSV
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            data = await client.fetch_inflation(
                country="PT",
                start_date=date(2020, 1, 1),
                end_date=date(2024, 12, 31),
            )

        # Records from year 2 onwards should have YoY calculations
        year2_onwards = [d for d in data if d.date >= date(2021, 1, 1)]
        records_with_yoy = [d for d in year2_onwards if d.yoy_change_pct is not None]

        # Most records should have YoY (some may not if data gaps)
        assert len(records_with_yoy) > 0, "Expected YoY calculations for year 2+ data"

    async def test_ac2_fetch_inflation_2022_inflation_spike(self) -> None:
        """
        Given: HICP data including 2022 (high inflation period)
        When: Data is fetched
        Then: 2022 shows significant YoY increases

        AC2: Capture real-world inflation patterns
        """
        client = ECBClient()

        mock_response = MagicMock()
        mock_response.text = SAMPLE_HICP_CSV
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            data = await client.fetch_inflation(
                country="PT",
                start_date=date(2020, 1, 1),
                end_date=date(2024, 12, 31),
            )

        # Find mid-2022 when inflation peaked
        mid_2022 = [d for d in data if d.date == date(2022, 6, 1)]
        if mid_2022 and mid_2022[0].yoy_change_pct is not None:
            # Portugal had ~8-9% inflation mid-2022
            assert mid_2022[0].yoy_change_pct > 5.0, "Expected high inflation in mid-2022"


@pytest.mark.slow
@pytest.mark.external_api
@pytest.mark.asyncio
class TestECBInflationRealAPI:
    """Real API tests for HICP inflation."""

    async def test_real_inflation_portugal(self) -> None:
        """
        Given: Real ECB SDW API connection
        When: fetch_inflation() is called
        Then: Real HICP data for Portugal is returned

        AC2: Real API integration verification
        """
        client = ECBClient()

        data = await client.fetch_inflation(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert len(data) >= 48, f"Expected at least 48 months, got {len(data)}"
        assert all(d.country == "PT" for d in data)
