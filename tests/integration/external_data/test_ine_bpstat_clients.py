"""Integration tests for INE and BPstat clients."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from raglite.external_data.clients import BPstatClient, INEClient
from raglite.external_data.models import (
    DataSource,
    INEBuildingPermits,
)

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


@pytest.mark.asyncio
class TestINEClientIntegration:
    """Integration tests for INE API client."""

    async def test_historical_load_q1_2024(self, sample_ine_response, mock_response) -> None:
        """Test historical data load for Q1 2024 sample period."""
        client = INEClient()

        http_mock = mock_response(json_data=sample_ine_response)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=http_mock)

            result = await client.fetch_building_permits(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 31),
            )

        # Verify correct number of records across 3 months
        assert len(result) >= 3
        # Verify model validation passed
        for record in result:
            assert record.__class__.__name__ == "INEBuildingPermits"
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

    async def test_historical_load_q1_2024(self, sample_bpstat_response, mock_response) -> None:
        """Test historical data load for Q1 2024."""
        client = BPstatClient()

        http_mock = mock_response(json_data=sample_bpstat_response)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=http_mock)

            result = await client.fetch_mortgage_loans(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 31),
            )

        assert len(result) == 3
        for record in result:
            assert record.__class__.__name__ == "BPstatMortgageLoans"
            assert record.source == DataSource.BPSTAT
            # Story 6.9.3: Now returns interest rates, not loan amounts
            assert record.total_loans_eur == 0.0
            # Verify interest rate is present
            assert record.avg_interest_rate_pct is not None
            assert 3.0 <= record.avg_interest_rate_pct <= 4.0
