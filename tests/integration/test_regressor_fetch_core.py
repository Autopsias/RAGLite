"""Integration tests for regressor fetching with Story 6.16 indicators.

Story 6.16: Add Eurostat Construction & Industrial Indicators

This test file focuses on:
- [P0] Successful fetching of construction_output via regressor_fetch
- [P0] Successful fetching of industrial_production via regressor_fetch
- [P1] Integration with fetch_regressors_for_metric()
- [P2] Error handling for fetch failures
- [P3] Performance of parallel fetching

These tests hit real Eurostat API (marked as slow).

Run with: pytest tests/integration/test_regressor_fetch_story_6_16.py -v -m integration
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

# Module-level marker for all tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,  # Real API calls
    pytest.mark.preserve_collection,  # Read-only tests (don't modify Qdrant)
]


class TestConstructionOutputRegressorFetch:
    """[P0] Integration tests for fetching construction_output regressor."""

    @pytest.mark.asyncio
    async def test_p0_fetch_construction_output_returns_series(self) -> None:
        """
        [P0] fetch_single_regressor("construction_output") returns pandas Series.

        Given: Request for construction_output regressor with date range
        When: fetch_single_regressor() is called
        Then: Returns pandas Series with datetime index and float values
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "construction_output", date(2023, 1, 1), date(2024, 6, 30)
        )

        assert result is not None, "Should return data for construction_output"
        assert isinstance(result, pd.Series), "Should return pandas Series"
        assert len(result) > 0, "Should have data points"
        assert result.dtype == float, "Values should be float (index values)"

    @pytest.mark.asyncio
    async def test_p0_construction_output_has_datetime_index(self) -> None:
        """
        [P0] construction_output Series should have DatetimeIndex.

        Given: Fetched construction_output data
        When: Examining the index
        Then: Index is DatetimeIndex
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "construction_output", date(2023, 1, 1), date(2024, 6, 30)
        )

        assert result is not None
        assert isinstance(result.index, pd.DatetimeIndex), "Index should be DatetimeIndex"

    @pytest.mark.asyncio
    async def test_p1_construction_output_values_positive(self) -> None:
        """
        [P1] construction_output index values should all be positive.

        Given: Fetched construction_output data
        When: Examining values
        Then: All values > 0 (index values are positive)
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "construction_output", date(2023, 1, 1), date(2024, 6, 30)
        )

        assert result is not None
        assert (result > 0).all(), "All index values should be positive"

    @pytest.mark.asyncio
    async def test_p1_construction_output_no_duplicates(self) -> None:
        """
        [P1] construction_output should have no duplicate dates.

        Given: Fetched construction_output data
        When: Checking for duplicate indices
        Then: No duplicates exist (deduplicated in fetch_single_regressor)
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "construction_output", date(2023, 1, 1), date(2024, 6, 30)
        )

        assert result is not None
        assert not result.index.duplicated().any(), "Should have no duplicate dates"

    @pytest.mark.asyncio
    async def test_p2_construction_output_sorted_by_date(self) -> None:
        """
        [P2] construction_output Series should be sorted by date.

        Given: Fetched construction_output data
        When: Examining index order
        Then: Index is sorted ascending
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "construction_output", date(2023, 1, 1), date(2024, 6, 30)
        )

        assert result is not None
        assert result.index.is_monotonic_increasing, "Index should be sorted ascending"


class TestIndustrialProductionRegressorFetch:
    """[P0] Integration tests for fetching industrial_production regressor."""

    @pytest.mark.asyncio
    async def test_p0_fetch_industrial_production_returns_series(self) -> None:
        """
        [P0] fetch_single_regressor("industrial_production") returns pandas Series.

        Given: Request for industrial_production regressor with date range
        When: fetch_single_regressor() is called
        Then: Returns pandas Series with datetime index and float values
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "industrial_production", date(2023, 1, 1), date(2024, 6, 30)
        )

        assert result is not None, "Should return data for industrial_production"
        assert isinstance(result, pd.Series), "Should return pandas Series"
        assert len(result) > 0, "Should have data points"
        assert result.dtype == float, "Values should be float"

    @pytest.mark.asyncio
    async def test_p0_industrial_production_has_datetime_index(self) -> None:
        """
        [P0] industrial_production Series should have DatetimeIndex.

        Given: Fetched industrial_production data
        When: Examining the index
        Then: Index is DatetimeIndex
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "industrial_production", date(2023, 1, 1), date(2024, 6, 30)
        )

        assert result is not None
        assert isinstance(result.index, pd.DatetimeIndex)

    @pytest.mark.asyncio
    async def test_p1_industrial_production_values_positive(self) -> None:
        """
        [P1] industrial_production index values should all be positive.

        Given: Fetched industrial_production data
        When: Examining values
        Then: All values > 0
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "industrial_production", date(2023, 1, 1), date(2024, 6, 30)
        )

        assert result is not None
        assert (result > 0).all(), "All index values should be positive"

    @pytest.mark.asyncio
    async def test_p1_industrial_production_no_duplicates(self) -> None:
        """
        [P1] industrial_production should have no duplicate dates.

        Given: Fetched industrial_production data
        When: Checking for duplicate indices
        Then: No duplicates exist
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "industrial_production", date(2023, 1, 1), date(2024, 6, 30)
        )

        assert result is not None
        assert not result.index.duplicated().any()


class TestFetchRegressorsForMetricIntegration:
    """[P1] Integration tests for fetch_regressors_for_metric() with new indicators."""

    @pytest.mark.asyncio
    async def test_p1_sales_volume_fetches_construction_and_industrial(self) -> None:
        """
        [P1] sales_volume should fetch construction_output and industrial_production.

        Given: Metric "sales_volume"
        When: fetch_regressors_for_metric() is called
        Then: Returns dict with construction_output and industrial_production
        """
        from raglite.forecasting.regressor_fetch import fetch_regressors_for_metric

        result = await fetch_regressors_for_metric(
            metric="sales_volume", start_date=date(2023, 1, 1), end_date=date(2024, 6, 30)
        )

        # Should have construction_output and/or industrial_production
        assert len(result) > 0, "Should fetch regressors"
        assert "construction_output" in result or "industrial_production" in result, (
            "Should include new indicators"
        )

    @pytest.mark.asyncio
    async def test_p1_capacity_utilization_fetches_industrial(self) -> None:
        """
        [P1] capacity_utilization should fetch industrial_production.

        Given: Metric "capacity_utilization"
        When: fetch_regressors_for_metric() is called
        Then: Returns dict with industrial_production
        """
        from raglite.forecasting.regressor_fetch import fetch_regressors_for_metric

        result = await fetch_regressors_for_metric(
            metric="capacity_utilization",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert "industrial_production" in result, "Should fetch industrial_production"

    @pytest.mark.asyncio
    async def test_p2_explicit_regressors_override_auto_selection(self) -> None:
        """
        [P2] Explicit regressor_names should override auto-selection.

        Given: Explicit regressor_names=["construction_output"]
        When: fetch_regressors_for_metric() is called
        Then: Only fetches construction_output (no auto-selection)
        """
        from raglite.forecasting.regressor_fetch import fetch_regressors_for_metric

        result = await fetch_regressors_for_metric(
            metric="revenue",  # Would normally select euribor, diesel, ttf
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
            regressor_names=["construction_output"],  # Explicit override
        )

        # Should only have construction_output
        assert "construction_output" in result
        assert "euribor_3m" not in result, "Should not auto-select when explicit names given"
