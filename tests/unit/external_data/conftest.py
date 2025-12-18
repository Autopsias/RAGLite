"""Shared fixtures for external data client unit tests.

Story 7.1: Split test_external_data_clients.py
This conftest provides shared fixtures and utilities for all external data client test modules.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.fixture
def mock_httpx_response() -> MagicMock:
    """Create a mock httpx response with configurable status and JSON.

    Returns:
        MagicMock configured as a standard httpx response.
    """
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value={})
    return response


@pytest.fixture
def mock_httpx_client(mock_httpx_response: MagicMock) -> MagicMock:
    """Create a mock async httpx client context manager.

    Args:
        mock_httpx_response: Pre-configured mock response.

    Yields:
        Mock httpx.AsyncClient that returns the mock response.
    """
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_httpx_response
        )
        yield mock_client


@pytest.fixture
def sample_date_range() -> tuple[date, date]:
    """Common date range for testing.

    Returns:
        Tuple of (start_date, end_date) for 2024 calendar year.
    """
    return date(2024, 1, 1), date(2024, 12, 31)


@pytest.fixture
def mock_error_response() -> MagicMock:
    """Create a mock HTTP error response.

    Returns:
        MagicMock configured as a failed httpx response.
    """
    response = MagicMock()
    response.status_code = 500
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=response
    )
    return response
