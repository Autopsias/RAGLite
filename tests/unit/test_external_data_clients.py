"""Unit tests for external data clients.

Story 6.1: Tier 1 External Data Source Integration
AC6: Unit Tests (80%+ coverage)

Tests scenarios:
- Success responses
- Timeout handling and retry
- Invalid response handling
- Server error (5xx) handling
- Client error (4xx) handling
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from raglite.external_data.clients.atic import ATICClient
from raglite.external_data.clients.basegov import BaseGovClient
from raglite.external_data.clients.bpstat import BPstatClient
from raglite.external_data.clients.commodities import CommoditiesClient
from raglite.external_data.clients.eu_oil_bulletin import EUOilBulletinClient
from raglite.external_data.clients.ine import INEClient
from raglite.external_data.clients.ipma import IPMAClient
from raglite.external_data.clients.omie import OMIEClient
from raglite.external_data.exceptions import (
    ExternalDataFetchError,
    ExternalDataValidationError,
)
from raglite.external_data.models import (
    ATICCementConsumption,
    BaseGovContract,
    BPstatMortgageLoans,
    EUDieselPrice,
    INEBuildingPermits,
    INEConstructionCostIndex,
    INEConstructionOutput,
    IPMAWeatherData,
    OMIEElectricityPrice,
)

# =============================================================================
# INE Client Tests
# =============================================================================


class TestINEClient:
    """Tests for INE API client."""

    @pytest.fixture
    def client(self) -> INEClient:
        """Create INE client instance."""
        return INEClient()

    @pytest.mark.asyncio
    async def test_fetch_building_permits_success(self, client: INEClient) -> None:
        """Test successful building permits fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Dados": {
                "202401": [{"valor": 1234, "geocod": "Lisboa"}],
                "202402": [{"valor": 1456, "geocod": "Porto"}],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_building_permits(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 2, 28),
            )

            assert len(result) == 2
            assert isinstance(result[0], INEBuildingPermits)
            assert result[0].permits_count == 1234
            assert result[0].region == "Lisboa"

    @pytest.mark.asyncio
    async def test_fetch_building_permits_timeout_retry(self, client: INEClient) -> None:
        """Test retry logic on timeout."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"Dados": {"202401": [{"valor": 100}]}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            # First two calls timeout, third succeeds
            mock_get = AsyncMock(
                side_effect=[
                    httpx.TimeoutException("timeout"),
                    httpx.TimeoutException("timeout"),
                    mock_response,
                ]
            )
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.fetch_building_permits(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )

            assert len(result) == 1
            assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_building_permits_timeout_exhausted(self, client: INEClient) -> None:
        """Test exception when all retries exhausted."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("timeout")
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ExternalDataFetchError) as exc_info:
                    await client.fetch_building_permits(
                        start_date=date(2024, 1, 1),
                        end_date=date(2024, 1, 31),
                    )

            assert exc_info.value.source == "INE"
            assert "Timeout" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_fetch_construction_output_success(self, client: INEClient) -> None:
        """Test successful construction output fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Dados": {
                "202401": [{"valor": 105.5, "variacao_homologa": 2.3}],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_construction_output(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

            assert len(result) == 1
            assert isinstance(result[0], INEConstructionOutput)
            assert result[0].index_value == 105.5
            assert result[0].yoy_change_pct == 2.3

    @pytest.mark.asyncio
    async def test_fetch_construction_cost_index_success(self, client: INEClient) -> None:
        """Test successful construction cost index fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Dados": {
                "202401": [{"valor": 110.2, "materiais": 112.5, "mao_obra": 108.1}],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_construction_cost_index(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

            assert len(result) == 1
            assert isinstance(result[0], INEConstructionCostIndex)
            assert result[0].total_index == 110.2
            assert result[0].materials_index == 112.5
            assert result[0].labor_index == 108.1


# =============================================================================
# ATIC Client Tests
# =============================================================================


class TestATICClient:
    """Tests for ATIC cement consumption client."""

    @pytest.fixture
    def client(self) -> ATICClient:
        """Create ATIC client instance."""
        return ATICClient()

    def test_parse_csv_content_success(self, client: ATICClient) -> None:
        """Test successful CSV parsing."""
        csv_content = """date,consumption,region,type
2024-01-01,150000,Portugal,gray
2024-02-01,160000,Portugal,gray
2024-03-01,170000,Lisboa,white"""

        result = client.parse_csv_content(csv_content)

        assert len(result) == 3
        assert isinstance(result[0], ATICCementConsumption)
        assert result[0].consumption_tonnes == 150000
        assert result[0].region == "Portugal"
        assert result[2].region == "Lisboa"
        assert result[2].cement_type == "white"

    def test_parse_csv_content_alternate_columns(self, client: ATICClient) -> None:
        """Test CSV with alternate column names."""
        csv_content = """Data,Consumo,Regiao
2024-01-01,150000,Norte
2024-02-01,160000,Sul"""

        result = client.parse_csv_content(csv_content)

        assert len(result) == 2
        assert result[0].consumption_tonnes == 150000
        assert result[0].region == "Norte"

    def test_parse_csv_content_no_headers(self, client: ATICClient) -> None:
        """Test CSV validation error on missing headers."""
        csv_content = ""

        with pytest.raises(ExternalDataValidationError) as exc_info:
            client.parse_csv_content(csv_content)

        assert exc_info.value.source == "ATIC"
        assert "headers" in exc_info.value.message.lower()

    def test_parse_csv_content_missing_date_column(self, client: ATICClient) -> None:
        """Test validation error on missing date column."""
        csv_content = """value,region
150000,Portugal"""

        with pytest.raises(ExternalDataValidationError) as exc_info:
            client.parse_csv_content(csv_content)

        assert "date column" in exc_info.value.message.lower()

    def test_parse_csv_content_missing_value_column(self, client: ATICClient) -> None:
        """Test validation error on missing value column."""
        csv_content = """date,region
2024-01-01,Portugal"""

        with pytest.raises(ExternalDataValidationError) as exc_info:
            client.parse_csv_content(csv_content)

        assert "value" in exc_info.value.message.lower()

    def test_parse_csv_file_not_found(self, client: ATICClient) -> None:
        """Test error on missing file."""
        with pytest.raises(ExternalDataFetchError) as exc_info:
            client.parse_csv_file("/nonexistent/path.csv")

        assert exc_info.value.source == "ATIC"
        assert "not found" in exc_info.value.message.lower()

    def test_parse_date_formats(self, client: ATICClient) -> None:
        """Test parsing various date formats."""
        # Test different date formats
        assert client._parse_date("2024-01-15") == date(2024, 1, 15)
        assert client._parse_date("15/01/2024") == date(2024, 1, 15)
        assert client._parse_date("2024-01") == date(2024, 1, 1)
        assert client._parse_date("01/2024") == date(2024, 1, 1)
        assert client._parse_date("202401") == date(2024, 1, 1)
        assert client._parse_date("invalid") is None


# =============================================================================
# BPstat Client Tests
# =============================================================================


class TestBPstatClient:
    """Tests for BPstat (Banco de Portugal) client."""

    @pytest.fixture
    def client(self) -> BPstatClient:
        """Create BPstat client instance."""
        return BPstatClient()

    @pytest.mark.asyncio
    async def test_fetch_mortgage_loans_success(self, client: BPstatClient) -> None:
        """Test successful mortgage loans fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "observations": [
                {"period": "2024-01", "value": 100000},
                {"period": "2024-02", "value": 105000},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_mortgage_loans(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 2, 28),
            )

            assert len(result) == 2
            assert isinstance(result[0], BPstatMortgageLoans)
            # BPstat reports in millions
            assert result[0].total_loans_eur == 100000 * 1_000_000

    @pytest.mark.asyncio
    async def test_fetch_mortgage_loans_server_error_retry(self, client: BPstatClient) -> None:
        """Test retry on server error (500)."""
        error_response = MagicMock()
        error_response.status_code = 500
        error = httpx.HTTPStatusError("Server Error", request=MagicMock(), response=error_response)

        success_response = MagicMock()
        success_response.json.return_value = {"observations": [{"period": "2024-01", "value": 100}]}
        success_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            # BPstat client fetches 3 series: total loans, new loans, rates
            # First series: 2 errors then success (3 calls)
            # Second and third series: just return success
            mock_get = AsyncMock(
                side_effect=[
                    # First series (total loans): retry twice then succeed
                    error,
                    error,
                    success_response,
                    # Second series (new loans): immediate success
                    success_response,
                    # Third series (rates): immediate success
                    success_response,
                ]
            )
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.fetch_mortgage_loans(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )

            assert len(result) == 1
            # 3 retries for first series + 1 for each of the other 2 series = 5 calls
            assert mock_get.call_count == 5


# =============================================================================
# OMIE Client Tests
# =============================================================================


class TestOMIEClient:
    """Tests for OMIE electricity market client."""

    @pytest.fixture
    def client(self) -> OMIEClient:
        """Create OMIE client instance."""
        return OMIEClient()

    @pytest.mark.asyncio
    async def test_fetch_spot_prices_success(self, client: OMIEClient) -> None:
        """Test successful spot prices fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """Hour;Portugal;Spain
1;45.50;46.00
2;44.20;45.00
24;50.10;51.00"""
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

            assert len(result) == 3
            assert isinstance(result[0], OMIEElectricityPrice)
            assert result[0].price_eur_mwh == 45.50
            assert result[0].hour == 0  # OMIE uses 1-24, we convert to 0-23

    @pytest.mark.asyncio
    async def test_fetch_spot_prices_daily_average(self, client: OMIEClient) -> None:
        """Test daily average price calculation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """Hour;Portugal;Spain
1;40.00;41.00
2;50.00;51.00"""
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
            assert result[0].price_eur_mwh == 45.00  # Average of 40 and 50
            assert result[0].price_type == "spot_daily_avg"

    @pytest.mark.asyncio
    async def test_fetch_spot_prices_404_handled(self, client: OMIEClient) -> None:
        """Test 404 (no data) is handled gracefully."""
        error_response = MagicMock()
        error_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found", request=MagicMock(), response=error_response
                )
            )

            result = await client.fetch_spot_prices(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
            )

            # 404 should return empty list, not raise
            assert result == []

    def test_parse_daily_file(self, client: OMIEClient) -> None:
        """Test parsing OMIE daily file."""
        content = """Hour;Portugal;Spain
1;45.50;46.00
2;44,20;45,00
3;invalid;bad"""

        result = client._parse_daily_file(content, date(2024, 1, 1))

        # Should parse 2 valid rows (comma decimal separator handled)
        assert len(result) == 2
        assert result[0].hour == 0
        assert result[0].price_eur_mwh == 45.50
        assert result[1].hour == 1
        assert result[1].price_eur_mwh == 44.20


# =============================================================================
# EU Oil Bulletin Client Tests
# =============================================================================


class TestEUOilBulletinClient:
    """Tests for EU Oil Bulletin client."""

    @pytest.fixture
    def client(self) -> EUOilBulletinClient:
        """Create EU Oil Bulletin client instance."""
        return EUOilBulletinClient()

    @pytest.mark.asyncio
    async def test_fetch_diesel_prices_success(self, client: EUOilBulletinClient) -> None:
        """Test successful diesel prices fetch."""
        mock_response = MagicMock()
        # XML must have a root element for ElementTree parsing
        mock_response.text = """<?xml version="1.0"?>
        <OilBulletin>
            <OilPrice date="2024-01-08" country="PT" diesel="1.456"/>
            <OilPrice date="2024-01-15" country="PT" diesel="1.478"/>
            <OilPrice date="2024-01-08" country="ES" diesel="1.423"/>
        </OilBulletin>
        """
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_diesel_prices(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                country="Portugal",
            )

            # Only Portugal (PT) results
            assert len(result) == 2
            assert isinstance(result[0], EUDieselPrice)
            assert result[0].price_eur_litre == 1.456
            assert result[0].country == "Portugal"

    def test_country_code_conversion(self, client: EUOilBulletinClient) -> None:
        """Test country code to name conversion."""
        assert client._code_to_country("PT") == "Portugal"
        assert client._code_to_country("ES") == "Spain"
        assert client._code_to_country("XX") == "XX"  # Unknown code returns as-is


# =============================================================================
# IPMA Client Tests
# =============================================================================


class TestIPMAClient:
    """Tests for IPMA weather client."""

    @pytest.fixture
    def client(self) -> IPMAClient:
        """Create IPMA client instance."""
        return IPMAClient()

    @pytest.mark.asyncio
    async def test_fetch_observations_success(self, client: IPMAClient) -> None:
        """Test successful weather observations fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tMed": 15.5,
            "tMax": 20.0,
            "tMin": 10.0,
            "prec": 2.5,
            "humidade": 75.0,
            "vento": 15.0,
        }
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
            assert isinstance(result[0], IPMAWeatherData)
            assert result[0].temperature_c == 15.5
            assert result[0].temperature_max_c == 20.0
            assert result[0].precipitation_mm == 2.5

    @pytest.mark.asyncio
    async def test_fetch_forecast_success(self, client: IPMAClient) -> None:
        """Test successful forecast fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"forecastDate": "2024-01-01", "tMax": 18, "tMin": 10, "precipitaProb": 20},
                {"forecastDate": "2024-01-02", "tMax": 19, "tMin": 11, "precipitaProb": 10},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_forecast(location_id="1110600", days=2)

            assert len(result) == 2
            assert result[0].temperature_max_c == 18.0

    def test_stations_dict(self, client: IPMAClient) -> None:
        """Test station ID mapping."""
        assert "Lisboa" in client.STATIONS
        assert "Porto" in client.STATIONS
        assert client.STATIONS["Lisboa"] == "1200535"


# =============================================================================
# Base.gov.pt Client Tests
# =============================================================================


class TestBaseGovClient:
    """Tests for Base.gov.pt public procurement client."""

    @pytest.fixture
    def client(self) -> BaseGovClient:
        """Create Base.gov.pt client instance."""
        return BaseGovClient()

    @pytest.mark.asyncio
    async def test_fetch_contracts_success(self, client: BaseGovClient) -> None:
        """Test successful contracts fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "12345",
                    "dataPublicacao": "2024-01-15",
                    "precoContratual": 1500000,
                    "objectoContrato": "Road construction",
                    "entidadeAdjudicante": "Câmara Municipal",
                    "adjudicatario": "Empresa ABC",
                    "cpv": "45233000",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_contracts(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

            assert len(result) == 1
            assert isinstance(result[0], BaseGovContract)
            assert result[0].contract_value_eur == 1500000
            assert result[0].contractor == "Empresa ABC"
            assert result[0].cpv_code == "45233000"

    def test_cpv_codes(self, client: BaseGovClient) -> None:
        """Test CPV code constants."""
        assert client.CPV_CONSTRUCTION == "45000000"
        assert client.CPV_BUILDING == "45210000"
        assert client.CPV_ROAD == "45233000"


# =============================================================================
# Commodities Client Tests
# =============================================================================


class TestCommoditiesClient:
    """Tests for commodities price client."""

    @pytest.fixture
    def client(self, tmp_path) -> CommoditiesClient:
        """Create commodities client with temp cache directory."""
        return CommoditiesClient(cache_dir=tmp_path / "cache")

    @pytest.mark.asyncio
    async def test_fetch_co2_prices_success(self, client: CommoditiesClient) -> None:
        """Test successful CO2 EUA prices fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"date": "2024-01-15", "price": 85.50},
                {"date": "2024-01-16", "price": 86.00},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_co2_prices(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

            assert len(result) == 2
            assert result[0].price == 85.50
            assert result[0].currency == "EUR"

    def test_save_and_load_cache(self, client: CommoditiesClient) -> None:
        """Test cache save and load operations."""
        from raglite.external_data.models import CoalPrice

        prices = [
            CoalPrice(date=date(2024, 1, 1), price=120.0, currency="EUR"),
            CoalPrice(date=date(2024, 1, 8), price=122.0, currency="EUR"),
        ]

        client.save_to_cache("coal", prices)
        loaded = client.load_from_cache("coal")

        assert len(loaded) == 2
        assert loaded[0].price == 120.0

    def test_load_cache_with_date_filter(self, client: CommoditiesClient) -> None:
        """Test cache loading with date filtering."""
        from raglite.external_data.models import CoalPrice

        prices = [
            CoalPrice(date=date(2024, 1, 1), price=120.0, currency="EUR"),
            CoalPrice(date=date(2024, 2, 1), price=122.0, currency="EUR"),
            CoalPrice(date=date(2024, 3, 1), price=124.0, currency="EUR"),
        ]

        client.save_to_cache("coal", prices)
        loaded = client.load_from_cache(
            "coal",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 2, 15),
        )

        assert len(loaded) == 1
        assert loaded[0].date == date(2024, 2, 1)

    def test_import_from_csv(self, client: CommoditiesClient, tmp_path) -> None:
        """Test CSV import."""
        csv_file = tmp_path / "coal_prices.csv"
        csv_file.write_text(
            """date,price,currency,unit,grade
2024-01-01,120.0,EUR,EUR/tonne,thermal
2024-01-08,122.0,EUR,EUR/tonne,thermal"""
        )

        result = client.import_from_csv("coal", csv_file)

        assert len(result) == 2
        assert result[0].price == 120.0
        assert result[0].grade == "thermal"

    def test_load_cache_empty(self, client: CommoditiesClient) -> None:
        """Test loading from non-existent cache returns empty list."""
        result = client.load_from_cache("nonexistent")
        assert result == []


# =============================================================================
# Exception Tests
# =============================================================================


# =============================================================================
# Additional Coverage Tests
# =============================================================================


class TestINEClientAdditional:
    """Additional tests for INE client coverage."""

    @pytest.fixture
    def client(self) -> INEClient:
        return INEClient()

    @pytest.mark.asyncio
    async def test_http_client_error(self, client: INEClient) -> None:
        """Test handling of 4xx client errors (no retry)."""
        error_response = MagicMock()
        error_response.status_code = 400
        error = httpx.HTTPStatusError("Bad Request", request=MagicMock(), response=error_response)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=error)

            with pytest.raises(ExternalDataFetchError) as exc_info:
                await client.fetch_building_permits(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )

            assert "HTTP 400" in exc_info.value.message

    def test_parse_building_permits_malformed_period(self, client: INEClient) -> None:
        """Test handling of malformed period data."""
        data = {"Dados": {"invalid": [{"valor": 100}]}}
        result = client._parse_building_permits(data)
        # Should handle gracefully and return empty
        assert result == []

    def test_parse_building_permits_missing_value(self, client: INEClient) -> None:
        """Test handling of missing value."""
        data = {"Dados": {"202401": [{"geocod": "Lisboa"}]}}
        result = client._parse_building_permits(data)
        assert result == []


class TestBPstatClientAdditional:
    """Additional tests for BPstat client coverage."""

    @pytest.fixture
    def client(self) -> BPstatClient:
        return BPstatClient()

    @pytest.mark.asyncio
    async def test_http_client_error_no_retry(self, client: BPstatClient) -> None:
        """Test 4xx errors don't trigger retry."""
        error_response = MagicMock()
        error_response.status_code = 401
        error = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=error_response)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=error)

            with pytest.raises(ExternalDataFetchError) as exc_info:
                await client.fetch_mortgage_loans(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )

            assert "HTTP 401" in exc_info.value.message

    def test_merge_loan_data_empty(self, client: BPstatClient) -> None:
        """Test merging when some series are empty."""
        total = {"observations": [{"period": "2024-01", "value": 100}]}
        new_loans = {"observations": []}
        rates = {"observations": []}

        result = client._merge_loan_data(total, new_loans, rates)

        assert len(result) == 1
        assert result[0].new_loans_eur is None
        assert result[0].avg_interest_rate_pct is None


