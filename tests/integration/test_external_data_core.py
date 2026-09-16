"""Integration tests for external data clients - Core clients.

Story 6.1: Tier 1 External Data Source Integration
AC7: Integration Tests

Tests end-to-end flows with sample data:
- Full fetch → parse → validate pipeline
- Pydantic model validation
- Historical data load (sample: 2024-01-01 to 2024-03-31)
- Multi-client coordination

Part 1: Core clients (INE, BPstat, OMIE)
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.external_data.clients import (
    BPstatClient,
    INEClient,
    OMIEClient,
)
from raglite.external_data.models import (
    DataSource,
    INEBuildingPermits,
)

# Mark all tests in this module as integration tests that preserve collection state
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.integration,
    pytest.mark.preserve_collection,
]

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
            assert record.__class__.__name__ == "BPstatMortgageLoans"
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
            assert record.__class__.__name__ == "OMIEElectricityPrice"
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
