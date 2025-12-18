"""Unit tests for Shared Exception and Rate Limiting Tests client.

Story 7.1: Split test_external_data_clients.py
This module contains tests for: TestExceptions, TestRateLimitHandling
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from raglite.external_data.clients.bpstat import BPstatClient
from raglite.external_data.clients.ine import INEClient
from raglite.external_data.exceptions import (
    ExternalDataFetchError,
    ExternalDataValidationError,
)


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

        # Story 6.10.3: Clear cache to ensure mock is used
        client._cache.clear()

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
        """Test BPstat client retries on 429 rate limit.

        Story 6.9.3: Updated for new API structure (single API call, not 3).
        """
        client = BPstatClient()

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_error = httpx.HTTPStatusError(
            "Too Many Requests", request=MagicMock(), response=rate_limit_response
        )

        success_response = MagicMock()
        # Story 6.9.3: New response format with series_id
        success_response.json.return_value = {
            "observations": [{"period": "2024-01", "value": 3.45, "series_id": "12710733"}]
        }
        success_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            # Story 6.9.3: Now single API call with retry: 429 then success
            mock_get = AsyncMock(
                side_effect=[
                    rate_limit_error,
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
            assert mock_get.call_count == 2  # 1 retry + 1 success


# =============================================================================
# End of Exception and Rate Limiting Tests
# =============================================================================