class TestOMIEClientAdditional:
    """Additional tests for OMIE client coverage."""

    @pytest.fixture
    def client(self) -> OMIEClient:
        return OMIEClient()

    @pytest.mark.asyncio
    async def test_server_error_retry_then_fail(self, client: OMIEClient) -> None:
        """Test retry exhaustion on server errors."""
        error_response = MagicMock()
        error_response.status_code = 503

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Service Unavailable", request=MagicMock(), response=error_response
                )
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                # Should fail after retries but not raise (404 handling)
                result = await client.fetch_spot_prices(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 1),
                )
                # Non-404 errors are caught and logged, returns empty
                assert result == []

    @pytest.mark.asyncio
    async def test_monthly_average(self, client: OMIEClient) -> None:
        """Test monthly average calculation."""
        mock_response = MagicMock()
        mock_response.text = """Hour;Portugal;Spain
1;50.00;51.00
2;60.00;61.00"""
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_monthly_average(2024, 1)

        assert result is not None
        assert result.price_type == "monthly_avg"


class TestIPMAClientAdditional:
    """Additional tests for IPMA client coverage."""

    @pytest.fixture
    def client(self) -> IPMAClient:
        return IPMAClient()

    @pytest.mark.asyncio
    async def test_fetch_all_stations(self, client: IPMAClient) -> None:
        """Test fetching from all weather stations."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"tMed": 15.0}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_all_stations(date(2024, 1, 1))

        # Should fetch from multiple stations
        assert len(result) >= 1

    def test_parse_forecast_day_missing_fields(self, client: IPMAClient) -> None:
        """Test parsing forecast with missing optional fields."""
        data = {"forecastDate": "2024-01-01"}  # Missing temperature fields

        result = client._parse_forecast_day(data, "1110600")

        assert result is not None
        assert result.temperature_max_c is None


class TestBaseGovClientAdditional:
    """Additional tests for Base.gov.pt client coverage."""

    @pytest.fixture
    def client(self) -> BaseGovClient:
        return BaseGovClient()

    @pytest.mark.asyncio
    async def test_fetch_construction_summary(self, client: BaseGovClient) -> None:
        """Test construction contracts summary calculation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {"id": "1", "dataPublicacao": "2024-01-15", "precoContratual": 1000000},
                {"id": "2", "dataPublicacao": "2024-01-20", "precoContratual": 2000000},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_construction_contracts_summary(2024, 1)

        assert result["total_contracts"] == 2
        assert result["total_value_eur"] == 3000000
        assert result["avg_value_eur"] == 1500000


