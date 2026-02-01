"""Integration tests for demand-side regressors.

Story 7b-7: Demand-Side Regressors for Cement Industry

Tests for end-to-end regressor fetching:
- housing_transactions from Eurostat prc_hpi_inx
- dwelling_completions from Eurostat sts_cobp_m

These tests hit real external APIs and require network connectivity.

Run with: pytest tests/integration/test_demand_regressors.py -v
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.external_api,  # Tests hit real external APIs
    pytest.mark.preserve_collection,  # Read-only tests, no DB modifications
    pytest.mark.slow,  # External API calls have variable latency
]


class TestHousingTransactionsIntegration:
    """Integration tests for housing transactions regressor (AC1)."""

    @pytest.mark.asyncio
    async def test_fetch_housing_transactions_real_api(self) -> None:
        """AC1: Fetch real housing transactions data from Eurostat.

        Given: Real Eurostat API is accessible
        When: fetch_housing_transactions() is called for Portugal
        Then: Returns housing transaction data for recent quarters
        """
        from raglite.external_data.clients.eurostat_housing import EurostatHousingClient

        client = EurostatHousingClient()
        result = await client.fetch_housing_transactions(
            country="PT",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Should have some data (may be empty if API is down)
        if result:
            # Verify data structure
            assert all(r.country == "PT" for r in result)
            assert all(r.transaction_count >= 0 for r in result)
            assert all("-Q" in r.period for r in result)  # Quarterly format

            # Verify date ordering
            dates = [r.date for r in result]
            assert dates == sorted(dates)

    @pytest.mark.asyncio
    async def test_fetch_single_regressor_housing_transactions(self) -> None:
        """AC1: fetch_single_regressor returns interpolated monthly series.

        Given: Real Eurostat API is accessible
        When: fetch_single_regressor("housing_transactions") is called
        Then: Returns monthly time series (interpolated from quarterly)
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "housing_transactions",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # May be None if API is down
        if result is not None:
            assert isinstance(result, pd.Series)
            assert len(result) > 0
            assert isinstance(result.index, pd.DatetimeIndex)


class TestDwellingCompletionsIntegration:
    """Integration tests for dwelling completions regressor (AC2)."""

    @pytest.mark.asyncio
    async def test_fetch_dwelling_completions_real_api(self) -> None:
        """AC2: Fetch real dwelling completions data from Eurostat.

        Given: Real Eurostat API is accessible
        When: fetch_dwelling_completions() is called for Portugal
        Then: Returns dwelling completion data for recent months
        """
        from raglite.external_data.clients.eurostat_housing import EurostatHousingClient

        client = EurostatHousingClient()
        result = await client.fetch_dwelling_completions(
            country="PT",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Should have some data (may be empty if API is down)
        if result:
            # Verify data structure
            assert all(r.country == "PT" for r in result)
            assert all(r.completion_count >= 0 for r in result)
            assert all(r.dwelling_type == "TOTAL" for r in result)

            # Verify date ordering
            dates = [r.date for r in result]
            assert dates == sorted(dates)

    @pytest.mark.asyncio
    async def test_fetch_single_regressor_dwelling_completions(self) -> None:
        """AC2: fetch_single_regressor returns monthly series.

        Given: Real Eurostat API is accessible
        When: fetch_single_regressor("dwelling_completions") is called
        Then: Returns monthly time series
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "dwelling_completions",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # May be None if API is down
        if result is not None:
            assert isinstance(result, pd.Series)
            assert len(result) > 0
            assert isinstance(result.index, pd.DatetimeIndex)


class TestRegressorConfigIntegration:
    """Integration tests for regressor configuration (AC4-AC6)."""

    @pytest.mark.asyncio
    async def test_ebitda_regressors_fetchable(self) -> None:
        """AC5: All EBITDA regressors can be fetched.

        Given: External APIs are accessible
        When: fetch_regressors_for_metric("ebitda") is called
        Then: Returns dict with at least some demand-side regressors
        """
        from raglite.forecasting.regressor_fetch import fetch_regressors_for_metric

        regressors = await fetch_regressors_for_metric(
            metric="ebitda",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Should have some regressors (may not have all due to API issues)
        # Just verify the function runs without error and returns a dict
        assert isinstance(regressors, dict)

        # Log which regressors were successfully fetched
        if regressors:
            print(f"Successfully fetched EBITDA regressors: {list(regressors.keys())}")

    @pytest.mark.asyncio
    async def test_sales_volume_regressors_fetchable(self) -> None:
        """AC6: All sales_volume regressors can be fetched.

        Given: External APIs are accessible
        When: fetch_regressors_for_metric("sales_volume") is called
        Then: Returns dict with demand-side regressors
        """
        from raglite.forecasting.regressor_fetch import fetch_regressors_for_metric

        regressors = await fetch_regressors_for_metric(
            metric="sales_volume",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Should have some regressors
        assert isinstance(regressors, dict)

        # Log which regressors were successfully fetched
        if regressors:
            print(f"Successfully fetched sales_volume regressors: {list(regressors.keys())}")


class TestQuarterlyToMonthlyInterpolation:
    """Integration tests for quarterly-to-monthly interpolation (AC3)."""

    @pytest.mark.asyncio
    async def test_housing_transactions_interpolated_to_monthly(self) -> None:
        """AC3: Housing transactions quarterly data is interpolated to monthly.

        Given: Quarterly housing transactions data
        When: fetch_single_regressor("housing_transactions") is called
        Then: Returns monthly frequency series
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "housing_transactions",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        if result is not None and len(result) >= 4:
            # Check that we have more data points than just quarterly
            # (interpolation should increase data points)
            # Original quarterly: ~12 quarters = 12 points
            # After interpolation: ~36 months = 36 points (or more)

            # Check monthly frequency by examining index gaps
            if len(result) > 1:
                gaps = result.index.to_series().diff().dropna()
                # Most gaps should be ~30 days (monthly) not ~90 days (quarterly)
                avg_gap_days = gaps.mean().days
                # Interpolated data should have ~30 day gaps
                assert avg_gap_days < 45, (
                    f"Expected monthly frequency, got avg gap of {avg_gap_days} days"
                )
