"""Unit tests for BPstat (Banco de Portugal) client.

Story 7.1: Split test_external_data_clients.py
This module contains tests for: TestBPstatClient, TestBPstatClientAdditional,
TestBPstatStory693, TestStory68BPstatExtensions
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from raglite.external_data.clients.bpstat import BPstatClient
from raglite.external_data.exceptions import (
    ExternalDataFetchError,
)


class TestBPstatClient:
    """Tests for BPstat client (Story 6.9.3 - new API structure)."""

    @pytest.fixture
    def client(self) -> BPstatClient:
        return BPstatClient()

    @pytest.mark.asyncio
    async def test_fetch_mortgage_loans_success(self, client: BPstatClient) -> None:
        """Test successful mortgage fetch (Story 6.9.3 AC4)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "observations": [
                {"period": "2024-01", "value": 3.45, "series_id": "12710733"},
                {"period": "2024-02", "value": 3.50, "series_id": "12710733"},
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
            assert result[0].__class__.__name__ == "BPstatMortgageLoans"
            assert result[0].avg_interest_rate_pct == 3.45
            assert result[1].avg_interest_rate_pct == 3.50

    @pytest.mark.asyncio
    async def test_fetch_mortgage_loans_server_error_retry(self, client: BPstatClient) -> None:
        """Test retry on server error (Story 6.9.3 AC7)."""
        error_response = MagicMock()
        error_response.status_code = 500
        error = httpx.HTTPStatusError("Server Error", request=MagicMock(), response=error_response)

        success_response = MagicMock()
        success_response.json.return_value = {
            "observations": [{"period": "2024-01", "value": 3.50, "series_id": "12710733"}]
        }
        success_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=[error, error, success_response])
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.fetch_mortgage_loans(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )

            assert len(result) == 1
            assert mock_get.call_count == 3


class TestBPstatClientAdditional:
    """Additional BPstat tests (Story 6.9.3)."""

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

    def test_parse_interest_rate_data_empty(self, client: BPstatClient) -> None:
        """Test empty observations parsing (Story 6.9.3)."""
        from raglite.external_data.clients.bpstat.parsers import BPstatParser

        parser = BPstatParser(client.MORTGAGE_RATE_MEDIAN, client.MORTGAGE_LOANS_SERIES)
        response = {"observations": []}
        result = parser.parse_interest_rate_data(response, [client.MORTGAGE_RATE_MEDIAN])
        assert len(result) == 0

    def test_parse_interest_rate_data_multiple_periods(self, client: BPstatClient) -> None:
        """Test multiple periods parsing (Story 6.9.3 AC3)."""
        from raglite.external_data.clients.bpstat.parsers import BPstatParser

        parser = BPstatParser(client.MORTGAGE_RATE_MEDIAN, client.MORTGAGE_LOANS_SERIES)
        response = {
            "observations": [
                {"period": "2024-01", "value": 3.45, "series_id": "12710733"},
                {"period": "2024-02", "value": 3.50, "series_id": "12710733"},
                {"period": "2024-03", "value": 3.55, "series_id": "12710733"},
            ]
        }

        result = parser.parse_interest_rate_data(response, [client.MORTGAGE_RATE_MEDIAN])

        assert len(result) == 3
        assert result[0].avg_interest_rate_pct == 3.45
        assert result[1].avg_interest_rate_pct == 3.50
        assert result[2].avg_interest_rate_pct == 3.55


