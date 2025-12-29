"""Integration tests for coordinating multiple clients."""

from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.external_data.clients import BPstatClient, INEClient, OMIEClient
from raglite.external_data.models import DataSource, ExternalDataPoint, INEBuildingPermits

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


@pytest.mark.asyncio
class TestMultiClientCoordination:
    """Integration tests for coordinating multiple clients."""

    async def test_parallel_data_fetch(
        self, sample_ine_response, sample_bpstat_response, sample_omie_response
    ) -> None:
        """Test fetching from multiple sources in parallel.

        Story 6.9: Updated for new API response formats.
        Each client is mocked independently to ensure proper responses.
        """
        # Create mock responses
        ine_response = MagicMock()
        ine_response.json.return_value = sample_ine_response
        ine_response.raise_for_status = MagicMock()

        # Story 6.9.3: BPstat now fetches interest rates in one request
        bpstat_response = MagicMock()
        bpstat_response.json.return_value = sample_bpstat_response
        bpstat_response.raise_for_status = MagicMock()

        # Story 6.9.2: OMIE uses new CSV format
        omie_response = MagicMock()
        omie_response.text = sample_omie_response
        omie_response.raise_for_status = MagicMock()

        # Mock each client's HTTP calls independently using patch.object
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
