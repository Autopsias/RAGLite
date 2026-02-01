"""Unit tests for INE (Instituto Nacional de Estatística) client.

Story 7.1: Split test_external_data_clients.py
This module contains all tests related to the INE client.

Test Classes:
- TestINEClient: Core API client tests
- TestINEDateFiltering: Date filtering bug fixes (Story 6.9.1)
- TestINEClientAdditional: Additional coverage tests
- TestStory68INEExtensions: Story 6.8 extensions (HPI, confidence index)
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from raglite.external_data.clients.ine import INEClient
from raglite.external_data.exceptions import ExternalDataFetchError


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
            assert result[0].__class__.__name__ == "INEBuildingPermits"
            assert result[0].permits_count == 1234
            assert result[0].region == "Lisboa"

    @pytest.mark.asyncio
    async def test_fetch_building_permits_timeout_retry(self, client: INEClient) -> None:
        """Test retry logic on timeout."""
        # Story 6.10.3: Clear cache to ensure mock is used
        client._cache.clear()

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
        # Story 6.10.3: Clear cache to ensure mock is used
        client._cache.clear()

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
                "202401": [{"valor": 105.5, "dim_3_t": "Total"}],
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
            assert result[0].__class__.__name__ == "INEConstructionOutput"
            assert result[0].index_value == 105.5
            # Note: INE doesn't provide YoY change in API response; it's calculated separately
            assert result[0].yoy_change_pct is None

    @pytest.mark.asyncio
    async def test_fetch_construction_cost_index_success(self, client: INEClient) -> None:
        """Test successful construction cost index fetch."""
        mock_response = MagicMock()
        # INE returns separate records per cost factor (Total, Materiais, Mão de obra)
        mock_response.json.return_value = {
            "Dados": {
                "202401": [
                    {"valor": 110.2, "dim_3_t": "Total"},
                    {"valor": 112.5, "dim_3_t": "Materiais"},
                    {"valor": 108.1, "dim_3_t": "Mão de obra"},
                ],
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
            assert result[0].__class__.__name__ == "INEConstructionCostIndex"
            assert result[0].total_index == 110.2
            assert result[0].materials_index == 112.5
            assert result[0].labor_index == 108.1


class TestINEDateFiltering:
    """Story 6.9.1 AC1-AC3 date filtering tests."""

    @pytest.fixture
    def client(self) -> INEClient:
        return INEClient()

    def test_mid_month_start_date_includes_month(self, client: INEClient) -> None:
        """AC1/AC2: Mid-month start includes full month."""
        data = {
            "Dados": {
                "Setembro de 2025": [{"valor": 1234, "geocod": "Portugal"}],
                "Outubro de 2025": [{"valor": 1456, "geocod": "Portugal"}],
            }
        }

        result = client._parse_building_permits(
            data,
            start_date=date(2025, 9, 15),
            end_date=date(2025, 10, 31),
        )

        assert len(result) == 2
        dates = [r.date for r in result]
        assert date(2025, 9, 1) in dates
        assert date(2025, 10, 1) in dates

    def test_first_of_month_start_date(self, client: INEClient) -> None:
        """AC1: Start date of 2025-09-01 should include September data."""
        data = {
            "Dados": {
                "Setembro de 2025": [{"valor": 1234, "geocod": "Portugal"}],
            }
        }

        result = client._parse_building_permits(
            data,
            start_date=date(2025, 9, 1),  # First of month
            end_date=date(2025, 9, 30),
        )

        assert len(result) == 1
        assert result[0].date == date(2025, 9, 1)

    def test_end_of_month_start_date_includes_month(self, client: INEClient) -> None:
        """AC1: End-of-month start includes full month."""
        data = {"Dados": {"Setembro de 2025": [{"valor": 1234, "geocod": "Portugal"}]}}
        result = client._parse_building_permits(
            data, start_date=date(2025, 9, 30), end_date=date(2025, 9, 30)
        )

        assert len(result) == 1
        assert result[0].date == date(2025, 9, 1)

    def test_construction_output_mid_month_filtering(self, client: INEClient) -> None:
        """AC3: construction_output first-of-month comparison."""
        data = {"Dados": {"202509": [{"valor": 105.5, "dim_3_t": "Total"}]}}
        result = client._parse_construction_output(
            data, start_date=date(2025, 9, 15), end_date=date(2025, 9, 30)
        )

        assert len(result) == 1
        assert result[0].date == date(2025, 9, 1)

    def test_construction_cost_index_mid_month_filtering(self, client: INEClient) -> None:
        """AC3: cost_index first-of-month comparison."""
        data = {"Dados": {"202509": [{"valor": 110.2, "dim_3_t": "Total"}]}}
        result = client._parse_construction_cost_index(
            data, start_date=date(2025, 9, 15), end_date=date(2025, 9, 30)
        )

        assert len(result) == 1
        assert result[0].date == date(2025, 9, 1)

    def test_date_filtering_excludes_earlier_months(self, client: INEClient) -> None:
        """Verify earlier months correctly excluded."""
        data = {
            "Dados": {
                "Agosto de 2025": [{"valor": 1000, "geocod": "Portugal"}],
                "Setembro de 2025": [{"valor": 1234, "geocod": "Portugal"}],
            }
        }
        result = client._parse_building_permits(
            data, start_date=date(2025, 9, 15), end_date=date(2025, 9, 30)
        )

        assert len(result) == 1
        assert result[0].date == date(2025, 9, 1)


class TestINEClientAdditional:
    """Additional tests for INE client coverage."""

    @pytest.fixture
    def client(self) -> INEClient:
        return INEClient()

    @pytest.mark.asyncio
    async def test_http_client_error(self, client: INEClient) -> None:
        """Test handling of 4xx client errors (no retry)."""
        # Story 6.10.3: Clear cache to ensure mock is used
        client._cache.clear()

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


class TestStory68INEExtensions:
    """Tests for INE client Story 6.8 extensions (AC2.1)."""

    @pytest.fixture
    def client(self) -> INEClient:
        return INEClient()

    def test_house_price_index_indicator_constant(self) -> None:
        """AC2.1: Verify HPI indicator (Story 6.11.4 fixed)."""
        assert INEClient.HOUSE_PRICE_INDEX_INDICATOR == "0009201"

    def test_construction_confidence_indicator_constant(self) -> None:
        """AC2.1: Verify Construction Confidence indicator code is defined."""
        assert INEClient.CONSTRUCTION_CONFIDENCE_INDICATOR == "0011127"

    @pytest.mark.asyncio
    async def test_fetch_house_price_index_success(self, client: INEClient) -> None:
        """AC2.1: Test successful house price index fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Dados": {
                "2024T1": [{"valor": 145.2, "geodsg": "Portugal"}],
                "2024T2": [{"valor": 148.5, "geodsg": "Portugal"}],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_house_price_index(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

            assert len(result) == 2
            assert result[0].index_value == 145.2
            assert result[0].region == "Portugal"

    @pytest.mark.asyncio
    async def test_fetch_construction_confidence_success(self, client: INEClient) -> None:
        """AC2.1: Test successful construction confidence fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Dados": {
                "202401": [{"valor": -5.2, "geodsg": "Portugal"}],
                "202402": [{"valor": -3.8, "geodsg": "Portugal"}],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_construction_confidence(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 2, 28),
            )

            assert len(result) == 2
            assert result[0].confidence_index == -5.2
