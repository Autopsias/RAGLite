"""Integration tests for IPMA, EU Oil Bulletin, ATIC, and Commodities clients."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from raglite.external_data.clients import (
    ATICClient,
    CommoditiesClient,
    EUOilBulletinClient,
    IPMAClient,
)
from raglite.external_data.models import (
    CO2EUAPrice,
    CoalPrice,
    DataSource,
    EUDieselPrice,
)

# Task 0.4: Added external_api marker + 60s timeout for API tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.external_api,
    pytest.mark.timeout(60),
]


@pytest.mark.asyncio
class TestIPMAClientIntegration:
    """Integration tests for IPMA weather client."""

    async def test_weather_observations_fetch(self, sample_ipma_response, mock_response) -> None:
        """Test fetching weather observations."""
        client = IPMAClient()

        http_mock = mock_response(json_data=sample_ipma_response)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=http_mock)

            result = await client.fetch_observations(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
                station_id="1200535",
            )

        assert len(result) == 1
        obs = result[0]
        assert obs.__class__.__name__ == "IPMAWeatherData"
        assert obs.source == DataSource.IPMA
        assert obs.temperature_c == 15.5
        assert obs.temperature_max_c == 20.0
        assert obs.precipitation_mm == 2.5


@pytest.mark.asyncio
class TestEUOilBulletinIntegration:
    """Integration tests for EU Oil Bulletin client."""

    async def test_diesel_prices_portugal(self, sample_eu_oil_bulletin_prices) -> None:
        """Test fetching Portugal diesel prices.

        Story 6.9.4: EU Oil Bulletin now uses XLSX format instead of XML.
        We mock the _parse_xlsx method to return test data since creating
        a valid XLSX in memory is complex.
        """
        client = EUOilBulletinClient()

        # Create mock parsed results (what _parse_xlsx would return)
        mock_results = [
            EUDieselPrice(
                date=date.fromisoformat(item["date"]),
                price_eur_litre=item["price"],
                country=item["country"],
                tax_included=True,
            )
            for item in sample_eu_oil_bulletin_prices
        ]

        # Mock the parsing and caching methods
        with (
            patch.object(client, "_get_cached_xlsx", return_value=None),
            patch.object(client, "_fetch_xlsx_data", new_callable=AsyncMock) as mock_fetch,
            patch.object(client, "_save_to_cache"),
            patch.object(client, "_parse_xlsx", return_value=mock_results),
        ):
            # Return fake XLSX bytes (content doesn't matter since _parse_xlsx is mocked)
            mock_fetch.return_value = b"PK\x03\x04fake_xlsx_content"

            result = await client.fetch_diesel_prices(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 31),
                country="Portugal",
            )

        # Should have 7 Portugal records (filtered from sample)
        assert len(result) == 7
        for price in result:
            assert price.__class__.__name__ == "EUDieselPrice"
            assert price.source == DataSource.EU_OIL_BULLETIN
            assert price.country == "Portugal"
            assert 1.0 <= price.price_eur_litre <= 2.0


class TestATICClientIntegration:
    """Integration tests for ATIC cement client."""

    def test_csv_import_and_validation(self, tmp_path: Path) -> None:
        """Test CSV import with full validation."""
        client = ATICClient()

        csv_content = """date,consumption,region,type
2024-01-01,150000,Portugal,gray
2024-02-01,160000,Portugal,gray
2024-03-01,170000,Portugal,gray
2024-01-01,25000,Lisboa,white
2024-02-01,27000,Lisboa,white
2024-03-01,29000,Lisboa,white"""

        csv_file = tmp_path / "atic_q1_2024.csv"
        csv_file.write_text(csv_content)

        result = client.parse_csv_file(csv_file)

        assert len(result) == 6
        for record in result:
            assert record.__class__.__name__ == "ATICCementConsumption"
            assert record.source == DataSource.ATIC
            assert record.consumption_tonnes > 0

        # Verify date filtering
        q1_records = [r for r in result if date(2024, 1, 1) <= r.date <= date(2024, 3, 31)]
        assert len(q1_records) == 6


class TestCommoditiesClientIntegration:
    """Integration tests for commodities client."""

    def test_multi_commodity_cache(self, tmp_path: Path) -> None:
        """Test caching multiple commodity types."""
        client = CommoditiesClient(cache_dir=tmp_path)

        # Save coal prices
        coal_prices = [
            CoalPrice(date=date(2024, 1, 1), price=120.0),
            CoalPrice(date=date(2024, 2, 1), price=125.0),
            CoalPrice(date=date(2024, 3, 1), price=118.0),
        ]
        client.save_to_cache("coal", coal_prices)

        # Save CO2 prices
        co2_prices = [
            CO2EUAPrice(date=date(2024, 1, 1), price=85.0),
            CO2EUAPrice(date=date(2024, 2, 1), price=88.0),
            CO2EUAPrice(date=date(2024, 3, 1), price=92.0),
        ]
        client.save_to_cache("co2_eua", co2_prices)

        # Load and verify
        loaded_coal = client.load_from_cache("coal")
        loaded_co2 = client.load_from_cache("co2_eua")

        assert len(loaded_coal) == 3
        assert len(loaded_co2) == 3
        assert loaded_coal[0].price == 120.0
        assert loaded_co2[2].price == 92.0