class TestATICClientAdditional:
    """Additional tests for ATIC client coverage."""

    @pytest.fixture
    def client(self) -> ATICClient:
        return ATICClient()

    @pytest.mark.asyncio
    async def test_fetch_historical_no_csv(self, client: ATICClient) -> None:
        """Test historical fetch without CSV returns empty with warning."""
        result = await client.fetch_historical_data(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            csv_path=None,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_historical_with_csv(self, client: ATICClient, tmp_path) -> None:
        """Test historical fetch with CSV and date filtering."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            """date,consumption,region
2024-01-01,100000,Portugal
2024-02-01,110000,Portugal
2024-06-01,120000,Portugal"""
        )

        result = await client.fetch_historical_data(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            csv_path=csv_file,
        )

        # Only 2 records in date range
        assert len(result) == 2


class TestCommoditiesClientAdditional:
    """Additional tests for commodities client coverage."""

    @pytest.fixture
    def client(self, tmp_path) -> CommoditiesClient:
        return CommoditiesClient(cache_dir=tmp_path / "cache")

    @pytest.mark.asyncio
    async def test_fetch_coal_falls_back_to_cache(self, client: CommoditiesClient) -> None:
        """Test coal prices fallback to cache (no API)."""
        result = await client.fetch_coal_prices(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )
        # No cache exists, returns empty
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_petcoke_falls_back_to_cache(self, client: CommoditiesClient) -> None:
        """Test petcoke prices fallback to cache (no API)."""
        result = await client.fetch_petcoke_prices(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_co2_api_failure_fallback(self, client: CommoditiesClient) -> None:
        """Test CO2 prices fallback on API failure."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("timeout")
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.fetch_co2_prices(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 3, 31),
                )

        # Falls back to empty cache
        assert result == []

    def test_import_csv_file_not_found(self, client: CommoditiesClient) -> None:
        """Test CSV import with non-existent file."""
        with pytest.raises(ExternalDataFetchError):
            client.import_from_csv("coal", "/nonexistent/path.csv")


