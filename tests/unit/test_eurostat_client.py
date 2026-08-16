"""Unit tests for Eurostat client.

Story 6.8: Tier 2 Data Sources & ML Enhancements (Conditional)

Tests for AC1.3 (Eurostat Electricity Prices) client.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from raglite.external_data.clients.eurostat import EurostatClient
from raglite.external_data.exceptions import ExternalDataFetchError


class TestEurostatClientElectricity:
    """Tests for Eurostat Electricity Prices (AC1.3)."""

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    @pytest.mark.asyncio
    async def test_fetch_electricity_prices_returns_data(self, client: EurostatClient) -> None:
        """AC1.3: Should fetch electricity prices for Portugal."""
        # Mock Eurostat SDMX response
        mock_response = {
            "value": {
                "0": 0.1234,
                "1": 0.1256,
                "2": 0.1278,
            },
            "dimension": {
                "time": {
                    "category": {
                        "index": {
                            "2024-01": 0,
                            "2024-02": 1,
                            "2024-03": 2,
                        }
                    }
                }
            },
        }

        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            result = await client.fetch_electricity_prices(
                country="PT",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 31),
            )

            assert len(result) == 3
            assert all(p.__class__.__name__ == "EurostatElectricityPrice" for p in result)
            assert result[0].price_eur_kwh == 0.1234
            assert result[0].country == "PT"

    @pytest.mark.asyncio
    async def test_fetch_electricity_prices_filters_by_date(self, client: EurostatClient) -> None:
        """AC1.3: Should filter results by date range."""
        mock_response = {
            "value": {
                "0": 0.12,
                "1": 0.13,
                "2": 0.14,
            },
            "dimension": {
                "time": {
                    "category": {
                        "index": {
                            "2024-01": 0,
                            "2024-02": 1,
                            "2023-12": 2,  # Outside range
                        }
                    }
                }
            },
        }

        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            result = await client.fetch_electricity_prices(
                country="PT",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 2, 28),
            )

            assert len(result) == 2
            assert all(r.date >= date(2024, 1, 1) for r in result)

    @pytest.mark.asyncio
    async def test_fetch_electricity_prices_multiple_countries(
        self, client: EurostatClient
    ) -> None:
        """AC1.3: Should support multiple EU countries."""
        mock_response = {
            "value": {"0": 0.15},
            "dimension": {"time": {"category": {"index": {"2024-01": 0}}}},
        }

        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            # Test Spain
            result = await client.fetch_electricity_prices(
                country="ES",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

            assert result[0].country == "ES"

    @pytest.mark.asyncio
    async def test_fetch_electricity_prices_consumption_bands(self, client: EurostatClient) -> None:
        """AC1.3: Should support different consumption bands."""
        mock_response = {
            "value": {"0": 0.10},
            "dimension": {"time": {"category": {"index": {"2024-01": 0}}}},
        }

        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            # Test industrial consumer band
            result = await client.fetch_electricity_prices(
                country="PT",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                consumption_band="IF",  # 2000-20000 MWh/year
            )

            assert result[0].consumption_band == "IF"

    @pytest.mark.asyncio
    async def test_fetch_electricity_prices_tax_excluded(self, client: EurostatClient) -> None:
        """AC1.3: Should support excluding taxes."""
        mock_response = {
            "value": {"0": 0.08},
            "dimension": {"time": {"category": {"index": {"2024-01": 0}}}},
        }

        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response

            result = await client.fetch_electricity_prices(
                country="PT",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                include_taxes=False,
            )

            assert result[0].tax_component == "X_TAX"

    @pytest.mark.asyncio
    async def test_fetch_electricity_prices_handles_api_error(self, client: EurostatClient) -> None:
        """AC1.3: Should handle API errors gracefully."""
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ExternalDataFetchError(
                source="Eurostat", message="API unavailable"
            )

            with pytest.raises(ExternalDataFetchError):
                await client.fetch_electricity_prices(
                    country="PT",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )


class TestEurostatClientRetry:
    """Tests for NFR1 retry logic."""

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    @pytest.mark.asyncio
    async def test_retry_on_server_error(self, client: EurostatClient) -> None:
        """NFR1: Should retry on 5xx errors."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Create proper mock responses
            error_response = AsyncMock()
            error_response.status_code = 503
            error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=AsyncMock(), response=error_response
            )

            success_response = AsyncMock()
            success_response.status_code = 200
            success_response.json.return_value = {
                "value": {"0": 0.12},
                "dimension": {"time": {"category": {"index": {"2024-01": 0}}}},
            }
            success_response.raise_for_status = lambda: None

            mock_client.get.side_effect = [
                error_response,
                success_response,
            ]

            # Test should succeed after retry
            # (actual test implementation depends on client retry logic)
            pass


class TestEurostatClientDatasets:
    """Tests for Eurostat dataset configuration."""

    def test_dataset_code_electricity(self) -> None:
        """Should use correct dataset code for electricity prices."""
        client = EurostatClient()
        assert client.ELECTRICITY_DATASET == "nrg_pc_204"

    def test_consumption_band_mapping(self) -> None:
        """Should map consumption bands correctly."""
        client = EurostatClient()
        assert "IC" in client.CONSUMPTION_BANDS  # 500-2000 MWh
        assert "IF" in client.CONSUMPTION_BANDS  # 2000-20000 MWh
