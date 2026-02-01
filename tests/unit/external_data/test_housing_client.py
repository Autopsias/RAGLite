"""Unit tests for Eurostat Housing Client (transactions and completions).

Story 7b-7: Demand-Side Regressors for Cement Industry

Tests for:
- EurostatHousingClient.fetch_housing_transactions()
- EurostatHousingClient.fetch_dwelling_completions()
- Quarterly/monthly period parsing

Run with: pytest tests/unit/external_data/test_housing_client.py -v
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest

from raglite.external_data.clients.eurostat_housing import EurostatHousingClient


class TestEurostatHousingClient:
    """Unit tests for Eurostat housing transactions fetcher (AC1, AC8)."""

    @pytest.fixture
    def client(self) -> EurostatHousingClient:
        """Create Eurostat housing client for testing."""
        return EurostatHousingClient(timeout=1.0)

    @pytest.fixture
    def mock_housing_transactions_response(self) -> dict:
        """Mock Eurostat JSON-stat response for housing transactions.

        Represents prc_hpi_inx dataset response with 4 quarters of data.
        """
        return {
            "value": {"0": 35000, "1": 38000, "2": 42000, "3": 40000},
            "dimension": {
                "time": {
                    "category": {"index": {"2024-Q1": 0, "2024-Q2": 1, "2024-Q3": 2, "2024-Q4": 3}}
                },
                "geo": {"category": {"index": {"PT": 0}}},
                "unit": {"category": {"index": {"NR": 0}}},
                "purchase": {"category": {"index": {"TOTAL": 0}}},
            },
        }

    # =========================================================================
    # AC1: Housing Transactions Fetcher Tests
    # =========================================================================

    def test_ac1_parse_housing_transactions_valid(
        self, client: EurostatHousingClient, mock_housing_transactions_response: dict
    ) -> None:
        """AC1: Parse valid housing transactions response.

        Given: A valid Eurostat housing transactions API response
        When: _parse_housing_transactions_data() is called
        Then: Returns list of EurostatHousingTransactions with correct values
        """
        result = client._parse_housing_transactions_data(
            mock_housing_transactions_response, "PT", None, None
        )

        assert len(result) == 4
        assert result[0].transaction_count == 35000
        assert result[0].country == "PT"
        assert result[0].period == "2024-Q1"
        assert result[0].date == date(2024, 1, 1)

    def test_ac1_parse_housing_transactions_returns_model_type(
        self, client: EurostatHousingClient, mock_housing_transactions_response: dict
    ) -> None:
        """AC1: Parser returns correct Pydantic model type.

        Given: Valid response data
        When: _parse_housing_transactions_data() is called
        Then: Each result is an EurostatHousingTransactions instance
        """
        result = client._parse_housing_transactions_data(
            mock_housing_transactions_response, "PT", None, None
        )

        assert all(r.__class__.__name__ == "EurostatHousingTransactions" for r in result)

    def test_ac1_parse_housing_transactions_sorted_by_date(
        self, client: EurostatHousingClient, mock_housing_transactions_response: dict
    ) -> None:
        """AC1: Results are sorted by date ascending.

        Given: Response with quarters in any order
        When: _parse_housing_transactions_data() is called
        Then: Results are sorted by date ascending
        """
        result = client._parse_housing_transactions_data(
            mock_housing_transactions_response, "PT", None, None
        )

        dates = [r.date for r in result]
        assert dates == sorted(dates)

    def test_ac1_parse_housing_transactions_date_filter_start(
        self, client: EurostatHousingClient, mock_housing_transactions_response: dict
    ) -> None:
        """AC1: Date filtering works correctly (start_date).

        Given: Response with Q1-Q4 2024 data
        When: Filtering with start_date=2024-07-01
        Then: Only Q3 and Q4 are returned
        """
        result = client._parse_housing_transactions_data(
            mock_housing_transactions_response,
            "PT",
            start_date=date(2024, 7, 1),
            end_date=None,
        )

        assert len(result) == 2
        assert result[0].period == "2024-Q3"
        assert result[1].period == "2024-Q4"

    def test_ac1_parse_housing_transactions_date_filter_end(
        self, client: EurostatHousingClient, mock_housing_transactions_response: dict
    ) -> None:
        """AC1: Date filtering works correctly (end_date).

        Given: Response with Q1-Q4 2024 data
        When: Filtering with end_date=2024-06-30
        Then: Only Q1 and Q2 are returned
        """
        result = client._parse_housing_transactions_data(
            mock_housing_transactions_response,
            "PT",
            start_date=None,
            end_date=date(2024, 6, 30),
        )

        assert len(result) == 2
        assert result[0].period == "2024-Q1"
        assert result[1].period == "2024-Q2"

    def test_ac1_parse_housing_transactions_date_filter_both(
        self, client: EurostatHousingClient, mock_housing_transactions_response: dict
    ) -> None:
        """AC1: Date filtering works correctly (both start and end).

        Given: Response with Q1-Q4 2024 data
        When: Filtering with start_date=2024-04-01 and end_date=2024-09-30
        Then: Only Q2 and Q3 are returned
        """
        result = client._parse_housing_transactions_data(
            mock_housing_transactions_response,
            "PT",
            start_date=date(2024, 4, 1),
            end_date=date(2024, 9, 30),
        )

        assert len(result) == 2
        assert result[0].period == "2024-Q2"
        assert result[1].period == "2024-Q3"

    def test_ac1_parse_housing_transactions_empty_values(
        self, client: EurostatHousingClient
    ) -> None:
        """AC1: Handle empty response gracefully.

        Given: An empty Eurostat response
        When: _parse_housing_transactions_data() is called
        Then: Returns empty list without error
        """
        empty_response = {"value": {}, "dimension": {"time": {"category": {"index": {}}}}}
        result = client._parse_housing_transactions_data(empty_response, "PT", None, None)

        assert result == []

    # =========================================================================
    # Quarterly Period Parsing Tests
    # =========================================================================

    def test_parse_quarterly_period_q1(self, client: EurostatHousingClient) -> None:
        """Parse Q1 period correctly."""
        result = client._parse_quarterly_period("2024-Q1")
        assert result == date(2024, 1, 1)

    def test_parse_quarterly_period_q2(self, client: EurostatHousingClient) -> None:
        """Parse Q2 period correctly."""
        result = client._parse_quarterly_period("2024-Q2")
        assert result == date(2024, 4, 1)

    def test_parse_quarterly_period_q3(self, client: EurostatHousingClient) -> None:
        """Parse Q3 period correctly."""
        result = client._parse_quarterly_period("2024-Q3")
        assert result == date(2024, 7, 1)

    def test_parse_quarterly_period_q4(self, client: EurostatHousingClient) -> None:
        """Parse Q4 period correctly."""
        result = client._parse_quarterly_period("2024-Q4")
        assert result == date(2024, 10, 1)

    def test_parse_quarterly_period_invalid_format(self, client: EurostatHousingClient) -> None:
        """Return None for invalid period format."""
        assert client._parse_quarterly_period("2024-01") is None
        assert client._parse_quarterly_period("2024") is None
        assert client._parse_quarterly_period("Q1-2024") is None
        assert client._parse_quarterly_period("invalid") is None

    def test_parse_quarterly_period_invalid_quarter(self, client: EurostatHousingClient) -> None:
        """Return None for invalid quarter number."""
        assert client._parse_quarterly_period("2024-Q0") is None
        assert client._parse_quarterly_period("2024-Q5") is None

    # =========================================================================
    # Fetch Method Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_fetch_housing_transactions_calls_api(
        self, client: EurostatHousingClient, mock_housing_transactions_response: dict
    ) -> None:
        """AC1: fetch_housing_transactions() calls API correctly.

        Given: A mocked Eurostat API
        When: fetch_housing_transactions() is called
        Then: API is called with correct parameters
        """
        with patch.object(client, "_fetch_with_retry", new_callable=AsyncMock) as mock_fetch:
            # Create a mock response with .json() method
            mock_response = Mock()
            mock_response.json.return_value = mock_housing_transactions_response
            mock_fetch.return_value = mock_response

            result = await client.fetch_housing_transactions(
                country="PT",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )

            assert mock_fetch.called
            assert len(result) == 4

    @pytest.mark.asyncio
    async def test_fetch_housing_transactions_handles_error(
        self, client: EurostatHousingClient
    ) -> None:
        """AC1: fetch_housing_transactions() handles API errors gracefully.

        Given: API returns an error
        When: fetch_housing_transactions() is called
        Then: Returns empty list without raising exception
        """
        with patch.object(client, "_fetch_with_retry", new_callable=AsyncMock) as mock_fetch:
            # Use specific exception types that are caught
            mock_fetch.side_effect = TimeoutError("API Timeout")

            result = await client.fetch_housing_transactions(country="PT")

            assert result == []


class TestDwellingCompletions:
    """Unit tests for dwelling completions fetcher (AC2)."""

    @pytest.fixture
    def client(self) -> EurostatHousingClient:
        """Create Eurostat housing client for testing."""
        return EurostatHousingClient(timeout=1.0)

    @pytest.fixture
    def mock_dwelling_completions_response(self) -> dict:
        """Mock Eurostat JSON-stat response for dwelling completions.

        Represents sts_cobp_m dataset response with monthly data.
        """
        return {
            "value": {"0": 1500, "1": 1600, "2": 1700, "3": 1800},
            "dimension": {
                "time": {
                    "category": {"index": {"2024M01": 0, "2024M02": 1, "2024M03": 2, "2024M04": 3}}
                },
                "geo": {"category": {"index": {"PT": 0}}},
                "unit": {"category": {"index": {"NR": 0}}},
                "building": {"category": {"index": {"TOTAL": 0}}},
            },
        }

    def test_ac2_parse_dwelling_completions_valid(
        self, client: EurostatHousingClient, mock_dwelling_completions_response: dict
    ) -> None:
        """AC2: Parse valid dwelling completions response.

        Given: A valid Eurostat dwelling completions API response
        When: _parse_dwelling_completions_data() is called
        Then: Returns list of EurostatDwellingCompletions with correct values
        """
        result = client._parse_dwelling_completions_data(
            mock_dwelling_completions_response, "PT", "TOTAL", None, None
        )

        assert len(result) == 4
        assert result[0].completion_count == 1500
        assert result[0].country == "PT"
        assert result[0].dwelling_type == "TOTAL"
        assert result[0].date == date(2024, 1, 1)

    def test_ac2_parse_dwelling_completions_returns_model_type(
        self, client: EurostatHousingClient, mock_dwelling_completions_response: dict
    ) -> None:
        """AC2: Parser returns correct Pydantic model type."""
        result = client._parse_dwelling_completions_data(
            mock_dwelling_completions_response, "PT", "TOTAL", None, None
        )

        assert all(r.__class__.__name__ == "EurostatDwellingCompletions" for r in result)

    def test_ac2_parse_dwelling_completions_sorted_by_date(
        self, client: EurostatHousingClient, mock_dwelling_completions_response: dict
    ) -> None:
        """AC2: Results are sorted by date ascending."""
        result = client._parse_dwelling_completions_data(
            mock_dwelling_completions_response, "PT", "TOTAL", None, None
        )

        dates = [r.date for r in result]
        assert dates == sorted(dates)

    def test_ac2_parse_dwelling_completions_date_filter_start(
        self, client: EurostatHousingClient, mock_dwelling_completions_response: dict
    ) -> None:
        """AC2: Date filtering works correctly (start_date)."""
        result = client._parse_dwelling_completions_data(
            mock_dwelling_completions_response,
            "PT",
            "TOTAL",
            start_date=date(2024, 3, 1),
            end_date=None,
        )

        assert len(result) == 2
        assert result[0].date == date(2024, 3, 1)
        assert result[1].date == date(2024, 4, 1)

    def test_ac2_parse_dwelling_completions_date_filter_end(
        self, client: EurostatHousingClient, mock_dwelling_completions_response: dict
    ) -> None:
        """AC2: Date filtering works correctly (end_date)."""
        result = client._parse_dwelling_completions_data(
            mock_dwelling_completions_response,
            "PT",
            "TOTAL",
            start_date=None,
            end_date=date(2024, 2, 28),
        )

        assert len(result) == 2
        assert result[0].date == date(2024, 1, 1)
        assert result[1].date == date(2024, 2, 1)

    def test_ac2_parse_dwelling_completions_empty_values(
        self, client: EurostatHousingClient
    ) -> None:
        """AC2: Handle empty response gracefully."""
        empty_response = {"value": {}, "dimension": {"time": {"category": {"index": {}}}}}
        result = client._parse_dwelling_completions_data(empty_response, "PT", "TOTAL", None, None)

        assert result == []

    def test_parse_monthly_period_valid(self, client: EurostatHousingClient) -> None:
        """Parse monthly period correctly."""
        assert client._parse_monthly_period("2024M01") == date(2024, 1, 1)
        assert client._parse_monthly_period("2024M06") == date(2024, 6, 1)
        assert client._parse_monthly_period("2024M12") == date(2024, 12, 1)

    def test_parse_monthly_period_format_yyyy_mm(self, client: EurostatHousingClient) -> None:
        """Parse YYYY-MM format correctly (used by sts_cobp_m)."""
        assert client._parse_monthly_period("2024-01") == date(2024, 1, 1)
        assert client._parse_monthly_period("2024-06") == date(2024, 6, 1)
        assert client._parse_monthly_period("2024-12") == date(2024, 12, 1)

    def test_parse_monthly_period_invalid(self, client: EurostatHousingClient) -> None:
        """Return None for invalid period format."""
        assert client._parse_monthly_period("2024") is None
        assert client._parse_monthly_period("M01-2024") is None
        assert client._parse_monthly_period("invalid") is None
        assert client._parse_monthly_period("24-01") is None  # Too short year

    @pytest.mark.asyncio
    async def test_fetch_dwelling_completions_calls_api(
        self, client: EurostatHousingClient, mock_dwelling_completions_response: dict
    ) -> None:
        """AC2: fetch_dwelling_completions() calls API correctly."""
        with patch.object(client, "_fetch_with_retry", new_callable=AsyncMock) as mock_fetch:
            # Create a mock response with .json() method
            mock_response = Mock()
            mock_response.json.return_value = mock_dwelling_completions_response
            mock_fetch.return_value = mock_response

            result = await client.fetch_dwelling_completions(
                country="PT",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )

            assert mock_fetch.called
            assert len(result) == 4

    @pytest.mark.asyncio
    async def test_fetch_dwelling_completions_handles_error(
        self, client: EurostatHousingClient
    ) -> None:
        """AC2: fetch_dwelling_completions() handles API errors gracefully."""
        with patch.object(client, "_fetch_with_retry", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = TimeoutError("API Timeout")

            result = await client.fetch_dwelling_completions(country="PT")

            assert result == []
