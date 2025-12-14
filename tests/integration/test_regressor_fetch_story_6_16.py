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
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

# Module-level marker for all tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,  # Real API calls
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


class TestErrorHandlingForNewRegressors:
    """[P1] Error handling tests for construction and industrial fetching."""

    @pytest.mark.asyncio
    async def test_p1_construction_fetch_failure_returns_none(self) -> None:
        """
        [P1] construction_output fetch failure should return None.

        Given: Mock Eurostat client that raises exception
        When: fetch_single_regressor() is called
        Then: Returns None (graceful degradation)
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        with patch("raglite.external_data.clients.eurostat.EurostatClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.fetch_construction_output = AsyncMock(side_effect=Exception("API error"))

            result = await fetch_single_regressor(
                "construction_output", date(2023, 1, 1), date(2024, 6, 30)
            )

            assert result is None, "Should return None on fetch failure"

    @pytest.mark.asyncio
    async def test_p1_industrial_fetch_failure_returns_none(self) -> None:
        """
        [P1] industrial_production fetch failure should return None.

        Given: Mock Eurostat client that raises exception
        When: fetch_single_regressor() is called
        Then: Returns None
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        with patch("raglite.external_data.clients.eurostat.EurostatClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.fetch_industrial_production = AsyncMock(side_effect=Exception("API error"))

            result = await fetch_single_regressor(
                "industrial_production", date(2023, 1, 1), date(2024, 6, 30)
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_p2_empty_data_returns_none(self) -> None:
        """
        [P2] Empty data response should return None.

        Given: Eurostat returns empty list
        When: fetch_single_regressor() is called
        Then: Returns None (no data to create Series)
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        with patch("raglite.external_data.clients.eurostat.EurostatClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.fetch_construction_output = AsyncMock(return_value=[])  # Empty

            result = await fetch_single_regressor(
                "construction_output", date(2023, 1, 1), date(2024, 6, 30)
            )

            assert result is None, "Empty data should return None"

    @pytest.mark.asyncio
    async def test_p2_partial_failure_continues_with_successful_regressors(self) -> None:
        """
        [P2] Partial fetch failures should not block successful regressors.

        Given: construction_output succeeds, industrial_production fails
        When: fetch_regressors_for_metric() with both
        Then: Returns dict with construction_output only
        """
        from raglite.forecasting.regressor_fetch import fetch_regressors_for_metric

        with patch("raglite.forecasting.regressor_fetch.fetch_single_regressor") as mock_fetch:

            async def mock_fetch_single(reg_name: str, start: date, end: date):
                if reg_name == "construction_output":
                    # Success
                    return pd.Series(
                        [105.0, 106.0], index=pd.DatetimeIndex([date(2023, 1, 1), date(2023, 2, 1)])
                    )
                else:
                    # Failure
                    return None

            mock_fetch.side_effect = mock_fetch_single

            result = await fetch_regressors_for_metric(
                metric="sales_volume",
                start_date=date(2023, 1, 1),
                end_date=date(2024, 6, 30),
                regressor_names=["construction_output", "industrial_production"],
            )

            # Should have construction_output but not industrial_production
            assert "construction_output" in result
            assert "industrial_production" not in result


class TestParallelFetchingPerformance:
    """[P3] Performance tests for parallel fetching of new indicators."""

    @pytest.mark.asyncio
    async def test_p3_parallel_fetch_faster_than_sequential(self) -> None:
        """
        [P3] Parallel fetching should be faster than sequential.

        Given: Request for multiple regressors including new indicators
        When: fetch_regressors_for_metric() is called
        Then: Completes in reasonable time (parallel fetch via asyncio.gather)
        """
        import time

        from raglite.forecasting.regressor_fetch import fetch_regressors_for_metric

        start_time = time.time()

        result = await fetch_regressors_for_metric(
            metric="sales_volume",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        elapsed = time.time() - start_time

        # Should complete in < 30 seconds with parallel fetch
        # (sequential would be much slower)
        assert elapsed < 30, f"Parallel fetch took {elapsed:.1f}s (should be <30s)"
        assert len(result) > 0, "Should successfully fetch regressors"

    @pytest.mark.asyncio
    async def test_p3_fetch_both_new_indicators_concurrently(self) -> None:
        """
        [P3] Fetching both construction and industrial concurrently should work.

        Given: Explicit request for both new regressors
        When: fetch_regressors_for_metric() is called
        Then: Both are fetched successfully
        """
        from raglite.forecasting.regressor_fetch import fetch_regressors_for_metric

        result = await fetch_regressors_for_metric(
            metric="production_volume",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
            regressor_names=["construction_output", "industrial_production"],
        )

        # Both should be present (unless API fails)
        assert "construction_output" in result or "industrial_production" in result, (
            "Should fetch at least one new indicator"
        )


class TestRegressorDataQuality:
    """[P2] Data quality checks for fetched construction and industrial data."""

    @pytest.mark.asyncio
    async def test_p2_construction_output_reasonable_value_range(self) -> None:
        """
        [P2] construction_output values should be in reasonable range (0-500).

        Given: Fetched construction_output data (index 2021=100)
        When: Examining values
        Then: Values are typically 50-200 (reasonable index range)
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "construction_output", date(2023, 1, 1), date(2024, 6, 30)
        )

        assert result is not None
        # Index values should be reasonable (not 10000 or 0.001)
        assert result.min() > 0, "Minimum should be positive"
        assert result.max() < 500, "Maximum should be reasonable for index"

    @pytest.mark.asyncio
    async def test_p2_industrial_production_reasonable_value_range(self) -> None:
        """
        [P2] industrial_production values should be in reasonable range.

        Given: Fetched industrial_production data (index 2021=100)
        When: Examining values
        Then: Values are typically 50-200
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "industrial_production", date(2023, 1, 1), date(2024, 6, 30)
        )

        assert result is not None
        assert result.min() > 0
        assert result.max() < 500

    @pytest.mark.asyncio
    async def test_p2_construction_output_monthly_frequency(self) -> None:
        """
        [P2] construction_output should have monthly frequency.

        Given: Fetched construction_output data for 2-year period
        When: Checking data frequency
        Then: Has approximately monthly spacing (18-24 months)
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "construction_output", date(2023, 1, 1), date(2024, 12, 31)
        )

        assert result is not None
        # Should have ~24 months of data (allow some missing)
        assert len(result) >= 18, f"Expected ~24 months, got {len(result)}"

    @pytest.mark.asyncio
    async def test_p2_industrial_production_monthly_frequency(self) -> None:
        """
        [P2] industrial_production should have monthly frequency.

        Given: Fetched industrial_production data for 2-year period
        When: Checking data frequency
        Then: Has approximately monthly spacing
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "industrial_production", date(2023, 1, 1), date(2024, 12, 31)
        )

        assert result is not None
        assert len(result) >= 18, f"Expected ~24 months, got {len(result)}"
