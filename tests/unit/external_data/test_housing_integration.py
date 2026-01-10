"""Unit tests for housing data integration with regressor system.

Story 7b-7: Demand-Side Regressors for Cement Industry

Tests for:
- interpolate_quarterly_series_to_monthly() function
- Integration with regressor_fetch.py
- Regressor configuration

Run with: pytest tests/unit/external_data/test_housing_integration.py -v
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from raglite.external_data.models import (  # noqa: E402
    EurostatDwellingCompletions,
    EurostatHousingTransactions,
)
from raglite.forecasting.regressor_fetch import interpolate_quarterly_series_to_monthly


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
        from raglite.forecasting.regressor_config_data.regressor_metadata import REGRESSOR_METADATA

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
        from raglite.forecasting.regressor_config_data.regressor_metadata import REGRESSOR_METADATA

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
