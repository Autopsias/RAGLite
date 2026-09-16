"""Integration tests for OMIE and BaseGov clients."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from raglite.external_data.clients import BaseGovClient, OMIEClient
from raglite.external_data.models import (
    DataSource,
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
class TestOMIEClientIntegration:
    """Integration tests for OMIE electricity market client."""

    async def test_historical_load_with_hourly_data(
        self, sample_omie_response, mock_response
    ) -> None:
        """Test fetching hourly electricity prices."""
        client = OMIEClient()

        http_mock = mock_response(text_data=sample_omie_response)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=http_mock)

            result = await client.fetch_spot_prices(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
                include_hourly=True,
            )

        # 24 hours of data
        assert len(result) == 24
        for record in result:
            assert record.__class__.__name__ == "OMIEElectricityPrice"
            assert record.market == "MIBEL"
            assert record.hour is not None and 0 <= record.hour <= 23
            assert record.price_eur_mwh > 0

    async def test_daily_average_calculation(self, sample_omie_response, mock_response) -> None:
        """Test daily average price calculation."""
        client = OMIEClient()

        http_mock = mock_response(text_data=sample_omie_response)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=http_mock)

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

    async def test_construction_contracts_fetch(self, mock_response) -> None:
        """Test fetching construction contracts.

        Story 6.9.5: BaseGov now uses dados.gov.pt IMPIC XLSX as primary source.
        Story 8.2 Task 4: Refactored IMPIC logic to standalone module.

        We mock IMPIC to return empty (triggers TED fallback) since IMPIC XLSX
        parsing requires real file downloads.
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

        http_mock = mock_response(json_data=ted_response)

        # Mock get_impic_resource_urls to return empty (trigger TED fallback)
        # Story 8.2: Method moved from private _get_impic_resource_urls to public
        # get_impic_resource_urls in impic module
        with patch(
            "raglite.external_data.clients.basegov.impic.get_impic_resource_urls",
            new_callable=AsyncMock,
        ) as mock_impic:
            mock_impic.return_value = {}  # Empty = no IMPIC data available

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=http_mock
                )

                result = await client.fetch_contracts(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 3, 31),
                    cpv_code="45000000",
                )

        assert len(result) == 2
        for contract in result:
            assert contract.__class__.__name__ == "BaseGovContract"
            assert contract.source == DataSource.BASEGOV
            assert contract.contract_value_eur > 0
            assert contract.cpv_code is not None
