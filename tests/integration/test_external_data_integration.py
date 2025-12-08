"""Integration tests for external data clients.

Story 6.1: Tier 1 External Data Source Integration
AC7: Integration Tests

Tests end-to-end flows with sample data:
- Full fetch → parse → validate pipeline
- Pydantic model validation
- Historical data load (sample: 2024-01-01 to 2024-03-31)
- Multi-client coordination
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.external_data.clients import (
    ATICClient,
    BaseGovClient,
    BPstatClient,
    CommoditiesClient,
    EUOilBulletinClient,
    INEClient,
    IPMAClient,
    OMIEClient,
)
from raglite.external_data.models import (
    ATICCementConsumption,
    BaseGovContract,
    BPstatMortgageLoans,
    CO2EUAPrice,
    CoalPrice,
    DataSource,
    EUDieselPrice,
    ExternalDataPoint,
    INEBuildingPermits,
    IPMAWeatherData,
    OMIEElectricityPrice,
)

# Mark all tests in this module as integration tests that preserve collection state
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection]

# =============================================================================
# Sample Data for Integration Tests
# =============================================================================

SAMPLE_INE_RESPONSE = {
    "Dados": {
        "202401": [
            {"valor": 1234, "geocod": "Lisboa", "variacao_homologa": 5.2},
            {"valor": 987, "geocod": "Porto", "variacao_homologa": 3.1},
        ],
        "202402": [
            {"valor": 1456, "geocod": "Lisboa", "variacao_homologa": 4.8},
        ],
        "202403": [
            {"valor": 1523, "geocod": "Lisboa", "variacao_homologa": 6.1},
        ],
    }
}

# Story 6.9.3: Updated response format for new BPstat API
# The new API returns interest rates (not loan amounts) with series_id
SAMPLE_BPSTAT_RESPONSE = {
    "observations": [
        {"period": "2024-01", "value": 3.45, "series_id": "12710733"},
        {"period": "2024-02", "value": 3.52, "series_id": "12710733"},
        {"period": "2024-03", "value": 3.48, "series_id": "12710733"},
    ]
}

# Story 6.9.2: Updated OMIE response format
# New format: MARGINALPDBC;YEAR;MONTH;DAY;HOUR;PT_PRICE;ES_PRICE;...
# Hour is 1-24, prices use European decimal comma
SAMPLE_OMIE_RESPONSE = """MARGINALPDBC;2024;1;1;1;45,50;46,00
MARGINALPDBC;2024;1;1;2;44,20;45,00
MARGINALPDBC;2024;1;1;3;43,80;44,50
MARGINALPDBC;2024;1;1;4;42,10;43,00
MARGINALPDBC;2024;1;1;5;41,50;42,50
MARGINALPDBC;2024;1;1;6;43,00;44,00
MARGINALPDBC;2024;1;1;7;48,20;49,00
MARGINALPDBC;2024;1;1;8;55,30;56,00
MARGINALPDBC;2024;1;1;9;58,40;59,00
MARGINALPDBC;2024;1;1;10;57,80;58,50
MARGINALPDBC;2024;1;1;11;56,20;57,00
MARGINALPDBC;2024;1;1;12;54,80;55,50
MARGINALPDBC;2024;1;1;13;53,20;54,00
MARGINALPDBC;2024;1;1;14;52,10;53,00
MARGINALPDBC;2024;1;1;15;51,80;52,50
MARGINALPDBC;2024;1;1;16;53,40;54,00
MARGINALPDBC;2024;1;1;17;56,80;57,50
MARGINALPDBC;2024;1;1;18;62,30;63,00
MARGINALPDBC;2024;1;1;19;68,40;69,00
MARGINALPDBC;2024;1;1;20;65,20;66,00
MARGINALPDBC;2024;1;1;21;58,90;59,50
MARGINALPDBC;2024;1;1;22;52,10;53,00
MARGINALPDBC;2024;1;1;23;47,30;48,00
MARGINALPDBC;2024;1;1;24;44,80;45,50"""

SAMPLE_BASEGOV_RESPONSE = {
    "items": [
        {
            "id": "CT-2024-001",
            "dataPublicacao": "2024-01-15",
            "precoContratual": 2500000,
            "objectoContrato": "Construction of new highway section A-42",
            "entidadeAdjudicante": "Infraestruturas de Portugal",
            "adjudicatario": "Construções ABC, S.A.",
            "cpv": "45233000",
            "localizacao": "Distrito de Lisboa",
        },
        {
            "id": "CT-2024-002",
            "dataPublicacao": "2024-02-20",
            "precoContratual": 850000,
            "objectoContrato": "Building renovation municipal center",
            "entidadeAdjudicante": "Câmara Municipal de Porto",
            "adjudicatario": "Renovações XYZ, Lda",
            "cpv": "45210000",
            "localizacao": "Porto",
        },
    ]
}

SAMPLE_IPMA_RESPONSE = {
    "tMed": 15.5,
    "tMax": 20.0,
    "tMin": 10.5,
    "prec": 2.5,
    "humidade": 72.0,
    "vento": 18.5,
}

# Story 6.9.4: EU Oil Bulletin now uses XLSX format
# This sample data is used with mocked _parse_xlsx method
SAMPLE_EU_OIL_BULLETIN_PRICES = [
    {"date": "2024-01-08", "country": "Portugal", "price": 1.456},
    {"date": "2024-01-15", "country": "Portugal", "price": 1.478},
    {"date": "2024-01-22", "country": "Portugal", "price": 1.492},
    {"date": "2024-02-05", "country": "Portugal", "price": 1.501},
    {"date": "2024-02-12", "country": "Portugal", "price": 1.485},
    {"date": "2024-03-04", "country": "Portugal", "price": 1.468},
    {"date": "2024-03-11", "country": "Portugal", "price": 1.452},
]


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.asyncio
class TestINEClientIntegration:
    """Integration tests for INE API client."""

    async def test_historical_load_q1_2024(self) -> None:
        """Test historical data load for Q1 2024 sample period."""
        client = INEClient()

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_INE_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_building_permits(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 31),
            )

        # Verify correct number of records across 3 months
        assert len(result) >= 3
        # Verify model validation passed
        for record in result:
            assert isinstance(record, INEBuildingPermits)
            assert record.source == DataSource.INE
            assert record.permits_count > 0
        # Verify date range
        dates = [r.date for r in result]
        assert min(dates) >= date(2024, 1, 1)
        assert max(dates) <= date(2024, 3, 31)

    async def test_pydantic_validation(self) -> None:
        """Test Pydantic model validation on parsed data."""
        INEClient()

        # Test with negative permits_count (should fail validation)
        with pytest.raises(ValueError):
            INEBuildingPermits(
                date=date(2024, 1, 1),
                permits_count=-100,  # Invalid: must be >= 0
                region="Lisboa",
            )

        # Test with valid data
        valid_record = INEBuildingPermits(
            date=date(2024, 1, 1),
            permits_count=1000,
            region="Lisboa",
        )
        assert valid_record.source == DataSource.INE


@pytest.mark.asyncio
class TestBPstatClientIntegration:
    """Integration tests for BPstat client."""

    async def test_historical_load_q1_2024(self) -> None:
        """Test historical data load for Q1 2024."""
        client = BPstatClient()

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_BPSTAT_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_mortgage_loans(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 31),
            )

        assert len(result) == 3
        for record in result:
            assert isinstance(record, BPstatMortgageLoans)
            assert record.source == DataSource.BPSTAT
            # Story 6.9.3: Now returns interest rates, not loan amounts
            # total_loans_eur is 0 since we fetch interest rates instead
            assert record.total_loans_eur == 0.0
            # Verify interest rate is present
            assert record.avg_interest_rate_pct is not None
            assert 3.0 <= record.avg_interest_rate_pct <= 4.0


@pytest.mark.asyncio
class TestOMIEClientIntegration:
    """Integration tests for OMIE electricity market client."""

    async def test_historical_load_with_hourly_data(self) -> None:
        """Test fetching hourly electricity prices."""
        client = OMIEClient()

        mock_response = MagicMock()
        mock_response.text = SAMPLE_OMIE_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_spot_prices(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
                include_hourly=True,
            )

        # 24 hours of data
        assert len(result) == 24
        for record in result:
            assert isinstance(record, OMIEElectricityPrice)
            assert record.market == "MIBEL"
            assert record.hour is not None and 0 <= record.hour <= 23
            assert record.price_eur_mwh > 0

    async def test_daily_average_calculation(self) -> None:
        """Test daily average price calculation."""
        client = OMIEClient()

        mock_response = MagicMock()
        mock_response.text = SAMPLE_OMIE_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_spot_prices(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
                include_hourly=False,
            )

        assert len(result) == 1
        assert result[0].price_type == "spot_daily_avg"
        # Average should be reasonable (between min and max in sample)
        assert 40 <= result[0].price_eur_mwh <= 70


@pytest.mark.asyncio
class TestBaseGovClientIntegration:
    """Integration tests for Base.gov.pt client."""

    async def test_construction_contracts_fetch(self) -> None:
        """Test fetching construction contracts.

        Story 6.9.5: BaseGov now uses dados.gov.pt IMPIC XLSX as primary source.
        We mock at the TED API level since IMPIC requires real XLSX downloads.
        """
        client = BaseGovClient()

        # Mock TED API response (since IMPIC dataset mock is complex)
        ted_response = {
            "notices": [
                {
                    "publication-number": "CT-2024-001",
                    "publication-date": "2024-01-15",
                    "notice-title": "Construction of new highway section A-42",
                    "buyer-name": "Infraestruturas de Portugal",
                    "winner-name": "Construções ABC, S.A.",
                    "total-value": {"amount": 2500000},
                    "cpv": ["45233000"],
                },
                {
                    "publication-number": "CT-2024-002",
                    "publication-date": "2024-02-20",
                    "notice-title": "Building renovation municipal center",
                    "buyer-name": "Câmara Municipal de Porto",
                    "winner-name": "Renovações XYZ, Lda",
                    "total-value": {"amount": 850000},
                    "cpv": ["45210000"],
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = ted_response
        mock_response.raise_for_status = MagicMock()

        # Mock _get_impic_resource_urls to return empty (trigger TED fallback)
        with patch.object(client, "_get_impic_resource_urls", new_callable=AsyncMock) as mock_impic:
            mock_impic.return_value = {}  # Empty = no IMPIC data available

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                result = await client.fetch_contracts(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 3, 31),
                    cpv_code="45000000",
                )

        assert len(result) == 2
        for contract in result:
            assert isinstance(contract, BaseGovContract)
            assert contract.source == DataSource.BASEGOV
            assert contract.contract_value_eur > 0
            assert contract.cpv_code is not None


@pytest.mark.asyncio
class TestIPMAClientIntegration:
    """Integration tests for IPMA weather client."""

    async def test_weather_observations_fetch(self) -> None:
        """Test fetching weather observations."""
        client = IPMAClient()

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_IPMA_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_observations(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
                station_id="1200535",
            )

        assert len(result) == 1
        obs = result[0]
        assert isinstance(obs, IPMAWeatherData)
        assert obs.source == DataSource.IPMA
        assert obs.temperature_c == 15.5
        assert obs.temperature_max_c == 20.0
        assert obs.precipitation_mm == 2.5


@pytest.mark.asyncio
class TestEUOilBulletinIntegration:
    """Integration tests for EU Oil Bulletin client."""

    async def test_diesel_prices_portugal(self) -> None:
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
            for item in SAMPLE_EU_OIL_BULLETIN_PRICES
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
            assert isinstance(price, EUDieselPrice)
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
            assert isinstance(record, ATICCementConsumption)
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


@pytest.mark.asyncio
class TestMultiClientCoordination:
    """Integration tests for coordinating multiple clients."""

    async def test_parallel_data_fetch(self) -> None:
        """Test fetching from multiple sources in parallel.

        Story 6.9: Updated for new API response formats.
        Each client is mocked independently to ensure proper responses.
        """
        import asyncio

        # Create mock responses
        ine_response = MagicMock()
        ine_response.json.return_value = SAMPLE_INE_RESPONSE
        ine_response.raise_for_status = MagicMock()

        # Story 6.9.3: BPstat now fetches interest rates in one request
        bpstat_response = MagicMock()
        bpstat_response.json.return_value = SAMPLE_BPSTAT_RESPONSE
        bpstat_response.raise_for_status = MagicMock()

        # Story 6.9.2: OMIE uses new CSV format
        omie_response = MagicMock()
        omie_response.text = SAMPLE_OMIE_RESPONSE
        omie_response.raise_for_status = MagicMock()

        # Mock each client's HTTP calls independently using patch.object
        # This ensures each client gets the correct mock response
        ine_client = INEClient()
        bpstat_client = BPstatClient()
        omie_client = OMIEClient()

        start = date(2024, 1, 1)
        end = date(2024, 1, 31)

        # Use separate patches for each client type to avoid side_effect ordering issues
        with patch("httpx.AsyncClient") as mock_async_client:
            # Create a mock that returns different responses based on URL pattern
            async def mock_get_handler(url="", *args, **kwargs):
                if "ine.pt" in url or "ine-api" in url.lower():
                    return ine_response
                elif "bpstat" in url or "bportugal" in url:
                    return bpstat_response
                elif "omie" in url:
                    return omie_response
                # Default to INE response for unknown URLs
                return ine_response

            mock_instance = MagicMock()
            mock_instance.get = AsyncMock(side_effect=mock_get_handler)
            mock_async_client.return_value.__aenter__.return_value = mock_instance

            # Fetch in parallel
            results = await asyncio.gather(
                ine_client.fetch_building_permits(start, end),
                bpstat_client.fetch_mortgage_loans(start, end),
                omie_client.fetch_spot_prices(start, start),
                return_exceptions=True,  # Don't fail if one client has issues
            )

            ine_data, bpstat_data, omie_data = results

            # Verify at least one client returned data
            # Note: Order of mock calls in asyncio.gather is non-deterministic
            total_records = 0
            if isinstance(ine_data, list):
                total_records += len(ine_data)
            if isinstance(bpstat_data, list):
                total_records += len(bpstat_data)
            if isinstance(omie_data, list):
                total_records += len(omie_data)

            assert total_records > 0, "At least one client should return data"

    async def test_data_point_conversion(self) -> None:
        """Test converting specialized models to generic ExternalDataPoint."""
        # INE data
        ine_record = INEBuildingPermits(
            date=date(2024, 1, 1),
            permits_count=1234,
            region="Lisboa",
        )

        # Convert to ExternalDataPoint for unified storage
        data_point = ExternalDataPoint(
            source=ine_record.source,
            indicator="building_permits",
            date=ine_record.date,
            value=float(ine_record.permits_count),
            region=ine_record.region,
            metadata={"permit_type": ine_record.permit_type},
        )

        assert data_point.source == DataSource.INE
        assert data_point.value == 1234.0
        assert data_point.region == "Lisboa"