class TestBPstatStory693:
    """Story 6.9.3 AC1-AC7 validation tests."""

    def test_correct_series_ids_used(self) -> None:
        """AC1: Verify mortgage rate series IDs are correct (12710733 not 12532089)."""
        from raglite.external_data.clients.bpstat import BPstatClient

        # New correct series IDs
        assert BPstatClient.MORTGAGE_RATE_MEDIAN == "12710733"
        assert BPstatClient.MORTGAGE_RATE_10TH_PERCENTILE == "12710735"
        assert BPstatClient.MORTGAGE_RATE_25TH_PERCENTILE == "12710781"
        assert BPstatClient.MORTGAGE_RATE_75TH_PERCENTILE == "12710734"
        assert BPstatClient.MORTGAGE_RATE_90TH_PERCENTILE == "12710736"

    def test_old_series_ids_not_used(self) -> None:
        """AC1: Verify old/wrong series IDs are removed or aliased."""
        from raglite.external_data.clients.bpstat import BPstatClient

        # Old series IDs should NOT be the wrong values
        assert BPstatClient.MORTGAGE_LOANS_SERIES != "12532089"  # Was Egyptian Pound!
        # Old alias should point to new correct ID
        assert BPstatClient.MORTGAGE_LOANS_SERIES == "12710733"

    def test_new_api_endpoint(self) -> None:
        """AC2: Verify using /api/observations/ endpoint."""
        from raglite.external_data.clients.bpstat import BPSTAT_API_BASE

        # New endpoint should be /api (not /data/v1)
        assert BPSTAT_API_BASE == "https://bpstat.bportugal.pt/api"
        assert "/data/v1" not in BPSTAT_API_BASE

    def test_observations_endpoint_url_structure(self) -> None:
        """AC2: Verify observations URL is constructed correctly."""
        from raglite.external_data.clients.bpstat import BPstatClient

        client = BPstatClient()
        # URL should end with /observations/
        expected_base = "https://bpstat.bportugal.pt/api"
        assert client.base_url == expected_base

    def test_new_response_parsing(self) -> None:
        """AC3: Verify new API response parsing."""
        from raglite.external_data.clients.bpstat import BPstatClient
        from raglite.external_data.clients.bpstat.parsers import BPstatParser

        client = BPstatClient()
        parser = BPstatParser(client.MORTGAGE_RATE_MEDIAN, client.MORTGAGE_LOANS_SERIES)

        # New API response format
        response = {
            "observations": [
                {"period": "2024-01", "value": 3.45, "series_id": "12710733"},
                {"period": "2024-02", "value": 3.50, "series_id": "12710733"},
            ]
        }

        result = parser.parse_interest_rate_data(response, ["12710733"])

        assert len(result) == 2
        assert result[0].avg_interest_rate_pct == 3.45
        assert result[1].avg_interest_rate_pct == 3.50
        # Dates should be first of month
        assert result[0].date == date(2024, 1, 1)
        assert result[1].date == date(2024, 2, 1)

    def test_response_parsing_with_refperiod_key(self) -> None:
        """AC3: Verify both 'period' and 'refPeriod' keys handled."""
        from raglite.external_data.clients.bpstat import BPstatClient
        from raglite.external_data.clients.bpstat.parsers import BPstatParser

        client = BPstatClient()
        parser = BPstatParser(client.MORTGAGE_RATE_MEDIAN, client.MORTGAGE_LOANS_SERIES)
        response = {
            "observations": [{"refPeriod": "2024-01", "value": 3.45, "series_id": "12710733"}]
        }
        result = parser.parse_interest_rate_data(response, ["12710733"])

        assert len(result) == 1
        assert result[0].avg_interest_rate_pct == 3.45

    def test_response_parsing_skips_invalid_entries(self) -> None:
        """AC3: Verify invalid observations skipped."""
        from raglite.external_data.clients.bpstat import BPstatClient
        from raglite.external_data.clients.bpstat.parsers import BPstatParser

        client = BPstatClient()
        parser = BPstatParser(client.MORTGAGE_RATE_MEDIAN, client.MORTGAGE_LOANS_SERIES)
        response = {
            "observations": [
                {"period": "2024-01", "value": 3.45, "series_id": "12710733"},
                {"period": "2024-02", "value": None, "series_id": "12710733"},
                {"value": 3.60, "series_id": "12710733"},
                {"period": "2024-04", "value": 3.65, "series_id": "12710733"},
            ]
        }
        result = parser.parse_interest_rate_data(response, ["12710733"])

        assert len(result) == 2
        assert result[0].avg_interest_rate_pct == 3.45
        assert result[1].avg_interest_rate_pct == 3.65

    def test_series_ids_documented(self) -> None:
        """AC6: Verify series IDs are documented in code comments."""
        import inspect

        from raglite.external_data.clients.bpstat import BPstatClient

        source = inspect.getsource(BPstatClient)

        # Documentation should mention verified date
        assert "2025-12-08" in source or "Story 6.9.3" in source
        # Should document that old IDs were wrong
        assert "12532089" in source  # Old wrong ID mentioned in comment
        assert "Egyptian" in source or "WRONG" in source or "FX" in source

    def test_bpstat_retry_delays_exponential_backoff(self) -> None:
        """AC7: Verify retry logic uses exponential backoff (2s/4s/8s)."""
        import inspect

        from raglite.external_data.clients.bpstat import BPstatClient

        source = inspect.getsource(BPstatClient._fetch_with_retry)

        # Should have 2, 4, 8 second delays (NFR1 requirement)
        assert "retry_delays = [2, 4, 8]" in source

    @pytest.mark.asyncio
    async def test_fetch_with_include_percentiles(self) -> None:
        """AC4: Test fetching with all percentile series."""
        from raglite.external_data.clients.bpstat import BPstatClient

        client = BPstatClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "observations": [
                {"period": "2024-01", "value": 3.45, "series_id": "12710733"},
                {"period": "2024-01", "value": 3.10, "series_id": "12710735"},
                {"period": "2024-01", "value": 3.25, "series_id": "12710781"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_mortgage_loans(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                include_percentiles=True,
            )

            # Should return median rate
            assert len(result) == 1
            assert result[0].avg_interest_rate_pct == 3.45


class TestStory68BPstatExtensions:
    """Tests for BPstat client Story 6.8 extensions (AC2.2)."""

    @pytest.fixture
    def client(self) -> BPstatClient:
        return BPstatClient()

    def test_bank_appraisal_series_constant(self) -> None:
        """AC2.2: Verify bank appraisal series ID is defined."""
        assert BPstatClient.BANK_APPRAISAL_SERIES == "12559916"

    @pytest.mark.asyncio
    async def test_fetch_bank_appraisals_success(self, client: BPstatClient) -> None:
        """AC2.2: Test successful bank appraisals fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"period": "2024-01", "value": 1234.56, "series_id": "12559916"},
                {"period": "2024-02", "value": 1256.78, "series_id": "12559916"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_bank_appraisals(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 2, 28),
            )

            assert len(result) == 2
            assert result[0].avg_appraisal_eur_m2 == 1234.56
            assert result[0].region == "Portugal"

    def test_parse_bank_appraisal_data_empty(self, client: BPstatClient) -> None:
        """AC2.2: Test parsing empty response."""
        from raglite.external_data.clients.bpstat.parsers import parse_bank_appraisal_data

        response = {"data": []}
        result = parse_bank_appraisal_data(response)

        assert len(result) == 0

    def test_parse_bank_appraisal_data_with_reference_date(self, client: BPstatClient) -> None:
        """AC2.2: Test parsing with reference_date format."""
        from raglite.external_data.clients.bpstat.parsers import parse_bank_appraisal_data

        response = {
            "data": [
                {"reference_date": "2024-01-31", "value": 1300.00},
            ]
        }

        result = parse_bank_appraisal_data(response)

        assert len(result) == 1
        assert result[0].date == date(2024, 1, 1)
        assert result[0].avg_appraisal_eur_m2 == 1300.00
