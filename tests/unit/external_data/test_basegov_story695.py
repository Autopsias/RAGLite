"""Unit tests for Base.gov.pt Story 6.9.5 (API Migration).

Story 7.1: Split test_external_data_clients.py
Story 6.9.5: Migrate from dados.gov.pt OCDS to TED API.

This module contains comprehensive tests for the BaseGov API migration.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from raglite.external_data.clients.basegov import BaseGovClient


class TestBaseGovStory695:
    """Tests for BaseGov Story 6.9.5 - Public Procurement Fix.

    Acceptance Criteria:
    - AC1: Research and verify dados.gov.pt OCDS dataset availability
    - AC2: Implement OCDS data fetching from dados.gov.pt
    - AC3: Parse OCDS format to BaseGovContract model
    - AC4: fetch_contracts() returns valid contract records
    - AC5: Handle pagination appropriately
    - AC6: Fallback to TED for contracts above EU thresholds
    - AC7: Document data source limitations in code comments
    - AC8: Implement retry logic per NFR1
    """

    @pytest.fixture
    def client(self) -> BaseGovClient:
        return BaseGovClient()

    def test_ac1_api_configuration(self) -> None:
        """AC1: Verify API configuration constants."""
        from raglite.external_data.clients.basegov import (
            BASEGOV_API_BASE,
            DADOS_GOV_API_BASE,
            OCDS_DATASET_ID,
            TED_API_BASE,
        )

        # TED API v3 is primary source
        assert TED_API_BASE == "https://tedweb.api.ted.europa.eu/v3"

        # dados.gov.pt OCDS dataset
        assert DADOS_GOV_API_BASE == "https://dados.gov.pt/api/1"
        assert OCDS_DATASET_ID == "ocds-portal-base-www-base-gov-pt"

        # Old Base.gov.pt URL kept for documentation (does NOT work)
        assert "base.gov.pt" in BASEGOV_API_BASE

    @pytest.mark.asyncio
    async def test_ac2_ocds_availability_check(self, client: BaseGovClient) -> None:
        """AC2: Test OCDS dataset availability check."""
        # Mock empty resources (current state as of 2025-12-08)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "ocds-portal-base-www-base-gov-pt",
            "title": "OCDS - Portal BASE",
            "resources": [],  # Empty - no resources available
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client._check_ocds_availability()
            assert result is None  # Returns None when no resources

    @pytest.mark.asyncio
    async def test_ac2_ocds_availability_with_resources(self, client: BaseGovClient) -> None:
        """AC2: Test OCDS check when resources exist."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "ocds-portal-base-www-base-gov-pt",
            "resources": [
                {"format": "json", "url": "https://example.com/ocds.json"},
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client._check_ocds_availability()
            assert result is not None
            assert len(result.get("resources", [])) == 1

    def test_ac3_parse_ocds_data(self, client: BaseGovClient) -> None:
        """AC3: Test OCDS format parsing."""
        ocds_data = {
            "releases": [
                {
                    "ocid": "ocds-pt-001",
                    "date": "2024-01-15T10:00:00Z",
                    "tender": {
                        "title": "Road construction",
                        "items": [{"classification": {"id": "45233000"}}],
                        "value": {"amount": 500000, "currency": "EUR"},
                    },
                    "awards": [{"value": {"amount": 450000}}],
                    "parties": [
                        {"name": "Municipality", "roles": ["buyer"]},
                        {"name": "Contractor ABC", "roles": ["supplier"]},
                    ],
                },
            ]
        }

        result = client._parse_ocds_data(
            ocds_data,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert len(result) == 1
        assert result[0].contract_id == "ocds-pt-001"
        assert result[0].description == "Road construction"
        assert result[0].contract_value_eur == 450000  # Award value
        assert result[0].contracting_entity == "Municipality"
        assert result[0].contractor == "Contractor ABC"

    @pytest.mark.asyncio
    async def test_ac4_fetch_contracts_via_ted(self, client: BaseGovClient) -> None:
        """AC4: Test fetch_contracts with TED API response."""
        mock_ted_response = MagicMock()
        mock_ted_response.json.return_value = {
            "notices": [
                {
                    "publication-number": "2024/S 015-012345",
                    "publication-date": "2024-01-15",
                    "notice-title": "Construction project",
                    "buyer-name": "Município de Porto",
                    "winner-name": "BuildCo, SA",
                    "total-value": 2500000,
                    "cpv": "45210000",
                },
                {
                    "publication-number": "2024/S 015-012346",
                    "publication-date": "2024-01-20",
                    "notice-title": "Road works",
                    "buyer-name": "Município de Braga",
                    "winner-name": "RoadCo, SA",
                    "total-value": 3000000,
                    "cpv": "45233000",
                },
            ]
        }
        mock_ted_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_ted_response
            )

            result = await client.fetch_contracts(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

            assert len(result) == 2
            assert result[0].contract_value_eur == 2500000
            assert result[1].contract_value_eur == 3000000

    @pytest.mark.asyncio
    async def test_ac5_pagination(self, client: BaseGovClient) -> None:
        """AC5: Test pagination in fetch_all_contracts."""
        call_count = 0

        async def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = MagicMock()
            if call_count == 1:
                # First page - full results
                mock_response.json.return_value = {
                    "notices": [
                        {
                            "publication-number": f"2024/S 015-{i:05d}",
                            "publication-date": "2024-01-15",
                            "notice-title": f"Project {i}",
                            "total-value": 1000000 + i * 100000,
                        }
                        for i in range(100)  # 100 results = full page
                    ]
                }
            else:
                # Second page - partial results (end of data)
                mock_response.json.return_value = {
                    "notices": [
                        {
                            "publication-number": "2024/S 015-99999",
                            "publication-date": "2024-01-20",
                            "notice-title": "Final Project",
                            "total-value": 5000000,
                        }
                    ]
                }
            mock_response.raise_for_status = MagicMock()
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_fetch

            result = await client.fetch_all_contracts(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )

            assert call_count == 2  # Two pages
            assert len(result) == 101  # 100 + 1

    @pytest.mark.asyncio
    async def test_ac6_ted_fallback_on_ocds_failure(self, client: BaseGovClient) -> None:
        """AC6: Test TED API is used when OCDS unavailable."""
        call_tracker = {"ted_called": False, "ocds_called": False}

        async def mock_get(*args, **kwargs):
            call_tracker["ocds_called"] = True
            mock_response = MagicMock()
            mock_response.json.return_value = {"resources": []}  # Empty OCDS
            mock_response.raise_for_status = MagicMock()
            return mock_response

        async def mock_post(*args, **kwargs):
            call_tracker["ted_called"] = True
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "notices": [
                    {
                        "publication-number": "2024/S 015-00001",
                        "publication-date": "2024-01-15",
                        "notice-title": "TED Contract",
                        "total-value": 6000000,
                    }
                ]
            }
            mock_response.raise_for_status = MagicMock()
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value.__aenter__.return_value
            instance.get = mock_get
            instance.post = mock_post

            result = await client.fetch_contracts(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

            assert call_tracker["ted_called"]
            assert len(result) == 1

    def test_ac7_documentation_comments(self) -> None:
        """AC7: Verify data source limitations are documented."""
        import inspect

        from raglite.external_data.clients import basegov

        source = inspect.getsource(basegov)

        # Check for important limitation documentation
        assert "UNAVAILABLE" in source or "no resources" in source.lower()
        assert "EU thresholds" in source or "EU_THRESHOLD" in source
        assert "TED API" in source
        assert "OCDS" in source
        assert "dados.gov.pt" in source

    @pytest.mark.slow  # Tests actual exponential backoff with real delays (~6s)
    @pytest.mark.asyncio
    async def test_ac8_retry_logic_exponential_backoff(self, client: BaseGovClient) -> None:
        """AC8: Test retry logic with exponential backoff."""
        call_times = []

        async def mock_post(*args, **kwargs):
            import time

            call_times.append(time.time())

            if len(call_times) < 3:
                raise httpx.TimeoutException("Timeout")

            mock_response = MagicMock()
            # Return non-empty result to avoid OCDS fallback
            mock_response.json.return_value = {
                "notices": [
                    {
                        "publication-number": "2024/S 015-00001",
                        "publication-date": "2024-01-15",
                        "total-value": 1000000,
                    }
                ]
            }
            mock_response.raise_for_status = MagicMock()
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post

            # Should succeed after retries
            result = await client.fetch_contracts(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

            assert len(call_times) == 3  # 2 failures + 1 success
            assert len(result) == 1  # Got results from TED after retry

    @pytest.mark.asyncio
    async def test_value_filtering(self, client: BaseGovClient) -> None:
        """Test min/max value filtering."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "notices": [
                {
                    "publication-number": "001",
                    "publication-date": "2024-01-15",
                    "total-value": 100000,
                },
                {
                    "publication-number": "002",
                    "publication-date": "2024-01-15",
                    "total-value": 500000,
                },
                {
                    "publication-number": "003",
                    "publication-date": "2024-01-15",
                    "total-value": 1000000,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            # Filter by min value
            result = await client.fetch_contracts(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                min_value=300000,
            )
            assert len(result) == 2

            # Filter by max value
            result = await client.fetch_contracts(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                max_value=600000,
            )
            assert len(result) == 2

    def test_parse_ted_notices_value_formats(self, client: BaseGovClient) -> None:
        """Test TED notice parsing with various value formats."""
        # Value as dict
        data = {
            "notices": [
                {
                    "publication-number": "001",
                    "publication-date": "2024-01-15",
                    "total-value": {"amount": 500000, "currency": "EUR"},
                }
            ]
        }
        result = client._parse_ted_notices(data)
        assert result[0].contract_value_eur == 500000

        # Value as string with comma decimal
        data = {
            "notices": [
                {
                    "publication-number": "002",
                    "publication-date": "2024-01-15",
                    "total-value": "1 500 000,50",
                }
            ]
        }
        result = client._parse_ted_notices(data)
        assert result[0].contract_value_eur == 1500000.50

    def test_deprecated_methods_log_warning(self, client: BaseGovClient, caplog) -> None:
        """Test deprecated methods log warnings."""
        import logging

        with caplog.at_level(logging.WARNING):
            client._parse_contracts({})

        assert "Deprecated" in caplog.text
        assert "_parse_contracts" in caplog.text or "deprecated" in caplog.text.lower()
