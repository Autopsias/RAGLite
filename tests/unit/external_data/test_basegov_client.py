"""Unit tests for Base.gov.pt (Public Contracts) client.

Story 7.1: Split test_external_data_clients.py
This module contains core BaseGov client tests.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from raglite.external_data.clients.basegov import BaseGovClient


class TestBaseGovClient:
    """Tests for Base.gov.pt public procurement client.

    Story 6.9.5: Updated tests for TED API v3 and OCDS fallback.
    """

    @pytest.fixture
    def client(self) -> BaseGovClient:
        """Create Base.gov.pt client instance."""
        return BaseGovClient()

    @pytest.fixture
    def mock_ted_response(self) -> dict:
        """Create mock TED API response."""
        return {
            "notices": [
                {
                    "publication-number": "2024/S 015-012345",
                    "publication-date": "2024-01-15",
                    "notice-title": "Road construction project",
                    "buyer-name": "Câmara Municipal de Lisboa",
                    "winner-name": "Empresa ABC, Lda",
                    "total-value": 1500000,
                    "cpv": "45233000",
                    "place-of-performance": "PT",
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_fetch_contracts_success(
        self, client: BaseGovClient, mock_ted_response: dict
    ) -> None:
        """Test successful contracts fetch via TED API."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_ted_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_contracts(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

            assert len(result) == 1
            assert result[0].__class__.__name__ == "BaseGovContract"
            assert result[0].contract_value_eur == 1500000
            assert result[0].contractor == "Empresa ABC, Lda"
            assert result[0].cpv_code == "45233000"

    def test_cpv_codes(self, client: BaseGovClient) -> None:
        """Test CPV code constants."""
        assert client.CPV_CONSTRUCTION == "45000000"
        assert client.CPV_BUILDING == "45210000"
        assert client.CPV_ROAD == "45233000"

    def test_eu_thresholds(self, client: BaseGovClient) -> None:
        """Test EU procurement threshold constants."""
        assert client.EU_THRESHOLD_WORKS == 5_382_000
        assert client.EU_THRESHOLD_SUPPLIES == 221_000
        assert client.EU_THRESHOLD_SERVICES == 221_000


# =============================================================================
# Story 6.9.5: BaseGov Public Procurement Fix Tests
# =============================================================================


class TestBaseGovClientAdditional:
    """Additional tests for Base.gov.pt client coverage.

    Story 6.9.5: Updated for TED API v3 implementation.
    """

    @pytest.fixture
    def client(self) -> BaseGovClient:
        return BaseGovClient()

    @pytest.mark.asyncio
    async def test_fetch_construction_summary(self, client: BaseGovClient) -> None:
        """Test construction contracts summary calculation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "notices": [
                {
                    "publication-number": "2024/S 015-00001",
                    "publication-date": "2024-01-15",
                    "total-value": 1000000,
                },
                {
                    "publication-number": "2024/S 015-00002",
                    "publication-date": "2024-01-20",
                    "total-value": 2000000,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_construction_contracts_summary(2024, 1)

        assert result["total_contracts"] == 2
        assert result["total_value_eur"] == 3000000
        assert result["avg_value_eur"] == 1500000
        # Story 6.9.5: Now uses IMPIC as primary source
        assert "IMPIC" in result["data_source"] or "TED" in result["data_source"]
        assert "note" in result


class TestBaseGovClientCoverage:
    """Additional tests for BaseGov client coverage.

    Story 6.9.5: Updated for TED API v3 implementation.
    """

    @pytest.fixture
    def client(self) -> BaseGovClient:
        return BaseGovClient()

    @pytest.mark.asyncio
    async def test_fetch_contracts_timeout_retry(self, client: BaseGovClient) -> None:
        """Test timeout retry logic with TED API."""
        success_response = MagicMock()
        # Return non-empty results to avoid OCDS fallback
        success_response.json.return_value = {
            "notices": [
                {
                    "publication-number": "2024/S 015-00001",
                    "publication-date": "2024-01-15",
                    "total-value": 1000000,
                }
            ]
        }
        success_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(
                side_effect=[
                    httpx.TimeoutException("timeout"),
                    success_response,
                ]
            )
            mock_client.return_value.__aenter__.return_value.post = mock_post

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.fetch_contracts(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )

            assert mock_post.call_count == 2
            # Retry succeeded - should return the contract from second attempt
            assert len(result) == 1
            assert result[0].contract_id == "2024/S 015-00001"

    @pytest.mark.asyncio
    async def test_fetch_all_contracts_pagination(self, client: BaseGovClient) -> None:
        """Test pagination handling with TED API."""
        page1_response = MagicMock()
        page1_response.json.return_value = {
            "notices": [
                {
                    "publication-number": f"2024/S 015-{i:05d}",
                    "publication-date": "2024-01-15",
                    "total-value": 1000000,
                }
                for i in range(100)  # Full page
            ]
        }
        page1_response.raise_for_status = MagicMock()

        page2_response = MagicMock()
        page2_response.json.return_value = {
            "notices": [
                {
                    "publication-number": f"2024/S 015-{100 + i:05d}",
                    "publication-date": "2024-01-20",
                    "total-value": 500000,
                }
                for i in range(50)  # Partial page
            ]
        }
        page2_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=[page1_response, page2_response])
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await client.fetch_all_contracts(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        # 100 from page 1 + 50 from page 2
        assert len(result) == 150

    def test_deprecated_parse_contracts_logs_warning(self, client: BaseGovClient, caplog) -> None:
        """Test deprecated _parse_contracts method logs warning."""
        import logging

        with caplog.at_level(logging.WARNING):
            # _parse_contracts is deprecated - should log warning and return empty
            result = client._parse_contracts({"items": []})

        assert "Deprecated" in caplog.text or "deprecated" in caplog.text.lower()
        assert result == []  # Deprecated method returns empty list

    def test_parse_ted_notices_missing_date(self, client: BaseGovClient) -> None:
        """Test TED notice parsing with missing publication date."""
        data = {
            "notices": [
                {"publication-number": "001"},  # Missing publication-date
                {
                    "publication-number": "002",
                    "publication-date": "2024-01-15",
                    "total-value": 1000000,
                },
            ]
        }
        result = client._parse_ted_notices(data)
        # Only second record should be parsed
        assert len(result) == 1
        assert result[0].contract_id == "002"


# =============================================================================
# End of BaseGov Client Tests
# =============================================================================