class TestExceptions:
    """Tests for external data exception classes."""

    def test_external_data_fetch_error(self) -> None:
        """Test ExternalDataFetchError formatting."""
        original = ValueError("Connection refused")
        error = ExternalDataFetchError(
            source="INE",
            message="Failed to connect",
            original_error=original,
        )

        assert error.source == "INE"
        assert error.message == "Failed to connect"
        assert error.original_error is original
        assert "[INE] Failed to connect" in str(error)

    def test_external_data_validation_error(self) -> None:
        """Test ExternalDataValidationError formatting."""
        error = ExternalDataValidationError(
            source="ATIC",
            message="Missing date column",
        )

        assert error.source == "ATIC"
        assert "Validation failed" in str(error)

    def test_external_data_stale_error(self) -> None:
        """Test ExternalDataStaleError formatting."""
        from raglite.external_data.exceptions import ExternalDataStaleError

        error = ExternalDataStaleError(
            source="OMIE",
            days_stale=45,
            max_days=30,
        )

        assert error.source == "OMIE"
        assert error.days_stale == 45
        assert error.max_days == 30
        assert "45 days old" in str(error)


# =============================================================================
# Rate Limit (429) Handling Tests
# =============================================================================


class TestRateLimitHandling:
    """Tests for rate limit (429) handling across clients."""

    @pytest.mark.asyncio
    async def test_ine_rate_limit_retry(self) -> None:
        """Test INE client retries on 429 rate limit."""
        client = INEClient()

        # Create 429 error response
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_error = httpx.HTTPStatusError(
            "Too Many Requests", request=MagicMock(), response=rate_limit_response
        )

        success_response = MagicMock()
        success_response.json.return_value = {"Dados": {"202401": [{"valor": 100}]}}
        success_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            # First call returns 429, second succeeds
            mock_get = AsyncMock(side_effect=[rate_limit_error, success_response])
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.fetch_building_permits(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )

            assert len(result) == 1
            assert mock_get.call_count == 2  # Retried after 429

    @pytest.mark.asyncio
    async def test_bpstat_rate_limit_retry(self) -> None:
        """Test BPstat client retries on 429 rate limit."""
        client = BPstatClient()

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_error = httpx.HTTPStatusError(
            "Too Many Requests", request=MagicMock(), response=rate_limit_response
        )

        success_response = MagicMock()
        success_response.json.return_value = {"observations": [{"period": "2024-01", "value": 100}]}
        success_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            # Each series gets retried: 429 then success
            mock_get = AsyncMock(
                side_effect=[
                    rate_limit_error,
                    success_response,  # Total loans
                    success_response,  # New loans
                    success_response,  # Rates
                ]
            )
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.fetch_mortgage_loans(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )

            assert len(result) == 1


