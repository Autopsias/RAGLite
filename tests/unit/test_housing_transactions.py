"""Unit tests for Eurostat Housing Transactions.

Story 7b-7: Demand-Side Regressors for Cement Industry

Tests for:
- EurostatHousingClient.fetch_housing_transactions()
- Quarterly period parsing (YYYY-Q1 format)
- interpolate_quarterly_series_to_monthly() function
- Integration with regressor_fetch.py

Run with: pytest tests/unit/test_housing_transactions.py -v
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from raglite.external_data.clients.eurostat_housing import EurostatHousingClient
from raglite.external_data.models import EurostatDwellingCompletions, EurostatHousingTransactions
from raglite.forecasting.regressor_fetch import interpolate_quarterly_series_to_monthly


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

        assert all(isinstance(r, EurostatHousingTransactions) for r in result)

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


class TestInterpolateQuarterlyToMonthly:
    """Unit tests for quarterly-to-monthly interpolation (AC3, AC8)."""

    def test_ac3_interpolation_empty_series(self) -> None:
        """AC3: Empty series returns empty series.

        Given: An empty pandas Series
        When: interpolate_quarterly_series_to_monthly() is called
        Then: Returns empty series without error
        """
        empty_series = pd.Series([], dtype=float)
        result = interpolate_quarterly_series_to_monthly(empty_series)
        assert len(result) == 0

    def test_ac3_interpolation_linear_basic(self) -> None:
        """AC3: Linear interpolation creates monthly values.

        Given: Quarterly data with 3 quarters
        When: interpolate_quarterly_series_to_monthly() is called with linear method
        Then: Monthly values are interpolated smoothly
        """
        # Create quarterly data (Q1, Q2, Q3 2024)
        quarterly = pd.Series(
            [100.0, 110.0, 105.0],
            index=pd.to_datetime(["2024-01-01", "2024-04-01", "2024-07-01"]),
        )

        result = interpolate_quarterly_series_to_monthly(quarterly, method="linear")

        # Should have monthly data from Jan to Jul
        assert len(result) >= 3
        # Values should be within the range of the input
        assert result.min() >= 99  # Allow small interpolation variance
        assert result.max() <= 111

    def test_ac3_interpolation_ffill(self) -> None:
        """AC3: Forward-fill creates step values.

        Given: Quarterly data
        When: interpolate_quarterly_series_to_monthly() with method='ffill'
        Then: Values are forward-filled (step function)
        """
        quarterly = pd.Series(
            [100.0, 110.0],
            index=pd.to_datetime(["2024-01-01", "2024-04-01"]),
        )

        result = interpolate_quarterly_series_to_monthly(quarterly, method="ffill")

        # All values in first quarter should be 100
        jan_val = result.loc["2024-01-01"]
        assert jan_val == 100.0

    def test_ac3_interpolation_preserves_index_type(self) -> None:
        """AC3: Interpolation preserves DatetimeIndex.

        Given: Quarterly series with DatetimeIndex
        When: interpolate_quarterly_series_to_monthly() is called
        Then: Result has DatetimeIndex
        """
        quarterly = pd.Series(
            [100.0, 110.0],
            index=pd.to_datetime(["2024-01-01", "2024-04-01"]),
        )

        result = interpolate_quarterly_series_to_monthly(quarterly)

        assert isinstance(result.index, pd.DatetimeIndex)

    def test_ac3_interpolation_handles_non_datetime_index(self) -> None:
        """AC3: Handles non-datetime index by converting.

        Given: Series with string dates
        When: interpolate_quarterly_series_to_monthly() is called
        Then: Converts to DatetimeIndex and interpolates
        """
        quarterly = pd.Series(
            [100.0, 110.0],
            index=["2024-01-01", "2024-04-01"],
        )

        result = interpolate_quarterly_series_to_monthly(quarterly)

        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) >= 2

    def test_ac3_interpolation_single_value(self) -> None:
        """AC3: Single value series returns that value.

        Given: Series with single quarterly value
        When: interpolate_quarterly_series_to_monthly() is called
        Then: Returns series with that value
        """
        quarterly = pd.Series(
            [100.0],
            index=pd.to_datetime(["2024-01-01"]),
        )

        result = interpolate_quarterly_series_to_monthly(quarterly)

        assert len(result) >= 1
        assert result.iloc[0] == 100.0


class TestRegressorConfigIntegration:
    """Tests for regressor configuration updates (AC4, AC5, AC6)."""

    def test_ac4_housing_transactions_in_available_regressors(self) -> None:
        """AC4: housing_transactions is in AVAILABLE_REGRESSORS.

        Given: The regressor configuration
        When: Checking AVAILABLE_REGRESSORS
        Then: housing_transactions is included
        """
        from raglite.forecasting.regressor_config import AVAILABLE_REGRESSORS

        assert "housing_transactions" in AVAILABLE_REGRESSORS

    def test_ac5_ebitda_uses_demand_regressors(self) -> None:
        """AC5: EBITDA mapping includes demand-side regressors.

        Given: The regressor configuration
        When: Checking EBITDA mapping
        Then: Includes construction_output, building_permits, housing_transactions
        """
        from raglite.forecasting.regressor_config import METRIC_REGRESSORS

        ebitda_regressors = METRIC_REGRESSORS.get("ebitda", [])

        # Demand-side regressors
        assert "construction_output" in ebitda_regressors
        assert "building_permits" in ebitda_regressors
        assert "construction_confidence" in ebitda_regressors
        assert "housing_transactions" in ebitda_regressors

        # Cost-side regressors (retained for margin)
        assert "ttf_gas" in ebitda_regressors
        assert "diesel" in ebitda_regressors

    def test_ac6_sales_volume_uses_demand_regressors(self) -> None:
        """AC6: sales_volume mapping includes demand-side regressors.

        Given: The regressor configuration
        When: Checking sales_volume mapping
        Then: Includes housing_transactions and construction indicators
        """
        from raglite.forecasting.regressor_config import METRIC_REGRESSORS

        sales_regressors = METRIC_REGRESSORS.get("sales_volume", [])

        assert "construction_output" in sales_regressors
        assert "building_permits" in sales_regressors
        assert "construction_confidence" in sales_regressors
        assert "housing_transactions" in sales_regressors

    def test_ac6_revenue_uses_housing_transactions(self) -> None:
        """AC6: revenue mapping includes housing_transactions.

        Given: The regressor configuration
        When: Checking revenue mapping
        Then: Includes housing_transactions
        """
        from raglite.forecasting.regressor_config import METRIC_REGRESSORS

        revenue_regressors = METRIC_REGRESSORS.get("revenue", [])
        assert "housing_transactions" in revenue_regressors

    def test_regressor_metadata_includes_housing_transactions(self) -> None:
        """Metadata includes housing_transactions with correct info."""
        from raglite.forecasting.regressor_config import REGRESSOR_METADATA

        assert "housing_transactions" in REGRESSOR_METADATA
        metadata = REGRESSOR_METADATA["housing_transactions"]
        assert metadata["source"] == "Eurostat"
        assert "quarterly" in metadata["unit"].lower()


class TestFetchSingleRegressorIntegration:
    """Tests for fetch_single_regressor integration (AC1, AC3)."""

    @pytest.mark.asyncio
    async def test_fetch_single_regressor_housing_transactions(self) -> None:
        """fetch_single_regressor handles housing_transactions.

        Given: A mocked EurostatHousingClient
        When: fetch_single_regressor("housing_transactions") is called
        Then: Returns interpolated monthly series
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        # Mock the housing client
        mock_transactions = [
            EurostatHousingTransactions(
                date=date(2024, 1, 1),
                transaction_count=35000,
                country="PT",
                period="2024-Q1",
            ),
            EurostatHousingTransactions(
                date=date(2024, 4, 1),
                transaction_count=38000,
                country="PT",
                period="2024-Q2",
            ),
            EurostatHousingTransactions(
                date=date(2024, 7, 1),
                transaction_count=42000,
                country="PT",
                period="2024-Q3",
            ),
        ]

        with patch(
            "raglite.external_data.clients.eurostat_housing.EurostatHousingClient"
        ) as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.fetch_housing_transactions = AsyncMock(return_value=mock_transactions)

            result = await fetch_single_regressor(
                "housing_transactions",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )

            assert result is not None
            assert isinstance(result, pd.Series)
            # Should have monthly data (interpolated from quarterly)
            assert len(result) >= 3

    @pytest.mark.asyncio
    async def test_fetch_single_regressor_housing_transactions_empty(self) -> None:
        """fetch_single_regressor returns None for empty data.

        Given: Housing client returns empty list
        When: fetch_single_regressor("housing_transactions") is called
        Then: Returns None
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        with patch(
            "raglite.external_data.clients.eurostat_housing.EurostatHousingClient"
        ) as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.fetch_housing_transactions = AsyncMock(return_value=[])

            result = await fetch_single_regressor(
                "housing_transactions",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )

            assert result is None


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

        assert all(isinstance(r, EurostatDwellingCompletions) for r in result)

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


class TestDwellingCompletionsConfig:
    """Tests for dwelling_completions in regressor configuration (AC4)."""

    def test_ac4_dwelling_completions_in_available_regressors(self) -> None:
        """AC4: dwelling_completions is in AVAILABLE_REGRESSORS."""
        from raglite.forecasting.regressor_config import AVAILABLE_REGRESSORS

        assert "dwelling_completions" in AVAILABLE_REGRESSORS

    def test_ac6_sales_volume_uses_dwelling_completions(self) -> None:
        """AC6: sales_volume mapping includes dwelling_completions."""
        from raglite.forecasting.regressor_config import METRIC_REGRESSORS

        sales_regressors = METRIC_REGRESSORS.get("sales_volume", [])
        # Per story spec, sales_volume should include dwelling_completions
        assert "dwelling_completions" in sales_regressors

    def test_regressor_metadata_includes_dwelling_completions(self) -> None:
        """Metadata includes dwelling_completions with correct info."""
        from raglite.forecasting.regressor_config import REGRESSOR_METADATA

        assert "dwelling_completions" in REGRESSOR_METADATA
        metadata = REGRESSOR_METADATA["dwelling_completions"]
        assert metadata["source"] == "Eurostat"
        assert "monthly" in metadata["unit"].lower()


class TestFetchDwellingCompletionsIntegration:
    """Tests for fetch_single_regressor with dwelling_completions."""

    @pytest.mark.asyncio
    async def test_fetch_single_regressor_dwelling_completions(self) -> None:
        """fetch_single_regressor handles dwelling_completions.

        Given: A mocked EurostatHousingClient
        When: fetch_single_regressor("dwelling_completions") is called
        Then: Returns monthly series
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        # Mock the housing client
        mock_completions = [
            EurostatDwellingCompletions(
                date=date(2024, 1, 1),
                completion_count=1500,
                country="PT",
                dwelling_type="TOTAL",
            ),
            EurostatDwellingCompletions(
                date=date(2024, 2, 1),
                completion_count=1600,
                country="PT",
                dwelling_type="TOTAL",
            ),
            EurostatDwellingCompletions(
                date=date(2024, 3, 1),
                completion_count=1700,
                country="PT",
                dwelling_type="TOTAL",
            ),
        ]

        with patch(
            "raglite.external_data.clients.eurostat_housing.EurostatHousingClient"
        ) as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.fetch_dwelling_completions = AsyncMock(return_value=mock_completions)

            result = await fetch_single_regressor(
                "dwelling_completions",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )

            assert result is not None
            assert isinstance(result, pd.Series)
            assert len(result) >= 3

    @pytest.mark.asyncio
    async def test_fetch_single_regressor_dwelling_completions_empty(self) -> None:
        """fetch_single_regressor returns None for empty data."""
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        with patch(
            "raglite.external_data.clients.eurostat_housing.EurostatHousingClient"
        ) as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.fetch_dwelling_completions = AsyncMock(return_value=[])

            result = await fetch_single_regressor(
                "dwelling_completions",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )

            assert result is None