# =============================================================================
# Additional Coverage Tests for eu_oil_bulletin.py
# =============================================================================


class TestEUOilBulletinAdditional:
    """Additional tests for EU Oil Bulletin coverage."""

    @pytest.fixture
    def client(self) -> EUOilBulletinClient:
        return EUOilBulletinClient()

    def test_parse_bulletin_xml_invalid_xml(self, client: EUOilBulletinClient) -> None:
        """Test handling of invalid XML content."""
        invalid_xml = "not valid xml <unclosed"
        result = client._parse_bulletin_xml(invalid_xml, "PT", date(2024, 1, 1), date(2024, 1, 31))
        assert result == []

    def test_parse_bulletin_xml_missing_attributes(self, client: EUOilBulletinClient) -> None:
        """Test handling of XML with missing attributes."""
        xml_content = """<?xml version="1.0"?>
        <OilBulletin>
            <OilPrice date="2024-01-08" country="PT"/>
            <OilPrice country="PT" diesel="1.456"/>
            <OilPrice date="2024-01-08" diesel="1.456"/>
        </OilBulletin>
        """
        result = client._parse_bulletin_xml(xml_content, "PT", date(2024, 1, 1), date(2024, 1, 31))
        # All three records are missing required attributes
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_weekly_prices(self, client: EUOilBulletinClient) -> None:
        """Test fetching weekly prices."""
        mock_response = MagicMock()
        mock_response.text = """<?xml version="1.0"?>
        <OilBulletin>
            <OilPrice date="2024-01-08" country="PT" diesel="1.456"/>
        </OilBulletin>
        """
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_weekly_prices(
                week_date=date(2024, 1, 10),  # Wednesday of week containing 2024-01-08
                country="Portugal",
            )

        assert result is not None
        assert result.price_eur_litre == 1.456

    @pytest.mark.asyncio
    async def test_fetch_weekly_prices_not_found(self, client: EUOilBulletinClient) -> None:
        """Test fetching weekly prices when no data available."""
        mock_response = MagicMock()
        mock_response.text = """<?xml version="1.0"?>
        <OilBulletin></OilBulletin>
        """
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_weekly_prices(
                week_date=date(2024, 6, 15),
                country="Portugal",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_bulletin_timeout_retry(self, client: EUOilBulletinClient) -> None:
        """Test timeout retry logic."""
        success_response = MagicMock()
        success_response.text = """<?xml version="1.0"?><OilBulletin></OilBulletin>"""
        success_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(
                side_effect=[
                    httpx.TimeoutException("timeout"),
                    success_response,
                ]
            )
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.fetch_diesel_prices(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )

            assert mock_get.call_count == 2


# =============================================================================
# Additional Coverage Tests for ipma.py
# =============================================================================


class TestIPMAClientCoverage:
    """Additional tests for IPMA client coverage."""

    @pytest.fixture
    def client(self) -> IPMAClient:
        return IPMAClient()

    @pytest.mark.asyncio
    async def test_fetch_observations_no_data(self, client: IPMAClient) -> None:
        """Test handling of empty observation response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # Empty response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_observations(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
            )

        # No valid observation data
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_fetch_observations_fetch_error(self, client: IPMAClient) -> None:
        """Test handling of fetch error during observations."""
        error_response = MagicMock()
        error_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found", request=MagicMock(), response=error_response
                )
            )

            # Should not raise - fetch errors are caught and result is empty
            result = await client.fetch_observations(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_forecast_parse_error(self, client: IPMAClient) -> None:
        """Test handling of parse error in forecast."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"forecastDate": "invalid-date"},  # Will fail to parse
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_forecast(location_id="1110600", days=1)

        # Invalid date causes parse failure, result is empty
        assert result == []

    def test_parse_observation_exception(self, client: IPMAClient) -> None:
        """Test parse observation with malformed data."""
        # Data that causes exception during parsing
        data = {"tMed": "not-a-number"}  # Will fail float conversion
        result = client._parse_observation(data, date(2024, 1, 1), "1200535")
        # Should return None on exception
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_observations_timeout_retry(self, client: IPMAClient) -> None:
        """Test timeout retry logic."""
        success_response = MagicMock()
        success_response.json.return_value = {"tMed": 15.0}
        success_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(
                side_effect=[
                    httpx.TimeoutException("timeout"),
                    success_response,
                ]
            )
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.fetch_observations(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 1),
                )

        # Retried and succeeded
        assert mock_get.call_count == 2


# =============================================================================
# Additional Coverage Tests for basegov.py
# =============================================================================


class TestBaseGovClientCoverage:
    """Additional tests for BaseGov client coverage."""

    @pytest.fixture
    def client(self) -> BaseGovClient:
        return BaseGovClient()

    @pytest.mark.asyncio
    async def test_fetch_contracts_timeout_retry(self, client: BaseGovClient) -> None:
        """Test timeout retry logic."""
        success_response = MagicMock()
        success_response.json.return_value = {"items": []}
        success_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(
                side_effect=[
                    httpx.TimeoutException("timeout"),
                    success_response,
                ]
            )
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.fetch_contracts(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )

            assert mock_get.call_count == 2
            assert result == []

    @pytest.mark.asyncio
    async def test_fetch_all_contracts_pagination(self, client: BaseGovClient) -> None:
        """Test pagination handling."""
        page1_response = MagicMock()
        page1_response.json.return_value = {
            "items": [{"id": "1", "dataPublicacao": "2024-01-15", "precoContratual": 1000000}]
            * 100  # Full page
        }
        page1_response.raise_for_status = MagicMock()

        page2_response = MagicMock()
        page2_response.json.return_value = {
            "items": [{"id": "101", "dataPublicacao": "2024-01-20", "precoContratual": 500000}]
            * 50  # Partial page
        }
        page2_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=[page1_response, page2_response])
            mock_client.return_value.__aenter__.return_value.get = mock_get

            result = await client.fetch_all_contracts(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        # 100 from page 1 + 50 from page 2
        assert len(result) == 150

    def test_parse_contracts_alternate_field_names(self, client: BaseGovClient) -> None:
        """Test parsing with alternate field names (contratos key)."""
        data = {
            "contratos": [
                {
                    "idContrato": "12345",
                    "data_publicacao": "2024-01-15T10:00:00",
                    "valor": "1500000.50",
                    "descricao": "Road construction",
                    "adjudicante": "Câmara Municipal",
                    "contratado": "Empresa ABC",
                },
            ]
        }
        result = client._parse_contracts(data)
        assert len(result) == 1
        assert result[0].contract_value_eur == 1500000.50

    def test_parse_contracts_malformed_data(self, client: BaseGovClient) -> None:
        """Test parsing with malformed data."""
        data = {
            "items": [
                {"id": "1"},  # Missing required fields
                {"dataPublicacao": "invalid-date", "precoContratual": 1000},
            ]
        }
        result = client._parse_contracts(data)
        # Both records should fail to parse
        assert result == []


# =============================================================================
# Additional Coverage Tests for commodities.py
# =============================================================================


class TestCommoditiesClientCoverage:
    """Additional tests for commodities client coverage."""

    @pytest.fixture
    def client(self, tmp_path) -> CommoditiesClient:
        return CommoditiesClient(cache_dir=tmp_path / "cache")

    @pytest.mark.asyncio
    async def test_fetch_co2_prices_timeout_exhausted(self, client: CommoditiesClient) -> None:
        """Test CO2 fetch with all retries exhausted."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("timeout")
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                # Should fall back to empty cache
                result = await client.fetch_co2_prices(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )

        assert result == []

    def test_save_to_cache_merge_existing(self, client: CommoditiesClient) -> None:
        """Test merging new prices with existing cache."""
        from raglite.external_data.models import CoalPrice

        # Save initial prices
        initial_prices = [
            CoalPrice(date=date(2024, 1, 1), price=120.0),
            CoalPrice(date=date(2024, 1, 8), price=122.0),
        ]
        client.save_to_cache("coal", initial_prices)

        # Save new prices (including one that overwrites)
        new_prices = [
            CoalPrice(date=date(2024, 1, 8), price=125.0),  # Overwrite
            CoalPrice(date=date(2024, 1, 15), price=128.0),  # New
        ]
        client.save_to_cache("coal", new_prices)

        # Load and verify
        loaded = client.load_from_cache("coal")
        assert len(loaded) == 3
        # Find the Jan 8 price - should be updated
        jan8_price = next(p for p in loaded if p.date == date(2024, 1, 8))
        assert jan8_price.price == 125.0

    def test_load_cache_corrupted_file(self, client: CommoditiesClient) -> None:
        """Test loading from corrupted cache file."""
        cache_file = client.cache_dir / "corrupted_prices.json"
        cache_file.write_text("not valid json {{{")

        result = client.load_from_cache("corrupted")
        assert result == []

    def test_load_cache_invalid_record(self, client: CommoditiesClient) -> None:
        """Test loading cache with invalid records."""
        import json

        cache_file = client.cache_dir / "coal_prices.json"
        cache_file.write_text(
            json.dumps(
                [
                    {"date": "2024-01-01", "price": 120.0},  # Valid
                    {"date": "invalid", "price": 130.0},  # Invalid date
                    {"date": "2024-01-15"},  # Missing price
                ]
            )
        )

        result = client.load_from_cache("coal")
        # Only the valid record should be loaded
        assert len(result) == 1

    def test_import_csv_petcoke(self, client: CommoditiesClient, tmp_path) -> None:
        """Test CSV import for petcoke commodity."""
        csv_file = tmp_path / "petcoke_prices.csv"
        csv_file.write_text(
            """date,price,currency,unit,sulfur_content_pct
2024-01-01,180.0,EUR,EUR/tonne,3.5
2024-01-08,185.0,EUR,EUR/tonne,3.2"""
        )

        result = client.import_from_csv("petcoke", csv_file)

        assert len(result) == 2
        assert result[0].price == 180.0
        assert result[0].sulfur_content_pct == 3.5

    def test_import_csv_co2(self, client: CommoditiesClient, tmp_path) -> None:
        """Test CSV import for CO2 EUA commodity."""
        csv_file = tmp_path / "co2_prices.csv"
        csv_file.write_text(
            """date,price,currency,unit
2024-01-01,85.0,EUR,EUR/tonne
2024-01-08,88.0,EUR,EUR/tonne"""
        )

        result = client.import_from_csv("co2_eua", csv_file)

        assert len(result) == 2
        assert result[0].price == 85.0

    def test_import_csv_generic_commodity(self, client: CommoditiesClient, tmp_path) -> None:
        """Test CSV import for generic commodity type."""
        csv_file = tmp_path / "other_prices.csv"
        csv_file.write_text(
            """date,price,currency,unit
2024-01-01,50.0,EUR,EUR/unit"""
        )

        result = client.import_from_csv("other", csv_file)

        assert len(result) == 1
        assert result[0].price == 50.0

    def test_import_csv_invalid_row(self, client: CommoditiesClient, tmp_path) -> None:
        """Test CSV import with invalid rows."""
        csv_file = tmp_path / "coal_prices.csv"
        csv_file.write_text(
            """date,price,currency,unit
2024-01-01,120.0,EUR,EUR/tonne
invalid-date,130.0,EUR,EUR/tonne
2024-01-15,not-a-number,EUR,EUR/tonne"""
        )

        result = client.import_from_csv("coal", csv_file)

        # Only the valid row should be imported
        assert len(result) == 1
        assert result[0].price == 120.0
